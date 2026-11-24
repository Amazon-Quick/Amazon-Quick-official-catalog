"""
description: Unit tests for scenario_config.validate_config: every resource limit and malformed setting raises a question before anything is allocated. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from scenario_config import DEFAULT_CONFIG, MAX_ITERATIONS, validate_config
from scenario_intake import ClarificationRequired


def config(**changes) -> dict:
    return {**DEFAULT_CONFIG, **changes}


class TestValidateConfig(unittest.TestCase):
    def test_defaults_pass(self) -> None:
        self.assertEqual(validate_config(config()), (12, 10000))

    def test_iterations_above_the_limit_raise(self) -> None:
        with self.assertRaises(ClarificationRequired):
            validate_config(config(mc_iterations=MAX_ITERATIONS + 1))

    def test_huge_fiscal_year_raises(self) -> None:
        with self.assertRaises(ClarificationRequired):
            validate_config(config(fy_length_periods=10**7))

    def test_iterations_times_periods_above_the_cell_limit_raise(self) -> None:
        with self.assertRaises(ClarificationRequired):
            validate_config(config(mc_iterations=MAX_ITERATIONS, fy_length_periods=366))

    def test_percentiles_out_of_order_raise(self) -> None:
        with self.assertRaises(ClarificationRequired):
            validate_config(config(bear_percentile=90, bull_percentile=10))

    def test_percentile_above_100_raises(self) -> None:
        with self.assertRaises(ClarificationRequired):
            validate_config(config(bull_percentile=150))

    def test_negative_timing_sigma_raises(self) -> None:
        with self.assertRaises(ClarificationRequired):
            validate_config(config(driver_timing_sigma=-1))

    def test_short_seasonality_profile_raises(self) -> None:
        with self.assertRaises(ClarificationRequired):
            validate_config(config(seasonality_profile=[1, 1, 1]))

    def test_non_numeric_judgment_range_raises(self) -> None:
        bad = [{"label": "Price", "low": "a", "likely": 1, "high": 2}]
        with self.assertRaises(ClarificationRequired):
            validate_config(config(judgment_adjustments=bad))

    def test_judgment_range_out_of_order_raises(self) -> None:
        bad = [{"label": "Price", "low": 5, "likely": 1, "high": 2}]
        with self.assertRaises(ClarificationRequired):
            validate_config(config(judgment_adjustments=bad))

    def test_too_many_drivers_raise(self) -> None:
        with self.assertRaises(ClarificationRequired):
            validate_config(config(), n_drivers=10_000)


if __name__ == "__main__":
    unittest.main()
