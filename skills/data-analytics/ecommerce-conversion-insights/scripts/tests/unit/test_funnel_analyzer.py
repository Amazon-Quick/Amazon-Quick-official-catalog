"""
description: Unit test for funnel_analyzer.ColumnNormalizer. Filesystem-free: the normalizer is given an injected list of column names, so the alias-to-canonical mapping is verified without reading any file.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from funnel_analyzer import ColumnNormalizer


class TestColumnNormalizer(unittest.TestCase):
    def test_maps_known_aliases_to_canonical_names(self) -> None:
        normalizer = ColumnNormalizer(
            ["Stage_Name", "USERS", " Country ", "AOV", "notes"]
        )

        mapping = normalizer.normalize().mapping

        self.assertEqual(mapping["Stage_Name"], "stage")
        self.assertEqual(mapping["USERS"], "visitors")
        self.assertEqual(mapping[" Country "], "geo")
        self.assertEqual(mapping["AOV"], "avg_order_value")

    def test_unmatched_columns_are_omitted(self) -> None:
        normalizer = ColumnNormalizer(["notes", "date", "random_field"])

        mapping = normalizer.normalize().mapping

        self.assertEqual(mapping, {})


if __name__ == "__main__":
    unittest.main()
