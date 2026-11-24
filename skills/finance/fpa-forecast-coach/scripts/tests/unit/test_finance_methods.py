"""
description: Unit test for finance_methods: run-rates, prior year growth, and target phasing on injected lists (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import finance_methods as fm
import numpy as np


class TestFinanceMethods(unittest.TestCase):
    def test_run_rate_is_the_trailing_average(self) -> None:
        np.testing.assert_allclose(fm.run_rate([1, 2, 3, 4, 5, 6], 2, 3), [5.0, 5.0])

    def test_run_rate_needs_the_window(self) -> None:
        self.assertIsNone(fm.run_rate([1, 2], 2, 3))

    def test_phased_target_sums_to_the_target(self) -> None:
        history = [10, 20, 30, 40] * 3
        out = fm.phase_target(history, 1000.0, 4, 4)
        self.assertAlmostEqual(float(out["phased"].sum()), 1000.0)
        self.assertEqual(out["cycles"], 3)

    def test_prior_year_growth_compounds(self) -> None:
        history = [100.0] * 4 + [110.0] * 4
        out = fm.prior_year_growth(history, 8, 4)
        self.assertAlmostEqual(float(out[0]), 121.0)
        self.assertAlmostEqual(float(out[4]), 133.1)


if __name__ == "__main__":
    unittest.main()
