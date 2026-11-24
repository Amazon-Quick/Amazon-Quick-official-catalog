"""
description: Budget fit checks BUD-1 to BUD-3 for the purchase and invoice review engine.
last_updated: 2026-11-24
"""

from collections import defaultdict
from decimal import Decimal

from pir_state import ClarificationNeeded
from pir_tables import _process_input, read_table
from pir_values import D, Out, date, fiscal, g, money

# Most distinct planning sources (budget, forecast, allocation ...) one review accepts.
_MAX_SOURCES = 10
# Most stale commitments named on one request (BUD-3 is informational).
_MAX_STALE_PER_REQUEST = 10


def cmd_budget(a):
    if getattr(a, "input", None):
        _process_input(a, "budget")
    grain = [c.strip() for c in a.grain.split(",")]
    sm, asof = a.fiscal_start_month, date(a.as_of)
    o = Out(
        "budget",
        {
            "grain": grain,
            "fiscal_start_month": sm,
            "as_of": a.as_of,
            "stale_days": a.stale_days,
            "commit_statuses": a.commit_statuses,
        },
    )

    def key(r):
        return "|".join(g(r, c) for c in grain)

    bud = defaultdict(Decimal)
    pooled, sources = set(), set()
    _saw_empty_period = False
    unreadable, bad_keys = (
        [],
        set(),
    )  # rows whose period cannot be read; their grain keys

    def _buckets(r, table):
        """(FY, quarter) for a row, or None (row listed under unreadable_periods, never dropped silently)."""
        nonlocal _saw_empty_period
        p = g(r, "period")
        if not p:
            _saw_empty_period = True
            p = "2000-01"
        fq = fiscal(p, sm)
        if fq is None:
            unreadable.append({"table": table, "period": p, "source": r["_src"]})
            if table != "requests":
                bad_keys.add(key(r))
        return fq

    budget_rows = read_table(a.budget)
    for r in budget_rows:
        fq = _buckets(r, "budget")
        if fq is None:
            continue
        src = g(r, "source", default="budget")
        sources.add(src)
        fy, q = fq
        for b in (fy, q):
            bud[(src, key(r), b)] += D(g(r, "amount"), Decimal(0))
        if g(r, "pooled").lower() in ("y", "yes", "true", "1"):
            pooled.add(key(r))

    act = defaultdict(Decimal)
    for r in read_table(a.actuals):
        fq = _buckets(r, "actuals")
        if fq is None:
            continue
        fy, q = fq
        for b in (fy, q):
            act[(key(r), b)] += D(g(r, "amount"), Decimal(0))

    com = defaultdict(Decimal)
    statuses = {s.strip().lower() for s in a.commit_statuses.split(",")}
    stale = []
    for r in read_table(a.commitments):
        if g(r, "status", default="open").lower() not in statuses:
            o.clear(
                "BUD-commit", g(r, "po"), "excluded: status {}".format(g(r, "status"))
            )
            continue
        open_amt = D(g(r, "po_amount"), Decimal(0)) - D(g(r, "invoiced"), Decimal(0))
        if open_amt < 0:
            o.extra.setdefault("over_invoiced_commitments", []).append(
                {
                    "po": g(r, "po"),
                    "overage": money(-open_amt),
                    "source": r["_src"],
                    "note": (
                        "Invoiced amount exceeds the PO value. Open commitment "
                        "is zero; confirm that the overage is included in actuals."
                    ),
                }
            )
            open_amt = Decimal(0)
        fq = _buckets(r, "commitments")
        if fq is None:
            continue
        fy, q = fq
        for b in (fy, q):
            com[(key(r), b)] += open_amt
        nb = date(g(r, "need_by"))
        if (
            asof
            and nb
            and (asof - nb).days > a.stale_days
            and D(g(r, "received"), Decimal(0)) == 0
        ):
            stale.append(
                {
                    "po": g(r, "po"),
                    "key": key(r),
                    "open": money(open_amt),
                    "need_by": str(nb),
                    "source": r["_src"],
                }
            )
    o.extra["stale_commitments"] = stale

    if _saw_empty_period:
        o.extra["assumed_single_period"] = True

    stale_by_key = defaultdict(
        list
    )  # grain key -> stale commitments, so no request scans them all
    for st in stale:
        stale_by_key[st["key"]].append(st)
    if len(sources) > _MAX_SOURCES:
        # Headroom is computed per request and per source, so a free-text source column with many
        # values would multiply the work and the table; a real plan has a handful of sources.
        raise ClarificationNeeded(
            f"The budget table names {len(sources)} planning sources. Which column holds the source "
            "(budget, forecast, allocation), or should all rows be one budget?",
            details={"field": "source", "sources": sorted(sources)[:_MAX_SOURCES]},
        )
    sorted_sources = sorted(sources)
    batch = defaultdict(Decimal)
    table = []
    requests = sorted(read_table(a.requests), key=lambda r: g(r, "id"))
    if requests and not budget_rows:
        # No budget table: the fit cannot be tested. Report it as not run, never as "unbudgeted".
        o.skip(
            "BUD-1..3",
            "budget",
            "Which budget or forecast should these requests be checked against? "
            "Paste it with cost_center, account, period, and amount columns.",
        )
        requests = []
    for r in requests:
        rid, k, amt = g(r, "id"), key(r), D(g(r, "amount"), Decimal(0))
        fq = _buckets(r, "requests")
        if fq is None:
            o.skip(
                "BUD-1..2",
                "period",
                "Period {!r} could not be read; give it as YYYY-MM.".format(
                    g(r, "period")
                ),
                item=rid,
            )
            continue
        if k in bad_keys:
            o.skip(
                "BUD-1..2",
                "period",
                f"A budget, actuals, or commitment row on line {k} has a period that "
                "could not be read (see unreadable_periods); give it as YYYY-MM.",
                item=rid,
            )
            continue
        fy, q = fq
        if not any((s, k, fy) in bud for s in sources):
            o.add(
                "BUD-1 unbudgeted",
                rid,
                "CONDITION",
                "no budget row at this grain in any planning source",
                f"key {k}",
                r["_src"],
                amt,
            )
            continue
        worst = None
        for s in sorted_sources:
            for b in (q, fy):
                h = (
                    bud.get((s, k, b), Decimal(0))
                    - act[(k, b)]
                    - com[(k, b)]
                    - batch[(k, b)]
                    - amt
                )
                alone = h + batch[(k, b)]
                table.append(
                    {
                        "request": rid,
                        "source": s,
                        "key": k,
                        "bucket": b,
                        "budget": money(bud.get((s, k, b), Decimal(0))),
                        "actuals": money(act[(k, b)]),
                        "open_commitments": money(com[(k, b)]),
                        "earlier_requests": money(batch[(k, b)]),
                        "request_amount": money(amt),
                        "headroom_after": money(h),
                    }
                )
                if worst is None or h < worst[0]:
                    worst = (h, s, b, alone)
        h, s, b, alone = worst
        if h < 0:
            pool = k in pooled
            what = "headroom negative (effective = lowest across sources)"
            if alone >= 0:
                what += "; fits alone, breaks only with earlier requests in this batch"
            what += (
                "; shortfall sits in a POOLED catch-all line"
                if pool
                else "; shortfall sits in the specific line"
            )
            o.add(
                "BUD-2 does not fit",
                rid,
                "CONDITION" if pool else "HOLD",
                what,
                f"{s} {b} headroom {money(h)}",
                r["_src"],
                min(-h, amt),
            )
        else:
            o.clear(
                "BUD-2",
                rid,
                f"fits: lowest headroom after request {money(h)} ({s} {b})",
            )
        for st in stale_by_key.get(k, [])[:_MAX_STALE_PER_REQUEST]:
            o.add(
                "BUD-3 stale commitment on same line",
                rid,
                "INFO",
                "open PO past need-by with nothing received; may be released; confirm with buyer",
                "PO {} open {} need-by {}".format(st["po"], st["open"], st["need_by"]),
                st["source"],
                Decimal(0),
            )
        for b in (q, fy):
            batch[(k, b)] += amt

    if _saw_empty_period:
        o.extra["assumed_single_period"] = True
    if unreadable:
        o.extra["unreadable_periods"] = unreadable

    o.extra["headroom_table"] = table
    o.dump()
