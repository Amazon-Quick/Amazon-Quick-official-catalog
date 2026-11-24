#!/usr/bin/env python3
"""
description: Check that a variance table foots, recompute each variance with favorable or unfavorable direction and materiality, summarize the report for chat, and re-export the rate, volume and mix split and the ledger check.
last_updated: 2026-11-24

Deterministic checks for a variance table, before any commentary is written.

Reads a CSV or Markdown table (passed as text) with one row per line item and reports:
  * footing: every parent recomputes from its children, with each child's roll-up sign
    (costs subtract from profit lines), within a tolerance scaled to the digits shown;
  * variance: actual minus comparison, recomputed, and checked against a stated variance column;
  * direction: favorable (F) or unfavorable (U) from the line type, never from the sign alone;
  * materiality: which lines clear the threshold;
  * ratio lines (margins, rates) are compared in percentage points and bps, never summed.

Import it and call the functions (the agent never runs it from a shell):
  import variance_check
  report = variance_check.check(text, unit="M")
  print(variance_check.summarize(report))
  variance_check.rvm(segment_text)
  variance_check.check_ledger(ledger_text, report)
The command-line entry point is for local testing only.

Standard library only. references/script-interface.md documents the columns,
arguments and result keys.
"""

import argparse
import json
import sys
from pathlib import Path

from variance_ledger import check_ledger
from variance_rvm import rvm
from variance_table import clean_num, decimals, find_col, parse_table
from variance_types import FAVORABLE_VALUES, LINE_TYPES, direction, infer_type

CHECK_COLUMNS = (
    "line",
    "actual",
    "comparison",
    "variance",
    "type",
    "parent",
    "rollup",
    "favorable_when",
    "formula",
)
REQUIRED_COLUMNS = ("line", "actual", "comparison")
MONEY_TYPES = ("revenue", "cost", "profit")
UNSUMMED_TYPES = ("ratio", "per_unit")
RATIO_MATERIAL_BPS = 10
SHARE_OF_HEADLINE = 0.01
FLOAT_EPSILON = 1e-12
SUMMARY_FIELDS = (
    "line",
    "type",
    "parent",
    "actual",
    "comparison",
    "variance",
    "variance_pct",
    "variance_bps",
    "direction",
    "material",
)

# Re-exported so callers import one module.
__all__ = [
    "check",
    "check_ledger",
    "clean_num",
    "infer_type",
    "parse_table",
    "rvm",
    "summarize",
]


def _cell(r, cols, key):
    return str(r.get(cols[key], "")).strip() if cols[key] else ""


def _line_type(r, cols, name, warnings):
    rtype = _cell(r, cols, "type").lower() or infer_type(name)
    if rtype not in LINE_TYPES:
        warnings.append(
            f"Line '{name}': unknown type '{rtype}', treated as metric. Use revenue, cost, profit, ratio, per_unit, or metric."
        )
        return "metric"
    return rtype


def _favorable(r, cols, name, warnings):
    fav = _cell(r, cols, "favorable_when").lower() or None
    if fav not in (None, *FAVORABLE_VALUES):
        warnings.append(
            f"Line '{name}': favorable_when must be higher, lower, or neutral; ignored."
        )
        return None
    return fav


def _read_row(r, cols, costs_negative, warnings):
    name = _cell(r, cols, "line")
    actual, comp = (
        clean_num(r.get(cols["actual"])),
        clean_num(r.get(cols["comparison"])),
    )
    stated = clean_num(r.get(cols["variance"])) if cols["variance"] else None
    rtype = _line_type(r, cols, name, warnings)
    if costs_negative and rtype == "cost":
        actual, comp, stated = (
            None if v is None else -v for v in (actual, comp, stated)
        )
    row = {
        "line": name,
        "type": rtype,
        "actual": actual,
        "comparison": comp,
        "parent": _cell(r, cols, "parent") or None,
        "rollup": _cell(r, cols, "rollup") or None,
        "favorable_when": _favorable(r, cols, name, warnings),
        "decimals": max(
            decimals(r.get(cols["actual"])), decimals(r.get(cols["comparison"]))
        ),
        "formula": _cell(r, cols, "formula") or None,
        "variance_stated": stated,
    }
    if actual is None or comp is None:
        warnings.append(
            f"Line '{name}': missing actual or comparison value; no variance computed."
        )
        row["variance"] = None
    else:
        row["variance"] = actual - comp
    return row


def _read_rows(raw, cols, costs_negative, report):
    rows, seen, neg_cost_lines = [], set(), []
    for r in raw:
        name = _cell(r, cols, "line")
        if not name:
            continue
        if name.lower() in seen:
            report["faults"].append(
                f"Duplicate line '{name}': give each line a unique name."
            )
        seen.add(name.lower())
        row = _read_row(r, cols, costs_negative, report["warnings"])
        if (
            row["type"] == "cost"
            and not costs_negative
            and any(v is not None and v < 0 for v in (row["actual"], row["comparison"]))
        ):
            neg_cost_lines.append(name)
        rows.append(row)
    if neg_cost_lines:
        report["warnings"].append(
            f"Cost lines with negative values ({', '.join(neg_cost_lines)}): are costs stored as negatives? If so, re-run check with costs_negative=True, or F and U will be reversed."
        )
    return rows


def _check_stated(rows, tol, faults):
    for r in rows:
        if (
            r["variance_stated"] is not None
            and r["variance"] is not None
            and r["type"] not in UNSUMMED_TYPES
            and abs(r["variance_stated"] - r["variance"]) > tol
        ):
            faults.append(
                f"Line '{r['line']}': stated variance {r['variance_stated']:,.4g} but actual - comparison = {r['variance']:,.4g}."
            )


def _rollup_sign(kid, parent):
    if kid["rollup"] in ("+", "-"):
        return kid["rollup"]
    return (
        "-"
        if kid["type"] == "cost" and parent["type"] in ("profit", "revenue")
        else "+"
    )


def _foot_column(parent, kids, col, tolerance, report):
    """Compare one parent value with the signed sum of its children."""
    tol, explicit = tolerance
    total, summed_count = 0.0, 0
    for k in kids:
        if k["type"] in UNSUMMED_TYPES or k[col] is None:
            continue
        total += k[col] if _rollup_sign(k, parent) == "+" else -k[col]
        summed_count += 1
    gap = abs(total - parent[col])
    # Each displayed child and the displayed total can be rounded, unless the caller set the tolerance.
    footing_tol = tol if explicit else tol * (summed_count + 1)
    epsilon = FLOAT_EPSILON * max(1, abs(total), abs(parent[col]))
    if gap > footing_tol + epsilon:
        report["faults"].append(
            f"'{parent['line']}' {col} is {parent[col]:,.4g} but its lines roll up to {total:,.4g} (difference {parent[col] - total:,.4g})."
        )
    elif gap > tol + epsilon:
        report["warnings"].append(
            f"'{parent['line']}' {col} differs from its summed lines "
            f"by {parent[col] - total:,.4g}, within the rounding "
            f"tolerance {footing_tol:,.4g} for {summed_count} lines "
            "and their total; confirm the rounding."
        )


def _check_footing(rows, by_name, tolerance, report):
    if not any(r["parent"] for r in rows):
        report["warnings"].append(
            "No parent column: footing not checked. Add a parent column (and rollup + or - if needed) to check subtotals and totals."
        )
        return
    children = {}
    for r in rows:
        if not r["parent"]:
            continue
        if r["parent"].lower() not in by_name:
            report["faults"].append(
                f"Line '{r['line']}': parent '{r['parent']}' is not a line in the table. Correct the parent name or add that line."
            )
            continue
        children.setdefault(r["parent"].lower(), []).append(r)
    for pkey, kids in children.items():
        parent = by_name[pkey]
        if parent["type"] in UNSUMMED_TYPES:
            report["warnings"].append(
                f"Ratio line '{parent['line']}' has children; ratios are not footed."
            )
            continue
        for col in ("actual", "comparison"):
            if parent[col] is not None:
                _foot_column(parent, kids, col, tolerance, report)


def _check_formulas(rows, by_name, report):
    """Recompute ratio and per-unit lines that give a formula like 'Gross profit / Revenue'."""
    for r in rows:
        f = r.get("formula")
        if not f or "/" not in f:
            continue
        num_name, den_name = [x.strip().lower() for x in f.split("/", 1)]
        num, den = by_name.get(num_name), by_name.get(den_name)
        if not num or not den:
            report["warnings"].append(
                f"Line '{r['line']}': formula '{f}' names a line that isn't in the table; not recomputed."
            )
            continue
        scale = 100.0 if r["type"] == "ratio" else 1.0
        for col in ("actual", "comparison"):
            if num[col] is None or not den[col]:
                continue
            calc = num[col] / den[col] * scale
            stated = r[col]
            shown = 0.5 * 10 ** -r["decimals"] if r["decimals"] else 0.5
            if stated is not None and abs(calc - stated) > shown:
                report["faults"].append(
                    f"'{r['line']}' {col} is stated as {stated:,.4g} but {f} = {calc:,.4g}. Which is right?"
                )


def _pct_of(r):
    base = abs(r["comparison"]) if r["comparison"] else 0
    return base, (round(r["variance"] / base * 100, 1) if base else None)


def _mark_material(r, limits, warnings):
    materiality_pct, materiality_abs, headline = limits
    if r["variance"] is None:
        r["material"] = False
    elif r["type"] == "ratio":
        r["variance_pp"] = r["variance"]
        r["variance_bps"] = round(r["variance"] * 100, 1)
        r["variance_pct"] = None
        r["material"] = abs(r["variance_bps"]) >= RATIO_MATERIAL_BPS
    elif r["type"] == "per_unit":
        _, r["variance_pct"] = _pct_of(r)
        r["material"] = (
            r["variance_pct"] is not None and abs(r["variance_pct"]) >= materiality_pct
        )
    else:
        base, r["variance_pct"] = _pct_of(r)
        pct_hit = (
            r["variance_pct"] is not None and abs(r["variance_pct"]) >= materiality_pct
        )
        abs_hit = materiality_abs is not None and abs(r["variance"]) >= materiality_abs
        share_hit = (
            (not headline)
            or r["type"] == "metric"
            or abs(r["variance"]) >= SHARE_OF_HEADLINE * headline
        )
        r["material"] = bool(abs_hit or (pct_hit and share_hit))
        if base == 0 and r["variance"]:
            # A metric's units cannot be compared with the money headline.
            r["material"] = bool(abs_hit or share_hit)
            warnings.append(
                f"Line '{r['line']}': non-zero variance has no comparison "
                "base; materiality uses its size. Confirm the zero base."
            )


def _direction_and_materiality(rows, materiality_pct, materiality_abs, warnings):
    # Headline = the largest money line (revenue, profit or cost), so units like headcount don't set the scale.
    headline = max(
        (
            abs(r["comparison"])
            for r in rows
            if r["comparison"] is not None and r["type"] in MONEY_TYPES
        ),
        default=0.0,
    )
    for r in rows:
        r["direction"] = direction(r)
        if r["direction"] == "ask":
            warnings.append(
                f"Line '{r['line']}': is higher favorable or unfavorable? Set type or favorable_when."
            )
        _mark_material(r, (materiality_pct, materiality_abs, headline), warnings)


def check(
    text,
    unit="",
    materiality_pct=2.0,
    materiality_abs=None,
    rounding=None,
    costs_negative=False,
):
    """Check a variance table given as CSV or Markdown text; see references/script-interface.md."""
    header, raw = parse_table(text)
    cols = {k: find_col(header, k) for k in CHECK_COLUMNS}
    report = {"faults": [], "warnings": []}
    for need in REQUIRED_COLUMNS:
        if not cols[need]:
            report["faults"].append(
                f"Missing required column '{need}'. Columns seen: {header}"
            )
    if report["faults"]:
        return {"status": "FAIL", **report, "rows": []}

    rows = _read_rows(raw, cols, costs_negative, report)
    # Tolerance: half of the last digit shown in the money lines (0.05 for one decimal, 0.5 for whole numbers).
    money = [r["decimals"] for r in rows if r["type"] in MONEY_TYPES]
    tol = (
        rounding if rounding is not None else 0.5 * 10 ** -(max(money) if money else 0)
    )
    by_name = {r["line"].lower(): r for r in rows}

    _check_stated(rows, tol, report["faults"])
    _check_footing(rows, by_name, (tol, rounding is not None), report)
    _check_formulas(rows, by_name, report)
    _direction_and_materiality(
        rows, materiality_pct, materiality_abs, report["warnings"]
    )

    faults, warnings = report["faults"], report["warnings"]
    status = "FAIL" if faults else ("PASS with warnings" if warnings else "PASS")
    return {
        "status": status,
        "tolerance": tol,
        "unit": unit or "as stated",
        "faults": faults,
        "warnings": warnings,
        "rows": rows,
    }


def _short(value):
    """A float rounded to 12 significant digits, so 2.6999999999999957 prints as 2.7."""
    return float(f"{value:.12g}") if isinstance(value, float) else value


def summarize(report):
    """JSON text of a check() report with only the fields the workflow reads, one row per line."""
    keep = {
        k: _short(report[k])
        for k in ("status", "tolerance", "unit", "faults", "warnings")
        if k in report
    }
    rows = [
        json.dumps({k: _short(r.get(k)) for k in SUMMARY_FIELDS}, default=str)
        for r in report.get("rows", [])
    ]
    head = json.dumps(keep, indent=1, default=str)
    return head[:-2] + ',\n "rows": [\n  ' + ",\n  ".join(rows) + "\n ]\n}"


def fmt(n):
    return "" if n is None else f"{n:,.2f}"


def _print_rows(result, is_rvm):
    if is_rvm and "segments" in result:
        print(f"\n{'Segment':28}{'Volume':>14}{'Mix':>14}{'Rate':>14}{'Total':>14}")
        for s in result["segments"] + [{"segment": "TOTAL", **result["totals"]}]:
            print(
                f"{s['segment'][:27]:28}{fmt(s['volume']):>14}{fmt(s['mix']):>14}{fmt(s['rate']):>14}{fmt(s['total']):>14}"
            )
    elif "rows" in result:
        print(
            f"\n{'Line':30}{'Type':9}{'Actual':>13}{'Compare':>13}{'Variance':>13}{'%/bps':>10} Dir Material"
        )
        for r in result["rows"]:
            pct = (
                f"{r['variance_bps']}bps"
                if r.get("variance_bps") is not None
                else (
                    f"{r['variance_pct']}%" if r.get("variance_pct") is not None else ""
                )
            )
            print(
                f"{r['line'][:29]:30}{r['type']:9}{fmt(r['actual']):>13}{fmt(r['comparison']):>13}{fmt(r['variance']):>13}{pct:>10} {r['direction']:4}{'yes' if r['material'] else ''}"
            )


def main(argv=None):
    """Local testing entry point: python3 variance_check.py table.csv [--unit M] [--rvm] [--json]."""
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("file", help="CSV or Markdown table, or - for stdin")
    ap.add_argument(
        "--unit",
        default="",
        help="Unit the values are in: K, M or B (labels only; the tolerance comes from the digits shown)",
    )
    ap.add_argument(
        "--rounding",
        type=float,
        default=None,
        help="Explicit footing tolerance; overrides the tolerance inferred from the digits shown",
    )
    ap.add_argument("--materiality-pct", type=float, default=2.0)
    ap.add_argument("--materiality-abs", type=float, default=None)
    ap.add_argument(
        "--rvm",
        action="store_true",
        help="Rate / volume / mix decomposition instead of footing",
    )
    ap.add_argument(
        "--costs-negative",
        action="store_true",
        help="Cost lines are stored as negative numbers; flip them before checking",
    )
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    text = (
        sys.stdin.read()
        if a.file == "-"
        else Path(a.file).read_text(encoding="utf-8-sig")
    )
    result = (
        rvm(text)
        if a.rvm
        else check(
            text,
            a.unit,
            a.materiality_pct,
            a.materiality_abs,
            a.rounding,
            a.costs_negative,
        )
    )
    if a.json:
        print(json.dumps(result, indent=2, default=str))
        return 0 if not result["status"].startswith("FAIL") else 1
    print(f"STATUS: {result['status']}")
    for f in result.get("faults", []):
        print(f"  FAULT: {f}")
    for w in result.get("warnings", []):
        print(f"  WARN:  {w}")
    _print_rows(result, a.rvm)
    return 0 if not result["status"].startswith("FAIL") else 1


if __name__ == "__main__":
    sys.exit(main())
