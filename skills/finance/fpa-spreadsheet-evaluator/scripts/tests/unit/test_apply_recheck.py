"""
description: Unit tests for apply_recheck: confirming edits landed in the copy, range overlap, and the re-check split between cleared, new and waiting findings. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import apply_recheck as AR  # noqa: E402
import openpyxl  # noqa: E402


def finding(check, cell, fid=None, sheet="Calc"):
    return {
        "id": fid or f"{check}-{cell}",
        "check": check,
        "severity": "warning",
        "sheet": sheet,
        "cell": cell,
        "description": "d",
    }


def copy_wb():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Calc"
    ws["B5"] = "=B3+B4"
    ws["C2"] = 7
    ws["Z9"] = "=B5*2"
    return wb


FORMULA_EDIT = {"op": "cell", "sheet": "Calc", "cell": "B5", "formula": "=B3+B4"}


class TestVerify(unittest.TestCase):
    def test_edits_that_landed_pass_and_missing_ones_are_reported(self) -> None:
        ok = {"n": 1, "edits": [FORMULA_EDIT]}
        bad = {
            "n": 2,
            "edits": [{"op": "cell", "sheet": "Calc", "cell": "C2", "value": 8}],
        }
        skipped = {"n": 3, "edits": [{"op": "cell", "sheet": "Calc", "cell": "C2"}]}
        results = [(ok, "applied", ""), (bad, "applied", ""), (skipped, "skipped", "")]
        problems = AR.verify(None, results, None, wf=copy_wb())
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("#2 Calc!C2: expected 8"))


class TestOverlap(unittest.TestCase):
    def test_ranges_on_the_same_sheet_overlap_only_when_they_meet(self) -> None:
        self.assertTrue(AR.overlap(finding("x", "A1:C3"), finding("x", "B2")))
        self.assertFalse(AR.overlap(finding("x", "A1:C3"), finding("x", "D4")))
        self.assertFalse(AR.overlap(finding("x", "B2"), finding("x", "B2", sheet="O")))


class TestRecheck(unittest.TestCase):
    def test_findings_split_into_cleared_new_and_waiting(self) -> None:
        before = {"findings": [finding("hardcoded_in_formula_row", "B5", "F-1")]}
        after = {
            "findings": [
                finding("error_value", "Z9"),  # reads B5's new formula: wait
                finding("default_sheet_name", "A1"),  # not a value check: new
            ]
        }
        results = [
            ({"n": 1, "edits": [FORMULA_EDIT], "finding_ids": ["F-1"]}, "applied", "")
        ]
        rc = AR.recheck(before, after, results, copy_wb())
        self.assertEqual((rc["cleared"], rc["targeted"], rc["skipped"]), (1, 1, 0))
        self.assertEqual([g["check"] for g in rc["new"]], ["default_sheet_name"])
        self.assertEqual([g["cell"] for g in rc["not_rechecked"]], ["Z9"])


if __name__ == "__main__":
    unittest.main()
