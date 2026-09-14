"""
description: Unit tests for completion_stats.py. Filesystem-free: each calculator is constructed with an injected distribution and given inputs directly, so the paired t-test, Wilcoxon signed-rank, and OLS logic are verified without reading any file or network.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from completion_stats import (
    BETACF_EPSILON,
    BETACF_FLOATING_POINT_MIN,
    BETACF_MAX_ITERATIONS,
    NormalDistribution,
    OlsRegressionCalculator,
    PairedSample,
    PairedTTestCalculator,
    RegressionRequest,
    StudentTDistribution,
    WilcoxonSignedRankCalculator,
)


def _student_t() -> StudentTDistribution:
    return StudentTDistribution(
        max_iterations=BETACF_MAX_ITERATIONS,
        epsilon=BETACF_EPSILON,
        floating_point_min=BETACF_FLOATING_POINT_MIN,
    )


class TestPairedTTestCalculator(unittest.TestCase):
    def test_detects_a_consistent_positive_shift(self) -> None:
        sample = PairedSample(
            group_a=[10.0, 12.0, 11.0, 13.0, 9.0],
            group_b=[13.0, 14.0, 14.0, 15.0, 12.0],
        )

        result = PairedTTestCalculator(_student_t()).evaluate(sample)

        self.assertEqual(result.n_pairs, 5)
        self.assertAlmostEqual(result.mean_difference, 2.6, places=12)
        self.assertTrue(result.significant_at_005)
        self.assertLess(result.p_value, 0.05)

    def test_rejects_mismatched_lengths(self) -> None:
        sample = PairedSample(group_a=[1.0, 2.0], group_b=[1.0])

        with self.assertRaises(ValueError):
            PairedTTestCalculator(_student_t()).evaluate(sample)


class TestWilcoxonSignedRankCalculator(unittest.TestCase):
    def test_drops_zero_differences_and_counts_effective_n(self) -> None:
        differences = [1.5, -2.0, 0.0, 3.0, 0.0, -0.5]

        result = WilcoxonSignedRankCalculator(NormalDistribution()).evaluate(
            differences
        )

        self.assertEqual(result.n_effective, 4)
        self.assertFalse(result.significant_at_005)

    def test_rejects_all_zero_differences(self) -> None:
        with self.assertRaises(ValueError):
            WilcoxonSignedRankCalculator(NormalDistribution()).evaluate([0.0, 0.0])


class TestOlsRegressionCalculator(unittest.TestCase):
    def test_recovers_a_known_linear_relationship(self) -> None:
        # y = 1 + 2*x exactly, so the intercept and slope are recovered.
        request = RegressionRequest(
            design_matrix=[[0.0], [1.0], [2.0], [3.0], [4.0]],
            response=[1.0, 3.0, 5.0, 7.0, 9.0],
            feature_names=["slope"],
        )

        result = OlsRegressionCalculator(_student_t()).evaluate(request)

        self.assertEqual([term.term for term in result.terms], ["const", "slope"])
        self.assertAlmostEqual(result.terms[0].coefficient, 1.0, places=9)
        self.assertAlmostEqual(result.terms[1].coefficient, 2.0, places=9)
        self.assertAlmostEqual(result.r_squared, 1.0, places=9)
        self.assertEqual(result.n_samples, 5)
        self.assertEqual(result.df_residual, 3)

    def test_default_feature_names_use_the_x_prefix(self) -> None:
        request = RegressionRequest(
            design_matrix=[[0.0], [1.0], [2.0], [3.0]],
            response=[0.0, 1.0, 2.0, 3.0],
        )

        result = OlsRegressionCalculator(_student_t()).evaluate(request)

        self.assertEqual([term.term for term in result.terms], ["const", "x1"])


if __name__ == "__main__":
    unittest.main()
