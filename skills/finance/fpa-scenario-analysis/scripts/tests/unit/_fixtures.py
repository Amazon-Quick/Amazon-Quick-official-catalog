"""
description: Shared inputs built in code for the unit tests: a nine-month revenue history against a twelve-month plan, and a balance roll-forward. No file is read.
last_updated: 2026-11-24
"""

import pandas as pd

REVENUE = [100.0, 112, 101, 108, 97, 109, 104, 111, 99]
UNITS = {"units": "USD thousands"}


def revenue_table() -> pd.DataFrame:
    """Nine months of actuals and a complete twelve-month plan of 105 per month."""
    months = pd.date_range("2026-01-01", periods=12, freq="MS")
    return pd.DataFrame(
        {"Month": months, "Revenue": REVENUE + [None] * 3, "Budget": [105.0] * 12}
    )


def balance_table() -> pd.DataFrame:
    """Nine months of a backlog roll-forward whose openings match the prior closings."""
    table = pd.DataFrame(
        {
            "period": pd.date_range("2026-01-01", periods=9, freq="MS"),
            "inflow": [100.0, 104, 98, 110, 107, 112, 109, 115, 111],
            "outflow": [90.0] * 9,
        }
    )
    table["opening"] = [500.0] + list(
        (500 + (table["inflow"] - table["outflow"]).cumsum())[:-1]
    )
    table["closing"] = table["opening"] + table["inflow"] - table["outflow"]
    return table


REVENUE_COLMAP = {"period": "Month", "measure": "Revenue", "benchmark": "Budget"}
BALANCE_COLMAP = {
    "period": "period",
    "measure": "closing",
    "opening": "opening",
    "inflow": "inflow",
    "outflow": "outflow",
}
