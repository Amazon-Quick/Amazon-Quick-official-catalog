"""
description: Unit tests for pir_profile: at most three questions, and no built-in default for any threshold.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_profile import PROFILE_FIELDS, cmd_profile
from pir_state import THRESHOLD_FIELDS
from pir_test_support import NS, reset_state, result


class TestProfile(unittest.TestCase):
    def test_asks_at_most_three_questions(self) -> None:
        reset_state()
        cmd_profile(NS(profile=None, modules="coding,budget,approval,price,invoice"))
        self.assertEqual(len(result()["questions"]), 3)

    def test_threshold_fields_have_no_default(self) -> None:
        for field in THRESHOLD_FIELDS:
            self.assertIsNone(PROFILE_FIELDS[field][1], field)


if __name__ == "__main__":
    unittest.main()
