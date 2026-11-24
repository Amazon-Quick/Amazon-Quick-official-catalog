"""
description: Unit tests for the trend-change test in trend_analysis, run through series_review.run with no workbook. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime as dt
import unittest

import series_review as sr


def trend(values: list) -> dict:
    dates = [f"{2021 + i // 12}-{i % 12 + 1:02d}-01" for i in range(len(values))]
    res = sr.run(
        {"Revenue": {"dates": dates, "values": values}},
        freq="monthly",
        analyses=("trend",),
        today=dt.date(2026, 11, 24),
    )
    return res["trends"][0]


class TestTrendChange(unittest.TestCase):
    def test_straight_line_in_amounts_is_not_called_slowing(self) -> None:
        self.assertIsNone(trend([1000.0 + 20 * m for m in range(36)])["trend_change"])

    def test_a_real_change_in_amount_added_is_reported(self) -> None:
        values = [1000.0 + 5 * m for m in range(24)] + [
            1115.0 + 60 * m for m in range(1, 25)
        ]
        change = trend(values)["trend_change"]
        self.assertIsNotNone(change)
        self.assertEqual(change["word"], "Picked up")


if __name__ == "__main__":
    unittest.main()
