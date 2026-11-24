"""
description: Unit tests for compare_export: the change log download lists every change type with its flag, and records both versions on the About tab. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_export as CE  # noqa: E402
import xlsx_capture  # noqa: E402


def setUpModule() -> None:
    xlsx_capture.start()


def tearDownModule() -> None:
    xlsx_capture.stop()


def make_res():
    edit = {"sheet": "Calc", "cell": "B4", "label": "Revenue"}
    return {
        "old": "plan_v1.xlsx",
        "new": "folder/plan_v2.xlsx",
        "flags": [{"sheet": "Calc", "cell": "B4", "text": "Input moved a lot"}],
        "assumptions": [dict(edit, before=10, after=99, count=1)],
        "formulas": [dict(edit, cell="C4", old="=B4*2", new="=B4*3", count=2)],
        "to_value": [dict(edit, cell="D4", old="=B4", new=5)],
        "to_formula": [],
        "structure": {"Calc": {"rows_added": ["Marketing"], "rows_removed": []}},
        "introduced": [{"sheet": "Calc", "cell": "E4", "description": "New error"}],
    }


class TestChangeLog(unittest.TestCase):
    def test_every_change_is_a_row_with_its_flag(self) -> None:
        link = CE._change_log_link(make_res(), "24 Nov 2026")
        ws = xlsx_capture.last_workbook()["Changes"]
        rows = [[c.value for c in r] for r in ws.iter_rows(min_row=2)]
        self.assertEqual(
            [r[0] for r in rows],
            [
                "Input changed",
                "Formula changed",
                "Formula to typed number",
                "Row added",
                "New issue",
            ],
        )
        self.assertEqual(rows[0][7], "Input moved a lot")
        self.assertEqual(rows[1][4:6], ["=B4*2", "=B4*3"])
        self.assertEqual(ws.freeze_panes, "A2")
        self.assertIn('download="plan_v2_change_log.xlsx"', link)

    def test_formula_text_is_stored_as_text_and_about_names_both_versions(self) -> None:
        CE._change_log_link(make_res(), "24 Nov 2026")
        wb = xlsx_capture.last_workbook()
        live = [c for ws in wb for r in ws.iter_rows() for c in r if c.data_type == "f"]
        self.assertEqual(live, [])
        about = {r[0].value: r[1].value for r in wb["About"].iter_rows()}
        self.assertEqual(about["Old version"], "plan_v1.xlsx")
        self.assertEqual(about["Compared"], "24 Nov 2026")


if __name__ == "__main__":
    unittest.main()
