---
description: "Module 6 invoice checks: 3-way and 2-way match, price and quantity tolerance, duplicate and out-of-period guards. Read when invoices are reviewed."
last_updated: 2026-11-24
---
# Module 6: Invoice

Goal: pay only for what was ordered, received, and contracted, once, in the right period, and know when the PO runs out.

Arguments (pass them as a list to `pir_run`, for example `pir_run(["invoice", ...])`; add `--input <saved message>` to use a pasted message): `invoice --invoices I.csv --po-lines PL.csv [--receipts GR.csv] --period-start <date> --period-end <date> --qty-tol 0 [--price-tol <profile>] --dup-window-days 30`

If `--price-tol` is omitted, INV-4 reports NOT RUN. With no receipts table, INV-5 reports NOT RUN; without `--period-start` and `--period-end`, INV-7 reports NOT RUN (pass the review period to `all` with `--period-start` and `--period-end`). All other INV rules always run. Qty tolerance defaults to 0 (exact match).

## Script rules
| Rule | Hit when | Severity |
|---|---|---|
| INV-1 does not foot | stated total differs from sum of lines | HOLD |
| INV-2 line math | qty x unit price differs from line amount by > 0.01 | HOLD |
| INV-3 no PO line | invoice line names no PO line on file | HOLD |
| INV-4 price over PO | invoice unit price > PO price x (1 + price tolerance) | HOLD |
| INV-5 billed more than received | cumulative invoiced qty > received qty + qty tolerance (3-way match) | HOLD |
| INV-6 billed more than ordered | cumulative invoiced qty > PO qty | HOLD |
| INV-7 out-of-period line | service dates outside the review period | CONDITION (accrue or charge to the right period) |
| INV-8 work after PO end | service end after PO end date (`end_date` / `service_end` on the PO line) | HOLD |
| INV-9 duplicate (exact / strong) | same vendor, same invoice number, or same after removing spaces, dashes, case and leading zeros | HOLD |
| INV-9 duplicate (review) | same vendor and amount within the window, different number; or the same row repeated byte-for-byte within one invoice that cannot be told apart as two submissions | CONDITION |

A vendor + invoice number that arrives twice is two submissions, not extra lines: rows with different invoice dates, one header-only row per submission, one register row (an amount but no line, qty, or PO) per submission unless a stated total equal to their sum shows one invoice, a line set repeated with a stated total equal to one copy, or, with no stated total, a line set repeated byte-for-byte. The later copy is item `<number> (submission 2)` and gets INV-9 (exact); the original keeps its own verdict and its clearance note says it is the first of several submissions. An invoice number used by more than one vendor carries the vendor in its item id, `<number> (<vendor>)`, so the vendors' invoices get separate verdicts and totals.

For speed on large batches, each submission is compared with at most 10 earlier submissions in each INV-9 test (the earliest copies of its number, and the nearest ones with the same amount).

`po_burn` gives each PO's value, billed, remaining, and % used. `invoice_items` gives each submission's amount (stated total, else the sum of its lines) for the batch totals.

## Judgment rules
- 3-way match: PO = what was agreed, receipt = what arrived or was performed, invoice = what is claimed. Pay the lowest of the three, and ask about the gap.
- Services with no receipt record: ask who confirmed the work, and treat their confirmation as the receipt.
- Time and materials (T&M): tie hours x rate to the rate card (module 3) and to timesheets when supplied; check daily hour caps, overtime approval, and the same person-day billed twice.
- Out-of-period: work in a prior period not accrued, or a future period billed early, goes to the right period; name both periods.
- Duplicates: the later copy is the item to confirm; the first is cleared unless it has its own issue.
- PO run-out: burn per day = billed / days in service window; projected run-out = last service end + remaining / burn. Label it "inference". If run-out falls before PO end, say so.
- Never write "overbilled"; write "billed amount not supported by the receipt / PO / contract".
- Draft a clarification or credit request only if the user asks; never send it.

## Not checked when
No invoice_tolerance in profile: INV-4 reports NOT RUN; ask what invoice price tolerance the team applies.
No receipts: INV-5 is "not tested - no receipt data"; say whether a 2-way match (PO against invoice) was done instead.
