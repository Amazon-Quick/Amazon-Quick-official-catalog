#!/usr/bin/env python3
"""
description: Work out what each proposed change does to the numbers, for the report.
last_updated: 2026-11-24

report_context.py - what each change does to the numbers, for the report.

  python3 report_context.py MODEL.xlsx SCAN.json CHANGES.json OUT_context.json
                            [--applied FIXED.xlsx] [--preview PREVIEW.xlsx] [--source "shown path"]
                            [--generated "11 Nov 2026, 5:03 PM PST"]

FIXED.xlsx / PREVIEW.xlsx must hold calculated results saved by Excel; without them the report
leaves out the before/after numbers.
  --applied   the fixed copy with the approved changes
  --preview   a scratch copy with every proposed change, used for "if applied" estimates
  --isolated  "1=preview_1.xlsx,4=preview_4.xlsx": copies with one change each (more precise estimates)
  --changelog the apply step's changelog JSON, so applied changes use FIXED.xlsx

Output (all optional for render_report.py):
  {"source": "...", "generated": "...",
   "changes": {"1": {"label": "Total cost · Q3", "old": "=SUM(D4:D4)", "new": "=SUM(D4:D5)", "cells": 1,
                     "values": [{"where": "Calc!D6", "label": "...", "before": 46305, "after": 46405}],
                     "basis": "applied" | "preview"}},
   "outputs": [{"label": "Total revenue", "where": "Summary!B1", "before": 822309,
                "applied": 816231, "preview": 816231}]}
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import openpyxl  # noqa: E402
import scan_workbook as S

MAX_VALUES = 3  # cells listed per change


def _values(path):
    if not path or not Path(path).exists():
        return None
    return openpyxl.load_workbook(path, data_only=True)


def _get(wb, sheet, ref):
    try:
        v = wb[sheet][ref.split(":")[0].replace("$", "")].value
    except Exception:
        return None
    return v


def _val(v):
    """Numbers and errors as-is; dates and short text as {"text", "kind"} for display."""
    if S.is_num(v) or (isinstance(v, str) and v.startswith("#")):
        return v
    if isinstance(v, (dt.datetime, dt.date)):
        return {"text": v.strftime("%d %b %Y"), "kind": "date"}
    if isinstance(v, str) and v and len(v) <= 30:
        return {"text": v, "kind": "text"}
    return None


def _num_or_err(v):
    if S.is_num(v):
        return v
    if isinstance(v, str) and v.startswith("#"):
        return v
    return None


def source_display(path):
    """How to show the user's file in the report: its file name only, never a folder or local path."""
    if not path:
        return ""
    return Path(str(path).replace("\\", "/")).name


def build(
    model,
    scan,
    plan,
    applied=None,
    preview=None,
    source=None,
    generated=None,
    changelog=None,
    isolated=None,
):
    """isolated: {change number: scratch copy with only that change, with saved results}."""
    wb = S.Workbook(Path(model))
    applied_wb, preview_wb = _values(applied), _values(preview)
    isolated = {str(k): v for k, v in (isolated or {}).items()}
    applied_ns = {
        r["n"]
        for r in (changelog or {}).get("results", [])
        if r.get("status") == "applied"
    }
    out = {
        "source": source_display(source),
        "generated": generated or "",
        "changes": {},
        "outputs": [],
    }
    for ch in (plan or {}).get("changes", []):
        info = {"label": "", "cells": 0, "values": []}
        sh = wb.sheets.get(ch.get("sheet") or "")
        if sh is not None and ch.get("target"):
            info["label"] = S.range_label(sh, ch["target"])
        cell_edits = [
            e
            for e in ch["edits"]
            if e.get("op") == "cell" and ("formula" in e or "value" in e)
        ]
        info["cells"] = len(cell_edits)
        if cell_edits:
            e = cell_edits[0]
            x = wb.cell(
                e["sheet"], S.parse_box(e["cell"])[1], S.parse_box(e["cell"])[0]
            )
            old = (x.formula or x.raw) if x else None
            new = e.get("formula", e.get("value"))
            converting = (
                isinstance(old, str)
                and not str(old).startswith("=")
                and not isinstance(new, str)
            )
            if (
                old is not None
                and new is not None
                and str(old) != str(new)
                and not converting
            ):
                info["old"], info["new"], info["where"] = (
                    str(old),
                    str(new),
                    f"{e['sheet']}!{e['cell']}",
                )
        if ch["n"] in applied_ns:
            basis, src = (
                ("applied", applied_wb) if applied_wb is not None else (None, None)
            )
        elif str(ch["n"]) in isolated:
            basis, src = "isolated", _values(isolated[str(ch["n"])])
        elif preview_wb is not None:
            basis, src = "combined", preview_wb
        else:
            basis, src = None, None
        if src is not None:
            for e in cell_edits:
                c, r = S.parse_box(e["cell"])[0], S.parse_box(e["cell"])[1]
                x = wb.cell(e["sheet"], r, c)
                before = _val(x.cached if x else None)
                after = _val(_get(src, e["sheet"], e["cell"]))
                if before is None and after is None:
                    continue
                if (
                    isinstance(before, dict)
                    and isinstance(after, dict)
                    and "old" in info
                ):
                    continue  # text in, text out (e.g. trimmed spaces): the comparison above shows it
                if before == after or (
                    S.is_num(before) and S.is_num(after) and abs(before - after) < 1e-9
                ):
                    continue
                s2 = wb.sheets.get(e["sheet"])
                info["values"].append(
                    {
                        "where": f"{e['sheet']}!{e['cell']}",
                        "label": S.range_label(s2, e["cell"]) if s2 else "",
                        "before": before,
                        "after": after,
                    }
                )
                if len(info["values"]) >= MAX_VALUES:
                    break
            info["basis"] = basis
        out["changes"][str(ch["n"])] = info
    for o in scan.get("map", {}).get("key_outputs", []):
        first = o["cell"].split(":")[0]
        row = {
            "label": o.get("label") or "",
            "where": f"{o['sheet']}!{o['cell']}",
            "before": _num_or_err(o.get("value")),
        }
        oc = wb.cell(o["sheet"], S.parse_box(first)[1], S.parse_box(first)[0])
        if oc is not None and "%" in S.fmt_section(oc.fmt or ""):
            row["pct"] = True
        if applied_wb is not None:
            row["applied"] = _num_or_err(_get(applied_wb, o["sheet"], first))
        if preview_wb is not None and len(applied_ns) < len(
            (plan or {}).get("changes", [])
        ):
            row["preview"] = _num_or_err(_get(preview_wb, o["sheet"], first))
        if o.get("periods", 1) > 1:
            row["note"] = "first period shown"
        out["outputs"].append(row)
    return out


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2

    def opt(k):
        return argv[argv.index(k) + 1] if k in argv else None

    scan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    plan = (
        json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        if Path(argv[2]).exists()
        else None
    )
    log_p = opt("--changelog")
    log = (
        json.loads(Path(log_p).read_text(encoding="utf-8"))
        if log_p and Path(log_p).exists()
        else None
    )
    iso = dict(
        x.split("=", 1) for x in (opt("--isolated") or "").split(",") if "=" in x
    )
    ctx = build(
        argv[0],
        scan,
        plan,
        opt("--applied"),
        opt("--preview"),
        opt("--source"),
        opt("--generated"),
        log,
        iso,
    )
    Path(argv[3]).write_text(json.dumps(ctx, indent=1, default=str), encoding="utf-8")
    print(f"Wrote {argv[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
