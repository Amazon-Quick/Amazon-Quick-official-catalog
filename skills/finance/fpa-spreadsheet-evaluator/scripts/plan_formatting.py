"""
description: Planned formatting changes: copy a neighbor's format so a cell's style matches its role, decimals or percent display.
last_updated: 2026-11-24
"""

from __future__ import annotations

import scan_workbook as S
from plan_common import a1, cells_of, nearest


def copy_style(p, f, ok, prefer=None, explain="Match the formatting of"):
    s = p.wb.sheets[f["sheet"]]
    pts = cells_of(f["cell"])
    if pts is None:
        return p.needs_you(f)
    edits, srcs = [], []
    for r, c in pts:
        x = s.cells.get((r, c))
        if not x or (s.name, r, c) in p.claimed:
            continue
        fits = ok(x)
        src = nearest(
            s,
            r,
            c,
            lambda y, fits=fits: (
                fits(y) and (f["check"], s.name, y.r, y.c) not in p.flagged
            ),
            prefer and prefer(x),
        )
        if not src:
            continue
        edits.append(
            {
                "op": "cell",
                "sheet": s.name,
                "cell": a1(r, c),
                "style_from": src.coord,
            }
        )
        srcs.append(src)
    if not edits:
        return None if p.is_claimed(s.name, pts) else p.needs_you(f)
    src = srcs[0]
    fmt_note = ""
    x0 = s.cells.get(
        (S.parse_box(edits[0]["cell"])[1], S.parse_box(edits[0]["cell"])[0])
    )
    if x0 and x0.fmt != src.fmt and f["check"] not in ("mixed_units", "mixed_decimals"):
        fmt_note = f"; also sets number format to {src.fmt}"
    p.add(
        [f["id"]],
        s.name,
        f["cell"],
        "format",
        "safe",
        f"{explain} {src.coord}"
        + (f" ({len(edits)} cells)" if len(edits) > 1 else "")
        + fmt_note,
        edits,
    )


def role_ok(p, role):
    want = p.conv.get(role, {})

    def ok(target):
        def inner(y):
            if role == "input":
                is_role = not y.formula and S.is_num(y.raw)
            elif role == "link":
                is_role = bool(y.formula and (y.links - {"[external]"}))
            else:
                is_role = bool(y.formula and not (y.links - {"[external]"}))
            return is_role and all(getattr(y, a) == v for a, v in want.items())

        return inner

    return ok


def fix_input_style(p, f):
    """Style a cell like the model's other inputs."""

    def same_fmt(x):
        return lambda y: y.fmt == x.fmt

    return copy_style(
        p,
        f,
        role_ok(p, "input"),
        same_fmt,
        "Style like the model's other inputs: copy format from",
    )


def fix_formula_styled_as_input(p, f):
    """Style a formula like the model's other formulas."""
    s = p.wb.sheets[f["sheet"]]
    pts = cells_of(f["cell"]) or []
    x = s.cells.get(pts[0]) if pts else None
    role = (
        "link"
        if x and x.links and (x.links - {"[external]"}) and "link" in p.conv
        else "formula"
    )

    def same_fmt(x):
        return lambda y: y.fmt == x.fmt

    return copy_style(
        p, f, role_ok(p, role), same_fmt, "Style as a formula: copy format from"
    )


def fix_link_style(p, f):
    """Style a cross-tab formula like the others."""

    def same_fmt(x):
        return lambda y: y.fmt == x.fmt

    return copy_style(
        p,
        f,
        role_ok(p, "link"),
        same_fmt,
        "Style like the other cross-tab formulas: copy format from",
    )


def fix_total_style(p, f):
    """Style a total like the tab's other total rows."""
    s = p.wb.sheets[f["sheet"]]
    pts = cells_of(f["cell"]) or []
    bad_r = pts[0][0] if pts else 0

    def ok(x):
        return lambda y: (
            y.c == x.c
            and y.r != bad_r
            and y.bold
            and (y.formula or S.is_num(y.raw))
            and (y.top or y.bottom)
            and y.r > s.header_row
        )

    return copy_style(
        p, f, ok, None, "Style like the tab's other total rows: copy format from"
    )


def fix_mixed_units(p, f):
    """Units are the owner's call."""
    return p.needs_you(
        f,
        "Confirm the stored units and intended display scale; copying a neighbor's format could misrepresent the amount.",
    )


def fix_mixed_decimals(p, f):
    """Match the neighbors' decimal places."""

    def ok(x):
        bad = S.fmt_decimals(x.fmt)
        return lambda y: (
            S.is_num(y.cached)
            and S.fmt_decimals(y.fmt) not in (None, bad)
            and y.fill == x.fill
            and y.font == x.font
        )

    return copy_style(
        p, f, ok, None, "Match the neighbors' decimal places: copy format from"
    )


def fix_percent_format(p, f):
    """Show fractions as percentages."""
    s = p.wb.sheets[f["sheet"]]
    pts = cells_of(f["cell"])
    if pts is None:
        return p.needs_you(f)
    vals = [
        s.cells[p].cached for p in pts if p in s.cells and S.is_num(s.cells[p].cached)
    ]
    whole = all(abs(v * 100 - round(v * 100)) < 1e-9 for v in vals)
    fmt_id = 9 if whole else 10
    edits = [
        {"op": "cell", "sheet": s.name, "cell": a1(r, c), "numfmt_id": fmt_id}
        for r, c in pts
        if (r, c) in s.cells and p.format_free(s.name, r, c)
    ]
    if (
        not edits
    ):  # every cell is already owned by another change - don't list an empty one
        return p.needs_you(f)
    return p.add(
        [f["id"]],
        s.name,
        f["cell"],
        "format",
        "safe",
        f"Show as percentages ({'0%' if whole else '0.00%'}){f' ({len(edits)} cells)' if len(edits) > 1 else ''}",
        edits,
    )
