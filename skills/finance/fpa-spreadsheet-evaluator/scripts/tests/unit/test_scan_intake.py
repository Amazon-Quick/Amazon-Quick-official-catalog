"""
description: Unit tests for scan_intake: date text is read in every valid order, and ambiguous dates or unit findings become questions unless the user already confirmed them. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_findings import Findings  # noqa: E402
from scan_intake import assess_intake, date_options  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402


def _dates_book(ws, wb):
    ws["A1"], ws["B1"] = "Date", "Amount"
    ws["A2"], ws["B2"] = "03/04/2025", 10


class TestDateOptions(unittest.TestCase):
    def test_slash_dates_return_every_valid_order(self):
        self.assertEqual(set(date_options("03/04/2025")), {"MDY", "DMY"})
        self.assertEqual(set(date_options("13/04/2025")), {"DMY"})
        self.assertEqual(set(date_options("2025-03-04")), {"ISO"})
        self.assertEqual(date_options("31/02/2025"), {})


class TestAssessIntake(unittest.TestCase):
    def test_ambiguous_date_column_asks_for_the_date_order(self):
        result = assess_intake(load(workbook_bytes(_dates_book)), [], {})
        self.assertEqual(result["status"], "needs_clarification")
        q = result["questions"][0]
        self.assertEqual(q["kind"], "date_order")
        self.assertEqual(q["cells"], ["Sheet!A2"])
        self.assertEqual(result["coverage"][0]["unscanned_filled_cells"], 0)

    def test_confirmed_date_order_resolves_the_question(self):
        context = {"date_order": {"Sheet": "DMY"}}
        result = assess_intake(load(workbook_bytes(_dates_book)), [], context)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["questions"], [])

    def test_unit_finding_without_a_note_asks_about_units(self):
        def build(ws, wb):
            ws["A1"], ws["B1"] = "Item", "Amount"
            ws["A2"], ws["B2"] = "Rent", 10

        fs = Findings()
        fs.add("mixed_units", "Sheet", "B2", "Some cells in thousands")
        wb = load(workbook_bytes(build))
        result = assess_intake(wb, fs.items, {})
        self.assertEqual([q["kind"] for q in result["questions"]], ["units"])
        self.assertEqual(result["questions"][0]["cells"], ["Sheet!B2"])
        noted = assess_intake(wb, fs.items, {"unit_notes": {"Sheet": "USD"}})
        self.assertEqual(noted["status"], "ready")


if __name__ == "__main__":
    unittest.main()
