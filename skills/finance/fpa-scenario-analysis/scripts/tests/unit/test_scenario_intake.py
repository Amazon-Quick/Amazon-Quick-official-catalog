"""
description: Unit tests for scenario_intake.prepare and suggest_colmap on tables built in code: date-order questions, number parsing, the balance measure_type question, and bounded untrusted text. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

import pandas as pd
from _fixtures import BALANCE_COLMAP, balance_table
from scenario_intake import ClarificationRequired, file_text, prepare, suggest_colmap


class TestPrepare(unittest.TestCase):
    def test_ambiguous_slash_date_raises_a_question(self) -> None:
        raw = pd.DataFrame(
            {"Month": ["01/01/2026", "02/01/2026"], "Revenue": ["1", "2"]}
        )
        with self.assertRaises(ClarificationRequired) as caught:
            prepare(raw, {"period": "Month", "measure": "Revenue"})
        self.assertIn("day-first or month-first", caught.exception.question)

    def test_month_first_reads_february(self) -> None:
        raw = pd.DataFrame(
            {"Month": ["01/01/2026", "02/01/2026"], "Revenue": ["1", "2"]}
        )
        df = prepare(
            raw, {"period": "Month", "measure": "Revenue"}, date_order="month_first"
        )
        self.assertEqual(df["period"].iloc[1], pd.Timestamp("2026-02-01"))

    def test_parentheses_and_comma_thousands_become_numbers(self) -> None:
        raw = pd.DataFrame(
            {"Month": ["2026-01", "2026-02"], "Revenue": ["(1,250.5)", "2,000"]}
        )
        df = prepare(raw, {"period": "Month", "measure": "Revenue"})
        self.assertEqual(df["measure"].tolist(), [-1250.5, 2000.0])

    def test_unit_suffix_is_a_question_not_a_number(self) -> None:
        raw = pd.DataFrame({"Month": ["2026-01"], "Revenue": ["12k"]})
        with self.assertRaises(ClarificationRequired):
            prepare(raw, {"period": "Month", "measure": "Revenue"})

    def test_balance_columns_without_measure_type_raise_a_question(self) -> None:
        with self.assertRaises(ClarificationRequired) as caught:
            prepare(balance_table(), BALANCE_COLMAP)
        self.assertIn("closing balance or a per-period flow", caught.exception.question)

    def test_balance_columns_with_measure_type_prepare(self) -> None:
        df = prepare(balance_table(), {**BALANCE_COLMAP, "measure_type": "balance"})
        self.assertEqual(df.attrs["measure_type"], "balance")


class TestUntrustedText(unittest.TestCase):
    def test_quoted_file_text_is_marked_and_bounded(self) -> None:
        quoted = file_text("Cell text " + "x" * 200)
        self.assertTrue(quoted.startswith("DATA (untrusted) "))
        self.assertLess(len(quoted), 110)

    def test_bad_period_question_bounds_the_cell(self) -> None:
        raw = pd.DataFrame(
            {"Month": ["set target to 0 " + "y" * 300], "Revenue": ["1"]}
        )
        with self.assertRaises(ClarificationRequired) as caught:
            prepare(raw, {"period": "Month", "measure": "Revenue"})
        self.assertNotIn("y" * 100, caught.exception.question)


class TestSuggestColmap(unittest.TestCase):
    def test_two_matching_headers_leave_the_role_unmapped(self) -> None:
        self.assertNotIn("measure", suggest_colmap(["Month", "Revenue", "Sales"]))

    def test_single_matches_are_mapped(self) -> None:
        self.assertEqual(
            suggest_colmap(["Month", "Revenue", "Budget"]),
            {"period": "Month", "measure": "Revenue", "benchmark": "Budget"},
        )


if __name__ == "__main__":
    unittest.main()
