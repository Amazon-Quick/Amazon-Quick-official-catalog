"""
description: Unit tests for pir_summary: the bottom-line sentence names every group that needs action.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_summary import _bottom_line_core


class TestSummary(unittest.TestCase):
    def test_bottom_line_names_every_non_ready_group(self) -> None:
        groups = [
            {
                "verdict": "Approve",
                "display": "Ready to approve",
                "count": 1,
                "amount": "30000.00",
            },
            {
                "verdict": "Approve with conditions",
                "display": "Approve with conditions",
                "count": 0,
                "amount": "0.00",
            },
            {
                "verdict": "Send back",
                "display": "Send back",
                "count": 1,
                "amount": "9500.00",
            },
            {"verdict": "Hold", "display": "Hold", "count": 1, "amount": "9800.00"},
        ]
        totals = {"all_count": 3, "all_amount": "49300.00"}
        line = _bottom_line_core(totals, groups)
        self.assertEqual(
            line,
            "Hold: 1 of 3 items, $9,800.00; 1 send back, $9,500.00; 1 ready to approve, $30,000.00.",
        )


if __name__ == "__main__":
    unittest.main()
