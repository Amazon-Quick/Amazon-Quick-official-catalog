"""
description: Infer a variance line's type (revenue, cost, profit, ratio, per_unit or metric) from its name, and label its variance favorable (F) or unfavorable (U) by type, never from the sign alone.
last_updated: 2026-11-24

Pure functions with no file access. variance_check imports them.
"""

import re

LINE_TYPES = ("revenue", "cost", "profit", "ratio", "per_unit", "metric")
FAVORABLE_VALUES = ("higher", "lower", "neutral")
DEFAULT_FAVORABLE = {"revenue": "higher", "profit": "higher", "cost": "lower"}

COST_WORDS = re.compile(
    r"\b(cost|costs|expense|expenses|opex|cogs|spend|fees?|salar|wage|payroll|rent|depreciation|amortization|tax|interest expense|headcount cost|contractor|travel|licen[cs]e)",
    re.I,
)
REVENUE_WORDS = re.compile(
    r"\b(revenue|sales|income from|bookings|billings|gmv|arr|mrr)\b", re.I
)
# A name that ends in a revenue word is revenue even when it contains a cost word,
# for example "License revenue", "Fee income" or "Rental income".
REVENUE_END = re.compile(r"\b(?:revenue|income|sales)\s*$", re.I)
COST_OF = re.compile(r"\bcost of\b", re.I)
PROFIT_WORDS = re.compile(
    r"\b(gross profit|operating income|ebit|ebitda|net income|profit|contribution|operating profit)\b",
    re.I,
)
RATIO_WORDS = re.compile(r"(%|\bmargin\b|\bratio\b)", re.I)
PER_UNIT_WORDS = re.compile(
    r"(\baverage\b|\bper\b|\bavg\b|\baov\b|\basp\b|\brate\b|/)", re.I
)
MARGIN_WORD = re.compile(r"\bmargin\b", re.I)


def infer_type(name):
    """Infer a line's type from its name; the user confirms it in the workflow."""
    if RATIO_WORDS.search(name):
        return "ratio"
    if PER_UNIT_WORDS.search(name):
        return "per_unit"
    if PROFIT_WORDS.search(name):
        return "profit"
    if COST_OF.search(name):
        return "cost"
    if REVENUE_END.search(name):
        return "revenue"
    if COST_WORDS.search(name):
        return "cost"
    if REVENUE_WORDS.search(name):
        return "revenue"
    return "metric"


def direction(row):
    """F, U, flat, neutral, n/a, or ask (when the favorable direction is unknown)."""
    var = row["variance"]
    if var is None:
        return "n/a"
    if var == 0:
        return "flat"
    fav = row["favorable_when"]
    if fav == "neutral":
        return "neutral"
    if not fav:
        fav = DEFAULT_FAVORABLE.get(row["type"])
    if not fav and row["type"] == "ratio" and MARGIN_WORD.search(row["line"]):
        fav = "higher"
    if not fav:
        return "ask"
    return "F" if (var > 0) == (fav == "higher") else "U"
