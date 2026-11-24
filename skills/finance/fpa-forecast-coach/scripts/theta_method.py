"""
description: The Theta method (simple exponential smoothing with drift equal to half the linear-trend slope) on seasonally adjusted data, with a lag-season autocorrelation test for seasonality and analytic bands. numpy only.
last_updated: 2026-11-24
origin: original
sources:
  - https://doi.org/10.1016/S0169-2070(01)00143-1
"""

from __future__ import annotations

import math

import numpy as np
from nelder_mead import minimize
from stat_core import ClassicalForecast, quantiles


def _seasonal_indices(y: np.ndarray, m: int, multiplicative: bool) -> np.ndarray:
    """Classical-decomposition seasonal indices (length m, aligned to y[0])."""
    n = y.size
    if m % 2 == 0:
        w = np.r_[0.5, np.ones(m - 1), 0.5] / m
    else:
        w = np.ones(m) / m
    trend = np.convolve(y, w, mode="valid")
    off = (w.size - 1) // 2
    full = np.full(n, np.nan)
    full[off : off + trend.size] = trend
    ratio = y / full if multiplicative else y - full
    idx = np.empty(m)
    for k in range(m):
        vals = ratio[k::m]
        vals = vals[np.isfinite(vals)]
        idx[k] = vals.mean() if vals.size else (1.0 if multiplicative else 0.0)
    if multiplicative:
        idx = idx / idx.mean()
    else:
        idx = idx - idx.mean()
    return idx


def _is_seasonal(y: np.ndarray, m: int) -> bool:
    """90% two-sided test on the lag-m autocorrelation (as used for Theta).

    The test runs on the series with its straight-line trend removed: on raw
    data a trend lifts every autocorrelation, which inflates the test's limit
    and hides a real season (a trending monthly revenue line would otherwise
    lose its seasonality).
    """
    n = y.size
    if m <= 1 or n < 3 * m:
        return False
    t = np.arange(n, dtype=float)
    d = y - np.polyval(np.polyfit(t, y, 1), t)
    denom = float(np.dot(d, d))
    if denom <= 0:
        return False
    acf = np.array([np.dot(d[k:], d[: n - k]) / denom for k in range(1, m + 1)])
    limit = 1.645 * math.sqrt((1 + 2 * float(np.sum(acf[: m - 1] ** 2))) / n)
    return bool(abs(acf[m - 1]) > limit)


def _ses_fit(y: np.ndarray) -> tuple[float, float, float]:
    """Simple exponential smoothing: returns (alpha, final level, sse)."""

    def run(alpha: float, l0: float) -> tuple[float, float]:
        level, sse = l0, 0.0
        for v in y:
            e = v - level
            sse += e * e
            level += alpha * e
        return sse, level

    def objective(theta: np.ndarray) -> float:
        a, l0 = theta
        if not (1e-4 <= a <= 0.9999):
            return math.inf
        return run(a, l0)[0]

    best = min(
        (np.array([a, float(y[0])]) for a in (0.1, 0.3, 0.5, 0.8)),
        key=objective,
    )
    scale = max(float(np.mean(np.abs(y))), 1.0)
    x, _ = minimize(objective, best, np.array([0.05, 0.05 * scale]))
    sse, level = run(float(x[0]), float(x[1]))
    return float(x[0]), level, sse


def forecast_theta(y: np.ndarray, m: int, h: int) -> ClassicalForecast:
    """Standard Theta method (SES with drift = half the linear-trend slope)."""
    n = y.size
    seasonal = _is_seasonal(y, m)
    multiplicative = seasonal and bool(np.all(y > 0))
    if seasonal:
        idx = _seasonal_indices(y, m, multiplicative)
        s_hist = np.array([idx[t % m] for t in range(n)])
        s_fut = np.array([idx[(n + j) % m] for j in range(h)])
        ya = y / s_hist if multiplicative else y - s_hist
    else:
        ya = y
    alpha, level, sse = _ses_fit(ya)
    t = np.arange(1, n + 1, dtype=float)
    slope = float(np.polyfit(t, ya, 1)[0])
    steps = np.arange(1, h + 1, dtype=float)
    drift = 0.5 * slope * (steps - 1 + 1 / alpha - (1 - alpha) ** n / alpha)
    mean = level + drift
    sigma2 = sse / max(n - 3, 1)  # alpha, l0, slope
    sd = np.sqrt(sigma2 * (1 + alpha**2 * (steps - 1)))
    if seasonal:
        if multiplicative:
            mean, sd = mean * s_fut, sd * s_fut
        else:
            mean = mean + s_fut
    p10, p50, p90 = quantiles(mean, sd)
    detail = {
        "seasonal": seasonal,
        "seasonal_form": ("multiplicative" if multiplicative else "additive")
        if seasonal
        else None,
        "alpha": round(alpha, 6),
        "drift_slope": round(slope, 6),
    }
    return ClassicalForecast(p10, p50, p90, "theta", detail)
