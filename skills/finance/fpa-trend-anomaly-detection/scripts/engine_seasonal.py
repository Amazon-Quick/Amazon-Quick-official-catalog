"""
description: Seasonal pattern: cycle average, index, repeat test, other-years effect.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math

import numpy as np


def _cma(x: np.ndarray, s: int) -> np.ndarray:
    """Centred moving average over one full cycle (2 x s for an even cycle), tolerant of a few gaps."""
    n = len(x)
    out = np.full(n, np.nan)
    w = np.ones(s + 1 if s % 2 == 0 else s)
    if s % 2 == 0:
        w[0] = w[-1] = 0.5
    w = w / w.sum()
    h = len(w) // 2
    for t in range(h, n - h):
        seg = x[t - h : t + h + 1]
        ok = np.isfinite(seg)
        if w[ok].sum() >= 0.75:
            out[t] = float((seg[ok] * w[ok]).sum() / w[ok].sum())
    return out


def _extend(level: np.ndarray, s: int) -> np.ndarray | None:
    """Carry a centred average out to both ends along its own recent slope."""
    idx = np.where(np.isfinite(level))[0]
    if idx.size == 0:
        return None
    out = level.copy()
    out[idx[0] : idx[-1] + 1] = np.interp(
        np.arange(idx[0], idx[-1] + 1), idx, level[idx]
    )

    def slope(take):
        if take.size < 2:
            return 0.0
        return float(np.median(np.diff(level[take]) / np.diff(take)))

    g0, g1 = slope(idx[: min(s, idx.size)]), slope(idx[-min(s, idx.size) :])
    for t in range(idx[0]):
        out[t] = level[idx[0]] - g0 * (idx[0] - t)
    for t in range(idx[-1] + 1, len(level)):
        out[t] = level[idx[-1]] + g1 * (t - idx[-1])
    return out


def _seasonal(x: np.ndarray, s: int, pos: np.ndarray) -> dict | None:
    """Seasonal pattern as the median gap to the cycle-average level at each position in the cycle.

    The cycle average is exact for a steady trend, so the caller takes any steps out of x first.
    """
    level = _extend(_cma(x, s), s)
    if level is None:
        return None
    d = x - level
    raw = np.full(s, np.nan)
    for k in range(s):
        v = d[(pos == k) & np.isfinite(d)]
        if v.size == 0:
            return None
        raw[k] = float(np.median(v))
    centre = float(raw.mean())
    return {"S": raw - centre, "d": d, "centre": centre}


def _repeat_r(d: np.ndarray, s: int) -> tuple:
    """Does one cycle's pattern show up again in the next? Rank correlation of each period with the
    same period one cycle later. Returns (r, t-statistic); (0, 0) when there are too few pairs."""
    a, b = d[:-s], d[s:]
    ok = np.isfinite(a) & np.isfinite(b)
    m = int(ok.sum())
    if m < 8:
        return 0.0, 0.0
    ra, rb = (
        np.argsort(np.argsort(a[ok])).astype(float),
        np.argsort(np.argsort(b[ok])).astype(float),
    )
    if ra.std() == 0 or rb.std() == 0:
        return 0.0, 0.0
    r = float(np.corrcoef(ra, rb)[0, 1])
    return r, r * math.sqrt((m - 2) / max(1e-9, 1 - r * r))


def _seasonal_loo(parts: dict, pos: np.ndarray, s: int) -> np.ndarray:
    """For each period, the seasonal effect implied by the OTHER years at the same position."""
    d, out = parts["d"], np.empty(len(pos))
    for k in range(s):
        idx = np.where(pos == k)[0]
        good = idx[np.isfinite(d[idx])]
        for t in idx:
            others = good[good != t]
            out[t] = (
                (float(np.median(d[others])) - parts["centre"])
                if others.size
                else parts["S"][k]
            )
    return out


def _leave_out(
    score: np.ndarray, pos: np.ndarray, s: int, z_threshold: float
) -> np.ndarray:
    """Which unusual periods to leave out when the seasonal pattern is re-estimated.

    At each position in the cycle the most extreme flagged period goes (with any nearly as extreme), as
    long as other years remain to estimate from. With only two years at a position and both flagged about
    equally, neither is dropped: the data cannot say which year is the odd one, and both stay flagged.
    """
    out = np.zeros(len(score), dtype=bool)
    mag = np.where(np.isfinite(score), np.abs(score), 0.0)
    for k in range(s):
        idx = np.where((pos == k) & np.isfinite(score))[0]
        hit = idx[mag[idx] >= z_threshold]
        if hit.size == 0 or idx.size < 2:
            continue
        top = float(mag[hit].max())
        drop = hit[mag[hit] >= 0.75 * top]
        if idx.size - drop.size < 1:
            continue
        if idx.size == 2 and hit.size == 2 and mag[hit].min() >= 0.5 * top:
            continue
        out[drop] = True
    return out
