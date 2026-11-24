"""
description: Croston's method with the Syntetos-Boylan approximation (SBA) for intermittent series (many zero periods): a flat forecast floored at zero, with analytic bands. numpy only.
last_updated: 2026-11-24
origin: original
sources:
  - https://doi.org/10.1057/jors.1972.50
  - https://doi.org/10.1016/j.ijforecast.2004.10.001
"""

from __future__ import annotations

import numpy as np
from stat_core import (
    INTERMITTENT_ZERO_SHARE,
    ClassicalError,
    ClassicalForecast,
    quantiles,
)


def is_intermittent(y: np.ndarray) -> bool:
    """True when a non-negative series has at least INTERMITTENT_ZERO_SHARE zero values."""
    return bool(np.all(y >= 0) and np.mean(y == 0) >= INTERMITTENT_ZERO_SHARE)


def forecast_croston(y: np.ndarray, h: int, alpha: float = 0.1) -> ClassicalForecast:
    """Croston's method with the Syntetos-Boylan approximation; flat forecast, floored at 0."""
    nz = np.flatnonzero(y != 0)
    if nz.size < 2:
        raise ClassicalError("Croston needs at least two non-zero observations")
    size = float(y[nz[0]])
    interval = float(nz[0] + 1)
    gap = 0
    fitted = np.empty(y.size)
    for t, v in enumerate(y):
        fitted[t] = (1 - alpha / 2) * size / interval
        gap += 1
        if v != 0:
            size += alpha * (v - size)
            interval += alpha * (gap - interval)
            gap = 0
    level = (1 - alpha / 2) * size / interval
    resid = y[nz[0] + 1 :] - fitted[nz[0] + 1 :]
    sigma2 = float(np.mean(resid**2)) if resid.size else 0.0
    steps = np.arange(1, h + 1, dtype=float)
    sd = np.sqrt(sigma2 * (1 + alpha**2 * (steps - 1)))
    p10, p50, p90 = quantiles(np.full(h, level), sd)
    p10 = np.maximum(p10, 0.0)
    detail = {
        "alpha": alpha,
        "mean_size": round(size, 6),
        "mean_interval": round(interval, 6),
    }
    return ClassicalForecast(p10, p50, p90, "croston", detail)
