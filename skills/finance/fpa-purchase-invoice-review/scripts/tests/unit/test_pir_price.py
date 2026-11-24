"""
description: Unit tests for pir_price: a request with an amount and no unit price still gets the quote checks.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_price import cmd_price
from pir_test_support import NS, reset_state, result, table


class TestPrice(unittest.TestCase):
    def test_amount_only_request_runs_quote_checks(self) -> None:
        reset_state()
        args = NS(
            lines=table(
                "req",
                [{"id": "R1", "vendor": "Acme", "item": "Laptop", "amount": "90000"}],
            ),
            quotes=table(
                "quotes",
                [{"id": "R1", "amount": "90000"}, {"id": "R1", "amount": "40000"}],
            ),
            quote_threshold="25000",
            quotes_required=3,
            window_days=365,
        )
        cmd_price(args)
        rules = sorted(f["rule"] for f in result()["findings"])
        self.assertEqual(rules, ["PRC-2 quotes below policy", "PRC-4 not lowest quote"])


if __name__ == "__main__":
    unittest.main()
