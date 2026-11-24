"""
description: Build the shared reading of one line of history (expected values, scatter and seasonality) that both analyses start from.
last_updated: 2026-11-24

The shared reading of one line of history that both analyses start from.

`decompose()` splits a series into the parts a finance reader already thinks in:

    level      where the line is running once seasonality is taken out (it may step when the level shifts)
    seasonal   the usual pattern by position in the year (or week), from the other years only
    expected   level + seasonal for each period, worked out WITHOUT that period's own value
    residual   actual minus expected, and a robust score for how unusual that is for this line

Trend analysis reads the level; anomaly detection reads the residual. Neither changes the other's result.

Design choices, in short:
  * Values that are all positive are analyzed as ratios (logs), so "10% above expected" means the same on a
    large line and a small one. Lines with zeros or negatives are analyzed in their own units.
  * Seasonal adjustment is used where the pattern plainly repeats from one cycle to the next, and never
    with less than two full cycles of history.
  * A sustained step is found first and treated as a new level, so the periods after it are judged against
    the new level rather than each being called unusual. On seasonal lines steps are found on the
    year-over-year change, which carries no seasonality and needs no estimate of the level.
  * Scatter is measured robustly (the Qn estimator), so the unusual points do not hide themselves and a
    short line is not judged against a scatter that happens to have come out small.

numpy and the standard library only. Deterministic: the same input gives the same output.
"""

from __future__ import annotations

import math

import numpy as np
import series_stats as st
from engine_constants import MIN_AFTER as MIN_AFTER
from engine_constants import MIN_BEFORE as MIN_BEFORE
from engine_constants import MIN_POINTS, SCALE_FLOOR, SEASON, SEASONAL_GAIN
from engine_constants import NEIGHBOURS as NEIGHBOURS
from engine_constants import PER_YEAR as PER_YEAR
from engine_constants import SHIFT_T as SHIFT_T
from engine_constants import SLOPE_SPAN as SLOPE_SPAN
from engine_constants import W_AFTER as W_AFTER
from engine_constants import W_BEFORE as W_BEFORE
from engine_grain import infer_grain as infer_grain
from engine_grain import normalise_freq
from engine_level import _local_level, _regimes, _step_function
from engine_seasonal import _leave_out, _repeat_r, _seasonal, _seasonal_loo
from engine_shifts_confirm import _confirm_shifts
from engine_shifts_local import _find_shifts_local
from engine_shifts_yoy import _find_shifts_yoy

__all__ = [
    "decompose",
    "SEASON",
    "PER_YEAR",
    "MIN_AFTER",
    "normalise_freq",
    "infer_grain",
]


def decompose(
    values,
    freq: str = "MS",
    season: int | None = None,
    pos0: int = 0,
    z_threshold: float = 3.5,
    min_shift_pct: float = 0.05,
    max_shifts: int = 4,
    seasonal: bool | None = None,
) -> dict:
    """Split one line into level, seasonal pattern, expected values and scored residuals.

    values         the history, oldest first; NaN marks a missing period
    freq           D, W, MS, QS or YS (see normalise_freq)
    season         periods per seasonal cycle; default by freq (12 for months, 4 for quarters, 7 for days)
    pos0           position of the first period in its cycle (0 = January for months), so the seasonal
                   pattern is labeled correctly
    z_threshold    robust score at which a period counts as unusual (3.5 is the standard cut-off)
    min_shift_pct  smallest step, as a share of level, that can be called a new level
    seasonal       force seasonal adjustment on or off; None lets the data decide

    Returns a dict; the arrays all have one entry per period:
      status        'ok' or 'short' (fewer than MIN_POINTS usable periods; nothing else is filled in)
      mode          'ratio' (all values positive, analyzed as percentages) or 'amount'
      seasonal      whether seasonal adjustment was used; seasonal_index is the pattern by position
      expected      what each period would be on the line's own pattern, without using that period
      gap, gap_pct  actual minus expected, in units and as a share of expected
      score         robust z-score of the residual; flagged = |score| >= z_threshold
      level         the smooth level in units; adjusted = seasonally adjusted actuals in units
      shifts        [{'index', 'size', 'size_pct', 't', 'p'}] sustained steps; regime numbers them
      scale         typical unexplained movement (log units in ratio mode, else units); scale_pct as a share
    """
    y = np.asarray(values, dtype=float).ravel()
    n = len(y)
    f = normalise_freq(freq) or "MS"
    s = int(season) if season else SEASON[f]
    valid = np.isfinite(y)
    out = {
        "status": "ok",
        "n": n,
        "n_valid": int(valid.sum()),
        "freq": f,
        "season": s,
        "notes": [],
    }
    if valid.sum() < MIN_POINTS:
        out["status"] = "short"
        out["notes"].append(
            f"only {valid.sum()} periods of history; at least {MIN_POINTS} are needed to judge a line"
        )
        return out

    ratio = bool(np.all(y[valid] > 0))
    x = (
        np.where(valid, np.log(np.where(valid & (y > 0), y, 1.0)), np.nan)
        if ratio
        else y.copy()
    )
    typical = float(np.median(np.abs(y[valid])))
    floor = SCALE_FLOOR if ratio else max(SCALE_FLOOR * typical, 1e-12)
    min_shift = math.log1p(min_shift_pct) if ratio else min_shift_pct * typical
    pos = (np.arange(n) + int(pos0)) % s
    zero = np.zeros(n)
    no_reg = np.zeros(n, dtype=int)

    def score_with(adj, seas_loo, regime):
        expected = _local_level(adj, regime, leave_out=True) + seas_loo
        resid = x - expected
        return {
            "adj": adj,
            "seas_loo": seas_loo,
            "regime": regime,
            "expected": expected,
            "resid": resid,
            "score": st.robust_z(resid, floor),
            "scale": st.qn_scale(resid, floor),
            "screen": st.robust_z(resid, floor, screen=True),
        }

    def is_flagged(res):
        return np.isfinite(res["score"]) & (np.abs(res["score"]) >= z_threshold)

    plain0 = score_with(x, zero, no_reg)
    plain_shifts = _find_shifts_local(x, plain0["scale"], f, min_shift, max_shifts)
    r_plain = score_with(x, zero, _regimes(n, plain_shifts))

    use_seasonal, parts, r, shifts = False, None, r_plain, plain_shifts
    can_seasonal = s > 1 and n >= 2 * s and valid.sum() >= 2 * s - s // 4
    if can_seasonal and seasonal is not False and _seasonal(x, s, pos) is not None:
        # Steps first (on the year-over-year change), then the seasonal pattern with the steps taken out,
        # then the scores; repeated with the unusual periods left out of both, so one odd December does
        # not bend what every other December is compared with, nor pass for the start of a new level.
        sh = _find_shifts_yoy(x, s, f, min_shift, max_shifts)
        rs, ps, seen = None, _seasonal(x, s, pos), set()
        for _ in range(5):
            # which periods to leave out is decided on the cruder screening score: early on, a run of
            # unusual months has bent its neighbors too, and the regular scatter is inflated by all of them
            drop = (
                _leave_out(rs["screen"], pos, s, z_threshold)
                if rs is not None
                else np.zeros(n, dtype=bool)
            )
            p2 = _seasonal(np.where(drop, np.nan, x) - _step_function(n, sh), s, pos)
            ps = p2 if p2 is not None else ps
            rs = score_with(
                x - ps["S"][pos], _seasonal_loo(ps, pos, s), _regimes(n, sh)
            )
            now = (tuple(np.where(is_flagged(rs))[0]), tuple(h["index"] for h in sh))
            odd = np.isfinite(rs["screen"]) & (np.abs(rs["screen"]) >= z_threshold)
            nxt = _find_shifts_yoy(
                np.where(odd, np.nan, x), s, f, min_shift, max_shifts
            )
            nxt = _confirm_shifts(rs["adj"], nxt, rs["scale"], f, min_shift)
            # The year-over-year search sees a step that lasts. A level that moves and comes back within
            # the year (a few months of disruption) shows there as two half-blocks and is missed, so what
            # is left of the adjusted line is searched directly for steps close together.
            room = max_shifts - len(nxt)
            if room > 0:
                more = _find_shifts_local(
                    rs["adj"] - _step_function(n, nxt), rs["scale"], f, min_shift, room
                )
                if more:
                    nxt = _confirm_shifts(
                        rs["adj"],
                        sorted(nxt + more, key=lambda h: h["index"]),
                        rs["scale"],
                        f,
                        min_shift,
                    )
            if tuple(h["index"] for h in nxt) == now[1] and now in seen:
                break  # same flags, same steps as a pass already made: settled
            seen.add(now)
            sh = nxt
        rs = score_with(x - ps["S"][pos], _seasonal_loo(ps, pos, s), _regimes(n, sh))
        # adjust when the pattern plainly repeats from one cycle to the next, or when adjusting clearly
        # cuts the scatter and the pattern repeats at least loosely. A seasonal swing left in is a
        # systematic error (it reads as steps and bends the trend); the cost of adjusting is only noise.
        rep_r, rep_t = _repeat_r(ps["d"], s)
        if (
            bool(seasonal)
            or (rep_r >= 0.4 and rep_t >= 2.5)
            or (rs["scale"] < SEASONAL_GAIN * r_plain["scale"] and rep_r >= 0.25)
        ):
            use_seasonal, parts, r, shifts = True, ps, rs, sh
    elif s > 1 and seasonal is not False and not can_seasonal:
        out["notes"].append(
            "under two full cycles of history, so the seasonal pattern cannot be separated; "
            "a regular seasonal peak may read as unusual"
        )

    score = r["score"]
    flagged = is_flagged(r)
    adj_clean = np.where(
        flagged & np.isfinite(r["expected"]), r["expected"] - r["seas_loo"], r["adj"]
    )
    level_x = _local_level(adj_clean, r["regime"], leave_out=False)

    def units(v):
        return np.exp(v) if ratio else np.asarray(v, dtype=float).copy()

    expected = units(r["expected"])
    gap = y - expected
    with np.errstate(divide="ignore", invalid="ignore"):
        gap_pct = np.where(
            np.abs(expected) > 0.1 * typical, gap / np.abs(expected), np.nan
        )
    shift_out = []
    for h in shifts:
        c = h["index"]
        # size of the step as the gap between the level just after and the level just before
        after = level_x[c] if np.isfinite(level_x[c]) else np.nan
        before = level_x[c - 1] if c > 0 and np.isfinite(level_x[c - 1]) else np.nan
        size_x = (
            float(after - before)
            if np.isfinite(after) and np.isfinite(before)
            else h["size"]
        )
        if not np.isfinite(before):
            before = math.log(typical) if ratio else typical
        base = float(np.exp(before)) if ratio else float(before)
        size_units = base * math.expm1(size_x) if ratio else size_x
        size_pct = (
            math.expm1(size_x)
            if ratio
            else (size_x / abs(base) if abs(base) > 0.1 * typical else float("nan"))
        )
        shift_out.append(
            {
                "index": c,
                "size": float(size_units),
                "size_pct": float(size_pct),
                "size_x": size_x,
                "t": h["t"],
                "p": h["p"],
            }
        )

    out.update(
        {
            "mode": "ratio" if ratio else "amount",
            "seasonal": bool(use_seasonal),
            "seasonal_index": (np.expm1(parts["S"]) if ratio else parts["S"].copy())
            if use_seasonal
            else None,
            "seasonal_x": parts["S"].copy() if use_seasonal else None,
            "pos": pos,
            "x": x,
            "adj_x": r["adj"],
            "adj_clean_x": adj_clean,
            "level_x": level_x,
            "expected": expected,
            "gap": gap,
            "gap_pct": gap_pct,
            "resid_x": r["resid"],
            "score": score,
            "flagged": flagged,
            "regime": r["regime"],
            "shifts": shift_out,
            "level": units(level_x),
            "adjusted": units(r["adj"]),
            "scale": float(r["scale"]),
            "scale_pct": float(math.expm1(r["scale"])) if ratio else float("nan"),
            "typical": typical,
            "z_threshold": float(z_threshold),
        }
    )
    return out
