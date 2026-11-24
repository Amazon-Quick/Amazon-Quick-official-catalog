"""
description: Invoice checks INV-1 to INV-9 (3-way match, duplicates, out-of-period) and PO burn for the purchase and invoice review engine.
last_updated: 2026-11-24
"""

import datetime as dt
import math
from collections import Counter, defaultdict
from decimal import Decimal

from pir_state import ClarificationNeeded
from pir_tables import _process_input, read_table
from pir_values import D, Out, _pct, date, g, money, norm_ref

# Most earlier submissions one submission is compared with, per INV-9 test.
_MAX_DUP_PAIRS = 10


def _row_sig(litem):
    """Every value on an invoice row except its source line; equal signatures = byte-identical rows."""
    return tuple(sorted((k, str(v).strip()) for k, v in litem.items() if k != "_src"))


def _deal_copies(ls, k, sig):
    """Deal rows that are k identical copies of one line set into k copies (file order kept)."""
    counts, seen, copies = (
        Counter(sig(litem) for litem in ls),
        Counter(),
        [[] for _ in range(k)],
    )
    for litem in ls:
        s_ = sig(litem)
        copies[seen[s_] // (counts[s_] // k)].append(litem)
        seen[s_] += 1
    return copies


def _split_submissions(ls):
    """Split the rows that share one vendor + invoice number into separate submissions.

    A resubmitted invoice must not look like extra lines on the original. Rows are split when
    (a) every row is header-only (no line, qty or amount): each row is one submission;
    (b) every row is a register row (an amount but no line, qty or PO) and no stated_total equal to
        their sum shows they are one invoice: each row is one submission;
    (c) every row has an invoice_date and there is more than one date: one submission per date;
    (d) the rows are k >= 2 identical copies of a line set whose stated_total equals one copy;
    (e) there is no stated_total and the rows are k >= 2 byte-identical copies of a line set.
    Otherwise the rows are one invoice. Returns (submissions earliest first, how they were split).
    """
    if len(ls) < 2:
        return [ls], None

    def by_date(part):
        return date(g(part[0], "invoice_date")) or dt.date.min

    stated = D(g(ls[0], "stated_total"))
    tot = sum((D(g(litem, "amount"), Decimal(0)) for litem in ls), Decimal(0))
    if not any(
        g(litem, "line") or g(litem, "qty") or g(litem, "amount") for litem in ls
    ):
        return sorted([[litem] for litem in ls], key=by_date), "header rows"
    if (
        not any(g(litem, "line") or g(litem, "qty") or g(litem, "po") for litem in ls)
        and stated != tot
    ):
        return sorted([[litem] for litem in ls], key=by_date), "register rows"
    dates = [g(litem, "invoice_date") for litem in ls]
    if all(dates) and len(set(dates)) > 1:
        parts = {}
        for litem, d0 in zip(ls, dates, strict=False):
            parts.setdefault(d0, []).append(litem)
        return sorted(parts.values(), key=by_date), "dates"
    if stated:
        k = tot / stated
        if k >= 2 and k == k.to_integral_value():
            k = int(k)

            def sig(litem):
                return tuple(
                    g(litem, c)
                    for c in (
                        "po",
                        "line",
                        "qty",
                        "unit_price",
                        "amount",
                        "service_start",
                        "service_end",
                    )
                )

            if all(c % k == 0 for c in Counter(sig(litem) for litem in ls).values()):
                return _deal_copies(ls, k, sig), "stated total"
    if stated is None:
        k = 0
        for c in Counter(_row_sig(litem) for litem in ls).values():
            k = math.gcd(k, c)
        if k >= 2:
            return _deal_copies(ls, k, _row_sig), "identical rows"
    return [ls], None


def cmd_invoice(a):
    if getattr(a, "input", None):
        _process_input(a, "invoice")
    ps, pe, _asof = date(a.period_start), date(a.period_end), date(a.as_of)
    o = Out(
        "invoice",
        {
            "period": [a.period_start, a.period_end],
            "qty_tol": a.qty_tol,
            "price_tol": a.price_tol,
            "dup_window_days": a.dup_window_days,
            "as_of": a.as_of,
        },
    )
    ptol = D(a.price_tol)
    if ptol is None:
        o.skip(
            "INV-4",
            "invoice_tolerance",
            "What is the invoice unit-price tolerance (for example 0.02 for 2%)?",
        )
    po_rows = read_table(a.po_lines, "po_lines")
    po = {(g(p, "po"), g(p, "line")): p for p in po_rows}
    po_by_number = defaultdict(
        list
    )  # PO number -> its lines, so no lookup scans the PO table
    for (pono, _line), p in po.items():
        po_by_number[pono].append(p)
    if len(po) != len(po_rows):
        raise ClarificationNeeded(
            "There is more than one PO row with the same PO and line. Are these corrections or separate lines?",
            str(a.po_lines),
        )
    if not po:
        o.skip(
            "INV-3",
            "po_lines",
            "No usable PO table was supplied. Add it to check PO matching.",
        )
    rec = defaultdict(Decimal)
    rec_rows = read_table(a.receipts, "receipts")
    for r in rec_rows:
        rec[(g(r, "po"), g(r, "line"))] += D(g(r, "qty_received"), Decimal(0))
    have_receipts, have_period = bool(rec_rows), bool(ps and pe)
    if not have_receipts:
        o.skip(
            "INV-5",
            "receipts",
            "No receipt data, so the 3-way match (INV-5) was not tested; only PO against "
            "invoice was checked. Who confirmed delivery or the work?",
        )
    if not have_period:
        o.skip(
            "INV-7",
            "review_period",
            "What review period (start and end date) should the invoices be "
            "checked against?",
        )
    lines = read_table(a.invoices, "invoices")
    have_line_math = bool(lines) and all(
        D(g(litem, "qty")) is not None and D(g(litem, "unit_price")) is not None
        for litem in lines
    )
    have_stated_totals = bool(lines) and all(
        D(g(litem, "stated_total")) is not None for litem in lines
    )
    have_links = bool(lines) and all(g(litem, "po") for litem in lines)
    if not have_line_math:
        o.skip(
            "INV-2",
            "qty/unit_price",
            "Quantity or unit price is absent on one or more invoice rows; line arithmetic is not checked for those rows.",
        )
    if not have_stated_totals:
        o.skip(
            "INV-1",
            "stated_total",
            "A stated invoice total is absent on one or more invoices; footing is not checked for those invoices.",
        )
    if not have_links:
        o.skip(
            "INV-3..6",
            "po/line",
            "A PO reference is absent on one or more invoice rows; matching is not checked for those rows.",
        )
    inv = defaultdict(list)
    for litem in lines:
        inv[(g(litem, "vendor").upper(), g(litem, "invoice_no"))].append(litem)
    # One entry per submission: the first keeps the invoice number as its item id, a resubmission
    # becomes "<number> (submission N)" so the original and the copy get separate verdicts. A number
    # that more than one vendor uses also carries the vendor, "<number> (<vendor>)", so two vendors'
    # invoices are never merged into one verdict or one total.
    shared = {no for no, n in Counter(no for _v, no in inv).items() if n > 1}
    subs, n_subs = [], {}
    for (v, no), ls in inv.items():
        parts, how = _split_submissions(ls)
        for k, part in enumerate(parts):
            quals = ([g(part[0], "vendor") or "no vendor"] if no in shared else []) + (
                [f"submission {k + 1}"] if k else []
            )
            item = no + (" ({})".format(", ".join(quals)) if quals else "")
            subs.append((v, no, k, item, part, how))
            n_subs[item] = len(parts)
    subs.sort(
        key=lambda x: (
            date(g(x[4][0], "invoice_date")) or dt.date.min,
            x[0],
            x[1],
            x[2],
        )
    )
    billed_qty = defaultdict(Decimal)
    billed_amt = defaultdict(Decimal)
    heads, inv_items, match_rows = [], [], []
    for v, no, _k, item, ls, how in subs:
        tot = sum((D(g(litem, "amount"), Decimal(0)) for litem in ls), Decimal(0))
        stated = D(g(ls[0], "stated_total"))
        if stated is not None and stated != tot:
            o.add(
                "INV-1 does not foot",
                item,
                "HOLD",
                "stated total differs from sum of lines",
                f"stated {money(stated)} against lines {money(tot)}",
                ls[0]["_src"],
                abs(stated - tot),
            )
        # Rows repeated byte-for-byte that could not be told apart as separate submissions.
        sigs, first = Counter(_row_sig(litem) for litem in ls), {}
        rep = [litem for litem in ls if sigs[_row_sig(litem)] > 1]
        if rep:
            for litem in rep:
                first.setdefault(_row_sig(litem), litem)
            extra = sum(
                (
                    D(g(litem, "amount"), Decimal(0)) * (sigs[s_] - 1)
                    for s_, litem in first.items()
                ),
                Decimal(0),
            )
            o.add(
                "INV-9 duplicate invoice (review)",
                item,
                "CONDITION",
                "the same row appears more than once on this invoice: confirm it is billed once, not twice",
                f"{len(rep)} identical rows",
                ";".join(litem["_src"] for litem in rep),
                extra,
            )
        heads.append(
            (v, no, item, date(g(ls[0], "invoice_date")), tot, ls[0]["_src"], how)
        )
        inv_items.append(
            {
                "item": item,
                "invoice_no": no,
                "vendor": g(ls[0], "vendor"),
                "amount": money(stated if stated is not None else tot),
                "source": ls[0]["_src"],
            }
        )
        for litem in ls:
            key = (g(litem, "po"), g(litem, "line"))
            q, u, amt = (
                D(g(litem, "qty")),
                D(g(litem, "unit_price")),
                D(g(litem, "amount")),
            )
            if (
                q is not None
                and u is not None
                and (q * u - amt).copy_abs() > Decimal("0.01")
            ):
                o.add(
                    "INV-2 line math",
                    item,
                    "HOLD",
                    "qty x unit price differs from line amount",
                    f"{q} x {money(u)} against {money(amt)}",
                    litem["_src"],
                    (q * u - amt).copy_abs(),
                )
            p = po.get(key) if key[0] else None
            if not p:
                # A PO given with one line and no line number (common when it was pasted as prose) is that line.
                same = po_by_number.get(key[0], [])
                if len(same) == 1 and not g(same[0], "line"):
                    p = same[0]
            row = {
                "item": item,
                "po_line": "{}/{}".format(*key),
                "ordered_qty": None,
                "received_qty": None,
                "invoiced_qty": str(q) if q is not None else None,
                "invoiced_qty_cumulative": None,
                "po_price": None,
                "invoice_price": money(u) if u is not None else None,
                "qty_match": "Not checked (no PO line)",
                "price_match": "Not checked (no PO line)",
                "duplicate_check": "Pass",
                "source": litem["_src"],
            }
            match_rows.append(row)
            s0, s1 = date(g(litem, "service_start")), date(g(litem, "service_end"))
            if ps and pe and s0 and s1 and (s0 < ps or s1 > pe):
                o.add(
                    "INV-7 out-of-period line",
                    item,
                    "CONDITION",
                    "service dates outside the review period: accrue/charge to the right period",
                    f"{s0}..{s1} against period {ps}..{pe}",
                    litem["_src"],
                    amt,
                )
            if not p and po and key[0] and key[1]:
                o.add(
                    "INV-3 no PO line",
                    item,
                    "HOLD",
                    "invoice line names no PO line on file",
                    "{}/{}".format(*key),
                    litem["_src"],
                    amt,
                )
            if not p:
                if po and key[0] and not key[1]:
                    o.skip(
                        "INV-3..6",
                        "line",
                        f"Invoice {item} has no line number and cannot be matched to a unique PO line.",
                    )
                continue
            pend = date(g(p, "service_end", "end_date", "end"))
            if pend and s1 and s1 > pend:
                o.add(
                    "INV-8 work after PO end",
                    item,
                    "HOLD",
                    "service after PO period of performance",
                    f"service end {s1} against PO end {pend}",
                    litem["_src"],
                    amt,
                )
            pp = D(g(p, "unit_price"))
            row.update(
                ordered_qty=g(p, "qty") or None,
                po_price=money(pp) if pp is not None else None,
            )
            if u is None:
                row["price_match"] = "Not checked (no invoice unit price)"
                o.skip("INV-4", "unit_price", f"Invoice {item} has no unit price.")
            elif pp is None:
                row["price_match"] = "Not checked (no PO unit price)"
            elif ptol is None:
                row["price_match"] = (
                    "Not checked (no price tolerance); equal to PO price"
                    if u == pp
                    else "Not checked (no price tolerance); differs from PO price"
                )
            elif u > pp * (1 + ptol):
                row["price_match"] = "Fail ({} over PO, tolerance {})".format(
                    _pct((u - pp) / pp) if pp else "n/a",
                    _pct(ptol),
                )
            else:
                row["price_match"] = "Pass"
            if (
                ptol is not None
                and pp is not None
                and u is not None
                and u > pp * (1 + ptol)
            ):
                o.add(
                    "INV-4 price over PO",
                    item,
                    "HOLD",
                    "invoice unit price above PO price beyond tolerance",
                    f"{money(u)} against PO {money(pp)}",
                    litem["_src"] + " / " + p["_src"],
                    (u - pp) * q if q is not None else amt,
                )
            billed_amt[g(litem, "po")] += amt
            if q is None:
                row["qty_match"] = "Not checked (no invoice quantity)"
                o.skip("INV-5..6", "qty", f"Invoice {item} has no quantity.")
                continue
            billed_qty[key] += q
            row["invoiced_qty_cumulative"] = str(billed_qty[key])
            po_qty = D(g(p, "qty"))
            over_ordered = po_qty is not None and billed_qty[key] > po_qty
            if have_receipts:
                row["received_qty"] = str(rec[key])
                over_rec = billed_qty[key] > rec[key] + D(a.qty_tol)
                row["qty_match"] = (
                    "Fail (billed more than received)"
                    if over_rec
                    else "Fail (billed more than ordered)"
                    if over_ordered
                    else "Pass"
                )
            else:
                row["qty_match"] = (
                    "Fail (billed more than ordered)"
                    if over_ordered
                    else "Not checked (no receipt data); within ordered qty"
                    if po_qty is not None
                    else "Not checked (no receipt data or PO quantity)"
                )
            if have_receipts and billed_qty[key] > rec[key] + D(a.qty_tol):
                o.add(
                    "INV-5 billed more than received",
                    item,
                    "HOLD",
                    "cumulative invoiced qty above received qty (3-way match)",
                    f"invoiced {billed_qty[key]} against received {rec[key]}",
                    litem["_src"],
                    (billed_qty[key] - rec[key]) * u if u is not None else amt,
                )
            if po_qty is not None and billed_qty[key] > po_qty:
                o.add(
                    "INV-6 billed more than ordered",
                    item,
                    "HOLD",
                    "cumulative invoiced qty above PO qty",
                    "invoiced {} against PO {}".format(billed_qty[key], g(p, "qty")),
                    litem["_src"],
                    (billed_qty[key] - D(g(p, "qty"), Decimal(0))) * u
                    if u is not None
                    else amt,
                )
    # INV-9 across submissions. Each submission is compared with at most _MAX_DUP_PAIRS earlier ones
    # per test (the earliest copies of its number, the nearest same-amount ones), which bounds the
    # work and the findings for a batch of many copies. Earlier submissions are indexed by vendor + normalized number and by
    # vendor + amount, so each submission is compared only with the ones that can match it. heads is
    # in date order, so the amount scan stops once it passes the duplicate window.
    by_ref, by_amount = defaultdict(list), defaultdict(list)
    for v, no, item, d, tot, src, how in heads:
        ref = norm_ref(no)
        for no2, item2, src2 in by_ref[(v, ref)][:_MAX_DUP_PAIRS]:
            tier = "exact" if no == no2 else "strong"
            what = "same vendor, same invoice number after normalizing"
            if tier == "exact" and how == "identical rows":
                what += "; the rows repeat byte-for-byte and no stated total shows them to be one invoice"
            o.add(
                f"INV-9 duplicate invoice ({tier})",
                item,
                "HOLD",
                what,
                f"{item} ~ {item2}",
                src + " / " + src2,
                tot,
            )
        if d:
            compared = 0
            for ref2, item2, d2, src2 in reversed(by_amount[(v, tot)]):
                if abs((d - d2).days) > a.dup_window_days or compared >= _MAX_DUP_PAIRS:
                    break
                compared += 1
                if ref2 == ref:
                    continue
                o.add(
                    "INV-9 duplicate invoice (review)",
                    item,
                    "CONDITION",
                    "same vendor and amount within window",
                    f"{item} and {item2} both {money(tot)}, {abs((d - d2).days)} days apart",
                    src + " / " + src2,
                    tot,
                )
        by_ref[(v, ref)].append((no, item, src))
        if d:  # an undated submission can never be in a duplicate window
            by_amount[(v, tot)].append((ref, item, d, src))
    runout = []
    for pono in sorted(po_by_number):
        po_group = po_by_number[pono]
        if any(
            D(g(p, "amount")) is None
            and (D(g(p, "qty")) is None or D(g(p, "unit_price")) is None)
            for p in po_group
        ):
            o.skip(
                "PO burn",
                "po_value",
                f"PO {pono} has no complete value or quantity/price basis; remaining value is not checked.",
            )
            runout.append(
                {
                    "po": pono,
                    "value": None,
                    "billed": money(billed_amt[pono]),
                    "remaining": None,
                    "pct_used": "Not checked",
                }
            )
            continue
        val = sum(
            (
                (D(g(p, "qty"), Decimal(0)) * D(g(p, "unit_price"), Decimal(0)))
                or D(g(p, "amount"), Decimal(0))
                for p in po_group
            ),
            Decimal(0),
        )
        rem = val - billed_amt[pono]
        runout.append(
            {
                "po": pono,
                "value": money(val),
                "billed": money(billed_amt[pono]),
                "remaining": money(rem),
                "pct_used": str((billed_amt[pono] / val * 100).quantize(Decimal("0.1")))
                if val
                else "n/a",
            }
        )
    o.extra["po_burn"] = runout
    o.extra["invoice_items"] = inv_items
    findings_by_item = defaultdict(list)
    for f in o.findings:
        findings_by_item[f["item"]].append(f)
    dup_status = {}  # item -> duplicate_check word, computed once per item
    for item, found in findings_by_item.items():
        dups = [f for f in found if f["rule"].startswith("INV-9")]
        if any(f["severity"] == "HOLD" for f in dups):
            dup_status[item] = "Fail (possible duplicate)"
        elif dups:
            dup_status[item] = "Confirm (possible duplicate)"
    for row in match_rows:
        if row["item"] in dup_status:
            row["duplicate_check"] = dup_status[row["item"]]
    o.extra["match_rows"] = match_rows
    # The clearance note names only the checks that actually ran. The first of several submissions
    # of one number is not called "no duplicate": its later copies carry INV-9.
    note = "No exception found in the checks run"
    if have_stated_totals:
        note += "; stated totals foot"
    if have_line_math:
        note += "; line arithmetic checked"
    skipped = [
        n
        for n, ran in (
            ("price tolerance (INV-4)", ptol is not None),
            ("receipt (INV-5)", have_receipts),
            ("review period (INV-7)", have_period),
        )
        if not ran
    ]
    tail = "; not checked: " + ", ".join(skipped) if skipped else ""
    for _v, _no, _k, item, _ls, _how in subs:
        if not findings_by_item[item]:
            dup = (
                ", no duplicate"
                if n_subs[item] == 1
                else f", first of {n_subs[item]} submissions of this invoice number (the later ones carry INV-9)"
            )
            o.clear("INV-1..9", item, note + dup + tail)
    o.dump()
