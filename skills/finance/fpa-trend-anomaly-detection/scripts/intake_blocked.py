"""
description: Build the needs-clarification result, its row counts, and the date question intake asks.
last_updated: 2026-11-24
"""

from __future__ import annotations

import re

from intake_cells import _untrusted


def _blocked(sheet, questions, row_audit=None, header_row=None, issues=None):
    """No analyzable series is exposed until the source ambiguity is resolved."""
    audit = row_audit or []
    unique = list(dict.fromkeys(questions))
    shown = unique[:10]
    if len(unique) > 10:
        shown.append(
            f"{len(unique) - 10} additional questions omitted "
            f"({len(unique)} total). See row_audit for all affected source rows."
        )
    return {
        "status": "needs_clarification",
        "series": {},
        "questions": shown,
        "sheet": sheet,
        "header_row": header_row,
        "provenance": {},
        "freq": None,
        "first_period": None,
        "last_actual": None,
        "skipped": [],
        "issues": issues or [],
        "notes": [],
        "overlaps": [],
        "row_audit": audit,
        "row_counts": _row_counts(audit),
    }


def _row_counts(audit):
    return {
        "source_rows": len(audit),
        **{
            status: sum(r["status"] == status for r in audit)
            for status in ("loaded", "excluded", "unresolved")
        },
    }


def _date_question(value, location):
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})", str(value).strip())
    if m and int(m[1]) != int(m[2]) and 1 <= int(m[1]) <= 12 and 1 <= int(m[2]) <= 12:
        return (
            f"{location} contains {_untrusted(value)}. "
            "Are these dates day/month/year or month/day/year? "
            "I have not assigned those rows to periods."
        )
    return (
        f"{location} contains an unreadable date ({_untrusted(value)}). "
        "What period does this row belong to, "
        "or should this specific row be excluded?"
    )
