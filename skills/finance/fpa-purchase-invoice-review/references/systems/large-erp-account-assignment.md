---
description: "Field mapping for a large ERP with account assignment categories onto the canonical schema. Read only when the profile names this system kind."
last_updated: 2026-11-24
---
# Mapping: large ERP, account assignment categories

Load only when the profile names an ERP of this kind. Field names below are typical standard names; customers rename and extend them, so confirm with the user's export headers.

| Canonical | Typical source field / screen | Note |
|---|---|---|
| po, line | Purchasing document, Item (PO header / item tables) | |
| vendor | Vendor / supplier number + name | match on number, show the name |
| qty, unit_price | Order quantity, Net price per price unit | divide by price unit when it is not 1 |
| account_type | Account assignment category on the item | blank = stock (inventory); K = cost center; P/F = project or order; A = asset |
| account | G/L account on the account assignment | stock lines post to an inventory / GR-IR account by design: not a CODE-4 finding |
| cost_center, project | Cost center; WBS element or internal order | |
| po_date, start, end | Document date; validity start/end or delivery date | |
| receipt (qty_received, receipt_date) | Goods receipt / service entry lines in PO history (movement type for GR; reversals net off) | |
| invoice (invoice_no, invoice_date, amount) | Logistics invoice document; vendor reference field holds the supplier's number | duplicate test on the vendor reference, not the internal document number |
| open commitment | PO value less invoiced, from PO history; or a commitments report | |
| budget, actuals | Plan and actual line items by cost center / cost element / period, or a planning tool export | |
| contract_id, ceiling | Outline agreement (contract) number, target value | release orders count against the target value |

## Quirks
- GR/IR clearing balances older than the review period are candidates for module 6 follow-up, not a finding on the current invoice.
- Price unit and order unit can differ from the invoice unit; convert before INV-4.
- Payment terms keys map to days through the terms configuration; ask for the days if only a key is exported.
- Parked or held invoices are not yet posted: include them in the duplicate test, not in actuals.
