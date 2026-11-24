"""
description: Unit tests for scan_checks_integrity: period header gaps, exact duplicate rows on a data tab, and default tab names. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_checks_integrity import check_data_integrity, check_structure  # noqa: E402
from scan_findings import Findings  # noqa: E402
from workbook_fixtures import load, prepare_finance, workbook_bytes  # noqa: E402


def scan_integrity(build):
    wb = load(workbook_bytes(build))
    prepare_finance(wb)
    fs = Findings()
    check_data_integrity(wb, fs, False)
    return fs.items


class TestDataIntegrity(unittest.TestCase):
    def test_repeated_period_header_is_reported(self):
        def build(ws, wb):
            for col, head in zip(
                "ABCDE", ("Line", "Q1", "Q2", "Q2", "Q3"), strict=True
            ):
                ws[f"{col}1"] = head
            ws["A2"], ws["B2"] = "Sales", 1

        found = [i for i in scan_integrity(build) if i["check"] == "period_header_gap"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["cell"], "D1")
        self.assertIn("Q2 appears twice", found[0]["description"])

    def test_exact_duplicate_row_on_data_tab_is_reported_once(self):
        def build(ws, wb):
            ws.append(["Invoice", "Region", "Amount"])
            for i in range(1, 26):
                ws.append([f"INV-{i:03d}", "East", 100 + i])
            ws.append(["INV-007", "East", 107])  # row 27 repeats row 8

        found = scan_integrity(build)
        dups = [i for i in found if i["check"] == "duplicate_rows"]
        self.assertEqual([i["cell"] for i in dups], ["A27:C27"])
        self.assertIn("row 27 repeats row 8", dups[0]["description"])
        # the repeated ID belongs to the duplicate row, so it isn't reported again
        self.assertFalse([i for i in found if i["check"] == "duplicate_key"])


class TestStructure(unittest.TestCase):
    def test_default_tab_names_are_flagged_and_quoted(self):
        def build(ws, wb):
            ws.title = "Revenue"
            ws["A1"] = 1
            wb.create_sheet("Sheet2")["A1"] = 1
            wb.create_sheet("Copy of Revenue")["A1"] = 1

        wb = load(workbook_bytes(build))
        prepare_finance(wb)
        fs = Findings()
        check_structure(wb, fs, {})
        flagged = [i["sheet"] for i in fs.items if i["check"] == "default_sheet_name"]
        self.assertEqual(flagged, ["Sheet2", "Copy of Revenue"])
        self.assertIn('"Sheet2"', fs.items[0]["description"])


if __name__ == "__main__":
    unittest.main()
