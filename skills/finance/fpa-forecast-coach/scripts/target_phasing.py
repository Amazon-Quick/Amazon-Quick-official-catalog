"""
description: The Target_Phasing sheet: find a target's window in the forecast periods, spread the target by historical period-of-year shares next to plain scaling of the baseline P50, and say where it sits against the P10 to P90 band.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

import finance_methods as fm
import numpy as np
from periods import AmbiguousDateError, as_date
from workbook_formats import defang


def target_start(start, labels: list, date_order: str | None = None) -> int:
    """Window start as an offset into the forecast periods: None -> 0, an int offset, or a period label/date
    (an ISO month such as '2030-01', or a label exactly as printed on the Forecast sheet)."""
    if start is None:
        return 0
    if isinstance(start, int) and not isinstance(start, bool):
        return max(0, start)
    want = str(start).strip()
    for i, lab in enumerate(labels):
        if lab == want:
            return i
    try:
        d = as_date(want, date_order)
    except AmbiguousDateError:
        raise
    except ValueError:
        d = None
    if d is not None:
        for i, lab in enumerate(labels):
            try:
                parsed = as_date(lab, date_order)
            except AmbiguousDateError:
                raise
            except ValueError:
                continue
            if parsed == d or (parsed.year, parsed.month) == (d.year, d.month):
                return i
    raise ValueError(
        f"target start {start!r} is not one of the forecast periods ({labels[0]} to {labels[-1]})"
    )


def _window(t, labels: list, horizon: int, date_order: str | None, name: str):
    total = float(t["total"] if isinstance(t, dict) else t)
    asked = t.get("periods") if isinstance(t, dict) else None
    s0 = target_start(
        t.get("start") if isinstance(t, dict) else None, labels, date_order
    )
    length = int(min(horizon - s0, asked or horizon - s0))
    if length < 1:
        raise ValueError(
            f"target window for {name} starts after the forecast horizon; raise horizon to at least "
            f"{s0 + int(asked or 1)}"
        )
    return total, s0, length


def _flag(name, total, p10, p90, outside, length, u) -> str | None:
    if total > float(p90.sum()) or total < float(p10.sum()):
        side = (
            "above the sum of the period P90s"
            if total > float(p90.sum())
            else "below the sum of the period P10s"
        )
        return (
            f"{name}: the target is {side} ({float(p10.sum()):,.1f} to {float(p90.sum()):,.1f}{u}). "
            "History alone does not get there; the gap has to be explained by something the baseline "
            "cannot see."
        )
    if outside:
        return (
            f"{name}: the target total is within reach, but {outside} of {length} phased periods fall "
            "outside the baseline's P10 to P90 band; the seasonal shape and the baseline's shape disagree in "
            "those periods."
        )
    return None


def write_target_phasing(
    wb, F, names, clean, fc, targets, labels, horizon, season, units, date_order=None
) -> list:
    """Write the Target_Phasing sheet and return one record per target.

    'Scaled' multiplies the baseline's P50 by one factor (what a goal-seek does). 'Phased' spreads the total by
    the share of a year each period has historically carried. They differ exactly where the baseline's shape
    and the business's seasonal shape differ, which is the thing worth looking at.
    """
    ws = wb.add_worksheet("Target_Phasing")
    hdr = [
        "Series",
        "Period",
        "Baseline P50",
        "P50 scaled to target",
        "Target phased by history",
        "Phased minus scaled",
        "Phased share of total",
        "Phased inside P10 to P90?",
    ]
    ws.write_string(
        0,
        0,
        "Phasing a total only makes sense for a flow (sales, units, spend). For a balance such as "
        "inventory or headcount, phase the driver rather than the balance.",
        F["flag"],
    )
    for c, h in enumerate(hdr):
        ws.write_string(2, c, h, F["h"])
    ws.set_column(0, 1, 22)
    ws.set_column(2, 7, 16)
    ws.set_row(2, 32)
    ws.freeze_panes(3, 0)
    u = f" {units}" if units else ""
    r, out = 3, []
    for n in names:
        if n not in targets:
            continue
        total, s0, length = _window(targets[n], labels, horizon, date_order, n)
        q = fc[n]
        p50, p10, p90 = (
            np.asarray(q[k][s0 : s0 + length], dtype=float)
            for k in ("p50", "p10", "p90")
        )
        base = float(p50.sum())
        # shares come from cycles that start at the window's own period-of-year (calendar years for a
        # calendar-year target), positioned from the window start
        full = fm.phase_target(
            clean[n]["values"], 1.0, length, season, fallback_shape=p50, start_offset=s0
        )
        w = np.asarray(full["weights"], dtype=float)
        w = w / w.sum() if w.sum() > 0 else np.full(length, 1.0 / length)
        phased = total * w
        scaled = p50 * (total / base) if base else np.full(length, total / length)
        outside = 0
        for i in range(length):
            inside = p10[i] <= phased[i] <= p90[i]
            outside += 0 if inside else 1
            ws.write_string(r, 0, defang(n))
            ws.write_string(r, 1, labels[s0 + i])
            ws.write_number(r, 2, float(p50[i]), F["num"])
            ws.write_number(r, 3, float(scaled[i]), F["num"])
            ws.write_number(r, 4, float(phased[i]), F["fin"])
            ws.write_number(r, 5, float(phased[i] - scaled[i]), F["num"])
            ws.write_number(r, 6, float(w[i]), F["pct"])
            ws.write_string(
                r, 7, "yes" if inside else "NO", F["lbl"] if inside else F["flag"]
            )
            r += 1
        ws.write_string(r, 0, defang(n), F["lbl"])
        ws.write_string(r, 1, "Total", F["lbl"])
        for c, v in ((2, base), (3, float(scaled.sum())), (4, float(phased.sum()))):
            ws.write_number(r, c, v, F["numb"])
        ws.write_string(r, 7, defang("basis: " + full["basis"]))
        r += 2
        gap = total / base - 1 if base else float("nan")
        j = int(np.argmax(np.abs(phased - scaled)))
        rec = {
            "series": n,
            "target": total,
            "periods": length,
            "window": [labels[s0], labels[s0 + length - 1]],
            "model_total": base,
            "gap_pct": gap,
            "basis": full["basis"],
            "periods_outside_band": outside,
            "phased": phased.tolist(),
            "scaled": scaled.tolist(),
            "line": (
                f"Target for {n}: {total:,.1f}{u} over {length} periods ({labels[s0]} to "
                f"{labels[s0 + length - 1]}) is {gap * 100:+.1f}% against the baseline's {base:,.1f}{u}. "
                f"Phased on {full['basis']}; the biggest difference from plain proportional scaling is "
                f"{labels[s0 + j]} ({phased[j] - scaled[j]:+,.1f}{u})."
            ),
            "flag": _flag(n, total, p10, p90, outside, length, u),
        }
        out.append(rec)
    return out
