"""
description: Exponential smoothing (ETS) in the additive-error state-space form, every admissible trend and season combination fitted and the lowest-AICc one kept, with analytic h-step bands. numpy only.
last_updated: 2026-11-24
origin: original
sources:
  - https://doi.org/10.1007/978-3-540-71918-2
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from nelder_mead import minimize
from stat_core import EPS, ClassicalError, ClassicalForecast, quantiles

_PHI_LO, _PHI_HI = 0.80, 0.98


@dataclass(frozen=True)
class _EtsSpec:
    trend: str  # "N" | "A" | "Ad"
    season: str  # "N" | "A" | "M"

    @property
    def name(self) -> str:
        return f"ETS(A,{self.trend},{self.season})"


def _ets_initial(
    y: np.ndarray, spec: _EtsSpec, m: int
) -> tuple[float, float, np.ndarray]:
    """Heuristic starting states (level, trend, seasonals) from the first seasons."""
    if spec.season == "N":
        k = min(y.size, 10)
        l0 = float(y[:k].mean()) if spec.trend == "N" else float(y[0])
        b0 = float(np.mean(np.diff(y[: min(y.size, 5)]))) if spec.trend != "N" else 0.0
        return l0, b0, np.zeros(0)
    first, second = y[:m], y[m : 2 * m]
    l0 = float(first.mean())
    b0 = float((second.mean() - first.mean()) / m) if spec.trend != "N" else 0.0
    base = l0 + b0 * (np.arange(m) - (m - 1) / 2.0)
    if spec.season == "A":
        s0 = first - base
        s0 = s0 - s0.mean()
    else:
        s0 = first / base
        s0 = s0 / s0.mean()
    # Level/trend at time 0 (one step before y[0]).
    l0 = l0 - b0 * (m + 1) / 2.0
    return l0, b0, s0


def _ets_run(
    y: np.ndarray,
    spec: _EtsSpec,
    m: int,
    alpha: float,
    beta: float,
    gamma: float,
    phi: float,
    l0: float,
    b0: float,
    s0: np.ndarray,
) -> tuple[float, float, float, np.ndarray]:
    """Filter y through the model; return (sse, final level, final trend, seasonals)."""
    level, trend = l0, b0
    seas = s0.copy()
    sse = 0.0
    has_trend = spec.trend != "N"
    damp = phi if spec.trend == "Ad" else 1.0
    for t in range(y.size):
        pb = damp * trend if has_trend else 0.0
        base = level + pb
        if spec.season == "N":
            yhat = base
        else:
            s_old = seas[t % m]
            yhat = base + s_old if spec.season == "A" else base * s_old
        e = y[t] - yhat
        sse += e * e
        if spec.season == "M":
            if abs(s_old) < EPS or abs(base) < EPS:
                return math.inf, level, trend, seas
            level = base + alpha * e / s_old
            if has_trend:
                trend = pb + beta * e / s_old
            seas[t % m] = s_old + gamma * e / base
        else:
            level = base + alpha * e
            if has_trend:
                trend = pb + beta * e
            if spec.season == "A":
                seas[t % m] = s_old + gamma * e
        if not math.isfinite(level):
            return math.inf, level, trend, seas
    return sse, level, trend, seas


def _ets_unpack(theta: np.ndarray, spec: _EtsSpec) -> tuple[float, ...] | None:
    """theta -> (alpha, beta, gamma, phi, l0, b0); None if outside the admissible region."""
    i = 0
    alpha = theta[i]
    i += 1
    beta = gamma = 0.0
    phi = 1.0
    if spec.trend != "N":
        beta = theta[i]
        i += 1
    if spec.season != "N":
        gamma = theta[i]
        i += 1
    if spec.trend == "Ad":
        phi = theta[i]
        i += 1
    l0 = theta[i]
    i += 1
    b0 = theta[i] if spec.trend != "N" else 0.0
    if not (1e-4 <= alpha <= 0.9999):
        return None
    if spec.trend != "N" and not (1e-4 <= beta <= alpha):
        return None
    if spec.season != "N" and not (1e-4 <= gamma <= 1.0 - alpha):
        return None
    if spec.trend == "Ad" and not (_PHI_LO <= phi <= _PHI_HI):
        return None
    return alpha, beta, gamma, phi, l0, b0


def _ets_fit(y: np.ndarray, spec: _EtsSpec, m: int) -> dict[str, Any] | None:
    n = y.size
    l0h, b0h, s0 = _ets_initial(y, spec, m)
    n_smooth = 1 + (spec.trend != "N") + (spec.season != "N") + (spec.trend == "Ad")
    n_states = 1 + (spec.trend != "N") + (m - 1 if spec.season != "N" else 0)
    k = n_smooth + n_states
    if n - k - 1 <= 0:
        return None

    def objective(theta: np.ndarray) -> float:
        p = _ets_unpack(theta, spec)
        if p is None:
            return math.inf
        alpha, beta, gamma, phi, l0, b0 = p
        sse, *_ = _ets_run(y, spec, m, alpha, beta, gamma, phi, l0, b0, s0)
        return sse

    # Fixed starting grid over the smoothing parameters, then Nelder-Mead.
    best_x, best_v = None, math.inf
    for a in (0.15, 0.5):
        for bf in (0.1,):
            for gf in (0.05, 0.3):
                x = [a]
                if spec.trend != "N":
                    x.append(a * bf)
                if spec.season != "N":
                    x.append((1 - a) * gf)
                if spec.trend == "Ad":
                    x.append(0.9)
                x.append(l0h)
                if spec.trend != "N":
                    x.append(b0h)
                v = objective(np.array(x))
                if v < best_v:
                    best_x, best_v = np.array(x), v
    if best_x is None or not math.isfinite(best_v):
        return None
    scale = max(float(np.mean(np.abs(y))), 1.0)
    step = np.array(
        [0.05] * n_smooth
        + [0.05 * scale]
        + ([0.01 * scale] if spec.trend != "N" else [])
    )
    x, sse = minimize(objective, best_x, step, iters=250)
    if not math.isfinite(sse):
        return None
    alpha, beta, gamma, phi, l0, b0 = _ets_unpack(x, spec)  # type: ignore[misc]
    sse, level, trend, seas = _ets_run(y, spec, m, alpha, beta, gamma, phi, l0, b0, s0)
    sse = max(sse, EPS)
    aicc = n * math.log(sse / n) + 2 * k + 2 * k * (k + 1) / (n - k - 1)
    sigma2 = sse / max(n - k, 1)
    return {
        "spec": spec,
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
        "phi": phi,
        "level": level,
        "trend": trend,
        "seas": seas,
        "n": n,
        "sigma2": sigma2,
        "aicc": aicc,
    }


def _ets_forecast(fit: dict[str, Any], m: int, h: int) -> tuple[np.ndarray, np.ndarray]:
    """Point forecasts and h-step standard deviations."""
    spec: _EtsSpec = fit["spec"]
    alpha, beta, gamma, phi = fit["alpha"], fit["beta"], fit["gamma"], fit["phi"]
    level, trend, seas, n = fit["level"], fit["trend"], fit["seas"], fit["n"]
    damp = phi if spec.trend == "Ad" else 1.0
    steps = np.arange(1, h + 1)
    if spec.trend == "N":
        phi_h = np.zeros(h)
    elif spec.trend == "A":
        phi_h = steps.astype(float)
    else:
        phi_h = np.cumsum(damp**steps)
    base = level + phi_h * trend
    if spec.season == "N":
        s_h = None
        mean = base
    else:
        s_h = np.array([seas[(n + j) % m] for j in range(h)])
        mean = base + s_h if spec.season == "A" else base * s_h

    # Class-1 variance (Hyndman et al. 2008, table 6.1): c_j for j = 1..h-1.
    var = np.empty(h)
    for i in range(h):
        acc = 1.0
        for j in range(1, i + 1):
            pj = phi_h[j - 1]
            c = (
                alpha
                + beta * pj
                + (gamma if (spec.season != "N" and j % m == 0) else 0.0)
            )
            if spec.season == "M" and s_h is not None:
                # Multiplicative seasonality: errors enter the level divided by the
                # seasonal index of their period and come out multiplied by the
                # forecast period's index (first-order approximation).
                s_from = seas[(n + i - j) % m]
                c = c * s_h[i] / s_from if abs(s_from) > EPS else c
            acc += c * c
        var[i] = fit["sigma2"] * acc
    return mean, np.sqrt(var)


def forecast_ets(y: np.ndarray, m: int, h: int) -> ClassicalForecast:
    """Fit every admissible ETS model and forecast with the lowest-AICc one."""
    specs = [_EtsSpec(t, "N") for t in ("N", "A", "Ad")]
    if m > 1 and y.size >= 2 * m + 2:
        specs += [_EtsSpec(t, "A") for t in ("N", "A", "Ad")]
        if np.all(y > 0):
            specs += [_EtsSpec(t, "M") for t in ("N", "A", "Ad")]
    fits = [f for f in (_ets_fit(y, s, m) for s in specs) if f is not None]
    if not fits:
        raise ClassicalError("no ETS model could be fitted to this series")
    best = min(fits, key=lambda f: f["aicc"])
    mean, sd = _ets_forecast(best, m, h)
    p10, p50, p90 = quantiles(mean, sd)
    detail = {
        "model": best["spec"].name,
        "alpha": round(best["alpha"], 6),
        "beta": round(best["beta"], 6),
        "gamma": round(best["gamma"], 6),
        "phi": round(best["phi"], 6),
        "aicc": round(best["aicc"], 4),
        "candidates": {f["spec"].name: round(f["aicc"], 4) for f in fits},
    }
    return ClassicalForecast(p10, p50, p90, "ets", detail)
