"""
description: Unit tests for pir_all: a PO on its own is an item, and the profile's grain and fiscal start month reach the budget check.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_test_support import run_message

PO_ONLY = (
    "| po | line | item | qty | unit_price | amount | vendor | contract_id | justification |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
    "| PO-900 | 1 | consulting hours | 200 | 150 | 30000 | B | MSA-1 | Audit prep consulting |\n\n"
    "| contract_id | vendor | ceiling | start | end |\n|---|---|---|---|---|\n"
    "| MSA-1 | B | 25000 | 2026-01-01 | 2026-12-31 |\n"
)


class TestAll(unittest.TestCase):
    def test_po_without_requisition_is_reviewed_as_an_item(self) -> None:
        res = run_message(PO_ONLY, "--tiers", "10000,50000")
        self.assertEqual(res["totals"]["all_count"], 1)
        self.assertEqual(res["items"][0]["type"], "po")
        self.assertEqual(res["items"][0]["amount"], "30000.00")
        self.assertEqual(res["justification_rows"][0]["text"], "Audit prep consulting")
        self.assertIn("approval", res["modules_run"])
        self.assertEqual(res["overall_verdict"], {"PO-900": "Hold"})

    def test_grain_and_fiscal_start_are_accepted(self) -> None:
        msg = (
            "| id | vendor | amount | project | period |\n|---|---|---|---|---|\n| R1 | A | 100 | P1 | 2026-02 |\n\n"
            "| project | period | source | amount |\n|---|---|---|---|\n| P1 | 2026-02 | budget | 50 |\n"
        )
        res = run_message(msg, "--grain", "project", "--fiscal-start-month", "2")
        self.assertTrue(res["ok"], res.get("error"))
        budget = [f for f in res["findings"] if f["module"] == "budget"]
        self.assertIn("FY2027-Q1", budget[0]["number"])

    def test_default_grain_is_labeled_assumption(self) -> None:
        msg = (
            "| id | vendor | amount | cost_center | account | period |\n|---|---|---|---|---|---|\n"
            "| R1 | A | 100 | CC1 | 6100 | 2026-10 |\n\n"
            "| cost_center | account | period | source | amount |\n|---|---|---|---|---|\n| CC1 | 6100 | 2026-10 | budget | 500 |\n"
        )
        res = run_message(msg)
        self.assertTrue(
            any(n.startswith("ASSUMPTION: budget grain") for n in res["notes"])
        )


if __name__ == "__main__":
    unittest.main()
