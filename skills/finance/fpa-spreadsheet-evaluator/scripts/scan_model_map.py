"""
description: The workbook map for the scan: tab roles, links between tabs, key inputs and outputs, and the time horizon.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from openpyxl.utils import get_column_letter
from scan_formats import is_num
from scan_formula_text import refs_in
from scan_labels import _clip
from scan_load import Workbook


def sheet_map(wb: Workbook):
    feeds = defaultdict(set)
    for x in wb.formulas:
        for litem in x.links:
            feeds[x.sheet].add(litem)
    used_by = defaultdict(set)
    for s, srcs in feeds.items():
        for litem in srcs:
            used_by[litem].add(s)
    out = []
    for s in wb.sheets.values():
        n_f = sum(1 for x in s.cells.values() if x.formula)
        n_n = sum(1 for x in s.cells.values() if not x.formula and is_num(x.raw))
        n_t = sum(
            1 for x in s.cells.values() if not x.formula and isinstance(x.raw, str)
        )
        if s.is_data:
            role = "data"
        elif n_f == 0 and n_n == 0:
            role = "notes"
        elif n_f == 0 or n_n > n_f:
            role = "inputs"
        elif s.name not in used_by:
            role = "output"
        else:
            role = "calculation"
        out.append(
            {
                "sheet": s.name,
                "role": role,
                "state": s.ws.sheet_state,
                "rows": len(s.rows),
                "formulas": n_f,
                "typed_numbers": n_n,
                "text_cells": n_t,
                "reads_from": sorted(feeds.get(s.name, ())),
                "feeds": sorted(used_by.get(s.name, ())),
                "used_range": s.ws.dimensions,
            }
        )
    return out


PERIOD_RES = [
    (
        "Monthly",
        re.compile(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.I),
    ),
    ("Quarterly", re.compile(r"^(q[1-4]\b|[1-4]q\b)", re.I)),
    ("Annual", re.compile(r"^(fy\s?\d{1,4}|cy\s?\d{2,4}|20\d\d|19\d\d)$", re.I)),
]
OUTPUT_WORDS = re.compile(
    r"total|net|profit|income|ebit|margin|cash|summary|result|grand", re.I
)


def model_map(wb: Workbook) -> dict:
    edges = Counter()
    for x in wb.formulas:
        for litem in x.links:
            edges[(litem, x.sheet)] += 1
    used = Counter()
    referenced = set()
    for x in wb.formulas:
        for sh, box, *_ in refs_in(x.formula):
            tgt = wb.resolve(sh) if sh else x.sheet
            if not tgt or (box[2] - box[0] + 1) * (box[3] - box[1] + 1) > 400:
                continue
            for r in range(box[1], box[3] + 1):
                for c in range(box[0], box[2] + 1):
                    used[(tgt, r, c)] += 1
                    referenced.add((tgt, r, c))

    def label(s, x):
        row_lab = next(
            (
                s.cells[(x.r, c)].raw
                for c in range(x.c - 1, 0, -1)
                if (x.r, c) in s.cells
                and isinstance(s.cells[(x.r, c)].raw, str)
                and not s.cells[(x.r, c)].formula
            ),
            "",
        )
        h = s.cells.get((s.header_row, x.c))
        col_lab = h.raw if h and isinstance(h.raw, str) and h.r != x.r else ""
        return " / ".join(p for p in (str(row_lab).strip(), str(col_lab).strip()) if p)[
            :80
        ]

    def row_label(s, x):
        return next(
            (
                str(s.cells[(x.r, c)].raw).strip()
                for c in range(x.c - 1, 0, -1)
                if (x.r, c) in s.cells
                and isinstance(s.cells[(x.r, c)].raw, str)
                and not s.cells[(x.r, c)].formula
            ),
            "",
        ) or label(s, x)

    def grouped(items, limit):
        """Collapse one entry per period into one entry per row: 'Payroll, C7:N7'."""
        rows = {}
        for sh, x, extra in items:
            k = (sh, x.r)
            if k not in rows:
                rows[k] = {
                    "sheet": sh,
                    "label": row_label(wb.sheets[sh], x),
                    "cols": [],
                    "first": x,
                    **extra,
                }
            rows[k]["cols"].append(x.c)
            if "used_by" in extra:
                rows[k]["used_by"] = max(rows[k]["used_by"], extra["used_by"])
        out = []
        for g in rows.values():
            c1, c2, x = min(g["cols"]), max(g["cols"]), g.pop("first")
            g["cell"] = f"{get_column_letter(c1)}{x.r}" + (
                f":{get_column_letter(c2)}{x.r}" if c2 > c1 else ""
            )
            g["value"] = x.cached if x.formula else x.raw
            g["periods"] = len(g.pop("cols"))
            out.append(g)
        return out[:limit]

    raw_in = []
    for (sh, r, c), n in used.most_common():
        s = wb.sheets[sh]
        x = s.cells.get((r, c))
        if x and not x.formula and is_num(x.raw) and not s.is_data and r > s.header_row:
            raw_in.append((sh, x, {"used_by": n}))
    inputs = sorted(grouped(raw_in, 10_000), key=lambda g: -g["used_by"])[:10]
    raw_out = []
    for s in wb.sheets.values():
        if s.is_data or s.hidden:
            continue
        for x in sorted(s.cells.values(), key=lambda y: (y.r, y.c)):
            if (
                x.formula
                and (s.name, x.r, x.c) not in referenced
                and (x.bold or OUTPUT_WORDS.search(label(s, x)))
            ):
                raw_out.append((s.name, x, {}))
    outputs = grouped(raw_out, 10)
    horizon = ""
    calc = max(
        (s for s in wb.sheets.values() if not s.is_data),
        key=lambda s: sum(1 for x in s.cells.values() if x.formula),
        default=None,
    )
    if calc:
        hdr = [
            x
            for x in sorted(calc.cells.values(), key=lambda y: y.c)
            if x.r == calc.header_row and x.c > 1
        ]
        texts = [str(x.cached if x.cached is not None else x.raw).strip() for x in hdr]
        for name, rx in PERIOD_RES:
            hits = [t for t in texts if rx.search(t)]
            if len(hits) >= 2:
                horizon = f"{name}, {_clip(hits[0], 24)} - {_clip(hits[-1], 24)} ({len(hits)} periods, '{calc.name}' tab)"
                break
    return {
        "edges": [{"from": a, "to": b, "refs": n} for (a, b), n in edges.most_common()],
        "key_inputs": inputs,
        "key_outputs": outputs,
        "time_horizon": horizon,
    }
