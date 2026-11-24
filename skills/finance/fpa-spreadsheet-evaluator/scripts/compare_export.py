#!/usr/bin/env python3
"""
description: Build the comparison report's Excel change log download.
last_updated: 2026-11-24

compare_export.py - every change, flag and new issue as an Excel sheet, embedded in the report.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import render_report as RR


def _change_log_link(res, generated):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except Exception:
        return ""
    wb = Workbook()
    ws = wb.active
    ws.title = "Changes"
    ws.append(
        [
            "Type",
            "Tab",
            "Where (new version)",
            "Line item",
            "Before",
            "After",
            "Cells",
            "Flag",
            "Reviewer note",
        ]
    )
    for c, w in zip("ABCDEFGHI", (22, 18, 20, 32, 40, 40, 8, 50, 30), strict=False):
        ws.column_dimensions[c].width = w
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="F3F4F6")
    flag_at = {
        (f["sheet"], f.get("cell")): RR.readable(f["text"]) for f in res["flags"]
    }
    for e in res["assumptions"]:
        ws.append(
            [
                "Input changed",
                e["sheet"],
                e["cell"],
                e["label"],
                e["before"],
                e["after"],
                e["count"],
                flag_at.get((e["sheet"], e["cell"]), ""),
                "",
            ]
        )
    for e in res["formulas"]:
        ws.append(
            [
                "Formula changed",
                e["sheet"],
                e["cell"],
                e["label"],
                e["old"],
                e["new"],
                e["count"],
                flag_at.get((e["sheet"], e["cell"]), ""),
                "",
            ]
        )
    for e in res["to_value"]:
        ws.append(
            [
                "Formula to typed number",
                e["sheet"],
                e["cell"],
                e["label"],
                e["old"],
                e["new"],
                1,
                flag_at.get((e["sheet"], e["cell"]), ""),
                "",
            ]
        )
    for e in res["to_formula"]:
        ws.append(
            [
                "Typed number to formula",
                e["sheet"],
                e["cell"],
                e["label"],
                e["old"],
                e["new"],
                1,
                "",
                "",
            ]
        )
    for sh, st in res["structure"].items():
        for lab in st.get("rows_added", []):
            ws.append(["Row added", sh, "", lab, "", "", "", "", ""])
        for lab in st.get("rows_removed", []):
            ws.append(["Row removed", sh, "", lab, "", "", "", "", ""])
    for f in res["introduced"]:
        ws.append(
            [
                "New issue",
                f.get("sheet") or "",
                f.get("cell") or "",
                f.get("label", ""),
                "",
                RR.readable(f["description"]),
                "",
                "",
                "",
            ]
        )
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:I{max(1, ws.max_row)}"
    about = wb.create_sheet("About")
    for line in [
        ("Old version", res["old"]),
        ("New version", res["new"]),
        ("Compared", generated),
        (
            "Important",
            "Automated comparison; flags marked as judgment are worth a question, not proof of an error.",
        ),
    ]:
        about.append(list(line))
    about.column_dimensions["A"].width, about.column_dimensions["B"].width = 14, 90
    # Preserve formula Before/After text without making it executable.
    for sheet in wb:
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
    buf = io.BytesIO()
    wb.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    stem = Path(res["new"]).stem
    return (
        f'<a class="btn primary" download="{RR.E(stem)}_change_log.xlsx" '
        f'href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}">Change log (Excel)</a>'
    )
