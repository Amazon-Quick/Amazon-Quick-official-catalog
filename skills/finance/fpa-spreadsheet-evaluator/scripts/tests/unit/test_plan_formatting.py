"""
description: Unit tests for plan_formatting: percent formats follow the values, units stay with the user, and copied styles come from a matching neighbor. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plan_changes as PC  # noqa: E402
import plan_formatting as FMT  # noqa: E402
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


def planner(build):
    return PC.Planner(workbook_bytes(build), {"findings": []}, {})


class TestPercentFormat(unittest.TestCase):
    def test_whole_percentages_get_0_percent(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            ws["A1"], ws["A2"] = 0.25, 0.5

        p = planner(build)
        FMT.fix_percent_format(p, finding("percent_general_format", "A1:A2"))
        self.assertEqual({e["numfmt_id"] for e in p.changes[0]["edits"]}, {9})

    def test_fractional_percentages_get_two_decimals(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            ws["A1"] = 0.125

        p = planner(build)
        FMT.fix_percent_format(p, finding("percent_general_format", "A1"))
        self.assertEqual(p.changes[0]["edits"][0]["numfmt_id"], 10)
        self.assertIn("0.00%", p.changes[0]["summary"])


class TestCopyStyle(unittest.TestCase):
    def test_mixed_units_always_go_to_the_user(self) -> None:
        p = planner(lambda ws, wb: setattr(ws, "title", "S"))
        FMT.fix_mixed_units(p, finding("mixed_units", "A1"))
        self.assertEqual(p.changes, [])
        self.assertIn("units", p.manual[0]["recommendation"])

    def test_mixed_decimals_copy_from_a_neighbor_with_other_decimals(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            for r, fmt in ((1, "0.00"), (2, "0.00"), (3, "0.000")):
                ws.cell(r, 1, 1.5).number_format = fmt

        p = planner(build)
        FMT.fix_mixed_decimals(p, finding("mixed_decimals", "A3"))
        self.assertEqual(
            p.changes[0]["edits"],
            [{"op": "cell", "sheet": "S", "cell": "A3", "style_from": "A2"}],
        )


if __name__ == "__main__":
    unittest.main()
