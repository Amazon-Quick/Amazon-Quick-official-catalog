"""
description: Finance forecasting methods (trailing run-rates, prior year x trailing year-on-year growth, seasonal naive, target phasing) to sit next to the baseline, numpy only.
last_updated: 2026-11-24
origin: original

These are the methods a finance analyst already computes by hand, written out so the coach can show them
beside the baseline, backtest all of them the same way, and say which one history favors per series.

    run_rate(values, horizon, window)             flat trailing average (T3M / T6M / T12M ...)
    prior_year_growth(values, horizon, season)    same period last year x (1 + trailing YoY growth)
    seasonal_naive(values, horizon, season)       same period last year, unchanged
    phase_target(values, total, periods, season)  spread a total by historical period-of-year shares
    ETS / Theta (stat_methods.py)                 exponential smoothing chosen by AICc, and the Theta method

Every function takes history oldest -> newest and returns None when there is not enough history for the
method to mean anything, rather than a number that looks fine and is not.
"""

from __future__ import annotations

import numpy as np
import stat_methods as sm

__all__ = [
    "run_rate",
    "prior_year_growth",
    "seasonal_naive",
    "phase_target",
    "seasonal_shares",
    "run_rate_windows",
    "method_forecasts",
    "MODEL_LABEL",
    "PY_LABEL",
    "SN_LABEL",
]

MODEL_LABEL = sm.BASELINE_LABEL
PY_LABEL = "Prior year x YoY"
SN_LABEL = "Seasonal naive"

# trailing windows that finance actually quotes, per reporting frequency
_WINDOWS = {
    "MS": [(3, "T3M run-rate"), (6, "T6M run-rate"), (12, "T12M run-rate")],
    "QS": [(2, "T2Q run-rate"), (4, "T4Q run-rate")],
    "W": [(4, "T4W run-rate"), (13, "T13W run-rate"), (52, "T52W run-rate")],
    "D": [(7, "T7D run-rate"), (28, "T28D run-rate")],
    "YS": [(2, "T2Y run-rate"), (3, "T3Y run-rate")],
}


def _arr(values) -> np.ndarray:
    return np.asarray(values, dtype=float).ravel()


def run_rate_windows(freq: str) -> list:
    """[(window_in_periods, label), ...] for a frequency code (MS, QS, W, D, YS)."""
    return list(_WINDOWS.get(freq, _WINDOWS["MS"]))


def run_rate(values, horizon: int, window: int):
    """Flat forecast at the average of the last `window` periods. None if history is shorter than the window."""
    v = _arr(values)
    if len(v) < window:
        return None
    tail = v[-window:]
    if np.isnan(tail).all():
        return None
    return np.full(int(horizon), float(np.nanmean(tail)))


def seasonal_naive(values, horizon: int, season: int):
    """Same period one cycle ago. None if there is less than one full cycle of history."""
    v = _arr(values)
    season = max(int(season), 1)
    if len(v) < season:
        return None
    tail = v[-season:]
    return np.array([tail[i % season] for i in range(int(horizon))], dtype=float)


def trailing_yoy(values, season: int):
    """(growth, periods_compared). Growth of the latest cycle over the one before it, on matched periods.

    With between one and two cycles of history it compares only the periods that have a year-ago match.
    Returns (None, 0) when fewer than 3 matched periods exist or the year-ago base is not positive.
    """
    v = _arr(values)
    season = max(int(season), 1)
    k = min(season, len(v) - season)
    if k < min(3, season):
        return None, 0
    cur, prev = v[-k:], v[-k - season : -season]
    ok = ~np.isnan(cur) & ~np.isnan(prev)
    if ok.sum() < min(3, season):
        return None, 0
    base = float(prev[ok].sum())
    if base <= 0 or float(cur[ok].sum()) < 0:
        return None, 0
    return float(cur[ok].sum()) / base - 1.0, int(ok.sum())


def prior_year_growth(values, horizon: int, season: int):
    """Same period last year x (1 + trailing YoY growth); growth compounds for each further year out."""
    v = _arr(values)
    season = max(int(season), 1)
    g, _ = trailing_yoy(v, season)
    if g is None or len(v) < season:
        return None
    base = v[-season:]
    if np.isnan(base).any():  # fill a gap in last year from the year before, grown once
        if len(v) >= 2 * season:
            older = v[-2 * season : -season]
            base = np.where(np.isnan(base), older * (1.0 + g), base)
        if np.isnan(base).any():
            return None
    return np.array(
        [
            base[h % season] * (1.0 + g) ** (h // season + 1)
            for h in range(int(horizon))
        ],
        dtype=float,
    )


def seasonal_shares(values, season: int, start_offset: int = 0):
    """(shares, cycles_used): average share of a cycle's total that falls in each period position.

    Position 0 is the period `start_offset` periods after the end of history (0 = the period right after
    history). Cycles are taken so that each one starts at the same period-of-year as that position, so a
    calendar-year target is phased from calendar-year cycles rather than from whichever 12 periods happen
    to end at the last actual. Only complete cycles with a positive total and no gaps or negatives are
    used. Returns (None, 0) when there is no such cycle.
    """
    v = _arr(values)
    season = max(int(season), 1)
    n = len(v)
    first = (
        n + int(start_offset)
    ) % season  # first history index at the same period-of-year as position 0
    rows = []
    starts = list(range(first, n - season + 1, season))
    for st in reversed(starts):
        cyc = v[st : st + season]
        if np.isnan(cyc).any() or (cyc < 0).any() or cyc.sum() <= 0:
            continue
        rows.append(cyc / cyc.sum())
    if not rows:
        return None, 0
    s = np.mean(rows, axis=0)
    return s / s.sum(), len(rows)


def phase_target(
    values,
    total: float,
    periods: int,
    season: int,
    fallback_shape=None,
    start_offset: int = 0,
) -> dict:
    """Spread `total` across the next `periods` periods by historical period-of-year shares.

    This is the top-down job: the number is given (a plan, a goal-seek, a full-year commitment) and the
    question is how it lands by period. Scaling a forecast proportionally keeps whatever shape the
    forecast has; this uses the shape the business has actually shown.

    If history has no complete cycle, it falls back to `fallback_shape` (for example the baseline's P50) and
    says so in the returned `basis`.
    """
    periods = int(periods)
    shares, cycles = seasonal_shares(values, season, start_offset)
    if shares is not None:
        w = np.array(
            [shares[h % max(int(season), 1)] for h in range(periods)], dtype=float
        )
        basis = f"historical period-of-year shares, averaged over {cycles} full cycle{'' if cycles == 1 else 's'}"
    elif (
        fallback_shape is not None
        and np.nansum(np.asarray(fallback_shape, float)[:periods]) > 0
    ):
        w = np.asarray(fallback_shape, dtype=float)[:periods].copy()
        basis = "baseline P50 shape (history has no complete cycle to take shares from)"
    else:
        w = np.ones(periods)
        basis = "even split (no complete cycle of history and no usable forecast shape)"
    w = np.where(np.isnan(w) | (w < 0), 0.0, w)
    if w.sum() <= 0:
        w = np.ones(periods)
    return {
        "phased": float(total) * w / w.sum(),
        "weights": w / w.sum(),
        "basis": basis,
        "cycles": cycles,
    }


def method_forecasts(values, horizon: int, season: int, freq: str) -> dict:
    """{label: array or None} for every finance method, in display order. The baseline is not included."""
    out = {}
    for window, label in run_rate_windows(freq):
        out[label] = run_rate(values, horizon, window)
    out[PY_LABEL] = prior_year_growth(values, horizon, season) if season > 1 else None
    out[SN_LABEL] = seasonal_naive(values, horizon, season) if season > 1 else None
    v = _arr(values)
    v = v[np.isfinite(v)] if np.isnan(v[-1:]).any() else v
    out[sm.ETS_LABEL] = sm.point(v, horizon, freq, "ets") if len(v) >= 8 else None
    out[sm.THETA_LABEL] = sm.point(v, horizon, freq, "theta") if len(v) >= 8 else None
    return out
