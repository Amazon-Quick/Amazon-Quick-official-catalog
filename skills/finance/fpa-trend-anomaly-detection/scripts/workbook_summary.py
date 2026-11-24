"""
description: Writes the Summary sheet: what was read, headline counts as live formulas, largest events and movers.
last_updated: 2026-11-24
"""

from __future__ import annotations

from workbook_anomalies import AC, AnomalyRows
from workbook_context import WorkbookContext, _cell, _num
from workbook_trends import TrendRows


def write_summary(
    ctx: WorkbookContext, anomaly_rows: AnomalyRows, trend_rows: TrendRows, movers: list
):
    """Write the Summary sheet; return the wrapped-text format it adds, which Method reuses."""
    res = ctx.res
    st = ctx.st
    labels = ctx.labels
    names = ctx.names
    do_anom = ctx.do_anom
    do_trend = ctx.do_trend
    voc = ctx.voc
    units = ctx.units
    wb = ctx.wb
    F = ctx.F
    ws_sum = ctx.ws_sum

    an_first, an_last = anomaly_rows
    TC, tr_first, tr_last = trend_rows

    ws = ws_sum
    ws.set_column(0, 0, 38)
    ws.set_column(1, 1, 22)
    ws.set_column(2, 2, 30)
    ws.set_column(3, 6, 16)
    ws.write_string(0, 0, res["title"], F["title"])
    ws.write_string(
        1,
        0,
        "{}{}, {} to {}. Run {}.".format(
            (st["source_file"] + ": ") if st["source_file"] else "",
            f"{len(names)} line{'' if len(names) == 1 else 's'} of {st['grain_word']} history",
            labels[0] if labels else "",
            labels[-1] if labels else "",
            res["run_at"],
        ),
        F["sub"],
    )
    r = 3
    if do_anom:
        ws.write_string(r, 0, "Anomaly detection", F["b"])
        r += 1
        if res["events"]:
            mrng = "Anomalies!{}:{}".format(
                _cell(an_first, AC["material"], True),
                _cell(an_last, AC["material"], True),
            )
            n_mat = sum(1 for e in res["events"] if e["material"])
            ws.write_string(r, 0, "Events at or above your thresholds")
            ws.write_formula(r, 1, f'=COUNTIF({mrng},"Yes")', F["int"], n_mat)
            ws.write_string(r + 1, 0, "Unusual for their line but below threshold")
            ws.write_formula(
                r + 1,
                1,
                f'=COUNTIF({mrng},"Below threshold")',
                F["int"],
                len(res["events"]) - n_mat,
            )
        else:
            ws.write_string(
                r,
                0,
                "No period stands out from its line's own pattern at this sensitivity.",
            )
        ws.write_string(r + 2, 0, "Data checks raised")
        ws.write_number(r + 2, 1, len(res["data_checks"]), F["int"])
        ws.write_string(r + 3, 0, "Thresholds in use")
        ws.write_formula(
            r + 3,
            1,
            f'=TEXT(Anomalies!{_cell(2, 2, True)},"0.0%")&IF(Anomalies!{_cell(3, 2, True)}>0," "&IF(Anomalies!{_cell(4, 2, True)}="Both","and","or")&" "&TEXT(Anomalies!{_cell(3, 2, True)},"#,##0"),"")',
            F["txt"],
            f"{100 * st['min_gap_pct']:.1f}%"
            + (
                (
                    " {} {}".format(
                        "and" if st["threshold_rule"] == "both" else "or",
                        "{:,.0f}".format(st["min_gap_amount"]),
                    )
                )
                if st["min_gap_amount"]
                else ""
            ),
        )
        ws.write_string(r + 3, 2, "Change them on the Anomalies sheet.", F["sub"])
        r += 5
        if res["events"]:
            ws.write_row(
                r,
                0,
                [
                    "Largest events",
                    "Period",
                    "Type",
                    "Gap" + units,
                    "Gap %",
                    "Material?",
                ],
                F["h"],
            )
            for i in range(min(10, len(res["events"]))):
                e, src = res["events"][i], an_first + i
                ws.write_formula(
                    r + 1 + i,
                    0,
                    "=Anomalies!{}".format(_cell(src, AC["line"])),
                    F["txt"],
                    e["line"],
                )
                ws.write_formula(
                    r + 1 + i,
                    1,
                    "=Anomalies!{}".format(_cell(src, AC["period"])),
                    F["txt"],
                    e["period"],
                )
                ws.write_formula(
                    r + 1 + i,
                    2,
                    "=Anomalies!{}".format(_cell(src, AC["type"])),
                    F["txt"],
                    e["type_label"],
                )
                ws.write_formula(
                    r + 1 + i,
                    3,
                    "=Anomalies!{}".format(_cell(src, AC["gap"])),
                    F["num"],
                    _num(e["gap"]) or 0,
                )
                gp = _num(e["gap_pct"])
                ws.write_formula(
                    r + 1 + i,
                    4,
                    "=Anomalies!{}".format(_cell(src, AC["gap_pct"])),
                    F["pct"],
                    gp if gp is not None else "n/a",
                )
                ws.write_formula(
                    r + 1 + i,
                    5,
                    "=Anomalies!{}".format(_cell(src, AC["material"])),
                    F["txt"],
                    "Yes" if e["material"] else "Below threshold",
                )
            r += min(10, len(res["events"])) + 3
    if do_trend:
        ws.write_string(r, 0, "Trend analysis", F["b"])
        r += 1
        drng = "Trends!{}:{}".format(
            _cell(tr_first, TC["dir"], True),
            _cell(tr_last, TC["dir"], True),
        )
        for j, word in enumerate(("Rising", "Flat", "Falling")):
            ws.write_string(r + j, 0, f"Lines {word.lower()}")
            ws.write_formula(
                r + j,
                1,
                f'=COUNTIF({drng},"{word}")',
                F["int"],
                sum(1 for t in res["trends"] if t.get("direction") == word),
            )
        r += 4
        if movers:
            ws.write_row(
                r,
                0,
                [
                    "Largest movers: "
                    + voc["ltm"].lower()
                    + " against the 12 months before",
                    "Change" + units,
                    "Change %",
                    "Direction",
                ],
                F["h"],
            )
            for i, t in enumerate(movers[:8]):
                tr = tr_first + names.index(t["name"])
                ws.write_formula(
                    r + 1 + i,
                    0,
                    "=Trends!{}".format(_cell(tr, TC["line"])),
                    F["txt"],
                    t["name"],
                )
                ws.write_formula(
                    r + 1 + i,
                    1,
                    "=Trends!{}".format(_cell(tr, TC["ltmchg"])),
                    F["num"],
                    t["ltm_change"],
                )
                ws.write_formula(
                    r + 1 + i,
                    2,
                    "=Trends!{}".format(_cell(tr, TC["ltmpct"])),
                    F["pct"],
                    t["ltm_pct"] if t["ltm_pct"] is not None else "n/a",
                )
                ws.write_formula(
                    r + 1 + i,
                    3,
                    "=Trends!{}".format(_cell(tr, TC["dir"])),
                    F["txt"],
                    t.get("direction", ""),
                )
            r += min(8, len(movers)) + 3
    ws.write_string(r, 0, "Read this before relying on it", F["b"])
    wide = wb.add_format({"text_wrap": True, "valign": "top"})
    for i, c in enumerate(res["caveats"]):
        ws.merge_range(r + 1 + i, 0, r + 1 + i, 6, c, wide)
        ws.set_row(r + 1 + i, 30 if len(c) > 110 else 15)
    return wide
