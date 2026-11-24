"""
description: Coding checks CODE-1 to CODE-6 for the purchase and invoice review engine.
last_updated: 2026-11-24
"""

from collections import defaultdict
from decimal import Decimal

from pir_tables import _process_input, read_table
from pir_values import D, Out, date, g, money

# Most prior-purchase rows a CODE-6 finding cites as its source; the rest are counted.
_MAX_PRIOR_SOURCES = 10


def cmd_coding(a):
    if getattr(a, "input", None):
        _process_input(a, "coding")
    o = Out(
        "coding",
        {
            "capex_threshold": a.capex_threshold,
            "life_months": a.life_months,
            "materiality": a.materiality,
            "project_required": a.project_required,
        },
    )
    cap, mat = D(a.capex_threshold), D(a.materiality)
    hist = defaultdict(list)
    for h in read_table(a.prior):
        hist[(g(h, "vendor").upper(), g(h, "item").upper())].append(h)
    # Accounts used before for each vendor + item, computed once rather than once per line.
    hist_accounts = {
        k: sorted({g(h, "account") for h in rows if g(h, "account")})
        for k, rows in hist.items()
    }
    coding_rows = read_table(a.lines)
    if coding_rows and not any(g(r, "account_type") for r in coding_rows):
        # CODE-1..4 all test the account type; without it none of them can run, whatever the thresholds.
        o.skip(
            "CODE-1..4",
            "account_type",
            "Which accounts are expense, asset (capex), prepaid, or balance sheet? "
            "Add an account_type column or give the account ranges.",
        )
    else:
        if cap is None:
            o.skip(
                "CODE-1",
                "capex_threshold",
                "What is the unit-cost threshold for capitalization?",
            )
            o.skip(
                "CODE-2",
                "capex_threshold",
                "What is the unit-cost threshold for capitalization?",
            )
        if mat is None:
            o.skip(
                "CODE-3",
                "materiality",
                "Below what amount should a finding be noted but not raised?",
            )
    for r in coding_rows:
        item = g(r, "id", "line_id", default=r["_src"])
        amt = D(g(r, "amount", "total"), Decimal(0))
        unit = D(g(r, "unit_price"), amt)
        life = D(g(r, "useful_life_months"), Decimal(0))
        atype = g(r, "account_type").lower()
        cat = g(r, "category").lower()
        hit = False
        if cap is not None:
            if atype == "expense" and unit >= cap and life > D(a.life_months):
                o.add(
                    "CODE-1 capex on expense account",
                    item,
                    "SEND_BACK",
                    f"unit price >= capex threshold and life > {a.life_months} months, coded to expense",
                    f"unit {money(unit)} against threshold {money(cap)}; life {life} m",
                    r["_src"],
                    amt,
                )
                hit = True
            if atype == "asset" and (unit < cap or "service" in cat):
                o.add(
                    "CODE-2 expense item on asset account",
                    item,
                    "SEND_BACK",
                    "below capex threshold or a service, coded to an asset account",
                    "unit {} against threshold {}; category {}".format(
                        money(unit), money(cap), cat or "-"
                    ),
                    r["_src"],
                    amt,
                )
                hit = True
        if mat is not None:
            s0, s1 = date(g(r, "service_start")), date(g(r, "service_end"))
            if atype == "expense" and s0 and s1 and (s1 - s0).days > 366 and amt >= mat:
                o.add(
                    "CODE-3 prepaid candidate",
                    item,
                    "CONDITION",
                    "service period over 12 months billed up front; expense over the period (prepaid)",
                    f"{s0} to {s1} ({(s1 - s0).days} days)",
                    r["_src"],
                    amt,
                )
                hit = True
        if atype == "balance_sheet":
            o.add(
                "CODE-4 expense on balance-sheet account",
                item,
                "SEND_BACK",
                "expensed line coded to a balance-sheet account",
                g(r, "account"),
                r["_src"],
                amt,
            )
            hit = True
        if (
            a.project_required
            and atype == "expense"
            and g(r, "project") in ("", "0", "0000", "none")
        ):
            o.add(
                "CODE-5 project missing",
                item,
                "CONDITION",
                "expensed line has no project code",
                "project={!r}".format(g(r, "project")),
                r["_src"],
                amt,
            )
            hit = True
        prior_key = (g(r, "vendor").upper(), g(r, "item").upper())
        prior = hist.get(prior_key, [])
        prior_accts = hist_accounts.get(prior_key, [])
        if prior_accts and g(r, "account") not in prior_accts:
            o.add(
                "CODE-6 differs from prior buys",
                item,
                "CONDITION",
                "same vendor + item was coded differently before",
                "this {} against prior {}".format(
                    g(r, "account"), ",".join(prior_accts)
                ),
                r["_src"]
                + " / "
                + ",".join(h["_src"] for h in prior[:_MAX_PRIOR_SOURCES])
                + (
                    f" and {len(prior) - _MAX_PRIOR_SOURCES} more"
                    if len(prior) > _MAX_PRIOR_SOURCES
                    else ""
                ),
                amt,
            )
            hit = True
        ran = (
            ([] if cap is None or not atype else ["capex threshold"])
            + ([] if mat is None or not atype else ["prepaid"])
            + (["account type"] if atype else [])
            + (["project"] if a.project_required and atype else [])
            + (["prior coding"] if prior_accts else [])
        )
        if not hit and ran:
            o.clear(
                "CODE",
                item,
                "account {} ({}): no issue in the checks that ran ({})".format(
                    g(r, "account"), atype, ", ".join(ran)
                ),
            )
    o.dump()
