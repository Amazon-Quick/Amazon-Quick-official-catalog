"""
description: Unit test for target_phasing: a calendar-year window is found in the forecast labels, and the phased target sums to the target. In-memory workbook, no filesystem.
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import io
import unittest

import numpy as np
import stat_methods as sm
import xlsxwriter
from target_phasing import target_start, write_target_phasing
from workbook_formats import WORKBOOK_OPTIONS, formats


class TestTargetPhasing(unittest.TestCase):
    def test_target_start_matches_an_iso_month(self) -> None:
        self.assertEqual(
            target_start("2027-01", ["Nov 2026", "Dec 2026", "Jan 2027"]), 2
        )

    def test_unknown_start_raises(self) -> None:
        with self.assertRaises(ValueError):
            target_start("2030-01", ["Nov 2026"])

    def test_phased_total_matches_target(self) -> None:
        hist = np.array([100.0 + 10 * (i % 12) for i in range(36)])
        labels = [f"P{i}" for i in range(12)]
        fc = {"R": sm.baseline(hist, 12, "MS")}
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {**WORKBOOK_OPTIONS, "in_memory": True})
        out = write_target_phasing(
            wb,
            formats(wb),
            ["R"],
            {"R": {"values": hist}},
            fc,
            {"R": 1500.0},
            labels,
            12,
            12,
            "$K",
        )
        wb.close()
        self.assertAlmostEqual(sum(out[0]["phased"]), 1500.0)
        self.assertEqual(out[0]["window"], ["P0", "P11"])


if __name__ == "__main__":
    unittest.main()
