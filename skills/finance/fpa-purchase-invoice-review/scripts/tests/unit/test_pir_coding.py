"""
description: Unit tests for pir_coding: capex coded to an expense account, from an in-memory table.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_coding import cmd_coding
from pir_test_support import NS, reset_state, result, table


class TestCoding(unittest.TestCase):
    def test_capital_item_on_expense_account_is_sent_back(self) -> None:
        reset_state()
        lines = table(
            "lines",
            [
                {
                    "id": "L1",
                    "account": "6100",
                    "account_type": "expense",
                    "unit_price": "8000",
                    "amount": "8000",
                    "useful_life_months": "36",
                }
            ],
        )
        cmd_coding(
            NS(
                lines=lines,
                capex_threshold="5000",
                life_months="12",
                materiality="100",
                project_required=False,
            )
        )
        self.assertEqual(
            [f["rule"] for f in result()["findings"]],
            ["CODE-1 capex on expense account"],
        )


if __name__ == "__main__":
    unittest.main()
