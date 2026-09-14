"""
description: Lithium-ion capacity fade model combining Arrhenius calendar aging and rainflow cycle aging using only the Python standard library.
last_updated: 2026-09-13
origin: original

Lithium-ion capacity fade: calendar (Arrhenius SEI) plus cycle (rainflow) aging.

Combines square-root-of-time calendar aging with Palmgren-Miner cycle-aging
damage from rainflow-counted depth-of-discharge (DoD). All model parameters
(activation energy, pre-exponential factor, cycle-life coefficients) must come
from a cell datasheet, published literature, or measured test data, never from
assumption. See references/degradation-model.md for the equations and citations.

Uses only the Python standard library so it runs inside the Amazon Quick sandbox.
"""

from __future__ import annotations

import argparse
import logging
import math
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

R_GAS = 8.314  # universal gas constant, J/(mol*K)

# Default empirical SOC sensitivity: no correction unless the caller supplies one.
DEFAULT_ALPHA = 0.0
# Capacity bounds expressed as a fraction of the rated (beginning-of-life) value.
FULL_CAPACITY = 1.0
MIN_REMAINING_CAPACITY = 0.0
# A neutral SOC term of 1.0 leaves calendar loss unscaled when SOC is unknown.
NEUTRAL_SOC_TERM = 1.0


@dataclass(frozen=True)
class CalendarAgingInput:
    """Structured inputs for a single calendar-aging evaluation."""

    a_cal: float
    ea_cal: float
    temp_k: float
    days: float
    soc: float | None = None
    alpha: float = DEFAULT_ALPHA


@dataclass(frozen=True)
class CycleObservation:
    """A single rainflow cycle expressed as depth-of-discharge, mean, and count."""

    dod: float
    mean: float
    count: float


class CalendarAgingCalculator:
    """Arrhenius square-root-of-time calendar-aging capacity loss."""

    def __init__(self, gas_constant: float) -> None:
        self._gas_constant = gas_constant

    def loss(self, inputs: CalendarAgingInput) -> float:
        """Fractional capacity loss from calendar aging for the given inputs."""
        arrhenius = math.exp(-inputs.ea_cal / (self._gas_constant * inputs.temp_k))
        soc_term = (
            math.exp(inputs.alpha * inputs.soc)
            if inputs.soc is not None
            else NEUTRAL_SOC_TERM
        )
        return inputs.a_cal * arrhenius * soc_term * math.sqrt(inputs.days)


class CycleDamageCalculator:
    """Palmgren-Miner cycle-aging damage from rainflow cycles."""

    def __init__(self, coefficient_a: float, exponent_b: float) -> None:
        self._coefficient_a = coefficient_a
        self._exponent_b = exponent_b

    def damage(self, cycles: list[CycleObservation]) -> float:
        """Accumulated damage fraction; 1.0 corresponds to end of cycle life."""
        total = 0.0
        for cycle in cycles:
            if cycle.dod <= 0:
                continue
            n_failure = self._coefficient_a * cycle.dod ** (-self._exponent_b)
            total += cycle.count / n_failure
        return total


class CapacityCombiner:
    """Superpose calendar and cycle losses into remaining capacity fraction."""

    def __init__(self, full_capacity: float, min_capacity: float) -> None:
        self._full_capacity = full_capacity
        self._min_capacity = min_capacity

    def combine(self, cal_loss: float, cyc_damage: float) -> float:
        """Remaining rated-capacity fraction after both aging mechanisms."""
        return max(self._min_capacity, self._full_capacity - cal_loss - cyc_damage)


def calendar_loss(
    a_cal: float,
    ea_cal: float,
    temp_k: float,
    days: float,
    soc: float | None = None,
    alpha: float = 0.0,
) -> float:
    """Fractional capacity loss from calendar aging over `days` at temperature `temp_k`.

    a_cal is the pre-exponential factor, ea_cal the SEI activation energy in
    J/mol, temp_k the cell temperature in kelvin. When soc is given, an
    empirical exp(alpha * soc) correction is applied.
    """
    inputs = CalendarAgingInput(
        a_cal=a_cal,
        ea_cal=ea_cal,
        temp_k=temp_k,
        days=days,
        soc=soc,
        alpha=alpha,
    )
    return CalendarAgingCalculator(R_GAS).loss(inputs)


def cycle_damage(cycles: list[tuple[float, float, float]], a: float, b: float) -> float:
    """Palmgren-Miner damage fraction from rainflow cycles [(dod, mean, count)].

    Cycle life follows N_failure(DoD) = a * DoD**(-b). DoD must be expressed as a
    fraction between 0 and 1. Damage of 1.0 corresponds to end of cycle life.
    """
    observations = [
        CycleObservation(dod=cycle[0], mean=cycle[1], count=cycle[2])
        for cycle in cycles
    ]
    return CycleDamageCalculator(a, b).damage(observations)


def remaining_capacity(cal_loss: float, cyc_damage: float) -> float:
    """Fraction of rated capacity remaining after superposed calendar and cycle aging."""
    return CapacityCombiner(FULL_CAPACITY, MIN_REMAINING_CAPACITY).combine(
        cal_loss, cyc_damage
    )


def _build_parser() -> argparse.ArgumentParser:
    """Construct the command-line parser for the calendar-aging demonstration."""
    parser = argparse.ArgumentParser(
        description="Lithium-ion calendar (Arrhenius SEI) capacity-fade calculation.",
    )
    parser.add_argument(
        "--a-cal", type=float, required=True, help="Pre-exponential factor."
    )
    parser.add_argument(
        "--ea-cal", type=float, required=True, help="SEI activation energy, J/mol."
    )
    parser.add_argument(
        "--temp-k", type=float, required=True, help="Cell temperature, kelvin."
    )
    parser.add_argument(
        "--days", type=float, required=True, help="Elapsed calendar days."
    )
    parser.add_argument(
        "--soc", type=float, default=None, help="Optional state of charge fraction."
    )
    parser.add_argument(
        "--alpha", type=float, default=DEFAULT_ALPHA, help="Empirical SOC sensitivity."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Compute calendar-aging loss for the supplied parameters and log it."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    loss = calendar_loss(
        args.a_cal, args.ea_cal, args.temp_k, args.days, args.soc, args.alpha
    )
    _LOGGER.info("calendar_loss_fraction=%s", loss)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
