"""
description: Unit tests for scan_checks_patterns: Excel version needs, compatibility findings, risky lookup and IFERROR patterns, and inconsistent lookup styles. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_checks_patterns import (  # noqa: E402
    check_compat,
    check_formula_patterns,
    excel_info,
)
from scan_findings import Findings  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402


def _xlookup_book(ws, wb):
    ws["A1"], ws["B1"] = "k", 1
    ws["C1"] = "=XLOOKUP(A1,A1:A2,B1:B2)"


class TestExcelVersion(unittest.TestCase):
    def test_auto_target_uses_the_newest_function_the_file_needs(self):
        info = excel_info(load(workbook_bytes(_xlookup_book)), "auto")
        self.assertEqual(info["file_needs_at_least"], "2021")
        self.assertEqual(info["effective_target"], "2021")
        self.assertEqual(info["functions_needing_newer_excel"], {"XLOOKUP": "2021"})

    def test_older_target_flags_functions_readers_cannot_calculate(self):
        wb = load(workbook_bytes(_xlookup_book))
        info = excel_info(wb, "2019")
        self.assertEqual(info["effective_target"], "2019")
        fs = Findings()
        check_compat(wb, fs, info)
        self.assertEqual(
            [(i["check"], i["cell"]) for i in fs.items], [("compat_function", "C1")]
        )
        self.assertIn("#NAME?", fs.items[0]["description"])


class TestFormulaPatterns(unittest.TestCase):
    def test_risky_formula_patterns_are_each_flagged_at_their_cell(self):
        def build(ws, wb):
            ws["A1"], ws["B1"] = 1, 2
            ws["C1"] = "=VLOOKUP(A1,A1:B2,2)"
            ws["C2"] = "=IFERROR(A1/B1,0)"
            ws["C3"] = "=+A1"
            ws["C4"] = "=SUM(A1+B1)"

        fs = Findings()
        check_formula_patterns(load(workbook_bytes(build)), fs)
        found = {(i["check"], i["cell"]) for i in fs.items}
        self.assertEqual(
            found,
            {
                ("vlookup_approx", "C1"),
                ("lookup_hardcoded_col", "C1"),
                ("iferror_masking", "C2"),
                ("redundant_formula", "C3"),
                ("redundant_formula", "C4"),
            },
        )

    def test_a_lookup_that_breaks_the_model_convention_is_flagged(self):
        def build(ws, wb):
            ws["A1"], ws["B1"] = "k", 1
            for r in range(2, 7):
                ws.cell(r, 3, "=XLOOKUP(A1,A1:A2,B1:B2)")
            ws["C7"] = "=INDEX(B1:B2,MATCH(A1,A1:A2,0))"

        fs = Findings()
        result = check_formula_patterns(load(workbook_bytes(build)), fs)
        self.assertEqual(result["dominant"], "XLOOKUP")
        flagged = [i for i in fs.items if i["check"] == "lookup_style_inconsistent"]
        self.assertEqual([i["cell"] for i in flagged], ["C7"])


if __name__ == "__main__":
    unittest.main()
