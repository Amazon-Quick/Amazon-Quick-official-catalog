---
description: "Module 3 contract and terms checks: ceilings, rate cards, renewal dates, and billing against the contract. Read when a contract is in the review."
last_updated: 2026-11-24
---
# Module 3: Contract and terms

Goal: the PO or invoice stays inside what the contract allows: value, dates, rates, payment terms, and no unwanted renewal.

Arguments (pass them as a list to `pir_run`, for example `pir_run(["contract", ...])`; add `--input <saved message>` to use a pasted message): `contract --contract K.csv --pos P.csv [--rates RC.csv] [--change-orders CO.csv] --as-of <date> [--renewal-warn-days 90]`

## Script rules
| Rule | Hit when | Severity |
|---|---|---|
| CON-0 no contract | PO names a contract not on file | CONDITION |
| CON-1 over contract ceiling | cumulative PO value (in PO-date order) > ceiling + approved change orders; $ = amount above ceiling | HOLD |
| CON-2 PO outside contract term | PO start/end outside contract start/end | SEND_BACK |
| CON-3 payment terms shorter | PO pays in fewer days than the contract (cash leaves early) | CONDITION |
| CON-4 item not on rate card | PO role/item absent from the rate card | SEND_BACK |
| CON-5 price above rate card | PO unit price > contract rate; $ = (price - rate) x qty | SEND_BACK |
| CON-6 auto-renewal | auto-renew contract whose notice deadline is within the warning window, or has passed | INFO |

## Judgment rules
- Read the executed copy. A draft, unsigned, or "clean" version is not the contract; say so.
- Ceiling includes only approved change orders. A change order that is drafted but not approved does not raise it.
- Change order review: the revised total is re-tested for ceiling, approval tier (module 5) and budget (module 2). A change order that moves the total into a higher tier needs that tier's approver.
- Annual or FTE pricing: convert to the rate card's unit before comparing (state the hours basis, for example 2,080 h per year, as ASSUMPTION unless the contract says).
- Billing method: if the contract says level monthly billing, milestone, or time and materials (T&M), the PO and invoices should follow it.
- Auto-renewal: give the notice deadline date and ask the owner whether to renew, renegotiate, or end it. Never assume intent.
- Escalation clauses: if a rate rose, check the contract allows it on that date and by that %.
- Cite the clause number from the contract for every finding; if the clause cannot be found, say "clause not located".

## Not checked when
No contract supplied: list "Contract and terms: no contract on file" under Not checked and ask for the executed copy if the spend is above materiality.
