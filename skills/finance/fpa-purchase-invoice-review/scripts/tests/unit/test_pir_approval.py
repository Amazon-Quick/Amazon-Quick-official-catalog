"""
description: Unit tests for pir_approval: APR-2 without tiers, unreadable tiers, and split detection on a large batch.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import time
import unittest

from pir_approval import cmd_approval
from pir_state import ClarificationNeeded
from pir_test_support import NS, reset_state, result, table


def _args(requests: str, tiers: object = None) -> NS:
    return NS(
        requests=requests,
        tiers=tiers,
        split_window_days=30,
        split_margin="0.15",
        addon_warn="0.15",
    )


class TestApproval(unittest.TestCase):
    def test_large_add_on_is_flagged_without_tiers(self) -> None:
        reset_state()
        reqs = table(
            "req",
            [
                {
                    "id": "REQ-50",
                    "vendor": "C",
                    "amount": "1000",
                    "date": "2026-10-02",
                    "freight": "300",
                    "tax": "100",
                }
            ],
        )
        cmd_approval(_args(reqs))
        rules = [f["rule"] for f in result()["findings"]]
        self.assertEqual(rules, ["APR-2 large add-on"])
        skipped = [n["check"] for n in result()["not_run"]]
        self.assertEqual(skipped, ["APR-1", "APR-3"])

    def test_unreadable_tiers_ask_a_question(self) -> None:
        reset_state()
        reqs = table(
            "req", [{"id": "R1", "vendor": "C", "amount": "10", "date": "2026-10-02"}]
        )
        with self.assertRaises(ClarificationNeeded):
            cmd_approval(_args(reqs, "10k,50k"))

    def test_split_detection_scales_to_thousands_of_requests(self) -> None:
        reset_state()
        rows = [
            {
                "id": f"R{i:05d}",
                "vendor": "A",
                "requester": "Pat",
                "amount": "100",
                "date": f"2026-{1 + i % 12:02d}-{1 + i % 28:02d}",
            }
            for i in range(3000)
        ]
        start = time.perf_counter()
        cmd_approval(_args(table("req", rows), "1000000"))
        self.assertLess(time.perf_counter() - start, 10)

    def test_split_detection_same_day_batch_is_linear(self) -> None:
        reset_state()
        rows = [
            {
                "id": f"R{i:05d}",
                "vendor": "A",
                "requester": "Pat",
                "amount": "1",
                "date": "2026-10-01",
            }
            for i in range(20000)
        ]
        start = time.perf_counter()
        cmd_approval(_args(table("req", rows), "1000000"))
        self.assertLess(time.perf_counter() - start, 10)

    def test_split_found_in_window(self) -> None:
        reset_state()
        rows = [
            {
                "id": "S1",
                "vendor": "A",
                "requester": "Pat",
                "amount": "9000",
                "date": "2026-10-01",
            },
            {
                "id": "S2",
                "vendor": "A",
                "requester": "Pat",
                "amount": "8000",
                "date": "2026-10-05",
            },
            {
                "id": "S3",
                "vendor": "A",
                "requester": "Pat",
                "amount": "8000",
                "date": "2026-12-05",
            },
        ]
        cmd_approval(_args(table("req", rows), "10000,50000"))
        items = sorted(
            f["item"]
            for f in result()["findings"]
            if f["rule"] == "APR-3 possible split"
        )
        self.assertEqual(items, ["S1", "S2"])


if __name__ == "__main__":
    unittest.main()
