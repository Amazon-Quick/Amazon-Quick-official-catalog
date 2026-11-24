"""
description: The Your_Forecast sheet: where the user's own forecast sits against the baseline's P50 and P10 to P90 band, period by period, and the summary lines about the largest disagreements.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import math

import numpy as np
from workbook_formats import defang

_HEADER = [
    "Series",
    "Period",
    "Your forecast",
    "Baseline P50",
    "Delta",
    "Delta %",
    "Inside P10 to P90?",
    "Baseline P10",
    "Baseline P90",
]


def _flag(n: str, outside: list, periods: int) -> str:
    first = outside[0]
    return (
        f"{n}: your number sits outside the baseline's P10 to P90 band in {len(outside)} of {periods} periods, "
        f"starting {first[0]} (you {first[1]:,.1f}, band {first[2]:,.1f} to {first[3]:,.1f}). "
        "History does not support this view; name the driver behind it."
    )


def write_user_comparison(
    wb, F, names, fc, user_forecast, labels, horizon, units
) -> list:
    """Write the Your_Forecast sheet and return one record per series the user supplied.

    There are no actuals for the future, so this is not an accuracy test. It is a disagreement map:
    where the user sits inside the band (the baseline has no argument), and where they sit outside it
    (the baseline does, and the user should be able to name the driver that justifies it).
    """
    ws = wb.add_worksheet("Your_Forecast")
    for c, h in enumerate(_HEADER):
        ws.write_string(0, c, h, F["h"])
    ws.set_column(0, 1, 22)
    ws.set_column(2, 8, 14)
    ws.freeze_panes(1, 0)
    r, out = 1, []
    for n in names:
        if n not in user_forecast:
            continue
        uv = np.asarray(user_forecast[n], dtype=float).ravel()[:horizon]
        q = fc[n]
        outside, tot_u, tot_m = [], 0.0, 0.0
        for i in range(min(len(uv), horizon)):
            if math.isnan(uv[i]):
                continue
            p50, p10, p90 = float(q["p50"][i]), float(q["p10"][i]), float(q["p90"][i])
            inside = p10 <= uv[i] <= p90
            ws.write_string(r, 0, defang(n))
            ws.write_string(r, 1, labels[i])
            ws.write_number(r, 2, float(uv[i]), F["num"])
            ws.write_number(r, 3, p50, F["num"])
            ws.write_number(r, 4, float(uv[i]) - p50, F["num"])
            ws.write(r, 5, (uv[i] - p50) / p50 if p50 else "", F["pct"])
            ws.write_string(
                r, 6, "yes" if inside else "NO", F["lbl"] if inside else F["flag"]
            )
            ws.write_number(r, 7, p10, F["num"])
            ws.write_number(r, 8, p90, F["num"])
            r += 1
            tot_u += float(uv[i])
            tot_m += p50
            if not inside:
                outside.append((labels[i], float(uv[i]), p10, p90))
        if tot_m:
            out.append(
                {
                    "series": n,
                    "your_total": tot_u,
                    "model_total": tot_m,
                    "delta": tot_u - tot_m,
                    "delta_pct": (tot_u - tot_m) / tot_m,
                    "outside": outside,
                    "n_outside": len(outside),
                    "flag": _flag(n, outside, min(len(uv), horizon))
                    if outside
                    else None,
                }
            )
    return out


def user_summary(gaps: list, units: str) -> list:
    """Summary lines comparing the user's forecast with the baseline across the series they supplied."""
    u = f" {units}" if units else ""
    gaps = sorted(gaps, key=lambda g: -abs(g["delta"]))
    tot_u = sum(g["your_total"] for g in gaps)
    tot_m = sum(g["model_total"] for g in gaps)
    pct = f" ({(tot_u - tot_m) / tot_m * 100:+.1f}%)" if tot_m else ""
    lines = [
        f"Against your own forecast: you total {tot_u:,.1f}{u} and the baseline totals {tot_m:,.1f}{u}"
        f"{pct} across the series you supplied."
    ]
    lines.append(
        "Largest disagreements (absolute): "
        + ", ".join(
            f"{g['series']} {g['delta']:+,.1f}{u} ({g['delta_pct'] * 100:+.1f}%)"
            for g in gaps[:5]
        )
        + "."
    )
    agree = [g["series"] for g in gaps if g["n_outside"] == 0]
    if agree:
        lines.append(
            f"Your forecast sits inside the baseline's band for every period on: "
            f"{', '.join(agree[:6])}{' and others' if len(agree) > 6 else ''}; the baseline has no "
            f"argument {'there' if len(agree) == 1 else 'with those'}."
        )
    return lines
