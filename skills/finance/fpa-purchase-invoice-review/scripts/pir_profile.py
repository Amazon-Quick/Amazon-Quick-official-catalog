"""
description: Finance profile questions for the purchase and invoice review engine: which profile fields each check needs and which are still missing.
last_updated: 2026-11-24
"""

import hashlib
import json
import os

from pir_state import INPUTS, THRESHOLD_FIELDS, _emit

# At most this many profile questions in one message (references/profile.md, First-run rules).
MAX_QUESTIONS = 3
# Threshold fields have no default: the second value is None and the check reports not run.
PROFILE_FIELDS = {
    "erp": (
        "Which accounting or enterprise resource planning (ERP) system holds the general ledger (GL)?",
        "unknown - generic field names",
    ),
    "purchasing_tool": ("Which tool raises requisitions and POs?", "same as ERP"),
    "coa_style": (
        "Chart of accounts: how are expense, asset (capex), and prepaid accounts told apart?",
        "account type column supplied with the data",
    ),
    "grain": (
        "At what grain is budget held (for example cost center x account x month)?",
        "cost_center,account; monthly",
    ),
    "budget_source": (
        "Which plan(s) is spend checked against (budget, forecast)?",
        "the budget file supplied",
    ),
    "approval_matrix": ("What are the approval $ tiers?", None),
    "quote_policy": (
        "Above what $ are competitive quotes required, and how many?",
        None,
    ),
    "capex_threshold": (
        "Unit cost and useful life above which an item is capitalized?",
        None,
    ),
    "fiscal_calendar": (
        "Which month starts the fiscal year, and which periods are closed?",
        "January; none closed",
    ),
    "currency": ("Reporting currency?", "USD"),
    "materiality": ("Below what $ should a finding be noted but not raised?", None),
    "invoice_tolerance": (
        "3-way match tolerance (qty and price)?",
        None,
    ),
}
MODULE_NEEDS = {
    "coding": ["coa_style", "capex_threshold", "materiality"],
    "budget": ["grain", "budget_source", "fiscal_calendar", "materiality"],
    "contract": ["materiality"],
    "price": ["quote_policy", "materiality"],
    "approval": ["approval_matrix", "quote_policy"],
    "invoice": ["invoice_tolerance", "fiscal_calendar", "materiality"],
}


def cmd_profile(a):
    prof = {}
    if a.profile and os.path.exists(a.profile):
        with open(a.profile, "rb") as fh:
            raw = fh.read()
        prof = json.loads(raw.decode("utf-8-sig"))
        INPUTS.append(
            {
                "file": os.path.basename(a.profile),
                "rows": len(prof),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    mods = [m.strip() for m in a.modules.split(",") if m.strip()]
    needed = []
    for m in mods:
        for f in MODULE_NEEDS.get(m, []):
            if f not in needed:
                needed.append(f)
    missing = [f for f in needed if not str(prof.get(f, "")).strip()]
    missing.sort(
        key=lambda f: f not in THRESHOLD_FIELDS
    )  # thresholds first: without them checks don't run
    ask = missing[:MAX_QUESTIONS]
    res = {
        "label": "script-computed",
        "subcommand": "profile",
        "inputs": INPUTS,
        "modules": mods,
        "profile_found": bool(prof),
        "profile_used": "; ".join(
            f"{k}={prof[k]}" for k in sorted(prof) if k in PROFILE_FIELDS
        ),
        "questions": [
            {
                "field": f,
                "question": PROFILE_FIELDS[f][0],
                "default": None
                if f in THRESHOLD_FIELDS
                else "ASSUMPTION: " + PROFILE_FIELDS[f][1],
            }
            for f in ask
        ],
        "defaults_applied_without_asking": [
            {"field": f, "default": "ASSUMPTION: " + PROFILE_FIELDS[f][1]}
            for f in missing[MAX_QUESTIONS:]
            if f not in THRESHOLD_FIELDS
        ],
        "thresholds_not_set": [
            f for f in missing[MAX_QUESTIONS:] if f in THRESHOLD_FIELDS
        ],
        "block_review": False,
    }
    _emit(res)
