"""
description: Unit tests for pir_columns: header synonyms and table type detection, from in-memory column lists.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_columns import detect_table_type, map_col


class TestColumns(unittest.TestCase):
    def test_map_col_maps_known_synonyms(self) -> None:
        self.assertEqual(map_col("Req ID"), "id")
        self.assertEqual(map_col("CC"), "cost_center")
        self.assertEqual(map_col("Unknown Header"), "unknown_header")

    def test_commitments_table_is_not_read_as_side_by_side_budget(self) -> None:
        cols = ["po", "cost_center", "account", "period", "po_amount", "invoiced"]
        self.assertEqual(detect_table_type(cols), "commitments")

    def test_side_by_side_budget_still_detected(self) -> None:
        cols = [
            "cost_center",
            "account",
            "period",
            "budget_amount",
            "actual_amount",
            "open_commitments",
        ]
        self.assertEqual(detect_table_type(cols), "budget_wide")

    def test_quote_table_linked_to_request_reads_as_quotes(self) -> None:
        cols = ["quote_id", "id", "vendor", "amount", "valid_until"]
        self.assertEqual(detect_table_type(cols), "quotes")

    def test_request_table_stays_requests(self) -> None:
        self.assertEqual(
            detect_table_type(["id", "vendor", "amount", "date"]), "requests"
        )


if __name__ == "__main__":
    unittest.main()
