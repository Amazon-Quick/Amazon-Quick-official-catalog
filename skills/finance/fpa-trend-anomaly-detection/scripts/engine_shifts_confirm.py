"""
description: Re-place each found level shift and keep those the adjusted line shows.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math

import numpy as np
from engine_constants import MIN_AFTER, W_AFTER, W_BEFORE
from engine_slope import _within_side_slope


def _confirm_shifts(
    adj: np.ndarray, shifts: list, scale: float, freq: str, min_shift: float
) -> list:
    """Place each step exactly and keep only the ones that show in the seasonally adjusted series itself.

    The year-over-year search is blunt in two ways. It places a step to within a period or two, because
    each period there is the difference of two noisy values. And it can pick up things that are not a
    step in the level: a lasting change in growth, or the echo a year after a temporary dip. So each
    step is moved to the nearby period where "one slope with a step here" fits the adjusted series best,
    then re-measured as the typical level after it against the typical level before it, and dropped if
    that gap is small or unclear.
    """
    ok = np.where(np.isfinite(adj))[0]
    wa, wb, ma = W_AFTER[freq], W_BEFORE[freq], MIN_AFTER[freq]
    cuts = [0] + [h["index"] for h in shifts] + [len(adj)]
    kept = []
    for i, h in enumerate(shifts):
        c0, lo, hi = h["index"], cuts[i], cuts[i + 2]
        window = ok[(ok >= max(lo, c0 - wb)) & (ok < min(hi, c0 + wa + 2))]
        best = None
        for c in range(max(lo + 1, c0 - 2), min(hi - 1, c0 + 2) + 1):
            a_idx, b_idx = window[window >= c], window[window < c]
            if a_idx.size < min(ma, 2) or b_idx.size < 2:
                continue
            slope, vfac = _within_side_slope(window, adj, c)
            da, db = adj[a_idx] - slope * (a_idx - c), adj[b_idx] - slope * (b_idx - c)
            cost = float(
                np.abs(da - np.median(da)).sum() + np.abs(db - np.median(db)).sum()
            )
            if best is None or cost < best[0] - 1e-12:
                near = a_idx[:wa]
                diff = float(np.median(adj[near] - slope * (near - c)) - np.median(db))
                gap = float(near.mean() - b_idx.mean())
                se = scale * math.sqrt(
                    1.57 / near.size + 1.57 / b_idx.size + vfac * gap * gap
                )
                best = (cost, c, diff, se)
        if best is None:
            kept.append(
                h
            )  # too little either side to re-measure; leave the call as made
            continue
        _, c, diff, se = best
        if (
            abs(diff) >= min_shift
            and se > 0
            and abs(diff / se) >= 3.0
            and diff * h["size"] > 0
        ):
            kept.append(
                {"index": int(c), "size": diff, "t": float(diff / se), "p": h["p"]}
            )
    kept = sorted(kept, key=lambda r: r["index"])
    out, i = [], 0
    while i < len(kept):
        if i + 1 < len(kept) and kept[i + 1]["index"] - kept[i]["index"] < ma:
            i += 2  # a level that held for under MIN_AFTER periods is not a
            continue  # level: those periods are left to be flagged one by one
        out.append(kept[i])
        i += 1
    return out
