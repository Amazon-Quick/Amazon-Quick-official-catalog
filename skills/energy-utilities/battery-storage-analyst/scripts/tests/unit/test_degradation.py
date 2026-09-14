"""
description: Dependency-injected unit tests for the lithium-ion degradation calculators, asserting pure logic without filesystem or network access.
last_updated: 2026-09-13
origin: original
"""

import math
import unittest

from degradation import (
    FULL_CAPACITY,
    MIN_REMAINING_CAPACITY,
    R_GAS,
    CalendarAgingCalculator,
    CalendarAgingInput,
    CapacityCombiner,
    CycleDamageCalculator,
    CycleObservation,
    calendar_loss,
    cycle_damage,
    remaining_capacity,
)


class CalendarAgingCalculatorTest(unittest.TestCase):
    def test_zero_activation_energy_reduces_to_sqrt_time(self) -> None:
        calculator = CalendarAgingCalculator(R_GAS)
        inputs = CalendarAgingInput(a_cal=1.0, ea_cal=0.0, temp_k=300.0, days=4.0)

        loss = calculator.loss(inputs)

        # arrhenius = exp(0) = 1, soc term = 1, sqrt(4) = 2.
        self.assertEqual(loss, 2.0)

    def test_soc_correction_applies_exponential_term(self) -> None:
        calculator = CalendarAgingCalculator(R_GAS)
        inputs = CalendarAgingInput(
            a_cal=1.0, ea_cal=0.0, temp_k=300.0, days=1.0, soc=0.5, alpha=2.0
        )

        loss = calculator.loss(inputs)

        self.assertAlmostEqual(loss, math.exp(2.0 * 0.5), places=12)


class CycleDamageCalculatorTest(unittest.TestCase):
    def test_damage_accumulates_and_skips_nonpositive_dod(self) -> None:
        calculator = CycleDamageCalculator(coefficient_a=1000.0, exponent_b=1.0)
        observations = [
            CycleObservation(dod=0.5, mean=0.5, count=1.0),
            CycleObservation(dod=0.0, mean=0.0, count=1.0),
        ]

        damage = calculator.damage(observations)

        # Only the 0.5 DoD cycle contributes: 1.0 / (1000 * 0.5**-1) = 0.0005.
        self.assertEqual(damage, 0.0005)


class CapacityCombinerTest(unittest.TestCase):
    def test_combine_superposes_losses(self) -> None:
        combiner = CapacityCombiner(FULL_CAPACITY, MIN_REMAINING_CAPACITY)

        self.assertEqual(combiner.combine(0.1, 0.05), 0.85)

    def test_combine_clamps_at_minimum(self) -> None:
        combiner = CapacityCombiner(FULL_CAPACITY, MIN_REMAINING_CAPACITY)

        self.assertEqual(combiner.combine(0.9, 0.5), 0.0)


class FacadeParityTest(unittest.TestCase):
    def test_facades_match_calculator_results(self) -> None:
        self.assertEqual(calendar_loss(1.0, 0.0, 300.0, 4.0), 2.0)
        self.assertEqual(cycle_damage([(0.5, 0.5, 1.0)], 1000.0, 1.0), 0.0005)
        self.assertEqual(remaining_capacity(0.1, 0.05), 0.85)


if __name__ == "__main__":
    unittest.main()
