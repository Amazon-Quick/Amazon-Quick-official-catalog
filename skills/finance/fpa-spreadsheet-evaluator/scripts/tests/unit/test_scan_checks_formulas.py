"""
description: Unit tests for scan_checks_formulas: circular references through ranges without a size cap, and error cause attribution. Filesystem-free.
last_updated: 2026-11-24
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_checks_formulas import check_circular, check_errors  # noqa: E402
from scan_findings import Findings  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402


class TestCircularReferences(unittest.TestCase):
    def test_whole_column_sumif_is_checked_in_full_without_a_cap(self):
        def build(ws, wb):
            for r in range(1, 3001):
                ws.cell(r, 1, f"k{r % 50}")
                ws.cell(r, 2, "=ROW()*2")
                ws.cell(r, 3, f"=SUMIF($A:$A,A{r},$B:$B)")

        wb = load(workbook_bytes(build))
        fs = Findings()
        check_circular(wb, fs)
        self.assertEqual(fs.items, [])
        self.assertEqual(wb.notes, [])

    def test_cycle_through_a_range_is_found(self):
        def build(ws, wb):
            ws["A1"] = "=B1"
            ws["B1"] = "=SUM(A1:A3)"
            ws["A2"] = 1
            ws["A3"] = "=A2*2"
            ws["D5"] = "=SUM(D1:D9)"
            ws["D6"] = "=D7"

        wb = load(workbook_bytes(build))
        fs = Findings()
        check_circular(wb, fs)
        self.assertEqual(sorted(i["cell"] for i in fs.items), ["A1:B1", "D5"])


class TestCheckErrors(unittest.TestCase):
    def test_error_names_the_upstream_error_it_comes_from(self):
        def build(ws, wb):
            ws["A1"] = "=1/0"
            ws["A2"] = "=A1*2"

        wb = load(workbook_bytes(build))
        for x in wb.formulas:
            x.cached = "#DIV/0!"
        fs = Findings()
        check_errors(wb, fs, True)
        by_cell = {i["cell"]: i["description"] for i in fs.items}
        self.assertEqual(by_cell["A1"], "Shows #DIV/0!.")
        self.assertIn('"A1"', by_cell["A2"])


if __name__ == "__main__":
    unittest.main()
