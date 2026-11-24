#!/usr/bin/env python3
"""
description: Draw the tab map (inline SVG) and the plain-text link summary for the review report.
last_updated: 2026-11-24

render_map.py - how the tabs feed each other, as an inline SVG and as text.
"""

from __future__ import annotations

import math
from collections import defaultdict

from render_format import E, pl
from render_taxonomy import ROLE_LABEL

EXT_NODE = "[other files]"  # '[' can't appear in a tab name, so this never clashes


def layout(sheets, edges, ext):
    """Left-to-right layers: a tab sits one column right of everything that feeds it."""
    names = [s["sheet"] for s in sheets]
    preds = defaultdict(set)
    for e in edges:
        if e["from"] in names and e["to"] in names and e["from"] != e["to"]:
            preds[e["to"]].add(e["from"])
    for t in ext or []:
        preds[t].add(EXT_NODE)
    level = {}

    def lv(n, seen=()):
        if n in level:
            return level[n]
        if n in seen:
            return 0
        level[n] = 0 if not preds[n] else 1 + max(lv(p, seen + (n,)) for p in preds[n])
        return level[n]

    linked = {e["from"] for e in edges} | {e["to"] for e in edges} | set(ext)
    for n in names:
        if n in linked:
            lv(n)
    if ext:
        level[EXT_NODE] = 0
    cols = defaultdict(list)
    for n in names:
        if n in level:
            cols[level[n]].append(n)
    if ext:
        cols[0].insert(0, EXT_NODE)
    lone = [n for n in names if n not in level]
    return cols, lone


def svg_map(scan, by_sheet):
    sheets = scan["sheets"]
    info = {s["sheet"]: s for s in sheets}
    edges = scan.get("map", {}).get("edges", [])
    ext_tabs = sorted(
        {
            f["sheet"]
            for f in scan["findings"]
            if f["check"] == "external_link" and f.get("sheet")
        }
    )
    cols, lone = layout(sheets, edges, ext_tabs)
    W, H, GX, GY, PAD = 214, 76, 120, 26, 24
    pos = {}
    ncols = (max(cols) + 1) if cols else 0
    for c, ns in cols.items():
        for i, n in enumerate(ns):
            pos[n] = (PAD + c * (W + GX), PAD + i * (H + GY))
    lone_x = PAD + ncols * (W + GX) if cols else PAD
    for i, n in enumerate(lone):
        pos[n] = (lone_x, PAD + 22 + i * (H + GY))
    width = max((x for x, _ in pos.values()), default=0) + W + PAD
    height = max((y for _, y in pos.values()), default=0) + H + PAD
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="How the tabs feed each other">',
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path class="m-arrow" d="M0,0 L10,5 L0,10 z"/></marker></defs>',
    ]
    if lone:
        out.append(
            f'<text class="m-lab" x="{lone_x}" y="{PAD + 10}">Not linked to other tabs</text>'
        )
    for e in list(edges) + [{"from": EXT_NODE, "to": t, "refs": 1} for t in ext_tabs]:
        if e["from"] not in pos or e["to"] not in pos or e["from"] == e["to"]:
            continue
        (x1, y1), (x2, y2) = pos[e["from"]], pos[e["to"]]
        sx, sy, tx, ty = x1 + W, y1 + H / 2, x2, y2 + H / 2
        if tx < sx:  # backwards link: route from the left side
            sx, tx = x1, x2 + W
        mx = (sx + tx) / 2
        sw = 1.4 + min(5, math.log10(e["refs"] + 1) * 1.6)
        dash = ' stroke-dasharray="5 4"' if e["from"] == EXT_NODE else ""
        out.append(
            f'<path class="m-edge" d="M{sx},{sy} C{mx},{sy} {mx},{ty} {tx - 2},{ty}" stroke-width="{sw:.1f}"{dash} marker-end="url(#arr)">'
            f"<title>{E(e['from'] if e['from'] != EXT_NODE else 'Other files')} → {E(e['to'])}: {pl(e['refs'], 'formula')}</title></path>"
        )
        if e["from"] != EXT_NODE:
            out.append(
                f'<text class="m-lab" x="{mx}" y="{(sy + ty) / 2 - 6}" text-anchor="middle">{e["refs"]:,}</text>'
            )
    for n, (x, y) in pos.items():
        sev = by_sheet.get(n, {})
        if n == EXT_NODE:
            role, title, sub, dash = (
                "external",
                "Other files",
                "linked workbooks",
                ' stroke-dasharray="6 4"',
            )
        else:
            s = info[n]
            role = s["role"] if s["role"] in ROLE_LABEL else "calculation"
            hidden = s["state"] != "visible"
            dash = ' stroke-dasharray="6 4"' if hidden else ""
            title = n if len(n) <= 24 else n[:23] + "…"
            sub = f"{ROLE_LABEL[role]}{' · hidden' if hidden else ''} · {pl(s['rows'], 'row')} · {pl(s['formulas'], 'formula')}"
        crit = " m-crit" if sev.get("critical") else ""
        out.append(
            f'<g class="m-node m-{role}{crit}"><rect x="{x}" y="{y}" width="{W}" height="{H}" rx="10"{dash}/>'
            f'<text class="m-t1" x="{x + 14}" y="{y + 30}">{E(title)}</text>'
            f'<text class="m-t2" x="{x + 14}" y="{y + 52}">{E(sub)}</text>'
        )
        n_issue = sev.get("critical", 0) + sev.get("warning", 0)
        if n_issue:
            out.append(
                f'<circle class="m-badge{" crit" if sev.get("critical") else ""}" cx="{x + W - 6}" cy="{y + 6}" r="12"/>'
                f'<text class="m-btx" x="{x + W - 6}" y="{y + 10}" text-anchor="middle">{n_issue}</text>'
                f"<title>{sev.get('critical', 0)} critical, {sev.get('warning', 0)} warning</title>"
            )
        out.append("</g>")
    out.append("</svg>")
    return "".join(out)


def flow_text(scan):
    hidden = {s["sheet"] for s in scan["sheets"] if s["state"] != "visible"}
    by_to = defaultdict(list)
    for e in scan.get("map", {}).get("edges", []):
        by_to[e["to"]].append(e["from"] + (" (hidden)" if e["from"] in hidden else ""))
    return "; ".join(f"{E(', '.join(srcs))} → {E(t)}" for t, srcs in by_to.items())


def excel_line(scan):
    xl = scan.get("excel", {})
    eff, setting = xl.get("effective_target"), xl.get("target_setting", "auto")
    name = {
        "365": "Microsoft 365",
        "2021": "Excel 2021 or Microsoft 365",
        "2019": "Excel 2019",
        "2016": "Excel 2016",
        "compatible": "Any version (most compatible fixes)",
    }.get(eff, "Not set")
    how = (
        "set by the user"
        if setting != "auto"
        else (
            "detected from functions in the file"
            if xl.get("file_needs_at_least") in ("2021", "365")
            else "not detected, so fixes work in every version"
        )
    )
    return f"{name} ({how})"
