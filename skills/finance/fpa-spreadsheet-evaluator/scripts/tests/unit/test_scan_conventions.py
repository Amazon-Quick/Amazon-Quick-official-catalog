"""
description: Unit tests for scan_conventions: a legend cell sets the style convention, and cells that break the majority style are flagged. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openpyxl.styles import Font  # noqa: E402
from scan_conventions import conventions, read_legend  # noqa: E402
from scan_findings import Findings  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402

BLUE = Font(color="FF0000FF")


class TestLegend(unittest.TestCase):
    def test_legend_cell_names_the_input_style(self):
        def build(ws, wb):
            ws["A1"] = "Blue font = input"

        legend = read_legend(load(workbook_bytes(build)))
        self.assertEqual(legend, {"input": ("font", "blue", "Sheet!A1")})


class TestConventions(unittest.TestCase):
    def test_cells_breaking_the_majority_style_are_flagged(self):
        def build(ws, wb):
            ws["A1"], ws["B1"], ws["C1"] = "Item", "Input", "Calc"
            for r in range(2, 9):
                ws.cell(r, 1, f"Line {r}")
                ws.cell(r, 2, r * 10).font = BLUE
                ws.cell(r, 3, f"=B{r}*2")
            ws["B8"].font = Font()  # typed input in the default style
            ws["C7"].font = BLUE  # formula styled like an input

        wb = load(workbook_bytes(build))
        fs = Findings()
        result = conventions(wb, fs)
        self.assertEqual(result["roles"]["input"]["font"], "blue")
        self.assertFalse(result["legend"])
        found = {(i["check"], i["cell"]) for i in fs.items}
        self.assertEqual(
            found, {("input_style_break", "B8"), ("formula_styled_as_input", "C7")}
        )
        self.assertEqual(wb.notes[-1]["note"], "convention_detected")

    def test_too_few_cells_means_no_convention_and_no_findings(self):
        def build(ws, wb):
            ws["A1"], ws["B1"] = "Item", "Input"
            ws["A2"], ws["B2"] = "Rent", 5

        wb = load(workbook_bytes(build))
        fs = Findings()
        conventions(wb, fs)
        self.assertEqual(fs.items, [])
        self.assertEqual(wb.notes[-1]["note"], "no_convention_found")


if __name__ == "__main__":
    unittest.main()
