---
description: "Help text shown by the Help workflow (fpa-pir help)."
last_updated: 2026-11-24
---
# Purchase and Invoice Review: help

Checks requisitions, purchase orders, and supplier invoices before approval or payment, and recommends a verdict per item. It does not approve, reject, or pay anything.

**Checks it runs (only the ones that apply)**
1. Coding: account, cost center, project, and capital, operating, or prepaid
2. Budget fit: headroom after actuals and open commitments
3. Contract and terms: ceilings, rates, renewals
4. Price and competition: quotes, sole source, price history
5. Approval and policy: tiers, possible split POs, after-the-fact purchases
6. Invoice: 3-way match, possible duplicates, out-of-period

**Verdicts:** Hold, Send back, Approve with conditions, Ready to approve.

**What you provide**
- items: the requisitions, POs, invoices, quotes, contracts, or budget tables, pasted or attached
- profile_file (optional): your approval tiers, tolerances, and thresholds, kept in a file you choose

**Commands**
- `fpa-pir help`: show this menu
- `fpa-pir review`: start a review of the items you paste or attach

**Try saying**
- "Review this req before I approve it."
- "Is this a split PO?"
- "Run a 3-way match on this invoice against the PO above."

Outputs are informational and are not accounting, audit, or financial advice. Validate each verdict with a qualified accountant, finance controller, or procurement lead before approving or paying.
