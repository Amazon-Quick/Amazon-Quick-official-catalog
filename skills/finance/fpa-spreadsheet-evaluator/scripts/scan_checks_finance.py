"""
description: Run the finance checks in order after preparing period layouts and tab titles.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

from scan_checks_integrity import check_data_integrity, check_structure
from scan_checks_logic import check_financial_logic
from scan_checks_reconciliation import (
    check_header_formulas,
    check_period_alignment,
    check_reconciliation,
    check_text_in_sums,
    check_tie_outs,
)
from scan_finance_base import period_layout, sheet_title_text
from scan_formula_text import parse_box, refs_in
from scan_model_map import sheet_map


def drop_total_column_noise(wb, fs):
    """A total column (FY, Total, Q1 among months) aggregates its row, so its formula is meant to
    differ from the period formulas beside it: don't report that as an inconsistency."""
    keep = []
    for i in fs.items:
        s = wb.sheets.get(i.get("sheet") or "")
        P = getattr(s, "periods", None) if s is not None else None
        if i["check"] == "inconsistent_formula" and P and P["totals"] and i.get("cell"):
            c1, r1, c2, r2 = parse_box(i["cell"])
            ok = True
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    x = s.cells.get((r, c))
                    if c not in P["totals"] or x is None or not x.formula:
                        ok = False
                        continue
                    same_row = [
                        box
                        for sh, box, *_ in refs_in(x.formula)
                        if (not sh or wb.resolve(sh) == s.name)
                        and box[1] == box[3] == r
                        and all(cc in P["cols"] for cc in (box[0], box[2]))
                    ]
                    if not same_row:
                        ok = False
            if ok:
                continue
        keep.append(i)
    fs.items[:] = keep


def check_finance(wb, fs, cached_ok, mp):
    for s in wb.sheets.values():
        s.periods = period_layout(s) if s.rows else None
        s.title_text = sheet_title_text(s) if s.rows else ""
    drop_total_column_noise(wb, fs)
    roles = {x["sheet"]: x["role"] for x in sheet_map(wb)}
    check_reconciliation(wb, fs, cached_ok)
    check_tie_outs(wb, fs, roles, cached_ok)
    check_period_alignment(wb, fs)
    check_header_formulas(wb, fs)
    check_text_in_sums(wb, fs)
    check_data_integrity(wb, fs, cached_ok)
    check_financial_logic(wb, fs, cached_ok)
    check_structure(wb, fs, roles)
