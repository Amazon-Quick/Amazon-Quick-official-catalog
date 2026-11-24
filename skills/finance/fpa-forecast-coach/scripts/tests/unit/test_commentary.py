"""
description: Unit test for commentary: an all-zero series does not break the summary (comment 4674175288), and the stated wording (no versus, no promos) on injected forecasts (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

import numpy as np
from commentary import flags, summary


def _fc(values):
    a = np.asarray(values, dtype=float)
    return {"p10": a, "p50": a, "p90": a, "method": "ETS-Theta average"}


class TestCommentary(unittest.TestCase):
    def test_zero_series_is_skipped_in_growth(self) -> None:
        fc = {"Z": _fc([0.0, 0.0, 0.0]), "R": _fc([1.0, 2.0, 3.0])}
        lines = summary(
            ["Z", "R"], fc, {"Z": {}, "R": {}}, ["a", "b", "c"], "", [], [], []
        )
        self.assertTrue(any("strongest R" in line for line in lines))

    def test_stock_is_read_at_the_end(self) -> None:
        fc = {"Inv": _fc([5.0, 6.0, 7.0])}
        lines = summary(
            ["Inv"], fc, {"Inv": {}}, ["a", "b", "c"], "", [], [], [], stocks={"Inv"}
        )
        self.assertIn("Inv 7.0 at c", lines[1])

    def test_flags_use_plain_wording(self) -> None:
        text = " ".join(
            flags({"S": {"values": np.ones(40)}}, {"S": {}}, 12, [], [0.95])
        )
        self.assertNotIn("versus", text)
        self.assertNotIn("promos", text)


if __name__ == "__main__":
    unittest.main()
