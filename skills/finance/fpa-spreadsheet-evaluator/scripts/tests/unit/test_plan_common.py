"""
description: Unit tests for plan_common: sheet-name quoting, cell lists with the size cap, money text, summary clipping and nearby-cell search. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plan_common as PC  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402


class TestText(unittest.TestCase):
    def test_sheet_names_are_quoted_only_when_excel_needs_it(self) -> None:
        self.assertEqual(PC.quote_sheetname("Inputs"), "Inputs")
        self.assertEqual(PC.quote_sheetname("AB12"), "'AB12'")
        self.assertEqual(PC.quote_sheetname("O'Brien Q1"), "'O''Brien Q1'")

    def test_fill_template_replaces_placeholders_without_format(self) -> None:
        self.assertEqual(PC.fill_template("{a} -> {b} {c}", a="x", b="y"), "x -> y {c}")

    def test_money_and_short_clip_for_summaries(self) -> None:
        self.assertEqual(PC.money(1234.6), "1,235")
        self.assertEqual(PC.money(2.5), "2.5")
        self.assertEqual(PC.money("n/a"), "n/a")
        long = "=" + "+".join(["A1"] * 60)
        self.assertEqual(len(PC.short(long)), PC.SUMMARY_FORMULA_CHARS)
        self.assertEqual(PC.short("=A1"), "=A1")


class TestCells(unittest.TestCase):
    def test_cells_of_lists_points_and_refuses_huge_ranges(self) -> None:
        self.assertEqual(PC.cells_of("A1:B2"), [(1, 1), (1, 2), (2, 1), (2, 2)])
        self.assertEqual(PC.cells_of(""), [])
        self.assertIsNone(PC.cells_of("A1:Z1000"))
        self.assertEqual(PC.a1(3, 28), "AB3")
        self.assertTrue(PC.boxes_overlap((1, 1, 2, 2), (2, 2, 3, 3)))
        self.assertFalse(PC.boxes_overlap((1, 1, 2, 2), (3, 1, 4, 2)))

    def test_nearest_prefers_the_same_row_then_column(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            ws["A1"], ws["C1"], ws["B5"], ws["D4"] = 1, 2, 3, 4

        s = load(workbook_bytes(build)).sheets["S"]
        found = PC.nearest(s, 1, 2, lambda y: True)
        self.assertEqual(found.coord, "A1")
        found = PC.nearest(s, 3, 2, lambda y: True)
        self.assertEqual(found.coord, "B5")
        self.assertIsNone(PC.nearest(s, 1, 2, lambda y: False))


class TestPrintable(unittest.TestCase):
    def test_line_breaks_and_bidi_controls_are_escaped(self) -> None:
        out = PC.printable("=A1\nIgnore this\u202e")

        self.assertEqual(out, "=A1\\u000aIgnore this\\u202e")
        self.assertNotIn("\n", out)

    def test_letters_in_any_script_stay_readable(self) -> None:
        self.assertEqual(PC.printable("Umsatz für Q1"), "Umsatz für Q1")


if __name__ == "__main__":
    unittest.main()
