"""
description: Plain-language labels and mini cell views for scan findings: row and column labels, range labels and the cell grid.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import datetime as dt

from openpyxl.styles.numbers import is_date_format
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import from_excel
from scan_formats import display_text, fmt_section, is_num, numeric_text
from scan_formula_text import parse_box
from scan_load import C, Sheet


def label_for(s: Sheet, x: C) -> str:
    h = s.cells.get((s.header_row, x.c))
    row_lab = next(
        (
            s.cells[(x.r, c)].raw
            for c in range(1, x.c)
            if (x.r, c) in s.cells
            and isinstance(s.cells[(x.r, c)].raw, str)
            and not s.cells[(x.r, c)].formula
        ),
        "",
    )
    return f"{h.raw if h and isinstance(h.raw, str) else ''} {row_lab}"


GRID_ROWS, GRID_COLS, GRID_MAX = (
    5,
    6,
    250,
)  # mini cell view: window size, and how many findings get one


def _clip(text, n=40):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "\u2026"


def row_label_at(s: Sheet, r: int, c: int) -> str:
    """Nearest typed text to the left of (r, c) - usually the line item."""
    return next(
        (
            _clip(s.cells[(r, cc)].raw)
            for cc in range(c - 1, 0, -1)
            if (r, cc) in s.cells
            and isinstance(s.cells[(r, cc)].raw, str)
            and not s.cells[(r, cc)].formula
            and s.cells[(r, cc)].raw.strip()
            and not numeric_text(s.cells[(r, cc)].raw)
        ),
        "",
    )


def col_label_at(s: Sheet, r: int, c: int) -> str:
    """The header-row text above (r, c) - usually the period or field name."""
    if not s.header_row or s.header_row >= r:
        return ""
    h = s.cells.get((s.header_row, c))
    if h and h.raw is not None and not h.formula and str(h.raw).strip():
        v = h.raw
        return _clip(
            v.strftime("%b %Y") if isinstance(v, (dt.datetime, dt.date)) else v, 24
        )
    return ""


def range_label(s: Sheet, ref: str) -> str:
    """Plain words for a cell or range: 'Revenue \u00b7 Q5', 'Cost \u00b7 Q1 \u2013 Q6'."""
    try:
        c1, r1, c2, r2 = parse_box(ref)
    except ValueError:
        return ""
    if r2 - r1 > 5000 or c2 - c1 > 500:
        return ""
    rows = [row_label_at(s, r, c1) for r in (r1, r2)]
    cols = [col_label_at(s, r1, c) for c in (c1, c2)]
    if (
        s.is_data
    ):  # data tabs: name the record by its first column and the field by its header
        field = (
            cols[0]
            if c1 == c2 or cols[0] == cols[1] or not cols[1]
            else f"{cols[0]} \u2013 {cols[1]}"
        )
        if r1 != r2:
            return " \u00b7 ".join(p for p in (field, f"rows {r1:,}\u2013{r2:,}") if p)
        k = s.cells.get((r1, 1))
        key = (
            _clip(k.cached if k.formula else k.raw, 24)
            if k is not None
            and c1 != 1
            and (k.cached if k.formula else k.raw) not in (None, "")
            else ""
        )
        return (
            " \u00b7 ".join(p for p in (key and str(key), field) if p) or f"row {r1:,}"
        )
    if (r1, c1) == (r2, c2) and not rows[
        0
    ]:  # a label cell itself (e.g. a lookup key): name it by its text
        x = s.cells.get((r1, c1))
        if x is not None and isinstance(x.raw, str) and not x.formula and x.raw.strip():
            return _clip(x.raw.strip(), 30)
    row_part = (
        rows[0]
        if r1 == r2 or rows[0] == rows[1] or not rows[1]
        else f"{rows[0]} \u2026 {rows[1]}"
    )
    col_part = (
        cols[0]
        if c1 == c2 or cols[0] == cols[1] or not cols[1]
        else f"{cols[0]} \u2013 {cols[1]}"
    )
    return " \u00b7 ".join(p for p in (row_part, col_part) if p)


def short_value(x) -> str:
    """Roughly what the cell shows, for the mini cell view."""
    v = x.cached if x.formula else x.raw
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v).upper()
    if isinstance(v, (dt.datetime, dt.date)):
        return v.strftime("%d %b %Y")
    if isinstance(v, str):
        return _clip(v, 18)
    if is_num(v) and x.fmt and is_date_format(x.fmt) and 0 < v < 2958466:
        try:
            date_text = from_excel(v).strftime("%d %b %Y")
        except (ValueError, OverflowError):
            date_text = None
        if date_text is not None:
            return date_text
    if is_num(v):
        shown = display_text(float(v), x.fmt or "General")
        if shown and fmt_section(x.fmt).strip().lower() != "general":
            pct = "%" in fmt_section(x.fmt)
            return ("-" if v < 0 else "") + shown[0] + ("%" if pct else "")
        if v != 0 and abs(v) < 1:
            return f"{v:.4g}"
        return f"{v:,.0f}" if abs(v) >= 1000 or float(v).is_integer() else f"{v:,.2f}"
    return _clip(v, 18)


def mini_grid(s: Sheet, ref: str):
    """A few cells around the finding, so the problem is visible at a glance."""
    try:
        c1, r1, c2, r2 = parse_box(ref)
    except ValueError:
        return None
    if r2 - r1 > 2000 or c2 - c1 > 200:
        return None
    top = max(1, r1 - 2)
    rows = list(range(top, top + GRID_ROWS))
    if r1 not in rows:
        rows = list(range(r1 - 1, r1 - 1 + GRID_ROWS))
    left = max(1, c1 - 1 if c2 > c1 else c1 - 2)
    cols = list(range(left, left + GRID_COLS))
    lab_c = next(
        (
            c
            for c in range(1, left)
            if any(
                isinstance(getattr(s.cells.get((r, c)), "raw", None), str) for r in rows
            )
        ),
        None,
    )
    if lab_c:
        cols = [lab_c, None] + cols[: GRID_COLS - 1]
    if s.header_row and s.header_row < rows[0]:
        rows = [s.header_row, None] + rows[: GRID_ROWS - 1]
    out_rows = []
    for r in rows:
        if r is None:
            out_rows.append(None)
            continue
        cells = []
        for c in cols:
            if c is None:
                cells.append(None)
                continue
            x = s.cells.get((r, c))
            hl = r1 <= r <= r2 and c1 <= c <= c2
            if x is None:
                cells.append({"t": "", "k": "", "hl": hl})
                continue
            v = x.cached if x.formula else x.raw
            kind = (
                "e"
                if isinstance(v, str)
                and v.startswith("#")
                and v.endswith(("!", "?", "A"))
                else "f"
                if x.formula
                else "i"
                if is_num(x.raw)
                else "t"
            )
            cell = {"t": short_value(x), "k": kind, "hl": hl}
            if x.formula:
                cell["f"] = x.formula[:200]
            cells.append(cell)
        out_rows.append({"r": r, "cells": cells})
    if not any(c and c.get("t") for row in out_rows if row for c in row["cells"]):
        return None
    return {
        "cols": [get_column_letter(c) if c else None for c in cols],
        "rows": out_rows,
    }
