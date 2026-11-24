"""
description: Unit tests for series_review.run defaults. Filesystem-free: no output path is given, so nothing is written.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime as dt
import unittest

import series_review as sr


class TestRunDefaults(unittest.TestCase):
    def test_no_workbook_unless_a_path_is_given(self) -> None:
        dates = [f"{2023 + i // 12}-{i % 12 + 1:02d}-01" for i in range(24)]
        res = sr.run(
            {"Revenue": {"dates": dates, "values": [100.0 + i for i in range(24)]}},
            freq="monthly",
            today=dt.date(2026, 11, 24),
        )
        self.assertIsNone(res["path"])


if __name__ == "__main__":
    unittest.main()
