"""
description: Unit tests for pir_values: amount and period parsing, including the bounded period regex.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import time
import unittest
from decimal import Decimal

from pir_values import D, _parse_period, fiscal


class TestValues(unittest.TestCase):
    def test_amounts_parse_with_commas_and_parentheses(self) -> None:
        self.assertEqual(D("$1,250.50"), Decimal("1250.50"))
        self.assertEqual(D("(40)"), Decimal("-40"))
        self.assertIsNone(D("n/a"))

    def test_quarter_labels_parse(self) -> None:
        self.assertEqual(_parse_period("Q4 FY2026"), ("quarter", 2026, 4))
        self.assertEqual(_parse_period("2026-Q1"), ("quarter", 2026, 1))
        self.assertIsNone(_parse_period("Q4"))

    def test_long_whitespace_period_returns_quickly(self) -> None:
        start = time.perf_counter()
        self.assertIsNone(_parse_period("Q1" + " " * 5000 + "x"))
        self.assertLess(time.perf_counter() - start, 0.5)

    def test_fiscal_start_month_shifts_quarters(self) -> None:
        self.assertEqual(fiscal("2026-02", 2), ("FY2027", "FY2027-Q1"))
        self.assertEqual(fiscal("2026-02", 1), ("FY2026", "FY2026-Q1"))


if __name__ == "__main__":
    unittest.main()
