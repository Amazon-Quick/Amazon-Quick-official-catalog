"""
description: Unit test for stat_methods.baseline: flat history forecasts flat, and an intermittent series names Croston/SBA as its method (RUN-7). No filesystem.
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import numpy as np
import stat_methods as sm


class TestBaseline(unittest.TestCase):
    def test_flat_history_forecasts_flat(self) -> None:
        out = sm.baseline([100.0] * 24, 6, "MS")
        np.testing.assert_allclose(out["p50"], 100.0)

    def test_intermittent_series_names_croston(self) -> None:
        values = [
            0,
            0,
            5,
            0,
            0,
            0,
            7,
            0,
            3,
            0,
            0,
            6,
            0,
            0,
            4,
            0,
            0,
            0,
            5,
            0,
            0,
            8,
            0,
            0,
        ] * 2
        self.assertEqual(sm.baseline(values, 6, "MS")["method"], sm.CROSTON_NAME)

    def test_regular_series_names_ets_theta(self) -> None:
        values = [100 + 3 * i + (i % 12) for i in range(36)]
        self.assertEqual(sm.baseline(values, 6, "MS")["method"], sm.ETS_THETA_NAME)

    def test_wape_and_bias(self) -> None:
        self.assertAlmostEqual(sm.wape([10, 10], [9, 11]), 0.1)
        self.assertAlmostEqual(sm.bias([10, 10], [11, 11]), 0.1)


if __name__ == "__main__":
    unittest.main()
