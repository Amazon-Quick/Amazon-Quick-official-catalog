#!/usr/bin/env python3
"""
description: Build the report's CSV issue list and Excel checklist downloads.
last_updated: 2026-11-24

render_downloads.py - the issue rows and the two downloads embedded in the report.
"""

from __future__ import annotations

import base64
import csv
import io
import urllib.parse
from pathlib import Path

from render_format import E, readable
from render_taxonomy import AREAS, NOT_AN_ATTESTATION, SEV_LABEL, tab_of


def issue_rows(findings, change_of, status_of):
    rows = []
    for f in findings:
        ch = change_of.get(f["id"])
        st = (status_of.get(ch["n"]) or {}).get("status") if ch else None
        rows.append(
            {
                "id": f["id"],
                "severity": SEV_LABEL[f["severity"]],
                "area": dict(AREAS).get(tab_of(f), f["group"]),
                "group": f["group"],
                "basis": "Question (AI judgment)"
                if f.get("basis") == "judgment"
                else "Verified",
                "question": f.get("question", ""),
                "sheet": f.get("sheet") or "",
                "cell": f.get("cell") or "",
                "label": f.get("label") or "",
                "what": readable(f["description"]),
                "fix": f["fix"],
                "change": ch["n"] if ch else "",
                "change_status": (
                    "Applied in the copy"
                    if st == "applied"
                    else "Skipped"
                    if st == "skipped"
                    else (
                        "Proposed (safe)"
                        if ch["risk"] == "safe"
                        else "Proposed (confirm first)"
                    )
                )
                if ch
                else (
                    "Ask the owner"
                    if f.get("basis") == "judgment"
                    else "Needs a person"
                ),
                "status": "Fixed in copy" if st == "applied" else "Open",
            }
        )
    return rows


def csv_link(rows, name):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "ID",
            "Severity",
            "Basis",
            "Area",
            "Group",
            "Tab",
            "Cell",
            "Line item",
            "What's wrong",
            "Question for the owner",
            "How to fix",
            "Change #",
            "Change status",
            "Status",
        ]
    )
    for r in rows:
        w.writerow(
            [
                "'" + value
                if isinstance(value, str)
                and value.startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
                for value in [
                    r["id"],
                    r["severity"],
                    r["basis"],
                    r["area"],
                    r["group"],
                    r["sheet"],
                    r["cell"],
                    r["label"],
                    r["what"],
                    r["question"],
                    r["fix"],
                    r["change"],
                    r["change_status"],
                    r["status"],
                ]
            ]
        )
    href = "data:text/csv;charset=utf-8," + urllib.parse.quote(
        "\ufeff" + buf.getvalue()
    )
    return f'<a class="btn" download="{E(Path(name).stem)}_issues.csv" href="{href}">Issue list (CSV)</a>'


def xlsx_link(rows, name, generated, headline=""):
    """An Excel checklist of every issue (status, owner, links to each cell) plus a sign-off sheet."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.worksheet.datavalidation import DataValidation
    except Exception:
        return ""
    wb = Workbook()
    ws = wb.active
    ws.title = "Issues"
    head = [
        "Status",
        "Severity",
        "Basis",
        "Area",
        "Tab",
        "Cell",
        "Line item",
        "What's wrong",
        "Question for the owner",
        "How to fix",
        "Change #",
        "Change status",
        "Owner",
        "Due",
        "Notes",
        "ID",
    ]
    ws.append(head)
    widths = [15, 11, 14, 20, 16, 12, 26, 60, 44, 52, 10, 22, 16, 12, 30, 8]
    for i, wdt in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = wdt
    hdr_fill = PatternFill("solid", fgColor="F3F4F6")
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = hdr_fill
        c.alignment = Alignment(vertical="center")
    sev_fill = {
        "Critical": PatternFill("solid", fgColor="FDE8E8"),
        "Warning": PatternFill("solid", fgColor="FEF3E2"),
        "Suggestion": PatternFill("solid", fgColor="EAF1FE"),
    }
    q_fill = PatternFill("solid", fgColor="F3E8FF")
    # Cell links open the model next to this file; only a plain file name, never a URL or a path.
    link_ok = bool(name) and Path(name).name == name and ":" not in name
    for r in rows:
        ws.append(
            [
                r["status"],
                r["severity"],
                r["basis"],
                r["area"],
                r["sheet"],
                r["cell"],
                r["label"],
                r["what"],
                r["question"],
                r["fix"],
                r["change"],
                r["change_status"],
                "",
                "",
                "",
                r["id"],
            ]
        )
        i = ws.max_row
        ws.cell(i, 2).fill = sev_fill.get(r["severity"], hdr_fill)
        if r["question"]:
            ws.cell(i, 3).fill = q_fill
        for col in (7, 8, 9, 10, 15):
            ws.cell(i, col).alignment = Alignment(wrap_text=True, vertical="top")
        if r["sheet"] and r["cell"] and link_ok:
            c = ws.cell(i, 6)
            c.hyperlink = name
            sheet_ref = r["sheet"].replace("'", "''")
            c.hyperlink.location = f"'{sheet_ref}'!{r['cell'].split(':')[0]}"
            c.font = Font(color="2563EB", underline="single")
    dv = DataValidation(
        type="list",
        formula1='"Open,In progress,Fixed in copy,Done,Confirmed OK,Won\'t fix"',
        allow_blank=True,
    )
    ws.add_data_validation(dv)
    if rows:
        dv.add(f"A2:A{len(rows) + 1}")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = (
        f"A1:{ws.cell(1, len(head)).column_letter}{max(1, len(rows) + 1)}"
    )
    so = wb.create_sheet("Sign-off", 0)
    so.column_dimensions["A"].width, so.column_dimensions["B"].width = 26, 70
    crit = sum(
        1
        for r in rows
        if r["severity"] == "Critical"
        and r["basis"] == "Verified"
        and r["status"] != "Fixed in copy"
    )
    warn = sum(
        1
        for r in rows
        if r["severity"] == "Warning"
        and r["basis"] == "Verified"
        and r["status"] != "Fixed in copy"
    )
    qs = sum(
        1
        for r in rows
        if r["basis"] == "Question (AI judgment)" and r["status"] != "Fixed in copy"
    )
    for line in [
        ("Spreadsheet evaluation: sign-off", ""),
        ("Workbook", name),
        ("Audited", generated),
        ("Automated summary", headline),
        ("Open verified issues", f"{crit} critical, {warn} warning"),
        ("Open questions for the owner", qs),
        ("", ""),
        ("Model owner", ""),
        ("Reviewer", ""),
        ("Review date", ""),
        ("Decision", ""),
        ("Conditions / notes", ""),
        ("", ""),
        (
            "Important",
            "Automated checks test formulas, arithmetic and data in the scanned range; questions are AI judgment. "
            "This checklist doesn't certify the numbers: the people above do. "
            + NOT_AN_ATTESTATION,
        ),
    ]:
        so.append(list(line))
    so["A1"].font = Font(bold=True, size=14)
    for c in so["A"][1:]:
        c.font = Font(bold=True)
    entry = PatternFill("solid", fgColor="FFF8DB")
    for rr_ in range(8, 13):
        so.cell(rr_, 2).fill = entry
    so["B14"].alignment = Alignment(wrap_text=True, vertical="top")
    dv2 = DataValidation(
        type="list",
        formula1='"Approved,Approved after changes,Not approved"',
        allow_blank=True,
    )
    so.add_data_validation(dv2)
    dv2.add("B11")
    about = wb.create_sheet("About")
    for line in [
        ("Model", name),
        ("Audited", generated),
        ("Issues", len(rows)),
        ("", ""),
        (
            "Basis",
            "Verified = found by an exact check. Question (AI judgment) = worth asking the owner, not proof of an error.",
        ),
        ("Status", "Pick a status per issue; filter on any column."),
        (
            "Links",
            f"The Cell links open the model when this file is saved in the same folder as {name}.",
        ),
        (
            "Confidential",
            "Contains labels from the model. Share it as you would the model.",
        ),
    ]:
        about.append(list(line))
    about.column_dimensions["A"].width, about.column_dimensions["B"].width = 14, 90
    for c in about["A"]:
        c.font = Font(bold=True)
    # Workbook values are report data, even when Excel would infer a formula.
    for sheet in wb:
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
    buf = io.BytesIO()
    wb.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return (
        f'<a class="btn primary" download="{E(Path(name).stem)}_issues.xlsx" '
        f'href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}">Issue checklist (Excel)</a>'
    )
