"""
description: Unit tests for render_taxonomy: report tab of a finding, performance findings, and judgment rows turned into findings. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import render_taxonomy as RT  # noqa: E402


class TestTabOf(unittest.TestCase):
    def test_area_wins_then_group_then_formula(self):
        self.assertEqual(RT.tab_of({"area": "logic", "group": "Errors"}), "logic")
        self.assertEqual(RT.tab_of({"group": "Pivots"}), "data")
        self.assertEqual(RT.tab_of({"group": "Unknown"}), "formula")

    def test_performance_findings_by_check_or_group(self):
        self.assertTrue(RT.is_perf({"check": "volatile_function"}))
        self.assertTrue(RT.is_perf({"check": "calc_manual", "group": "Performance"}))
        self.assertFalse(RT.is_perf({"check": "error_value", "group": "Errors"}))


class TestJudgmentFindings(unittest.TestCase):
    def test_rows_get_ids_areas_and_safe_severities(self):
        out = RT.judgment_findings(
            [
                {
                    "area": " Data Integrity ",
                    "severity": "critical",
                    "title": "Odd",
                    "observation": "Growth jumps",
                    "sheet": "Calc",
                    "cell": "B4",
                },
                {"area": "nonsense", "severity": "info", "text": "Check this"},
            ]
        )
        first, second = out
        self.assertEqual(first["id"], "J-01")
        self.assertEqual((first["area"], first["group"]), ("data", "Data integrity"))
        self.assertEqual(first["severity"], "warning")  # never critical
        self.assertEqual(first["description"], "Odd: Growth jumps")
        self.assertEqual(first["fix"], "Confirm with the model owner.")
        self.assertEqual((second["area"], second["severity"]), ("logic", "info"))
        self.assertEqual(second["question"], "Check this")
        self.assertTrue(all(f["basis"] == "judgment" for f in out))

    def test_no_rows_gives_no_findings(self):
        self.assertEqual(RT.judgment_findings(None), [])


if __name__ == "__main__":
    unittest.main()
