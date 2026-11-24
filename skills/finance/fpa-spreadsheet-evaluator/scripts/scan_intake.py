"""
description: Intake questions for the workbook scan: coverage, header rows, date order and units the user has to confirm.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import datetime as dt

from openpyxl.utils import get_column_letter
from scan_findings import data_text
from scan_formats import DATE_TEXT


def date_options(text):
    """Return every valid date interpretation. No locale is silently preferred."""
    options = {}
    for name, formats in {
        "ISO": (
            "%Y-%m-%d",
            "%d-%b-%Y",
            "%d-%b-%y",
            "%b %d, %Y",
            "%b %d %Y",
            "%b-%d-%Y",
        ),
        "MDY": ("%m/%d/%Y", "%m/%d/%y"),
        "DMY": ("%d/%m/%Y", "%d/%m/%y"),
    }.items():
        for fmt in formats:
            try:
                options[name] = dt.datetime.strptime(text.strip(), fmt)
                break
            except ValueError:
                pass
    return options


def assess_intake(wb, findings, context):
    """Keep unresolved meaning separate from exact cell/formula checks."""
    questions, coverage = [], []
    for s in wb.sheets.values():
        loaded = len(s.cells)
        # Private openpyxl 3.1 attribute, as in Workbook._load_sheets.
        source_filled = sum(c.value is not None for c in s.ws._cells.values())
        coverage.append(
            {
                "sheet": s.name,
                "header_row": s.header_row,
                "filled_rows_scanned": len(s.rows),
                "filled_cells_scanned": loaded,
                "unscanned_filled_cells": max(0, source_filled - loaded),
                "pre_header_rows": sorted(r for r in s.rows if r < s.header_row),
                "note": "All loaded cells, including title/footer/total rows, remain available to applicable checks; no transaction rows are dropped.",
            }
        )
        if source_filled > loaded:
            questions.append(
                {
                    "kind": "coverage",
                    "id": "coverage:" + s.name,
                    "cells": [],
                    "question": f"Tab {data_text(s.name)}: {source_filled - loaded} filled cells are outside the scan. Can you provide smaller workbooks covering those cells?",
                    "blocks": "Full-workbook conclusions",
                }
            )
        if len(s.header_candidates) > 1 and s.name not in context.get("headers", {}):
            questions.append(
                {
                    "kind": "header",
                    "id": "header:" + s.name,
                    "cells": [f"{s.name}!A{r}" for r in s.header_candidates],
                    "question": f"Tab {data_text(s.name)}: rows {s.header_candidates} could be field headings. Which row labels the data, or are these separate tables?",
                    "blocks": "Header-dependent interpretation",
                }
            )
        ambiguous = {}
        invalid = []
        conflicts = []
        for x in s.cells.values():
            if x.formula or not isinstance(x.raw, str) or not DATE_TEXT.match(x.raw):
                continue
            opts = date_options(x.raw)
            address = f"{s.name}!{x.coord}"
            order = context.get("date_order", {}).get(s.name)
            if not opts:
                invalid.append(address)
            elif "/" in x.raw and order in ("DMY", "MDY") and order not in opts:
                conflicts.append(address)
            elif len(set(opts.values())) > 1:
                if order not in opts:
                    ambiguous.setdefault(x.c, []).append((address, x.raw, opts))
        for col, values in ambiguous.items():
            example = values[0]
            a, b = example[2]["DMY"], example[2]["MDY"]
            questions.append(
                {
                    "kind": "date_order",
                    "id": f"date:{s.name}:{get_column_letter(col)}",
                    "cells": [v[0] for v in values],
                    "question": f"Cell {data_text(example[0])} is {data_text(example[1])}: does it mean {a.day} {a.strftime('%B')} (day/month/year) or {b.strftime('%B')} {b.day} (month/day/year)?",
                    "options": ["DMY", "MDY", "Mixed or unknown"],
                    "blocks": "Date conversion and date-dependent conclusions",
                }
            )
        if invalid:
            questions.append(
                {
                    "kind": "invalid_date",
                    "id": "invalid-date:" + s.name,
                    "cells": invalid,
                    "question": f"Cell {data_text(invalid[0])} has a date that cannot be read. What date should it be? These cells remain in the audit; they are not missing periods.",
                    "blocks": "Date-dependent conclusions; provide a corrected copy",
                }
            )
        if conflicts:
            questions.append(
                {
                    "kind": "date_order_conflict",
                    "id": "date-conflict:" + s.name,
                    "cells": conflicts,
                    "question": f"Cell {data_text(conflicts[0])} is incompatible with the confirmed date order. Are date formats mixed? Please provide consistent dates before conversion.",
                    "blocks": "Date-dependent conclusions and conversion",
                }
            )
        unit_findings = [
            f
            for f in findings
            if f.get("sheet") == s.name
            and f["check"]
            in ("mixed_units", "mixed_units_in_formula", "mixed_currency")
        ]
        if (
            unit_findings
            and not str(context.get("unit_notes", {}).get(s.name, "")).strip()
        ):
            questions.append(
                {
                    "kind": "units",
                    "id": "units:" + s.name,
                    "cells": [
                        f"{s.name}!{f['cell']}" for f in unit_findings if f.get("cell")
                    ],
                    "question": f"Tab {data_text(s.name)} shows different unit scales or currencies ({unit_findings[0]['description']}). What units are stored, and are the different displays intentional?",
                    "blocks": "Unit-dependent impact amounts and format changes",
                }
            )
    return {
        "status": "needs_clarification" if questions else "ready",
        "questions": questions,
        "coverage": coverage,
        "confirmed_context": context,
    }
