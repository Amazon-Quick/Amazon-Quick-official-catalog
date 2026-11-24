"""
description: Writes the Trends sheet: one row per line with comparisons as formulas on the Data sheet.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np
import trend_analysis as ta
from workbook_context import WorkbookContext, _cell


class TrendRows(NamedTuple):
    """The Trends column positions and first and last line rows (empty / None when not written)."""

    TC: dict
    first: int | None
    last: int | None


def write_trends(ctx: WorkbookContext) -> TrendRows:
    """Write the Trends sheet when trend analysis ran; return its columns and rows."""
    res = ctx.res
    st = ctx.st
    lines = ctx.lines
    names = ctx.names
    do_trend = ctx.do_trend
    voc = ctx.voc
    units = ctx.units
    F = ctx.F
    ws_tr = ctx.ws_tr
    dref = ctx.dref
    drange = ctx.drange

    TC = {}
    tr_first = tr_last = None
    if do_trend:
        ws = ws_tr
        ws.write_string(
            0, 0, "Trends: where each line is heading and how fast", F["title"]
        )
        ws.write_string(
            1,
            0,
            "Comparisons are formulas on the Data sheet. Amounts for the period are totaled over a window; "
            "balances and rates are averaged.",
            F["sub"],
        )
        cols = [
            ("line", "Line", 32),
            ("basis", "Window basis", 11),
            ("periods", "Periods of history", 9),
            ("last", "Latest period", 11),
            ("value", "Latest value" + units, 14),
            ("prior", voc["prior"] + " %", 9),
            ("yoy", "Year on year %", 9),
            ("recent", voc["recent"] + ", year on year %", 12),
            ("ytd", "Year to date, year on year %", 12),
            ("ltm", voc["ltm"] + units, 14),
            ("ltmp", "Prior " + voc["ltm"].lower() + units, 14),
            ("ltmpct", voc["ltm"] + " %", 9),
            ("ltmchg", voc["ltm"] + " change" + units, 14),
            ("cagr", "Compound annual growth %", 11),
            ("cagry", "over years", 7),
            ("trend", "Trend, % a year", 9),
            ("under", "Trend with level shifts taken out, % a year", 13),
            ("dir", "Direction", 11),
            ("chg", "Change in trend", 34),
            ("shift", "Level shifts", 34),
            ("seas", "Seasonal pattern", 16),
            ("peak", "Highest", 14),
            ("low", "Lowest", 14),
            ("noise", "Typical unexplained movement", 12),
            ("aside", "Set aside from the trend", 28),
            ("read", "Reading", 90),
        ]
        TC = {k: i for i, (k, _, _) in enumerate(cols)}
        H = 3
        for k, title, w in cols:
            ws.write_string(H, TC[k], title, F["h"])
            ws.set_column(TC[k], TC[k], w)
        tr_first = H + 1
        by_name = {t["name"]: t for t in res["trends"]}
        for i, n in enumerate(names):
            r, t = tr_first + i, by_name[n]
            rec = lines[n]
            ws.write_string(r, TC["line"], n, F["b"])
            ws.write_string(r, TC["basis"], t["basis"], F["txt"])
            ws.write_number(r, TC["periods"], t["periods"], F["int"])
            if "last_period" not in t:
                continue
            ws.write_string(r, TC["last"], t["last_period"], F["txt"])
            valid = np.isfinite(rec["values"])
            last = int(np.where(valid)[0][-1])
            agg = "SUM" if t["basis"] == "Total" else "AVERAGE"
            lag, recn = ta.PER_YEAR_N[st["freq"]], ta.RECENT[st["freq"]]
            ws.write_formula(
                r, TC["value"], "=" + dref(n, last), F["num"], t["last_value"]
            )
            if t.get("prior_pct") is not None:
                ws.write_formula(
                    r,
                    TC["prior"],
                    f"={dref(n, last)}/{dref(n, last - 1)}-1",
                    F["pct"],
                    t["prior_pct"],
                )
            if t.get("yoy_pct") is not None and last - lag >= 0:
                ws.write_formula(
                    r,
                    TC["yoy"],
                    f"={dref(n, last)}/{dref(n, last - lag)}-1",
                    F["pct"],
                    t["yoy_pct"],
                )
            if t.get("recent_yoy_pct") is not None:
                ws.write_formula(
                    r,
                    TC["recent"],
                    f"={agg}({drange(n, last - recn + 1, last)})/{agg}({drange(n, last - lag - recn + 1, last - lag)})-1",
                    F["pct"],
                    t["recent_yoy_pct"],
                )
            if t.get("ytd_pct") is not None:
                k = t["ytd_periods"]
                ws.write_formula(
                    r,
                    TC["ytd"],
                    f"={agg}({drange(n, last - k + 1, last)})/{agg}({drange(n, last - lag - k + 1, last - lag)})-1",
                    F["pct"],
                    t["ytd_pct"],
                )
            ltm_len = lag
            if t.get("ltm") is not None:
                ws.write_formula(
                    r,
                    TC["ltm"],
                    f"={agg}({drange(n, last - ltm_len + 1, last)})",
                    F["num"],
                    t["ltm"],
                )
            if t.get("ltm_prior") is not None:
                ws.write_formula(
                    r,
                    TC["ltmp"],
                    f"={agg}({drange(n, last - lag - ltm_len + 1, last - lag)})",
                    F["num"],
                    t["ltm_prior"],
                )
                a, b = _cell(r, TC["ltm"]), _cell(r, TC["ltmp"])
                if t.get("ltm_pct") is not None:
                    ws.write_formula(
                        r, TC["ltmpct"], f"={a}/{b}-1", F["pct"], t["ltm_pct"]
                    )
                ws.write_formula(
                    r, TC["ltmchg"], f"={a}-{b}", F["num"], t["ltm_change"]
                )
            if t.get("cagr_pct") is not None:
                ws.write_number(r, TC["cagr"], t["cagr_pct"], F["pct"])
                ws.write_number(r, TC["cagry"], t["cagr_years"], F["int"])
            if t.get("trend_pct") is not None:
                ws.write_number(r, TC["trend"], t["trend_pct"], F["pct"])
            if t.get("underlying_pct") is not None:
                ws.write_number(r, TC["under"], t["underlying_pct"], F["pct"])
            ws.write_string(r, TC["dir"], t.get("direction", ""), F["txt"])
            c = t.get("trend_change")
            if c:
                ws.write_string(
                    r,
                    TC["chg"],
                    "{} around {}: from {:+.1f}% to {:+.1f}% a year".format(
                        c["word"],
                        c["period"],
                        100 * c["before_pct"],
                        100 * c["after_pct"],
                    ),
                    F["wrap"],
                )
            if t.get("level_shifts"):
                ws.write_string(
                    r,
                    TC["shift"],
                    "; ".join(
                        "{} {} from {}".format(
                            "Up" if h["size"] > 0 else "Down",
                            (f"{100 * abs(h['size_pct']):.0f}%")
                            if math.isfinite(h["size_pct"])
                            else "{:,.0f}".format(abs(h["size"])),
                            h["period"],
                        )
                        for h in t["level_shifts"]
                    ),
                    F["wrap"],
                )
            ws.write_string(r, TC["seas"], t.get("seasonal_label", ""), F["txt"])
            if t.get("peak"):
                ws.write_string(
                    r,
                    TC["peak"],
                    "{} ({:+.0f}%)".format(t["peak"], 100 * t["peak_index"])
                    if rec["d"]["mode"] == "ratio"
                    else t["peak"],
                    F["txt"],
                )
                ws.write_string(
                    r,
                    TC["low"],
                    "{} ({:+.0f}%)".format(t["trough"], 100 * t["trough_index"])
                    if rec["d"]["mode"] == "ratio"
                    else t["trough"],
                    F["txt"],
                )
            if t.get("noise_pct") is not None:
                ws.write_number(r, TC["noise"], t["noise_pct"], F["pct0"])
            elif t.get("noise") is not None:
                ws.write_number(r, TC["noise"], t["noise"], F["num"])
            if t.get("set_aside"):
                ws.write_string(r, TC["aside"], ", ".join(t["set_aside"]), F["wrap"])
            ws.write_string(r, TC["read"], t.get("read", ""), F["wrap"])
        tr_last = tr_first + max(len(names), 1) - 1
        ws.autofilter(H, 0, tr_last, len(cols) - 1)
        ws.freeze_panes(H + 1, 1)
    return TrendRows(TC, tr_first, tr_last)
