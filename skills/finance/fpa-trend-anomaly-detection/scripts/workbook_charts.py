"""
description: Writes the Charts sheet and its hidden _chart helper sheet: actual against expected or level per line.
last_updated: 2026-11-24
"""

from __future__ import annotations

import numpy as np
from workbook_context import MAX_CHARTS, NAVY, RED, WorkbookContext, _cell, _num


def write_charts(ctx: WorkbookContext) -> list:
    """Write the charts; return the lines ranked by last-twelve-months change, largest first."""
    res = ctx.res
    labels = ctx.labels
    lines = ctx.lines
    names = ctx.names
    do_anom = ctx.do_anom
    wb = ctx.wb
    F = ctx.F
    ws_ch = ctx.ws_ch
    ws_x = ctx.ws_x
    R0 = ctx.R0
    C0 = ctx.C0
    row_of = ctx.row_of

    ws_ch.write_string(0, 0, "Charts", F["title"])
    ws_ch.write_string(
        1,
        0,
        "Actual against expected, with unusual periods marked. Lines with the largest events come first."
        if do_anom
        else "Actual against the underlying level. Lines with the largest movement come first.",
        F["sub"],
    )
    order = []
    for e in res["events"]:
        if e["line"] not in order:
            order.append(e["line"])
    movers = sorted(
        [t for t in res["trends"] if t.get("ltm_change") is not None],
        key=lambda t: -abs(t["ltm_change"]),
    )
    for n in [t["name"] for t in movers] + names:
        if n not in order:
            order.append(n)
    order = [n for n in order if lines[n]["d"]["status"] == "ok"][:MAX_CHARTS]
    ws_x.write_row(0, 0, ["line"] + labels)
    for i, n in enumerate(order):
        d = lines[n]["d"]
        xr = 1 + 2 * i
        ws_x.write_string(xr, 0, n + " | unusual")
        ws_x.write_string(xr + 1, 0, n + " | level")
        for t in range(len(labels)):
            if do_anom and d["flagged"][t] and np.isfinite(lines[n]["values"][t]):
                ws_x.write_number(xr, 1 + t, float(lines[n]["values"][t]))
            lv = _num(d["level"][t])
            if lv is not None:
                ws_x.write_number(xr + 1, 1 + t, lv)
        ch = wb.add_chart({"type": "line"})
        cats = f"=Data!{_cell(R0, C0, True)}:{_cell(R0, C0 + len(labels) - 1, True)}"
        dr = row_of[n]
        ch.add_series(
            {
                "name": "Actual",
                "categories": cats,
                "values": f"=Data!{_cell(dr, C0, True)}:{_cell(dr, C0 + len(labels) - 1, True)}",
                "line": {"color": NAVY, "width": 1.75},
            }
        )
        if do_anom:
            ch.add_series(
                {
                    "name": "Expected",
                    "categories": cats,
                    "values": f"=Expected!{_cell(dr, C0, True)}:{_cell(dr, C0 + len(labels) - 1, True)}",
                    "line": {"color": "#7F7F7F", "width": 1.0, "dash_type": "dash"},
                }
            )
            ch.add_series(
                {
                    "name": "Unusual",
                    "categories": cats,
                    "values": f"=_chart!{_cell(xr, 1, True)}:{_cell(xr, len(labels), True)}",
                    "line": {"none": True},
                    "marker": {
                        "type": "circle",
                        "size": 8,
                        "fill": {"color": RED},
                        "border": {"color": RED},
                    },
                }
            )
        else:
            ch.add_series(
                {
                    "name": "Level, seasonally adjusted" if d["seasonal"] else "Level",
                    "categories": cats,
                    "values": f"=_chart!{_cell(xr + 1, 1, True)}:{_cell(xr + 1, len(labels), True)}",
                    "line": {"color": "#C55A11", "width": 1.25},
                }
            )
        ws_x.write_string(xr, len(labels) + 1, n)
        ch.set_title(
            {"name": ["_chart", xr, len(labels) + 1], "name_font": {"size": 11}}
        )
        ch.set_legend({"position": "bottom"})
        ch.set_y_axis(
            {
                "num_format": "#,##0",
                "major_gridlines": {"visible": True, "line": {"color": "#D9D9D9"}},
            }
        )
        ch.set_x_axis(
            {"interval_unit": max(1, len(labels) // 12), "num_font": {"rotation": -45}}
        )
        ch.set_size({"width": 860, "height": 300})
        ch.show_blanks_as("gap")
        ws_ch.insert_chart(3 + 16 * i, 0, ch)
    if len(names) > len(order):
        ws_ch.write_string(
            3 + 16 * len(order),
            0,
            f"{len(names) - len(order)} more line{'' if len(names) - len(order) == 1 else 's are'} not charted; every line is on the Data and Expected sheets.",
            F["sub"],
        )
    return movers
