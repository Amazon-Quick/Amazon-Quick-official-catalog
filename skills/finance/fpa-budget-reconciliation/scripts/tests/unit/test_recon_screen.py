"""
description: Unit tests for recon_screen: headcount is compared at one month with open requisitions, and a repeated invoice number is flagged for inspection with file text bounded in its reason. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest
from datetime import date

from recon_models import HeadcountRow, InvoiceRow, Rules, Tier
from recon_screen import HeadcountScreen, OutlierScreen


class TestHeadcountScreen(unittest.TestCase):
    def test_open_requisitions_that_overshoot_plan_are_called_out(self) -> None:
        rows = [
            HeadcountRow(
                key="Eng",
                keys={"department": "Eng"},
                period=p,
                plan=138,
                actual=130,
                open_reqs=12,
            )
            for p in ("2026-08", "2026-09")
        ]
        flags = HeadcountScreen(Rules(), "2026-09").screen(rows)
        self.assertEqual(len(flags), 1)
        self.assertIn("committed", flags[0].tests)
        self.assertIn("130 heads against 138", flags[0].reason)


class TestOutlierScreen(unittest.TestCase):
    def test_repeated_invoice_number_is_an_inspect_item(self) -> None:
        invoice = InvoiceRow(
            invoice_number="INV-9" + "9" * 5000,
            po_number="",
            key="Eng",
            vendor="Example Vendor " + "x" * 5000,
            invoice_date="2026-09-01",
            amount=100.0,
            status="approved",
            posted=False,
            days_unposted=5,
        )
        screen = OutlierScreen(Rules(), "$", 1000.0, 500.0, "2026-09")
        flags = screen.screen([], {}, {}, [], [invoice, invoice], date(2026, 10, 1))
        kinds = {f.kind for f in flags}
        self.assertTrue(all(len(f.reason) < 300 for f in flags))
        self.assertIn("duplicate_invoice", kinds)
        self.assertTrue(all(f.tier == Tier.INSPECT for f in flags))


if __name__ == "__main__":
    unittest.main()
