"""
description: Unit tests for pir_invoice: line arithmetic and exact duplicate submissions, from in-memory tables.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import time
import unittest

from pir_invoice import cmd_invoice
from pir_test_support import NS, reset_state, result, table


def _args(invoices: str, po_lines: str) -> NS:
    return NS(
        invoices=invoices,
        po_lines=po_lines,
        qty_tol="0",
        price_tol="0",
        dup_window_days=30,
    )


class TestInvoice(unittest.TestCase):
    def test_line_math_error_is_a_hold(self) -> None:
        reset_state()
        inv = table(
            "inv",
            [
                {
                    "invoice_no": "HP-1",
                    "vendor": "A",
                    "po": "PO-1",
                    "line": "1",
                    "qty": "2",
                    "unit_price": "10",
                    "amount": "25",
                }
            ],
        )
        po = table("po", [{"po": "PO-1", "line": "1", "qty": "2", "unit_price": "10"}])
        cmd_invoice(_args(inv, po))
        self.assertEqual([f["rule"] for f in result()["findings"]], ["INV-2 line math"])

    def test_resubmitted_invoice_is_an_exact_duplicate(self) -> None:
        reset_state()
        row = {
            "invoice_no": "HP-1",
            "vendor": "A",
            "po": "PO-1",
            "line": "1",
            "qty": "1",
            "unit_price": "10",
            "amount": "10",
        }
        inv = table(
            "inv",
            [
                dict(row, invoice_date="2026-09-01"),
                dict(row, invoice_date="2026-09-15"),
            ],
        )
        po = table("po", [{"po": "PO-1", "line": "1", "qty": "5", "unit_price": "10"}])
        cmd_invoice(_args(inv, po))
        dups = [f for f in result()["findings"] if f["rule"].startswith("INV-9")]
        self.assertEqual(dups[0]["item"], "HP-1 (submission 2)")

    def test_duplicate_check_scales_to_large_batches(self) -> None:
        reset_state()
        rows = [
            {
                "invoice_no": f"N{i:05d}",
                "vendor": "A",
                "amount": "100",
                "invoice_date": f"2026-{1 + i % 12:02d}-{1 + i % 28:02d}",
            }
            for i in range(6000)
        ]
        start = time.perf_counter()
        cmd_invoice(_args(table("inv", rows), table("po", [])))
        self.assertLess(time.perf_counter() - start, 20)


if __name__ == "__main__":
    unittest.main()
