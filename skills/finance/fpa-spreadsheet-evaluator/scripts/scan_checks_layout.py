"""
description: Layout checks: hidden tabs, rows and columns inside data, Excel Tables and pivot tables.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re
from collections import defaultdict

from openpyxl.utils import column_index_from_string, get_column_letter
from scan_findings import Findings, add_grouped, data_text, rectangles
from scan_formats import plural
from scan_formula_text import parse_box, refs_in
from scan_limits import COL_CAP, MAX_ROW, TABLE_COVER_SHARE
from scan_load import Workbook


def check_hidden(wb: Workbook, fs: Findings):
    for s in wb.sheets.values():
        if s.hidden:
            users = sorted({x.sheet for x in wb.formulas if s.name in (x.links or ())})
            fs.add(
                "hidden_sheet",
                s.name,
                None,
                f"Tab is {s.ws.sheet_state}"
                + (f" and feeds {data_text(', '.join(users))}." if users else "."),
                severity=None if users else "info",
            )
            continue
        if not s.rows:
            continue
        lo, hi = min(s.rows), max(s.rows)
        hidden = [r for r, d in s.ws.row_dimensions.items() if d.hidden and lo < r < hi]
        if hidden:
            maxc = max(x.c for x in s.cells.values())
            minc = min(x.c for x in s.cells.values())
            {(r, c): 0 for r in hidden for c in (minc, maxc)}
            for rng in rectangles([(r, minc) for r in hidden]):
                a, _, b = rng.partition(":")
                b = b or a
                r1, r2 = int(re.sub(r"\D", "", a)), int(re.sub(r"\D", "", b))
                fs.add(
                    "hidden_rows_in_block",
                    s.name,
                    f"{get_column_letter(minc)}{r1}:{get_column_letter(maxc)}{r2}",
                    f"Rows {r1}-{r2} are hidden in the middle of the data."
                    if r1 != r2
                    else f"Row {r1} is hidden in the middle of the data.",
                )
        hcols = []
        for key, d in s.ws.column_dimensions.items():
            if d.hidden:
                lo = max(1, d.min or column_index_from_string(key))
                hi = min(COL_CAP, d.max or column_index_from_string(key))
                hcols.extend(range(lo, hi + 1))
        cols_used = {x.c for x in s.cells.values()}
        hcols = [c for c in hcols if min(cols_used) < c < max(cols_used)]
        if hcols:
            fs.add(
                "hidden_rows_in_block",
                s.name,
                f"{get_column_letter(min(hcols))}:{get_column_letter(max(hcols))}",
                f"{plural(len(hcols), 'column')} hidden inside the used area.",
            )


def check_tables(wb: Workbook, fs: Findings):
    tables = []
    for s in wb.sheets.values():
        for name, t in s.ws.tables.items():
            ref = t.ref if hasattr(t, "ref") else t
            c1, r1, c2, r2 = parse_box(ref)
            tables.append((s, name, (c1, r1, c2, r2)))
            r = r2 + 1
            while sum(
                1 for c in range(c1, c2 + 1) if s.cells.get((r, c)) is not None
            ) * 2 >= (c2 - c1 + 1):
                r += 1
            if r > r2 + 1:
                fs.add(
                    "data_past_table_edge",
                    s.name,
                    f"{get_column_letter(c1)}{r2 + 1}:{get_column_letter(c2)}{r - 1}",
                    f"{plural(r - r2 - 1, 'row')} of data sit directly below table {data_text(name)} (ends row {r2}); table formulas and pivots miss them.",
                )
            for c in range(c1, c2 + 1):
                h = s.cells.get((r1, c))
                if h is None or (
                    isinstance(h.raw, str) and re.fullmatch(r"\s*Column\d+\s*", h.raw)
                ):
                    fs.add(
                        "generic_table_header",
                        s.name,
                        f"{get_column_letter(c)}{r1}",
                        f"Table {data_text(name)} column is named {data_text(h.raw if h else '')}.",
                    )
    if not tables:
        return
    pts = defaultdict(dict)
    for x in wb.formulas:
        for sh, box, *_ in refs_in(x.formula):
            tgt = wb.resolve(sh) if sh else x.sheet
            for s, name, tb in tables:
                if s.name != tgt or box[1] == box[3] and box[0] == box[2]:
                    continue
                inside = (
                    tb[0] <= box[0]
                    and box[2] <= tb[2]
                    and box[1] >= tb[1]
                    and box[3] <= max(tb[3], box[3])
                )
                covered = max(0, min(box[3], tb[3]) - max(box[1], tb[1] + 1) + 1)
                if (
                    inside
                    and covered >= TABLE_COVER_SHARE * (tb[3] - tb[1])
                    and box[3] < MAX_ROW
                ):
                    pts[x.sheet][(x.r, x.c)] = name
    for sheet, p in pts.items():
        add_grouped(
            fs,
            "fixed_range_over_table",
            sheet,
            p,
            lambda k, rng: (
                f"Uses a fixed cell range over table {data_text(k)} instead of the table's column names; it won't grow with the data."
            ),
        )


def check_pivots(wb: Workbook, fs: Findings):
    tables = {}
    for s in wb.sheets.values():
        for name, t in s.ws.tables.items():
            tables[name.lower()] = (s, parse_box(t.ref if hasattr(t, "ref") else t))
    boxes = []
    for s in wb.sheets.values():
        # Private openpyxl 3.1 attribute with no public equivalent; guarded the same way.
        for p in getattr(s.ws, "_pivots", []) or []:
            try:
                loc = parse_box(p.location.ref)
                boxes.append((s.name, loc, p.name))
                cache = p.cache
                src = (
                    getattr(cache.cacheSource, "worksheetSource", None)
                    if cache and cache.cacheSource
                    else None
                )
                records = getattr(cache, "recordCount", None)
                if src is None:
                    continue
                if src.name:
                    t = tables.get(src.name.lower())
                    if not t:
                        if src.name not in getattr(wb.wf, "defined_names", {}):
                            fs.add(
                                "pivot_missing_source",
                                s.name,
                                None,
                                f"Pivot {data_text(p.name)} uses {data_text(src.name)}, which no longer exists.",
                            )
                        continue
                    rows = t[1][3] - t[1][1]
                    if records is not None and rows > records:
                        fs.add(
                            "pivot_stale_cache",
                            s.name,
                            None,
                            f"Pivot {data_text(p.name)} was last refreshed with {records} rows; table {data_text(src.name)} now has {rows}.",
                        )
                    continue
                tgt = wb.resolve(src.sheet) if src.sheet else None
                if not tgt:
                    fs.add(
                        "pivot_missing_source",
                        s.name,
                        None,
                        f"Pivot {data_text(p.name)} source tab {data_text(src.sheet)} doesn't exist.",
                    )
                    continue
                c1, r1, c2, r2 = parse_box(src.ref)
                ts = wb.sheets[tgt]
                fs.add(
                    "pivot_fixed_range",
                    s.name,
                    None,
                    f"Pivot {data_text(p.name)} is built on a typed range ({data_text(tgt)}!{data_text(src.ref)}), not a Table.",
                )
                r = r2 + 1
                while sum(
                    1 for c in range(c1, c2 + 1) if ts.cells.get((r, c)) is not None
                ) * 2 >= (c2 - c1 + 1):
                    r += 1
                if r > r2 + 1:
                    fs.add(
                        "pivot_source_short",
                        s.name,
                        None,
                        f"Pivot {data_text(p.name)} reads {data_text(tgt)}!{data_text(src.ref)}, but the data continues {plural(r - r2 - 1, 'more row')} to row {r - 1}.",
                    )
                if records is not None and (r2 - r1) > records:
                    fs.add(
                        "pivot_stale_cache",
                        s.name,
                        None,
                        f"Pivot {data_text(p.name)} was last refreshed with {records} rows; its source now has {r2 - r1}.",
                    )
            except Exception as exc:  # noqa: BLE001 - pivots vary; report, don't crash the scan
                wb.notes.append(
                    {
                        "note": "pivot_unreadable",
                        "detail": f"{data_text(s.name)}: {data_text(exc, 80)}",
                    }
                )
    if not boxes:
        return
    pts = defaultdict(dict)
    for x in wb.formulas:
        if "GETPIVOTDATA" in x.formula.upper():
            continue
        for sh, box, *_ in refs_in(x.formula):
            tgt = wb.resolve(sh) if sh else x.sheet
            for psheet, loc, pname in boxes:
                if psheet == tgt and not (
                    box[2] < loc[0]
                    or loc[2] < box[0]
                    or box[3] < loc[1]
                    or loc[3] < box[1]
                ):
                    pts[x.sheet][(x.r, x.c)] = pname
    for sheet, p in pts.items():
        add_grouped(
            fs,
            "formula_reads_pivot_by_position",
            sheet,
            p,
            lambda k, rng: (
                f"Reads a cell inside pivot {data_text(k)} by position; the number changes if the pivot reshapes."
            ),
        )
