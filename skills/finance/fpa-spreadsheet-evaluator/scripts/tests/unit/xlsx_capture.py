"""
description: Test helper that records the workbook bytes a download link embeds, by watching base64.b64encode, so tests read the Excel file without decoding the page.
last_updated: 2026-11-24
"""

import base64
import io
from unittest import mock

import openpyxl

_REAL_ENCODE = base64.b64encode
_SEEN: list[bytes] = []
_PATCH = mock.patch("base64.b64encode")


def _record(data, *args, **kwargs):
    _SEEN.append(bytes(data))
    return _REAL_ENCODE(data, *args, **kwargs)


def start() -> None:
    """Call from setUpModule: every later b64encode call is recorded."""
    _SEEN.clear()
    _PATCH.start().side_effect = _record


def stop() -> None:
    """Call from tearDownModule."""
    _PATCH.stop()


def last_workbook() -> openpyxl.Workbook:
    """The most recent .xlsx (a zip, so it starts with PK) passed to b64encode."""
    data = next(b for b in reversed(_SEEN) if b[:2] == b"PK")
    return openpyxl.load_workbook(io.BytesIO(data))
