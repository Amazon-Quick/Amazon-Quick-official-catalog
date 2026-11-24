"""
description: Front door to the statistical forecasts: the skill's baseline (the average of ETS and Theta, or Croston/SBA for an intermittent series) with analytic P10/P90 bands, ETS and Theta on their own, and the WAPE and bias scores. numpy only, no randomness.
last_updated: 2026-11-24
origin: original
sources:
  - https://doi.org/10.1007/978-3-540-71918-2
  - https://doi.org/10.1016/S0169-2070(01)00143-1
  - https://doi.org/10.1057/jors.1972.50
  - https://doi.org/10.1016/j.ijforecast.2004.10.001

Each method is written from its published description: ETS in the additive-error state-space form of
Hyndman, Koehler, Ord and Snyder, Forecasting with Exponential Smoothing (2008), in ets_method.py; Theta as
simple exponential smoothing with drift (Hyndman and Billah, 2003) on seasonally adjusted data, in
theta_method.py; Croston (1972) with the Syntetos-Boylan (2005) correction, in croston_method.py. Bands come
from each method's analytic h-step variance under normal errors.
"""

from __future__ import annotations

import numpy as np
from croston_method import forecast_croston, is_intermittent
from ets_method import forecast_ets
from stat_core import (
    ClassicalError,
    ClassicalForecast,
    clean_series,
    season_length,
)
from theta_method import forecast_theta

METHODS: tuple[str, ...] = ("auto", "ets", "theta", "croston")

BASELINE_LABEL = "Baseline P50"
ETS_LABEL = "ETS"
THETA_LABEL = "Theta"
ETS_THETA_NAME = "ETS-Theta average"
CROSTON_NAME = "Croston/SBA"

_MEMO: dict = {}
_MEMO_LIMIT = 4096


def forecast(
    values: np.ndarray, frequency: str, h: int, method: str = "auto"
) -> ClassicalForecast:
    """Memoized front door: the same history, horizon and method are fitted once per process."""
    arr = np.asarray(values, dtype=float)
    key = (arr.tobytes(), frequency, int(h), method)
    hit = _MEMO.get(key)
    if hit is None:
        if len(_MEMO) > _MEMO_LIMIT:
            _MEMO.clear()
        hit = _MEMO[key] = _forecast(arr, frequency, h, method)
    return ClassicalForecast(
        hit.p10.copy(), hit.p50.copy(), hit.p90.copy(), hit.method, dict(hit.detail)
    )


def _forecast(
    values: np.ndarray, frequency: str, h: int, method: str = "auto"
) -> ClassicalForecast:
    """Forecast ``h`` periods ahead with ``method``; quantiles are ordered P10 <= P50 <= P90."""
    if method not in METHODS:
        raise ClassicalError(f"unknown method {method!r}; choose from {METHODS}")
    if h < 1:
        raise ClassicalError("h must be >= 1")
    y = clean_series(values)
    if y.size < 4:
        raise ClassicalError(f"need at least 4 observations, got {y.size}")
    m = season_length(frequency)

    if np.all(y == y[0]):
        flat = np.full(h, float(y[0]))
        return ClassicalForecast(
            flat,
            flat.copy(),
            flat.copy(),
            method,
            {"chosen": "constant series held flat", "constant_series": True},
        )

    if method == "ets":
        out = forecast_ets(y, m, h)
    elif method == "theta":
        out = forecast_theta(y, m, h)
    elif method == "croston":
        out = forecast_croston(y, h)
    elif is_intermittent(y) and np.count_nonzero(y) >= 2:
        out = forecast_croston(y, h)
        out.method = "auto"
        out.detail = {"chosen": "croston", **out.detail}
    else:
        e = forecast(values, frequency, h, "ets")
        t = forecast(values, frequency, h, "theta")
        out = ClassicalForecast(
            (e.p10 + t.p10) / 2,
            (e.p50 + t.p50) / 2,
            (e.p90 + t.p90) / 2,
            "auto",
            {"chosen": "ets+theta average", "ets": e.detail, "theta": t.detail},
        )

    lo = np.minimum(np.minimum(out.p10, out.p50), out.p90)
    hi = np.maximum(np.maximum(out.p10, out.p50), out.p90)
    out.p50 = np.clip(out.p50, lo, hi)
    out.p10, out.p90 = lo, hi
    return out


def baseline_name(detail: dict) -> str:
    """The method a baseline forecast actually used, named for the user (Rule 7 in SKILL.md)."""
    chosen = detail.get("chosen", "")
    if chosen == "croston":
        return CROSTON_NAME
    if chosen == "constant series held flat":
        return "Constant history held flat"
    return ETS_THETA_NAME


def baseline(values, horizon: int, freq: str = "MS") -> dict:
    """The baseline as {'p10', 'p50', 'p90', 'method', 'detail'}; 'method' names what produced it."""
    out = forecast(np.asarray(values, dtype=float), freq, int(horizon), "auto")
    return {
        "p10": out.p10,
        "p50": out.p50,
        "p90": out.p90,
        "method": baseline_name(out.detail),
        "detail": out.detail,
    }


def point(values, horizon: int, freq: str, method: str):
    """P50 of one method ('ets' or 'theta') as an array, or None when the series cannot take it."""
    try:
        return forecast(np.asarray(values, dtype=float), freq, int(horizon), method).p50
    except ClassicalError:
        return None


def wape(actual, pred) -> float:
    """Weighted absolute percentage error: sum |actual - pred| / sum |actual|."""
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    d = np.abs(a).sum()
    return float(np.abs(a - p).sum() / d) if d else float("nan")


def bias(actual, pred) -> float:
    """Signed bias: sum (pred - actual) / sum |actual|. Positive means over-forecast."""
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    d = np.abs(a).sum()
    return float((p - a).sum() / d) if d else float("nan")


__all__ = [
    "BASELINE_LABEL",
    "CROSTON_NAME",
    "ETS_LABEL",
    "ETS_THETA_NAME",
    "METHODS",
    "THETA_LABEL",
    "ClassicalError",
    "ClassicalForecast",
    "baseline",
    "baseline_name",
    "bias",
    "clean_series",
    "forecast",
    "forecast_croston",
    "forecast_ets",
    "forecast_theta",
    "is_intermittent",
    "point",
    "season_length",
    "wape",
]
