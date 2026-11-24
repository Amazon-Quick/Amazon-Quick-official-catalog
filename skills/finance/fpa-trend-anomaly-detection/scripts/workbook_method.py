"""
description: Writes the Method sheet: how to read the workbook, the settings, each line's treatment and the limits.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math

import numpy as np
from workbook_context import WorkbookContext


def write_method(ctx: WorkbookContext, wide) -> None:
    """Write the Method sheet, using the wrapped-text format the Summary sheet added."""
    res = ctx.res
    st = ctx.st
    lines = ctx.lines
    names = ctx.names
    F = ctx.F
    ws_m = ctx.ws_m

    ws = ws_m
    ws.set_column(0, 0, 34)
    ws.set_column(1, 1, 26)
    ws.set_column(2, 7, 18)
    ws.write_string(0, 0, "Method and settings", F["title"])
    text = [
        (
            "What this is",
            "Two separate analyses of each line's own history. Trend analysis says where a line is heading and how fast. "
            "Anomaly detection says which periods do not fit the line's pattern. Neither has seen a budget, a forecast, or any drivers, and neither says why.",
        ),
        (
            "Expected value",
            "For each period: the level of the periods around it, carried along the local slope, plus the usual pattern for that position "
            "in the year taken from the other years. The period's own value is never used to work out its own expected value.",
        ),
        (
            "Unusual",
            "A period whose gap to expected is more than {:.1f} times the line's own usual scatter (a z-score using the Qn estimate of scatter, which "
            "ignores up to half the periods being unusual). 'Outlier test' is a second opinion: the generalized ESD test at 5%, applied when a line has 15 or more periods.".format(
                st["z_threshold"]
            ),
        ),
        (
            "Material",
            "Your thresholds, at the top of the Anomalies sheet. Every unusual period is listed either way; those under threshold are marked, not removed.",
        ),
        (
            "New level",
            f"A step that has held for at least {({'D': 7, 'W': 4}).get(st['freq'], 3)} "
            "periods. On seasonal lines it is found on the change from the same period "
            "a year earlier, then placed and confirmed on the seasonally adjusted line. "
            "Periods after it are judged against the new level.",
        ),
        (
            "Seasonal adjustment",
            "Used where the pattern plainly repeats from year to year and there are at least two full years. Otherwise the line is read without it, and that is stated per line below.",
        ),
        (
            "Trend",
            "The annual rate at which the level has moved over the trend window, on the seasonally adjusted line with unusual periods set aside. "
            "Where the level stepped, the rate with the steps taken out is shown beside it. Direction is 'Flat' unless a rank test finds a clear trend and it is at least 1% a year.",
        ),
        (
            "Windows",
            "Amounts for the period are totaled over a window (year to date, last twelve months); balances and rates are averaged. The line's type is on the Data sheet.",
        ),
    ]
    r = 2
    for k, v in text:
        ws.write_string(r, 0, k, F["b"])
        ws.merge_range(r, 1, r, 7, v, wide)
        ws.set_row(r, 15 * max(1, math.ceil(len(v) / 115)))
        r += 1
    r += 1
    ws.write_string(r, 0, "Settings", F["b"])
    rows = [
        (
            "Analyses run",
            ", ".join(
                "trend analysis" if a == "trend" else "anomaly detection"
                for a in st["analyses"]
            ),
        ),
        ("Time grain", "{} ({})".format(st["grain_word"], st["grain_source"])),
        ("Seasonal cycle", f"{st['season']} periods"),
        (
            "Fiscal year starts",
            [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ][st["fiscal_year_start"] - 1],
        ),
        (
            "Sensitivity",
            "{} (score {:.1f})".format(st["sensitivity"], st["z_threshold"]),
        ),
        (
            "Direction reported",
            {
                "both": "above and below expected",
                "above": "above expected only",
                "below": "below expected only",
            }[st["direction"]],
        ),
        ("Units", st["units"] or "as in the source"),
        ("Source", st["source_file"] or "passed in directly"),
        (
            "Version / run",
            "{} / {} at {}".format(st["version"], res["run_id"], res["run_at"]),
        ),
    ]
    for k, v in rows:
        r += 1
        ws.write_string(r, 0, k)
        ws.write_string(r, 1, v)
    r += 2
    ws.write_row(
        r,
        0,
        [
            "Line",
            "Read from",
            "Type",
            "Periods",
            "Analyzed as",
            "Seasonal adjustment",
            "Typical unexplained movement",
            "Notes",
        ],
        F["h"],
    )
    for n in names:
        r += 1
        rec, d = lines[n], lines[n]["d"]
        ws.write_string(r, 0, n)
        ws.write_string(r, 1, str(res["provenance"].get(n, "")))
        ws.write_string(
            r,
            2,
            "{} ({})".format(
                {"flow": "amount for the period", "balance": "balance", "rate": "rate"}[
                    rec["kind"]
                ],
                rec["kind_source"],
            ),
        )
        ws.write_number(r, 3, int(np.isfinite(rec["values"]).sum()), F["int"])
        if d["status"] != "ok":
            ws.write_string(r, 4, "not analyzed: too short")
        else:
            ws.write_string(r, 4, "percentages" if d["mode"] == "ratio" else "amounts")
            ws.write_string(
                r,
                5,
                "yes"
                if d["seasonal"]
                else (
                    "no: under two years"
                    if d["season"] > 1 and d["n"] < 2 * d["season"]
                    else "no: no repeating pattern found"
                ),
            )
            if d["mode"] == "ratio":
                ws.write_number(r, 6, d["scale_pct"], F["pct0"])
            else:
                ws.write_number(r, 6, d["scale"], F["num"])
        ws.write_string(r, 7, " ".join(d.get("notes", [])))
    r += 2
    ws.write_string(r, 0, "Limits", F["b"])
    limits = [
        "Only the line's own history is used: no budget, forecast, drivers, or transactions, so causes are not identified.",
        "No working-day, public-holiday, or moving-event adjustment. A 4-4-5 style calendar is handled only to the extent it repeats every year.",
        "Under two years of history the seasonal pattern cannot be separated; with exactly two, a flag may be either year's.",
        "A change in the latest period or two cannot yet be called a one-off or a new level.",
        "A seasonal pattern that is itself changing (a peak growing year by year) can show as unusual periods at the peak.",
        "Events are ranked by amount, which does not compare across lines in different units.",
        "Currency effects are not separated out.",
    ]
    for i, v in enumerate(limits):
        ws.merge_range(r + 1 + i, 0, r + 1 + i, 7, v, wide)
