"""
description: Holds what the workbook sheets share: the open workbook, formats, sheet handles, cell helpers and colours.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

NAVY, GREY, YELLOW, BLUE, RED, GREEN = (
    "#1F3864",
    "#F2F2F2",
    "#FFF2CC",
    "#0000FF",
    "#C00000",
    "#375623",
)
MAX_CHARTS = 12
RECURRING = ["One-time", "Recurring", "Timing", "Error / correction", "Under review"]


def _col(n: int) -> str:
    s, n = "", n + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(r: int, c: int, absolute: bool = False) -> str:
    return ("$%s$%d" if absolute else "%s%d") % (_col(c), r + 1)


def _num(v):
    """A float xlsxwriter can write, or None for missing."""
    if v is None:
        return None
    v = float(v)
    return v if math.isfinite(v) else None


@dataclass
class WorkbookContext:
    """The open workbook and everything the sheet writers share."""

    res: dict
    st: dict
    labels: list
    lines: dict
    names: list
    do_anom: bool
    do_trend: bool
    voc: dict
    units: str
    wb: Any
    F: dict
    ws_sum: Any
    ws_an: Any
    ws_tr: Any
    ws_dc: Any
    ws_ch: Any
    ws_d: Any
    ws_e: Any
    ws_s: Any
    ws_m: Any
    ws_x: Any
    R0: int
    C0: int
    row_of: dict

    def dref(self, n, t):
        """A reference to one period of a line on the Data sheet."""
        return f"Data!{_cell(self.row_of[n], self.C0 + t)}"

    def drange(self, n, t0, t1):
        """A reference to a run of periods of a line on the Data sheet."""
        return f"Data!{_cell(self.row_of[n], self.C0 + t0)}:{_cell(self.row_of[n], self.C0 + t1)}"
