"""
description: Normalise frequency labels and infer the time grain from date gaps.
last_updated: 2026-11-24
"""

from __future__ import annotations

import numpy as np
from engine_constants import SEASON

_FREQ = {
    "m": "MS",
    "mon": "MS",
    "month": "MS",
    "monthly": "MS",
    "ms": "MS",
    "me": "MS",
    "q": "QS",
    "quarter": "QS",
    "quarterly": "QS",
    "qs": "QS",
    "qe": "QS",
    "w": "W",
    "week": "W",
    "weekly": "W",
    "d": "D",
    "day": "D",
    "daily": "D",
    "b": "D",
    "y": "YS",
    "a": "YS",
    "year": "YS",
    "annual": "YS",
    "yearly": "YS",
    "ys": "YS",
    "ye": "YS",
}


def normalise_freq(freq) -> str | None:
    """Map 'M', 'monthly', 'W-SUN', 'QE-DEC' and the like to one of D, W, MS, QS, YS. None if unknown."""
    if not freq:
        return None
    f = str(freq).strip()
    if f in SEASON:
        return f
    return _FREQ.get(f.split("-")[0].lower(), _FREQ.get(f.lower()))


def infer_grain(dates) -> dict:
    """Work out the time grain from the spacing of the dates.

    Returns {'freq', 'confident', 'why'}. `confident` is False when there are no dates, too few of them,
    or the spacing is mixed, and the caller should then ask the user rather than guess.
    """
    ds = sorted(d for d in (dates or []) if d is not None)
    if len(ds) < 3:
        return {
            "freq": None,
            "confident": False,
            "why": "fewer than three dated periods",
        }
    gaps = np.array(
        [(b - a).days for a, b in zip(ds, ds[1:], strict=False)], dtype=float
    )
    gaps = gaps[gaps > 0]
    if gaps.size < 2:
        return {"freq": None, "confident": False, "why": "the dates do not advance"}
    bands = [
        ("D", 0.5, 3.5),
        ("W", 5.5, 9.5),
        ("MS", 27.5, 32.5),
        ("QS", 88.5, 93.5),
        ("YS", 360, 370),
    ]
    share = {f: float(np.mean((gaps >= lo) & (gaps <= hi))) for f, lo, hi in bands}
    best = max(share, key=share.get)
    if share[best] >= 0.9:
        return {
            "freq": best,
            "confident": True,
            "why": f"{100 * share[best]:.0f}% of gaps between periods fit",
        }
    med = float(np.median(gaps))
    guess = (
        "D"
        if med <= 3.5
        else "W"
        if med <= 10
        else "MS"
        if med <= 45
        else "QS"
        if med <= 135
        else "YS"
    )
    return {
        "freq": guess,
        "confident": False,
        "why": f"period spacing is mixed (typical gap {med:.0f} days, only {100 * share[best]:.0f}% regular)",
    }
