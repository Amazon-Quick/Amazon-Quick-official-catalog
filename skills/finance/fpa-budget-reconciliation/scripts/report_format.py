"""
description: Shared formatting for create_report.py: the report palette, flag labels, money, percent and month formatting, HTML escaping and the inspect-item count.
last_updated: 2026-11-24
"""

from __future__ import annotations

import html
from datetime import datetime

INK = "#1B1F24"
MUTED = "#5B6470"
FAINT = "#8A929C"
RULE = "#E4E1DA"
PAPER = "#FBFAF7"
SPENT = "#23343D"
PENDING = "#557386"
OPEN = "#9BB3C1"
AVAILABLE = "#E7EDF0"
AVAILABLE_INK = "#2D6C93"
OVER = "#B4472D"
UNDER = "#2D6C93"
PLAN_LINE = "#8A929C"
MAX_INSPECT_ROWS = 7
MAX_VARIANCE_BARS = 8
CHAR_W = 0.56
KIND_LABELS = {
    "spike": "Spike against history",
    "overspend": "Over plan",
    "underspend": "Under plan",
    "timing": "Likely timing",
    "unplanned": "No plan",
    "committed_beyond_budget": "Committed past budget",
    "credit_balance": "Credit balance",
    "po_overrun": "PO overrun",
    "stale_commitment": "Stale PO",
    "aged_unposted_invoice": "Unposted invoice",
    "duplicate_invoice": "Duplicate invoice",
    "possible_duplicate_invoice": "Possible duplicate",
    "headcount_variance": "Headcount",
    "headcount_committed": "Headcount + reqs",
}


def money(symbol: str, value: float, decimals: int | None = None) -> str:
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e9:
        return f"{sign}{symbol}{v / 1e9:.{1 if decimals is None else decimals}f}B"
    if v >= 1e6:
        return f"{sign}{symbol}{v / 1e6:.{1 if decimals is None else decimals}f}M"
    if v >= 1e3:
        return f"{sign}{symbol}{v / 1e3:.0f}K"
    return f"{sign}{symbol}{v:,.0f}"


def signed_money(symbol: str, value: float) -> str:
    return ("+" if value > 0 else "") + money(symbol, value)


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:+.0f}%" if abs(value) >= 0.01 else f"{value * 100:+.1f}%"


def month_label(period: str, long: bool = False) -> str:
    stamp = datetime(int(period[:4]), int(period[5:]), 1)
    return stamp.strftime("%B %Y" if long else "%b")


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def text_width(text: str, size: float) -> float:
    return len(text) * size * CHAR_W


def inspect_items(result: dict) -> int:
    """Count each inspected line once, plus document and headcount items."""
    seen = {
        f["key"] if f["view"] != "document" else f["id"]
        for f in result["flags"]
        if f["tier"] == "inspect"
    }
    return len(seen) + sum(
        1 for f in result["headcount_flags"] if f["tier"] == "inspect"
    )
