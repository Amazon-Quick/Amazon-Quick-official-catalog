"""Lithium-ion capacity fade: calendar (Arrhenius SEI) plus cycle (rainflow) aging.

Combines square-root-of-time calendar aging with Palmgren-Miner cycle-aging
damage from rainflow-counted depth-of-discharge (DoD). All model parameters
(activation energy, pre-exponential factor, cycle-life coefficients) must come
from a cell datasheet, published literature, or measured test data, never from
assumption. See references/degradation-model.md for the equations and citations.

Uses only the Python standard library so it runs inside the Amazon Quick sandbox.
"""

from __future__ import annotations

import math

R_GAS = 8.314  # universal gas constant, J/(mol*K)


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
    arrhenius = math.exp(-ea_cal / (R_GAS * temp_k))
    soc_term = math.exp(alpha * soc) if soc is not None else 1.0
    return a_cal * arrhenius * soc_term * math.sqrt(days)


def cycle_damage(cycles: list[tuple[float, float, float]], a: float, b: float) -> float:
    """Palmgren-Miner damage fraction from rainflow cycles [(dod, mean, count)].

    Cycle life follows N_failure(DoD) = a * DoD**(-b). DoD must be expressed as a
    fraction between 0 and 1. Damage of 1.0 corresponds to end of cycle life.
    """
    total = 0.0
    for dod, _mean, count in cycles:
        if dod <= 0:
            continue
        n_failure = a * dod ** (-b)
        total += count / n_failure
    return total


def remaining_capacity(cal_loss: float, cyc_damage: float) -> float:
    """Fraction of rated capacity remaining after superposed calendar and cycle aging."""
    return max(0.0, 1.0 - cal_loss - cyc_damage)
