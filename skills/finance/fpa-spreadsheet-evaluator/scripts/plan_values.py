"""
description: Planned value changes: turn numbers and dates stored as text into real values, and trim spaces in lookup keys.
last_updated: 2026-11-24
"""

from __future__ import annotations

import datetime as dt
import re

import scan_workbook as S
from plan_common import a1, cells_of, nearest


def text_to_value(p, f, kind):
    s = p.wb.sheets[f["sheet"]]
    edits = []
    for r, c in cells_of(f["cell"]) or []:
        x = s.cells.get((r, c))
        if not x or not isinstance(x.raw, str) or (s.name, r, c) in p.claimed:
            continue
        txt = x.raw.strip()
        if kind == "number":
            neg = txt.startswith("(") and txt.endswith(")") or txt.startswith("-")
            core = re.sub(r"[^\d.]", "", txt)
            try:
                v = float(core) * (-1 if neg else 1)
            except ValueError:
                continue
            v = v / 100 if txt.endswith("%") else v
            v = int(v) if v == int(v) else v
            like = nearest(
                s,
                r,
                c,
                lambda y, c=c: (
                    y.c == c and S.is_num(y.raw) and not y.is_date and not y.formula
                ),
            )
        else:
            opts = S.date_options(txt)
            order = (
                p.scan.get("intake", {})
                .get("confirmed_context", {})
                .get("date_order", {})
                .get(s.name)
            )
            if "/" in txt and order in ("DMY", "MDY") and order not in opts:
                return p.needs_you(
                    f,
                    f"{S.data_text(txt)} conflicts with the confirmed date order; ask for a consistent date.",
                )
            if len(set(opts.values())) > 1 and order not in opts:
                return p.needs_you(
                    f,
                    f"Confirm whether {S.data_text(txt)} is day/month/year or month/day/year before converting it.",
                )
            d = opts.get(order) if order in opts else next(iter(opts.values()), None)
            if d is None:
                return p.needs_you(
                    f,
                    f"Confirm the intended date for {S.data_text(txt)}; it was not converted.",
                )
            v = (d - dt.datetime(1899, 12, 30)).days
            like = nearest(
                s, r, c, lambda y, c=c: y.c == c and y.is_date and not y.formula
            )
        e = {"op": "cell", "sheet": s.name, "cell": a1(r, c), "value": v}
        if like:
            e["style_from"] = like.coord
        edits.append(e)
    if not edits:
        return p.needs_you(f)
    p.add(
        [f["id"]],
        s.name,
        f["cell"],
        "value",
        "safe",
        f"Convert {S.data_text(s.cells[S.parse_box(edits[0]['cell'])[1], S.parse_box(edits[0]['cell'])[0]].raw)} to a real "
        f"{'number' if kind == 'number' else 'date'}"
        + (f" ({len(edits)} cells)" if len(edits) > 1 else ""),
        edits,
    )


def fix_spaces(p, f):
    s = p.wb.sheets[f["sheet"]]
    edits = []
    for r, c in cells_of(f["cell"]) or []:
        x = s.cells.get((r, c))
        if x and isinstance(x.raw, str) and not x.formula and x.raw != x.raw.strip():
            edits.append(
                {
                    "op": "cell",
                    "sheet": s.name,
                    "cell": a1(r, c),
                    "value": x.raw.strip(),
                }
            )
    if not edits:
        return p.needs_you(f)
    p.add(
        [f["id"]],
        s.name,
        f["cell"],
        "value",
        "confirm",
        f"Remove extra spaces in {S.plural(len(edits), 'cell')}, for example {S.data_text(s.cells[S.parse_box(edits[0]['cell'])[1], S.parse_box(edits[0]['cell'])[0]].raw)} → {S.data_text(edits[0]['value'])} (lookups and SUMIFS will start matching them)",
        edits,
    )


def fix_text_in_sum_range(p, f):
    """Convert text cells inside a SUM range, unless a number_as_text change already does."""
    tcs = f.get("text_cells") or []
    if not tcs or any(tc["sheet"] != f["sheet"] for tc in tcs):
        return p.needs_you(f)
    pts = [S.parse_box(tc["cell"])[1::-1] for tc in tcs]  # (r, c)
    owners = {
        p.claimed[(f["sheet"], r, c)] for r, c in pts if (f["sheet"], r, c) in p.claimed
    }
    if owners and all((f["sheet"], r, c) in p.claimed for r, c in pts):
        for n in owners:  # the number_as_text changes already convert them
            p.changes[n - 1]["finding_ids"].append(f["id"])
        return None
    for r, c in pts:  # convert the rest, one cell each
        if (f["sheet"], r, c) not in p.claimed:
            text_to_value(p, dict(f, cell=a1(r, c)), "number")
    return None
