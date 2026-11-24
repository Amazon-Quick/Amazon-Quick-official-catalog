"""
description: Unit test for history_prep.prepare: gap count after trimming (RUN-3), ambiguous dates and duplicate periods reported as issues, and pandas-style date columns accepted (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import math
import unittest

from history_prep import prepare

DATES = [f"{2024 + i // 12}-{i % 12 + 1:02d}-01" for i in range(24)]


class TestPrepare(unittest.TestCase):
    def test_trailing_blank_is_not_counted_as_a_gap(self) -> None:
        values = [100.0 + i for i in range(24)]
        values[10] = math.nan
        values[-1] = math.nan
        issues = prepare({"Rev": {"dates": DATES, "values": values}}, "MS")["issues"]
        self.assertIn(
            "Rev: 1 gap inside the history (treated as missing, not zero)", issues
        )

    def test_ambiguous_dates_skip_the_series_with_an_issue(self) -> None:
        dates = [f"01/{m:02d}/2024" for m in range(1, 13)]
        out = prepare({"S": {"dates": dates, "values": [1.0] * 12}}, "MS")
        self.assertEqual(out["series"], {})
        self.assertIn("date_order", out["issues"][0])

    def test_confirmed_day_first_dates_are_read(self) -> None:
        dates = [f"01/{m:02d}/2024" for m in range(1, 13)]
        out = prepare(
            {"S": {"dates": dates, "values": [1.0] * 12}}, "MS", date_order="DMY"
        )
        self.assertEqual(out["series"]["S"]["dates"][-1].month, 12)

    def test_duplicate_periods_are_reported(self) -> None:
        dates = DATES[:10] + DATES[9:10]
        out = prepare({"S": {"dates": dates, "values": [1.0] * 11}}, "MS")
        self.assertEqual(out["series"], {})

    def test_tuple_dates_are_accepted(self) -> None:
        out = prepare(
            {
                "S": {
                    "dates": tuple(DATES),
                    "values": tuple(float(i) for i in range(24)),
                }
            },
            "MS",
        )
        self.assertIn("S", out["series"])


if __name__ == "__main__":
    unittest.main()
