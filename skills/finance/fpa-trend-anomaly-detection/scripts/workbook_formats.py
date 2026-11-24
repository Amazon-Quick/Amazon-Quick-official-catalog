"""
description: Adds the cell formats every workbook sheet uses and returns them by name.
last_updated: 2026-11-24
"""

from __future__ import annotations

from workbook_context import BLUE, NAVY, RED, YELLOW


def add_formats(wb, nfmt: str) -> dict:
    """Add the shared formats to the workbook, in the original order, and return them by name."""
    F = {
        "title": wb.add_format({"bold": True, "font_size": 14, "font_color": NAVY}),
        "sub": wb.add_format({"italic": True, "font_color": "#595959"}),
        "h": wb.add_format(
            {
                "bold": True,
                "bg_color": NAVY,
                "font_color": "#FFFFFF",
                "border": 1,
                "text_wrap": True,
                "valign": "top",
            }
        ),
        "hy": wb.add_format(
            {
                "bold": True,
                "bg_color": YELLOW,
                "border": 1,
                "text_wrap": True,
                "valign": "top",
            }
        ),
        "b": wb.add_format({"bold": True}),
        "txt": wb.add_format({"valign": "top"}),
        "wrap": wb.add_format({"text_wrap": True, "valign": "top"}),
        "num": wb.add_format({"num_format": nfmt, "valign": "top"}),
        "numb": wb.add_format({"num_format": nfmt, "valign": "top", "bold": True}),
        "pct": wb.add_format({"num_format": "+0.0%;-0.0%;0.0%", "valign": "top"}),
        "pct0": wb.add_format({"num_format": "0.0%", "valign": "top"}),
        "sc": wb.add_format({"num_format": "+0.0;-0.0;0.0", "valign": "top"}),
        "int": wb.add_format({"num_format": "0", "valign": "top"}),
        "in_pct": wb.add_format(
            {"num_format": "0.0%", "font_color": BLUE, "bg_color": YELLOW, "border": 1}
        ),
        "in_num": wb.add_format(
            {"num_format": nfmt, "font_color": BLUE, "bg_color": YELLOW, "border": 1}
        ),
        "in_txt": wb.add_format({"font_color": BLUE, "bg_color": YELLOW, "border": 1}),
        "fill": wb.add_format(
            {"bg_color": YELLOW, "border": 1, "text_wrap": True, "valign": "top"}
        ),
        "yes": wb.add_format({"bold": True, "font_color": RED}),
        "hi": wb.add_format({"bg_color": "#F8CBAD"}),
        "lo": wb.add_format({"bg_color": "#BDD7EE"}),
        "note": wb.add_format(
            {"text_wrap": True, "valign": "top", "font_color": "#404040"}
        ),
    }
    return F
