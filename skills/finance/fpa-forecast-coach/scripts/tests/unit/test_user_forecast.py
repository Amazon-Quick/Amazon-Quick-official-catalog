"""
description: Unit test for user_forecast: the summary survives a zero baseline total, and periods outside the band are flagged. In-memory workbook, no filesystem.
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import io
import unittest

import numpy as np
import xlsxwriter
from user_forecast import user_summary, write_user_comparison
from workbook_formats import WORKBOOK_OPTIONS, formats


class TestUserForecast(unittest.TestCase):
    def test_summary_with_zero_baseline_total(self) -> None:
        gaps = [
            {
                "series": "S",
                "your_total": 5.0,
                "model_total": 0.0,
                "delta": 5.0,
                "delta_pct": 0.0,
                "n_outside": 0,
            }
        ]
        self.assertIn("you total 5.0", user_summary(gaps, "")[0])

    def test_outside_band_is_flagged(self) -> None:
        a = np.array([10.0, 10.0])
        fc = {"S": {"p10": a - 1, "p50": a, "p90": a + 1}}
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {**WORKBOOK_OPTIONS, "in_memory": True})
        out = write_user_comparison(
            wb, formats(wb), ["S"], fc, {"S": [10.0, 50.0]}, ["a", "b"], 2, ""
        )
        wb.close()
        self.assertEqual(out[0]["n_outside"], 1)
        self.assertIn("outside the baseline's P10 to P90 band", out[0]["flag"])


if __name__ == "__main__":
    unittest.main()
