"""
description: Cell formatting, conditional formatting and dropdown checks: numbers stored as text, units, decimals, widths and validation lists.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from openpyxl.utils import column_index_from_string, get_column_letter
from scan_findings import Findings, add_grouped, data_text
from scan_formats import (
    DATE_TEXT,
    display_text,
    fmt_decimals,
    fmt_scale,
    fmt_section,
    is_num,
    numeric_text,
    plural,
)
from scan_formula_text import parse_box, refs_in
from scan_labels import label_for
from scan_limits import (
    COL_CAP,
    CONVENTION_SHARE,
    DV_CELL_WORK_CAP,
    DV_RULE_CAP,
    FRAGMENT_MIN,
    FREEZE_MIN_ROWS,
    MAX_COL,
    MAX_ROW,
    MIN_ROLE_CELLS,
    PCT_WORDS,
    ROW_CAP,
)
from scan_load import Workbook


def check_text_numbers_uncached(wb, fs):
    """Numbers typed as text, found from typed values when the file has no saved formula results."""
    for s in wb.sheets.values():
        if s.hidden:
            continue
        pts = {}
        groups = defaultdict(list)
        for x in s.cells.values():
            if x.r > s.header_row and not x.formula:
                groups[("r", x.r)].append(x)
                groups[("c", x.c)].append(x)
        for xs in groups.values():
            nums = [x for x in xs if is_num(x.raw) and not x.is_date]
            texts = [x for x in xs if isinstance(x.raw, str) and numeric_text(x.raw)]
            if texts and len(nums) + len(texts) >= 3 and len(nums) >= len(texts):
                for x in texts:
                    pts[(x.r, x.c)] = x.raw.strip()
        add_grouped(
            fs,
            "number_as_text",
            s.name,
            pts,
            lambda k, rng: (
                f"{data_text(k)} is stored as text; SUM and other math skip it."
            ),
        )


def check_cell_formats(wb: Workbook, fs: Findings, cached_ok: bool):
    for s in wb.sheets.values():
        if s.hidden:
            continue
        cols = defaultdict(list)
        for x in s.cells.values():
            if x.r > s.header_row:
                cols[x.c].append(x)
        text_num, text_date, pct, dec = {}, {}, {}, {}
        for _c, xs in cols.items():
            vals = [x for x in xs if x.cached is not None]
            if len(vals) < MIN_ROLE_CELLS:
                continue
            nums = [x for x in vals if is_num(x.cached) and not x.is_date]
            dates = [x for x in vals if x.is_date]
            texts = [x for x in vals if isinstance(x.cached, str) and not x.formula]
            if len(nums) >= CONVENTION_SHARE * len(vals):
                for x in texts:
                    if numeric_text(x.cached):
                        text_num[(x.r, x.c)] = x.cached.strip()
            date_texts = [x for x in texts if DATE_TEXT.match(x.cached)]
            if dates and len(dates) + len(date_texts) >= CONVENTION_SHARE * len(vals):
                for x in texts:
                    if DATE_TEXT.match(x.cached):
                        text_date[(x.r, x.c)] = x.cached.strip()
            if s.is_data and len(nums) >= 10:
                d = Counter(
                    fmt_decimals(x.fmt) for x in nums if fmt_decimals(x.fmt) is not None
                )
                if d:
                    top, n = d.most_common(1)[0]
                    if n >= CONVENTION_SHARE * sum(d.values()):
                        for x in nums:
                            k = fmt_decimals(x.fmt)
                            if k is not None and k != top:
                                dec[(x.r, x.c)] = (k, top)
        # rows too: a line of periods where a few months were loaded as text
        for r, rxs in s.rows.items():
            if r <= s.header_row:
                continue
            typed = [
                x
                for x in rxs
                if not x.formula and x.raw is not None and not isinstance(x.raw, bool)
            ]
            rnums = [x for x in typed if is_num(x.raw) and not x.is_date]
            rtexts = [
                x for x in typed if isinstance(x.raw, str) and numeric_text(x.raw)
            ]
            if rtexts and len(rnums) + len(rtexts) >= 3 and len(rnums) >= len(rtexts):
                for x in rtexts:
                    text_num[(x.r, x.c)] = x.raw.strip()
        for x in s.cells.values():
            if x.r <= s.header_row or not is_num(x.cached) or x.is_date:
                continue
            if (
                fmt_section(x.fmt).strip().lower() == "general"
                and 0 < abs(x.cached) <= 1
                and x.cached != int(x.cached)
            ):
                if PCT_WORDS.search(label_for(s, x)):
                    pct[(x.r, x.c)] = 0
        if not s.is_data:
            units_flag = set()
            sc = Counter(
                fmt_scale(x.fmt)
                for x in s.cells.values()
                if is_num(x.cached)
                and not x.is_date
                and fmt_decimals(x.fmt) is not None
                and ("$" in x.fmt or fmt_scale(x.fmt) != "units")
            )
            if sc and sum(sc.values()) >= MIN_ROLE_CELLS:
                top, n = sc.most_common(1)[0]
                if n >= CONVENTION_SHARE * sum(sc.values()):
                    pts = {}
                    for x in s.cells.values():
                        if (
                            is_num(x.cached)
                            and not x.is_date
                            and fmt_decimals(x.fmt) is not None
                            and ("$" in x.fmt or fmt_scale(x.fmt) != "units")
                            and fmt_scale(x.fmt) != top
                        ):
                            pts[(x.r, x.c)] = (fmt_scale(x.fmt), top)
                            units_flag.add((x.r, x.c))
                    add_grouped(
                        fs,
                        "mixed_units",
                        s.name,
                        pts,
                        lambda k, rng: (
                            f"Shown in {k[0]}; the rest of the tab is in {k[1]}."
                        ),
                    )
            for r, xs in s.rows.items():
                if r <= s.header_row:
                    continue
                nums = [
                    x
                    for x in xs
                    if is_num(x.cached)
                    and not x.is_date
                    and fmt_decimals(x.fmt) is not None
                ]
                if len(nums) < 3:
                    continue
                d = Counter(fmt_decimals(x.fmt) for x in nums)
                top, n = d.most_common(1)[0]
                if n >= CONVENTION_SHARE * len(nums):
                    for x in nums:
                        if fmt_decimals(x.fmt) != top and (x.r, x.c) not in units_flag:
                            dec[(x.r, x.c)] = (fmt_decimals(x.fmt), top)
        add_grouped(
            fs,
            "number_as_text",
            s.name,
            text_num,
            lambda k, rng: (
                f"{data_text(k)} is stored as text; SUM and other math skip it."
            ),
        )
        add_grouped(
            fs,
            "date_as_text",
            s.name,
            text_date,
            lambda k, rng: f"{data_text(k)} is stored as text, not a date.",
        )
        add_grouped(
            fs,
            "percent_general_format",
            s.name,
            pct,
            lambda k, rng, s=s: (
                lambda cell: (
                    f"Rate shown as a decimal ({cell.cached:g}) in General format, not as a percentage."
                    + (" Same in the rest of the range." if ":" in rng else "")
                )
            )(s.cells[parse_box(rng)[1], parse_box(rng)[0]]),
        )
        add_grouped(
            fs,
            "mixed_decimals",
            s.name,
            dec,
            lambda k, rng: (
                f"Shows {plural(k[0], 'decimal place')}; its neighbors show {k[1]}."
            ),
        )
        # merged cells holding numbers or formulas
        for mr in s.ws.merged_cells.ranges:
            a = s.cells.get((mr.min_row, mr.min_col))
            if a and (a.formula or is_num(a.raw)):
                fs.add(
                    "merged_cells_in_calc",
                    s.name,
                    mr.coord,
                    "A number/formula cell is merged across cells.",
                )
        # freeze panes on long tabs
        if s.rows and len(s.rows) > FREEZE_MIN_ROWS and not s.ws.freeze_panes:
            fs.add(
                "no_freeze_panes",
                s.name,
                None,
                f"{len(s.rows)} rows and nothing frozen; the header row scrolls out of view.",
            )
        # columns too narrow for their numbers
        default_w = (
            s.ws.sheet_format.defaultColWidth
            or (s.ws.sheet_format.baseColWidth or 8) + 0.43
        )
        widths = {}
        for key, d in s.ws.column_dimensions.items():
            if d.width and d.customWidth:
                lo = max(1, d.min or column_index_from_string(key))
                hi = min(COL_CAP, d.max or column_index_from_string(key))
                for c in range(lo, hi + 1):
                    widths[c] = d.width
        narrow = {}
        for x in s.cells.values():
            if not is_num(x.cached) or x.is_date:
                continue
            dtxt = display_text(float(x.cached), x.fmt)
            if dtxt and dtxt[1] > widths.get(x.c, default_w):
                narrow[(x.r, x.c)] = 0
        add_grouped(
            fs,
            "column_too_narrow",
            s.name,
            narrow,
            lambda k, rng: "Column is too narrow for the number; Excel shows ####.",
        )


def rule_words(typ, op, formulas):
    t = {
        "cellIs": "cell value",
        "expression": "formula",
        "colorScale": "color scale",
        "dataBar": "data bar",
        "iconSet": "icon set",
        "containsText": "contains text",
        "duplicateValues": "duplicates",
        "top10": "top/bottom",
    }.get(typ, typ)
    o = re.sub(r"(?<!^)([A-Z])", r" \1", op or "").lower()
    return " ".join(p for p in (t, o, ", ".join(formulas)[:30]) if p)


def check_cf_dv(wb: Workbook, fs: Findings):
    dv_rules = dv_work = 0
    dv_capped = False
    allowed_cache = {}

    def cells_in_box(sheet, box):
        nonlocal dv_work, dv_capped
        c1, r1, c2, r2 = box
        c2, r2 = min(c2, COL_CAP), min(r2, ROW_CAP)
        area = max(0, c2 - c1 + 1) * max(0, r2 - r1 + 1)
        work = min(area, len(sheet.cells))
        if dv_work + work > DV_CELL_WORK_CAP:
            dv_capped = True
            return []
        dv_work += work
        if area <= len(sheet.cells):
            return [
                x
                for r in range(r1, r2 + 1)
                for c in range(c1, c2 + 1)
                if (x := sheet.cells.get((r, c))) is not None
            ]
        return [
            x for (r, c), x in sheet.cells.items() if c1 <= c <= c2 and r1 <= r <= r2
        ]

    for s in wb.sheets.values():
        sig = defaultdict(list)
        for cf in s.ws.conditional_formatting:
            rng = str(cf.sqref)
            for rule in cf.rules:
                formulas = tuple(rule.formula or ())
                if any("#REF!" in f for f in formulas):
                    fs.add(
                        "cf_broken_ref",
                        s.name,
                        rng.split()[0] if len(rng.split()) == 1 else rng.split()[0],
                        "A conditional-formatting rule refers to #REF! (a deleted cell).",
                    )
                sig[(rule.type, rule.operator, formulas)].append(rng)
            for part in rng.split():
                try:
                    c1, r1, c2, r2 = parse_box(part)
                except ValueError:
                    continue
                if r2 - r1 + 1 >= MAX_ROW - 1 or c2 - c1 + 1 >= MAX_COL - 1:
                    letter = get_column_letter(c1)
                    fs.add(
                        "cf_whole_column",
                        s.name,
                        f"{letter}:{get_column_letter(c2)}"
                        if r2 - r1 + 1 >= MAX_ROW - 1
                        else part,
                        f"A conditional-formatting rule covers the entire {'column' if r2 - r1 + 1 >= MAX_ROW - 1 else 'row'} ({part}).",
                    )
        for (typ, op, formulas), ranges in sig.items():
            if len(ranges) >= FRAGMENT_MIN:
                boxes = [parse_box(p) for r in ranges for p in r.split()]
                c1, r1 = min(b[0] for b in boxes), min(b[1] for b in boxes)
                c2, r2 = max(b[2] for b in boxes), max(b[3] for b in boxes)
                fs.add(
                    "cf_fragmented",
                    s.name,
                    f"{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{r2}",
                    f"The same highlight rule ({data_text(rule_words(typ, op, formulas))}) exists as {len(ranges)} separate copies.",
                )
        for dv in s.ws.data_validations.dataValidation:
            if dv_capped or dv_rules >= DV_RULE_CAP:
                dv_capped = True
                break
            dv_rules += 1
            src = dv.formula1 or ""
            rng = str(dv.sqref)
            if "#REF!" in src:
                fs.add(
                    "dv_broken_source",
                    s.name,
                    rng,
                    "Dropdown list points at #REF! (a deleted range).",
                )
                continue
            if dv.type != "list":
                continue
            allowed = None
            if src.startswith('"'):
                allowed = {a.strip().lower() for a in src.strip('"').split(",")}
            else:
                refs = list(refs_in("=" + src.lstrip("=")))
                if len(refs) == 1:
                    sh, box, *_ = refs[0]
                    ts = wb.sheets.get(wb.resolve(sh) if sh else s.name)
                    if ts:
                        key = (ts.name, tuple(box))
                        if key not in allowed_cache:
                            allowed_cache[key] = {
                                str(x.cached).strip().lower()
                                for x in cells_in_box(ts, box)
                                if x.cached is not None
                            }
                        allowed = allowed_cache[key]
            if dv_capped:
                break
            if not allowed:
                continue
            bad = {}
            for part in rng.split():
                for x in cells_in_box(s, parse_box(part)):
                    if (
                        x.cached is not None
                        and str(x.cached).strip().lower() not in allowed
                    ):
                        bad[(x.r, x.c)] = str(x.cached)
                if dv_capped:
                    break
            for (r, c), v in bad.items():
                fs.add(
                    "dv_violation",
                    s.name,
                    f"{get_column_letter(c)}{r}",
                    f"{data_text(v)} is not one of the dropdown choices.",
                )
    if dv_capped:
        wb.notes.append(
            {
                "note": "data_validation_scan_capped",
                "detail": (
                    "Dropdown checks are incomplete: the scan reached its limit "
                    f"of {DV_RULE_CAP:,} rules or {DV_CELL_WORK_CAP:,} cell visits. "
                    "Unscanned rules and cells have not been verified."
                ),
            }
        )
