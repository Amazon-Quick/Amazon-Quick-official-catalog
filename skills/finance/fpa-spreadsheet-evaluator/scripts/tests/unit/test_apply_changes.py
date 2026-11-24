"""
description: Unit tests for apply_changes: sheet XML edits with and without a namespace prefix, highlight-rule merging, output-path safety, archive limits and the re-check split. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import contextlib
import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import apply_changes as AC  # noqa: E402
import openpyxl  # noqa: E402

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
UNPREFIXED = (
    f'<?xml version="1.0"?><worksheet xmlns="{MAIN}"><sheetData>'
    '<row r="7"><c r="B7"><f>B5-B6</f><v>40</v></c><c r="C7"><v>50</v></c></row>'
    "</sheetData></worksheet>"
)
PREFIXED = (
    f'<?xml version="1.0"?><ns0:worksheet xmlns:ns0="{MAIN}"><ns0:sheetData>'
    '<ns0:row r="7"><ns0:c r="B7"><ns0:f>B5-B6</ns0:f><ns0:v>40</ns0:v></ns0:c>'
    '<ns0:c r="C7"><ns0:v>50</ns0:v></ns0:c></ns0:row>'
    "</ns0:sheetData></ns0:worksheet>"
)


class FakePackage:
    """The two things SheetXml reads from a package: the sheet's part name and its text."""

    def __init__(self, xml):
        self.xml = xml
        self.sheets = {"Summary": "xl/worksheets/sheet1.xml"}

    def text(self, _name):
        return self.xml


def sheet(xml):
    return AC.SheetXml(FakePackage(xml), "Summary", None)


class TestSetCell(unittest.TestCase):
    def test_unprefixed_sheet_gets_the_new_formula(self):
        sx = sheet(UNPREFIXED)
        sx.set_cell("C7", formula="=C5-C6")
        self.assertIn('<c r="C7"><f>C5-C6</f></c>', sx.serialize())

    def test_prefixed_sheet_gets_the_new_formula_with_its_prefix_kept(self):
        sx = sheet(PREFIXED)
        sx.set_cell("C7", formula="=C5-C6")
        out = sx.serialize()
        self.assertIn('<ns0:c r="C7"><ns0:f>C5-C6</ns0:f></ns0:c>', out)
        self.assertNotIn("<v>50</v>", out)
        self.assertTrue(out.startswith('<?xml version="1.0"?><ns0:worksheet'))

    def test_prefixed_sheet_inserts_a_missing_cell_in_column_order(self):
        sx = sheet(PREFIXED)
        sx.set_cell("A7", value="Gross profit")
        out = sx.serialize()
        self.assertLess(out.index('r="A7"'), out.index('r="B7"'))
        self.assertIn("<ns0:is><ns0:t", out)

    def test_prefix_bound_to_another_namespace_is_refused(self):
        xml = PREFIXED.replace(MAIN, "urn:other")
        with self.assertRaises(ValueError):
            sheet(xml)

    def test_style_only_edit_on_a_missing_cell_is_refused(self):
        with self.assertRaises(ValueError):
            sheet(UNPREFIXED).set_cell("D7", s="3")


def cf_block(sqref, priority, dxf="0", formula="5"):
    return (
        f'<conditionalFormatting sqref="{sqref}"><cfRule type="cellIs" dxfId="{dxf}" '
        f'priority="{priority}" operator="greaterThan"><formula>{formula}</formula></cfRule>'
        "</conditionalFormatting>"
    )


def cf_sheet(*blocks):
    return f'<worksheet xmlns="{MAIN}"><sheetData/>' + "".join(blocks) + "</worksheet>"


class TestCfMerge(unittest.TestCase):
    def test_copies_of_one_rule_become_one_block(self):
        sx = sheet(cf_sheet(cf_block("A1", 1), cf_block("A2", 2), cf_block("A3", 3)))
        sx.cf_merge(["A1", "A2", "A3"], "A1:A3")
        out = sx.serialize()
        self.assertEqual(out.count("<conditionalFormatting"), 1)
        self.assertIn('sqref="A1:A3"', out)

    def test_a_different_rule_on_the_same_range_is_kept(self):
        other = cf_block("A1", 9, dxf="4", formula="100")
        sx = sheet(cf_sheet(cf_block("A1", 1), cf_block("A2", 2), other))
        sx.cf_merge(["A1", "A2"], "A1:A2")
        out = sx.serialize()
        self.assertIn(other, out)
        self.assertEqual(out.count("<conditionalFormatting"), 2)

    def test_copies_with_different_formats_are_not_merged(self):
        sx = sheet(cf_sheet(cf_block("A1", 1, dxf="0"), cf_block("A2", 2, dxf="1")))
        with self.assertRaises(ValueError):
            sx.cf_merge(["A1", "A2"], "A1:A2")

    def test_a_block_with_two_rules_is_not_merged(self):
        two = cf_block("A2", 2).replace(
            "</conditionalFormatting>",
            '<cfRule type="cellIs" dxfId="1" priority="5" operator="lessThan">'
            "<formula>0</formula></cfRule></conditionalFormatting>",
        )
        sx = sheet(cf_sheet(cf_block("A1", 1), two))
        with self.assertRaises(ValueError):
            sx.cf_merge(["A1", "A2"], "A1:A2")


class FakePath:
    """Path stand-in: `inode` says which file a name points at, None if it doesn't exist."""

    def __init__(self, name, inode):
        self.name, self.inode = name, inode

    def resolve(self):
        return self.name

    def exists(self):
        return self.inode is not None

    def samefile(self, other):
        return self.inode == other.inode


class TestValidateOutput(unittest.TestCase):
    model = FakePath("/w/Budget.xlsx", 1)

    def test_another_name_for_the_model_is_refused_even_with_force(self):
        for alias in ("/w/budget.xlsx", "/w/hard-link.xlsx"):
            with (
                self.subTest(alias=alias),
                self.assertRaisesRegex(ValueError, "original"),
            ):
                AC.validate_output(self.model, FakePath(alias, 1), force=True)

    def test_the_model_path_itself_is_refused(self):
        with self.assertRaisesRegex(ValueError, "original"):
            AC.validate_output(self.model, FakePath("/w/Budget.xlsx", None), force=True)

    def test_an_existing_file_is_refused_without_force(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            AC.validate_output(self.model, FakePath("/w/other.xlsx", 2))

    def test_an_existing_file_is_allowed_with_force(self):
        AC.validate_output(self.model, FakePath("/w/other.xlsx", 2), force=True)

    def test_a_new_file_is_allowed(self):
        AC.validate_output(self.model, FakePath("/w/new.xlsx", None))


class TestPackageLimits(unittest.TestCase):
    def test_an_oversized_part_is_refused_before_it_is_read(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/media/pad.bin", b"\0" * (40 << 20))
        with self.assertRaises(ValueError):
            AC.Package(buf)


def finding(check, cell, sheet="Summary", fid=None):
    return {
        "id": fid or f"{check}-{cell}",
        "check": check,
        "severity": "warning",
        "sheet": sheet,
        "cell": cell,
        "description": "d",
    }


def change(n, edits, fids=()):
    return {"n": n, "edits": edits, "finding_ids": list(fids)}


class TestRecheck(unittest.TestCase):
    def setUp(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Summary"
        ws["C7"] = "=C5-C6"
        ws["G2"] = "=C7*2"
        ws["H9"] = "=A1"
        self.wf = wb
        typed = finding("value_in_formula_row", "C7", fid="F-1")
        self.before = {"findings": [typed]}
        self.results = [
            (
                change(
                    1,
                    [
                        {
                            "op": "cell",
                            "sheet": "Summary",
                            "cell": "C7",
                            "formula": "=C5-C6",
                        }
                    ],
                    ["F-1"],
                ),
                "applied",
                "",
            ),
            (
                change(
                    2, [{"op": "cell", "sheet": "Summary", "cell": "B2", "value": 1}]
                ),
                "skipped",
                "gone",
            ),
        ]

    def run_recheck(self, *after):
        return AC.recheck(self.before, {"findings": list(after)}, self.results, self.wf)

    def test_value_check_on_the_row_of_a_new_formula_waits_for_excel(self):
        rc = self.run_recheck(finding("period_total_mismatch", "E7"))
        self.assertEqual(rc["new"], [])
        self.assertEqual([g["cell"] for g in rc["not_rechecked"]], ["E7"])

    def test_value_check_whose_formula_reads_the_new_formula_waits_for_excel(self):
        rc = self.run_recheck(finding("tie_out_mismatch", "G2"))
        self.assertEqual([g["cell"] for g in rc["not_rechecked"]], ["G2"])

    def test_value_check_elsewhere_is_still_reported_as_new(self):
        rc = self.run_recheck(finding("tie_out_mismatch", "H9"))
        self.assertEqual([g["cell"] for g in rc["new"]], ["H9"])
        self.assertEqual(rc["not_rechecked"], [])

    def test_formula_check_on_the_same_row_is_still_reported_as_new(self):
        rc = self.run_recheck(finding("inconsistent_formula", "E7"))
        self.assertEqual([g["check"] for g in rc["new"]], ["inconsistent_formula"])

    def test_cleared_and_skipped_counts(self):
        rc = self.run_recheck()
        self.assertEqual((rc["cleared"], rc["targeted"], rc["skipped"]), (1, 1, 1))

    def test_printed_lines_name_the_waiting_checks_and_skips(self):
        rc = self.run_recheck(finding("period_total_mismatch", "E7"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            AC.print_recheck(rc)
        text = out.getvalue()
        self.assertIn(
            "1 of 1 targeted findings cleared; 0 new; 1 change skipped.", text
        )
        self.assertIn(
            "Not re-checked until Excel recalculates: 1 value check(s) on cells that read new formulas.",
            text,
        )


class TestParseApprove(unittest.TestCase):
    changes = [
        {"n": 1, "risk": "safe"},
        {"n": 2, "risk": "confirm"},
        {"n": 3, "risk": "safe"},
    ]

    def test_safe_skips_confirm_marked_changes(self):
        self.assertEqual(AC.parse_approve("safe", self.changes), [1, 3])

    def test_ranges_and_lists(self):
        self.assertEqual(AC.parse_approve("1, 2-3", self.changes), [1, 2, 3])

    def test_unknown_number_stops(self):
        with self.assertRaises(SystemExit):
            AC.parse_approve("4", self.changes)

    def test_huge_range_is_refused_before_it_is_expanded(self) -> None:
        with self.assertRaises(SystemExit):
            AC.parse_approve("1-999999999", self.changes)


if __name__ == "__main__":
    unittest.main()
