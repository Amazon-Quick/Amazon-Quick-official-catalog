"""
description: Unit tests for render_map: tab layering, the escaped SVG tab map, the plain-text link summary and the Excel version line. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import render_map  # noqa: E402

HOSTILE = "<script>x</script>"


def sheet(name, role="calculation", state="visible"):
    return {"sheet": name, "role": role, "state": state, "rows": 5, "formulas": 2}


class TestLayout(unittest.TestCase):
    def test_tabs_sit_one_column_right_of_their_sources(self):
        sheets = [sheet("Inputs"), sheet("Calc"), sheet("Out"), sheet("Notes")]
        edges = [
            {"from": "Inputs", "to": "Calc", "refs": 3},
            {"from": "Calc", "to": "Out", "refs": 1},
        ]
        cols, lone = render_map.layout(sheets, edges, [])
        self.assertEqual(dict(cols), {0: ["Inputs"], 1: ["Calc"], 2: ["Out"]})
        self.assertEqual(lone, ["Notes"])

    def test_external_links_add_the_other_files_node_first(self):
        cols, _ = render_map.layout([sheet("Calc")], [], ["Calc"])
        self.assertEqual(cols[0], [render_map.EXT_NODE])
        self.assertEqual(cols[1], ["Calc"])


class TestSvgAndText(unittest.TestCase):
    def scan(self):
        return {
            "sheets": [sheet(HOSTILE, role="inputs"), sheet("Calc", state="hidden")],
            "findings": [],
            "map": {"edges": [{"from": HOSTILE, "to": "Calc", "refs": 4}]},
        }

    def test_svg_escapes_tab_names_and_shows_issue_badge(self):
        svg = render_map.svg_map(self.scan(), {"Calc": {"critical": 2}})
        self.assertTrue(svg.startswith("<svg") and svg.endswith("</svg>"))
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)
        self.assertIn("m-crit", svg)
        self.assertIn("2 critical, 0 warning", svg)

    def test_flow_text_marks_hidden_sources(self):
        scan = {
            "sheets": [sheet("A", state="hidden"), sheet("B")],
            "map": {"edges": [{"from": "A", "to": "B", "refs": 1}]},
        }
        self.assertEqual(render_map.flow_text(scan), "A (hidden) → B")

    def test_excel_line_names_version_and_how_it_was_chosen(self):
        self.assertEqual(
            render_map.excel_line(
                {"excel": {"effective_target": "2019", "target_setting": "2019"}}
            ),
            "Excel 2019 (set by the user)",
        )
        self.assertEqual(
            render_map.excel_line({}),
            "Not set (not detected, so fixes work in every version)",
        )


if __name__ == "__main__":
    unittest.main()
