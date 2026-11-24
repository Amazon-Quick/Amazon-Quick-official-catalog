"""
description: The Forecast sheet: baseline P50 per series with an explanatory comment in every cell, the Method picker and overlay inputs, the comparison with a prior run on shared periods, and the formula-driven Final block with a flows-only Total row.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import numpy as np
import xlsxwriter
from cell_notes import explain
from run_context import RunContext
from workbook_formats import defang

P0 = 5  # first period column on the Forecast and Methods sheets
_cell = xlsxwriter.utility.xl_rowcol_to_cell


def method_rows(ctx: RunContext) -> dict:
    """{series: (first row, last row)} of each series' block on the Methods sheet."""
    rows, r = {}, 1
    for n in ctx.names:
        rows[n] = (r, r + len(ctx.methods[n]) - 1)
        r += len(ctx.methods[n]) + 1
    return rows


def _prior_cells(
    ws, F, ctx: RunContext, r: int, n: str, prior: dict, issues: list, movers: list
):
    q = ctx.fc[n]
    shared = [i for i, label in enumerate(ctx.labels) if label in prior[n]]
    if not shared:
        issues.append(f"{n}: prior comparison skipped; no shared forecast periods.")
        return
    if n in ctx.stocks:
        shared = shared[-1:]
        window = f"balance at {ctx.labels[shared[0]]}"
    else:
        window = f"over {len(shared)} shared periods, {ctx.labels[shared[0]]} to {ctx.labels[shared[-1]]}"
    tot = float(np.sum(q["p50"][shared]))
    ptot = float(sum(prior[n][ctx.labels[i]] for i in shared))
    h = ctx.horizon
    ws.write_number(r, P0 + h, ptot, F["num"])
    ws.write_number(r, P0 + h + 1, tot - ptot, F["num"])
    ws.write(r, P0 + h + 2, (tot - ptot) / ptot if ptot else "", F["pct"])
    ws.write_string(r, P0 + h + 3, window)
    movers.append(
        (
            abs(tot - ptot),
            n,
            tot - ptot,
            (tot - ptot) / ptot if ptot else float("nan"),
            window,
        )
    )


def _input_row(ws, F, ctx: RunContext, r: int, n: str) -> None:
    hist = ctx.clean[n]["values"]
    q = ctx.fc[n]
    ws.write_string(r, 0, defang(n), F["lbl"])
    ws.write_string(r, 1, ctx.default[n], F["txt_in"])
    ws.data_validation(
        r,
        1,
        r,
        1,
        {
            "validate": "list",
            "source": list(ctx.methods[n]),
            "error_title": "Pick a method from the list",
            "error_message": "Only methods with enough history are offered for this series.",
        },
    )
    ws.write_number(r, 2, 0.0, F["pct_in"])
    ws.write_number(r, 3, 0.0, F["abs_in"])
    ws.write_number(r, 4, float(hist[~np.isnan(hist)][-1]), F["num"])
    for i in range(ctx.horizon):
        ws.write_number(r, P0 + i, float(q["p50"][i]), F["num"])
        note = explain(
            n,
            i,
            ctx.labels[i],
            q["p10"][i],
            q["p50"][i],
            q["p90"][i],
            hist,
            ctx.clean[n]["dates"],
            ctx.freq,
            ctx.season,
        )
        ws.write_comment(
            r, P0 + i, f"Baseline: {q['method']}\n{note}", {"width": 320, "height": 200}
        )


def _final_block(ws, F, ctx: RunContext, r: int, mrows: dict) -> None:
    ws.write_string(
        r + 1, 0, "Final = selected Method x (1 + Overlay %) + Overlay abs", F["title"]
    )
    for c, h in enumerate(["Series", "Method in use"] + ctx.labels):
        ws.write_string(r + 2, c if c < 2 else c + P0 - 2, h, F["h"])
    col_tot = np.zeros(ctx.horizon)
    for k, n in enumerate(ctx.names):
        rr, src = r + 3 + k, 4 + k
        s0, s1 = mrows[n]
        ws.write_string(rr, 0, defang(n), F["lbl"])
        ws.write_formula(
            rr,
            1,
            "=" + _cell(src, 1, row_abs=True, col_abs=True),
            F["lbl"],
            ctx.default[n],
        )
        picked = ctx.methods[n][ctx.default[n]]
        names_rng = f"Methods!{_cell(s0, 1, True, True)}:{_cell(s1, 1, True, True)}"
        pick, pct, ab = (_cell(src, c, row_abs=True, col_abs=True) for c in (1, 2, 3))
        for i in range(ctx.horizon):
            col = P0 + i
            rng = f"Methods!{_cell(s0, col, True, True)}:{_cell(s1, col, True, True)}"
            ws.write_formula(
                rr,
                col,
                f"=INDEX({rng},MATCH({pick},{names_rng},0))*(1+{pct})+{ab}",
                F["fin"],
                float(picked[i]),
            )
            if n not in ctx.stocks:
                col_tot[i] += float(picked[i])
    total_row = r + 3 + len(ctx.names)
    flow_rows = [r + 3 + k for k, n in enumerate(ctx.names) if n not in ctx.stocks]
    if not flow_rows:
        ws.write_string(
            total_row,
            0,
            "No Total row: every series is a balance, and balances are not summed.",
            F["lbl"],
        )
        return
    ws.write_string(
        total_row,
        0,
        "Total (flows only; balances are not summed)" if ctx.stocks else "Total",
        F["lbl"],
    )
    for i in range(ctx.horizon):
        refs = ",".join(_cell(rr, P0 + i) for rr in flow_rows)
        ws.write_formula(
            total_row, P0 + i, f"=SUM({refs})", F["numb"], float(col_tot[i])
        )


def write_forecast_sheet(
    wb, F, ctx: RunContext, prior: dict | None
) -> tuple[list, list]:
    """Write the Forecast sheet; return (movers against the prior run, comparison issues)."""
    ws = wb.add_worksheet("Forecast")
    ws.set_column(0, 0, 26)
    ws.set_column(1, 1, 20)
    ws.set_column(2, 4, 12)
    ws.set_column(P0, P0 + ctx.horizon + 3, 12)
    units = f" ({ctx.units})" if ctx.units else ""
    ws.write_string(
        0, 0, defang(f"{ctx.title}: baseline P50 and Method picker{units}"), F["title"]
    )
    ws.write_string(
        1,
        0,
        f"Run {ctx.run_id}. Edit the yellow cells (Method, Overlay %, Overlay abs); the green Final block "
        "recalculates. Each cell comment names the baseline method used for that series.",
        F["lbl"],
    )
    hdr = ["Series", "Method", "Overlay %", "Overlay abs", "Last actual"] + ctx.labels
    if prior:
        hdr += [
            "Prior P50 (shared window)",
            "Delta against prior",
            "Delta %",
            "Comparison window",
        ]
    for c, h in enumerate(hdr):
        ws.write_string(3, c, h, F["h"])
    ws.freeze_panes(4, 1)
    r, movers, issues = 4, [], []
    for n in ctx.names:
        _input_row(ws, F, ctx, r, n)
        if prior and n in prior:
            _prior_cells(ws, F, ctx, r, n, prior, issues, movers)
        elif prior:
            issues.append(
                f"{n}: prior comparison skipped; series absent from prior Bands."
            )
        r += 1
    _final_block(ws, F, ctx, r, method_rows(ctx))
    return movers, issues
