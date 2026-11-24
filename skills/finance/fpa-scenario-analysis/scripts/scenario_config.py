"""
description: The engine's default configuration and the checks that stop an out-of-range setting before the simulation allocates its arrays, raising ClarificationRequired with a question for the user.
last_updated: 2026-11-24

Called by scenario_engine.run; the settings are documented in references/method.md (Configuration).
"""

from __future__ import annotations

import math

from scenario_intake import ClarificationRequired

DEFAULT_CONFIG = {
    # Scenario percentiles read off the Monte Carlo distribution
    "bear_percentile": 10,
    "base_percentile": 50,
    "bull_percentile": 90,
    # Monte Carlo
    "mc_iterations": 10000,
    "seed": 42,
    # Trend / regression
    "poly_degree": 2,
    "detect_seasonality": True,
    # Driver conversion defaults (replace with the user's own stages and weights)
    "driver_stage_prob": {
        "stage_1": 0.10,
        "stage_2": 0.30,
        "stage_3": 0.60,
        "stage_4": 0.90,
    },
    "driver_timing_sigma": 1.0,
    # Target / plan: a number for P(hit target); None uses the benchmark FY total
    "target": None,
    "target_direction": "at_least",
    # Display label only, after amounts and target have been put on one confirmed basis.
    # Never infer currency/scale or convert values from this label.
    "units": None,
    # Judgment adjustments, ranged: {"label", "low", "likely", "high", "source" (optional)}
    "judgment_adjustments": [],
    # Seasonality profile: one multiplicative index per fiscal period, averaging about 1.0;
    # None estimates it when detect_seasonality
    "seasonality_profile": None,
    # Fiscal year: start period (for example "2026-01"); None aligns the year to the data's first period
    "fy_start_period": None,
    "fy_length_periods": 12,
    # Period cadence: None infers it from the dates ("M", "Q", "W" or "D")
    "freq": None,
}

# Resource limits, checked before the simulation allocates its (iterations x periods) arrays.
MAX_ITERATIONS = 1_000_000
MAX_FY_PERIODS = 366  # a daily fiscal year
MAX_SIMULATED_CELLS = (
    20_000_000  # iterations x remaining periods, about 160 MB per float array
)
MAX_DRIVERS = 500
MAX_JUDGMENT_ITEMS = 100
MAX_POLY_DEGREE = 5


def _number(value) -> float | None:
    """A finite float, or None when the value is not a usable number."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _whole(value) -> int | None:
    """An integer value, or None when the value is not a whole number."""
    number = _number(value)
    return int(number) if number is not None and number == int(number) else None


def _check_percentiles(cfg: dict) -> None:
    keys = ("bear_percentile", "base_percentile", "bull_percentile")
    values = [_number(cfg[k]) for k in keys]
    if any(v is None or not 0 < v < 100 for v in values) or not (
        values[0] < values[1] < values[2]
    ):
        raise ClarificationRequired(
            "Scenario percentiles must be numbers between 0 and 100 with Bear below Base below Bull "
            f"(got {[cfg[k] for k in keys]}). Which percentiles should be used?"
        )


def _check_sizes(cfg: dict) -> tuple[int, int]:
    length, iterations = _whole(cfg["fy_length_periods"]), _whole(cfg["mc_iterations"])
    if length is None or not 1 <= length <= MAX_FY_PERIODS:
        raise ClarificationRequired(
            f"fy_length_periods must be a whole number from 1 to {MAX_FY_PERIODS}. "
            "How many periods are in the fiscal year?"
        )
    if iterations is None or iterations < 1:
        raise ClarificationRequired(
            "mc_iterations must be a positive whole number. How many simulation runs should be used?"
        )
    if iterations > MAX_ITERATIONS:
        raise ClarificationRequired(
            f"Simulation iterations exceed the safety limit of {MAX_ITERATIONS:,}. "
            "What smaller mc_iterations value should be used?"
        )
    if iterations * length > MAX_SIMULATED_CELLS:
        raise ClarificationRequired(
            f"{iterations:,} iterations over {length} periods exceeds the safety limit of "
            f"{MAX_SIMULATED_CELLS:,} simulated values. What smaller mc_iterations value should be used?"
        )
    return length, iterations


def _check_model(cfg: dict, length: int) -> None:
    degree = _whole(cfg["poly_degree"])
    if degree is None or not 0 <= degree <= MAX_POLY_DEGREE:
        raise ClarificationRequired(
            f"poly_degree must be a whole number from 0 to {MAX_POLY_DEGREE}. Which trend degree should be used?"
        )
    sigma = _number(cfg["driver_timing_sigma"])
    if sigma is None or sigma < 0:
        raise ClarificationRequired(
            "driver_timing_sigma must be zero or a positive number of periods. What timing uncertainty should be used?"
        )
    profile = cfg.get("seasonality_profile")
    if profile is not None:
        values = (
            [_number(v) for v in profile]
            if isinstance(profile, (list, tuple))
            else [None]
        )
        if len(values) != length or any(v is None or v <= 0 for v in values):
            raise ClarificationRequired(
                f"A seasonality profile needs {length} positive numbers, one per fiscal period. "
                "Which indices should be used?"
            )


def _check_inputs(cfg: dict, n_drivers: int) -> None:
    if n_drivers > MAX_DRIVERS:
        raise ClarificationRequired(
            f"{n_drivers} drivers exceed the limit of {MAX_DRIVERS}. Can they be grouped into fewer drivers?"
        )
    items = cfg.get("judgment_adjustments") or []
    if not isinstance(items, (list, tuple)) or len(items) > MAX_JUDGMENT_ITEMS:
        raise ClarificationRequired(
            f"judgment_adjustments must be a list of at most {MAX_JUDGMENT_ITEMS} ranges."
        )
    for item in items:
        entry = item if isinstance(item, dict) else {}
        low, likely, high = (_number(entry.get(k)) for k in ("low", "likely", "high"))
        if not entry.get("label") or None in (low, likely, high):
            raise ClarificationRequired(
                "Each judgment adjustment needs a label and numeric low, likely, and high values. "
                "Which values should be used?"
            )
        if not low <= likely <= high:
            raise ClarificationRequired(
                "A judgment adjustment needs low <= likely <= high. Which order is intended?"
            )


def validate_config(cfg: dict, n_drivers: int = 0) -> tuple[int, int]:
    """Check every setting the simulation sizes or draws from. Returns (fy_length_periods, mc_iterations)."""
    _check_percentiles(cfg)
    length, iterations = _check_sizes(cfg)
    _check_model(cfg, length)
    _check_inputs(cfg, n_drivers)
    return length, iterations
