---
description: "Field mapping for a small-business accounting package onto the canonical schema. Read only when the profile names this system kind."
last_updated: 2026-11-24
---
# Mapping: small-business accounting package

Load when the profile names a small-business accounting package or a spreadsheet-run business with no purchasing tool.

| Canonical | Typical source | Note |
|---|---|---|
| requisition | Often none: an email, chat message, or quote is the request | use the quote date as the request date and say so |
| po | Purchase order if the package has them; else the quote or order confirmation | without a PO, module 5 checks the approver against the matrix on the bill total |
| vendor | Supplier / contact name | normalize spelling before duplicate tests |
| account, account_type | Expense or asset account from the chart of accounts list | small charts often have one "equipment" asset account: CODE-1 still applies |
| cost_center / project | Class, location, tag, or tracking category | use whatever the business uses for the profile grain |
| receipt | Rarely recorded: ask who confirmed delivery | 3-way match becomes 2-way plus confirmation |
| invoice | Bill: number, date, lines, total | duplicate test on supplier + normalized number + amount |
| budget | Budget report or a spreadsheet by account x month | |
| actuals | Profit and loss by account x month | |
| open commitment | Usually not tracked: open POs or signed quotes not yet billed | ask; if none, say commitments were not available |
| contract | Signed quote, statement of work, or subscription terms | auto-renewals on subscriptions are the common risk |

## Quirks
- Cash-basis books record expense at payment: out-of-period tests compare service dates to the bill date and say which basis is used.
- Card and expense-claim purchases bypass POs: include them in split detection when the user supplies them.
- Keep questions short; the approver is often the owner.
