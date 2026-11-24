"""
description: Unit tests for quick_runner's input refusal, slug, timestamp and intake-context helpers. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import quick_runner  # noqa: E402


class TestCheckInput(unittest.TestCase):
    def test_unsupported_types_are_refused_before_any_copy(self) -> None:
        for name in ("budget.xls", "budget.xlsb", "export.csv", "notes"):
            with self.subTest(name=name), self.assertRaises(ValueError) as err:
                quick_runner._check_input(f"/nonexistent/{name}")
            self.assertIn("save the workbook as .xlsx", str(err.exception))

    def test_supported_type_that_does_not_exist_names_only_the_file(self) -> None:
        with self.assertRaises(ValueError) as err:
            quick_runner._check_input("/nonexistent/folder/model.xlsx")
        self.assertEqual(str(err.exception), "File not found: model.xlsx")
        self.assertNotIn("/nonexistent", str(err.exception))


class TestSlug(unittest.TestCase):
    def test_spaces_and_symbols_become_underscores(self) -> None:
        self.assertEqual(quick_runner._slug("FY26 Budget (v2)"), "FY26_Budget_v2")

    def test_empty_name_falls_back_to_model(self) -> None:
        self.assertEqual(quick_runner._slug("()"), "model")


class TestNow(unittest.TestCase):
    def test_unknown_timezone_falls_back_to_utc(self) -> None:
        self.assertTrue(quick_runner._now("Not/AZone").endswith("UTC"))

    def test_no_timezone_is_utc(self) -> None:
        self.assertTrue(quick_runner._now(None).endswith("UTC"))


class TestJsonName(unittest.TestCase):
    def test_paths_are_refused(self) -> None:
        for name in ("../escape", "a/b", "/abs", "Decisions", "", "x" * 41):
            with self.subTest(name=name), self.assertRaises(ValueError):
                quick_runner._json_name(name)

    def test_working_file_names_are_accepted(self) -> None:
        self.assertEqual(
            quick_runner._json_name("compare_narrative"), "compare_narrative.json"
        )


class TestContextFields(unittest.TestCase):
    def test_only_user_answer_fields_are_accepted(self) -> None:
        self.assertEqual(
            quick_runner.CONTEXT_FIELDS, ("headers", "date_order", "unit_notes")
        )


if __name__ == "__main__":
    unittest.main()
