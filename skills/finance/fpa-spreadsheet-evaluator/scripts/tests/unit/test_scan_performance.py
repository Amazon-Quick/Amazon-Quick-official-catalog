"""
description: Unit tests for scan_performance: the scorecard reads calculation mode and volatile formulas, and the findings flag manual calculation, conditional SUMPRODUCT and unused names. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openpyxl.workbook.defined_name import DefinedName  # noqa: E402
from scan_findings import Findings  # noqa: E402
from scan_performance import (  # noqa: E402
    _identifiers,
    check_performance_findings,
    performance,
)
from workbook_fixtures import load, workbook_bytes  # noqa: E402


class MemoryFile(io.BytesIO):
    """In-memory .xlsx that also answers the path.stat() call performance() makes."""

    def stat(self):
        return SimpleNamespace(st_size=len(self.getvalue()))


def _manual_book(ws, wb):
    wb.calculation.calcMode = "manual"
    ws["A1"], ws["B1"] = 1, 2
    for r in range(2, 5):
        ws.cell(r, 1, "=TODAY()")
    ws["B2"] = "=SUMPRODUCT((A1:A3>0)*B1:B3)"
    ws["C1"] = "=Used*2"
    wb.defined_names.add(DefinedName("Used", attr_text="Sheet!$B$1"))
    wb.defined_names.add(DefinedName("Unused", attr_text="Sheet!$A$1"))


class TestPerformance(unittest.TestCase):
    def setUp(self):
        self.file = MemoryFile(workbook_bytes(_manual_book).getvalue())
        self.wb = load(self.file)
        self.perf = performance(self.wb, self.file, 0)

    def test_scorecard_reports_manual_calc_and_volatile_formulas(self):
        m = {x["key"]: x for x in self.perf["metrics"]}
        self.assertEqual(
            (m["calc_mode"]["value"], m["calc_mode"]["rating"]), ("Manual", "red")
        )
        self.assertEqual(m["volatile"]["value"], 3)
        self.assertEqual(m["volatile"]["note"], "TODAY 3")
        self.assertEqual(m["named_ranges"]["value"], 2)
        self.assertEqual(self.perf["verdict"], "fixes")

    def test_findings_flag_manual_calc_sumproduct_and_unused_name(self):
        fs = Findings()
        check_performance_findings(self.wb, fs, self.perf)
        checks = {i["check"]: i for i in fs.items}
        self.assertIn("calc_manual", checks)
        self.assertEqual(checks["sumproduct_conditional"]["cell"], "B2")
        self.assertEqual(checks["unused_named_range"]["_names"], ["Unused"])
        self.assertNotIn("volatile_load", checks)  # 3 is below the threshold


class TestIdentifiers(unittest.TestCase):
    def test_names_are_found_but_function_calls_are_not(self) -> None:
        ids = _identifiers("=SUM(RATE*2)+TAX_RATE+SHEET1!GROWTH.Q1")

        self.assertIn("RATE", ids)
        self.assertIn("TAX_RATE", ids)
        self.assertIn("GROWTH.Q1", ids)
        self.assertNotIn("SUM", ids)


if __name__ == "__main__":
    unittest.main()
