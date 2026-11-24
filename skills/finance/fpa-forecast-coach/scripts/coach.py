"""
description: Forecast Coach entry point: prepare the history, forecast and backtest every method, write the coach workbook (Forecast, Methods, Bands, Backtest, Commentary, Actuals, Run_Info, and the optional sheets), and return what the agent reads out.
last_updated: 2026-11-24
origin: original

Deterministic. No LLM calls, no network. Everything a user sees in the workbook is computed by the
modules this file imports, so two runs on the same data produce the same workbook (apart from the run
id and timestamp). Import it and call build; never read the modules into the conversation.

    import coach
    res = coach.build(series={"Product A": {"dates": [...], "values": [...]}}, horizon=12,
                      freq="MS", season=12, out_path="<folder the user chose>/Forecast_Coach.xlsx",
                      method="baseline",                # or "best", a method label, or {series: label}
                      targets={"Product A": 250000})    # optional: phase a total across the horizon
    print(res["summary"])      # what to tell the user
    print(res["flags"])        # risks worth saying out loud
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os

import numpy as np
import stat_methods as sm
from backtest import all_methods, backtest_all, method_order, pick_method
from commentary import flags as build_flags
from commentary import summary as build_summary
from history_prep import prepare
from periods import fmt_period, next_periods, normalise_freq
from prior_run import load_prior
from run_context import RunContext
from sheet_actuals import write_actuals_sheet
from sheet_forecast import write_forecast_sheet
from sheet_tables import (
    end_or_total,
    write_backtest_sheet,
    write_bands_sheet,
    write_methods_sheet,
)
from sheet_text import write_commentary_sheet, write_run_info_sheet
from target_phasing import write_target_phasing
from user_forecast import user_summary, write_user_comparison
from workbook_formats import formats, open_workbook

__all__ = ["build", "prepare", "normalise_freq", "SHEETS", "METHOD_ORDER"]

METHOD_ORDER = method_order

SHEETS = [
    "Forecast",
    "Methods",
    "Bands",
    "Backtest",
    "Target_Phasing (only with targets)",
    "Your_Forecast (only with user_forecast)",
    "Commentary",
    "Actuals",
    "Run_Info",
]
_SWITCHED_LIMIT = 8


def max_horizon(season: int) -> int:
    """The longest horizon build accepts for a season length (keeps run time and the workbook bounded)."""
    return 4 * season + 60


def _stocks(stock, clean: dict) -> frozenset:
    if stock is True:
        return frozenset(clean)
    if isinstance(stock, str):
        stock = [stock]
    return frozenset(n for n in (stock or []) if n in clean)


def _same_end(clean: dict, issues: list) -> dict:
    """Keep the series whose history ends at the latest period; the forecast periods are labeled from it."""
    ends = {n: v["dates"][-1] for n, v in clean.items() if v["dates"]}
    if not ends:
        return clean
    last = max(ends.values())
    kept = {}
    for n, v in clean.items():
        if n in ends and ends[n] < last:
            issues.append(
                f"{n}: skipped; its history ends {ends[n]:%Y-%m-%d}, before the latest series ({last:%Y-%m-%d}), "
                "so its forecast periods would be labeled wrong. Forecast it in a separate run."
            )
            continue
        kept[n] = v
    return kept


def _run_id(clean: dict, horizon: int, freq: str) -> str:
    payload = json.dumps(
        {k: list(np.round(v["values"][-12:], 6)) for k, v in clean.items()}, default=str
    )
    return hashlib.sha1(
        (payload + str(horizon) + freq).encode(), usedforsecurity=False
    ).hexdigest()[:8]


def _forecast_all(clean, names, horizon, season, freq, folds):
    order = method_order(freq, season)
    fc, bt, methods, missing = {}, {}, {}, {}
    for n in names:
        v = clean[n]["values"]
        fc[n] = sm.baseline(v, horizon, freq)
        test_len = min(horizon, max(2, (len(v) - max(8, season)) // max(folds, 1)))
        bt[n] = backtest_all(v, test_len, folds, season, freq)
        alt = all_methods(v, horizon, season, freq, fc[n]["p50"])
        methods[n] = {
            m: np.asarray(alt[m], dtype=float) for m in order if alt.get(m) is not None
        }
        missing[n] = [m for m in order if alt.get(m) is None]
    return order, fc, bt, methods, missing


def _check_inputs(horizon, season: int, out_path) -> None:
    if not isinstance(horizon, (int, np.integer)) or not 1 <= horizon <= max_horizon(
        season
    ):
        raise ValueError(
            f"horizon must be an integer between 1 and {max_horizon(season)} periods"
        )
    if not out_path:
        raise ValueError(
            "out_path is required: ask the user where to save the workbook"
        )


def build(
    series: dict,
    horizon: int = 12,
    freq: str | None = None,
    season: int | None = None,
    out_path: str | None = None,
    user_forecast: dict | None = None,
    prior_path: str | None = None,
    units: str = "",
    title: str = "Forecast Coach",
    backtest_folds: int = 2,
    source_file: str | None = None,
    method="baseline",
    targets: dict | None = None,
    stock=None,
    date_order: str | None = None,
) -> dict:
    """Forecast every series, backtest, and write the coach workbook. Returns a dict for the agent to read out.

    out_path     where to write the workbook (required; ask the user).
    method       which method each series starts on in the workbook's Method picker: "baseline" (default),
                 "best" (the backtest winner per series), a method label such as "T12M run-rate", or
                 {series: label}. The user can change it in Excel afterward; Final recalculates.
    targets      {series: total} or {series: {"total": x, "periods": n, "start": "2027-01"}}: a number to hit
                 across n forecast periods starting at `start` (a period label or date, or an offset; default:
                 the first forecast period). Raise `horizon` so it reaches the end of the window. Adds a
                 Target_Phasing sheet that spreads it by historical period-of-year shares, next to plain
                 proportional scaling of the baseline.
    stock        series that are balances (inventory, headcount, cash): True for all, a name, or a list of
                 names. Their summaries read the end-of-horizon value instead of summing periods.
    date_order   'MDY' or 'DMY' after the user confirms; otherwise only dates that can be read one way are used.
    """
    prep = prepare(series, freq, season, date_order)
    freq, season = prep["freq"], prep["season"]
    clean = _same_end(prep["series"], prep["issues"])
    _check_inputs(horizon, season, out_path)
    if not clean:
        raise ValueError("no usable series: " + "; ".join(prep["issues"]))
    run_id = _run_id(clean, horizon, freq)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    names = list(clean)
    stocks = _stocks(stock, clean)
    last_date = max(
        (v["dates"][-1] for v in clean.values() if v["dates"]), default=_dt.date.today()
    )
    labels = [fmt_period(d, freq) for d in next_periods(last_date, horizon, freq)]
    order, fc, bt, methods, missing = _forecast_all(
        clean, names, horizon, season, freq, backtest_folds
    )
    default = {
        n: pick_method(
            method, n, list(methods[n]), bt[n].get("average", {}).get("best_method")
        )
        for n in names
    }
    ctx = RunContext(
        names,
        clean,
        fc,
        bt,
        methods,
        missing,
        default,
        stocks,
        labels,
        horizon,
        freq,
        season,
        units,
        title,
        run_id,
    )

    prior, comparison_issues = None, []
    if prior_path:
        try:
            prior = load_prior(prior_path)
        except (OSError, ValueError) as err:
            comparison_issues.append(
                f"Prior comparison failed, so no comparison was made: {err}"
            )

    wb = open_workbook(out_path)
    F = formats(wb)
    movers, issues = write_forecast_sheet(wb, F, ctx, prior)
    comparison_issues += issues
    write_methods_sheet(wb, F, ctx)
    write_bands_sheet(wb, F, ctx)
    beat, cover = write_backtest_sheet(wb, F, ctx, order)
    phased = (
        write_target_phasing(
            wb, F, names, clean, fc, targets, labels, horizon, season, units, date_order
        )
        if targets
        else []
    )
    gaps = (
        write_user_comparison(wb, F, names, fc, user_forecast, labels, horizon, units)
        if user_forecast
        else []
    )

    flags = build_flags(clean, bt, season, prep["issues"], cover) + comparison_issues
    summary = build_summary(names, fc, bt, labels, units, beat, cover, movers, stocks)
    summary += _baseline_lines(ctx)
    if phased:
        summary += [p["line"] for p in phased]
        flags += [p["flag"] for p in phased if p.get("flag")]
    if gaps:
        summary += user_summary(gaps, units)
        flags += [g["flag"] for g in gaps if g.get("flag")]
    write_commentary_sheet(wb, F, summary, flags)
    write_actuals_sheet(wb, F, ctx)
    write_run_info_sheet(wb, F, ctx, source_file, prior_path)
    wb.close()
    return _result(ctx, out_path, summary, flags, phased, gaps, prep["issues"])


def _baseline_lines(ctx: RunContext) -> list:
    lines = []
    other = [n for n in ctx.names if ctx.fc[n]["method"] != sm.ETS_THETA_NAME]
    if other:
        lines.append(
            "Baseline method by series where it is not the ETS-Theta average: "
            + ", ".join(f"{n} ({ctx.fc[n]['method']})" for n in other[:_SWITCHED_LIMIT])
            + ("" if len(other) <= _SWITCHED_LIMIT else " and others")
            + "."
        )
    switched = [n for n in ctx.names if ctx.default[n] != sm.BASELINE_LABEL]
    if switched:
        lines.append(
            "Final starts on a method other than the baseline for: "
            + ", ".join(f"{n} ({ctx.default[n]})" for n in switched[:_SWITCHED_LIMIT])
            + ("" if len(switched) <= _SWITCHED_LIMIT else " and others")
            + ". Change it in the Method column of the Forecast sheet."
        )
    return lines


def _result(ctx: RunContext, out_path, summary, flags, phased, gaps, issues) -> dict:
    return {
        "path": out_path,
        "run_id": ctx.run_id,
        "series": ctx.names,
        "horizon": ctx.horizon,
        "freq": ctx.freq,
        "season": ctx.season,
        "periods": ctx.labels,
        "summary": summary,
        "flags": flags,
        "vs_user": [
            {k: v for k, v in g.items() if k not in ("outside", "flag")} for g in gaps
        ],
        "forecast": {
            n: {
                "baseline_method": ctx.fc[n]["method"],
                "p10": ctx.fc[n]["p10"].tolist(),
                "p50": ctx.fc[n]["p50"].tolist(),
                "p90": ctx.fc[n]["p90"].tolist(),
            }
            for n in ctx.names
        },
        "backtest": {n: ctx.bt[n].get("average", {}) for n in ctx.names},
        "methods": {
            n: {
                "baseline_method": ctx.fc[n]["method"],
                "is_stock": n in ctx.stocks,
                "selected": ctx.default[n],
                "available": list(ctx.methods[n]),
                "not_available": ctx.missing[n],
                "best_in_backtest": ctx.bt[n].get("average", {}).get("best_method"),
                # a balance is read at the end of the horizon, a flow is summed over it (Rule 5)
                "totals": {
                    m: end_or_total(v, n in ctx.stocks)
                    for m, v in ctx.methods[n].items()
                },
            }
            for n in ctx.names
        },
        "final": {n: ctx.methods[n][ctx.default[n]].tolist() for n in ctx.names},
        "targets": [
            {k: v for k, v in p.items() if k not in ("line", "flag")} for p in phased
        ],
        "issues": issues,
        "sheets": SHEETS,
    }
