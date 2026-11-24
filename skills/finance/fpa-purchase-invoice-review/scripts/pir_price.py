"""
description: Price and competition checks PRC-1 to PRC-4 for the purchase and invoice review engine.
last_updated: 2026-11-24
"""

import statistics
from collections import defaultdict
from decimal import Decimal

from pir_tables import _process_input, read_table
from pir_values import D, Out, date, g, money


def cmd_price(a):
    if getattr(a, "input", None):
        _process_input(a, "price")
    asof = date(a.as_of)
    o = Out(
        "price",
        {
            "tolerance": a.tolerance,
            "quote_threshold": a.quote_threshold,
            "quotes_required": a.quotes_required,
            "window_days": a.window_days,
            "as_of": a.as_of,
        },
    )
    hist = defaultdict(list)
    for h in read_table(a.history):
        d = date(g(h, "date"))
        if asof and d and (asof - d).days > a.window_days:
            continue
        price = D(g(h, "unit_price"))
        if price is None:
            raise ValueError(f"{h['_src']}: unreadable history unit price")
        hist[g(h, "item").upper()].append(price)
    quotes = defaultdict(list)
    for q in read_table(a.quotes):
        quotes[g(q, "request_id", "id")].append(q)
    tol, qthr = D(a.tolerance), D(a.quote_threshold)
    if tol is None:
        o.skip(
            "PRC-1",
            "price_tolerance",
            "How far above the median of prior purchases may a unit price be "
            "before it is questioned (for example 0.20 for 20%)?",
        )
    if qthr is None:
        o.skip(
            "PRC-2",
            "quote_policy",
            "Above what amount are competitive quotes required, and how many?",
        )
    for r in read_table(a.lines):
        rid, it = g(r, "id"), g(r, "item").upper()
        unit, qty = D(g(r, "unit_price")), D(g(r, "qty", default="1"))
        amount = g(r, "amount")
        total = D(amount) if amount else None
        if not amount and unit is not None and qty is not None:
            total = unit * qty
        if hist.get(it) and tol is not None and (unit is None or qty is None):
            o.skip(
                "PRC-1",
                "unit_price/qty",
                "What are the request's numeric unit price and quantity?",
                item=rid,
            )
        elif hist.get(it) and tol is not None:
            med = Decimal(str(statistics.median(hist[it])))
            if med > 0 and unit > med * (1 + tol):
                o.add(
                    "PRC-1 above history median",
                    rid,
                    "CONDITION",
                    "unit price above median of prior buys by more than tolerance",
                    f"{money(unit)} against median {money(med)} (n={len(hist[it])})",
                    r["_src"],
                    (unit - med) * qty,
                )
            else:
                o.clear(
                    "PRC-1",
                    rid,
                    f"unit {money(unit)} within tolerance of median {money(med)} (n={len(hist[it])})",
                )
        elif tol is not None:
            o.clear("PRC-1", rid, "not tested: no purchase history in window")
        qs = quotes.get(rid, [])
        valid, expired = [], []
        for q in qs:
            until = date(g(q, "valid_until"))
            (expired if asof and until and until < asof else valid).append(q)
        for q in expired:
            o.add(
                "PRC-3 quote expired",
                rid,
                "SEND_BACK",
                "quote validity date has passed",
                "valid until {}".format(g(q, "valid_until")),
                q["_src"],
                Decimal(0),
            )
        if total is None:
            o.skip(
                "PRC-2/4",
                "amount",
                "Which column is the numeric request total? Supply a readable "
                "amount or, when absent, a unit price and quantity.",
                item=rid,
            )
            continue
        if qthr is not None and total >= qthr and len(valid) < a.quotes_required:
            if g(r, "sole_source_reason"):
                o.add(
                    "PRC-2 sole source - reason to test",
                    rid,
                    "CONDITION",
                    "fewer quotes than policy; sole-source reason given",
                    f"{len(valid)} valid quote(s); reason: {g(r, 'sole_source_reason')}",
                    r["_src"],
                    Decimal(0),
                )
            else:
                o.add(
                    "PRC-2 quotes below policy",
                    rid,
                    "SEND_BACK",
                    "fewer valid quotes than policy and no sole-source reason",
                    f"{len(valid)} of {a.quotes_required} at total {money(total)}",
                    r["_src"],
                    total,
                )
        if len(valid) >= 2:
            amounts = [D(g(q, "amount")) for q in valid]
            if any(amount is None for amount in amounts):
                o.skip(
                    "PRC-4",
                    "quote_amount",
                    "What is the numeric amount for each valid quote?",
                    item=rid,
                )
                continue
            low = min(amounts)
            if total > low:
                o.add(
                    "PRC-4 not lowest quote",
                    rid,
                    "CONDITION",
                    "chosen price above lowest valid quote; ask why",
                    f"{money(total)} against lowest {money(low)}",
                    r["_src"],
                    total - low,
                )
    o.dump()
