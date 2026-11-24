"""
description: Unit tests for compare_render: the verdict wording, key-result deltas, structure renames and tab counts in the comparison page. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_render as CR  # noqa: E402
import xlsx_capture  # noqa: E402


def setUpModule() -> None:
    xlsx_capture.start()


def tearDownModule() -> None:
    xlsx_capture.stop()


def flag(fid, severity):
    return {
        "id": fid,
        "severity": severity,
        "basis": "verified",
        "sheet": "Calc",
        "cell": "B4",
        "label": "Revenue",
        "text": "Changed",
    }


def make_res(flags=()):
    counts = dict.fromkeys(
        ("assumptions", "formulas", "to_value", "to_formula", "rows_added"), 0
    )
    counts.update(rows_removed=0, introduced=0, resolved=0)
    return {
        "old": "v1.xlsx",
        "new": "v2.xlsx",
        "sheets": {
            "added": ["Notes"],
            "removed": [],
            "renamed": [("Sheet1", "Summary")],
            "hidden": [],
            "unhidden": [],
        },
        "structure": {},
        "assumptions": [],
        "formulas": [],
        "to_value": [],
        "to_formula": [],
        "data": {},
        "outputs": [
            {
                "sheet": "Calc",
                "cell": "B9",
                "label": "Margin",
                "before": 0.2,
                "after": 0.25,
                "pct": True,
            }
        ],
        "introduced": [],
        "resolved": [],
        "flags": list(flags),
        "counts": counts,
    }


class TestRender(unittest.TestCase):
    def test_a_critical_flag_leads_the_verdict(self) -> None:
        page = CR.render(
            make_res([flag("K-1", "critical"), flag("K-2", "warning")]), generated="now"
        )
        self.assertIn("v-crit", page)
        self.assertIn("1 change broke something, and 1 more may be unintended.", page)
        self.assertIn("<span class='cnt crit'>2</span>", page)

    def test_warnings_only_ask_for_a_check(self) -> None:
        page = CR.render(make_res([flag("K-1", "warning")]), generated="now")
        self.assertIn("v-warn", page)
        self.assertIn("1 change may be unintended: check it", page)

    def test_percent_results_show_points_and_structure_lists_renames(self) -> None:
        page = CR.render(make_res(), generated="24 Nov 2026")
        self.assertIn("20.0%", page)
        self.assertIn("25.0%", page)
        self.assertIn("+5.0 pts", page)
        self.assertIn("Sheet1 → Summary", page)
        self.assertIn("<dt>Tabs added</dt><dd>Notes</dd>", page)
        self.assertIn("Compared 24 Nov 2026", page)

    def test_missing_values_read_as_blank(self) -> None:
        self.assertEqual(CR._val(None), "(blank)")
        self.assertEqual(CR._val(0.5, pct=True), "50.0%")


if __name__ == "__main__":
    unittest.main()
