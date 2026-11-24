"""
description: Unit tests for scenario_engine.run and fit_trend on tables built in code: fixture figures, bridge and per-period ties, balance closing balance, fiscal-year window, seasonality on non-positive series, provenance labels and the no-benchmark bridge label. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

import numpy as np
import pandas as pd
import scenario_engine as sa
from _fixtures import (
    BALANCE_COLMAP,
    REVENUE_COLMAP,
    UNITS,
    balance_table,
    revenue_table,
)


def revenue_df():
    return sa.prepare(revenue_table(), REVENUE_COLMAP)


class TestRunFigures(unittest.TestCase):
    def test_matches_the_clean_fixture_figures(self) -> None:
        res = sa.run(revenue_df(), UNITS)
        self.assertAlmostEqual(res["p_hit"], 0.0299, places=4)
        self.assertAlmostEqual(res["base"], 1241.509, places=3)
        self.assertEqual(res["target"], 1260.0)

    def test_bridge_and_per_period_runs_tie_to_each_scenario(self) -> None:
        summary = sa.summarize(sa.run(revenue_df(), UNITS))
        self.assertAlmostEqual(summary["bridge_gap"], 0.0, places=6)
        for gap in summary["path_gaps"].values():
            self.assertAlmostEqual(gap, 0.0, places=6)

    def test_balance_outcome_is_the_closing_balance(self) -> None:
        df = sa.prepare(balance_table(), {**BALANCE_COLMAP, "measure_type": "balance"})
        res = sa.run(df, {**UNITS, "target": 700})
        self.assertEqual(res["outcome_label"], "closing balance")
        self.assertAlmostEqual(res["base"], 725.8, places=1)


class TestFiscalWindow(unittest.TestCase):
    def test_fiscal_start_before_the_history_raises_a_question(self) -> None:
        six = pd.DataFrame(
            {
                "period": pd.date_range("2025-03-01", periods=6, freq="MS"),
                "actual": [10.0, 11, 12, 13, 12, 14],
            }
        )
        df = sa.prepare(six, {"period": "period", "measure": "actual"})
        with self.assertRaises(sa.ClarificationRequired):
            sa.run(df, {**UNITS, "fy_start_period": "2025-01", "target": 100})

    def test_iteration_limit_raises_before_simulating(self) -> None:
        with self.assertRaises(sa.ClarificationRequired):
            sa.run(revenue_df(), {**UNITS, "mc_iterations": 10**9})


class TestSeasonality(unittest.TestCase):
    def test_series_through_zero_skips_multiplicative_seasonality(self) -> None:
        y = np.array([50, 40, 30, 20, -5, -10, -8, -2, 10, 25, 35, 45] * 2, dtype=float)
        trend = sa.fit_trend(y, dict(sa.DEFAULT_CONFIG))
        self.assertTrue(trend["seasonality_source"].startswith("none ("))
        self.assertTrue(np.allclose(trend["seasonality"], 1.0))


class TestLabels(unittest.TestCase):
    def test_user_seasonality_profile_is_user_set(self) -> None:
        res = sa.run(revenue_df(), {**UNITS, "seasonality_profile": [1.0] * 12})
        row = next(a for a in res["assumptions"] if a["name"] == "Seasonality")
        self.assertEqual(row["label"], "USER-SET")

    def test_skipped_seasonality_is_default_not_data_backed(self) -> None:
        values = [50.0, 40, 30, 20, -5, -10, -8, -2, 10, 25, 35, 45] * 2
        table = pd.DataFrame(
            {
                "period": pd.date_range("2024-01-01", periods=24, freq="MS"),
                "actual": values,
            }
        )
        df = sa.prepare(table, {"period": "period", "measure": "actual"})
        res = sa.run(df, {**UNITS, "target": 100})
        row = next(a for a in res["assumptions"] if a["name"] == "Seasonality")
        self.assertEqual(row["label"], "DEFAULT")

    def test_benchmark_target_is_user_set(self) -> None:
        res = sa.run(revenue_df(), UNITS)
        row = next(a for a in res["assumptions"] if a["name"] == "Target")
        self.assertEqual(row["label"], "USER-SET")

    def test_duplicate_period_question_marks_file_text(self) -> None:
        table = pd.DataFrame(
            {
                "period": ["2026-01-01", "2026-01-01", "2026-02-01"],
                "actual": ["1", "2", "3"],
            }
        )
        df = sa.prepare(table, {"period": "period", "measure": "actual"})
        with self.assertRaises(sa.ClarificationRequired) as caught:
            sa.run(df, {**UNITS, "target": 1})
        self.assertIn("DATA (untrusted)", caught.exception.question)

    def test_no_benchmark_bridge_names_the_trend_projection(self) -> None:
        table = revenue_table().drop(columns=["Budget"])
        df = sa.prepare(table, {"period": "Month", "measure": "Revenue"})
        res = sa.run(df, {**UNITS, "target": 1260})
        self.assertEqual(
            res["bridge"][1]["label"], "Trend projection (remaining periods)"
        )

    def test_user_text_is_never_rewritten_in_labels(self) -> None:
        drivers = [
            {
                "name": "Bullock Ranch contract",
                "value": 20,
                "prob": 0.5,
                "date": "2026-11-01",
            }
        ]
        res = sa.run(
            revenue_df(),
            {**UNITS, "target_direction": "at_most", "target": 1250},
            drivers=drivers,
        )
        self.assertEqual(
            sa.summarize(res)["drivers_included"], ["Bullock Ranch contract"]
        )


if __name__ == "__main__":
    unittest.main()
