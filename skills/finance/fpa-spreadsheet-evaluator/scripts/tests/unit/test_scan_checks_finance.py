"""
description: Unit tests for scan_checks_finance: total-column formulas aren't reported as inconsistent, and check_finance prepares period layouts before running the checks. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_checks_finance import check_finance, drop_total_column_noise  # noqa: E402
from scan_findings import Findings  # noqa: E402
from workbook_fixtures import load, prepare_finance, workbook_bytes  # noqa: E402


def months_with_total(ws, wb):
    ws.title = "Plan"
    for col, head in zip("ABCDE", ("Line", "Jan", "Feb", "Mar", "Total"), strict=True):
        ws[f"{col}1"] = head
    for r in (2, 3):
        ws[f"A{r}"] = f"Line {r}"
        for col in "BCD":
            ws[f"{col}{r}"] = r * 10
    ws["E2"] = "=SUM(B2:D2)"
    ws["E3"] = "=SUM(B2:D2)"  # reads another row: a real slip


class TestDropTotalColumnNoise(unittest.TestCase):
    def test_only_same_row_totals_are_dropped(self):
        wb = load(workbook_bytes(months_with_total))
        prepare_finance(wb)
        fs = Findings()
        for cell in ("E2", "E3", "C2"):
            fs.add("inconsistent_formula", "Plan", cell, "Differs from neighbors")
        fs.add("hardcoded_number_in_formula", "Plan", "E2", "Typed number")
        drop_total_column_noise(wb, fs)
        kept = [(i["check"], i["cell"]) for i in fs.items]
        self.assertEqual(
            kept,
            [
                ("inconsistent_formula", "E3"),
                ("inconsistent_formula", "C2"),
                ("hardcoded_number_in_formula", "E2"),
            ],
        )


class TestCheckFinance(unittest.TestCase):
    def test_sets_period_layout_and_reports_a_header_gap(self):
        def build(ws, wb):
            ws.title = "Plan"
            for col, head in zip(
                "ABCDE", ("Line", "Jan", "Feb", "Apr", "May"), strict=True
            ):
                ws[f"{col}1"] = head
            ws["A2"] = "Sales"
            for col in "BCDE":
                ws[f"{col}2"] = 5

        wb = load(workbook_bytes(build))
        fs = Findings()
        check_finance(wb, fs, False, {})
        self.assertEqual(wb.sheets["Plan"].periods["kind"], "mo")
        gaps = [i for i in fs.items if i["check"] == "period_header_gap"]
        self.assertEqual([i["cell"] for i in gaps], ["D1"])
        self.assertIn("Mar", gaps[0]["description"])


if __name__ == "__main__":
    unittest.main()
