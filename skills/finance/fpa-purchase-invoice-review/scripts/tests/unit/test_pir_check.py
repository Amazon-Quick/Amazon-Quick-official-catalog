"""
description: Unit tests for pir_check: run() returns errors as data and names the right program.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import pir_check


class TestCheck(unittest.TestCase):
    def test_bad_subcommand_returns_error_with_program_name(self) -> None:
        res = pir_check.run(["nope"])
        self.assertFalse(res["ok"])
        self.assertIn("pir_check.py: error", res["error"])

    def test_column_map_must_be_an_object(self) -> None:
        res = pir_check.run(["all", "--input", "-", "--column-map", "[1, 2]"])
        self.assertFalse(res["ok"])
        self.assertIn("--column-map", res["error"])

    def test_fiscal_start_month_out_of_range_is_rejected(self) -> None:
        res = pir_check.run(["all", "--input", "-", "--fiscal-start-month", "13"])
        self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
