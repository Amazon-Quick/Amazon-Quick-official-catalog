"""
description: Unit tests for pir_budget: an over-invoiced PO adds no negative commitment and is reported.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_budget import cmd_budget
from pir_state import ClarificationNeeded
from pir_test_support import NS, reset_state, result, table


class TestBudget(unittest.TestCase):
    def test_over_invoiced_po_does_not_inflate_headroom(self) -> None:
        reset_state()
        key = {"cost_center": "CC1", "account": "6100", "period": "2026-10"}
        args = NS(
            budget=table("bud", [dict(key, amount="1000", source="budget")]),
            actuals=table("act", [dict(key, amount="900")]),
            commitments=table(
                "com", [dict(key, po="PO1", po_amount="500", invoiced="900")]
            ),
            requests=table("req", [dict(key, id="R1", vendor="A", amount="400")]),
            grain="cost_center,account",
            fiscal_start_month=1,
            stale_days=90,
            commit_statuses="open",
        )
        cmd_budget(args)
        res = result()
        self.assertEqual([f["rule"] for f in res["findings"]], ["BUD-2 does not fit"])
        self.assertEqual(res["findings"][0]["severity"], "HOLD")
        self.assertEqual(res["over_invoiced_commitments"][0]["overage"], "400.00")

    def test_many_planning_sources_ask_a_question(self) -> None:
        reset_state()
        key = {"cost_center": "CC1", "account": "6100", "period": "2026-10"}
        args = NS(
            budget=table(
                "bud", [dict(key, amount="10", source=f"s{i}") for i in range(11)]
            ),
            requests=table("req", [dict(key, id="R1", vendor="A", amount="1")]),
            grain="cost_center,account",
            fiscal_start_month=1,
            stale_days=90,
            commit_statuses="open",
        )
        with self.assertRaises(ClarificationNeeded):
            cmd_budget(args)


if __name__ == "__main__":
    unittest.main()
