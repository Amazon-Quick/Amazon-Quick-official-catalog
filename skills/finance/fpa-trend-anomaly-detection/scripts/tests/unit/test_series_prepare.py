"""
description: Unit tests for series_prepare.prepare. Filesystem-free: series are built in Python lists.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime as dt
import unittest

from series_prepare import MAX_LINE_PERIODS, prepare

TODAY = dt.date(2026, 11, 24)


def months(n: int, start: int = 2023) -> list:
    return [f"{start + i // 12}-{i % 12 + 1:02d}-01" for i in range(n)]


class TestPrepare(unittest.TestCase):
    def test_repeated_period_is_asked_about_not_summed(self) -> None:
        dates = months(24) + [months(24)[5]]
        prep = prepare(
            {"Revenue": {"dates": dates, "values": [100.0] * 25}},
            freq="monthly",
            today=TODAY,
        )
        self.assertEqual(prep["status"], "needs_clarification")
        self.assertIn("repeated period", prep["questions"][0])

    def test_summing_repeats_needs_the_users_confirmation(self) -> None:
        dates = months(24) + [months(24)[5]]
        prep = prepare(
            {"Revenue": {"dates": dates, "values": [100.0] * 25}},
            freq="monthly",
            today=TODAY,
            aggregate_duplicates=True,
        )
        self.assertEqual(prep["questions"], [])
        self.assertEqual(prep["lines"]["Revenue"]["values"][5], 200.0)

    def test_mistyped_year_is_asked_about(self) -> None:
        dates = months(23) + ["2204-12-01"]
        prep = prepare(
            {"Revenue": {"dates": dates, "values": [100.0] * 24}},
            freq="monthly",
            today=TODAY,
        )
        self.assertEqual(prep["status"], "needs_clarification")
        self.assertIn("mistyped", prep["questions"][0])

    def test_too_many_line_periods_is_asked_about(self) -> None:
        n_lines = MAX_LINE_PERIODS // 120 + 1
        series = {
            f"L{i}": {"dates": months(120, 2015), "values": [1.0 + i] * 120}
            for i in range(n_lines)
        }
        prep = prepare(series, freq="monthly", today=TODAY)
        self.assertEqual(prep["status"], "needs_clarification")
        self.assertIn("line-periods", prep["questions"][0])

    def test_empty_input_points_back_to_the_intake_question(self) -> None:
        with self.assertRaisesRegex(ValueError, "needs_clarification"):
            prepare({})


if __name__ == "__main__":
    unittest.main()
