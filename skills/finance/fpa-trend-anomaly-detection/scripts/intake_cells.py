"""
description: Read a sheet or CSV into a bounded cell matrix and classify single cell values for intake.
last_updated: 2026-11-24
"""

from __future__ import annotations

import csv as _csv
import json
import os
import re
import unicodedata

import numpy as np
from openpyxl import load_workbook

ROW_CAP = (
    20000  # a sheet can declare millions of empty rows; scans stop here and say so
)


COL_CAP = 400


TEXT_CAP = 6000  # characters any one printed view may return


NOTE_MIN_CHARS = 40  # a text cell this long is a note or an instruction, not a label


ERRORS = ("#REF!", "#NAME?", "#VALUE!", "#DIV/0!", "#N/A", "#NUM!", "#NULL!")


_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ]
    )
}


_TOTAL_WORDS = re.compile(
    r"\b(total|subtotal|sub-total|grand|sum of|consolidated|all (segments|regions|channels))\b",
    re.I,
)


_RATIO_WORDS = re.compile(
    r"(%|\bpct\b|\bpercent|\brate\b|\bratio\b|\bmargin\b|\bmix\b|\bshare\b|\bbps\b|\byoy\b|\bgrowth\b|\bper unit\b|\basp\b)",
    re.I,
)


_ACTUAL_WORDS = re.compile(r"^\s*(a|act|actual|actuals|ytd actual)\s*$", re.I)


_PLAN_WORDS = re.compile(
    r"\b(plan|budget|bud|fcst|forecast|reforecast|f|outlook|guidance|target|proj|projection|"
    r"est|estimate|e|le|current|latest|view|scenario)\b",
    re.I,
)


def _matrix(
    path: str,
    sheet: str | None = None,
    max_rows: int = ROW_CAP,
    max_cols: int = COL_CAP,
):
    """(rows, truncated, sheet_name): the sheet as a list of tuples of cached values, bounded."""
    if str(path).lower().endswith((".csv", ".txt")):
        out = []
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for i, row in enumerate(_csv.reader(fh)):
                if i >= max_rows:
                    return out, True, "csv"
                out.append(tuple(_coerce(c) for c in row[:max_cols]))
        return out, False, "csv"
    ws = _book(path)[sheet] if sheet else _book(path).worksheets[0]
    out, truncated = [], False
    for i, row in enumerate(ws.iter_rows(values_only=True, max_col=max_cols)):
        if i >= max_rows:
            truncated = True
            break
        out.append(row)
    while out and not any(v is not None for v in out[-1]):
        out.pop()
    return out, truncated, ws.title


_BOOKS: dict = {}


def _book(path: str):
    key = (os.path.abspath(path), os.path.getmtime(path))
    if key not in _BOOKS:
        _BOOKS.clear()
        _BOOKS[key] = load_workbook(path, read_only=True, data_only=True)
    return _BOOKS[key]


# an optional sign or brackets, an optional currency symbol (any Unicode Sc character, checked in
# _coerce), then digits with commas only in groups of three, so a decimal comma such as 12,5 stays text
_NUMBER_CELL = re.compile(
    r"\(?-?([^\w\s.,()%-])?\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)\s*(%?)\)?"
)


def _coerce(text: str):
    """A CSV field as a number when it is one (handles 1,234.5, (1,234), 12%), else the stripped text."""
    t = text.strip()
    if not t:
        return None
    if len(t) > 40:
        return t
    m = _NUMBER_CELL.fullmatch(t)
    if m and (not m.group(1) or unicodedata.category(m.group(1)) == "Sc"):
        v = float(m.group(2).replace(",", ""))
        if t.startswith("(") or "-" in t[: m.start(2)]:
            v = -v
        return v / 100.0 if m.group(3) else v
    return t


def _col(n: int) -> str:
    """0-based column index -> Excel letters."""
    s, n = "", n + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _is_num(v) -> bool:
    return (
        isinstance(v, (int, float))
        and not isinstance(v, bool)
        and not (isinstance(v, float) and np.isnan(v))
    )


def _text(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _is_missing(v) -> bool:
    return (
        v is None
        or (isinstance(v, str) and not v.strip())
        or (isinstance(v, (float, np.floating)) and np.isnan(v))
    )


def _untrusted(value) -> str:
    """A bounded, escaped preview of source data, never an instruction."""
    text = str(value)
    preview = text[:120] + ("..." if len(text) > 120 else "")
    return "untrusted cell value " + json.dumps(preview, ensure_ascii=True)


def _untrusted_values(values) -> str:
    preview = ", ".join(_untrusted(value) for value in values[:10])
    if len(values) > 10:
        preview += f", and {len(values) - 10} more values (see source)"
    return preview
