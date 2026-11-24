"""
description: Unit tests for pir_justification: blank text is JUS-1 and a missing template element is JUS-2.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_justification import cmd_justification
from pir_test_support import NS, reset_state, result, table


class TestJustification(unittest.TestCase):
    def test_blank_justification_is_sent_back(self) -> None:
        reset_state()
        reqs = table("req", [{"id": "R1", "justification": ""}])
        cmd_justification(NS(requests=reqs))
        self.assertEqual(
            [f["rule"] for f in result()["findings"]], ["JUS-1 justification missing"]
        )

    def test_missing_template_element_is_flagged(self) -> None:
        reset_state()
        reqs = table(
            "req",
            [{"id": "R1", "justification": "WHAT: two switches. WHY: end of life."}],
        )
        template = table(
            "tpl", [{"element": "WHAT"}, {"element": "WHY"}, {"element": "BUDGET"}]
        )
        cmd_justification(NS(requests=reqs, template_fields=template))
        self.assertEqual([f["number"] for f in result()["findings"]], ["BUDGET"])


if __name__ == "__main__":
    unittest.main()
