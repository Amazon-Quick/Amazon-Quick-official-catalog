"""
description: Unit test for ets_method.forecast_ets on an injected trending seasonal series (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import numpy as np
from ets_method import forecast_ets


class TestForecastEts(unittest.TestCase):
    def test_bands_are_ordered_and_widen(self) -> None:
        t = np.arange(48, dtype=float)
        y = 100 + 2 * t + 10 * np.sin(2 * np.pi * t / 12)
        out = forecast_ets(y, 12, 6)
        self.assertTrue(np.all(out.p10 <= out.p50) and np.all(out.p50 <= out.p90))
        self.assertGreaterEqual(out.p90[-1] - out.p10[-1], out.p90[0] - out.p10[0])
        self.assertTrue(out.detail["model"].startswith("ETS(A,"))


if __name__ == "__main__":
    unittest.main()
