"""
description: Unit tests for apply_sheet.SheetXml: trimming, frozen panes, column widths, unmerging, shared-formula unsharing and typed cell values. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import apply_sheet as AS  # noqa: E402
import openpyxl  # noqa: E402

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


class FakePackage:
    def __init__(self, xml):
        self.xml = xml
        self.sheets = {"Calc": "xl/worksheets/sheet1.xml"}

    def text(self, _name):
        return self.xml


def sheet(body, wf=None):
    xml = f'<worksheet xmlns="{MAIN}">{body}</worksheet>'
    return AS.SheetXml(FakePackage(xml), "Calc", wf)


class TestLayoutEdits(unittest.TestCase):
    def test_trim_drops_empty_rows_cells_and_columns_past_the_data(self) -> None:
        sx = sheet(
            '<dimension ref="A1:Z99"/><cols><col min="1" max="30" width="9"/></cols>'
            '<sheetData><row r="1" spans="1:9"><c r="A1"><v>1</v></c><c r="H1" s="2"/></row>'
            '<row r="50"><c r="A50" s="2"/></row></sheetData>'
        )
        sx.trim(max_row=1, max_col=2)
        out = sx.serialize()
        self.assertIn('<dimension ref="A1:B1"/>', out)
        self.assertNotIn('r="H1"', out)
        self.assertIn('max="2"', out)
        self.assertNotIn("spans", out)

    def test_trim_drops_empty_styled_rows_below_the_data(self) -> None:
        sx = sheet(
            '<sheetData><row r="1"><c r="A1"><v>1</v></c></row>'
            '<row r="50"><c r="A50" s="2"/></row></sheetData>'
        )
        sx.trim(max_row=1, max_col=2)
        self.assertNotIn('r="50"', sx.serialize())

    def test_freeze_adds_a_pane_below_the_header(self) -> None:
        sx = sheet(
            '<sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetData/>'
        )
        sx.freeze(1)
        self.assertIn('<pane ySplit="1" topLeftCell="A2"', sx.serialize())

    def test_col_width_splits_an_existing_range(self) -> None:
        sx = sheet('<cols><col min="1" max="3" width="9"/></cols><sheetData/>')
        sx.col_width("B", 20)
        out = sx.serialize()
        self.assertIn('<col min="1" max="1" width="9"/>', out)
        self.assertIn('<col min="2" max="2" width="20" customWidth="1"/>', out)
        self.assertIn('<col min="3" max="3" width="9"/>', out)

    def test_unmerge_removes_the_last_merge_block(self) -> None:
        sx = sheet(
            '<sheetData/><mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells>'
        )
        sx.unmerge("A1:B1")
        self.assertNotIn("mergeCell", sx.serialize())
        with self.assertRaises(ValueError):
            sx.unmerge("A1:B1")


class TestCellEdits(unittest.TestCase):
    def test_unshare_writes_each_cell_its_own_formula(self) -> None:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Calc"
        ws["B1"], ws["C1"] = "=A1*2", "=B1*2"
        sx = sheet(
            '<sheetData><row r="1"><c r="B1"><f t="shared" ref="B1:C1" si="0">A1*2</f></c>'
            '<c r="C1"><f t="shared" si="0"/></c></row></sheetData>',
            wf=wb,
        )
        sx.unshare(["C1"])
        out = sx.serialize()
        self.assertIn('<c r="C1"><f>B1*2</f></c>', out)
        self.assertNotIn('t="shared"', out)

    def test_numbers_and_text_get_the_right_cell_type(self) -> None:
        sx = sheet(
            '<sheetData><row r="2"><c r="A2" s="4"><v>1</v></c></row></sheetData>'
        )
        sx.set_cell("A2", value=2.5)
        sx.set_cell("B2", value="a<b")
        out = sx.serialize()
        self.assertIn('<c r="A2" s="4"><v>2.5</v></c>', out)
        self.assertIn('t="inlineStr"><is><t xml:space="preserve">a&lt;b</t>', out)
        with self.assertRaises(ValueError):
            sx.set_cell("A2", value=3, must_be_empty=True)


if __name__ == "__main__":
    unittest.main()
