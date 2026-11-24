"""
description: Scan limits, thresholds and fixed word lists shared by the workbook scan's checks.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re

# Limits. Each is a judgment call; the reason is next to it.
ROW_CAP, COL_CAP = 20_000, 256
"""Cells beyond these are not scanned. A stray formatted cell can make a sheet claim
millions of cells; real finance models sit well inside 20,000 rows x 256 columns."""
CELL_CAP = (
    1_500_000  # stored cells per workbook; beyond this the scan stops and says so
)
# The metadata/formula copy stays in memory for structural checks. Bound its
# input before openpyxl parses it; compressed file size alone is not a safe limit.
ARCHIVE_SIZE_CAP = 32 * 1024 * 1024
ARCHIVE_MEMBER_CAP = 16 * 1024 * 1024
ARCHIVE_RATIO_CAP = 1000
CIRCULAR_EDGE_CAP = 2_000_000  # range references add O(log n) edges each
FINANCIAL_WORK_CAP = (
    2_000_000  # cell visits in the double-counting check; also bounds its memory
)
DV_RULE_CAP = 1_000
DV_CELL_WORK_CAP = 2_000_000
MAX_ROW, MAX_COL = 1_048_576, 16_384  # Excel's grid
CONVENTION_SHARE = (
    0.70  # a style counts as "the convention" when 70%+ of cells of that kind use it
)
MIN_ROLE_CELLS = 5  # fewer cells than this is too few to infer a convention from
FRAGMENT_MIN = (
    20  # one highlight rule split into 20+ pieces is copy-paste bloat, not design
)
DATA_MIN_ROWS = (
    20  # a tab with 20+ rows of typed values and under 10% formulas is raw data
)
DATA_MAX_FORMULA_SHARE = 0.10
FREEZE_MIN_ROWS = 40  # past ~40 rows the header row scrolls off a laptop screen
LONG_FORMULA_CHARS = 250  # longer than this is hard to check by eye
MAX_IF_NESTING = (
    4  # IF inside IF inside IF inside IF; past this a lookup table is clearer
)
TABLE_COVER_SHARE = (
    0.5  # a fixed range covering half a Table's rows is standing in for the Table
)

ERRORS = {
    "#REF!",
    "#DIV/0!",
    "#VALUE!",
    "#N/A",
    "#NAME?",
    "#NULL!",
    "#NUM!",
    "#SPILL!",
    "#CALC!",
}

# Numbers that are unit conversions or identities, not business assumptions.
OK_NUMBERS = {0, 1, 4, 7, 12, 24, 30, 31, 52, 60, 100, 365, 366, 1000, 1_000_000}
# Working days per year: a convention, not worth flagging - unless the model uses more than one of them.
WORKDAYS = {250, 252, 260, 261, 262}
# Plain-language guesses for common typed-in numbers (shown as "often ...").
NUMBER_HINTS = {
    0.85: "a productivity or efficiency rate",
    0.9: "a utilization or retention rate",
    0.95: "a quality or service level",
    1.03: "3% growth or escalation",
    1.05: "5% growth or escalation",
    1.1: "10% growth or a markup",
    8: "hours per workday",
    40: "hours per week",
    22: "working days per month",
    2080: "working hours per year",
    1.0e3: "a units conversion",
}
# Function arguments that are positions/flags, not assumptions (0-based argument index).
POSITIONAL = {
    "VLOOKUP": {2, 3},
    "HLOOKUP": {2, 3},
    "INDEX": {1, 2, 3},
    "MATCH": {2},
    "XMATCH": {2, 3},
    "XLOOKUP": {4, 5},
    "OFFSET": {1, 2, 3, 4},
    "ROUND": {1},
    "ROUNDUP": {1},
    "ROUNDDOWN": {1},
    "LEFT": {1},
    "RIGHT": {1},
    "MID": {1, 2},
    "CHOOSE": {0},
    "LARGE": {1},
    "SMALL": {1},
    "RANK": {2},
    "RANK.EQ": {2},
    "WEEKDAY": {1},
    "EOMONTH": {1},
    "EDATE": {1},
    "DATE": {0, 1, 2},
    "SUBTOTAL": {0},
    "AGGREGATE": {0, 1},
    "IFERROR": {1},
    "IFNA": {1},
    "TEXT": {1},
    "FIXED": {1},
    "SEQUENCE": {0, 1, 2, 3},
    "TAKE": {1, 2},
    "DROP": {1, 2},
    "CHOOSECOLS": {1, 2, 3},
    "CHOOSEROWS": {1, 2, 3},
    "PERCENTILE": {1},
    "QUARTILE": {1},
    "MOD": {1},
    "POWER": {1},
    "LOG": {1},
    "WORKDAY": {1},
    "DATEDIF": {2},
}
VOLATILE = ("OFFSET", "INDIRECT")
PCT_WORDS = re.compile(
    r"%|percent|pct|\brate\b|margin|growth|discount|share|\bmix\b|yield", re.I
)
