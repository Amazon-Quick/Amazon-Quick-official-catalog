"""
description: Unit tests for variance_rvm: volume, mix and rate add up to the total variance, including on tables in whole dollars where totals reach into the billions, and an empty or incomplete table fails. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest

from variance_rvm import rvm

HEADER = "segment,actual_units,comparison_units,actual_rate,comparison_rate\n"


class TestRvm(unittest.TestCase):
    def test_effects_add_up_to_the_total(self) -> None:
        result = rvm(HEADER + "Pro,120,100,10,10\nEnterprise,50,60,30,28\n")
        totals = result["totals"]
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(
            totals["volume"] + totals["mix"] + totals["rate"], totals["total"]
        )
        self.assertAlmostEqual(totals["total"], 20.0)

    def test_large_tables_are_not_failed_by_float_rounding(self) -> None:
        for seed in range(200):
            rows = "".join(
                f"s{j},{100000 + (seed * 7919 + j * 104729) % 9900000}.125,"
                f"{100000 + (seed * 6151 + j * 130363) % 9900000}.375,"
                f"{10 + (seed * 37 + j * 101) % 4990}.0625,{10 + (seed * 53 + j * 89) % 4990}.8125\n"
                for j in range(5)
            )
            self.assertEqual(rvm(HEADER + rows)["status"], "PASS")

    def test_missing_value_and_empty_table_fail(self) -> None:
        self.assertEqual(rvm(HEADER + "Pro,120,,10,10\n")["status"], "FAIL")
        self.assertEqual(rvm(HEADER)["status"], "FAIL")
        self.assertEqual(rvm("segment,units\nPro,1\n")["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
