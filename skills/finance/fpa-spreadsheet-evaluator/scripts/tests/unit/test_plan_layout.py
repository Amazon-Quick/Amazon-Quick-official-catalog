"""
description: Unit tests for plan_layout: calculation mode, unused names, column widths, frozen headers and merged cells become the right planned edits. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plan_changes as PC  # noqa: E402
import plan_layout as LAY  # noqa: E402
from workbook_fixtures import workbook_bytes  # noqa: E402


def finding(check, cell=None, sheet="S", **extra):
    return {
        "id": "F-1",
        "check": check,
        "sheet": sheet,
        "cell": cell,
        "severity": "warning",
        "description": "d",
        "fix": "scan fix",
        **extra,
    }


def planner(build):
    return PC.Planner(workbook_bytes(build), {"findings": []}, {})


def titled(ws, wb):
    ws.title = "S"


class TestWorkbookSettings(unittest.TestCase):
    def test_manual_calculation_becomes_a_confirm_change(self) -> None:
        p = planner(titled)
        LAY.fix_calc_manual(p, finding("calc_manual", sheet=None))
        self.assertEqual(p.changes[0]["edits"], [{"op": "calc_auto"}])
        self.assertEqual(p.changes[0]["risk"], "confirm")

    def test_unused_names_are_listed_and_clipped_after_six(self) -> None:
        p = planner(titled)
        names = [f"N{i}" for i in range(8)]
        LAY.fix_unused_names(p, finding("unused_named_range", sheet=None, names=names))
        self.assertEqual(p.changes[0]["edits"][0]["names"], names)
        self.assertTrue(p.changes[0]["summary"].endswith(" ..."))
        LAY.fix_unused_names(p, finding("unused_named_range", sheet=None))
        self.assertEqual(len(p.manual), 1)


class TestSheetLayout(unittest.TestCase):
    def test_freeze_panes_uses_a_clear_header_row(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            ws.append(["Item", "Amount"])
            ws.append(["Rent", 100])
            ws.append(["Fees", 20])

        p = planner(build)
        LAY.fix_freeze_panes(p, finding("no_freeze_panes"))
        self.assertEqual(
            p.changes[0]["edits"][0], {"op": "freeze", "sheet": "S", "row": 1}
        )

    def test_narrow_column_is_widened_past_its_widest_number(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            ws["B2"], ws["B3"] = 1234567, 12
            for ref in ("B2", "B3"):
                ws[ref].number_format = "#,##0.00"

        p = planner(build)
        LAY.fix_narrow_column(p, finding("column_too_narrow", "B2:B3"))
        edit = p.changes[0]["edits"][0]
        self.assertEqual((edit["op"], edit["col"]), ("col_width", "B"))
        self.assertGreaterEqual(edit["width"], len("1,234,567.00") + 2)

    def test_merged_cells_are_unmerged(self) -> None:
        p = planner(titled)
        LAY.fix_merged_cells(p, finding("merged_cells_in_calc", "A1:B1"))
        self.assertEqual(
            p.changes[0]["edits"], [{"op": "unmerge", "sheet": "S", "ref": "A1:B1"}]
        )


if __name__ == "__main__":
    unittest.main()
