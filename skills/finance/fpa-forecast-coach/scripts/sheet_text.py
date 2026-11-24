"""
description: The Commentary and Run_Info sheets: what the run says and the risks in prose, then the run id, settings, source file, the methods' limits, and the disclaimer.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import datetime as _dt

from run_context import RunContext
from workbook_formats import defang

# timezone(timedelta(0)) is UTC and works on Python 3.10, where datetime.UTC does not exist.
_UTC = _dt.timezone(_dt.timedelta(0))
DISCLAIMER = (
    "Outputs are informational and are not accounting or financial advice. Validate the forecast with a "
    "qualified accountant or finance controller before relying on it."
)


def write_commentary_sheet(wb, F, summary: list, flags: list) -> None:
    """What this run says, then the flags to read before using the numbers."""
    ws = wb.add_worksheet("Commentary")
    ws.set_column(0, 0, 118)
    ws.write_string(0, 0, "What this run says", F["title"])
    rr = 2
    for line in summary:
        ws.write_string(rr, 0, defang(line), F["wrap"])
        rr += 1
    rr += 1
    ws.write_string(rr, 0, "Read these before using the numbers", F["title"])
    rr += 2
    for line in flags:
        ws.write_string(rr, 0, "\u2022 " + defang(line), F["flag"])
        rr += 1
    ws.write_string(rr + 1, 0, DISCLAIMER, F["wrap"])


def write_run_info_sheet(
    wb, F, ctx: RunContext, source_file: str | None, prior_path: str | None
) -> None:
    """Run id, settings, inputs, and the methods' limits."""
    ws = wb.add_worksheet("Run_Info")
    ws.set_column(0, 0, 30)
    ws.set_column(1, 1, 86)
    used = sorted({ctx.fc[n]["method"] for n in ctx.names})
    info = [
        ("Run ID", ctx.run_id),
        ("Generated (UTC)", _dt.datetime.now(_UTC).strftime("%Y-%m-%d %H:%M")),
        ("Baseline method used", ", ".join(used)),
        ("Horizon requested", f"{ctx.horizon}"),
        ("Frequency", ctx.freq),
        ("Season", ctx.season),
        ("Series", len(ctx.names)),
        ("Source file", source_file or "(supplied in chat)"),
        ("Prior workbook", prior_path or "(none, first run)"),
        (
            "Baseline method",
            "exponential smoothing (ETS, chosen per series by the corrected Akaike information criterion, "
            "AICc) averaged with the Theta method, or Croston's method with the Syntetos-Boylan approximation "
            "for a series with 40% or more zero values; fitted to "
            "this history; bands are the methods' analytic 80% intervals; no drivers, no scenarios",
        ),
        (
            "Other methods",
            "trailing run-rates, prior year x trailing year-on-year growth, seasonal naive, ETS, Theta, and last "
            "actual held flat, fitted to or computed from the history and backtested on the same windows as "
            "the baseline",
        ),
        ("Disclaimer", DISCLAIMER),
    ]
    for i, (k, v) in enumerate(info):
        ws.write_string(i, 0, k, F["lbl"])
        ws.write(i, 1, v if isinstance(v, int) else defang(v))
