"""
description: Find the right rows and columns of history in a spreadsheet or CSV without dumping whole sheets.
last_updated: 2026-11-24

Workbook intake: find the right rows in a spreadsheet without ever dumping a sheet.

Finance workbooks are large, have many tabs, and mix actuals with plan. Reading one into the model's
context either blows the budget or clips the row that mattered, and eyeballing a dump is how the wrong
scenario or a totals row gets analyzed. So every view here is small and targeted:

    menu(path)                       every sheet: size, header text, row labels, where the periods are. No numbers.
    find(path, text)                 every cell whose text contains `text`, with its coordinates
    rows(path, sheet, first, last)   a short row range, values only
    periods(path, sheet)             where the period header is and what it covers
    values(path, sheet, header)      the distinct values under a column header (to choose grouping and filters)

and one function does the reading for real, deterministically, once the agent knows what it wants:

    extract(path, sheet, rows=[...] | labels=[...])    wide layout: one line per row, periods across columns
    extract_long(path, sheet, date_col, value_col, key_cols, filters)   one row per period per entity

Both return the `series` dict series_review.run() takes, plus where each line came from (`provenance`),
what was left out and why (`skipped`), and what to tell the user before analysing (`issues`). Text printed
by `menu`, `find`, `rows` and `values` is capped, so a 30 MB workbook costs the same context as a small one.

Works on .xlsx/.xlsm (streamed, so large files open in seconds) and .csv. numpy and openpyxl only.
"""

from __future__ import annotations

from intake_bands import periods as periods
from intake_long import extract_long as extract_long
from intake_periods import parse_period as parse_period
from intake_views import find as find
from intake_views import menu as menu
from intake_views import rows as rows
from intake_views import values as values
from intake_wide import extract as extract

__all__ = [
    "menu",
    "find",
    "rows",
    "periods",
    "values",
    "extract",
    "extract_long",
    "parse_period",
]
