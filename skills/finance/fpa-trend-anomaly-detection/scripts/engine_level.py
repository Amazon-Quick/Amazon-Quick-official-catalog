"""
description: Local level per regime, and regime and step arrays from found shifts.
last_updated: 2026-11-24
"""

from __future__ import annotations

import numpy as np
import series_stats as st
from engine_constants import NEIGHBOURS, SLOPE_SPAN


def _local_level(z: np.ndarray, regime: np.ndarray, leave_out: bool) -> np.ndarray:
    """Level at each period from the nearest periods in the same regime, carried along the local slope.

    leave_out=True excludes the period's own value (used to judge it); False includes it (used to draw
    the level and measure the trend).
    """
    n = len(z)
    out = np.full(n, np.nan)
    valid = np.where(np.isfinite(z))[0]
    for t in range(n):
        lo, hi = max(0, t - 4 * SLOPE_SPAN), min(n, t + 4 * SLOPE_SPAN + 1)
        cand = valid[(valid >= lo) & (valid < hi)]
        cand = cand[regime[cand] == regime[t]]
        if leave_out:
            cand = cand[cand != t]
        if cand.size < 3:
            continue
        near = cand[np.argsort(np.abs(cand - t), kind="stable")]
        nb, sp = near[: NEIGHBOURS + (0 if leave_out else 1)], near[:SLOPE_SPAN]
        b = 0.0
        if sp.size >= 5:
            b = st.theil_sen(sp, z[sp])[0] * min(1.0, sp.size / SLOPE_SPAN)
        out[t] = float(np.median(z[nb] + b * (t - nb)))
    return out


def _regimes(n: int, shifts: list) -> np.ndarray:
    reg = np.zeros(n, dtype=int)
    for h in shifts:
        reg[h["index"] :] += 1
    return reg


def _step_function(n: int, shifts: list) -> np.ndarray:
    steps = np.zeros(n)
    for h in shifts:
        steps[h["index"] :] += h["size"]
    return steps
