"""
description: Find level shifts in a seasonal series from the year-over-year change.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math

import numpy as np
import series_stats as st
from engine_constants import MIN_AFTER, SHIFT_T


def _find_shifts_yoy(
    x: np.ndarray, s: int, freq: str, min_shift: float, max_shifts: int
) -> list:
    """Sustained steps in a seasonal series, read off the change from the same period one cycle earlier.

    That change carries no seasonal pattern and needs no estimate of the level. A step of size d at
    period c lifts it by d for exactly one cycle, from c to c + s - 1, so the search is for the block of
    one cycle's length that stands furthest from the rest. A step in the first cycle shows only as the
    end of its block; a step on a cycle boundary with nothing but one cycle either side can be read as
    a step there or as an opposite step a cycle away, and the reading with the gentler underlying growth
    is taken.
    """
    n = len(x)
    ma = MIN_AFTER[freq]
    v = np.full(n, np.nan)
    v[s:] = x[s:] - x[:-s]
    idx = np.where(np.isfinite(v))[0]
    if idx.size < ma + 3:
        return []
    dv = np.diff(v[idx])[np.diff(idx) == 1]
    if dv.size < 4:
        return []
    # noise of the year-over-year change, from its own period-to-period differences (a step moves two
    # of them, so the median absolute deviation does not see it)
    sigma_v = st.mad_scale(dv) / math.sqrt(2.0)
    if not sigma_v > 0:
        return []
    resid = v.copy()
    found: list = []
    for _ in range(max_shifts):
        flat = float(np.abs(resid[idx] - np.median(resid[idx])).sum())
        cands = []
        for c in range(1, n - ma + 1):
            inside = idx[(idx >= c) & (idx < c + s)]
            outside = idx[(idx < c) | (idx >= c + s)]
            if inside.size < ma or outside.size < 3:
                continue
            m_in, m_out = (
                float(np.median(resid[inside])),
                float(np.median(resid[outside])),
            )
            diff = m_in - m_out
            se = sigma_v * math.sqrt(1.57 / inside.size + 1.57 / outside.size)
            t = diff / se
            if abs(t) < SHIFT_T or abs(diff) < min_shift:
                continue
            cost = float(
                np.abs(resid[inside] - m_in).sum()
                + np.abs(resid[outside] - m_out).sum()
            )
            gain = (flat - cost) / idx.size
            if gain > 0:
                cands.append((gain, c, diff, t, abs(m_out), inside, outside))
        if not cands:
            break
        top = max(r[0] for r in cands)
        # near-ties: the gentler underlying growth first, then the earlier period
        close = sorted(
            (r for r in cands if r[0] >= 0.95 * top),
            key=lambda r: (round(r[4], 9), r[1]),
        )
        hit = None
        for _gain, c, diff, t, _, inside, outside in close + sorted(
            (r for r in cands if r[0] < 0.95 * top), key=lambda r: -r[0]
        ):
            p = st.mann_whitney(resid[inside], resid[outside])["p"]
            if p <= 0.05:
                hit = {
                    "index": int(c),
                    "size": float(diff),
                    "t": float(t),
                    "p": float(p),
                }
                resid[inside] -= diff
                break
        if hit is None:
            break
        found.append(hit)
    return sorted(found, key=lambda h: h["index"])
