"""
description: Write the summary sentences and caveats the agent reports from a review result.
last_updated: 2026-11-24
"""

from __future__ import annotations

import numpy as np


def _fmt(v: float) -> str:
    if v is None or not np.isfinite(v):
        return "n/a"
    a = abs(v)
    return f"{v:,.0f}" if a >= 100 else f"{v:,.1f}" if a >= 1 else f"{v:,.3f}"


def _pct(v, signed=True) -> str:
    if v is None or not np.isfinite(v):
        return "n/a"
    big = abs(v) >= 0.095
    return (
        ("%+.0f%%" if signed else "%.0f%%")
        if big
        else ("%+.1f%%" if signed else "%.1f%%")
    ) % (100 * v)


def _headline_events(res: dict) -> list:
    ev = [e for e in res["events"] if e["material"]]
    n = res["settings"]["focus_last"]
    if n:
        ev = [e for e in ev if e["since_end"] < int(n)]
    return ev


def _summary(res: dict) -> list:
    """Sentences the agent can say, most important first. Numbers only; no causes."""
    s, st_, labels = [], res["settings"], res["labels"]
    n_lines = len(res["lines"])
    span = f"{labels[0]} to {labels[-1]}" if labels else ""
    short_note = f"; {len(res['short'])} too short to judge" if res["short"] else ""
    s.append(
        f"Read {n_lines} line{'' if n_lines == 1 else 's'} of {st_['grain_word']} "
        f"history, {span} ({len(labels)} periods){short_note}."
    )
    if "anomaly" in st_["analyses"]:
        head = _headline_events(res)
        mat = [e for e in res["events"] if e["material"]]
        below = len(res["events"]) - len(mat)
        thr = "{}{}".format(
            _pct(st_["min_gap_pct"], signed=False),
            (
                " {} {}".format(
                    "and" if st_["threshold_rule"] == "both" else "or",
                    _fmt(st_["min_gap_amount"]),
                )
            )
            if st_["min_gap_amount"]
            else "",
        )
        if not res["events"]:
            s.append(
                "Anomaly detection: no period stands out from its line's own pattern at this sensitivity."
            )
        else:
            n_mat_lines = len({e["line"] for e in mat})
            below_note = (
                f"; {below} more {'is' if below == 1 else 'are'} unusual for "
                f"{'its line' if below == 1 else 'their line'} but below it"
                if below
                else ""
            )
            focus_note = (
                f"; {len(head)} of them in the latest period"
                if st_["focus_last"] and int(st_["focus_last"]) == 1
                else f"; {len(head)} of them in the last {st_['focus_last']} periods"
                if st_["focus_last"]
                else ""
            )
            s.append(
                f"Anomaly detection: {len(mat)} event{'' if len(mat) == 1 else 's'} on "
                f"{n_mat_lines} line{'' if n_mat_lines == 1 else 's'} at or above the "
                f"threshold ({thr}){below_note}{focus_note}."
            )
            for e in head[:5]:
                s.append(
                    "  {}, {}: {}. {}".format(
                        e["line"], e["period"], e["type_label"], e["why"]
                    )
                )
            big_below = [e for e in res["events"] if not e["material"]]
            if big_below and (not mat or abs(big_below[0]["gap"]) > abs(mat[0]["gap"])):
                e = big_below[0]
                s.append(
                    "  Largest by amount but below the percentage threshold: {}, {} ({}, {}).".format(
                        e["line"], e["period"], _fmt(e["gap"]), _pct(e["gap_pct"])
                    )
                )
        if res["data_checks"]:
            kinds = {}
            for c in res["data_checks"]:
                kinds[c["check"]] = kinds.get(c["check"], 0) + 1
            s.append(
                "Data checks: {}.".format(
                    ", ".join(f"{v} {k.lower()}" for k, v in kinds.items())
                )
            )
    if "trend" in st_["analyses"]:
        ok = [
            t
            for t in res["trends"]
            if t.get("direction") and t["direction"] != "Not enough history"
        ]
        cnt = {
            k: sum(1 for t in ok if t["direction"] == k)
            for k in ("Rising", "Flat", "Falling")
        }
        history_note = (
            f" of {len(ok)} lines with enough history" if len(ok) != n_lines else ""
        )
        s.append(
            f"Trend analysis: {cnt['Rising']} rising, {cnt['Flat']} flat, "
            f"{cnt['Falling']} falling{history_note}."
        )
        movers = sorted(
            [t for t in ok if t.get("ltm_change") is not None],
            key=lambda t: -abs(t["ltm_change"]),
        )
        for t in (movers or ok)[:5]:
            s.append("  " + t["read"])
    return s


def _caveats(res: dict) -> list:
    c, st_ = list(res["issues"]), res["settings"]
    lines = res["lines"]
    not_seasonal = [
        n
        for n, r in lines.items()
        if r["d"]["status"] == "ok"
        and r["d"]["season"] > 1
        and r["d"]["n"] < 2 * r["d"]["season"]
    ]
    if not_seasonal:
        c.append(
            f"{len(not_seasonal)} line{' has' if len(not_seasonal) == 1 else 's have'} under two years of history, so a regular seasonal peak cannot be told from an unusual period: {', '.join(not_seasonal[:5]) + (' ...' if len(not_seasonal) > 5 else '')}."
        )
    if any(e["type"] == "either_year" for e in res["events"]):
        c.append(
            "Some flags rest on two years of history: the same period in the two years disagree and either could be the unusual one."
        )
    if any(e["type"] == "latest" for e in res["events"]):
        c.append(
            "Flags in the latest period cannot yet be called a one-off or a new level; that takes a few more periods."
        )
    if "anomaly" in st_["analyses"]:
        c.append(
            "Expected values come from each line's own history only. The analysis says what is unusual and what kind of "
            "event it looks like; it does not know why, and it has not seen a budget, a forecast, or any drivers."
        )
        if st_["min_gap_pct"] == 0.10 and st_["min_gap_amount"] == 0:
            c.append(
                "The 10% materiality threshold is a default, with no amount test. Give your own (for example 5% and 50,000) to apply it."
            )
    if st_["freq"] in ("D", "W"):
        c.append(
            "No adjustment is made for public holidays or events that move between weeks; those will read as unusual periods."
        )
    elif st_["freq"] == "MS":
        c.append(
            "No adjustment is made for the number of working days in a month or for 4-4-5 style calendars beyond what repeats every year."
        )
    units = {r["d"].get("mode") for r in lines.values() if r["d"]["status"] == "ok"}
    if "amount" in units:
        c.append(
            "Lines with zeros or negative values are analyzed in their own units, so their gaps are amounts; percentages are shown only where they mean something."
        )
    return c
