"""
description: Split a segment table's variance into volume, mix and rate effects that add up exactly to the total variance, per segment and in total.
last_updated: 2026-11-24

Pure function with no file access. variance_check re-exports rvm.
"""

from variance_table import clean_num, find_col, parse_table

RVM_COLUMNS = (
    "segment",
    "actual_units",
    "comparison_units",
    "actual_rate",
    "comparison_rate",
)
VALUE_COLUMNS = RVM_COLUMNS[1:]
# Relative, so a table in whole dollars (totals near 1e9) is not failed by float rounding.
IDENTITY_TOLERANCE = 1e-9
NOTE = (
    "Volume = change in total units at comparison mix and rate. Mix = shift in unit share "
    "at comparison rates (mix_vs_avg shows each segment against the average rate; its "
    "total equals the total mix). Rate = rate change on actual units. Volume + mix + rate "
    "= total variance, per segment and in total."
)


def _fail(message):
    return {"status": "FAIL", "faults": [message]}


def _read_segments(header, raw, cols):
    segs = []
    for r in raw:
        vals = {k: clean_num(r.get(cols[k])) for k in VALUE_COLUMNS}
        if None in vals.values():
            return (
                None,
                f"Segment '{r.get(cols['segment'])}' is missing a unit or rate value.",
            )
        segs.append({"segment": str(r.get(cols["segment"], "")).strip(), **vals})
    if not segs:
        return None, f"No segment rows found. Columns seen: {header}"
    return segs, None


def _segment_effects(s_, totals):
    total_au, total_cu, comp_avg_rate = totals
    comp_share = s_["comparison_units"] / total_cu if total_cu else 0.0
    act_share = s_["actual_units"] / total_au if total_au else 0.0
    shift_units = (act_share - comp_share) * total_au
    return {
        "segment": s_["segment"],
        "volume": (total_au - total_cu) * comp_share * s_["comparison_rate"],
        "mix": shift_units * s_["comparison_rate"],
        "rate": (s_["actual_rate"] - s_["comparison_rate"]) * s_["actual_units"],
        "total": s_["actual_units"] * s_["actual_rate"]
        - s_["comparison_units"] * s_["comparison_rate"],
        # For reading a segment's mix sign: share shift valued against the average comparison rate.
        "mix_vs_avg": shift_units * (s_["comparison_rate"] - comp_avg_rate),
    }


def rvm(text):
    """Split a segment table's variance into volume, mix and rate, and report whether they sum to the total."""
    header, raw = parse_table(text)
    cols = {k: find_col(header, k) for k in RVM_COLUMNS}
    missing = [k for k, v in cols.items() if not v]
    if missing:
        return _fail(
            f"Missing columns for rate, volume, and mix: {missing}. Columns seen: {header}"
        )
    segs, error = _read_segments(header, raw, cols)
    if error:
        return _fail(error)
    total_au = sum(s["actual_units"] for s in segs)
    total_cu = sum(s["comparison_units"] for s in segs)
    comp_avg_rate = (
        sum(s["comparison_units"] * s["comparison_rate"] for s in segs) / total_cu
        if total_cu
        else 0.0
    )
    out = [_segment_effects(s_, (total_au, total_cu, comp_avg_rate)) for s_ in segs]
    sums = {k: sum(o[k] for o in out) for k in ("volume", "mix", "rate", "total")}
    check_total = sums["volume"] + sums["mix"] + sums["rate"]
    allowed = IDENTITY_TOLERANCE * max(1.0, abs(sums["total"]), abs(check_total))
    return {
        "status": "PASS" if abs(check_total - sums["total"]) <= allowed else "FAIL",
        "segments": out,
        "totals": sums,
        "note": NOTE,
    }
