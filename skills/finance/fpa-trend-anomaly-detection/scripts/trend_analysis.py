"""
description: Measure where a line is heading, how fast, whether that has changed, and its seasonal pattern.
last_updated: 2026-11-24

Trend analysis: where a line is heading, how fast, whether that has changed, and its seasonal pattern.

Works from the shared reading in series_engine.decompose(). For one line, `analyse()` returns:

    the standard comparisons   latest period against the prior period and the same period a year earlier,
                               the most recent few periods year over year, year to date, the last twelve
                               months (or 4 quarters / 52 weeks), and compound annual growth
    the trend                  the annual rate at which the level has moved, on the seasonally adjusted line
                               with one-offs set aside; a direction and whether it is clear; and, where the
                               level stepped, the underlying rate with the steps taken out
    a change in trend          the period where growth picked up, slowed or reversed, when the evidence is strong
    the seasonal pattern       how strong it is, and the peak and the low point
    what was set aside         the periods and steps left out of the trend, so nothing is cleaned silently

Flows (revenue, spend, units sold) are totaled over a window; balances and rates (inventory, headcount,
a margin) are averaged, because adding up twelve month-end balances means nothing.
"""

from __future__ import annotations

import datetime as _dt
import math

import numpy as np
import series_engine as eng
import series_stats as st

__all__ = ["analyse", "position_label", "PER_YEAR_N", "RECENT", "VOCAB"]

PER_YEAR_N = {
    "D": 364,
    "W": 52,
    "MS": 12,
    "QS": 4,
    "YS": 1,
}  # periods back to the same period a year earlier
RECENT = {
    "D": 28,
    "W": 13,
    "MS": 3,
    "QS": 2,
    "YS": 1,
}  # the "most recent few periods" window
TREND_SPAN = {
    "D": 182,
    "W": 104,
    "MS": 24,
    "QS": 8,
    "YS": 6,
}  # periods the underlying trend is measured over
MIN_SEG = {
    "D": 28,
    "W": 13,
    "MS": 6,
    "QS": 4,
    "YS": 3,
}  # periods each side of a change in trend
VOCAB = {
    "MS": {
        "unit": "month",
        "prior": "MoM",
        "recent": "Last 3 months",
        "ltm": "Last 12 months",
    },
    "QS": {
        "unit": "quarter",
        "prior": "QoQ",
        "recent": "Last 2 quarters",
        "ltm": "Last 4 quarters",
    },
    "W": {
        "unit": "week",
        "prior": "WoW",
        "recent": "Last 13 weeks",
        "ltm": "Last 52 weeks",
    },
    "D": {
        "unit": "day",
        "prior": "DoD",
        "recent": "Last 28 days",
        "ltm": "Last 52 weeks",
    },
    "YS": {
        "unit": "year",
        "prior": "YoY",
        "recent": "Latest year",
        "ltm": "Latest year",
    },
}
_MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]
_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def position_label(freq: str, k: int) -> str:
    """Name of a position in the seasonal cycle: a month, a quarter, a weekday or a week number."""
    if freq == "MS":
        return _MONTHS[k % 12]
    if freq == "QS":
        return f"Q{k % 4 + 1}"
    if freq == "D":
        return _DAYS[k % 7]
    return f"week {k + 1}"


def _pct(a, b):
    """a / b - 1 when that is meaningful (b clearly positive), else None."""
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b) or b <= 0:
        return None
    return float(a / b - 1.0)


def _window(y: np.ndarray, end: int, length: int, total: bool):
    """Sum (flows) or average (balances, rates) of `length` periods ending at index `end`; None if incomplete."""
    start = end - length + 1
    if start < 0 or end >= len(y):
        return None
    seg = y[start : end + 1]
    if not np.all(np.isfinite(seg)):
        return None
    return float(seg.sum() if total else seg.mean())


HINGE_BIC_GAIN = (
    10.0  # how far a broken line must beat one straight line on BIC to count
)


def _hinge_fit(t: np.ndarray, v: np.ndarray, k: int) -> tuple:
    """Residual sum of squares and coefficients of a line with one change in slope at t[k]."""
    x1 = np.column_stack([np.ones(t.size), t, np.maximum(0.0, t - t[k])])
    beta = np.linalg.lstsq(x1, v, rcond=None)[0]
    return float(((v - x1 @ beta) ** 2).sum()), beta


def _line_rss(t: np.ndarray, v: np.ndarray) -> float:
    """Residual sum of squares of one straight line through (t, v)."""
    x0 = np.column_stack([np.ones(t.size), t])
    return float(((v - x0 @ np.linalg.lstsq(x0, v, rcond=None)[0]) ** 2).sum())


def _bic_gain(rss0: float, rss1: float, m: int) -> float | None:
    """BIC improvement of the broken line over the straight one, or None when either fit is exact."""
    if not rss0 > 0 or not rss1 > 0:
        return None
    return m * math.log(rss0 / rss1) - 2.0 * math.log(m)


def _best_hinge(t: np.ndarray, v: np.ndarray, min_seg: int) -> tuple:
    """(BIC gain, position, coefficients) of the best single change in slope."""
    best = None
    for k in range(min_seg, t.size - min_seg):
        rss1, beta = _hinge_fit(t, v, k)
        if best is None or rss1 < best[0]:
            best = (rss1, k, beta)
    if best is None:
        return None, None, None
    return _bic_gain(_line_rss(t, v), best[0], t.size), best[1], best[2]


def _hinge_gain_at(t: np.ndarray, v: np.ndarray, k: int) -> float | None:
    """BIC gain of a change in slope at t[k] for the values v."""
    return _bic_gain(_line_rss(t, v), _hinge_fit(t, v, k)[0], t.size)


def _trend_change(
    z: np.ndarray,
    idx: np.ndarray,
    per_year: float,
    ratio: bool,
    level: float,
    min_seg: int,
):
    """Strongest single change in slope (a broken straight line against one straight line), if clear.

    Returns None, or {'index', 'before', 'after'} with annual rates. The broken line has to beat the
    straight one by a wide margin on BIC and the two rates have to differ by at least 3 points a year.
    """
    m = idx.size
    if m < 2 * min_seg + 2:
        return None
    t = idx.astype(float)
    v = z[idx]
    gain, k, beta = _best_hinge(t, v, min_seg)
    if gain is None or gain < HINGE_BIC_GAIN:
        return None
    if ratio:
        # On the log scale a steady amount added each period looks like slowing growth, because the
        # base grows. Report a change only when the amount added per period changed as well.
        amount_gain = _hinge_gain_at(t, np.exp(v), k)
        if amount_gain is None or amount_gain < HINGE_BIC_GAIN:
            return None

    def annual(slope):
        return (
            math.expm1(slope * per_year)
            if ratio
            else (slope * per_year / abs(level) if abs(level) > 1e-12 else float("nan"))
        )

    before, after = annual(beta[1]), annual(beta[1] + beta[2])
    if not (np.isfinite(before) and np.isfinite(after)) or abs(after - before) < 0.03:
        return None
    return {"index": int(idx[k]), "before": float(before), "after": float(after)}


def analyse(
    values,
    d: dict,
    labels: list,
    dates: list | None = None,
    kind: str = "flow",
    fiscal_year_start: int = 1,
    name: str = "",
) -> dict:
    """Trend facts for one line.

    values             the history, oldest first (NaN = missing)
    d                  series_engine.decompose() for the same values
    labels, dates      period labels, and dates when known (needed for year to date)
    kind               'flow' (totaled over a window), or 'balance' / 'rate' (averaged)
    fiscal_year_start  month the fiscal year starts in (1 = January)
    Every comparison is None when the history does not reach far enough or a period in it is missing.
    """
    y = np.asarray(values, dtype=float)
    n = len(y)
    f = d.get("freq", "MS")
    voc = VOCAB[f]
    total = kind == "flow"
    valid = np.isfinite(y)
    out = {
        "name": name,
        "kind": kind,
        "basis": "Total" if total else "Average",
        "periods": int(valid.sum()),
        "status": d.get("status", "short"),
        "notes": list(d.get("notes", [])),
    }
    if valid.sum() == 0:
        return out
    first, last = int(np.where(valid)[0][0]), int(np.where(valid)[0][-1])
    lag, rec = PER_YEAR_N[f], RECENT[f]
    out.update(
        {
            "first_period": labels[first],
            "last_period": labels[last],
            "last_value": float(y[last]),
        }
    )

    prev = y[last - 1] if last >= 1 and valid[last - 1] else None
    out["prior_change"] = None if prev is None else float(y[last] - prev)
    out["prior_pct"] = _pct(y[last], prev)
    ya = y[last - lag] if last - lag >= 0 and valid[last - lag] else None
    out["yoy_change"] = None if ya is None else float(y[last] - ya)
    out["yoy_pct"] = _pct(y[last], ya) if f != "YS" else out["prior_pct"]
    r_now, r_then = _window(y, last, rec, total), _window(y, last - lag, rec, total)
    out["recent"], out["recent_prior_year"], out["recent_yoy_pct"] = (
        r_now,
        r_then,
        _pct(r_now, r_then),
    )
    ltm_len = lag if f != "D" else 364
    l_now, l_then = (
        _window(y, last, ltm_len, total),
        _window(y, last - lag, ltm_len, total),
    )
    out["ltm"], out["ltm_prior"], out["ltm_pct"] = l_now, l_then, _pct(l_now, l_then)
    out["ltm_change"] = (
        None if l_now is None or l_then is None else float(l_now - l_then)
    )

    out["ytd"] = out["ytd_prior"] = out["ytd_pct"] = None
    out["ytd_periods"] = 0
    if dates and dates[last] is not None and f != "YS":
        end = dates[last]
        m0 = int(fiscal_year_start)
        fy_start = _dt.date(end.year if end.month >= m0 else end.year - 1, m0, 1)
        cur = [
            t
            for t in range(first, last + 1)
            if dates[t] is not None and dates[t] >= fy_start
        ]
        if cur and cur[0] - lag >= 0:
            a, b = (
                _window(y, last, len(cur), total),
                _window(y, last - lag, len(cur), total),
            )
            out.update(
                {
                    "ytd": a,
                    "ytd_prior": b,
                    "ytd_pct": _pct(a, b),
                    "ytd_periods": len(cur),
                    "ytd_from": labels[cur[0]],
                }
            )

    out["cagr_pct"] = out["cagr_years"] = None
    years = (last - first + 1) // lag - 1
    if years >= 2 and l_now is not None:
        then = _window(y, last - years * lag, ltm_len, total)
        if then is not None and then > 0 and l_now > 0:
            out["cagr_pct"], out["cagr_years"] = (
                float((l_now / then) ** (1.0 / years) - 1.0),
                int(years),
            )

    # consecutive periods of year-over-year growth (or decline)
    streak, sign = 0, 0
    for t in range(last, lag - 1, -1):
        if not (valid[t] and valid[t - lag]) or y[t] == y[t - lag]:
            break
        sg = 1 if y[t] > y[t - lag] else -1
        if sign == 0:
            sign = sg
        if sg != sign:
            break
        streak += 1
    out["yoy_streak"] = int(streak * sign)

    if d.get("status") != "ok":
        out["direction"] = "Not enough history"
        out["read"] = (
            f"{name or 'This line'}: {valid.sum()} periods of history, too few to describe a trend."
        )
        return out

    #      with one-offs set aside. Level shifts are part of that movement; the rate with them taken out
    #      is reported beside it as the underlying trend, because a step and steady growth are different news.
    ratio = d["mode"] == "ratio"
    per_year = eng.PER_YEAR[f]
    steps = np.zeros(n)
    for h in d["shifts"]:
        steps[h["index"] :] += h["size_x"]
    with_steps = d["adj_clean_x"]
    z = with_steps - steps
    idx = np.where(np.isfinite(z))[0]
    win = idx[-TREND_SPAN[f] :]
    level_now = (
        float(d["level"][last]) if np.isfinite(d["level"][last]) else float(y[last])
    )

    def annual(slope):
        if ratio:
            return math.expm1(slope * per_year)
        return (
            slope * per_year / abs(level_now)
            if abs(level_now) > 0.1 * d["typical"]
            else float("nan")
        )

    under_slope = st.theil_sen(win, z[win])[0] if win.size >= 4 else 0.0
    lv = d["level_x"]
    ends = [t for t in win if np.isfinite(lv[t])]
    total_slope = (
        (lv[ends[-1]] - lv[ends[0]]) / (ends[-1] - ends[0])
        if len(ends) >= 2 and ends[-1] > ends[0]
        else under_slope
    )
    steps_in_window = [
        h for h in d["shifts"] if win.size and win[0] < h["index"] <= win[-1]
    ]
    if not steps_in_window:
        total_slope = under_slope  # no step in the window: the two are the same thing
    rate, under = annual(total_slope), annual(under_slope)
    out["trend_pct"] = float(rate) if np.isfinite(rate) else None
    out["trend_per_year"] = None if ratio else float(total_slope * per_year)
    out["underlying_pct"] = (
        float(under) if np.isfinite(under) and steps_in_window else None
    )
    mk = st.mann_kendall(with_steps[win])
    out["trend_p"] = float(mk["p"])
    clear = mk["p"] <= 0.05 and win.size >= 8
    small = np.isfinite(rate) and abs(rate) < 0.01
    out["direction"] = (
        "Flat" if (not clear or small) else ("Rising" if total_slope > 0 else "Falling")
    )
    out["trend_window"] = (
        f"{labels[int(win[0])]} to {labels[int(win[-1])]}" if win.size else ""
    )

    span = idx[-5 * int(round(per_year)) :] if per_year > 1 else idx
    chg = _trend_change(z, span, per_year, ratio, level_now, MIN_SEG[f])
    out["trend_change"] = None
    if chg is not None:
        b, a = chg["before"], chg["after"]
        if b * a < 0 and min(abs(a), abs(b)) >= 0.01:
            word = "Reversed"
        elif abs(a) > abs(b):
            word = "Picked up" if a > 0 else "Decline deepened"
        else:
            word = "Slowed" if b > 0 else "Decline eased"
        out["trend_change"] = {
            "period": labels[chg["index"]],
            "index": chg["index"],
            "before_pct": b,
            "after_pct": a,
            "word": word,
        }

    out["level_shifts"] = [
        {
            "period": labels[h["index"]],
            "index": h["index"],
            "size": h["size"],
            "size_pct": h["size_pct"],
            "size_x": h["size_x"],
        }
        for h in d["shifts"]
    ]
    out["set_aside"] = [labels[t] for t in np.where(d["flagged"])[0]]

    s = d["season"]
    out["seasonal"] = bool(d["seasonal"])
    if d["seasonal"]:
        detr = d["x"] - d["level_x"]
        rem = detr - d["seasonal_x"][d["pos"]]
        ok = np.isfinite(detr) & np.isfinite(rem) & ~d["flagged"]
        strength = (
            max(0.0, 1.0 - float(np.var(rem[ok])) / float(np.var(detr[ok])))
            if ok.sum() > 3 and np.var(detr[ok]) > 0
            else 0.0
        )
        hi, lo = int(np.argmax(d["seasonal_x"])), int(np.argmin(d["seasonal_x"]))
        out.update(
            {
                "seasonal_strength": float(strength),
                "seasonal_label": "Strong"
                if strength >= 0.6
                else "Moderate"
                if strength >= 0.3
                else "Weak",
                "peak": position_label(f, hi),
                "peak_index": float(d["seasonal_index"][hi]),
                "trough": position_label(f, lo),
                "trough_index": float(d["seasonal_index"][lo]),
            }
        )
    else:
        too_short = s > 1 and n < 2 * s
        out.update(
            {
                "seasonal_strength": None,
                "peak": None,
                "trough": None,
                "peak_index": None,
                "trough_index": None,
                "seasonal_label": "Not assessed (under two years)"
                if too_short
                else "None found",
            }
        )
    out["noise_pct"] = float(d["scale_pct"]) if ratio else None
    out["noise"] = None if ratio else float(d["scale"])

    def p(v, signed=True):
        if v is None or not np.isfinite(v):
            return "n/a"
        return (
            ("%+.0f%%" if signed else "%.0f%%") % (100 * v)
            if abs(v) >= 0.095
            else ("%+.1f%%" if signed else "%.1f%%") % (100 * v)
        )

    who = name or "This line"
    under = (
        ""
        if out["underlying_pct"] is None
        else "{} a year with the level shifts taken out".format(
            p(out["underlying_pct"])
        )
    )
    if out["direction"] == "Flat":
        inside = (
            []
            if out["trend_pct"] is None
            else [
                "{} a year, not clearly different from zero".format(p(out["trend_pct"]))
            ]
        )
        inside += [under] if under else []
        lead = f"{who} is broadly flat" + (
            " ({})".format("; ".join(inside)) if inside else ""
        )
    else:
        size = (
            p(abs(out["trend_pct"]), signed=False)
            if out["trend_pct"] is not None
            else "{:,.0f}".format(abs(out["trend_per_year"]))
        )
        lead = "{} is {} at about {} a year".format(
            who, out["direction"].lower(), size
        ) + (f" ({under})" if under else "")
    bits = [lead]
    if out["trend_change"]:
        c = out["trend_change"]
        bits.append(
            "the underlying trend {} around {} (from {} to {} a year)".format(
                c["word"].lower(), c["period"], p(c["before_pct"]), p(c["after_pct"])
            )
        )
    steps_said, k, sh = [], 0, out["level_shifts"]
    while k < len(sh):
        h, nx = sh[k], (sh[k + 1] if k + 1 < len(sh) else None)
        if (
            nx is not None
            and h["size_x"] * nx["size_x"] < 0
            and abs(h["size_x"] + nx["size_x"])
            <= 0.5 * max(abs(h["size_x"]), abs(nx["size_x"]))
        ):
            # down and back up (or the reverse): one temporary change, not two steps
            steps_said.append(
                "a temporary {} of about {} from {} to {}".format(
                    "rise" if h["size"] > 0 else "drop",
                    p(abs(h["size_pct"]), signed=False),
                    h["period"],
                    labels[nx["index"] - 1],
                )
            )
            k += 2
            continue
        steps_said.append(
            "a step {} of about {} from {}".format(
                "up" if h["size"] > 0 else "down",
                p(abs(h["size_pct"]), signed=False),
                h["period"],
            )
        )
        k += 1
    bits += steps_said[-2:]
    if out["yoy_pct"] is not None and f != "YS":
        bits.append(
            "{} is {} on a year earlier".format(out["last_period"], p(out["yoy_pct"]))
        )
    if out["ltm_pct"] is not None and f != "YS":
        bits.append("the {} are {}".format(voc["ltm"].lower(), p(out["ltm_pct"])))
    if d["seasonal"] and out["seasonal_strength"] >= 0.3:
        bits.append(
            "{} seasonal pattern, highest in {} ({}) and lowest in {} ({})".format(
                out["seasonal_label"].lower(),
                out["peak"],
                p(out["peak_index"]),
                out["trough"],
                p(out["trough_index"]),
            )
        )
    if out["set_aside"]:
        shown = ", ".join(out["set_aside"][:4]) + (
            f" and {len(out['set_aside']) - 4} more"
            if len(out["set_aside"]) > 4
            else ""
        )
        bits.append(f"unusual periods set aside from the trend: {shown}")
    out["read"] = bits[0] + ("; " + "; ".join(bits[1:]) if len(bits) > 1 else "") + "."
    return out
