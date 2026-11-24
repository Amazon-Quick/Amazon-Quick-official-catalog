"""
description: Shared workbook pieces for the Forecast Coach: the cell formats, the workbook options that keep user text as text (no formulas, no hyperlinks), and the guard that stops a text cell being read as a formula.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import xlsxwriter

# Store every string as text: never turn user text into a formula or a clickable link.
WORKBOOK_OPTIONS = {
    "nan_inf_to_errors": True,
    "default_date_format": "yyyy-mm-dd",
    "strings_to_formulas": False,
    "strings_to_urls": False,
}
_FORMULA_STARTS = ("=", "+", "-", "@")


def defang(text) -> str:
    """Prefix an apostrophe so Excel never reads a text cell or chart title as a formula."""
    s = "" if text is None else str(text)
    return "'" + s if s[:1] in _FORMULA_STARTS else s


def open_workbook(out_path: str) -> xlsxwriter.Workbook:
    """A new xlsxwriter workbook at `out_path` with WORKBOOK_OPTIONS."""
    return xlsxwriter.Workbook(out_path, WORKBOOK_OPTIONS)


def formats(wb: xlsxwriter.Workbook) -> dict:
    """The named cell formats every sheet uses."""
    return {
        "h": wb.add_format(
            {
                "bold": True,
                "bg_color": "#1F3864",
                "font_color": "white",
                "border": 1,
                "text_wrap": True,
                "valign": "vcenter",
            }
        ),
        "num": wb.add_format({"num_format": "#,##0.0"}),
        "numb": wb.add_format({"num_format": "#,##0.0", "bold": True}),
        "pct": wb.add_format({"num_format": "0.0%"}),
        "pctb": wb.add_format(
            {"num_format": "0.0%", "bold": True, "bg_color": "#E2EFDA"}
        ),
        "pct_in": wb.add_format(
            {"num_format": "0.0%", "bg_color": "#FFF2CC", "border": 1}
        ),
        "abs_in": wb.add_format(
            {"num_format": "#,##0.0", "bg_color": "#FFF2CC", "border": 1}
        ),
        "txt_in": wb.add_format({"bg_color": "#FFF2CC", "border": 1}),
        "fin": wb.add_format(
            {"num_format": "#,##0.0", "bold": True, "bg_color": "#E2EFDA", "border": 1}
        ),
        "lbl": wb.add_format({"bold": True}),
        "wrap": wb.add_format({"text_wrap": True, "valign": "top"}),
        "title": wb.add_format({"bold": True, "font_size": 14}),
        "flag": wb.add_format(
            {"text_wrap": True, "valign": "top", "font_color": "#9C0006"}
        ),
    }
