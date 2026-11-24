"""
description: Unit test for periods: day-first and month-first dates are never guessed (RUN-5), and period stepping and labels (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import datetime as dt
import unittest

from periods import (
    AmbiguousDateError,
    as_date,
    date_order,
    fmt_period,
    next_periods,
    normalise_freq,
)


class TestPeriods(unittest.TestCase):
    def test_ambiguous_slash_date_raises(self) -> None:
        with self.assertRaises(AmbiguousDateError):
            as_date("03/04/2025")

    def test_confirmed_order_is_used(self) -> None:
        self.assertEqual(as_date("03/04/2025", "DMY"), dt.date(2025, 4, 3))
        self.assertEqual(as_date("03/04/2025", "MDY"), dt.date(2025, 3, 4))

    def test_order_is_inferred_from_an_unambiguous_date(self) -> None:
        self.assertEqual(date_order(["13/04/2025", "01/05/2025"]), "DMY")

    def test_conflicting_orders_raise(self) -> None:
        with self.assertRaises(AmbiguousDateError):
            date_order(["13/04/2025", "04/13/2025"])

    def test_monthly_steps_and_labels(self) -> None:
        nxt = next_periods(dt.date(2026, 11, 1), 3, "MS")
        self.assertEqual(
            [fmt_period(d, "MS") for d in nxt], ["Dec 2026", "Jan 2027", "Feb 2027"]
        )

    def test_normalise_freq(self) -> None:
        self.assertEqual(normalise_freq("W-SUN"), "W")
        self.assertEqual(normalise_freq("quarterly"), "QS")


if __name__ == "__main__":
    unittest.main()
