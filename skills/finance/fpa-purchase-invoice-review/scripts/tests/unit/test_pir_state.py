"""
description: Unit tests for pir_state: an emitted result does not change when the shared state is reset.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from pir_state import _IGNORED_TABLES, _STATE, _emit
from pir_test_support import reset_state


class TestState(unittest.TestCase):
    def test_emitted_result_is_independent_of_shared_state(self) -> None:
        reset_state()
        _IGNORED_TABLES.append({"type": "budget"})
        _emit({"ok": False, "questions": [{"tables": _IGNORED_TABLES}]})
        res = _STATE["result"]
        _IGNORED_TABLES.clear()
        self.assertEqual(res["questions"][0]["tables"], [{"type": "budget"}])
        self.assertEqual(res["ignored_tables"], [{"type": "budget"}])


if __name__ == "__main__":
    unittest.main()
