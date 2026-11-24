"""
description: Opens the xlsxwriter workbook, adds the formats and sheets, and returns the shared context.
last_updated: 2026-11-24
"""

from __future__ import annotations

import numpy as np
import xlsxwriter
from workbook_context import WorkbookContext
from workbook_formats import add_formats


def open_workbook(res: dict, path: str) -> WorkbookContext:
    """Open the workbook at path with its formats and sheets, ready for the sheet writers."""
    st, labels, lines = res["settings"], res["labels"], res["lines"]
    names = list(lines)
    do_anom, do_trend = "anomaly" in st["analyses"], "trend" in st["analyses"]
    voc = res["vocab"]
    units = (" ({})".format(st["units"])) if st["units"] else ""
    biggest = max(
        (
            float(np.nanmax(np.abs(r["values"])))
            for r in lines.values()
            if np.isfinite(r["values"]).any()
        ),
        default=1.0,
    )
    nfmt = (
        "#,##0;(#,##0)"
        if biggest >= 1000
        else "#,##0.0;(#,##0.0)"
        if biggest >= 20
        else "#,##0.000;(#,##0.000)"
    )

    wb = xlsxwriter.Workbook(
        path,
        {
            "nan_inf_to_errors": False,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        },
    )
    wb.set_properties(
        {
            "title": res["title"],
            "comments": "Trend analysis and anomaly detection {}, run {}".format(
                st["version"], res["run_id"]
            ),
        }
    )
    F = add_formats(wb, nfmt)

    # sheet order as the reader meets it; Data comes late but everything points at it
    ws_sum = wb.add_worksheet("Summary")
    ws_an = wb.add_worksheet("Anomalies") if do_anom else None
    ws_tr = wb.add_worksheet("Trends") if do_trend else None
    ws_dc = wb.add_worksheet("Data checks") if do_anom else None
    ws_ch = wb.add_worksheet("Charts")
    ws_d = wb.add_worksheet("Data")
    ws_e = wb.add_worksheet("Expected") if do_anom else None
    ws_s = wb.add_worksheet("Scores") if do_anom else None
    ws_m = wb.add_worksheet("Method")
    ws_x = wb.add_worksheet("_chart")
    ws_x.hide()

    R0, C0 = 3, 3  # header row and first period column (0-based)
    row_of = {n: R0 + 1 + i for i, n in enumerate(names)}
    return WorkbookContext(
        res=res,
        st=st,
        labels=labels,
        lines=lines,
        names=names,
        do_anom=do_anom,
        do_trend=do_trend,
        voc=voc,
        units=units,
        wb=wb,
        F=F,
        ws_sum=ws_sum,
        ws_an=ws_an,
        ws_tr=ws_tr,
        ws_dc=ws_dc,
        ws_ch=ws_ch,
        ws_d=ws_d,
        ws_e=ws_e,
        ws_s=ws_s,
        ws_m=ws_m,
        ws_x=ws_x,
        R0=R0,
        C0=C0,
        row_of=row_of,
    )
