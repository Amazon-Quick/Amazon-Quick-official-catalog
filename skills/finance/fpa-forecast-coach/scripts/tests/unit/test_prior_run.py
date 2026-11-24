"""
description: Unit test for prior_run.bands_by_period on injected Bands rows: per-period values and defanged names (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from prior_run import bands_by_period


class TestBandsByPeriod(unittest.TestCase):
    def test_reads_p50_per_series_and_period(self) -> None:
        rows = [
            ("Rev", "Jan-27", 9.0, 10.0, 11.0, 0.2),
            ("Rev", "Feb-27", 9.0, 12.0, 13.0, 0.3),
        ]
        self.assertEqual(
            bands_by_period(rows), {"Rev": {"Jan-27": 10.0, "Feb-27": 12.0}}
        )

    def test_strips_the_formula_guard_from_names(self) -> None:
        self.assertIn(
            "-Returns", bands_by_period([("'-Returns", "Jan-27", 1.0, 2.0, 3.0, 0.1)])
        )

    def test_repeated_period_is_rejected(self) -> None:
        rows = [("Rev", "Jan-27", 1.0, 2.0, 3.0, 0.1)] * 2
        with self.assertRaises(ValueError):
            bands_by_period(rows)

    def test_empty_sheet_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            bands_by_period([])


if __name__ == "__main__":
    unittest.main()
