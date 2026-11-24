"""
description: Unit tests for intake_cells._coerce and _untrusted. Filesystem-free: cell strings are passed in directly.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import time
import unittest

from intake_cells import _coerce, _untrusted


class TestCoerce(unittest.TestCase):
    def test_reads_thousands_separators_brackets_and_percent(self) -> None:
        self.assertEqual(_coerce("1,234.5"), 1234.5)
        self.assertEqual(_coerce("(1,234)"), -1234.0)
        self.assertEqual(_coerce("-$5"), -5.0)
        self.assertAlmostEqual(_coerce("12%"), 0.12)

    def test_decimal_comma_stays_text_so_intake_asks(self) -> None:
        self.assertEqual(_coerce("12,5"), "12,5")
        self.assertEqual(_coerce("1,5%"), "1,5%")

    def test_reads_any_currency_symbol_but_not_letters(self) -> None:
        self.assertEqual(_coerce("¥1,200"), 1200.0)
        self.assertEqual(_coerce("₹50"), 50.0)
        self.assertEqual(_coerce("x50"), "x50")

    def test_long_digit_run_returns_quickly(self) -> None:
        start = time.perf_counter()
        _coerce("1" * 32000 + "x")
        _coerce("1" * 39 + "x")
        self.assertLess(time.perf_counter() - start, 0.05)


class TestUntrusted(unittest.TestCase):
    def test_preview_is_labeled_and_bounded(self) -> None:
        text = _untrusted("A" * 5200)
        self.assertTrue(text.startswith("untrusted cell value "))
        self.assertLess(len(text), 160)


if __name__ == "__main__":
    unittest.main()
