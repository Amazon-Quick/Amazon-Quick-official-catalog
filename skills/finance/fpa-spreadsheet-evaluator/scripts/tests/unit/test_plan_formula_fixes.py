"""
description: Unit tests for plan_formula_fixes: a short SUM is extended, a broken row pattern is restored, a typed number moves to an inputs tab, and lookup targets follow the Excel version. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plan_changes as PC  # noqa: E402
import plan_formula_fixes as FX  # noqa: E402
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


def planner(build, **scan):
    return PC.Planner(workbook_bytes(build), {"findings": [], **scan}, {})


class TestFormulaFixes(unittest.TestCase):
    def test_sum_that_stops_short_is_extended_to_the_row_above(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            for r, v in enumerate([10, 20, 30, 40], start=1):
                ws.cell(r, 1, v)
            ws["A5"] = "=SUM(A1:A3)"

        p = planner(build)
        FX.extend_sum(p, finding("sum_range_gap", "A5"))
        self.assertEqual(p.changes[0]["edits"][0]["formula"], "=SUM(A1:A4)")
        self.assertIn("+40", p.changes[0]["summary"])

    def test_typed_value_in_a_formula_row_is_replaced_by_the_pattern(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            for c in range(1, 6):
                ws.cell(1, c, c)
                ws.cell(2, c, f"={ws.cell(1, c).column_letter}1*2")
            ws["C2"] = 99

        p = planner(build)
        FX.restore_pattern(p, finding("value_in_formula_row", "C2"), "confirm")
        edit = p.changes[0]["edits"][0]
        self.assertEqual((edit["formula"], edit["style_from"]), ("=C1*2", "B2"))

    def test_typed_number_moves_to_the_inputs_tab(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            ws["A1"], ws["B1"], ws["C1"] = "Growth", 100, "=B1*1.07"
            wb.create_sheet("Inputs")["A1"] = "Assumptions"

        sheets = [
            {"sheet": "S", "role": "calc", "state": "visible", "reads_from": []},
            {"sheet": "Inputs", "role": "inputs", "state": "visible"},
        ]
        p = planner(build, sheets=sheets)
        FX.extract_input(p, finding("hardcoded_number_in_formula", "C1"))
        edits = p.changes[0]["edits"]
        self.assertEqual(edits[1]["value"], 1.07)
        self.assertEqual(edits[2]["formula"], f"=B1*Inputs!${edits[1]['cell'][0]}$3")

    def test_lookup_target_falls_back_when_excel_is_old(self) -> None:
        p = planner(lambda ws, wb: None)
        p.scan["excel"] = {
            "lookup_style": {"dominant": "XLOOKUP"},
            "effective_target": "2016",
        }
        self.assertEqual(FX.lookup_target(p), "INDEX/MATCH")
        p.scan["excel"] = {"effective_target": "365"}
        self.assertEqual(FX.lookup_target(p), "XLOOKUP")


if __name__ == "__main__":
    unittest.main()
