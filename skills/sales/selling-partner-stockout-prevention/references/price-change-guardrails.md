---
description: "The approval and safety rules for the one write action in this skill, a price change through the Selling Partner API listings patch operation: preview first, show the diff, require explicit approval, propose an auto-revert, and change one SKU at a time."
last_updated: 2026-09-15
origin: original
---

# Price-change guardrails

A price change is the only write action in this skill, and it is seller-initiated: the skill does not proactively recommend raising the price; it drafts one only when the seller asks to change price. When it does, the agent proposes the exact change and the seller disposes.

## Rules
1. Preview first. Always call the listings patch operation with mode VALIDATION_PREVIEW. This validates the patch without making a live change.
2. Show the diff. Present current then proposed price, the SKU, and the expected effect on days of cover before asking for anything.
3. Explicit approval. Do not run a live patch until the seller types "approve" (or supplies a modified price). Silence is not approval.
4. Always propose an auto-revert date. A stockout price increase is temporary. Tie the revert to the inbound shipment's delivery window so the price returns to normal once stock is replenished, and tell the seller the revert is manual unless they schedule it.
5. One change at a time. Draft each SKU's change as its own numbered item; never bundle multiple live writes into one approval.

## Listings patch operation essentials
- Required inputs: the seller identifier, `sku`, `marketplaceIds`, `productType`, `patches`, and the merchant account context.
- `patches` is a JSON Patch array (op/path/value). Only top-level listing attributes can be patched.
- An ACCEPTED response means the patch was submitted, not that the change is live yet. Confirm with the seller and verify afterward by re-reading the item.
