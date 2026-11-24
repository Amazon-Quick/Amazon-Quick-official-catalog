"""
description: Unit tests for scan_checks_logic: the double-counting check finds a subtotal added twice and stays within its work limit on running totals. Filesystem-free.
last_updated: 2026-11-24
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_checks_logic import check_financial_logic  # noqa: E402
from scan_findings import Findings  # noqa: E402
from workbook_fixtures import (  # noqa: E402
    SLOW_SECONDS,
    load,
    prepare_finance,
    workbook_bytes,
)


class TestDoubleCounting(unittest.TestCase):
    def test_total_that_adds_a_subtotal_and_its_lines_is_flagged(self):
        def build(ws, wb):
            ws["A1"], ws["B1"] = "Item a", 10
            ws["A2"], ws["B2"] = "Item b", 20
            ws["A3"], ws["B3"] = "Item c", 30
            ws["A4"], ws["B4"] = "Subtotal", "=SUM(B1:B3)"
            ws["A5"], ws["B5"] = "Total", "=SUM(B1:B4)"

        wb = load(workbook_bytes(build))
        prepare_finance(wb)
        fs = Findings()
        check_financial_logic(wb, fs, False)
        found = [i for i in fs.items if i["check"] == "double_counting"]
        self.assertEqual([i["cell"] for i in found], ["B5"])
        self.assertIn('"Subtotal" (B4)', found[0]["description"])

    def test_running_totals_summed_again_finish_without_hitting_the_cap(self):
        def build(ws, wb):
            for r in range(1, 2001):
                ws.cell(r, 1, r)
                ws.cell(r, 2, f"=SUM($A$1:A{r})")
            for r in range(1, 1001):
                ws.cell(r, 3, "=SUM($B$1:$B$2000)")

        wb = load(workbook_bytes(build))
        prepare_finance(wb)
        start = time.time()
        check_financial_logic(wb, Findings(), False)
        self.assertLess(time.time() - start, SLOW_SECONDS)
        self.assertEqual([n for n in wb.notes if n["note"] == "scan_capped"], [])


if __name__ == "__main__":
    unittest.main()
