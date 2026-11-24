"""
description: Pure parsing and formatting helpers for run_reconciliation.py: untrusted-text quoting, dates, fiscal and month period labels, amounts, the robust z-score and money formatting.
last_updated: 2026-11-24
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime

import numpy as np
import pandas as pd
from recon_models import (
    SpecError,
)

MODIFIED_Z_SCALE = 0.6745
DATA_TEXT_LIMIT = 240
REASON_TEXT_LIMIT = 80
PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
NUMERIC_DATE_RE = re.compile(r"^(\d{1,2})[\s./-]+(\d{1,2})[\s./-]+\d{2,4}(?:$|[ T])")
FISCAL_PERIOD_RE = re.compile(
    r"^(?:FY)?\s*'?(\d{2,4})\s*(?:[-_/]\s*)?(?:P|M|PER|PERIOD)\s*(\d{1,2})$",
    re.IGNORECASE,
)
PERIOD_FIRST_RE = re.compile(
    r"^(?:P|M|PER|PERIOD)\s*(\d{1,2})\s*(?:[-_/]\s*)?(?:FY\s*)?'?(\d{2,4})$",
    re.IGNORECASE,
)
MON_YEAR_RE = re.compile(r"^([A-Za-z]{3,9})[-\s/'.]*(\d{4}|\d{2})$")
MONTHS_ABBR = {
    m: i
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
        ],
        start=1,
    )
}
NUMBER_RE = re.compile(
    r"(?P<sign>[-+]?)\s*(?:(?:[A-Z]{3}|[AC]\$|[$€£¥₹])\s*)?"
    r"(?P<number>[-+]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)"
    r"(?:[eE][-+]?\d+)?)\s*(?:[A-Z]{3}|[AC]\$|[$€£¥₹])?",
    re.IGNORECASE,
)


def clip_text(value: object) -> str:
    """Bound file text quoted inside a flag reason."""
    return str(value)[:REASON_TEXT_LIMIT]


def file_data(value: object) -> str:
    """Bound and quote file text before including it in an agent-facing message."""
    return "DATA (untrusted, from file): " + json.dumps(
        str(value)[:DATA_TEXT_LIMIT], ensure_ascii=True
    )


def parse_date(value: object, date_order: str | None = None) -> date | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.date() if isinstance(value, datetime) else value
    text = str(value).strip()
    if not text:
        return None
    numeric = NUMERIC_DATE_RE.match(text)
    if numeric and date_order is None:
        first, second = map(int, numeric.groups())
        if 1 <= first <= 12 and 1 <= second <= 12 and first != second:
            raise SpecError(
                "Ambiguous numeric date; confirm date_order as 'day_first' or "
                f"'month_first' in the spec, or use ISO dates. {file_data(text)}"
            )
    if numeric and date_order is not None:
        first, second = map(int, numeric.groups())
        day, month = (first, second) if date_order == "day_first" else (second, first)
        if not (1 <= day <= 31 and 1 <= month <= 12):
            raise SpecError(
                f"Numeric date contradicts date_order={date_order!r}; "
                f"correct the date or convention. {file_data(text)}"
            )
    # Pandas also applies dayfirst to ISO dates unless it is restricted here.
    stamp = pd.to_datetime(
        text,
        errors="coerce",
        format="mixed",
        dayfirst=date_order == "day_first" and numeric is not None,
    )
    if numeric and date_order is not None and pd.isna(stamp):
        raise SpecError(
            f"Invalid numeric date for date_order={date_order!r}; "
            f"correct the date. {file_data(text)}"
        )
    return None if pd.isna(stamp) else stamp.date()


class PeriodParser:
    """Turns dates, month labels and fiscal period labels into YYYY-MM."""

    def __init__(
        self, fy_start_month: int, fy_label: str, date_order: str | None = None
    ) -> None:
        self.fy_start_month = fy_start_month
        self.fy_label = fy_label
        self.date_order = date_order

    def parse(self, value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        if isinstance(value, (datetime, date, pd.Timestamp)):
            return f"{value.year:04d}-{value.month:02d}"
        text = str(value).strip()
        if not text:
            return None
        if PERIOD_RE.match(text):
            return text
        fiscal = self._fiscal(text) if len(text) <= 32 else None
        if fiscal:
            return fiscal
        named = MON_YEAR_RE.match(text)
        if named and named.group(1)[:3].lower() in MONTHS_ABBR:
            year = int(named.group(2))
            year = year + 2000 if year < 100 else year
            return f"{year:04d}-{MONTHS_ABBR[named.group(1)[:3].lower()]:02d}"
        stamp = parse_date(text, self.date_order)
        if stamp is None:
            return None
        return f"{stamp.year:04d}-{stamp.month:02d}"

    def _fiscal(self, text: str) -> str | None:
        match = FISCAL_PERIOD_RE.match(text)
        year_txt, period_txt = (
            (match.group(1), match.group(2)) if match else (None, None)
        )
        if not match:
            other = PERIOD_FIRST_RE.match(text)
            if not other:
                return None
            period_txt, year_txt = other.group(1), other.group(2)
        year = int(year_txt)
        year = year + 2000 if year < 100 else year
        period = int(period_txt)
        if not 1 <= period <= 12:
            return None
        start_year = (
            year - 1 if (self.fy_label == "end" and self.fy_start_month != 1) else year
        )
        month_index = self.fy_start_month - 1 + period - 1
        return f"{start_year + month_index // 12:04d}-{month_index % 12 + 1:02d}"


def period_range(start: str, end: str) -> list[str]:
    y, m = int(start[:4]), int(start[5:])
    ey, em = int(end[:4]), int(end[5:])
    out: list[str] = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def shift_period(period: str, months: int) -> str:
    index = int(period[:4]) * 12 + int(period[5:]) - 1 + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def to_number(value: object) -> float:
    """Read one finite amount; never turn an unreadable cell into zero.

    An empty cell is missing, not corrupt: None, blank text and NaN read as
    zero, the way an absent row does, so a period with no actuals yet still
    ties out. Text that is present but cannot be read raises instead, so the
    caller reports the cell rather than counting it as zero.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        try:
            number = float(value)
        except OverflowError as exc:
            raise ValueError("Number is outside the finite range") from exc
        if math.isnan(number):
            return 0.0
        if not math.isfinite(number):
            raise ValueError(f"Non-finite number: {value!r}")
        return number
    text = str(value).strip()
    if not text:
        return 0.0
    negative = text.upper().endswith("CR")
    if text.upper().endswith(("CR", "DR")):
        text = text[:-2].rstrip()
    if text.endswith("-"):
        negative, text = True, text[:-1]
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1].strip()
    match = NUMBER_RE.fullmatch(text)
    if not match or (match["sign"] and match["number"].startswith(("-", "+"))):
        raise ValueError(f"Unreadable number: {str(value)[:80]!r}")
    number = float(match["sign"] + match["number"].replace(",", ""))
    if not math.isfinite(number):
        raise ValueError(f"Non-finite number: {str(value)[:80]!r}")
    return -abs(number) if negative else number


def nice_round(value: float) -> float:
    """Rounds down to two significant figures so a floor reads as a round number without halving it."""
    if value <= 0:
        return 0.0
    base = 10 ** (math.floor(math.log10(value)) - 1)
    return float(math.floor(value / base) * base)


def modified_z(values: np.ndarray, target: float) -> float | None:
    """Iglewicz-Hoaglin modified z of target against values (median and MAD)."""
    if values.size == 0:
        return None
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    if mad == 0:
        spread = float(np.mean(np.abs(values - median)))
        if spread == 0:
            return None
        return (target - median) / (1.253314 * spread)
    return MODIFIED_Z_SCALE * (target - median) / mad


def safe_pct(numerator: float, denominator: float) -> float | None:
    return None if abs(denominator) < 1e-9 else numerator / abs(denominator)


def normal_text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def money(symbol: str, value: float) -> str:
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e9:
        return f"{sign}{symbol}{v / 1e9:.1f}B"
    if v >= 1e6:
        return f"{sign}{symbol}{v / 1e6:.1f}M"
    if v >= 1e3:
        return f"{sign}{symbol}{v / 1e3:.0f}K"
    return f"{sign}{symbol}{v:,.0f}"


def pct_text(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:+.0f}%"
