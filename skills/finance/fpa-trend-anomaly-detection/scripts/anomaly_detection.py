"""
description: Find the periods that do not fit a line's own pattern, size them in amount and percent, and label each one-off, temporary or a new level.
last_updated: 2026-11-24

Anomaly detection: which periods do not fit a line's own pattern, by how much, and what kind of thing it is.

Works from the shared reading in series_engine.decompose(). It does three things and nothing else:

    find_events()     turns unusual periods and level shifts into a short list of events, each typed
                      (one-off, offsetting pair, temporary, new level, too early to tell) with the actual,
                      the expected value, the gap, how strong the evidence is, and what to check
    data_checks()     things that look like a problem with the data rather than the business: a missing
                      period, a zero where a value belongs, a flipped sign, a units slip, a repeated value
    is_material()     applies the reader's own thresholds (a percentage, an amount, or both)

It never says why something happened. It has only the line's history, so it can say that a period is
unusual and what kind of event it looks like, and name the usual things to check.
"""

from __future__ import annotations

import math

import numpy as np
import series_engine as eng
import series_stats as st

__all__ = ["find_events", "data_checks", "is_material", "TYPE_LABEL", "CHECK_HINT"]

TYPE_LABEL = {
    "one_off": "One-off",
    "pair": "Offsetting pair",
    "temporary": "Temporary",
    "latest": "Latest period: too early to tell",
    "new_level": "New level",
    "temporary_level": "Temporary change in level",
    "unwound_level": "Step in level, since unwound",
    "either_year": "Differs from the other year",
}
CHECK_HINT = {
    "one_off": "A one-time item, a timing difference, a catch-up or true-up, or a miscoding. If it was a one-off, leave it out of any run-rate.",
    "pair": "Timing between the two periods: a cut-off or accrual that reversed, or an item booked in the wrong period. The two largely net off.",
    "temporary": "Something that held for a few periods and then ended: a promotion, an outage, a short contract, a backlog being cleared.",
    "latest": "Whether the period is complete and final, then whether this is a one-off or the start of a new level. The next period or two will tell.",
    "new_level": "A lasting change: pricing, volume or scope, a reclassification, an acquisition or disposal, a change in method. If it is real, earlier periods are no longer a fair comparison.",
    "temporary_level": "A change that lasted several periods and then reversed. Check what started and stopped at those two dates.",
    "unwound_level": "A change that began abruptly and wore off gradually. Check what happened at the start date and whether its effect has now fully passed.",
    "either_year": "With two years of history the same period in the two years disagree and either could be the unusual one. Check both.",
}
ESD_MIN = 15  # NIST: critical values reasonably accurate from 15 observations


def _fmt_amt(v: float) -> str:
    a = abs(v)
    if a >= 100:
        return f"{v:,.0f}"
    if a >= 1:
        return f"{v:,.1f}"
    return f"{v:,.3f}"


def _fmt_pct(v: float) -> str:
    return (
        "n/a"
        if not np.isfinite(v)
        else "%+.0f%%" % (100 * v)
        if abs(v) >= 0.095
        else "%+.1f%%" % (100 * v)
    )


def is_material(
    gap: float,
    gap_pct: float,
    min_pct: float = 0.10,
    min_amount: float = 0.0,
    rule: str = "both",
) -> bool:
    """Apply the reader's thresholds to one gap.

    rule='both'    the gap must reach the percentage AND the amount (an amount of 0 means no amount test)
    rule='either'  reaching one of them is enough (an amount of 0 then means percentage only)
    A gap whose percentage cannot be computed (expected near zero) is judged on the amount alone.
    """
    amt_ok = abs(gap) >= min_amount
    if not np.isfinite(gap_pct):
        return bool(amt_ok and (min_amount > 0 or rule == "both"))
    pct_ok = abs(gap_pct) >= min_pct
    if rule == "either":
        return bool(pct_ok or (min_amount > 0 and amt_ok))
    return bool(pct_ok and amt_ok)


def _runs(flagged: np.ndarray, sign: np.ndarray, valid: np.ndarray) -> list:
    """Consecutive flagged periods with the same sign. A missing period in between ends a run."""
    out, i, n = [], 0, len(flagged)
    while i < n:
        if not flagged[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and flagged[j + 1] and sign[j + 1] == sign[i] and valid[j + 1]:
            j += 1
        out.append((i, j))
        i = j + 1
    return out


def find_events(
    d: dict,
    labels: list,
    kind: str = "flow",
    esd_alpha: float = 0.05,
    direction: str = "both",
) -> list:
    """Turn a decomposition into a list of events, most recent first within each type.

    d          the dict from series_engine.decompose() (status 'ok')
    labels     period labels, one per period
    kind       'flow', 'balance' or 'rate': a total over several periods is shown only for flows
    direction  'both', 'above' or 'below': keep only events on that side of expected
    Each event: type, type_label, start, end, periods, peak, period (label or 'a to b'), direction,
    actual, expected, gap, gap_pct, total_gap, score, evidence, basis, why, check, since_end.
    """
    if d.get("status") != "ok":
        return []
    n, f, s = d["n"], d["freq"], d["season"]
    score, gap, gap_pct, expected = d["score"], d["gap"], d["gap_pct"], d["expected"]
    y = (
        np.exp(d["x"]) if d["mode"] == "ratio" else np.asarray(d["x"], dtype=float)
    )  # the actuals
    valid = np.isfinite(y)
    last_valid = int(np.where(valid)[0][-1])
    flagged = d["flagged"]
    sign = np.sign(np.where(np.isfinite(score), score, 0.0))
    ma = eng.MIN_AFTER[f]

    scoreable = np.isfinite(d["resid_x"])
    esd_hits = set()
    tested = int(scoreable.sum()) >= ESD_MIN
    if tested:
        esd_hits = set(st.generalized_esd(d["resid_x"], alpha=esd_alpha)["outliers"])

    basis = (
        "the level of the surrounding periods and the usual pattern for that {} in the other years".format(
            {"MS": "month", "QS": "quarter", "W": "week", "D": "weekday", "YS": "year"}[
                f
            ]
        )
        if d["seasonal"]
        else "the level and slope of the surrounding periods"
    )
    unit = {"MS": "month", "QS": "quarter", "W": "week", "D": "day", "YS": "year"}[f]
    events = []

    def span(i, j):
        return labels[i] if i == j else f"{labels[i]} to {labels[j]}"

    def evidence(idx):
        if not tested:
            return "Not tested (short history)"
        return "Confirmed" if any(i in esd_hits for i in idx) else "Not confirmed"

    runs = _runs(flagged, sign, valid)
    used = set()
    for r_i, (i, j) in enumerate(runs):
        if r_i in used:
            continue
        idx = list(range(i, j + 1))
        peak = max(idx, key=lambda t: abs(score[t]))
        etype = "one_off" if i == j else "temporary"
        note = ""
        # an offsetting neighbor: up then down (or the reverse) that largely nets off
        if i == j and r_i + 1 < len(runs):
            i2, j2 = runs[r_i + 1]
            if (
                i2 == j + 1
                and j2 == i2
                and sign[i2] == -sign[i]
                and abs(gap[i] + gap[i2]) <= 0.5 * max(abs(gap[i]), abs(gap[i2]))
            ):
                used.add(r_i + 1)
                idx = [i, i2]
                j = i2
                etype = "pair"
                note = f" The following {unit} is {_fmt_amt(abs(gap[i2]))} the other way, so the two largely net off (net {_fmt_amt(gap[i] + gap[i2])})."
        periods_after = last_valid - j
        if j >= last_valid and len(idx) < ma and etype != "pair":
            etype = "latest"
        elif etype != "pair" and periods_after < 1:
            etype = "latest"
        # two-year ambiguity: the only other observation at this position is flagged the other way
        if etype == "one_off" and d["seasonal"]:
            same = [
                t
                for t in range(n)
                if t != peak and d["pos"][t] == d["pos"][peak] and np.isfinite(score[t])
            ]
            if len(same) == 1 and flagged[same[0]] and sign[same[0]] == -sign[peak]:
                etype = "either_year"
        above = gap[peak] > 0
        if direction in ("above", "below") and (direction == "above") != above:
            continue
        g, gp = float(gap[peak]), float(gap_pct[peak])
        if etype == "one_off":
            why = "{} came in {} ({}) {} what the periods around it and its usual pattern suggest, and the line returned to pattern afterwards.".format(
                labels[peak],
                _fmt_amt(abs(g)),
                _fmt_pct(abs(gp)).lstrip("+"),
                "above" if above else "below",
            )
        elif etype == "pair":
            why = "{} came in {} ({}) {} expected.{}".format(
                labels[peak],
                _fmt_amt(abs(g)),
                _fmt_pct(abs(gp)).lstrip("+"),
                "above" if above else "below",
                note,
            )
        elif etype == "temporary":
            why = f"{len(idx)} {unit}s in a row ({span(i, j)}) ran {'above' if above else 'below'} expected, the largest by {_fmt_amt(abs(g))} ({_fmt_pct(abs(gp)).lstrip('+')}) in {labels[peak]}, before returning to pattern."
        elif etype == "either_year":
            why = "{} is {} ({}) {} what the same period in the other year implies. With two years of history either one could be the unusual year.".format(
                labels[peak],
                _fmt_amt(abs(g)),
                _fmt_pct(abs(gp)).lstrip("+"),
                "above" if above else "below",
            )
        else:
            many = len(idx) > 1
            why = "{} {} {} ({}) {} expected. {}".format(
                span(i, j) if many else labels[peak],
                "ran up to" if many else "came in",
                _fmt_amt(abs(g)),
                _fmt_pct(abs(gp)).lstrip("+"),
                "above" if above else "below",
                "There are not yet enough periods after it to say whether this is a one-off or a new level.",
            )
        if d["seasonal"] and etype in ("one_off", "latest", "either_year"):
            # say so when the surprise is a usual seasonal move that did not happen
            prev = peak - 1
            if (
                prev >= 0
                and np.isfinite(expected[prev])
                and np.isfinite(y[prev])
                and abs(expected[prev]) > 0
            ):
                exp_move = (
                    expected[peak] / expected[prev] - 1
                    if d["mode"] == "ratio"
                    else (expected[peak] - expected[prev])
                    / max(abs(expected[prev]), 1e-12)
                )
                act_move = (
                    y[peak] / y[prev] - 1
                    if d["mode"] == "ratio" and y[prev] > 0
                    else (y[peak] - y[prev]) / max(abs(y[prev]), 1e-12)
                )
                if abs(exp_move) >= 0.08 and abs(act_move) <= 0.35 * abs(exp_move):
                    why += " The usual {} of about {} from the prior {} did not happen.".format(
                        "rise" if exp_move > 0 else "fall",
                        _fmt_pct(abs(exp_move)).lstrip("+"),
                        unit,
                    )
        events.append(
            {
                "type": etype,
                "type_label": TYPE_LABEL[etype],
                "start": int(idx[0]),
                "end": int(idx[-1]),
                "periods": len(idx),
                "peak": int(peak),
                "period": span(idx[0], idx[-1]),
                "direction": "above" if above else "below",
                "actual": float(y[peak]),
                "expected": float(expected[peak]),
                "gap": g,
                "gap_pct": gp,
                "total_gap": float(np.nansum(gap[idx]))
                if kind == "flow" and len(idx) > 1
                else None,
                "score": float(score[peak]),
                "evidence": evidence(idx),
                "basis": basis,
                "why": why,
                "check": CHECK_HINT[etype],
                "since_end": int(last_valid - idx[-1]),
            }
        )

    shifts = d["shifts"]
    skip = set()
    overshoot = {}
    for e in list(events):
        for h in shifts:
            if (
                e["start"] == h["index"]
                and (e["gap"] > 0) == (h["size"] > 0)
                and e["type"] in ("one_off", "temporary", "latest")
            ):
                overshoot[h["index"]] = e
                events.remove(e)
                break
    for k, h in enumerate(shifts):
        if k in skip:
            continue
        c = h["index"]
        up = h["size"] > 0
        if direction in ("above", "below") and (direction == "above") != up:
            continue
        nxt = shifts[k + 1] if k + 1 < len(shifts) else None
        held = (nxt["index"] if nxt else last_valid + 1) - c
        etype, end = "new_level", (nxt["index"] - 1 if nxt is not None else last_valid)
        # the row shows the first period of the new level that has a value: what it was, what it would
        # have been at the old level, and the gap between the two
        at = next((t for t in range(c, end + 1) if valid[t]), c)
        yc = float(y[at]) if valid[at] else float("nan")
        if d["mode"] == "ratio" and np.isfinite(h["size_pct"]):
            exp_c = yc / (1.0 + h["size_pct"])
            g_c, gp_c = yc - exp_c, float(h["size_pct"])
        else:
            exp_c, g_c = yc - h["size"], float(h["size"])
            gp_c = (
                g_c / abs(exp_c)
                if np.isfinite(exp_c) and abs(exp_c) > 0.1 * d["typical"]
                else float("nan")
            )
        size_txt = (
            "{} ({})".format(_fmt_amt(abs(g_c)), _fmt_pct(abs(gp_c)).lstrip("+"))
            if np.isfinite(gp_c)
            else _fmt_amt(abs(g_c))
        )
        if (
            nxt is not None
            and nxt["size"] * h["size"] < 0
            and held <= max(2 * eng.W_AFTER[f], s)
            and abs(h["size_x"] + nxt["size_x"])
            <= 0.5 * max(abs(h["size_x"]), abs(nxt["size_x"]))
        ):
            skip.add(k + 1)
            etype, end = "temporary_level", nxt["index"] - 1
            why = f"The level ran about {size_txt} {'higher' if up else 'lower'} for {held} {unit}s ({span(c, end)}) and then returned to about where it had been."
        else:
            # has the level since drifted back to where it stood? A step that wore off gradually leaves no
            # second step to find, and calling it a level that "has held" would be wrong
            lv = d["level_x"]
            now = next((lv[t] for t in range(end, c, -1) if np.isfinite(lv[t])), np.nan)
            was = next(
                (lv[t] for t in range(c - 1, -1, -1) if np.isfinite(lv[t])), np.nan
            )
            back = (
                np.isfinite(now)
                and np.isfinite(was)
                and held >= 2 * ma
                and abs(now - was) <= 0.5 * abs(h["size_x"])
            )
            if back:
                etype = "unwound_level"
                rel = (
                    math.expm1(now - was)
                    if d["mode"] == "ratio"
                    else (
                        (now - was) / abs(was)
                        if abs(was) > 0.1 * d["typical"]
                        else float("nan")
                    )
                )
                why = "At {} the level stepped {} by about {}. It has since drifted back: by {} it stood {}.".format(
                    labels[c],
                    "up" if up else "down",
                    size_txt,
                    labels[end],
                    (
                        "{} {} where it was before the step".format(
                            _fmt_pct(abs(rel)).lstrip("+"),
                            "above" if rel > 0 else "below",
                        )
                    )
                    if np.isfinite(rel)
                    else "close to where it was before the step",
                )
            else:
                still = (
                    f"and has held for the {held} {unit}s since"
                    if nxt is None
                    else f"and held for {held} {unit}s until the next change"
                )
                why = "From {} the line has run about {} {} than its earlier level, {}. The periods after it are judged against the new level.".format(
                    labels[c], size_txt, "higher" if up else "lower", still
                )
        if c in overshoot:
            o = overshoot[c]
            why += " The first {} ran a further {} {} the new level.".format(
                unit if o["periods"] == 1 else f"{o['periods']} {unit}s",
                _fmt_pct(abs(o["gap_pct"])).lstrip("+"),
                "above" if up else "below",
            )
        events.append(
            {
                "type": etype,
                "type_label": TYPE_LABEL[etype],
                "start": int(c),
                "end": int(end),
                "periods": int(held),
                "peak": int(at),
                "period": f"{labels[c]} onward"
                if etype == "new_level" and nxt is None
                else (labels[c] if etype == "unwound_level" else span(c, end)),
                "direction": "above" if up else "below",
                "actual": yc,
                "expected": float(exp_c),
                "gap": float(g_c),
                "gap_pct": float(gp_c),
                "total_gap": _level_total(y, valid, c, end, h, d["mode"])
                if kind == "flow" and end > c
                else None,
                "score": float(h["t"]),
                "evidence": "Confirmed" if h["p"] <= 0.05 else "Not confirmed",
                "basis": "the level before {} carried forward{}".format(
                    labels[c],
                    " with the usual seasonal pattern" if d["seasonal"] else "",
                ),
                "why": why,
                "check": CHECK_HINT[etype],
                "since_end": int(last_valid - end),
            }
        )
    events.sort(key=lambda e: (-e["end"], -abs(e["gap"])))
    return events


def _level_total(y, valid, c: int, end: int, h: dict, mode: str):
    """A level change summed over the periods it held: each period against the old level carried forward."""
    idx = [t for t in range(c, end + 1) if valid[t]]
    if not idx:
        return None
    if mode == "ratio" and np.isfinite(h["size_pct"]) and h["size_pct"] > -1:
        tot = sum(float(y[t]) * h["size_pct"] / (1.0 + h["size_pct"]) for t in idx)
    else:
        tot = float(h["size"]) * len(idx)
    return float(tot) if np.isfinite(tot) else None


def data_checks(values, d: dict | None, labels: list) -> list:
    """Things that look like a problem with the data. Returns [{'check', 'period', 'index', 'detail'}].

    Run on the raw values, so it works even when the line is too short to judge statistically.
    """
    y = np.asarray(values, dtype=float)
    n = len(y)
    valid = np.isfinite(y)
    out = []
    if valid.sum() == 0:
        return out
    first, last = int(np.where(valid)[0][0]), int(np.where(valid)[0][-1])
    typical = float(np.median(np.abs(y[valid])))

    def add(check, i, detail, j=None):
        out.append(
            {
                "check": check,
                "index": int(i),
                "period": labels[i]
                if j is None or j == i
                else f"{labels[i]} to {labels[j]}",
                "detail": detail,
            }
        )

    # 1. missing periods inside the history
    gaps = [t for t in range(first, last + 1) if not valid[t]]
    for t in gaps[:12]:
        add(
            "Missing period",
            t,
            "No value for this period. It is read as missing, not as zero.",
        )
    if len(gaps) > 12:
        add(
            "Missing period",
            gaps[12],
            f"{len(gaps) - 12} more periods are missing.",
        )

    nonzero = valid & (y != 0)
    # 2. a zero where a value belongs
    if typical > 0 and nonzero.sum() >= 0.8 * valid.sum():
        for t in np.where(valid & (y == 0))[0][:12]:
            add(
                "Zero value",
                t,
                "Zero in a line that otherwise always has a value. Check whether it is a blank or a load that did not arrive.",
            )

    # 3. a flipped sign
    pos_share = float(np.mean(y[nonzero] > 0)) if nonzero.any() else 0.5
    if nonzero.sum() >= 8 and (pos_share >= 0.9 or pos_share <= 0.1):
        major = 1.0 if pos_share >= 0.9 else -1.0
        for t in np.where(
            nonzero & (np.sign(y) == -major) & (np.abs(y) >= 0.2 * typical)
        )[0][:12]:
            add(
                "Sign reversed",
                t,
                "{} in a line that is otherwise {}. Check the sign convention or a reversal booked without its original.".format(
                    "Negative" if major > 0 else "Positive",
                    "positive" if major > 0 else "negative",
                ),
            )

    # 4. a units slip: about 100x, 1,000x or 1,000,000x off what the line implies
    if d is not None and d.get("status") == "ok":
        exp = d["expected"]
        with np.errstate(divide="ignore", invalid="ignore"):
            # only where the period is flagged and expected is well away from zero: a ratio to a
            # near-zero expected value means nothing
            ratio = np.where(
                valid
                & np.isfinite(exp)
                & (np.abs(exp) > 0.1 * d["typical"])
                & (y != 0)
                & d["flagged"],
                np.abs(y) / np.abs(exp),
                np.nan,
            )
        for t in np.where(np.isfinite(ratio))[0]:
            for factor, name in ((1000.0, "1,000"), (1e6, "1,000,000"), (100.0, "100")):
                for f_, way in ((factor, "too large"), (1.0 / factor, "too small")):
                    if abs(math.log(ratio[t] / f_)) <= 0.15:
                        add(
                            "Units",
                            t,
                            f"About {name} times {way} for this line. Check the units (thousands against units, percent against decimal).",
                        )

    # 5. the same value repeated
    if valid.sum() >= 8:
        dif = np.diff(y)
        pair_ok = valid[1:] & valid[:-1]
        same = pair_ok & (dif == 0) & (y[1:] != 0)
        if pair_ok.sum() and same.sum() <= 0.2 * pair_ok.sum():
            t = 0
            while t < n - 1:
                if same[t]:
                    j = t
                    while j + 1 < n - 1 and same[j + 1]:
                        j += 1
                    run = j - t + 2  # periods sharing the value
                    if run >= 3:
                        add(
                            "Repeated value",
                            t,
                            f"The same value {run} periods running. Check whether a figure was carried forward instead of updated.",
                            j + 1,
                        )
                    elif j + 1 == last:
                        add(
                            "Repeated value",
                            last,
                            "The latest period repeats the prior period exactly. Check whether it has been updated yet.",
                        )
                    t = j + 1
                else:
                    t += 1
    return out
