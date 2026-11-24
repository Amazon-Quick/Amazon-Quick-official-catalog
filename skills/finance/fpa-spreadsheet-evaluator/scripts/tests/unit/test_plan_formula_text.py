"""
description: Unit tests for plan_formula_text: argument splitting, paren stripping, range parsing, literal numbers, VLOOKUP parts and the pattern neighbor. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plan_formula_text as FT  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402


class TestSplitting(unittest.TestCase):
    def test_split_top_ignores_separators_in_calls_and_strings(self) -> None:
        self.assertEqual(
            FT.split_top('A1, "x,y", SUM(B1,C1)', ","),
            ["A1", '"x,y"', "SUM(B1,C1)"],
        )

    def test_strip_parens_removes_only_wrapping_parens(self) -> None:
        self.assertEqual(FT.strip_parens(" ((A1+B1)) "), "A1+B1")
        self.assertEqual(FT.strip_parens("(A1)+(B1)"), "(A1)+(B1)")


class TestRanges(unittest.TestCase):
    def test_split_ref_and_vlookup_parts(self) -> None:
        self.assertEqual(
            FT.split_ref("Prices!$A$2:$D$21"), ("Prices!", (1, 2, 4, 21), True, False)
        )
        self.assertEqual(
            FT.vlookup_parts(["A2", "P!$A$2:$D$9", "3", "FALSE"]),
            ("A2", "P!$A$2:$A$9", "P!$C$2:$C$9"),
        )
        self.assertIsNone(FT.vlookup_parts(["A2", "P!$A$2:$D$9", "5", "FALSE"]))
        self.assertIsNone(FT.vlookup_parts(["A2", "P!$A$2:$D$9", "3", "TRUE"]))

    def test_literal_spans_skip_references_and_ordinary_numbers(self) -> None:
        formula = "=A1*1.07+B12*12"
        spans = FT.literal_spans(formula)
        self.assertEqual([t for _, _, t in spans], ["1.07"])
        a, b, _ = spans[0]
        self.assertEqual(formula[a:b], "1.07")


class TestPatternSource(unittest.TestCase):
    def test_left_neighbor_is_the_source_when_the_row_agrees(self) -> None:
        def build(ws, wb):
            ws.title = "S"
            for c in range(1, 6):
                ws.cell(1, c, c)
            ws["A2"], ws["B2"], ws["C2"], ws["D2"] = "=A1*2", "=B1*2", 9, "=D1*2"

        s = load(workbook_bytes(build)).sheets["S"]
        src = FT.pattern_source(s, 2, 3)
        self.assertEqual(src.coord, "B2")
        self.assertEqual(FT.translate(src, 2, 3), "=C1*2")


if __name__ == "__main__":
    unittest.main()
