"""
description: Dependency-injected unit tests for the battery storage project-finance calculators, asserting pure logic without filesystem or network access.
last_updated: 2026-09-13
origin: original
"""

import unittest

from financial import (
    PAYBACK_THRESHOLD,
    ZERO_DISCHARGE,
    InternalRateOfReturnCalculator,
    IrrRequest,
    LevelizedCostCalculator,
    LevelizedCostInput,
    NetPresentValueCalculator,
    PaybackCalculator,
    irr,
    lcos,
    npv,
    payback_year,
)


class NetPresentValueCalculatorTest(unittest.TestCase):
    def test_zero_rate_sums_cash_flows(self) -> None:
        calculator = NetPresentValueCalculator()

        self.assertEqual(calculator.value(0.0, [-100.0, 50.0, 50.0, 50.0]), 50.0)


class InternalRateOfReturnCalculatorTest(unittest.TestCase):
    def test_solves_simple_two_period_root(self) -> None:
        calculator = InternalRateOfReturnCalculator(NetPresentValueCalculator())
        request = IrrRequest(
            cash_flows=[-100.0, 110.0],
            low=-0.9,
            high=1.0,
            tol=1e-6,
            max_iter=200,
        )

        rate = calculator.rate(request)

        self.assertIsNotNone(rate)
        assert rate is not None  # nosec B101
        self.assertAlmostEqual(rate, 0.1, places=4)

    def test_returns_none_without_sign_change(self) -> None:
        calculator = InternalRateOfReturnCalculator(NetPresentValueCalculator())
        request = IrrRequest(
            cash_flows=[1.0, 2.0, 3.0],
            low=-0.9,
            high=1.0,
            tol=1e-6,
            max_iter=200,
        )

        self.assertIsNone(calculator.rate(request))


class PaybackCalculatorTest(unittest.TestCase):
    def test_returns_first_non_negative_year(self) -> None:
        calculator = PaybackCalculator(PAYBACK_THRESHOLD)

        self.assertEqual(calculator.year([-100.0, 40.0, 40.0, 40.0]), 3)

    def test_returns_none_when_never_recovered(self) -> None:
        calculator = PaybackCalculator(PAYBACK_THRESHOLD)

        self.assertIsNone(calculator.year([-100.0, 40.0]))


class LevelizedCostCalculatorTest(unittest.TestCase):
    def test_cost_divides_discounted_cost_by_discounted_energy(self) -> None:
        calculator = LevelizedCostCalculator(ZERO_DISCHARGE)
        inputs = LevelizedCostInput(
            capital=100.0,
            opex_by_year=[0.0, 0.0],
            discharged_by_year=[10.0, 10.0],
            rate=0.0,
        )

        self.assertEqual(calculator.cost(inputs), 5.0)

    def test_cost_is_none_when_no_energy_discharged(self) -> None:
        calculator = LevelizedCostCalculator(ZERO_DISCHARGE)
        inputs = LevelizedCostInput(
            capital=100.0,
            opex_by_year=[0.0, 0.0],
            discharged_by_year=[0.0, 0.0],
            rate=0.0,
        )

        self.assertIsNone(calculator.cost(inputs))


class FacadeParityTest(unittest.TestCase):
    def test_facades_match_calculator_results(self) -> None:
        self.assertEqual(npv(0.0, [-100.0, 50.0, 50.0, 50.0]), 50.0)
        rate = irr([-100.0, 110.0])
        self.assertIsNotNone(rate)
        assert rate is not None  # nosec B101
        self.assertAlmostEqual(rate, 0.1, places=4)
        self.assertEqual(payback_year([-100.0, 40.0, 40.0, 40.0]), 3)
        self.assertEqual(lcos(100.0, [0.0, 0.0], [10.0, 10.0], 0.0), 5.0)


if __name__ == "__main__":
    unittest.main()
