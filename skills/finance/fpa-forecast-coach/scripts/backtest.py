"""
description: The methods the Forecast Coach offers, in display order, how the method argument picks one per series, and the backtest that scores the baseline and every finance method on the same held-out windows.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import math

import finance_methods as fm
import numpy as np
import stat_methods as sm

LV_LABEL = "Last actual held flat"  # no commas in labels: Excel's picker list is comma-separated
MIN_TRAIN = 8
_BASELINE_ALIASES = ("baseline", "baseline p50", "model", "ets-theta", "ets-theta p50")


def method_order(freq: str, season: int) -> list:
    """Every method the workbook can show, in display order. The baseline always comes first."""
    out = [fm.MODEL_LABEL] + [label for _, label in fm.run_rate_windows(freq)]
    if season > 1:
        out += [fm.PY_LABEL, fm.SN_LABEL]
    return out + [sm.ETS_LABEL, sm.THETA_LABEL, LV_LABEL]


def pick_method(spec, name: str, available: list, best: str | None) -> str:
    """Resolve the `method` argument to one of this series' available method labels."""
    want = spec.get(name) if isinstance(spec, dict) else spec
    want = str(want or "baseline").strip().lower()
    if want in _BASELINE_ALIASES:
        return fm.MODEL_LABEL
    if want == "best":
        return best if best in available else fm.MODEL_LABEL
    for a in available:
        if a.lower() == want:
            return a
    for a in available:  # "T12M" -> "T12M run-rate", "prior year" -> "Prior year x YoY"
        if a.lower().startswith(want):
            return a
    return fm.MODEL_LABEL


def all_methods(
    values: np.ndarray, horizon: int, season: int, freq: str, base_p50
) -> dict:
    """{label: array or None} for the baseline, last actual held flat, and every finance method."""
    out = {
        fm.MODEL_LABEL: base_p50,
        LV_LABEL: fm.run_rate(values[~np.isnan(values)], horizon, 1),
    }
    out.update(fm.method_forecasts(values, horizon, season, freq))
    return out


def backtest_all(values, horizon: int, folds: int, season: int, freq: str) -> dict:
    """Hold out the last `folds` windows and score the baseline and every finance method on the same ones.

    A method only gets an average if it could be computed on every fold, so the comparison is like for
    like. `best_method` is the lowest average WAPE among those.
    """
    s = np.asarray(values, dtype=float)
    rows = []
    for k in range(folds, 0, -1):
        cut_at = len(s) - k * horizon
        if cut_at < max(MIN_TRAIN, season):
            continue
        train, test = s[:cut_at], s[cut_at : cut_at + horizon]
        ok = ~np.isnan(test)
        if len(test) < horizon or not ok.any() or np.isnan(train).all():
            continue
        f = sm.baseline(train, horizon, freq)
        preds = all_methods(train, horizon, season, freq, f["p50"])
        rows.append(
            {
                "fold": folds - k + 1,
                "train_points": int(cut_at),
                "wape": {
                    m: sm.wape(test[ok], p[ok])
                    for m, p in preds.items()
                    if p is not None and not np.isnan(np.asarray(p)[ok]).any()
                },
                "model_bias": sm.bias(test[ok], f["p50"][ok]),
                "coverage": float(
                    np.mean((test[ok] >= f["p10"][ok]) & (test[ok] <= f["p90"][ok]))
                ),
            }
        )
    if not rows:
        return {"folds": [], "note": "series too short to backtest at this horizon"}
    scored = {
        m: float(np.mean([r["wape"][m] for r in rows]))
        for m in rows[0]["wape"]
        if all(m in r["wape"] for r in rows)
    }
    scored = {m: w for m, w in scored.items() if not math.isnan(w)}
    model_w = scored.get(fm.MODEL_LABEL, float("nan"))
    naive_w = scored.get(fm.SN_LABEL, scored.get(LV_LABEL, float("nan")))
    best = min(scored, key=scored.get) if scored else fm.MODEL_LABEL
    avg = {
        "model_wape": model_w,
        "model_bias": float(np.mean([r["model_bias"] for r in rows])),
        "seasonal_naive_wape": naive_w,
        "last_value_wape": scored.get(LV_LABEL, float("nan")),
        "coverage_p10_p90": float(np.mean([r["coverage"] for r in rows])),
        "beats_seasonal_naive": bool(model_w < naive_w),
        "methods": scored,
        "best_method": best,
    }
    return {"folds": rows, "average": avg, "horizon": horizon, "season": season}
