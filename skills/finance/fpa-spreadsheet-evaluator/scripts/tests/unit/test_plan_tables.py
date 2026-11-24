"""
description: Unit tests for plan_tables: a table is extended over the rows below it, and a fixed range over a table column becomes a structured reference. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plan_changes as PC  # noqa: E402
import plan_tables as TBL  # noqa: E402
from openpyxl.worksheet.table import Table  # noqa: E402
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


def build(ws, wb):
    ws.title = "S"
    ws.append(["Item", "Amount"])
    ws.append(["Rent", 100])
    ws.append(["Fees", 20])
    ws.append(["Late", 5])
    ws.add_table(Table(displayName="Costs", ref="A1:B3"))
    ws["D1"] = "=SUM(B2:B3)"


def planner():
    return PC.Planner(workbook_bytes(build), {"findings": []}, {})


class TestTables(unittest.TestCase):
    def test_table_is_extended_to_the_finding_row(self) -> None:
        p = planner()
        TBL.resize_table(p, finding("data_past_table_edge", "A4:B4"))
        self.assertEqual(
            p.changes[0]["edits"][0],
            {"op": "table_ref", "sheet": "S", "table": "Costs", "ref": "A1:B4"},
        )
        self.assertEqual(p.table_resized, {"Costs": 4})

    def test_range_outside_any_table_goes_to_the_user(self) -> None:
        p = planner()
        TBL.resize_table(p, finding("data_past_table_edge", "F4:G4"))
        self.assertEqual((p.changes, len(p.manual)), ([], 1))

    def test_fixed_range_over_a_column_becomes_a_structured_reference(self) -> None:
        p = planner()
        TBL.structured_ref(p, finding("fixed_range_over_table", "D1"))
        self.assertEqual(p.changes[0]["edits"][0]["formula"], "=SUM(Costs[Amount])")


if __name__ == "__main__":
    unittest.main()
