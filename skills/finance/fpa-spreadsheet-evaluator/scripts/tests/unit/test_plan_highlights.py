"""
description: Unit tests for plan_highlights: which highlight rules may merge, merging copies into one rule, limiting whole-column rules and deleting broken ones. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import openpyxl  # noqa: E402
import plan_changes as PC  # noqa: E402
import plan_highlights as HL  # noqa: E402
from openpyxl.formatting.rule import (  # noqa: E402
    CellIsRule,
    ColorScaleRule,
    FormulaRule,
)
from openpyxl.styles import PatternFill  # noqa: E402
from workbook_fixtures import workbook_bytes  # noqa: E402

RED = PatternFill("solid", start_color="FF0000")


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


def only_block(rule):
    ws = openpyxl.Workbook().active
    ws.conditional_formatting.add("A1:A5", rule)
    return next(iter(ws.conditional_formatting))


class TestMergeKey(unittest.TestCase):
    def test_absolute_rules_merge_and_relative_or_scale_rules_do_not(self) -> None:
        gt = CellIsRule(operator="greaterThan", formula=["$B$1"], fill=RED)
        self.assertIsNotNone(HL.cf_merge_key(only_block(gt)))
        rel = FormulaRule(formula=["A1>5"], fill=RED)
        self.assertIsNone(HL.cf_merge_key(only_block(rel)))
        scale = ColorScaleRule(
            start_type="min", start_color="FFFFFF", end_type="max", end_color="FF0000"
        )
        self.assertIsNone(HL.cf_merge_key(only_block(scale)))


class TestPlannedRules(unittest.TestCase):
    def test_copies_of_one_rule_merge_into_one_range(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            for r in range(1, 25):
                ws.cell(r, 1, r)
                ws.conditional_formatting.add(
                    f"A{r}", CellIsRule(operator="greaterThan", formula=["5"], fill=RED)
                )

        p = PC.Planner(workbook_bytes(build), {"findings": []}, {})
        HL.merge_highlight_copies(p, finding("cf_fragmented", "A1:A24"))
        edit = p.changes[0]["edits"][0]
        self.assertEqual(
            (edit["op"], edit["sqref"], len(edit["sqrefs"])), ("cf_merge", "A1:A24", 24)
        )

    def test_whole_column_rule_is_limited_and_broken_rule_deleted(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            ws["A1"], ws["A3"] = 1, 3
            ws.conditional_formatting.add(
                "A1:A1048576",
                CellIsRule(operator="greaterThan", formula=["5"], fill=RED),
            )

        p = PC.Planner(workbook_bytes(build), {"findings": []}, {})
        HL.limit_whole_column(p, finding("cf_whole_column", "A:A"))
        self.assertEqual(p.changes[0]["edits"][0]["new"], "A1:A3")
        HL.delete_broken_rule(p, finding("cf_broken_ref", "C1:C9"))
        self.assertEqual(p.changes[1]["risk"], "confirm")
        self.assertEqual(p.changes[1]["edits"][0]["op"], "cf_delete_ref")


if __name__ == "__main__":
    unittest.main()
