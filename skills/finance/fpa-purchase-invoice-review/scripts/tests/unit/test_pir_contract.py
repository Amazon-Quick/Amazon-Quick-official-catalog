"""
description: Unit tests for pir_contract: cumulative PO value above the contract ceiling.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_contract import cmd_contract
from pir_test_support import NS, reset_state, result, table


class TestContract(unittest.TestCase):
    def test_po_over_ceiling_is_a_hold(self) -> None:
        reset_state()
        contract = table(
            "k",
            [
                {
                    "contract_id": "MSA-1",
                    "ceiling": "25000",
                    "start": "2026-01-01",
                    "end": "2026-12-31",
                }
            ],
        )
        pos = table("po", [{"po": "PO-900", "contract_id": "MSA-1", "amount": "30000"}])
        cmd_contract(NS(contract=contract, pos=pos, renewal_warn_days=90))
        finding = result()["findings"][0]
        self.assertEqual(finding["rule"], "CON-1 over contract ceiling")
        self.assertEqual(finding["at_stake"], "5000.00")


if __name__ == "__main__":
    unittest.main()
