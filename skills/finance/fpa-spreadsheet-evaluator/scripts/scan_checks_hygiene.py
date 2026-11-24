"""
description: Data hygiene checks: blank rows and cells inside data, and lookup keys with stray spaces.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re
from collections import defaultdict

from openpyxl.utils import get_column_letter
from scan_findings import Findings, add_grouped, data_text, rectangles
from scan_formats import is_num, plural
from scan_formula_text import func_calls, refs_in
from scan_limits import ROW_CAP
from scan_load import Workbook


def check_data_hygiene(wb: Workbook, fs: Findings):
    for s in wb.sheets.values():
        if s.hidden or not s.rows:
            continue
        lo, hi = s.header_row + 1, max(s.rows)
        if s.is_data:
            blank = [r for r in range(lo, hi) if r not in s.rows]
            maxc = max(x.c for x in s.cells.values())
            for rng in rectangles([(r, 1) for r in blank]):
                a, _, b = rng.partition(":")
                r1, r2 = int(re.sub(r"\D", "", a)), int(re.sub(r"\D", "", b or a))
                fs.add(
                    "blank_rows_in_data",
                    s.name,
                    f"A{r1}:{get_column_letter(maxc)}{r2}",
                    f"Row{'s' if r2 > r1 else ''} {r1}{'-' + str(r2) if r2 > r1 else ''} {'are' if r2 > r1 else 'is'} blank in the middle of the data.",
                )
        # empty cells inside a column that is otherwise full of numbers
        cols = defaultdict(dict)
        for x in s.cells.values():
            if x.r > s.header_row:
                cols[x.c][x.r] = x
        gaps = {}
        for c, cells in cols.items():
            nums = [r for r, x in cells.items() if is_num(x.cached) and not x.is_date]
            if len(nums) < 10 or c == 1:
                continue
            r1, r2 = min(nums), max(nums)
            inside = r2 - r1 + 1
            if len(nums) < 0.9 * inside:
                continue
            for r in range(r1 + 1, r2):
                if r in cells or r not in s.rows:
                    continue  # filled, or a fully blank row (reported separately)
                others = sum(
                    1
                    for x in s.rows[r]
                    if is_num(x.cached) or isinstance(x.cached, str)
                )
                if others >= 2:
                    gaps[(r, c)] = 0
        add_grouped(
            fs,
            "empty_cell_gap",
            s.name,
            gaps,
            lambda k, rng: (
                "Blank cell inside a column that is otherwise filled - possibly missing data."
            ),
        )
    # lookup keys and criteria ranges with stray spaces
    keyed = defaultdict(set)
    for x in wb.formulas:
        for name, args, *_ in func_calls(x.formula):
            idx = []
            if name in ("VLOOKUP", "HLOOKUP") and len(args) >= 2:
                idx = [(1, "first")]
            elif name in ("MATCH", "XMATCH") and len(args) >= 2:
                idx = [(1, "all")]
            elif name == "XLOOKUP" and len(args) >= 2:
                idx = [(1, "all")]
            elif name in ("SUMIFS", "AVERAGEIFS", "MAXIFS", "MINIFS"):
                idx = [(i, "all") for i in range(1, len(args), 2)]
            elif name in ("COUNTIFS",):
                idx = [(i, "all") for i in range(0, len(args), 2)]
            elif name in ("SUMIF", "COUNTIF", "AVERAGEIF"):
                idx = [(0, "all")]
            for i, part in idx:
                if i >= len(args):
                    continue
                for sh, box, *_ in refs_in("=" + args[i]):
                    tgt = wb.resolve(sh) if sh else x.sheet
                    if tgt:
                        c2 = box[0] if part == "first" else box[2]
                        keyed[tgt].add((box[0], box[1], c2, min(box[3], ROW_CAP)))
    for sheet, boxes in keyed.items():
        s = wb.sheets[sheet]
        pts = {}
        for (r, c), x in s.cells.items():
            if (
                isinstance(x.raw, str)
                and not x.formula
                and x.raw != x.raw.strip()
                and x.raw.strip()
            ):
                if any(b[0] <= c <= b[2] and b[1] <= r <= b[3] for b in boxes):
                    pts[(r, c)] = 0
        by_col = defaultdict(list)
        for r, c in pts:
            by_col[c].append(r)
        for c, rows in sorted(by_col.items()):
            rows.sort()
            col = get_column_letter(c)
            ex = s.cells[(rows[0], c)].raw
            fs.add(
                "lookup_key_spaces",
                sheet,
                f"{col}{rows[0]}" + (f":{col}{rows[-1]}" if len(rows) > 1 else ""),
                f"{plural(len(rows), 'cell')} with extra spaces (for example {data_text(ex)} in {col}{rows[0]}) in a column that lookups or SUMIFS match on - "
                f"those rows are silently skipped: "
                + ", ".join(f"{col}{r}" for r in rows[:10])
                + (" ..." if len(rows) > 10 else ""),
            )
            fs.items[-1]["_cells"] = {(r, c) for r in rows}


def scaffold_note(wb: Workbook):
    n = sum(len(s.cells) for s in wb.sheets.values())
    if not wb.formulas and n < 60:
        wb.notes.append(
            {
                "note": "template_scaffold",
                "detail": "the file has no formulas and very little content - it may be a template or placeholder rather than a working model",
            }
        )
