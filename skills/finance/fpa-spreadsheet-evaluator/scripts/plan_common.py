"""
description: Shared helpers for planning changes: cell lists, A1 text, money, summary clipping and nearby-cell search.
last_updated: 2026-11-24
"""

from __future__ import annotations

import re

import scan_workbook as S
from openpyxl.utils import get_column_letter


def fill_template(text, **values):
    """Fill {name} placeholders by plain replacement, so braces in workbook text are left alone."""
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    return text


def quote_sheetname(name):
    return (
        name
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name)
        and not re.fullmatch(r"[A-Za-z]{1,3}\d+", name)
        else "'" + name.replace("'", "''") + "'"
    )


MAX_CELLS_PER_CHANGE = (
    2000  # bigger ranges are listed for manual handling, not edited cell by cell
)


def cells_of(rng):
    if not rng:
        return []
    c1, r1, c2, r2 = S.parse_box(rng)
    if (c2 - c1 + 1) * (r2 - r1 + 1) > MAX_CELLS_PER_CHANGE:
        return None
    return [(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]


def a1(r, c):
    return f"{get_column_letter(c)}{r}"


def money(v):
    try:
        return f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.4g}"
    except (TypeError, ValueError):
        return str(v)


def row_label(s: S.Sheet, r, c):
    for cc in range(c - 1, 0, -1):
        x = s.cells.get((r, cc))
        if x and isinstance(x.raw, str) and not x.formula:
            return x.raw.strip()
    return ""


def nearest(s: S.Sheet, r, c, ok, prefer=None):
    """Closest cell satisfying ok(): same row, then same column, then anywhere on the tab."""
    best = None
    for (rr, cc), x in s.cells.items():
        if (rr, cc) == (r, c) or not ok(x):
            continue
        d = (
            0 if rr == r else 1 if cc == c else 2,
            abs(rr - r) + abs(cc - c),
            0 if prefer and prefer(x) else 1,
        )
        d = (d[0], d[2], d[1])
        if best is None or d < best[0]:
            best = (d, x)
    return best[1] if best else None


def boxes_overlap(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def display(f):
    return S.XL_PREFIX.sub("", f) if f else f


def printable(text):
    """Text for one printed line: control, bidi and line-separator characters escaped."""
    return "".join(ch if ch.isprintable() else f"\\u{ord(ch):04x}" for ch in str(text))


SUMMARY_FORMULA_CHARS = 80  # formulas quoted in a change's summary are clipped to this


def short(formula):
    """A formula clipped for a one-line summary (the full text is in the change's edits)."""
    return (
        formula
        if len(formula) <= SUMMARY_FORMULA_CHARS
        else formula[: SUMMARY_FORMULA_CHARS - 3] + "..."
    )
