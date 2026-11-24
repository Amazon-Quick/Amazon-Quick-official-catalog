"""
description: Validate and clean the input history for the Forecast Coach: sort by date, drop trailing blanks, count inner gaps, and report short series, duplicate periods, ambiguous dates, and negatives as issues to show the user.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import numpy as np
from periods import SEASON, AmbiguousDateError, as_date, normalise_freq
from periods import date_order as infer_date_order

MIN_POINTS = 8


def _values(obj) -> np.ndarray:
    raw = obj["values"] if isinstance(obj, dict) else obj
    return np.asarray(
        [
            np.nan if x is None or (isinstance(x, str) and not x.strip()) else x
            for x in list(raw)
        ],
        dtype=float,
    )


def _dates(obj, given_order: str | None) -> list | None:
    raw = obj.get("dates") if isinstance(obj, dict) else None
    if raw is None:
        return None
    raw = list(raw)
    if not raw:
        return None
    order = infer_date_order(raw, given_order)
    return [as_date(d, order) for d in raw]


def _drop_trailing_blanks(vals: np.ndarray, dates: list | None):
    k = len(vals) - 1
    while k >= 0 and np.isnan(vals[k]):
        k -= 1
    return vals[: k + 1], (dates[: k + 1] if dates else None)


def prepare(
    series: dict,
    freq: str | None = None,
    season: int | None = None,
    date_order: str | None = None,
) -> dict:
    """Validate and clean the input. Returns {'series', 'freq', 'season', 'issues'}; show issues first."""
    freq = normalise_freq(freq)
    season = int(season) if season else SEASON.get(freq, 12)
    clean, issues = {}, []
    for name, obj in series.items():
        vals = _values(obj)
        try:
            dates = _dates(obj, date_order)
        except AmbiguousDateError as err:
            issues.append(
                f"{name}: skipped; {err} Ask the user whether the dates are day-first or "
                "month-first, then pass date_order."
            )
            continue
        if dates is not None and len(dates) != len(vals):
            issues.append(
                f"{name}: {len(dates)} dates against {len(vals)} values; skipped"
            )
            continue
        if dates is not None:
            if len(set(dates)) != len(dates):
                issues.append(
                    f"{name}: the same period appears more than once; skipped. Sum or "
                    "pick one row per period first."
                )
                continue
            idx = np.argsort(dates)
            dates = [dates[i] for i in idx]
            vals = vals[idx]
        if len(vals) and np.isnan(vals[-1]):
            vals, dates = _drop_trailing_blanks(vals, dates)
            issues.append(f"{name}: trailing blanks dropped, now {len(vals)} points")
        if len(vals) < MIN_POINTS:
            issues.append(
                f"{name}: only {len(vals)} points, too short to forecast; skipped"
            )
            continue
        n_nan = int(np.isnan(vals).sum())
        if n_nan:
            issues.append(
                f"{name}: {n_nan} {'gap' if n_nan == 1 else 'gaps'} inside the history "
                "(treated as missing, not zero)"
            )
        if np.nanmin(vals) < 0:
            issues.append(
                f"{name}: contains negatives; fine for the baseline, but check the sign convention"
            )
        clean[name] = {"values": vals, "dates": dates}
    return {"series": clean, "freq": freq, "season": season, "issues": issues}
