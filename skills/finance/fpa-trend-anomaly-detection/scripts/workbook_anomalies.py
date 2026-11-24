"""
description: Writes the Anomalies sheet: one row per event, the reader's thresholds and the sign-off columns.
last_updated: 2026-11-24
"""

from __future__ import annotations

from typing import NamedTuple

from workbook_context import RECURRING, WorkbookContext, _cell, _num

AC = {
    k: i
    for i, k in enumerate(
        [
            "line",
            "period",
            "type",
            "dir",
            "actual",
            "expected",
            "gap",
            "gap_pct",
            "periods",
            "total",
            "score",
            "evidence",
            "material",
            "why",
            "check",
            "basis",
            "expl",
            "recur",
            "owner",
            "review",
            "date",
        ]
    )
}


class AnomalyRows(NamedTuple):
    """The first and last event rows on the Anomalies sheet (None when not written)."""

    first: int | None
    last: int | None


def write_anomalies(ctx: WorkbookContext) -> AnomalyRows:
    """Write the Anomalies sheet when anomaly detection ran; return its event rows."""
    res = ctx.res
    st = ctx.st
    do_anom = ctx.do_anom
    units = ctx.units
    F = ctx.F
    ws_an = ctx.ws_an
    C0 = ctx.C0
    row_of = ctx.row_of
    dref = ctx.dref

    an_first = an_last = None
    if do_anom:
        ws = ws_an
        ws.write_string(
            0,
            0,
            "Anomalies: periods that do not fit their line's own pattern",
            F["title"],
        )
        ws.write_string(
            1,
            0,
            "Largest gap first. Change the blue cells to apply your own thresholds; Material? and the Summary recalculate.",
            F["sub"],
        )
        ws.write_string(2, 1, "Minimum gap %", F["b"])
        ws.write_number(2, 2, st["min_gap_pct"], F["in_pct"])
        ws.write_string(
            2,
            3,
            "A gap smaller than this share of expected is below threshold.",
            F["note"],
        )
        ws.write_string(3, 1, "Minimum gap amount" + units, F["b"])
        ws.write_number(3, 2, st["min_gap_amount"], F["in_num"])
        ws.write_string(3, 3, "0 = no amount test.", F["note"])
        ws.write_string(4, 1, "A gap must reach", F["b"])
        ws.write_string(
            4, 2, "Both" if st["threshold_rule"] == "both" else "Either", F["in_txt"]
        )
        ws.data_validation(
            4, 2, 4, 2, {"validate": "list", "source": ["Both", "Either"]}
        )
        ws.write_string(
            4,
            3,
            "Both = the percentage and the amount. Either = one of them is enough.",
            F["note"],
        )
        hdr = [
            "Line",
            "Period",
            "Type",
            "Above / below expected",
            "Actual" + units,
            "Expected" + units,
            "Gap" + units,
            "Gap %",
            "Periods",
            "Total gap over the event" + units,
            "Score",
            "Outlier test",
            "Material?",
            "What it looks like",
            "What to check",
            "Expected is based on",
        ]
        H = 6
        ws.write_row(H, 0, hdr, F["h"])
        ws.write_row(
            H,
            AC["expl"],
            ["Explanation", "One-time or recurring?", "Owner", "Reviewed by", "Date"],
            F["hy"],
        )
        r = H + 1
        an_first = r
        pc, ac, rc = _cell(2, 2, True), _cell(3, 2, True), _cell(4, 2, True)
        for e in res["events"]:
            n, t = e["line"], e["peak"]
            ws.write_string(r, AC["line"], n, F["txt"])
            ws.write_string(r, AC["period"], e["period"], F["txt"])
            ws.write_string(r, AC["type"], e["type_label"], F["txt"])
            ws.write_string(
                r, AC["dir"], "Above" if e["gap"] > 0 else "Below", F["txt"]
            )
            point = e["type"] not in ("new_level", "temporary_level", "unwound_level")
            a, x = _num(e["actual"]), _num(e["expected"])
            if point and a is not None and x is not None:
                ws.write_formula(r, AC["actual"], "=" + dref(n, t), F["num"], a)
                ws.write_formula(
                    r,
                    AC["expected"],
                    f"=Expected!{_cell(row_of[n], C0 + t)}",
                    F["num"],
                    x,
                )
            else:
                if a is not None:
                    ws.write_number(r, AC["actual"], a, F["num"])
                if x is not None:
                    ws.write_number(r, AC["expected"], x, F["num"])
            g, gp = _num(e["gap"]), _num(e["gap_pct"])
            ga, gx = _cell(r, AC["actual"]), _cell(r, AC["expected"])
            ws.write_formula(
                r, AC["gap"], f"={ga}-{gx}", F["numb"], g if g is not None else 0
            )
            gcell, pcell = _cell(r, AC["gap"]), _cell(r, AC["gap_pct"])
            if gp is not None:
                ws.write_formula(
                    r,
                    AC["gap_pct"],
                    f'=IF({gx}=0,"",{gcell}/ABS({gx}))',
                    F["pct"],
                    gp,
                )
            else:
                ws.write_string(r, AC["gap_pct"], "n/a", F["txt"])
            ws.write_number(r, AC["periods"], e["periods"], F["int"])
            if e.get("total_gap") is not None:
                ws.write_number(r, AC["total"], e["total_gap"], F["num"])
            ws.write_number(r, AC["score"], _num(e["score"]) or 0.0, F["sc"])
            ws.write_string(r, AC["evidence"], e["evidence"], F["txt"])
            mat = (
                f'=IF(ISNUMBER({pcell}),IF({rc}="Either",IF(OR(ABS({pcell})>={pc},AND({ac}>0,ABS({gcell})>={ac})),"Yes","Below threshold"),'
                f'IF(AND(ABS({pcell})>={pc},ABS({gcell})>={ac}),"Yes","Below threshold")),'
                f'IF(AND(ABS({gcell})>={ac},OR({ac}>0,{rc}="Both")),"Yes","Below threshold"))'
            )
            ws.write_formula(
                r,
                AC["material"],
                mat,
                F["txt"],
                "Yes" if e["material"] else "Below threshold",
            )
            ws.write_string(r, AC["why"], e["why"], F["wrap"])
            ws.write_string(r, AC["check"], e["check"], F["wrap"])
            ws.write_string(r, AC["basis"], e["basis"], F["wrap"])
            for c in ("expl", "recur", "owner", "review", "date"):
                ws.write_blank(r, AC[c], None, F["fill"])
            r += 1
        an_last = r - 1
        if not res["events"]:
            ws.write_string(
                H + 1,
                0,
                "No period stands out from its line's own pattern at this sensitivity.",
                F["txt"],
            )
            an_last = an_first
        else:
            ws.data_validation(
                an_first,
                AC["recur"],
                an_last,
                AC["recur"],
                {"validate": "list", "source": RECURRING},
            )
            mrng = "{}:{}".format(
                _cell(an_first, AC["material"]),
                _cell(an_last, AC["material"]),
            )
            ws.conditional_format(
                mrng,
                {
                    "type": "cell",
                    "criteria": "==",
                    "value": '"Yes"',
                    "format": F["yes"],
                },
            )
            ws.autofilter(H, 0, an_last, AC["date"])
        for c, w in zip(
            range(len(AC)),
            [
                30,
                20,
                24,
                12,
                14,
                14,
                14,
                9,
                8,
                14,
                8,
                16,
                15,
                62,
                50,
                36,
                40,
                18,
                14,
                14,
                11,
            ],
            strict=False,
        ):
            ws.set_column(c, c, w)
        ws.freeze_panes(H + 1, 2)
    return AnomalyRows(an_first, an_last)
