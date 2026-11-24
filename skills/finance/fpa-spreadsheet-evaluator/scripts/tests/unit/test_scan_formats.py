"""
description: Unit tests for scan_formats: number-like text recognition stays bounded on long whitespace. Filesystem-free.
last_updated: 2026-11-24
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_formats import numeric_text  # noqa: E402
from workbook_fixtures import SLOW_SECONDS  # noqa: E402


class TestNumericText(unittest.TestCase):
    def test_numeric_text_is_bounded_on_long_whitespace(self):
        start = time.time()
        self.assertFalse(numeric_text("1" + " " * 32000 + "x"))
        self.assertLess(time.time() - start, SLOW_SECONDS)

    def test_numeric_text_recognizes_numbers_and_rejects_words(self):
        self.assertTrue(numeric_text(" (1,234.50) "))
        self.assertFalse(numeric_text("12 apples"))


if __name__ == "__main__":
    unittest.main()
