"""
description: Unit test for backtest: method picking and the like-for-like backtest scores on an injected series (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import finance_methods as fm
import numpy as np
from backtest import backtest_all, method_order, pick_method


class TestBacktest(unittest.TestCase):
    def test_pick_method_resolves_prefixes_and_falls_back(self) -> None:
        available = [fm.MODEL_LABEL, "T12M run-rate", "Prior year x YoY"]
        self.assertEqual(pick_method("t12m", "S", available, None), "T12M run-rate")
        self.assertEqual(pick_method("nonsense", "S", available, None), fm.MODEL_LABEL)
        self.assertEqual(
            pick_method("best", "S", available, "Prior year x YoY"), "Prior year x YoY"
        )

    def test_baseline_comes_first(self) -> None:
        self.assertEqual(method_order("MS", 12)[0], fm.MODEL_LABEL)

    def test_backtest_scores_every_method_on_two_folds(self) -> None:
        values = np.array(
            [100 + 2 * i + 5 * (i % 12 == 11) for i in range(48)], dtype=float
        )
        out = backtest_all(values, 6, 2, 12, "MS")
        self.assertEqual(len(out["folds"]), 2)
        self.assertIn(fm.MODEL_LABEL, out["average"]["methods"])


if __name__ == "__main__":
    unittest.main()
