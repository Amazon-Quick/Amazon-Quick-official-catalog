"""
description: Slope from pairs on one side of a candidate step, for sizing shifts.
last_updated: 2026-11-24
"""

from __future__ import annotations

import numpy as np


def _within_side_slope(idx: np.ndarray, z: np.ndarray, c: int) -> tuple:
    """Slope from pairs of periods on the same side of a candidate step, so the step cannot bias it.

    Returns (slope, variance factor): the slope's variance is about sigma^2 x the factor.
    """
    left, right = idx[idx < c], idx[idx >= c]
    slopes, denom = [], 0.0
    for side in (left, right):
        if side.size >= 2:
            i, j = np.triu_indices(side.size, 1)
            slopes.append((z[side[j]] - z[side[i]]) / (side[j] - side[i]))
            denom += float(((side - side.mean()) ** 2).sum())
    if not slopes or denom <= 0:
        return 0.0, 0.0
    return float(np.median(np.concatenate(slopes))), 1.0 / denom
