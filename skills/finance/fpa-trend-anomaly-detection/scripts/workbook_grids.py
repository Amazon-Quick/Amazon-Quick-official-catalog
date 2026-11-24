"""
description: Writes the Data, Expected and Scores sheets: one row per line, one column per period.
last_updated: 2026-11-24
"""

from __future__ import annotations

from workbook_context import WorkbookContext, _cell, _num


def _grid(ctx: WorkbookContext, ws, title, note, getter, fmt):
    """Write one line-by-period grid sheet."""
    res = ctx.res
    labels = ctx.labels
    lines = ctx.lines
    names = ctx.names
    F = ctx.F
    R0 = ctx.R0
    C0 = ctx.C0
    row_of = ctx.row_of

    ws.write_string(0, 0, title, F["title"])
    ws.write_string(1, 0, note, F["sub"])
    ws.write_row(R0, 0, ["Line", "Type", "Read from"], F["h"])
    for t, lab in enumerate(labels):
        ws.write_string(R0, C0 + t, lab, F["h"])
    for n in names:
        r = row_of[n]
        ws.write_string(r, 0, n, F["b"])
        ws.write_string(
            r,
            1,
            {"flow": "Amount for the period", "balance": "Balance", "rate": "Rate"}[
                lines[n]["kind"]
            ],
        )
        ws.write_string(r, 2, str(res["provenance"].get(n, "")))
        arr = getter(lines[n])
        if arr is None:
            continue
        for t in range(len(labels)):
            v = _num(arr[t])
            if v is not None:
                ws.write_number(r, C0 + t, v, fmt)
    ws.set_column(0, 0, 34)
    ws.set_column(1, 1, 20)
    ws.set_column(2, 2, 26)
    ws.set_column(C0, C0 + max(len(labels), 1) - 1, 11)
    ws.freeze_panes(R0 + 1, 1)


def write_grids(ctx: WorkbookContext) -> None:
    """Write the Data sheet and, for anomaly detection, the Expected and Scores sheets."""
    st = ctx.st
    labels = ctx.labels
    names = ctx.names
    do_anom = ctx.do_anom
    units = ctx.units
    F = ctx.F
    ws_d = ctx.ws_d
    ws_e = ctx.ws_e
    ws_s = ctx.ws_s
    R0 = ctx.R0
    C0 = ctx.C0

    _grid(
        ctx,
        ws_d,
        "Data" + units,
        "The history as read, oldest period first. Blank = no value for that period.",
        lambda rec: rec["values"],
        F["num"],
    )
    if do_anom:
        _grid(
            ctx,
            ws_e,
            "Expected" + units,
            "What each period would have been on the line's own level and seasonal pattern, "
            "worked out without using that period's own value. Computed by the skill's scripts and stored as values, "
            "not formulas: changing the Data sheet does not re-run detection. Run the review again instead.",
            lambda rec: rec["d"].get("expected"),
            F["num"],
        )
        _grid(
            ctx,
            ws_s,
            "Scores",
            "How far each period sits from expected, in units of the line's usual scatter. "
            "Beyond {:.1f} either way counts as unusual. Stored values from the skill's scripts, not formulas.".format(
                st["z_threshold"]
            ),
            lambda rec: rec["d"].get("score"),
            F["sc"],
        )
        if names and labels:
            rng = f"{_cell(R0 + 1, C0)}:{_cell(R0 + len(names), C0 + len(labels) - 1)}"
            ws_s.conditional_format(
                rng,
                {
                    "type": "cell",
                    "criteria": ">=",
                    "value": st["z_threshold"],
                    "format": F["hi"],
                },
            )
            ws_s.conditional_format(
                rng,
                {
                    "type": "cell",
                    "criteria": "<=",
                    "value": -st["z_threshold"],
                    "format": F["lo"],
                },
            )
