"""
description: Batch summary for the purchase and invoice review engine: verdict groups, totals, the bottom-line sentence and combining module results.
last_updated: 2026-11-24
"""

import hashlib
import json
import os
from decimal import Decimal

from pir_state import (
    _GROUP_DISPLAY,
    _GROUP_ORDER,
    _PENDING_EXCLUDE,
    INPUTS,
    VERDICT,
    _emit,
)
from pir_tables import read_table
from pir_values import D, g, mfmt, money


def _bottom_line_text(totals, groups, n_findings=0, not_run_checks=None):
    """Bottom-line sentence. When items are called ready to approve while some checks did not run,
    the sentence names those checks so "ready" is never read as "fully checked"."""
    line = _bottom_line_core(totals, groups, n_findings)
    approve_g = next((gx for gx in groups if gx["verdict"] == "Approve"), None)
    if not_run_checks and approve_g and approve_g["count"] > 0:
        line += (
            ' Not run, so not covered by "ready to approve": {} (see not_run).'.format(
                ", ".join(not_run_checks)
            )
        )
    return line


def _bottom_line_core(totals, groups, n_findings=0):
    total_count = totals.get("all_count", 0)
    if total_count == 0:
        if n_findings:
            return f"No item totals could be built from this input; {n_findings} finding{'s' if n_findings != 1 else ''} to review; nothing is marked ready to approve."
        return "No items found to review; nothing is marked ready to approve."
    # Every non-empty group that needs action, worst first: the first is the sentence's
    # subject and each other one follows it, so a reader who stops here misses none.
    action = [
        gx
        for v in ["Hold", "Send back", "Approve with conditions"]
        for gx in groups
        if gx["verdict"] == v and gx["count"] > 0
    ]
    worst = action[0] if action else None
    others_part = "".join(
        f"; {gx['count']} {gx['display'].lower()}, ${mfmt(gx['amount'])}"
        for gx in action[1:]
    )
    approve_g = next((gx for gx in groups if gx["verdict"] == "Approve"), None)
    approve_part = ""
    if approve_g and approve_g["count"] > 0:
        approve_part = (
            f"; {approve_g['count']} ready to approve, ${mfmt(approve_g['amount'])}"
        )
    # Items no module gave a verdict (their checks did not run) are never "ready to approve".
    nv_count, nv_amount = _no_verdict(totals, groups)
    if worst is None:
        if nv_count:
            return f"No verdict for {nv_count} of {total_count} item{'s' if total_count != 1 else ''}, ${mfmt(nv_amount)}: the checks they need did not run (see not_run){approve_part}."
        return f"All {total_count} item{'s' if total_count != 1 else ''} ready to approve, ${mfmt(totals.get('ready_now_amount', '0.00'))}."
    nv_part = f"; {nv_count} with no verdict, ${mfmt(nv_amount)}" if nv_count else ""
    return f"{worst['display']}: {worst['count']} of {total_count} item{'s' if total_count != 1 else ''}, ${mfmt(worst['amount'])}{others_part}{approve_part}{nv_part}."


def _no_verdict(totals, groups):
    """(count, amount) of items that are in the totals but in no verdict group."""
    count = totals.get("all_count", 0) - sum(gx["count"] for gx in groups)
    amount = D(totals.get("all_amount"), Decimal(0)) - sum(
        (D(gx["amount"], Decimal(0)) for gx in groups), Decimal(0)
    )
    return max(count, 0), amount


def _totals_line_text(totals):
    parts = [
        f"All {totals.get('all_count', 0)}: ${mfmt(totals.get('all_amount', '0.00'))}"
    ]
    if "pending_count" in totals:
        parts.append(
            f"{totals['pending_count']} still pending you: ${mfmt(totals['pending_amount'])}"
        )
    if "ready_now_count" in totals:
        parts.append(
            f"{totals['ready_now_count']} ready now: ${mfmt(totals['ready_now_amount'])}"
        )
    if totals.get("no_verdict_count"):
        parts.append(
            f"{totals['no_verdict_count']} with no verdict: ${mfmt(totals['no_verdict_amount'])}"
        )
    return "Totals: " + " | ".join(parts)


def _gaps_for_ready(not_run, overall):
    """Checks that did not run and that apply to an item called ready to approve (named in the bottom line)."""
    approved = {i for i, v in overall.items() if v == "Approve"}
    gaps = []
    for nr in not_run or []:
        if ("item" not in nr or nr["item"] in approved) and nr["check"] not in gaps:
            gaps.append(nr["check"])
    return gaps


def cmd_summary(a):
    with open(a.verdicts, "rb") as fh:
        raw = fh.read()
    vdata = json.loads(raw.decode("utf-8-sig"))
    INPUTS.append(
        {
            "file": os.path.basename(a.verdicts),
            "rows": 1,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    verdicts_map = vdata.get("overall_verdict") or vdata.get("suggested_verdict", {})
    items_data = read_table(a.items)

    all_count = 0
    all_amount = Decimal(0)
    pending_count = 0
    pending_amount = Decimal(0)
    pending_known = False
    group_counts = dict.fromkeys(_GROUP_ORDER, 0)
    group_amounts = {v: Decimal(0) for v in _GROUP_ORDER}

    for r in items_data:
        iid = g(r, "id")
        amt = D(g(r, "amount"), Decimal(0))
        status = g(r, "status", default="").lower().strip()
        all_count += 1
        all_amount += amt
        if status:
            pending_known = True
            if status not in _PENDING_EXCLUDE:
                pending_count += 1
                pending_amount += amt
        v = verdicts_map.get(iid)
        if v in group_counts:
            group_counts[v] += 1
            group_amounts[v] += amt

    groups = [
        {
            "verdict": v,
            "display": _GROUP_DISPLAY[v],
            "count": group_counts[v],
            "amount": money(group_amounts[v]),
        }
        for v in _GROUP_ORDER
    ]
    totals = {"all_count": all_count, "all_amount": money(all_amount)}
    if pending_known:
        totals["pending_count"] = pending_count
        totals["pending_amount"] = money(pending_amount)
    totals["ready_now_count"] = group_counts["Approve"]
    totals["ready_now_amount"] = money(group_amounts["Approve"])

    group_total = sum(D(gx["amount"]) for gx in groups)
    _emit(
        {
            "label": "script-computed",
            "subcommand": "summary",
            "inputs": INPUTS,
            "bottom_line": _bottom_line_text(
                totals, groups, 0, _gaps_for_ready(vdata.get("not_run"), verdicts_map)
            ),
            "check_sum_ok": group_total == all_amount,
            "groups": groups,
            "totals": totals,
            "totals_line": _totals_line_text(totals),
        }
    )


def cmd_combine(a):
    rank = {v: k for k, v in VERDICT.items()}
    per_item, findings, ok, mods, not_run = {}, [], [], [], []
    for path in [x.strip() for x in a.results.split(",") if x.strip()]:
        with open(path, encoding="utf-8-sig") as fh:
            r = json.load(fh)
        mods.append(r.get("subcommand"))
        not_run += [dict(nr, module=r.get("subcommand")) for nr in r.get("not_run", [])]
        INPUTS.extend(i for i in r.get("inputs", []) if i not in INPUTS)
        findings += [dict(f, module=r.get("subcommand")) for f in r.get("findings", [])]
        ok += [
            dict(o, module=r.get("subcommand")) for o in r.get("checked_no_issue", [])
        ]
        for item, v in r.get("suggested_verdict", {}).items():
            per_item.setdefault(item, {})[r.get("subcommand")] = v
    overall = {
        i: max(vs.values(), key=lambda v: rank.get(v, 0)) for i, vs in per_item.items()
    }
    _emit(
        {
            "label": "script-computed",
            "subcommand": "combine",
            "modules": mods,
            "inputs": INPUTS,
            "findings": findings,
            "checked_no_issue": ok,
            "not_run": not_run,
            "verdict_by_module": per_item,
            "overall_verdict": overall,
        }
    )


def _combine_in_memory(results_list):
    """Merge a list of result dicts without writing temp files (used by cmd_all)."""
    rank = {v: k for k, v in VERDICT.items()}
    per_item, findings, ok, mods = {}, [], [], []
    for r in results_list:
        mods.append(r.get("subcommand"))
        for inp in r.get("inputs", []):
            if inp not in INPUTS:
                INPUTS.append(inp)
        findings += [dict(f, module=r.get("subcommand")) for f in r.get("findings", [])]
        ok += [
            dict(o, module=r.get("subcommand")) for o in r.get("checked_no_issue", [])
        ]
        for item, v in r.get("suggested_verdict", {}).items():
            per_item.setdefault(item, {})[r.get("subcommand")] = v
    overall = {
        i: max(vs.values(), key=lambda v: rank.get(v, 0)) for i, vs in per_item.items()
    }
    return {
        "label": "script-computed",
        "subcommand": "combine",
        "modules": mods,
        "inputs": list(INPUTS),
        "findings": findings,
        "checked_no_issue": ok,
        "verdict_by_module": per_item,
        "overall_verdict": overall,
    }
