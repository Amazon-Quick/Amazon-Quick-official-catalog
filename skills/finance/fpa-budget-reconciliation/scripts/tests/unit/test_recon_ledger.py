"""
description: Unit tests for recon_ledger: the purchase-order ledger places each ordered dollar in one bucket, and the line keyer rolls detail accounts up to plan accounts. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest
from datetime import date

import pandas as pd
from recon_ledger import CommitmentLedger, LineKeyer
from recon_models import CommitmentLink, Finding, ReconSpec

SPEC = ReconSpec.model_validate(
    {
        "last_closed_period": "2026-09",
        "grain": ["department"],
        "sources": {"plan": {"path": "plan.csv"}, "actuals": {"path": "gl.csv"}},
        "rules": {"commitment_link": CommitmentLink.BY_REFERENCE},
    }
)


class TestCommitmentLedger(unittest.TestCase):
    def test_each_ordered_dollar_is_posted_pending_or_open(self) -> None:
        gl = pd.DataFrame(
            {
                "key": ["Eng", "Eng"],
                "reference": ["PO-1", ""],
                "invoice_ref": ["INV-1", ""],
                "amount": [300.0, 50.0],
            }
        )
        pos = pd.DataFrame(
            {
                "key": ["Eng"],
                "department": ["Eng"],
                "po_number": ["PO-1"],
                "ordered": [1000.0],
                "status": ["open"],
            }
        )
        inv = pd.DataFrame(
            {
                "key": ["Eng", "Eng"],
                "invoice_number": ["INV-1", "INV-2"],
                "po_number": ["PO-1", "PO-1"],
                "amount": [300.0, 200.0],
                "status": ["paid", "approved"],
            }
        )
        rows, _, linkage, _ = CommitmentLedger(SPEC, date(2026, 10, 14)).build(
            gl, pos, inv, []
        )
        po = rows[0]
        self.assertEqual(linkage.method, "by_reference")
        self.assertEqual((po.posted, po.pending, po.open_amount), (300.0, 200.0, 500.0))
        self.assertEqual(
            po.ordered,
            po.posted + po.pending + po.open_amount + po.released - po.overrun,
        )


class TestLineKeyer(unittest.TestCase):
    def test_detail_account_rolls_up_and_unknown_stays_unplanned(self) -> None:
        keyer = LineKeyer(
            ["account"], {"account": {"6200"}}, {"account": {"6220": "6200"}}
        )
        findings: list[Finding] = []
        out = keyer.apply(
            pd.DataFrame({"account": ["6220", "6700"]}), "actuals", findings
        )
        self.assertEqual(list(out["key"]), ["6200", "6700"])
        self.assertEqual(out["unplanned_value"].iloc[1].strip(), "account=6700")


if __name__ == "__main__":
    unittest.main()
