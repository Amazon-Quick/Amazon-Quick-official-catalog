"""
description: Unit tests for scan_limits: the shared limits stay consistent with each other and the word lists match the labels they are meant for. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import scan_limits  # noqa: E402


class TestLimits(unittest.TestCase):
    def test_scan_caps_fit_inside_excel_and_archive_limits(self):
        self.assertLessEqual(scan_limits.ROW_CAP, scan_limits.MAX_ROW)
        self.assertLessEqual(scan_limits.COL_CAP, scan_limits.MAX_COL)
        self.assertLessEqual(
            scan_limits.ARCHIVE_MEMBER_CAP, scan_limits.ARCHIVE_SIZE_CAP
        )
        self.assertTrue(0.5 < scan_limits.CONVENTION_SHARE < 1)

    def test_percent_words_match_rate_labels_but_not_lookalike_words(self):
        for label in ("Growth %", "Tax rate", "Gross margin", "Discount"):
            with self.subTest(label=label):
                self.assertIsNotNone(scan_limits.PCT_WORDS.search(label))
        for label in ("Rated capacity", "Revenue", "Headcount"):
            with self.subTest(label=label):
                self.assertIsNone(scan_limits.PCT_WORDS.search(label))

    def test_lookup_column_index_is_positional_not_an_assumption(self):
        self.assertIn(2, scan_limits.POSITIONAL["VLOOKUP"])
        self.assertNotIn(0, scan_limits.POSITIONAL["VLOOKUP"])
        self.assertIn("#REF!", scan_limits.ERRORS)
        self.assertIn(12, scan_limits.OK_NUMBERS)


if __name__ == "__main__":
    unittest.main()
