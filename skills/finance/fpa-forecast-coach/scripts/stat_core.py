"""
description: Shared pieces of the statistical forecasts (the result type, the error type, season lengths, series cleaning, and the P10/P90 quantile helper), numpy only.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

# z for the 10th / 90th percentile of a standard normal.
Z90 = 1.2815515655446004

# Seasonal period per frequency code the skill uses.
_SEASON_LENGTH = {"D": 7, "W": 52, "MS": 12, "QS": 4, "YS": 1}

# Share of zero observations at which a non-negative series counts as intermittent.
INTERMITTENT_ZERO_SHARE = 0.4

EPS = 1e-10


@dataclass
class ClassicalForecast:
    """P10/P50/P90 arrays of length ``h`` plus what produced them."""

    p10: np.ndarray
    p50: np.ndarray
    p90: np.ndarray
    method: str
    detail: dict[str, Any] = field(default_factory=dict)


class ClassicalError(ValueError):
    """The series cannot be forecast by the requested method."""


def season_length(frequency: str) -> int:
    """Seasonal period for a frequency code (MS, QS, W, D, YS; 1 = no seasonality)."""
    try:
        return _SEASON_LENGTH[frequency]
    except KeyError as exc:
        raise ClassicalError(f"unknown frequency code {frequency!r}") from exc


def clean_series(values: np.ndarray) -> np.ndarray:
    """Float array with inf -> NaN, leading/trailing NaNs dropped, gaps interpolated."""
    y = np.asarray(values, dtype=float).copy()
    y[~np.isfinite(y)] = np.nan
    ok = np.flatnonzero(~np.isnan(y))
    if ok.size == 0:
        raise ClassicalError("series has no finite values")
    y = y[ok[0] : ok[-1] + 1]
    gaps = np.isnan(y)
    if gaps.any():
        idx = np.arange(y.size)
        y[gaps] = np.interp(idx[gaps], idx[~gaps], y[~gaps])
    return y


def quantiles(
    mean: np.ndarray, sd: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(P10, P50, P90) from a mean and a standard deviation under normal errors."""
    sd = np.maximum(sd, 0.0)
    return mean - Z90 * sd, mean.copy(), mean + Z90 * sd
