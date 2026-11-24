"""
description: Unit test for scenario_segments.segment_screen on a two-segment table built in code. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

import pandas as pd
from scenario_segments import segment_screen


class TestSegmentScreen(unittest.TestCase):
    def test_ranks_the_segment_furthest_behind_first(self) -> None:
        df = pd.DataFrame(
            {
                "period": list(pd.date_range("2026-01-01", periods=3, freq="MS")) * 2,
                "measure": [10.0, 10, 10, 12, 12, 12],
                "benchmark": [11.0] * 6,
                "segment": ["North"] * 3 + ["South"] * 3,
            }
        )
        rows = segment_screen(df)
        self.assertEqual([r["segment"] for r in rows], ["North", "South"])
        self.assertEqual([r["status"] for r in rows], ["Behind", "Ahead"])

    def test_no_segment_column_returns_empty(self) -> None:
        self.assertEqual(segment_screen(pd.DataFrame({"measure": [1.0]})), [])


if __name__ == "__main__":
    unittest.main()
