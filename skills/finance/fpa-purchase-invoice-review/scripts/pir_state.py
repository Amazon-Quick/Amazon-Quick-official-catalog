"""
description: Shared per-call state, verdict constants, the clarification exception and the result emitter for the purchase and invoice review engine.
last_updated: 2026-11-24
"""

import copy
import json
import sys

SEV_RANK = {"INFO": 0, "CONDITION": 1, "SEND_BACK": 2, "HOLD": 3}
VERDICT = {0: "Approve", 1: "Approve with conditions", 2: "Send back", 3: "Hold"}
INPUTS = []
_STATE = {"result": None, "quiet": False}
# Fields with no org-neutral default; script emits a not_run entry when these are absent.
THRESHOLD_FIELDS = {
    "materiality",
    "approval_matrix",
    "quote_policy",
    "capex_threshold",
    "invoice_tolerance",
}
# Verdict display names and ordering for batch output (plain text; the report uses no emoji).
_GROUP_ORDER = ["Approve", "Approve with conditions", "Send back", "Hold"]
_GROUP_DISPLAY = {
    "Approve": "Ready to approve",
    "Approve with conditions": "Approve with conditions",
    "Send back": "Send back",
    "Hold": "Hold",
}
_PENDING_EXCLUDE = {"approved", "rejected", "closed", "cancelled", "paid"}

_TABLE_CACHE = {}  # pseudo_path -> list[dict], populated by _parse_message_tables
_MAPPED_COLS = {}  # orig_normalized -> canonical (for mapped_columns output)
_IGNORED_TABLES = []  # pasted tables not used because a table of the same type came first
_EXCLUDED_ROWS = []


class ClarificationNeeded(Exception):
    """An interpretation problem, not evidence for a payment verdict."""

    def __init__(self, question, source="", details=None):
        self.question, self.source, self.details = question, source, details or {}


def _intake_result(exc):
    return {
        "ok": False,
        "status": "needs_clarification",
        "questions": [{"question": exc.question, "source": exc.source, **exc.details}],
        "mapped_columns": dict(_MAPPED_COLS),
        "excluded_rows": list(_EXCLUDED_ROWS),
        "findings": [],
        "overall_verdict": {},
        "note": "Review paused before payment verdicts. Confirm the interpretation and rerun.",
    }


def _emit(res):
    """Record the result for main() to return; print JSON unless quiet."""
    if "inputs" in res:
        res["inputs"] = list(res["inputs"])  # snapshot
    if _IGNORED_TABLES:
        res["ignored_tables"] = list(_IGNORED_TABLES)
    if _EXCLUDED_ROWS:
        res["excluded_rows"] = list(_EXCLUDED_ROWS)
    # A deep copy, so a later call that resets the shared state never changes this result.
    res = copy.deepcopy(res)
    _STATE["result"] = res
    if not _STATE["quiet"]:
        json.dump(res, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
