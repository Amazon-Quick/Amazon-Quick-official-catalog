"""
description: Performance scorecard for the workbook scan and the findings that come from it.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl.utils import get_column_letter
from scan_findings import Findings, add_grouped, data_text
from scan_formats import plural
from scan_formula_text import EXT_RE, XL_PREFIX, func_calls, mask_strings, refs_in
from scan_limits import MAX_ROW
from scan_load import Workbook

CALC_MODES = ("auto", "autoNoTable", "manual")
IDENT = re.compile(r"[\w.\\]+")


def _identifiers(text: str) -> set[str]:
    """Every name-like token in formula text that isn't a function call (not followed by "(")."""
    return {
        m.group(0) for m in IDENT.finditer(text) if not text.startswith("(", m.end())
    }


def check_performance_findings(wb: Workbook, fs: Findings, perf):
    m = {x["key"]: x for x in perf["metrics"]}
    if m["calc_mode"]["value"].lower() == "manual":
        fs.add(
            "calc_manual",
            None,
            None,
            "Calculation is set to Manual - numbers shown may be out of date until someone recalculates.",
        )
    if m["iterative"]["value"] == "On":
        fs.add(
            "iterative_calc_on",
            None,
            None,
            "Iterative calculation is on - circular references calculate silently instead of warning.",
        )
    for i in perf["inflated"]:
        fs.add(
            "inflated_used_range",
            i["sheet"],
            None,
            f"The tab claims {i['claims']} but its data ends at {i['data_ends']}; the empty formatted area bloats the file.",
        )
    if m["cell_styles"]["rating"] in ("yellow", "red"):
        fs.add(
            "excess_cell_styles",
            None,
            None,
            f"The file stores {m['cell_styles']['value']:,} cell formats (usually from copying between workbooks).",
            severity="warning" if m["cell_styles"]["rating"] == "red" else None,
        )
    vol = defaultdict(list)
    for x in wb.formulas:
        up = XL_PREFIX.sub("", mask_strings(x.formula).upper())
        if re.search(r"(?<![\w.])(NOW|TODAY|RAND|RANDBETWEEN)\s*\(", up):
            vol[x.sheet].append(x)
    total = sum(len(v) for v in vol.values())
    if total >= PERF_LIMITS["volatile"][0]:
        for sheet, xs in vol.items():
            pts = [(x.r, x.c) for x in xs]
            r1, c1 = min(p[0] for p in pts), min(p[1] for p in pts)
            r2, c2 = max(p[0] for p in pts), max(p[1] for p in pts)
            fs.add(
                "volatile_load",
                sheet,
                f"{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{r2}",
                f"{len(xs)} formulas use TODAY/NOW/RAND and recalculate on every edit, along with everything that depends on them.",
            )
    wc, sp = defaultdict(dict), defaultdict(dict)
    for x in wb.formulas:
        calls = func_calls(x.formula)
        arrayish = not isinstance(x.raw, str) or any(
            n == "SUMPRODUCT" for n, *_ in calls
        )
        if arrayish and any(
            b[3] - b[1] + 1 >= MAX_ROW - 1 for _sh, b, *_ in refs_in(x.formula)
        ):
            wc[x.sheet][(x.r, x.c)] = 0
        for name, args, *_ in calls:
            if name == "SUMPRODUCT" and re.search(
                r"[<>=]", mask_strings(",".join(args))
            ):
                sp[x.sheet][(x.r, x.c)] = 0
    for sheet, p in wc.items():
        add_grouped(
            fs,
            "whole_column_array",
            sheet,
            p,
            lambda k, rng: (
                "Array math (SUMPRODUCT or an array formula) over whole columns - over a million rows each time it calculates."
            ),
        )
    for sheet, p in sp.items():
        add_grouped(
            fs,
            "sumproduct_conditional",
            sheet,
            p,
            lambda k, rng: (
                "SUMPRODUCT used as a conditional sum; SUMIFS is usually much faster."
            ),
        )
    # named ranges nothing uses
    try:
        names = list(wb.wf.defined_names.items())
    except AttributeError:
        names = [(d.name, d) for d in wb.wf.defined_names.definedName]
    text = " ".join(x.formula for x in wb.formulas).upper()
    for s in wb.sheets.values():
        for cf in s.ws.conditional_formatting:
            for rule in cf.rules:
                text += " " + " ".join(rule.formula or ()).upper()
        for dv in s.ws.data_validations.dataValidation:
            text += (
                " " + (dv.formula1 or "").upper() + " " + (dv.formula2 or "").upper()
            )
    text += " " + " ".join((d.attr_text or "") for _, d in names).upper()
    used = _identifiers(text)  # one pass over the text, not one regex search per name
    unused = [
        n
        for n, d in names
        if not n.startswith("_xlnm")
        and not (d.hidden)
        and "#REF!" not in (d.attr_text or "")
        and n.upper() not in used
    ]
    if unused:
        fs.add(
            "unused_named_range",
            None,
            None,
            f"{plural(len(unused), 'named range')} {'is not' if len(unused) == 1 else 'are not'} used by any formula, rule or dropdown: "
            + ", ".join(data_text(name) for name in unused[:8])
            + (" ..." if len(unused) > 8 else ""),
        )
        fs.items[-1]["_names"] = unused


# (green_max, yellow_max): above yellow_max is red. These are starting points chosen for
# slower machines, not published limits; adjust them as more models are tested.
PERF_LIMITS = {
    "file_mb": (5, 20),
    "tabs": (10, 25),
    "filled_cells": (50_000, 200_000),
    "formulas": (10_000, 50_000),
    "volatile": (50, 200),
    "array_formulas": (10, 50),
    "named_ranges": (50, 200),
    "pivots": (3, 8),
    "cell_styles": (
        1_000,
        4_000,
    ),  # Excel errors out near 64,000; slowdowns start in the thousands
    "cf_rules": (100, 1_000),
    "external_files": (0, 1),
}
VOLATILE_ALL = (
    "OFFSET",
    "INDIRECT",
    "NOW",
    "TODAY",
    "RAND",
    "RANDBETWEEN",
    "CELL",
    "INFO",
)


def rate(key, v):
    g, y = PERF_LIMITS[key]
    return "green" if v <= g else "yellow" if v <= y else "red"


def performance(wb: Workbook, path: Path, n_circular: int) -> dict:

    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        wbxml = z.read("xl/workbook.xml").decode("utf-8", "replace")
        styles = (
            z.read("xl/styles.xml").decode("utf-8", "replace")
            if "xl/styles.xml" in names
            else ""
        )
        conns = (
            z.read("xl/connections.xml").decode("utf-8", "replace")
            if "xl/connections.xml" in names
            else ""
        )
    calc = re.search(r"<calcPr\b[^>]*>", wbxml)
    calc_tag = calc.group(0) if calc else ""
    m = re.search(r'calcMode="([^"]+)"', calc_tag)
    calc_mode = m.group(1) if m else "auto"
    if calc_mode not in CALC_MODES:  # file text: keep only the values Excel writes
        calc_mode = "other"
    iterate = bool(re.search(r'iterate="(1|true)"', calc_tag))
    xfs = re.search(r"<cellXfs\b[^>]*>(.*?)</cellXfs>", styles, re.S)
    n_styles = len(re.findall(r"<xf\b", xfs.group(1))) if xfs else 0
    n_named_styles = len(re.findall(r"<cellStyle\b", styles))
    vol = Counter()
    for x in wb.formulas:
        up = mask_strings(x.formula).upper()
        for fn in VOLATILE_ALL:
            if re.search(rf"(?<![\w.]){fn}\s*\(", up):
                vol[fn] += 1
    n_vol = sum(
        1
        for x in wb.formulas
        if any(
            re.search(rf"(?<![\w.]){fn}\s*\(", mask_strings(x.formula).upper())
            for fn in VOLATILE_ALL
        )
    )
    n_array = sum(
        1
        for s in wb.sheets.values()
        for x in s.cells.values()
        if x.formula and not isinstance(x.raw, str)
    )
    try:
        n_names = len(list(wb.wf.defined_names.items()))
    except AttributeError:
        n_names = len(wb.wf.defined_names.definedName)
    n_cf = sum(
        len(cf.rules) for s in wb.sheets.values() for cf in s.ws.conditional_formatting
    )
    n_pivots = sum(
        1 for n in names if re.match(r"xl/pivotTables/pivotTable\d+\.xml$", n)
    )
    n_ext = sum(
        1 for n in names if re.match(r"xl/externalLinks/externalLink\d+\.xml$", n)
    )
    n_ext = max(
        n_ext,
        len({m for x in wb.formulas for m in EXT_RE.findall(mask_strings(x.formula))}),
    )
    n_conn = len(re.findall(r"<connection\b", conns))
    vba = "xl/vbaProject.bin" in names
    n_media = sum(1 for n in names if n.startswith("xl/media/"))
    size_mb = path.stat().st_size / 1_048_576
    inflated = []
    for s in wb.sheets.values():
        if not s.cells:
            continue
        real_r, real_c = (
            max(x.r for x in s.cells.values()),
            max(x.c for x in s.cells.values()),
        )
        dr, dc = s.ws.max_row or 0, s.ws.max_column or 0
        if dr * dc > 4 * real_r * real_c and dr * dc > 100_000:
            inflated.append(
                {
                    "sheet": s.name,
                    "claims": s.ws.dimensions,
                    "data_ends": f"{get_column_letter(real_c)}{real_r}",
                }
            )
    rows = [
        (
            "calc_mode",
            "Calculation mode",
            calc_mode.capitalize(),
            "red" if calc_mode == "manual" else "green",
            "Numbers may be stale until someone presses F9"
            if calc_mode == "manual"
            else "",
        ),
        (
            "iterative",
            "Iterative calculation",
            "On" if iterate else "Off",
            "yellow" if iterate else "green",
            "Hides accidental circular references" if iterate else "",
        ),
        (
            "circular",
            "Circular references",
            n_circular,
            "red" if n_circular else "green",
            "",
        ),
        (
            "file_mb",
            "File size",
            f"{size_mb:.1f} MB"
            if size_mb >= 1
            else f"{path.stat().st_size / 1024:.0f} KB",
            rate("file_mb", size_mb),
            "",
        ),
        ("tabs", "Tabs", len(wb.sheets), rate("tabs", len(wb.sheets)), ""),
        (
            "filled_cells",
            "Filled cells",
            sum(len(s.cells) for s in wb.sheets.values()),
            None,
            "",
        ),
        (
            "formulas",
            "Formulas",
            len(wb.formulas),
            rate("formulas", len(wb.formulas)),
            "",
        ),
        (
            "volatile",
            "Volatile formulas",
            n_vol,
            rate("volatile", n_vol),
            ", ".join(f"{k} {v}" for k, v in vol.most_common()) if vol else "",
        ),
        (
            "array_formulas",
            "Array formulas",
            n_array,
            rate("array_formulas", n_array),
            "",
        ),
        (
            "used_range",
            "Inflated used range",
            len(inflated),
            "red" if inflated else "green",
            "; ".join(
                f"{data_text(i['sheet'])} claims {i['claims']}, data ends {i['data_ends']}"
                for i in inflated
            ),
        ),
        (
            "cell_styles",
            "Cell formats stored",
            n_styles,
            rate("cell_styles", n_styles),
            f"{n_named_styles} named styles" if n_named_styles > 50 else "",
        ),
        ("cf_rules", "Highlight rules", n_cf, rate("cf_rules", n_cf), ""),
        ("named_ranges", "Named ranges", n_names, rate("named_ranges", n_names), ""),
        ("pivots", "Pivot tables", n_pivots, rate("pivots", n_pivots), ""),
        (
            "external_files",
            "Links to other files",
            n_ext,
            rate("external_files", n_ext),
            "",
        ),
        (
            "connections",
            "Data connections",
            n_conn,
            "yellow" if n_conn else "green",
            "Power Query / ODBC" if n_conn else "",
        ),
        (
            "vba",
            "Macros (VBA)",
            "Yes" if vba else "None",
            "yellow" if vba else "green",
            "Not checked by this scan" if vba else "",
        ),
        ("media", "Images / media", n_media, "green" if n_media < 20 else "yellow", ""),
    ]
    rows[5] = rows[5][:3] + (rate("filled_cells", rows[5][2]),) + rows[5][4:]
    metrics = [
        {"key": k, "label": litem, "value": v, "rating": r, "note": n}
        for k, litem, v, r, n in rows
    ]
    reds = sum(1 for m in metrics if m["rating"] == "red")
    yellows = sum(1 for m in metrics if m["rating"] == "yellow")
    verdict = (
        "restructure"
        if reds >= 2 or yellows >= 3
        else "fixes"
        if reds or yellows
        else "healthy"
    )
    return {
        "metrics": metrics,
        "verdict": verdict,
        "reds": reds,
        "yellows": yellows,
        "inflated": inflated,
    }
