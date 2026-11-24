"""
description: Write the review workbook a finance reader can check, filter, annotate and hand on.
last_updated: 2026-11-24

Writes the review workbook: one file a finance reader can check, filter, annotate and hand on.

Sheets (those for an analysis that was not run are left out):

    Summary       what was read, the headline counts (live formulas), the largest events, the largest movers
    Anomalies     one row per event: actual, expected, gap, type, evidence, Material? against the reader's
                  own thresholds (editable cells at the top), and blank columns for the explanation and sign-off
    Trends        one row per line: the standard comparisons as formulas on the Data sheet, the trend, any
                  change in it, level shifts, the seasonal pattern, and what was set aside
    Data checks   things that look like a data problem rather than the business
    Charts        actual against expected with the unusual periods marked
    Data          the history as read, one row per line (every figure on the other sheets traces back here)
    Expected      what each period would have been on the line's own pattern
    Scores        how unusual each period is for its line, as a heat map
    Method        how to read the workbook, the settings used, each line's source and treatment, the limits

Conventions: blue type is an input you can change; yellow marks cells for you to fill in; every change is
shown with its sign. Formulas carry their computed values, so the file reads the same before recalculation.
"""

from __future__ import annotations

from workbook_anomalies import write_anomalies
from workbook_charts import write_charts
from workbook_checks import write_checks
from workbook_grids import write_grids
from workbook_method import write_method
from workbook_setup import open_workbook
from workbook_summary import write_summary
from workbook_trends import write_trends

__all__ = ["write"]


def write(res: dict, path: str) -> str:
    """Write the workbook for a series_review.run() result. Returns the path."""
    # sections are written in this order on purpose: it fixes the bytes of the file
    ctx = open_workbook(res, path)
    write_grids(ctx)
    anomaly_rows = write_anomalies(ctx)
    write_checks(ctx)
    trend_rows = write_trends(ctx)
    movers = write_charts(ctx)
    wide = write_summary(ctx, anomaly_rows, trend_rows, movers)
    write_method(ctx, wide)
    ctx.ws_sum.activate()
    ctx.wb.close()
    return path
