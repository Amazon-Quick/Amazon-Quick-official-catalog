"""
description: Find level shifts in a non-seasonal series by best-split search.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math

import numpy as np
import series_stats as st
from engine_constants import MIN_AFTER, MIN_BEFORE, SHIFT_T, W_AFTER, W_BEFORE
from engine_slope import _within_side_slope


def _find_shifts_local(
    z: np.ndarray, scale: float, freq: str, min_shift: float, max_shifts: int
) -> list:
    """Sustained steps in a series with no seasonal pattern, by repeated best-split search.

    A step is accepted when the typical level after it differs from the typical level before it (both
    carried along the local slope) by at least SHIFT_T standard errors and by at least `min_shift`, and
    a Mann-Whitney test agrees the two sides differ. It must have held for MIN_AFTER periods.
    """
    ok = np.isfinite(z)
    wa, wb, ma = W_AFTER[freq], W_BEFORE[freq], MIN_AFTER[freq]
    found: list = []

    def best_split(lo: int, hi: int):
        vi = np.where(ok[lo:hi])[0] + lo
        cands = []
        for c in range(lo + 1, hi):
            after = vi[(vi >= c) & (vi < c + wa)]
            b_idx = vi[(vi < c) & (vi >= c - wb)]
            if after.size < ma or b_idx.size < MIN_BEFORE:
                continue
            best = None
            # a new level may hold for only a few periods before the next change, so the comparison is
            # tried on the first 3, 4, ... periods after the candidate and the clearest one is kept
            for la in range(ma, after.size + 1):
                a_idx = after[:la]
                both = np.concatenate([b_idx, a_idx])
                slope, vfac = _within_side_slope(both, z, c)
                da, db = z[a_idx] - slope * (a_idx - c), z[b_idx] - slope * (b_idx - c)
                diff = float(np.median(da) - np.median(db))
                gap = float(a_idx.mean() - b_idx.mean())
                se = scale * math.sqrt(
                    1.57 / a_idx.size + 1.57 / b_idx.size + vfac * gap * gap
                )
                t = diff / se if se > 0 else 0.0
                if best is None or abs(t) > abs(best[0]):
                    best = (t, diff, da, db, both)
            t, diff, da, db, both = best
            if abs(t) < SHIFT_T or abs(diff) < min_shift:
                continue
            # does "one slope with a step here" describe these periods better than one straight line?
            # The fit is sharpest at the true first period of the new level, which is what places it.
            cost_step = float(
                np.abs(da - np.median(da)).sum() + np.abs(db - np.median(db)).sum()
            )
            s0, i0 = st.theil_sen(both, z[both])
            cost_line = float(np.abs(z[both] - (i0 + s0 * both)).sum())
            gain = (cost_line - cost_step) / both.size
            if gain > 0:
                cands.append((gain, c, diff, t, da, db))
        for _, c, diff, t, da, db in sorted(cands, key=lambda r: -r[0]):
            p = st.mann_whitney(da, db)["p"]
            if p <= 0.05:
                return {"index": int(c), "size": diff, "t": float(t), "p": float(p)}
        return None

    def search(lo: int, hi: int):
        if len(found) >= max_shifts or hi - lo < MIN_BEFORE + ma:
            return
        hit = best_split(lo, hi)
        if hit is None:
            return
        found.append(hit)
        search(lo, hit["index"])
        search(hit["index"], hi)

    search(0, len(z))
    return sorted(found, key=lambda h: h["index"])
