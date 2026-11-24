"""
description: Check the written copy: confirm each edit landed, then compare a scan of the copy with the original's, holding back value checks on cells that read new formulas.
last_updated: 2026-11-24
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import scan_workbook as S


def verify(plan, results, out: Path, wf=None):
    """Re-open the copy (or use the already opened `wf`) and confirm each applied edit landed."""
    wf = wf or openpyxl.load_workbook(out, data_only=False)
    problems = []
    for ch, status, _ in results:
        if status != "applied":
            continue
        for e in ch["edits"]:
            if e["op"] not in ("cell", "new_cell"):
                continue
            got = wf[e["sheet"]][e["cell"]].value
            if "formula" in e and S.formula_text(got) != e["formula"]:
                problems.append(
                    f"#{ch['n']} {e['sheet']}!{e['cell']}: expected {e['formula']}, found {got!r}"
                )
            if (
                "value" in e
                and got != e["value"]
                and not (isinstance(got, (int, float)) and abs(got - e["value"]) < 1e-9)
            ):
                if not (hasattr(got, "year") and isinstance(e["value"], int)):
                    problems.append(
                        f"#{ch['n']} {e['sheet']}!{e['cell']}: expected {e['value']!r}, found {got!r}"
                    )
    return problems


def overlap(a, b):
    if not a.get("cell") or not b.get("cell"):
        return a.get("sheet") == b.get("sheet")
    x, y = S.parse_box(a["cell"]), S.parse_box(b["cell"])
    return a.get("sheet") == b.get("sheet") and not (
        x[2] < y[0] or y[2] < x[0] or x[3] < y[1] or y[3] < x[1]
    )


# Checks that compare saved results. A cell that just received a formula has no saved result
# until Excel recalculates, so these checks can't be trusted on cells that read it.
VALUE_CHECKS = frozenset(
    {
        "error_value",
        "period_total_mismatch",
        "crossfoot_mismatch",
        "tie_out_mismatch",
        "same_metric_differs",
        "outlier_value",
        "unusual_movement",
        "sign_flip",
        "unexpected_zero",
        "margin_out_of_range",
        "mixed_decimals",
        "percent_general_format",
        "column_too_narrow",
    }
)


REFS_CELL_CAP = 2000  # cells of one finding whose formulas are read for references


def new_formula_cells(results):
    """{(sheet, col, row)} of every cell an applied change gave a new formula."""
    return {
        (e["sheet"], *S.parse_box(e["cell"])[:2])
        for ch, status, _ in results
        if status == "applied"
        for e in ch["edits"]
        if e["op"] in ("cell", "new_cell") and "formula" in e
    }


def reads_new_formula(finding, cells, wf):
    """True when a value check's finding shares a row or column with a cell that just received
    a formula, or one of its formulas refers to such a cell."""
    if finding["check"] not in VALUE_CHECKS or not finding.get("cell"):
        return False
    sheet = finding["sheet"]
    c1, r1, c2, r2 = S.parse_box(finding["cell"])
    mine = [(c, r) for sh, c, r in cells if sh == sheet]
    if any(r1 <= r <= r2 or c1 <= c <= c2 for c, r in mine):
        return True
    if not cells or sheet not in wf.sheetnames:
        return False
    if (c2 - c1 + 1) * (r2 - r1 + 1) > REFS_CELL_CAP:
        return False
    ws = wf[sheet]
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            text = S.formula_text(ws.cell(r, c).value)
            for sh, box, *_ in S.refs_in(text or ""):
                tab = (sh or sheet).lower()
                if any(
                    tab == s.lower()
                    and box[0] <= cc <= box[2]
                    and box[1] <= rr <= box[3]
                    for s, cc, rr in cells
                ):
                    return True
    return False


def recheck(before, after, results, wf):
    """Compare the scan of the copy with the scan of the original."""
    by_id = {f["id"]: f for f in before["findings"]}
    fixed_ids = [i for c, st, _ in results if st == "applied" for i in c["finding_ids"]]
    still = [
        i
        for i in fixed_ids
        if i in by_id
        and any(
            g["check"] == by_id[i]["check"] and overlap(g, by_id[i])
            for g in after["findings"]
        )
    ]
    new = [
        g
        for g in after["findings"]
        if not any(
            f["check"] == g["check"] and overlap(f, g) for f in before["findings"]
        )
    ]
    cells = new_formula_cells(results)
    waiting = [g for g in new if reads_new_formula(g, cells, wf)]
    new = [g for g in new if g not in waiting]

    def brief(g):
        return {k: g[k] for k in ("check", "severity", "sheet", "cell", "description")}

    return {
        "cleared": len(fixed_ids) - len(still),
        "targeted": len(fixed_ids),
        "still_present": still,
        "new": [brief(g) for g in new],
        "not_rechecked": [brief(g) for g in waiting],
        "skipped": sum(1 for _, st, _ in results if st != "applied"),
    }


def print_recheck(rc):
    print(
        f"Re-check of the copy: {rc['cleared']} of {rc['targeted']} targeted findings cleared"
        + (
            f"; still present: {', '.join(rc['still_present'])}"
            if rc["still_present"]
            else ""
        )
        + f"; {len(rc['new'])} new; {S.plural(rc['skipped'], 'change')} skipped."
    )
    for g in rc["new"][:10]:
        print(
            f"  NEW {g['severity']} {g['check']} {S.data_text(g['sheet'])}!{g['cell']} - {g['description'][:90]}"
        )
    if rc["not_rechecked"]:
        print(
            f"Not re-checked until Excel recalculates: {len(rc['not_rechecked'])} value check(s) "
            "on cells that read new formulas."
        )
        for g in rc["not_rechecked"][:10]:
            print(f"  WAITING {g['check']} {S.data_text(g['sheet'])}!{g['cell']}")
