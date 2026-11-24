"""
description: The Methods, Bands, and Backtest sheets: every method side by side with its backtest WAPE, the baseline's P10/P50/P90 by period, and the per-series backtest scoreboard with the baseline method, bias, and band coverage.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import math

import numpy as np
from run_context import RunContext
from sheet_forecast import P0, method_rows
from workbook_formats import defang


def end_or_total(values, is_stock: bool) -> float:
    """A balance's value at the end of the horizon, or a flow's sum over it."""
    v = np.asarray(values, dtype=float)
    return float(v[-1]) if is_stock else float(np.sum(v))


def write_methods_sheet(wb, F, ctx: RunContext) -> None:
    """Every method with enough history for each series, period by period, with its backtest WAPE."""
    ws = wb.add_worksheet("Methods")
    h = ctx.horizon
    ws.set_column(0, 0, 26)
    ws.set_column(1, 1, 20)
    ws.set_column(2, P0 + h, 12)
    ws.set_column(P0 + h + 1, P0 + h + 1, 60)
    total = "Total (balances: end of horizon)" if ctx.stocks else "Total"
    for c, head in enumerate(
        ["Series", "Method", "Backtest WAPE", "Best in backtest", total] + ctx.labels
    ):
        ws.write_string(0, c, head, F["h"])
    ws.write_string(0, P0 + h + 1, "Methods without enough history", F["h"])
    ws.freeze_panes(1, 2)
    rows = method_rows(ctx)
    for n in ctx.names:
        s0, _ = rows[n]
        avg = ctx.bt[n].get("average", {})
        for k, (m, vals) in enumerate(ctx.methods[n].items()):
            row = s0 + k
            best = avg.get("best_method") == m
            ws.write_string(row, 0, defang(n), F["lbl"] if k == 0 else None)
            ws.write_string(row, 1, m, F["lbl"] if best else None)
            w = avg.get("methods", {}).get(m)
            if w is not None and not math.isnan(w):
                ws.write_number(row, 2, float(w), F["pctb"] if best else F["pct"])
            ws.write_string(row, 3, "best" if best else "")
            ws.write_number(row, 4, end_or_total(vals, n in ctx.stocks), F["numb"])
            for i in range(h):
                ws.write_number(row, P0 + i, float(vals[i]), F["num"])
        if ctx.missing[n]:
            ws.write_string(s0, P0 + h + 1, defang(", ".join(ctx.missing[n])))


def write_bands_sheet(wb, F, ctx: RunContext) -> None:
    """P10 / P50 / P90 for the baseline, one row per series per period."""
    ws = wb.add_worksheet("Bands")
    for c, head in enumerate(
        ["Series", "Period", "P10", "P50", "P90", "Band % of P50"]
    ):
        ws.write_string(0, c, head, F["h"])
    ws.set_column(0, 1, 22)
    ws.set_column(2, 5, 13)
    ws.freeze_panes(1, 0)
    rb = 1
    for n in ctx.names:
        q = ctx.fc[n]
        for i in range(ctx.horizon):
            ws.write_string(rb, 0, defang(n))
            ws.write_string(rb, 1, ctx.labels[i])
            ws.write_number(rb, 2, float(q["p10"][i]), F["num"])
            ws.write_number(rb, 3, float(q["p50"][i]), F["num"])
            ws.write_number(rb, 4, float(q["p90"][i]), F["num"])
            ws.write(
                rb,
                5,
                (q["p90"][i] - q["p10"][i]) / q["p50"][i] if q["p50"][i] else "",
                F["pct"],
            )
            rb += 1


def write_backtest_sheet(wb, F, ctx: RunContext, order: list) -> tuple[list, list]:
    """Per-series backtest scoreboard; returns (beats seasonal naive per series, coverage per series)."""
    ws = wb.add_worksheet("Backtest")
    cols = (
        ["Series", "Folds", "Best method", "Baseline method"]
        + [m + " WAPE" for m in order]
        + ["Baseline bias", "Band coverage", "Baseline beats seasonal naive?"]
    )
    for c, head in enumerate(cols):
        ws.write_string(0, c, head, F["h"])
    ws.set_column(0, 0, 26)
    ws.set_column(1, 1, 7)
    ws.set_column(2, 3, 20)
    ws.set_column(4, len(cols) - 1, 14)
    ws.set_row(0, 32)
    ws.freeze_panes(1, 1)
    first = 4
    beat, cover = [], []
    for row, n in enumerate(ctx.names, start=1):
        b = ctx.bt[n]
        ws.write_string(row, 0, defang(n))
        ws.write_string(row, 3, ctx.fc[n]["method"])
        if not b.get("folds"):
            ws.write_number(row, 1, 0)
            ws.write_string(row, 2, "history too short to backtest")
            continue
        a = b["average"]
        beat.append(bool(a["beats_seasonal_naive"]))
        cover.append(a["coverage_p10_p90"])
        ws.write_number(row, 1, len(b["folds"]))
        ws.write_string(row, 2, a["best_method"], F["lbl"])
        for j, m in enumerate(order):
            w = a["methods"].get(m)
            if w is not None and not math.isnan(w):
                ws.write_number(
                    row,
                    first + j,
                    float(w),
                    F["pctb"] if m == a["best_method"] else F["pct"],
                )
        ws.write_number(row, first + len(order), float(a["model_bias"]), F["pct"])
        ws.write_number(
            row, first + len(order) + 1, float(a["coverage_p10_p90"]), F["pct"]
        )
        ws.write_string(
            row, first + len(order) + 2, "yes" if a["beats_seasonal_naive"] else "no"
        )
    return beat, cover
