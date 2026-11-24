"""
description: Writes the Data checks sheet: things that look like a problem with the data, not the business.
last_updated: 2026-11-24
"""

from __future__ import annotations

from workbook_context import WorkbookContext


def write_checks(ctx: WorkbookContext) -> None:
    """Write the Data checks sheet when anomaly detection ran."""
    res = ctx.res
    do_anom = ctx.do_anom
    F = ctx.F
    ws_dc = ctx.ws_dc

    if do_anom:
        ws = ws_dc
        ws.write_string(
            0,
            0,
            "Data checks: things that look like a problem with the data, not the business",
            F["title"],
        )
        ws.write_string(
            1,
            0,
            "Confirm these at the source before reading anything into the periods they touch.",
            F["sub"],
        )
        ws.write_row(3, 0, ["Line", "Period", "Check", "Detail"], F["h"])
        for i, c in enumerate(res["data_checks"]):
            ws.write_string(4 + i, 0, c["line"], F["txt"])
            ws.write_string(4 + i, 1, c["period"], F["txt"])
            ws.write_string(4 + i, 2, c["check"], F["txt"])
            ws.write_string(4 + i, 3, c["detail"], F["wrap"])
        if not res["data_checks"]:
            ws.write_string(
                4,
                0,
                "Nothing found: no missing periods, stray zeros, reversed signs, unit slips, repeated values, or duplicate lines.",
                F["txt"],
            )
        for c, w in enumerate([34, 20, 18, 100]):
            ws.set_column(c, c, w)
        ws.freeze_panes(4, 0)
