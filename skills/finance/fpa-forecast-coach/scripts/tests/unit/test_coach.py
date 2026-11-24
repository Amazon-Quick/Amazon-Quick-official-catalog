"""
description: Unit test for coach: input checks (horizon cap, required out_path), stock names as a string, series that end early, and the returned totals reading a balance at the end of the horizon (RUN-2). No filesystem.
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import datetime as dt
import unittest

import numpy as np
import stat_methods as sm
from coach import _check_inputs, _result, _same_end, _stocks, max_horizon
from run_context import RunContext


class TestCoach(unittest.TestCase):
    def test_horizon_is_capped(self) -> None:
        with self.assertRaises(ValueError):
            _check_inputs(max_horizon(12) + 1, 12, "x.xlsx")

    def test_out_path_is_required(self) -> None:
        with self.assertRaises(ValueError):
            _check_inputs(12, 12, None)

    def test_stock_given_as_one_name(self) -> None:
        self.assertEqual(
            _stocks("Inventory", {"Inventory": {}, "Revenue": {}}),
            frozenset({"Inventory"}),
        )

    def test_series_ending_early_is_skipped(self) -> None:
        clean = {
            "A": {"values": [1.0], "dates": [dt.date(2026, 9, 1)]},
            "B": {"values": [1.0], "dates": [dt.date(2024, 8, 1)]},
        }
        issues: list = []
        self.assertEqual(list(_same_end(clean, issues)), ["A"])
        self.assertIn("B: skipped", issues[0])

    def test_returned_totals_read_a_balance_at_the_end(self) -> None:
        p50 = np.array([1.0, 2.0, 3.0])
        fc = {"Inv": {"p10": p50, "p50": p50, "p90": p50, "method": sm.ETS_THETA_NAME}}
        ctx = RunContext(
            ["Inv"],
            {},
            fc,
            {"Inv": {}},
            {"Inv": {sm.BASELINE_LABEL: p50}},
            {"Inv": []},
            {"Inv": sm.BASELINE_LABEL},
            frozenset({"Inv"}),
            ["a", "b", "c"],
            3,
            "MS",
            12,
            "",
            "t",
            "id",
        )
        res = _result(ctx, "x.xlsx", [], [], [], [], [])
        self.assertEqual(res["methods"]["Inv"]["totals"][sm.BASELINE_LABEL], 3.0)
        self.assertTrue(res["methods"]["Inv"]["is_stock"])


if __name__ == "__main__":
    unittest.main()
