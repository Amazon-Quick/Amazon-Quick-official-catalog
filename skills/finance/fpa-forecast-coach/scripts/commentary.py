"""
description: The Forecast Coach's words: the flags (risks to read before using the numbers) and the summary lines (what the run says), built from the forecasts, the backtest, and the prior-run comparison.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import math

import finance_methods as fm
import numpy as np

HIGH_COVERAGE = 0.90
LOW_COVERAGE = 0.60
MATERIAL_MOVE = 0.001
_LIST_LIMIT = 6


def _coverage_flag(cover: list) -> str | None:
    c = float(np.mean(cover))
    if c > HIGH_COVERAGE:
        return (
            f"Band coverage in backtest is {c * 100:.0f}% against the 80% the band claims, so the P10 to P90 "
            "range is wider than it needs to be and is not a usable planning range. The baseline hedges "
            "when history is short; treat P50 as a midpoint and set your own range in the overlay columns."
        )
    if c < LOW_COVERAGE:
        return (
            f"Band coverage is only {c * 100:.0f}% against the 80% the band claims: actuals fall outside "
            "it more often than they should, so the range understates risk."
        )
    return None


def _lost_flags(bt: dict) -> list:
    lost = [
        (n, b["average"])
        for n, b in bt.items()
        if b.get("average") and b["average"]["best_method"] != fm.MODEL_LABEL
    ]
    scored = [n for n, b in bt.items() if b.get("average")]
    out = []
    if scored and len(lost) == len(scored):
        k = max(len(bt[n]["folds"]) for n in scored)
        out.append(
            f"The baseline was not the most accurate method on any series in backtest ({k} held-out "
            f"window{'s' if k != 1 else ''} per series). On that evidence it adds no accuracy over simple "
            "finance methods here; use it as a cross-check rather than as the main forecast."
        )
    if lost:
        out.append(
            "A simpler method beat the baseline in backtest, by weighted absolute percentage error (WAPE), on: "
            + "; ".join(
                f"{n} ({a['best_method']}, {a['methods'][a['best_method']] * 100:.1f}% WAPE against "
                f"{a['model_wape'] * 100:.1f}% for the baseline)"
                for n, a in lost[:_LIST_LIMIT]
            )
            + (
                f"; and {len(lost) - _LIST_LIMIT} more (see Backtest)"
                if len(lost) > _LIST_LIMIT
                else ""
            )
            + ". Pick that method in the Method column if you trust the recent pattern more than the baseline."
        )
    return out


def flags(clean: dict, bt: dict, season: int, issues: list, cover: list) -> list:
    """Risks worth saying out loud, issues from prepare first."""
    out = list(issues)
    if cover:
        c = _coverage_flag(cover)
        if c:
            out.append(c)
    out += _lost_flags(bt)
    short = [n for n, v in clean.items() if len(v["values"]) < 3 * season]
    if short:
        out.append(
            f"Under 3 full cycles of history on {len(short)} series ({', '.join(short[:4])}"
            f"{' and others' if len(short) > 4 else ''}): seasonal peaks come out flattened, so P90 is the "
            "better guide for a peak period than P50."
        )
    out.append(
        "History only: the baseline is fitted to your history alone and uses no drivers, price, promotions, "
        "or plan scenarios. Anything you know about the future that is not in the history has to come in "
        "through the overlay columns."
    )
    return out


def _size(fc: dict, n: str, stocks) -> float:
    """A balance is read at the end of the horizon; a flow is summed over it."""
    return float(fc[n]["p50"][-1]) if n in stocks else float(np.sum(fc[n]["p50"]))


def _head(names, fc, labels, u, stocks) -> str:
    flows = [n for n in names if n not in stocks]
    head = f"{len(names)} series forecast over {len(labels)} periods ({labels[0]} to {labels[-1]})."
    if flows:
        tot = float(sum(np.sum(fc[n]["p50"]) for n in flows))
        head += (
            f" Summed over the horizon, the {len(flows)} flow series add to {tot:,.1f}{u}"
            ". This total double-counts any series that includes another."
        )
    if stocks:
        noun = (
            "series is a balance, so it is"
            if len(stocks) == 1
            else "series are balances, so they are"
        )
        head += (
            f" {len(stocks)} {noun} read at {labels[-1]}, never summed across periods."
        )
    return head


def _growth_line(names, fc) -> str | None:
    grow = []
    for n in names:
        p = fc[n]["p50"]
        early = float(np.mean(p[: max(1, len(p) // 3)]))
        late = float(np.mean(p[-max(1, len(p) // 3) :]))
        g = (late / early - 1 if early else float("nan")) if len(p) >= 3 else 0.0
        if math.isfinite(g):
            grow.append((g, n))
    if not grow:
        return None
    grow.sort(reverse=True)
    return (
        f"Implied change from the first third of the horizon to the last: strongest {grow[0][1]} "
        f"{grow[0][0] * 100:+.1f}%, weakest {grow[-1][1]} {grow[-1][0] * 100:+.1f}%."
    )


def _backtest_line(names, bt, beat, cover) -> str:
    if not beat:
        return "Backtest: not enough history to hold out a window, so there is no accuracy evidence on this run."
    wins: dict = {}
    for n in names:
        a = bt[n].get("average")
        if a:
            wins[a["best_method"]] = wins.get(a["best_method"], 0) + 1
    board = ", ".join(
        f"{m} on {k} series" for m, k in sorted(wins.items(), key=lambda kv: -kv[1])
    )
    return (
        f"Most accurate method in backtest: {board} ({len(beat)} series scored). The baseline beat seasonal "
        f"naive on {sum(beat)} of {len(beat)}; average band coverage {float(np.mean(cover)) * 100:.0f}% "
        "against the 80% the band claims."
    )


def _movers_line(movers: list, u: str) -> str:
    movers = sorted(movers, reverse=True)
    material = [
        m
        for m in movers
        if abs(m[3]) >= MATERIAL_MOVE or (not math.isfinite(m[3]) and m[2] != 0)
    ]
    if not material:
        return (
            "No series moved by more than 0.1% against the prior run over the compared windows: "
            + "; ".join(f"{n}: {window}" for _, n, _, _, window in movers)
            + "."
        )
    return (
        "Biggest moves against the prior run (ranked by absolute change): "
        + ", ".join(
            f"{n} {d:+,.1f}{u} "
            + (
                f"({p * 100:+.1f}%, {window})"
                if math.isfinite(p)
                else f"(prior zero, percentage unavailable, {window})"
            )
            for _, n, d, p, window in material[:5]
        )
        + "."
    )


def summary(names, fc, bt, labels, units, beat, cover, movers, stocks=()) -> list:
    """What the run says, in the order the chat answer should read it."""
    u = f" {units}" if units else ""
    lines = [_head(names, fc, labels, u, stocks)]
    rank = sorted(names, key=lambda n: -abs(_size(fc, n, stocks)))
    lines.append(
        "Largest series: "
        + ", ".join(
            f"{n} {_size(fc, n, stocks):,.1f}{u}"
            + (f" at {labels[-1]}" if n in stocks else " total")
            for n in rank[:5]
        )
        + "."
    )
    growth = _growth_line(names, fc)
    if growth:
        lines.append(growth)
    lines.append(_backtest_line(names, bt, beat, cover))
    if movers:
        lines.append(_movers_line(movers, u))
    return lines
