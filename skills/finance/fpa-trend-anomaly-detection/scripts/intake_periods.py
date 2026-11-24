"""
description: Parse period labels and dates, and work out the time grain and the last finished period.
last_updated: 2026-11-24
"""

from __future__ import annotations

import datetime as _dt
import re

from intake_cells import _MONTHS, _is_num


def parse_period(v, date_order=None):
    """Parse only an unambiguous date, or use the user's explicit MDY/DMY answer.

    Invalid dates return None. Numeric dates such as 03/04/2025 need date_order;
    silently guessing changes which period receives the amount.
    """
    if date_order is not None and date_order not in ("MDY", "DMY"):
        raise ValueError("date_order must be 'MDY' or 'DMY'")
    try:
        return _parse_period(v, date_order)
    except (ValueError, OverflowError):
        return None


def _parse_period(v, date_order=None):
    """A header cell as a period start date, or None. Handles dates, 'Jan-24', 'Jan 2024', '2024-01',
    '1/2024', 'Q1 2025', 'FY25 Q1', '2025Q1' and plain years. Quarters are read as calendar quarters."""
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    if _is_num(v) and float(v).is_integer() and 1990 <= int(v) <= 2100:
        return _dt.date(int(v), 1, 1)
    if not isinstance(v, str):
        return None
    t = v.strip().lower().replace("'", "-")
    if not t or len(t) > 24:
        return None
    m = re.fullmatch(r"(\d{1,2})[\s\-/]([a-z]{3})[a-z]*[\s\-/](\d{2}|\d{4})", t)
    if m and m.group(2) in _MONTHS:
        return _dt.date(_year(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
    m = re.fullmatch(r"([a-z]{3})[a-z]*[\s\-/](\d{1,2}),?[\s\-/](\d{2}|\d{4})", t)
    if m and m.group(1) in _MONTHS:
        return _dt.date(_year(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))
    m = re.fullmatch(r"([a-z]{3})[a-z]*[\s\-/]*(\d{2}|\d{4})", t)
    if m and m.group(1) in _MONTHS:
        return _dt.date(_year(m.group(2)), _MONTHS[m.group(1)], 1)
    m = re.fullmatch(r"(\d{4})[\s\-/]([a-z]{3})[a-z]*", t)
    if m and m.group(2) in _MONTHS:
        return _dt.date(int(m.group(1)), _MONTHS[m.group(2)], 1)
    m = re.fullmatch(r"(\d{4})[\-/](\d{1,2})(?:[\-/](\d{1,2}))?", t)
    if m and 1 <= int(m.group(2)) <= 12:
        return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if not date_order and a != b and 1 <= a <= 12 and 1 <= b <= 12:
            return None
        order = date_order or ("DMY" if a > 12 else "MDY")
        month, day = (b, a) if order == "DMY" else (a, b)
        return _dt.date(_year(m.group(3)), month, day)
    m = re.fullmatch(r"(\d{1,2})/(\d{4})", t)
    if m and 1 <= int(m.group(1)) <= 12:
        return _dt.date(int(m.group(2)), int(m.group(1)), 1)
    m = re.fullmatch(r"(?:fy)?\s*(\d{2}|\d{4})[\s\-_]*q([1-4])", t) or re.fullmatch(
        r"q([1-4])[\s\-_]*(?:fy)?\s*(\d{2}|\d{4})", t
    )
    if m:
        a, b = m.groups()
        yr, q = (a, b) if len(a) != 1 else (b, a)
        return _dt.date(_year(yr), 3 * (int(q) - 1) + 1, 1)
    m = re.fullmatch(r"(?:fy|cy)\s*(\d{2}|\d{4})", t)
    if m:
        return _dt.date(_year(m.group(1)), 1, 1)
    return None


def _year(s: str) -> int:
    y = int(s)
    return y if y > 99 else (2000 + y if y < 70 else 1900 + y)


def _freq(dates: list) -> str:
    if len(dates) < 2:
        return "MS"
    gaps = sorted((b - a).days for a, b in zip(dates, dates[1:], strict=False))
    g = gaps[len(gaps) // 2]
    return (
        "D"
        if g <= 2
        else "W"
        if g <= 10
        else "MS"
        if g <= 45
        else "QS"
        if g <= 135
        else "YS"
    )


def _longest_run_loose(cells: list) -> tuple:
    """Down a column the same period repeats for every entity, so only require dates not to be sparse."""
    return [p for p, _ in cells], sorted({d for _, d in cells})


def _grain(v) -> str:
    """What size of period a header cell names: M(onth or finer), Q(uarter) or Y(ear)."""
    if isinstance(v, (_dt.date, _dt.datetime)):
        return "M"
    if _is_num(v):
        return "Y"
    t = str(v).strip().lower()
    if re.search(r"q[1-4]", t):
        return "Q"
    if re.fullmatch(r"(fy|cy)?\s*\d{2,4}", t):
        return "Y"
    return "M"


def _cells_as_periods(cells: list, date_order=None) -> list:
    """[(position, date)] for the cells that read as periods, keeping one grain only.

    A finance header often runs Jan, Feb, Mar, Q1, Apr ... Dec, FY: the quarter and year columns are
    subtotals. The grain with the most cells wins and the others are ignored. Bare numbers such as 2024
    only count when they run consecutively, so a data row whose values sit between 1990 and 2100 is not
    taken for a header.
    """
    found = []
    for i, (pos, v) in enumerate(cells):
        d = parse_period(v, date_order)
        if d is None:
            continue
        if _is_num(v):
            near = [x for _, x in cells[max(0, i - 2) : i + 3] if _is_num(x)]
            if not any(abs(float(x) - float(v)) == 1 for x in near):
                continue
        found.append((pos, d, _grain(v)))
    if not found:
        return []
    counts = {}
    for _, _, g in found:
        counts[g] = counts.get(g, 0) + 1
    top = max(counts, key=lambda g: (counts[g], g == "M"))
    return [(pos, d) for pos, d, g in found if g == top]


def _last_full_period(dates: list, freq: str, today: _dt.date) -> int:
    """Index of the last period that had fully ended before `today`. -1 if none."""
    last = -1
    for i, d in enumerate(dates):
        if freq == "MS":
            end = _dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        elif freq == "QS":
            m = d.month + 3
            end = _dt.date(d.year + (m > 12), (m - 1) % 12 + 1, 1)
        elif freq == "YS":
            end = _dt.date(d.year + 1, 1, 1)
        elif freq == "W":
            end = d + _dt.timedelta(days=7)
        else:
            end = d + _dt.timedelta(days=1)
        if end <= today:
            last = i
    return last


def _as_date(x) -> _dt.date | None:
    if x is None:
        return None
    return (
        parse_period(x)
        if not isinstance(x, (_dt.date, _dt.datetime))
        else (x.date() if isinstance(x, _dt.datetime) else x)
    )
