"""
description: Justification checks JUS-1 and JUS-2 for the purchase and invoice review engine.
last_updated: 2026-11-24
"""

from collections import Counter
from decimal import Decimal

from pir_tables import _process_input, read_table
from pir_values import Out, g


def cmd_justification(a):
    if getattr(a, "input", None):
        _process_input(a, "justification")
    o = Out("justification", {"template_fields": a.template_fields})
    template = []
    if a.template_fields:
        template = [
            g(r, "element", "field", "name")
            for r in read_table(a.template_fields, "template_fields")
        ]
    for r in read_table(a.requests):
        item = g(r, "id", default=r["_src"])
        text = g(
            r,
            "justification",
            "justification_text",
            "description",
            "business_justification",
        )
        if not text.strip():
            o.add(
                "JUS-1 justification missing",
                item,
                "SEND_BACK",
                "no justification text found",
                "field=justification",
                r["_src"],
                Decimal(0),
            )
            continue
        if template:
            missing = 0
            for elem in template:
                if elem.upper() not in text.upper():
                    missing += 1
                    o.add(
                        "JUS-2 element missing",
                        item,
                        "SEND_BACK",
                        f"justification does not address required element {elem}",
                        elem,
                        r["_src"],
                        Decimal(0),
                    )
            if not missing:
                o.clear(
                    "JUS-1..2",
                    item,
                    f"justification present and covers all {len(template)} template elements",
                )
        else:
            o.clear("JUS-1", item, "justification text present (no template on file)")
    if template:
        all_items = {f["item"] for f in o.findings} | {c["item"] for c in o.ok}
        blank = {f["item"] for f in o.findings if f["rule"].startswith("JUS-1")}
        misses = Counter(f["item"] for f in o.findings if f["rule"].startswith("JUS-2"))
        summary = {}
        for it in sorted(all_items):
            if it in blank:
                summary[it] = {
                    "total": len(template),
                    "present": 0,
                    "missing": len(template),
                    "display": f"0/{len(template)}",
                }
            else:
                n_miss = misses[it]
                total = len(template)
                present = total - n_miss
                summary[it] = {
                    "total": total,
                    "present": present,
                    "missing": n_miss,
                    "display": f"{present}/{total}",
                }
        o.extra["justification_summary"] = summary
    o.dump()
