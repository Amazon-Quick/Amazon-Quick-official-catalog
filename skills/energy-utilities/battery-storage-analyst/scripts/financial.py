"""
description: Project-finance metrics for battery storage computing NPV, IRR, payback, and LCOS using only the Python standard library.
last_updated: 2026-09-13
origin: original

Project-finance metrics for battery storage: NPV, IRR, payback, and LCOS.

numpy_financial is not available in the Amazon Quick sandbox, so these are
implemented directly with the standard library. Cash flows are a list in nominal
dollars indexed by year, with year 0 as the capital outlay (negative). See
references/financial-model.md for how the cash flow series is assembled.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass


class _PrintStream:
    """Adapter that lets logging emit timestamped lines to the real stdout."""

    def write(self, message: str) -> None:
        text = message.rstrip("\n")
        if text:
            sys.__stdout__.write(text + "\n")

    def flush(self) -> None:
        sys.__stdout__.flush()


logging.basicConfig(
    stream=_PrintStream(),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    force=True,
)
_LOGGER = logging.getLogger(__name__)

# Bisection bracket and stopping rule for the internal-rate-of-return search.
DEFAULT_IRR_LOW = -0.9
DEFAULT_IRR_HIGH = 1.0
DEFAULT_IRR_TOLERANCE = 1e-6
DEFAULT_IRR_MAX_ITER = 200
# Cumulative cash flow at or above this level marks the payback year.
PAYBACK_THRESHOLD = 0.0
# Discounted discharge at or below this level means no energy was delivered.
ZERO_DISCHARGE = 0.0


@dataclass(frozen=True)
class IrrRequest:
    """Structured inputs for an internal-rate-of-return bisection search."""

    cash_flows: list[float]
    low: float
    high: float
    tol: float
    max_iter: int


@dataclass(frozen=True)
class LevelizedCostInput:
    """Structured inputs for a levelized-cost-of-stored-energy calculation."""

    capital: float
    opex_by_year: list[float]
    discharged_by_year: list[float]
    rate: float


class NetPresentValueCalculator:
    """Discounts a nominal cash-flow series to present value."""

    def value(self, rate: float, cash_flows: list[float]) -> float:
        """Net present value of `cash_flows` discounted at `rate`."""
        return sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cash_flows))


class InternalRateOfReturnCalculator:
    """Finds the discount rate that zeroes NPV via bisection."""

    def __init__(self, npv_calculator: NetPresentValueCalculator) -> None:
        self._npv_calculator = npv_calculator

    def rate(self, request: IrrRequest) -> float | None:
        """Internal rate of return, or None when no sign change brackets a root."""
        low = request.low
        high = request.high
        f_low = self._npv_calculator.value(low, request.cash_flows)
        f_high = self._npv_calculator.value(high, request.cash_flows)
        if f_low * f_high > 0:
            return None
        for _ in range(request.max_iter):
            mid = (low + high) / 2.0
            f_mid = self._npv_calculator.value(mid, request.cash_flows)
            if abs(f_mid) < request.tol:
                return mid
            if f_low * f_mid < 0:
                high = mid
            else:
                low = mid
                f_low = f_mid
        return (low + high) / 2.0


class PaybackCalculator:
    """Finds the first year cumulative undiscounted cash flow turns non-negative."""

    def __init__(self, threshold: float) -> None:
        self._threshold = threshold

    def year(self, cash_flows: list[float]) -> int | None:
        """First year index at or above the payback threshold, else None."""
        cumulative = 0.0
        for t, cf in enumerate(cash_flows):
            cumulative += cf
            if cumulative >= self._threshold:
                return t
        return None


class LevelizedCostCalculator:
    """Levelized cost of stored energy: discounted cost over discounted discharge."""

    def __init__(self, zero_discharge: float) -> None:
        self._zero_discharge = zero_discharge

    def cost(self, inputs: LevelizedCostInput) -> float | None:
        """Discounted cost per discounted unit of discharge, or None when no discharge."""
        disc_cost = inputs.capital + sum(
            o / (1.0 + inputs.rate) ** (t + 1)
            for t, o in enumerate(inputs.opex_by_year)
        )
        disc_energy = sum(
            e / (1.0 + inputs.rate) ** (t + 1)
            for t, e in enumerate(inputs.discharged_by_year)
        )
        if disc_energy == self._zero_discharge:
            return None
        return disc_cost / disc_energy


def npv(rate: float, cash_flows: list[float]) -> float:
    """Net present value of a cash flow series discounted at `rate` (e.g. WACC)."""
    return NetPresentValueCalculator().value(rate, cash_flows)


def irr(
    cash_flows: list[float],
    low: float = -0.9,
    high: float = 1.0,
    tol: float = 1e-6,
    max_iter: int = 200,
) -> float | None:
    """Internal rate of return via bisection. Returns None if no sign change exists."""
    request = IrrRequest(
        cash_flows=cash_flows,
        low=low,
        high=high,
        tol=tol,
        max_iter=max_iter,
    )
    return InternalRateOfReturnCalculator(NetPresentValueCalculator()).rate(request)


def payback_year(cash_flows: list[float]) -> int | None:
    """First year index where cumulative (undiscounted) cash flow turns non-negative."""
    return PaybackCalculator(PAYBACK_THRESHOLD).year(cash_flows)


def lcos(
    capital: float,
    opex_by_year: list[float],
    discharged_by_year: list[float],
    rate: float,
) -> float | None:
    """Levelized cost of stored energy: discounted cost over discounted discharge.

    Units follow the inputs ($/kWh if discharge is in kWh). Returns None when no
    energy is discharged.
    """
    inputs = LevelizedCostInput(
        capital=capital,
        opex_by_year=opex_by_year,
        discharged_by_year=discharged_by_year,
        rate=rate,
    )
    return LevelizedCostCalculator(ZERO_DISCHARGE).cost(inputs)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the command-line parser for the project-finance demonstration."""
    parser = argparse.ArgumentParser(
        description="Battery storage project-finance metrics (NPV, IRR, payback).",
    )
    parser.add_argument(
        "--rate",
        type=float,
        required=True,
        help="Discount rate (WACC) as a fraction, e.g. 0.08.",
    )
    parser.add_argument(
        "--cash-flows",
        type=float,
        nargs="+",
        required=True,
        help="Nominal cash flows by year, year 0 first (capital outlay negative).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Compute NPV, IRR, and payback for the supplied cash flows and log them."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    net_present_value = npv(args.rate, args.cash_flows)
    internal_rate = irr(args.cash_flows)
    payback = payback_year(args.cash_flows)
    _LOGGER.info("npv=%s", net_present_value)
    _LOGGER.info("irr=%s", internal_rate)
    _LOGGER.info("payback_year=%s", payback)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
