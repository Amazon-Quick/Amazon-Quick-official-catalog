---
description: "Field mapping for a cloud procure-to-pay suite onto the canonical schema. Read only when the profile names this system kind."
last_updated: 2026-11-24
---
# Mapping: cloud procure-to-pay suite

Load only when the profile names a cloud procure-to-pay suite of this kind. Confirm names against the user's export.

| Canonical | Typical source | Note |
|---|---|---|
| requisition id, requester, date | Requisition number, Requested by, Submitted date | the page text is the source of truth; the approval email can be stale |
| justification | Justification / comments field, attachments | read earlier approvers' comments before asking the obvious question |
| account string | Billing / account segments (company-location-cost center-account-project ...) | split the string into grain columns per the profile |
| amount | Line total excluding freight and tax | freight and tax are often added by the supplier at invoice time: test them in module 5, not as a missing-field finding |
| need-by / service dates | Need-by date, start/end date on the line | check before claiming an after-the-fact purchase |
| quote | Attachments (PDF); quote number may encode the quote date | expired quotes go to PRC-3 |
| po, line | Order number and line, once the requisition is approved | |
| receipt | Receipt / receiving lines | services often receipt on invoice approval |
| invoice | Invoice number, supplier, lines, totals step | duplicate test on supplier + normalized number |
| contract_id, ceiling | Contract record (max value, term, auto-renew) | |
| approval chain | Approval chain list on the document | an "approval complete" node is the end marker, not an approver |
| budget | Budget lines if the suite holds them; otherwise the ERP or planning file | |

## Quirks
- Payment terms on the PO may be overridden by policy (for example a standard net-days term); compare to the contract, not to the quote.
- Scanned PDF attachments with almost no text can't be read: ask the user for a text copy.
- Change requests on an existing order are change orders: re-test the full revised total.
