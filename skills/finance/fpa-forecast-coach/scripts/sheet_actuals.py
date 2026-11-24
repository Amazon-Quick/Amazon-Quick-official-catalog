"""
description: The Actuals sheet: the input history by period, with a line chart per series (actual, P50, and dashed P10/P90) for up to eight series.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import math

from periods import fmt_period
from run_context import RunContext
from workbook_formats import defang

MAX_CHARTS = 8


def _write_history(ws, F, ctx: RunContext) -> int:
    """Write the history columns; return the number of history rows."""
    all_dates = sorted(
        {d for v in ctx.clean.values() if v["dates"] for d in v["dates"]}
    )
    if not all_dates:
        for c, n in enumerate(ctx.names, start=1):
            for i, val in enumerate(ctx.clean[n]["values"]):
                if not math.isnan(val):
                    ws.write_number(i + 1, c, float(val), F["num"])
        return max(len(v["values"]) for v in ctx.clean.values())
    pos = {d: i for i, d in enumerate(all_dates)}
    for i, d in enumerate(all_dates):
        ws.write_string(i + 1, 0, fmt_period(d, ctx.freq))
    for c, n in enumerate(ctx.names, start=1):
        v, ds = ctx.clean[n]["values"], ctx.clean[n]["dates"]
        if not ds:
            continue
        for val, d in zip(v, ds, strict=True):
            if not math.isnan(val):
                ws.write_number(pos[d] + 1, c, float(val), F["num"])
    return len(all_dates)


def _chart(wb, k: int, n: str, n_act: int, horizon: int):
    ch = wb.add_chart({"type": "line"})
    ch.add_series(
        {
            "name": "Actual",
            "categories": ["Actuals", 1, 0, n_act, 0],
            "values": ["Actuals", 1, k + 1, n_act, k + 1],
            "line": {"color": "#404040", "width": 1.75},
        }
    )
    base = 1 + k * horizon
    for name, col, line in (
        ("P50", 3, {"color": "#1F77B4", "width": 1.75}),
        ("P10", 2, {"color": "#9DC3E6", "dash_type": "dash"}),
        ("P90", 4, {"color": "#9DC3E6", "dash_type": "dash"}),
    ):
        ch.add_series(
            {
                "name": name,
                "categories": ["Bands", base, 1, base + horizon - 1, 1],
                "values": ["Bands", base, col, base + horizon - 1, col],
                "line": line,
            }
        )
    ch.set_title({"name": defang(f"{n}: actuals and forecast")})
    ch.set_legend({"position": "bottom"})
    ch.set_size({"width": 760, "height": 320})
    return ch


def write_actuals_sheet(wb, F, ctx: RunContext) -> None:
    """The input history and one chart per series (first MAX_CHARTS series)."""
    ws = wb.add_worksheet("Actuals")
    ws.write_string(0, 0, "Period", F["h"])
    for c, n in enumerate(ctx.names, start=1):
        ws.write_string(0, c, defang(n), F["h"])
    ws.set_column(0, len(ctx.names), 14)
    n_act = _write_history(ws, F, ctx)
    for k, n in enumerate(ctx.names[:MAX_CHARTS]):
        ws.insert_chart(
            2 + k * 17, len(ctx.names) + 2, _chart(wb, k, n, n_act, ctx.horizon)
        )
