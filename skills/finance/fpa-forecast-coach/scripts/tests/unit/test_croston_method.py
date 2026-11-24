"""
description: Unit test for croston_method on an injected intermittent series (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import numpy as np
from croston_method import forecast_croston, is_intermittent
from stat_core import ClassicalError


class TestCroston(unittest.TestCase):
    def test_flat_non_negative_forecast_for_intermittent_series(self) -> None:
        y = np.array([0, 0, 5, 0, 0, 0, 7, 0, 3, 0, 0, 6], dtype=float)
        self.assertTrue(is_intermittent(y))
        out = forecast_croston(y, 4)
        self.assertTrue(np.all(out.p10 >= 0))
        self.assertAlmostEqual(float(out.p50[0]), float(out.p50[-1]))

    def test_needs_two_non_zero_values(self) -> None:
        with self.assertRaises(ClassicalError):
            forecast_croston(np.array([0, 0, 4, 0], dtype=float), 2)


if __name__ == "__main__":
    unittest.main()
