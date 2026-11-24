"""
description: Unit test for cell_notes.explain: a zero last actual gives no infinite percentage (RUN-8) on injected history (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import numpy as np
from cell_notes import explain


class TestExplain(unittest.TestCase):
    def test_zero_last_actual_has_no_infinite_percentage(self) -> None:
        hist = np.array([0.0, 5.0, 0.0, 0.0] * 6)
        text = explain("S", 0, "Jan-27", 0.0, 1.0, 2.0, hist, None, "MS", 12)
        self.assertNotIn("inf", text)
        self.assertIn("Last actual 0.0; percentage change is unavailable.", text)


if __name__ == "__main__":
    unittest.main()
