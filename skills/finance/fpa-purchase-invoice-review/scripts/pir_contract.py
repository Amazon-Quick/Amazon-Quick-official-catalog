"""
description: Contract and terms checks CON-0 to CON-6 for the purchase and invoice review engine.
last_updated: 2026-11-24
"""

import datetime as dt
from collections import defaultdict
from decimal import Decimal

from pir_tables import _process_input, read_table
from pir_values import D, Out, date, g, money


def cmd_contract(a):
    if getattr(a, "input", None):
        _process_input(a, "contract")
    asof = date(a.as_of)
    o = Out("contract", {"as_of": a.as_of, "renewal_warn_days": a.renewal_warn_days})
    contracts = {g(c, "contract_id"): c for c in read_table(a.contract)}
    rates = defaultdict(dict)
    for r in read_table(a.rates):
        # "rate" column fuzzy-maps to canonical "unit_price"; keep "rate" as fallback
        rates[g(r, "contract_id")][g(r, "item", "role").upper()] = (
            D(g(r, "unit_price", "rate")),
            r["_src"],
        )
    used = defaultdict(Decimal)
    for c in read_table(a.change_orders):
        cid = g(c, "contract_id")
        if cid in contracts:
            contracts[cid]["_co"] = contracts[cid].get("_co", Decimal(0)) + D(
                g(c, "amount"), Decimal(0)
            )
    for p in sorted(
        read_table(a.pos),
        key=lambda p: (date(g(p, "po_date")) or dt.date.min, g(p, "po")),
    ):
        cid, po = g(p, "contract_id"), g(p, "po")
        c = contracts.get(cid)
        if not c:
            o.add(
                "CON-0 no contract",
                po,
                "CONDITION",
                "PO names no contract on file",
                f"contract_id={cid!r}",
                p["_src"],
                D(g(p, "amount"), Decimal(0)),
            )
            continue
        amt = D(g(p, "amount"), Decimal(0))
        ceiling = D(g(c, "ceiling"), Decimal(0)) + c.get("_co", Decimal(0))
        before = used[cid]
        used[cid] += amt
        if used[cid] > ceiling:
            o.add(
                "CON-1 over contract ceiling",
                po,
                "HOLD",
                "cumulative PO value exceeds ceiling (incl. approved change orders)",
                f"cumulative {money(used[cid])} against ceiling {money(ceiling)}",
                p["_src"] + " / " + c["_src"],
                used[cid] - max(ceiling, before),
            )
        else:
            o.clear(
                "CON-1",
                po,
                f"cumulative {money(used[cid])} within ceiling {money(ceiling)}",
            )
        # "start"/"end" stay as-is (not mapped); "service_start/end" is the canonical for service-date cols
        cs = date(g(c, "start", "service_start"))
        ce = date(g(c, "end", "service_end"))
        ps = date(g(p, "start", "service_start"))
        pe = date(g(p, "end", "service_end"))
        if cs and ce and ps and pe and (ps < cs or pe > ce):
            o.add(
                "CON-2 PO outside contract term",
                po,
                "SEND_BACK",
                "PO service dates fall outside the term",
                f"PO {ps}..{pe} against term {cs}..{ce}",
                p["_src"] + " / " + c["_src"],
                amt,
            )
        ct, pt = g(c, "payment_terms_days"), g(p, "payment_terms_days")
        if ct and pt and int(pt) < int(ct):
            o.add(
                "CON-3 payment terms shorter than contract",
                po,
                "CONDITION",
                "PO pays faster than the contract requires",
                f"PO net {pt} against contract net {ct}",
                p["_src"],
                Decimal(0),
            )
        rc = rates.get(cid, {})
        price = D(g(p, "unit_price"))
        it = g(p, "item", "role").upper()
        if price is not None and it and rc:
            if it not in rc:
                o.add(
                    "CON-4 item not on rate card",
                    po,
                    "SEND_BACK",
                    "PO item/role not on the contract rate card",
                    it,
                    p["_src"],
                    amt,
                )
            elif price > rc[it][0]:
                qty = D(g(p, "qty"), Decimal(1))
                o.add(
                    "CON-5 price above rate card",
                    po,
                    "SEND_BACK",
                    "PO unit price above contract rate",
                    f"{money(price)} against {money(rc[it][0])}",
                    p["_src"] + " / " + rc[it][1],
                    (price - rc[it][0]) * qty,
                )
    for cid, c in sorted(contracts.items()):
        ce, notice = (
            date(g(c, "end", "service_end")),
            int(g(c, "notice_days", default="0") or 0),
        )
        if g(c, "auto_renew").lower() in ("y", "yes", "true", "1") and ce and asof:
            deadline = ce - dt.timedelta(days=notice)
            if (deadline - asof).days < 0 <= (ce - asof).days:
                o.add(
                    "CON-6 auto-renewal notice passed",
                    cid,
                    "INFO",
                    "notice deadline has passed; contract will renew",
                    f"deadline {deadline}, term end {ce}",
                    c["_src"],
                    Decimal(0),
                )
            elif 0 <= (deadline - asof).days <= a.renewal_warn_days:
                o.add(
                    "CON-6 auto-renewal notice due",
                    cid,
                    "INFO",
                    "auto-renews unless notice is given",
                    f"notice deadline {deadline} ({(deadline - asof).days} days)",
                    c["_src"],
                    Decimal(0),
                )
    o.dump()
