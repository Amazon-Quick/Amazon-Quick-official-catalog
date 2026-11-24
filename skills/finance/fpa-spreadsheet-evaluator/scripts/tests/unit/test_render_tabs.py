"""
description: Unit tests for render_tabs: the Changes tab cards and Needs you list, escaped tab names on the Map tab, and the Performance verdict. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import render_tabs  # noqa: E402

HOSTILE = "<img src=x onerror=alert(1)>"

PLAN = {
    "changes": [
        {
            "n": 1,
            "sheet": "Calc",
            "target": "B5",
            "risk": "safe",
            "summary": "Fix the total",
            "finding_ids": ["F-1"],
        },
        {
            "n": 2,
            "sheet": "Calc",
            "target": "C5",
            "risk": "confirm",
            "summary": "Link the cell",
            "finding_ids": [],
        },
    ],
    "manual": [
        {
            "where": "Calc!D9",
            "finding_id": "F-1",
            "what": "Odd growth",
            "recommendation": "Ask the owner",
        }
    ],
}
KEPT = [{"id": "F-1", "label": "Revenue"}]


class TestChangesTab(unittest.TestCase):
    def test_no_plan_says_no_changes(self):
        html = render_tabs.changes_tab(None, None, {}, {}, [], [])
        self.assertIn("No changes proposed yet.", html)

    def test_unapplied_plan_shows_cards_chips_and_manual_rows(self):
        status = {2: {"status": "skipped", "why": HOSTILE}}
        html = render_tabs.changes_tab(PLAN, None, status, {}, KEPT, [])
        self.assertIn("Nothing applied yet.", html)
        self.assertIn("chg st-proposed r-safe", html)
        self.assertIn("chg st-skipped r-confirm", html)
        self.assertIn("<span class='lab'>Revenue</span>", html)
        self.assertIn("Needs you <span class='cnt'>1</span>", html)
        self.assertIn("Ask the owner", html)
        self.assertNotIn(HOSTILE, html)

    def test_applied_plan_names_only_the_copy_file(self):
        applied = {"copy": "/home/user/secret/model_fixed.xlsx"}
        status = {1: {"status": "applied"}}
        html = render_tabs.changes_tab(PLAN, applied, status, {}, KEPT, [])
        self.assertIn("Applied 1 of 2 to a copy:</b> model_fixed.xlsx", html)
        self.assertNotIn("/home/user", html)


class TestMapAndPerformanceTabs(unittest.TestCase):
    def test_map_tab_escapes_tab_names_and_lists_hidden_tabs(self):
        s = {
            "sheet": HOSTILE,
            "role": "inputs",
            "state": "hidden",
            "rows": 3,
            "formulas": 0,
            "reads_from": [],
            "feeds": [],
        }
        html = render_tabs.map_tab({"sheets": [s], "findings": []}, {}, [])
        self.assertNotIn(HOSTILE, html)
        self.assertIn("<dt>Hidden tabs</dt>", html)
        self.assertIn("Tabs are not linked by formulas", html)

    def test_performance_tab_reports_limits_over_and_within(self):
        perf = {
            "verdict": "restructure",
            "reds": 1,
            "yellows": 1,
            "metrics": [
                {"label": "Tabs", "value": 90, "rating": "yellow", "note": "Many"},
                {"label": "Formulas", "value": 9, "rating": "red", "note": "Slow"},
                {"label": "Names", "value": 2, "rating": "green", "note": ""},
            ],
        }
        html = render_tabs.performance_tab(perf, "<p>extra</p>")
        self.assertIn("note crit", html)
        self.assertIn("2 performance limits exceeded", html)
        self.assertLess(html.index("Formulas"), html.index("Tabs"))  # red first
        self.assertIn("Within limits", html)
        self.assertTrue(html.endswith("<p>extra</p>"))

    def test_performance_tab_with_no_verdict_is_ok(self):
        html = render_tabs.performance_tab({}, "")
        self.assertIn("No performance limits exceeded.", html)


if __name__ == "__main__":
    unittest.main()
