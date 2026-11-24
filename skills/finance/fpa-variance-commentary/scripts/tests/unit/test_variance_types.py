"""
description: Unit tests for variance_types: names ending in a revenue word are revenue even with a cost word inside, 'cost of' lines are costs, and direction comes from the line type, never the sign alone. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest

from variance_types import direction, infer_type


class TestInferType(unittest.TestCase):
    def test_revenue_ending_wins_over_cost_words(self) -> None:
        for name in (
            "License revenue",
            "Fee income",
            "Rental income",
            "Interest income",
        ):
            with self.subTest(name=name):
                self.assertEqual(infer_type(name), "revenue")

    def test_cost_names_stay_costs(self) -> None:
        for name in (
            "Cost of revenue",
            "Cost of sales",
            "Income tax",
            "Travel",
            "Rent",
        ):
            with self.subTest(name=name):
                self.assertEqual(infer_type(name), "cost")

    def test_profit_ratio_and_metric(self) -> None:
        self.assertEqual(infer_type("Net income"), "profit")
        self.assertEqual(infer_type("Gross margin %"), "ratio")
        self.assertEqual(infer_type("Headcount"), "metric")


class TestDirection(unittest.TestCase):
    @staticmethod
    def _row(line_type: str, variance: float | None, fav: str | None = None) -> dict:
        return {
            "line": "x",
            "type": line_type,
            "variance": variance,
            "favorable_when": fav,
        }

    def test_cost_increase_is_unfavorable(self) -> None:
        self.assertEqual(direction(self._row("cost", 1.0)), "U")
        self.assertEqual(direction(self._row("revenue", 1.0)), "F")

    def test_unknown_direction_asks(self) -> None:
        self.assertEqual(direction(self._row("metric", 1.0)), "ask")
        self.assertEqual(direction(self._row("metric", 1.0, "neutral")), "neutral")
        self.assertEqual(direction(self._row("cost", None)), "n/a")


if __name__ == "__main__":
    unittest.main()
