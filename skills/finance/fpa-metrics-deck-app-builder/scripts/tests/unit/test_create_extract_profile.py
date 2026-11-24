"""
description: Unit tests for create_extract_profile. Filesystem-free: pandas chunks constructed in the test are passed to ChunkProfiler, and its profile to ProfileSummary.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

import pandas as pd
from create_extract_profile import (
    ChunkProfiler,
    ProfileInputError,
    ProfileRequest,
    ProfileSummary,
)


def _chunks() -> list[pd.DataFrame]:
    first = pd.DataFrame(
        {
            "entity": ["A", "B"],
            "period": ["2026-09-30", "2026-10-31"],
            "amount": ["1.5", None],
        },
        dtype=str,
    )
    second = pd.DataFrame(
        {
            "entity": ["B", "C"],
            "period": ["2026-08-31", "not a date"],
            "amount": ["2.0", "3.0"],
        },
        dtype=str,
    )
    return [first, second]


class TestChunkProfiler(unittest.TestCase):
    def test_counts_rows_and_distinct_keys_across_chunks(self) -> None:
        profile = ChunkProfiler(
            _chunks(), ProfileRequest(key_columns=["entity"])
        ).profile()

        self.assertEqual(profile.row_count, 4)
        self.assertEqual(profile.keys[0].distinct_count, 3)
        self.assertFalse(profile.keys[0].capped)

    def test_reports_the_date_range_and_unparsed_dates(self) -> None:
        request = ProfileRequest(key_columns=[], date_column="period")

        profile = ChunkProfiler(_chunks(), request).profile()

        self.assertEqual(profile.date_min, "2026-08-31")
        self.assertEqual(profile.date_max, "2026-10-31")
        self.assertEqual(profile.unparsed_dates, 1)

    def test_reports_null_rates(self) -> None:
        profile = ChunkProfiler(_chunks(), ProfileRequest(key_columns=[])).profile()

        amount = next(column for column in profile.columns if column.name == "amount")
        self.assertEqual(amount.null_count, 1)
        self.assertAlmostEqual(amount.null_rate, 0.25)

    def test_missing_key_column_raises(self) -> None:
        with self.assertRaises(ProfileInputError):
            ChunkProfiler(
                _chunks(), ProfileRequest(key_columns=["cost_center"])
            ).profile()


class TestProfileSummary(unittest.TestCase):
    def test_summary_prints_counts_not_row_values(self) -> None:
        profile = ChunkProfiler(
            _chunks(), ProfileRequest(key_columns=["entity"])
        ).profile()

        summary = ProfileSummary(profile).build()

        self.assertIn("Rows: 4", summary)
        self.assertIn("Distinct entity: 3", summary)
        self.assertNotIn("1.5", summary)

    def test_summary_strips_unprintable_characters_from_column_names(self) -> None:
        chunk = pd.DataFrame({"amount\x1b[31m": [None]}, dtype=str)
        profile = ChunkProfiler([chunk], ProfileRequest(key_columns=[])).profile()

        summary = ProfileSummary(profile).build()

        self.assertNotIn("\x1b", summary)

    def test_summary_neutralizes_markdown_in_column_names(self) -> None:
        chunk = pd.DataFrame({"a|b`# x" + "z" * 200: [None]}, dtype=str)
        profile = ChunkProfiler([chunk], ProfileRequest(key_columns=[])).profile()

        summary = ProfileSummary(profile).build()

        self.assertNotIn("|", summary)
        self.assertNotIn("`", summary)
        self.assertNotIn("z" * 100, summary)


if __name__ == "__main__":
    unittest.main()
