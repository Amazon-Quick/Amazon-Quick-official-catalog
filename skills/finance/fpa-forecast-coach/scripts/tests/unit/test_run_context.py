"""
description: Unit test for run_context.RunContext: it is read-only once built (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import dataclasses
import unittest

from run_context import RunContext


class TestRunContext(unittest.TestCase):
    def test_is_frozen(self) -> None:
        ctx = RunContext(
            [], {}, {}, {}, {}, {}, {}, frozenset(), [], 1, "MS", 12, "", "t", "id"
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            ctx.horizon = 2  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
