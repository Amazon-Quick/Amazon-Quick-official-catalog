"""
description: Finding records for the workbook scan: quoting workbook text, the findings list, and grouping cells into ranges.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import json
from collections import defaultdict

from openpyxl.utils import get_column_letter
from scan_catalog import CHECKS, JUDGMENT_CHECKS, area_of


def data_text(value, limit=40):
    """A workbook fragment for a description: clipped, JSON-quoted, controls escaped.
    The quotes mark it as file content; summary() and show() say that quoted text is data."""
    text = str(value)
    clipped = text[:limit] + ("..." if len(text) > limit else "")
    # Letters in any script stay readable; control, format (bidi, zero-width) and
    # line-separator characters are escaped so they can't reshape the text around them.
    quoted = json.dumps(clipped, ensure_ascii=False)
    return "".join(ch if ch.isprintable() else f"\\u{ord(ch):04x}" for ch in quoted)


class Findings:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, check, sheet, cell, description, severity=None, question=None):
        group, sev, fix = CHECKS[check]
        judgment = check in JUDGMENT_CHECKS
        sev = severity or sev
        if judgment and sev == "critical":
            sev = "warning"
        item = {
            "check": check,
            "group": group,
            "area": area_of(check, group),
            "severity": sev,
            "basis": "judgment" if judgment else "verified",
            "sheet": sheet,
            "cell": cell,
            "description": description,
            "fix": fix,
        }
        if question:
            item["question"] = question
        self.items.append(item)

    def has(self, check, sheet, r, c):
        return any(
            i["check"] == check
            and i["sheet"] == sheet
            and i.get("_cells")
            and (r, c) in i["_cells"]
            for i in self.items
        )


def rectangles(cells):
    """Merge (row, col) points into a few rectangular ranges."""
    by_row = defaultdict(list)
    for r, c in cells:
        by_row[r].append(c)
    segs = []
    for r in sorted(by_row):
        cs = sorted(set(by_row[r]))
        start = prev = cs[0]
        for c in cs[1:] + [None]:
            if c is not None and c == prev + 1:
                prev = c
                continue
            segs.append([r, start, r, prev])
            if c is not None:
                start = prev = c
    rects = []
    for r, c1, _, c2 in segs:
        for rc in rects:
            if rc[1] == c1 and rc[3] == c2 and rc[2] == r - 1:
                rc[2] = r
                break
        else:
            rects.append([r, c1, r, c2])
    return [
        f"{get_column_letter(c1)}{r1}"
        + ("" if (r1, c1) == (r2, c2) else f":{get_column_letter(c2)}{r2}")
        for r1, c1, r2, c2 in rects
    ]


def add_grouped(fs, check, sheet, points, describe):
    """points: {(r, c): key}; one finding per key per rectangle."""
    by_key = defaultdict(list)
    for rc, k in points.items():
        by_key[k].append(rc)
    for k, pts in by_key.items():
        for rng in rectangles(pts):
            fs.add(check, sheet, rng, describe(k, rng))
            fs.items[-1]["_cells"] = set(pts)
