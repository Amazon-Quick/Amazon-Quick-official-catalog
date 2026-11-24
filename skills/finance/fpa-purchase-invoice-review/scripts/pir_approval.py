"""
description: Approval and policy checks APR-1 to APR-4 for the purchase and invoice review engine.
last_updated: 2026-11-24
"""

import datetime as dt
from collections import defaultdict, deque
from decimal import Decimal

from pir_state import ClarificationNeeded
from pir_tables import _process_input, read_table
from pir_values import D, Out, date, g, money


def cmd_approval(a):
    if getattr(a, "input", None):
        _process_input(a, "approval")
    tiers_str = a.tiers
    o = Out(
        "approval",
        {
            "tiers": tiers_str,
            "split_window_days": a.split_window_days,
            "split_margin": a.split_margin,
            "addon_warn": a.addon_warn,
        },
    )
    if tiers_str is None:
        tiers = None
        tier_of = None
        o.skip("APR-1", "tiers", "What are the approval $ tiers (comma-separated)?")
        o.skip("APR-3", "tiers", "What are the approval $ tiers (comma-separated)?")
    else:
        parsed = [D(t) for t in tiers_str.split(",")]
        if not parsed or any(t is None or t <= 0 for t in parsed):
            raise ClarificationNeeded(
                "What are the approval tier upper limits as plain numbers, lowest first "
                "(for example 10000,50000)?",
                details={"field": "tiers", "value": tiers_str},
            )
        tiers = sorted(parsed)

        def tier_of(v, _t=tiers):
            return sum(1 for t in _t if v > t)

    reqs = read_table(a.requests)
    request_dates = {id(r): date(g(r, "date")) for r in reqs}
    for r in reqs:
        rid = g(r, "id")
        base = D(g(r, "amount"), Decimal(0))
        add = sum(
            (D(g(r, c), Decimal(0)) for c in ("freight", "tax", "contingency")),
            Decimal(0),
        )
        full = base + add
        crossed = tiers is not None and tier_of(full) > tier_of(base)
        if crossed:
            o.add(
                "APR-1 tier crossed after add-ons",
                rid,
                "SEND_BACK",
                "freight/tax/contingency push the commitment into a higher approval tier",
                f"{money(base)} + {money(add)} = {money(full)} against tier {money(tiers[tier_of(base)])}",
                r["_src"],
                full,
            )
        elif base > 0 and add / base > D(a.addon_warn):
            # APR-2 needs no tiers: a large add-on share is worth a condition at any tier.
            o.add(
                "APR-2 large add-on",
                rid,
                "CONDITION",
                "add-ons above warning share of the base",
                "{} = {}%".format(
                    money(add), (add / base * 100).quantize(Decimal("0.1"))
                ),
                r["_src"],
                add,
            )
        elif tiers is not None:
            o.clear(
                "APR-1",
                rid,
                f"full commitment {money(full)} stays in tier {tier_of(full)}",
            )
        d0 = request_dates[id(r)]
        svc = date(g(r, "service_start", "receipt_date"))
        if d0 and svc and svc < d0:
            o.add(
                "APR-4 receipt/service before PO",
                rid,
                "CONDITION",
                "goods or service started before the request (after-the-fact)",
                f"service {svc} against request {d0}",
                r["_src"],
                base,
            )
    if tiers is not None:
        groups = defaultdict(list)
        for r in reqs:
            groups[(g(r, "vendor").upper(), g(r, "requester").upper())].append(r)
        for (_v, _rq), rs in sorted(groups.items()):
            rs.sort(key=lambda r: (request_dates[id(r)] or dt.date.min, g(r, "id")))
            _find_split(o, a, rs, request_dates, tiers, tier_of)
        seen, uniq = set(), []
        for f in o.findings:
            k = (f["rule"], f["item"])
            if f["rule"].startswith("APR-3") and k in seen:
                continue
            seen.add(k)
            uniq.append(f)
        o.findings = uniq
    o.dump()


def _find_split(o, a, rs, request_dates, tiers, tier_of):
    """APR-3 for one vendor + requester group, sorted by date: the first window that splits a tier.

    A two-pointer window with running sums keeps this linear in the group size, so a large
    pasted batch cannot stall the sandbox. Rows with no date never start or join a window.
    """
    dated = [r for r in rs if request_dates[id(r)] is not None]
    amounts = [D(g(r, "amount"), Decimal(0)) for r in dated]
    row_tier = [tier_of(x) for x in amounts]
    margin = 1 - D(a.split_margin)
    near = [
        1 if t < len(tiers) and x >= tiers[t] * margin else 0
        for x, t in zip(amounts, row_tier, strict=True)
    ]
    end, total, near_count, tier_max = 0, Decimal(0), 0, deque()
    for i, r in enumerate(dated):
        d0 = request_dates[id(r)]
        while (
            end < len(dated)
            and (request_dates[id(dated[end])] - d0).days <= a.split_window_days
        ):
            total += amounts[end]
            near_count += near[end]
            while tier_max and row_tier[tier_max[-1]] <= row_tier[end]:
                tier_max.pop()
            tier_max.append(end)
            end += 1
        while tier_max and tier_max[0] < i:
            tier_max.popleft()
        if end - i >= 2:
            each_tier = row_tier[tier_max[0]]
            if tier_of(total) > each_tier and near_count >= 1:
                win = dated[i:end]
                ids = _capped_list([g(x, "id") for x in win], ",")
                sources = _capped_list([y["_src"] for y in win], ";")
                for x in win:
                    o.add(
                        "APR-3 possible split",
                        g(x, "id"),
                        "SEND_BACK",
                        f"same vendor + requester within {a.split_window_days} days; each under a tier, together above it",
                        f"{ids} total {money(total)} against tier {money(tiers[each_tier])}",
                        sources,
                        total,
                    )
                return
        total -= amounts[i]
        near_count -= near[i]


# Ids and sources named in one APR-3 finding; the rest are counted, so a huge window cannot
# make every finding carry the whole batch.
_MAX_LISTED = 20


def _capped_list(values, sep):
    """Join the first _MAX_LISTED values and say how many more there are."""
    shown = sep.join(values[:_MAX_LISTED])
    extra = len(values) - _MAX_LISTED
    return shown + (f"{sep} and {extra} more" if extra > 0 else "")
