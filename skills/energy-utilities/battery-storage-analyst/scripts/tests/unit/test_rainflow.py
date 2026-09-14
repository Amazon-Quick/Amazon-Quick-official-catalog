"""
description: Dependency-injected unit tests for the rainflow four-point cycle counter, asserting pure logic without filesystem or network access.
last_updated: 2026-09-13
origin: original
"""

import unittest

from rainflow import (
    FULL_CYCLE_COUNT,
    HALF_CYCLE_COUNT,
    Cycle,
    RainflowCounter,
    count_cycles,
)


class RainflowCounterTest(unittest.TestCase):
    def test_count_extracts_one_full_cycle_and_one_residual(self) -> None:
        counter = RainflowCounter()

        cycles = counter.count([1.0, 3.0, 2.0, 4.0])

        self.assertEqual(
            cycles,
            [
                Cycle(1.0, 2.5, FULL_CYCLE_COUNT),
                Cycle(3.0, 2.5, HALF_CYCLE_COUNT),
            ],
        )

    def test_dedupe_collapses_plateaus(self) -> None:
        counter = RainflowCounter()

        deduped = counter._dedupe([0.5, 0.5, 0.8, 0.8, 0.5])

        self.assertEqual(deduped, [0.5, 0.8, 0.5])

    def test_short_series_yields_only_residual_half_cycles(self) -> None:
        counter = RainflowCounter()

        cycles = counter.count([0.0, 1.0, 0.0])

        self.assertEqual(
            cycles,
            [
                Cycle(1.0, 0.5, HALF_CYCLE_COUNT),
                Cycle(1.0, 0.5, HALF_CYCLE_COUNT),
            ],
        )

    def test_facade_returns_plain_tuples(self) -> None:
        result = count_cycles([1.0, 3.0, 2.0, 4.0])

        self.assertEqual(result, [(1.0, 2.5, 1.0), (3.0, 2.5, 0.5)])


if __name__ == "__main__":
    unittest.main()
