"""
description: Unit test for stat_core: series cleaning and the P10/P90 helper, on injected arrays (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import numpy as np
from stat_core import ClassicalError, clean_series, quantiles, season_length


class TestStatCore(unittest.TestCase):
    def test_clean_series_trims_edges_and_interpolates_gaps(self) -> None:
        y = clean_series(np.array([np.nan, 1.0, np.nan, 3.0, np.inf]))
        np.testing.assert_allclose(y, [1.0, 2.0, 3.0])

    def test_clean_series_rejects_all_missing(self) -> None:
        with self.assertRaises(ClassicalError):
            clean_series(np.array([np.nan, np.nan]))

    def test_quantiles_are_symmetric_around_the_mean(self) -> None:
        lo, mid, hi = quantiles(np.array([10.0]), np.array([1.0]))
        self.assertAlmostEqual(float(mid[0] - lo[0]), float(hi[0] - mid[0]))

    def test_season_length_rejects_legacy_codes(self) -> None:
        self.assertEqual(season_length("MS"), 12)
        with self.assertRaises(ClassicalError):
            season_length("AS")


if __name__ == "__main__":
    unittest.main()
