---
description: "Field mapping for a large ERP with a segmented account string onto the canonical schema. Read only when the profile names this system kind."
last_updated: 2026-11-24
---
# Mapping: large ERP, segmented account string

Load only when the profile names an ERP of this kind. Confirm against the user's export headers.

| Canonical | Typical source | Note |
|---|---|---|
| po, line | PO number, line number (and shipment / distribution below the line) | coding sits on the distribution: one line can carry several accounts |
| account string | Charge account (segmented: company, cost center, account, project ...) | split into grain columns per the profile |
| account_type | Account type of the natural account segment (expense, asset, liability) | |
| requisition | Requisition number, preparer, need-by date | |
| receipt | Receipt transactions (receive, deliver, correct, return) | net returns and corrections before INV-5 |
| invoice | Payables invoice number, supplier, invoice date, lines, holds | existing holds (price, qty, receipt) already flag 3-way mismatches: list them |
| open commitment | Encumbrance or PO amount less billed | if encumbrance accounting is on, commitments may already be in budget-checked funds |
| budget, actuals | Budget balances or a planning export by account combination and period | funds-available results are the system's own headroom: compare to the script's |
| contract_id, ceiling | Blanket purchase agreement or contract purchase agreement, amount agreed | releases count against amount agreed |
| fiscal_calendar | Accounting calendar period names | map period names to YYYY-MM |

## Quirks
- Match approval level (2-, 3-, or 4-way) is set per line; a 2-way line has no receipt by design.
- Tolerances live in the system; take the user's numbers for `--price-tol` / `--qty-tol` if supplied.
- Prepayments are their own invoice type; do not treat them as duplicates of the standard invoice they later apply to.
