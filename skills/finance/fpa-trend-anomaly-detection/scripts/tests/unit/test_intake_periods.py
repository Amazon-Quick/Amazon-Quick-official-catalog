"""
description: Unit tests for intake_periods. Filesystem-free: dates and labels are passed in directly.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime as dt
import unittest

from intake_periods import _last_full_period, parse_period


class TestParsePeriod(unittest.TestCase):
    def test_ambiguous_numeric_date_needs_an_order(self) -> None:
        self.assertIsNone(parse_period("01/04/2025"))
        self.assertEqual(parse_period("01/04/2025", "DMY"), dt.date(2025, 4, 1))
        self.assertEqual(parse_period("01/04/2025", "MDY"), dt.date(2025, 1, 4))

    def test_iso_date_needs_no_order(self) -> None:
        self.assertEqual(parse_period("2025-03-01"), dt.date(2025, 3, 1))


class TestLastFullPeriod(unittest.TestCase):
    def test_no_finished_period_when_every_date_is_in_the_future(self) -> None:
        dates = [dt.date(2030, m, 1) for m in range(1, 13)]
        self.assertLess(_last_full_period(dates, "MS", dt.date(2026, 11, 24)), 0)


if __name__ == "__main__":
    unittest.main()
