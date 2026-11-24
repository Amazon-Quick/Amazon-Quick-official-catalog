"""
description: The comment the Forecast Coach writes into each forecast cell: the band, the change from the last actual and the trailing average, the trend share, the seasonal position, and the band width.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import math

import numpy as np
from periods import PERIOD_LABEL, season_pos

WIDE_BAND = 0.4
FLAT_TREND = 1e-4


def _trend_pct(v: np.ndarray, season: int) -> float:
    """Slope of the recent history as a share of its own level, per period."""
    w = v[~np.isnan(v)][-max(2 * season, 6) :]
    if len(w) < 3:
        return 0.0
    x = np.arange(len(w), dtype=float)
    slope = float(np.polyfit(x, w, 1)[0])
    lvl = float(np.mean(np.abs(w))) or 1.0
    return slope / lvl


def _seasonal_index(v: np.ndarray, season: int) -> np.ndarray | None:
    """Average same-period deviation from a centered level, as a ratio. None when history is too short."""
    v = np.asarray(v, dtype=float)
    if season < 2 or len(v) < 2 * season:
        return None
    k = (len(v) // season) * season
    tail = v[-k:]
    base = np.nanmean(tail.reshape(-1, season), axis=1, keepdims=True)
    base = np.where(np.abs(base) < 1e-12, np.nan, base)
    if not np.isfinite(base).any():
        return None
    idx = np.nanmean(tail.reshape(-1, season) / base, axis=0)
    return idx if np.isfinite(idx).all() else None


def explain(name, i, period_label, p10, p50, p90, hist, dates, freq, season) -> str:
    """One cell comment that says something different per cell."""
    unit = PERIOD_LABEL.get(freq, "period")
    last = float(hist[~np.isnan(hist)][-1])
    tr = _trend_pct(hist, season)
    idx = _seasonal_index(hist, season)
    bits = [
        f"{name}: {period_label}",
        f"P50 {p50:,.1f}  (band {p10:,.1f} to {p90:,.1f})",
    ]
    bits.append(
        f"Last actual {last:,.1f}; this point is {(p50 / last - 1) * 100:+.1f}% against that."
        if last
        else "Last actual 0.0; percentage change is unavailable."
    )
    tw = hist[~np.isnan(hist)][-min(4, len(hist)) :]
    bits.append(
        f"Against the trailing {len(tw)}-period average {np.mean(tw):,.1f}: {(p50 / np.mean(tw) - 1) * 100:+.1f}%"
        if np.mean(tw)
        else f"Trailing {len(tw)}-period average 0.0; percentage change is unavailable."
    )
    bits.append(
        f"Recent trend {tr * 100:+.2f}% per {unit}"
        + (
            f", so {abs(tr) * 100 * (i + 1):.1f}% of the move by step {i + 1} is trend."
            if abs(tr) > FLAT_TREND
            else " (flat)."
        )
    )
    if idx is not None and dates is not None:
        pos = season_pos(dates[-1], freq, season, i + 1)
        if pos is not None and 0 <= pos < len(idx):
            bits.append(
                f"Seasonally this {unit} runs {(idx[pos] - 1) * 100:+.1f}% against the cycle average."
            )
    elif season > 1:
        bits.append(
            "History is under 2 full cycles, so no seasonal shape was estimated; expect flattened peaks."
        )
    width = (p90 - p10) / abs(p50) if p50 else float("nan")
    bits.append(
        f"Band width {width * 100:.1f}% of P50: {'wide, treat P50 as a midpoint only' if width > WIDE_BAND else 'reasonably tight'}."
        if math.isfinite(width)
        else "P50 is zero; percentage band width is unavailable."
    )
    return "\n".join(bits)
