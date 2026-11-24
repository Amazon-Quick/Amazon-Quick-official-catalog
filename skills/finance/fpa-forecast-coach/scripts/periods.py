"""
description: Frequencies and dates for the Forecast Coach: normalize a frequency code, read a date without guessing day-first or month-first, step forward by periods, label a period, and find a period's position in the season.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import datetime as _dt
import re

_FREQ = {
    "m": "MS",
    "mon": "MS",
    "month": "MS",
    "monthly": "MS",
    "ms": "MS",
    "me": "MS",
    "q": "QS",
    "quarter": "QS",
    "quarterly": "QS",
    "qs": "QS",
    "qe": "QS",
    "w": "W",
    "week": "W",
    "weekly": "W",
    "d": "D",
    "day": "D",
    "daily": "D",
    "y": "YS",
    "a": "YS",
    "year": "YS",
    "annual": "YS",
    "yearly": "YS",
    "ys": "YS",
}
SEASON = {"MS": 12, "QS": 4, "W": 52, "D": 7, "YS": 1}
PERIOD_LABEL = {"MS": "month", "QS": "quarter", "W": "week", "D": "day", "YS": "year"}
DATE_ORDERS = ("MDY", "DMY")
_NUMERIC_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/\d{4}")
_MONTHS_PER_YEAR = 12


class AmbiguousDateError(ValueError):
    """A source date needs an explicit day-first or month-first convention before it can be used."""


def normalise_freq(freq: str | None) -> str:
    """Map anything a user or pandas might hand us ('M', 'W-SUN', 'monthly') to one canonical code."""
    if not freq:
        return "MS"
    f = str(freq).strip()
    base = f.split("-")[0].lower()
    return _FREQ.get(base, _FREQ.get(f.lower(), "MS"))


def _check_order(given: str | None) -> None:
    if given is not None and given not in DATE_ORDERS:
        raise ValueError("date_order must be 'MDY' or 'DMY'")


def date_order(dates, given: str | None = None) -> str | None:
    """'DMY', 'MDY', or None, from the dates that can only be read one way; raises on a conflict."""
    _check_order(given)
    evidence = set()
    for value in dates:
        match = _NUMERIC_DATE.fullmatch(str(value).strip())
        if match:
            a, b = int(match[1]), int(match[2])
            if a > _MONTHS_PER_YEAR and 1 <= b <= _MONTHS_PER_YEAR:
                evidence.add("DMY")
            elif b > _MONTHS_PER_YEAR and 1 <= a <= _MONTHS_PER_YEAR:
                evidence.add("MDY")
    if len(evidence) > 1 or (given and evidence and given not in evidence):
        raise AmbiguousDateError(
            "Conflicting numeric date conventions. Confirm the source dates "
            "or provide unambiguous ISO dates before forecasting."
        )
    return given or next(iter(evidence), None)


def as_date(x, order: str | None = None) -> _dt.date:
    """A date from a date, a datetime, or text; a day/month date with no known order raises AmbiguousDateError."""
    _check_order(order)
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    text = str(x).strip()
    numeric = _NUMERIC_DATE.fullmatch(text)
    if numeric:
        a, b = int(numeric[1]), int(numeric[2])
        order = order or date_order([x])
        if order is None and a != b:
            raise AmbiguousDateError(
                f"Ambiguous date {text!r}: is this day/month/year or month/day/year? "
                "Confirm date_order='DMY' or 'MDY', or supply ISO dates."
            )
        fmt = "%d/%m/%Y" if order == "DMY" else "%m/%d/%Y"
        return _dt.datetime.strptime(text, fmt).date()
    s = text[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%b-%y", "%b %Y"):
        try:
            return _dt.datetime.strptime(s if fmt != "%b-%y" else text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"cannot read date: {x!r}")


def _add_months(d: _dt.date, k: int) -> _dt.date:
    m = d.month - 1 + k
    return _dt.date(d.year + m // 12, m % 12 + 1, min(d.day, 28))


def next_periods(last, n: int, freq: str) -> list:
    """n period-start dates after `last`, without needing pandas offsets."""
    out, d = [], as_date(last)
    for _ in range(n):
        if freq == "MS":
            d = _add_months(d, 1)
        elif freq == "QS":
            d = _add_months(d, 3)
        elif freq == "YS":
            d = _add_months(d, 12)
        elif freq == "W":
            d = d + _dt.timedelta(days=7)
        else:
            d = d + _dt.timedelta(days=1)
        out.append(d)
    return out


def fmt_period(d: _dt.date, freq: str) -> str:
    """The label a period carries in the workbook, such as 'Jan 2027' or 'Q1 2027'."""
    if freq == "MS":
        return d.strftime("%b %Y")
    if freq == "QS":
        return f"Q{(d.month - 1) // 3 + 1} {d.year}"
    if freq == "YS":
        return d.strftime("%Y")
    return d.strftime("%Y-%m-%d")


def season_pos(last_date, freq: str, season: int, steps_ahead: int) -> int | None:
    """Position in the season (0-based) of the period `steps_ahead` after `last_date`, or None."""
    d = next_periods(last_date, steps_ahead, freq)[-1]
    if freq == "MS" and season == SEASON["MS"]:
        return d.month - 1
    if freq == "QS" and season == SEASON["QS"]:
        return (d.month - 1) // 3
    if freq == "W" and season == SEASON["W"]:
        return min(d.isocalendar()[1] - 1, 51)
    if freq == "D" and season == SEASON["D"]:
        return d.weekday()
    return None
