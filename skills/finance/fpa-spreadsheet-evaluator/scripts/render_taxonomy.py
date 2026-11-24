#!/usr/bin/env python3
"""
description: Severity, area and note names the report uses, and judgment rows from judgments.json.
last_updated: 2026-11-24

render_taxonomy.py - the report's labels and how findings map to its tabs.
"""

from __future__ import annotations

SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}
SEV_LABEL = {"critical": "Critical", "warning": "Warning", "info": "Suggestion"}
SEV_HELP = {
    "critical": "Numbers are wrong now",
    "warning": "Could give wrong numbers",
    "info": "Would make it clearer or tidier",
}
AREAS = [
    ("formula", "Formula integrity"),
    ("data", "Data integrity"),
    ("logic", "Financial logic"),
    ("structure", "Structure & formatting"),
]
AREA_OF_GROUP = {
    "Errors": "formula",
    "Hardcodes & consistency": "formula",
    "Formula patterns": "formula",
    "Risk": "formula",
    "Tables": "data",
    "Pivots": "data",
    "Data hygiene": "data",
    "Reconciliation": "data",
    "Financial logic": "logic",
    "Cell formatting": "structure",
    "Conditional formatting & dropdowns": "structure",
    "Performance": "structure",
    "Structure": "structure",
}
AREA_KEYS = {
    "formula integrity": "formula",
    "data integrity": "data",
    "financial logic": "logic",
    "structure & formatting": "structure",
    "structure": "structure",
    "formatting": "structure",
    "presentation": "structure",
}
NOT_AN_ATTESTATION = (
    "This is not a financial statement audit or an internal-control attestation."
)
DISCLAIMER = (
    "Automated checks test formulas, arithmetic and data in the scanned range; items marked Question are AI judgment, "
    "raised for the owner to confirm. This audit does not certify the numbers: the model owner and reviewer sign off. "
    + NOT_AN_ATTESTATION
)
# Checks scan_workbook.scan skips when the file has no saved formula results (its `cached_ok` branches),
# named in the report whenever the scan adds the values_not_cached note.
VALUE_CHECKS_SKIPPED = "error values in cells, number formats, reconciliations and tie-outs, outlier values, and period-based logic checks"
NOTE_TITLES = {
    "values_not_cached": "No saved results",
    "scan_capped": "Incomplete scan",
    "pivot_unreadable": "Pivot not readable",
    "excel_version_detected": "Excel version",
    "mixed_working_days": "Mixed working-day counts",
    "template_scaffold": "Looks like an empty template",
}

# Performance findings also get their own tab.
PERFORMANCE_CHECKS = {"volatile_function", "cf_fragmented", "cf_whole_column"}


def tab_of(f):
    return f.get("area") or AREA_OF_GROUP.get(f.get("group"), "formula")


def is_perf(f):
    return f["check"] in PERFORMANCE_CHECKS or f.get("group") == "Performance"


def judgment_findings(items):
    """Turn the reviewer's own judgment calls (judgments.json) into findings."""
    out = []
    for i, j in enumerate(items or [], start=1):
        area = AREA_KEYS.get(
            str(j.get("area", "")).strip().lower(),
            j.get("area") if j.get("area") in dict(AREAS) else "logic",
        )
        sev = (
            j.get("severity") if j.get("severity") in ("warning", "info") else "warning"
        )
        out.append(
            {
                "id": f"J-{i:02d}",
                "check": "reviewer_judgment",
                "group": dict(AREAS)[area],
                "area": area,
                "severity": sev,
                "basis": "judgment",
                "sheet": j.get("sheet"),
                "cell": j.get("cell"),
                "label": j.get("label", ""),
                "description": (j.get("title") + ": " if j.get("title") else "")
                + str(j.get("observation") or j.get("text") or ""),
                "question": j.get("question")
                or j.get("text")
                or j.get("observation")
                or "",
                "fix": j.get("suggestion", "") or "Confirm with the model owner.",
            }
        )
    return out


ROLE_LABEL = {
    "inputs": "Inputs",
    "calculation": "Calculation",
    "output": "Output",
    "data": "Raw data",
    "notes": "Notes",
    "external": "Other files",
}
