"""
description: Unit test for theta_method.forecast_theta on an injected linear series (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import numpy as np
from theta_method import forecast_theta


class TestForecastTheta(unittest.TestCase):
    def test_follows_an_upward_trend(self) -> None:
        y = 50 + 3 * np.arange(30, dtype=float)
        out = forecast_theta(y, 1, 4)
        self.assertGreater(out.p50[-1], out.p50[0])
        self.assertFalse(out.detail["seasonal"])


if __name__ == "__main__":
    unittest.main()
