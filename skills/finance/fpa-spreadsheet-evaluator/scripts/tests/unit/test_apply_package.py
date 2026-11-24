"""
description: Unit tests for apply_package: sheet part discovery, on-demand part reads, number-format styles and output-path safety. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_package as AP  # noqa: E402
from workbook_fixtures import workbook_bytes  # noqa: E402


def two_tabs(ws, wb):
    ws.title = "P&L"
    ws["A1"] = 1
    wb.create_sheet("Data")["A1"] = 2


class FakePath:
    def __init__(self, name, inode):
        self.name, self.inode = name, inode

    def resolve(self):
        return self.name

    def exists(self):
        return self.inode is not None

    def samefile(self, other):
        return self.inode == other.inode


class TestPackage(unittest.TestCase):
    def setUp(self) -> None:
        self.pkg = AP.Package(workbook_bytes(two_tabs))

    def test_sheet_names_map_to_their_parts(self) -> None:
        self.assertEqual(
            self.pkg.sheets,
            {"P&L": "xl/worksheets/sheet1.xml", "Data": "xl/worksheets/sheet2.xml"},
        )
        self.assertIn("<sheetData>", self.pkg.text(self.pkg.sheets["Data"]))
        self.assertEqual(self.pkg.sheet_rel_targets("P&L", "comments"), [])

    def test_put_marks_a_part_dirty(self) -> None:
        self.pkg.put("xl/worksheets/sheet1.xml", "<worksheet/>")
        self.assertEqual(self.pkg.dirty, {"xl/worksheets/sheet1.xml"})
        self.assertEqual(self.pkg.text("xl/worksheets/sheet1.xml"), "<worksheet/>")

    def test_with_numfmt_appends_one_style_and_caches_it(self) -> None:
        styles = AP.Styles(self.pkg)
        before = len(re.findall(r"<xf\b", self.pkg.text("xl/styles.xml")))
        idx = styles.with_numfmt(0, 10)
        self.assertEqual(styles.with_numfmt(0, 10), idx)
        xml = self.pkg.text("xl/styles.xml")
        cell_xfs = re.search(r"<cellXfs\b[^>]*>(.*?)</cellXfs>", xml, re.S).group(1)
        new_xf = re.findall(r"<xf\b[^>]*>", cell_xfs)[idx]
        self.assertIn('numFmtId="10"', new_xf)
        self.assertIn('applyNumberFormat="1"', new_xf)
        self.assertEqual(len(re.findall(r"<xf\b", xml)), before + 1)


class TestValidateOutput(unittest.TestCase):
    def test_the_model_is_never_overwritten(self) -> None:
        model = FakePath("/w/m.xlsx", 1)
        with self.assertRaisesRegex(ValueError, "original"):
            AP.validate_output(model, FakePath("/w/alias.xlsx", 1), force=True)
        with self.assertRaisesRegex(ValueError, "already exists"):
            AP.validate_output(model, FakePath("/w/o.xlsx", 2))
        AP.validate_output(model, FakePath("/w/new.xlsx", None))


if __name__ == "__main__":
    unittest.main()
