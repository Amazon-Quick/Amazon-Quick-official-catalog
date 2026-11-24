"""
description: Unit tests for series_stats. Filesystem-free: checks the clean-room incomplete beta against published Student's t values, the Qn scatter against its definition, and the Qn size cap.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import itertools
import unittest

import numpy as np
import series_stats as st


class TestStudentT(unittest.TestCase):
    def test_t_cdf_matches_published_values(self) -> None:
        self.assertAlmostEqual(st.t_cdf(2.0, 10), 0.96330598, places=7)
        self.assertAlmostEqual(st.t_cdf(-1.5, 4), 0.104, places=9)  # exact for df = 4

    def test_t_ppf_matches_published_values(self) -> None:
        self.assertAlmostEqual(st.t_ppf(0.975, 10), 2.22813885, places=7)
        self.assertAlmostEqual(st.t_ppf(0.995, 30), 2.74999565, places=7)

    def test_generalized_esd_finds_the_one_outlier(self) -> None:
        sample = [1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 3, 2, 1, 2, 30]
        self.assertEqual(st.generalized_esd(sample)["outliers"], [14])


class TestQnScale(unittest.TestCase):
    def test_qn_is_the_kth_smallest_pairwise_distance(self) -> None:
        sample = np.random.default_rng(3).normal(size=41)
        dist = sorted(abs(a - b) for a, b in itertools.combinations(sample, 2))
        h = 41 // 2 + 1
        expected = 2.21914 * (41 / (41 + 1.4)) * dist[h * (h - 1) // 2 - 1]
        self.assertAlmostEqual(st.qn_scale(sample), expected, places=12)

    def test_qn_refuses_more_points_than_the_cap(self) -> None:
        with self.assertRaises(ValueError):
            st.qn_scale(np.zeros(st.MAX_QN_POINTS + 1))


if __name__ == "__main__":
    unittest.main()
