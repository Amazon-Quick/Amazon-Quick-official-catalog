"""
description: Planned table changes: extend a table over rows below it, and point fixed ranges at table columns.
last_updated: 2026-11-24
"""

from __future__ import annotations

import scan_workbook as S
from openpyxl.utils import get_column_letter
from plan_common import a1, cells_of, short


def table_for(p, sheet, box):
    s = p.wb.sheets[sheet]
    for name, t in s.ws.tables.items():
        tb = S.parse_box(t.ref if hasattr(t, "ref") else t)
        if tb[0] <= box[0] and box[2] <= tb[2]:
            return name, tb, s.ws.tables[name]
    return None


def resize_table(p, f):
    c1, r1, c2, r2 = S.parse_box(f["cell"])
    hit = table_for(p, f["sheet"], (c1, r1, c2, r2))
    if not hit:
        return p.needs_you(f)
    name, tb, _ = hit
    new = f"{get_column_letter(tb[0])}{tb[1]}:{get_column_letter(tb[2])}{r2}"
    p.add(
        [f["id"]],
        f["sheet"],
        f["cell"],
        "table",
        "confirm",
        f"Extend table {S.data_text(name)} to row {r2} so it includes the {r2 - tb[3]} rows below it",
        [{"op": "table_ref", "sheet": f["sheet"], "table": name, "ref": new}],
    )
    p.table_resized[name] = r2


def structured_ref(p, f):
    s = p.wb.sheets[f["sheet"]]
    edits, sample = [], None
    for r, c in cells_of(f["cell"]) or []:
        x = s.cells.get((r, c))
        if not x or not x.formula or (s.name, r, c) in p.claimed:
            continue
        new, last, changed = [], 0, False
        for sh, box, s0, e0, _ref in S.refs_in(x.formula):
            tgt = p.wb.resolve(sh) if sh else s.name
            if not tgt or box[0] != box[2]:
                continue
            hit = table_for(p, tgt, box)
            if not hit:
                continue
            name, tb, tobj = hit
            if box[1] != tb[1] + 1 or box[3] != tb[3]:
                continue
            header = p.wb.sheets[tgt].cells.get((tb[1], box[0]))
            if not header or not isinstance(header.raw, str):
                continue
            col = (
                header.raw.replace("'", "''")
                .replace("[", "'[")
                .replace("]", "']")
                .replace("#", "'#")
            )
            new.append(x.formula[last:s0] + f"{name}[{col}]")
            last, changed = e0, True
        if changed:
            new.append(x.formula[last:])
            edits.append(
                {
                    "op": "cell",
                    "sheet": s.name,
                    "cell": a1(r, c),
                    "formula": "".join(new),
                }
            )
            sample = sample or (x.formula, "".join(new))
    if not edits:
        return p.needs_you(f)
    grown = p.table_resized
    p.add(
        [f["id"]],
        s.name,
        f["cell"],
        "formula",
        "confirm",
        f"{short(sample[0])} → {short(sample[1])} (grows with the table"
        + (
            ", and picks up the added rows, so the result will change)"
            if grown
            else ")"
        ),
        edits,
    )
