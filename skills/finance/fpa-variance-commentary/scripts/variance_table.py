"""
description: Parse a pasted CSV or Markdown variance table into rows, find its columns by alias, and read money cells such as '$1,234', '(1,234)' or '1.2M'.
last_updated: 2026-11-24

Pure functions with no file access. variance_check and variance_rvm import them.
"""

import csv
import math
import re
from io import StringIO

# Column names accepted for each field, matched case-insensitively.
ALIASES = {
    "line": [
        "line",
        "line item",
        "metric",
        "account",
        "description",
        "category",
        "item",
    ],
    "actual": ["actual", "actuals", "act", "current"],
    "comparison": [
        "comparison",
        "budget",
        "plan",
        "forecast",
        "prior",
        "prior period",
        "prior_period",
        "prior year",
        "prior_year",
        "py",
        "ly",
        "last year",
        "target",
        "op",
        "outlook",
    ],
    "variance": ["variance", "var", "delta", "diff", "difference"],
    "type": ["type", "line type", "kind"],
    "parent": ["parent", "rolls up to", "parent line"],
    "rollup": ["rollup", "roll-up", "sign"],
    "favorable_when": ["favorable_when", "favorable when", "favourable when"],
    "formula": ["formula", "computed as", "ratio of"],
    # rate / volume / mix
    "segment": ["segment", "product", "line", "category"],
    "actual_units": ["actual_units", "actual units", "act units", "actual volume"],
    "comparison_units": [
        "comparison_units",
        "budget_units",
        "plan_units",
        "forecast_units",
        "prior_units",
        "prior_year_units",
        "comparison units",
        "budget units",
        "plan units",
        "prior units",
    ],
    "actual_rate": [
        "actual_rate",
        "actual rate",
        "act rate",
        "actual price",
        "actual asp",
    ],
    "comparison_rate": [
        "comparison_rate",
        "budget_rate",
        "plan_rate",
        "forecast_rate",
        "prior_rate",
        "prior_year_rate",
        "comparison rate",
        "budget rate",
        "plan rate",
        "prior rate",
    ],
}

EMPTY_CELLS = ("", "-", "--", "n/a", "N/A", "na", "NA")
SCALE_SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9}
DECIMALS = re.compile(r"\.(\d+)")
SEPARATOR_CELL = re.compile(r"[-:\s]*")


def decimals(value):
    """Decimal places shown in a raw cell, for example '1,234.5' -> 1, '(300)' -> 0."""
    m = DECIMALS.search(str(value or ""))
    return len(m.group(1)) if m else 0


def clean_num(value):
    """Parse '$1,234', '(1,234)', '1.2M', '-5%' into a finite float, or None."""
    if value is None:
        return None
    s = str(value).strip()
    if s in EMPTY_CELLS:
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = (
        s.strip("()")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace(",", "")
        .replace("%", "")
        .strip()
    )
    mult = 1.0
    if s and s[-1].lower() in SCALE_SUFFIX:
        mult = SCALE_SUFFIX[s[-1].lower()]
        s = s[:-1]
    try:
        n = float(s) * mult
    except ValueError:
        return None
    if not math.isfinite(n):
        return None
    return -n if neg else n


def parse_table(text):
    """Return (header, rows) for a CSV or Markdown table; header names are lowercased."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if lines and sum(ln.lstrip().startswith("|") for ln in lines) > len(lines) // 2:
        rows, header = [], None
        for ln in lines:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if all(SEPARATOR_CELL.fullmatch(c) for c in cells):
                continue
            if header is None:
                header = [c.lower() for c in cells]
            else:
                # Markdown rows can be shorter than the header, so strict=True would raise.
                rows.append(dict(zip(header, cells, strict=False)))
        return header or [], rows
    reader = csv.DictReader(StringIO(text.strip()))
    rows = [{(k or "").strip().lower(): v for k, v in r.items()} for r in reader]
    return [(h or "").strip().lower() for h in (reader.fieldnames or [])], rows


def find_col(header, key):
    """The first alias of `key` present in `header`, or None."""
    for alias in ALIASES[key]:
        if alias in header:
            return alias
    return None
