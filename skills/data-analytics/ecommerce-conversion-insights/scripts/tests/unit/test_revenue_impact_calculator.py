"""
description: Unit test for revenue_impact_calculator pure logic. Filesystem-free: StageConverter and TwoProportionTest receive injected data and numbers, so conversion math and the Z-score are verified without any file or network access.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from revenue_impact_calculator import StageConverter, TwoProportionTest


class TestStageConverter(unittest.TestCase):
    def test_computes_conversion_and_drop_off_between_stages(self) -> None:
        data = [
            {"stage": "A", "visitors": 1000},
            {"stage": "B", "visitors": 250},
        ]

        conversions = StageConverter(data, ["A", "B"]).convert()

        self.assertEqual(conversions.stage_totals, {"A": 1000, "B": 250})
        transition = conversions.transitions[0]
        self.assertEqual(transition.from_visitors, 1000)
        self.assertEqual(transition.to_visitors, 250)
        self.assertEqual(transition.conversion_rate, 25.0)
        self.assertEqual(transition.drop_off_rate, 75.0)
        self.assertEqual(transition.visitors_lost, 750)

    def test_zero_source_visitors_yields_integer_zero_conversion(self) -> None:
        data = [{"stage": "B", "visitors": 400}]

        conversions = StageConverter(data, ["A", "B"]).convert()

        transition = conversions.transitions[0]
        self.assertEqual(transition.conversion_rate, 0)
        self.assertEqual(transition.drop_off_rate, 100)


class TestTwoProportionTest(unittest.TestCase):
    def test_zero_sample_size_returns_zero_z_score(self) -> None:
        result = TwoProportionTest(0.5, 0, 0.4, 1000).test()

        self.assertEqual(result.z_score, 0.0)


if __name__ == "__main__":
    unittest.main()
