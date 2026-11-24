"""
description: Unit tests for plan_values: numbers and dates stored as text become real values, ambiguous dates go to the user, and extra spaces are trimmed. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plan_changes as PC  # noqa: E402
import plan_values as VAL  # noqa: E402
from workbook_fixtures import workbook_bytes  # noqa: E402


def finding(check, cell, sheet="S"):
    return {
        "id": "F-1",
        "check": check,
        "sheet": sheet,
        "cell": cell,
        "severity": "warning",
        "description": "d",
        "fix": "scan fix",
    }


def planner(values):
    def build(ws, wb):
        ws.title = "S"
        for i, v in enumerate(values, start=1):
            ws.cell(i, 1, v)

    return PC.Planner(workbook_bytes(build), {"findings": []}, {})


def converted(p):
    return [e["value"] for c in p.changes for e in c["edits"]]


class TestTextToValue(unittest.TestCase):
    def test_numbers_in_text_keep_sign_and_percent(self) -> None:
        p = planner(["(1,234)", "12.5%", "-7"])
        VAL.text_to_value(p, finding("number_as_text", "A1:A3"), "number")
        self.assertEqual(converted(p), [-1234, 0.125, -7])

    def test_iso_date_text_becomes_an_excel_serial(self) -> None:
        p = planner(["2024-01-15"])
        VAL.text_to_value(p, finding("date_as_text", "A1"), "date")
        self.assertEqual(converted(p), [45306])

    def test_ambiguous_slash_date_goes_to_the_user(self) -> None:
        p = planner(["03/04/2024"])
        VAL.text_to_value(p, finding("date_as_text", "A1"), "date")
        self.assertEqual(p.changes, [])
        self.assertIn("day/month/year", p.manual[0]["recommendation"])


class TestSpaces(unittest.TestCase):
    def test_lookup_keys_are_trimmed_with_confirm_risk(self) -> None:
        p = planner([" ACME ", "Beta"])
        VAL.fix_spaces(p, finding("lookup_key_spaces", "A1:A2"))
        self.assertEqual(converted(p), ["ACME"])
        self.assertEqual(p.changes[0]["risk"], "confirm")


if __name__ == "__main__":
    unittest.main()
