"""
description: Read a previous Forecast Coach workbook's Bands sheet as P50 by series and period, so a re-run compares only the periods both runs share, and raise ValueError with a reason when it can't.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import math
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

MAX_ROWS = 200_000  # a Bands sheet has one row per series per period; refuse anything far larger
_DEFANGED = ("=", "+", "-", "@")


def _p50(value) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        p50 = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError("prior Bands contains an unreadable P50") from err
    return None if math.isnan(p50) else p50


def _series_name(raw) -> str:
    name = str(raw)
    if name.startswith("'") and name[1:2] in _DEFANGED:
        return name[1:]
    return name


def bands_by_period(rows) -> dict:
    """{series: {period label: P50}} from Bands rows (series, period, P10, P50, ...), header excluded."""
    values: dict = {}
    for count, row in enumerate(rows, start=1):
        if count > MAX_ROWS:
            raise ValueError(f"prior Bands has more than {MAX_ROWS} rows")
        if not row or all(v is None for v in row):
            continue
        p50 = _p50(row[3] if len(row) > 3 else None)
        if p50 is None:
            continue
        if row[0] is None or row[1] is None or not math.isfinite(p50):
            raise ValueError(
                "prior Bands contains an unreadable series, period, or P50"
            )
        line = values.setdefault(_series_name(row[0]), {})
        period = str(row[1])
        if period in line:
            raise ValueError("prior Bands repeats a series and period")
        line[period] = p50
    if not values:
        raise ValueError("prior Bands has no comparable P50 values")
    return values


def load_prior(path: str) -> dict:
    """{series: {period label: P50}} from a prior workbook; ValueError or OSError says why it failed."""
    wb = None
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
        if "Bands" not in wb.sheetnames:
            raise ValueError("prior workbook has no Bands sheet")
        return bands_by_period(wb["Bands"].iter_rows(min_row=2, values_only=True))
    except (BadZipFile, InvalidFileException, KeyError, SyntaxError) as err:
        # SyntaxError covers xml.etree's ParseError for a corrupt sheet
        raise ValueError(f"cannot read prior workbook ({type(err).__name__})") from err
    finally:
        if wb is not None:
            wb.close()
