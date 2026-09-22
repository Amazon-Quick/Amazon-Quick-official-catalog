---
description: "How to read a listing's issues[] and status from the Selling Partner API listings search operation: the status states, issue object fields, severities, enforcement actions, and the priority order for fixing."
last_updated: 2026-09-15
origin: original
---

# Listing Issue Taxonomy

Reference detail for reading a listing's `issues[]` and `status` from the Selling Partner API listings search operation. This describes what the operation returns (not its inputs, which are in the connector tool schema), and it is loaded on demand so SKILL.md stays lean. Grounded in the SP-API Manage Listings Issues guide.

## Listing status (`summaries[].status`)

A listing's status is an array of independent states:

| Status | Question it answers | If missing |
|--------|---------------------|-----------|
| BUYABLE | Can customers buy it right now? | Not purchasable, usually fully suppressed or out of stock |
| DISCOVERABLE | Does it appear in search? | Search-suppressed, buyable by direct link only |

A listing can be BUYABLE but not DISCOVERABLE (search-suppressed), or neither (fully suppressed). BUYABLE and DISCOVERABLE both present with no ERROR issue means healthy.

## Issue object fields

Each entry in `issues[]` carries:

- `code`: Amazon's error code (for example 90220, 100708).
- `message`: human-readable description with the fix.
- `severity`: ERROR or WARNING (see below).
- `attributeName` or `attributeNames`: the attribute(s) at fault, which is what you fix.
- `categories`: issue category, for example MISSING_ATTRIBUTE, INVALID_ATTRIBUTE, INVALID_PRICE.
- `enforcements.actions[].action`: what Amazon did to the listing (see below).

## Severity

| Severity | Meaning | Blocks the listing? |
|----------|---------|---------------------|
| ERROR | Prevents acceptance, or makes the listing non-buyable or search-suppressed | Yes, fix first |
| WARNING | Quality problem; the listing stays live | No, surface calmly, do not alarm |

Example: a pricing issue with code 100708 and category INVALID_PRICE is a WARNING ("not eligible to be the Featured Offer due to uncompetitive price"). The update is accepted and the listing stays active; it just may not win the Featured Offer.

## Enforcement actions (`enforcements.actions`)

What Amazon has done to the listing because of the issue. Priority order for fixing:

| Action | Effect | Urgency |
|--------|--------|---------|
| LISTING_SUPPRESSED | Entire listing not buyable | Highest, lost sales now |
| SEARCH_SUPPRESSED | Buyable but not in search results | High, customers cannot find it |
| ATTRIBUTE_SUPPRESSED | One attribute value hidden | Medium |
| CATALOG_ITEM_REMOVED | Item removed from the catalog | Investigate, may need support |

No enforcement action plus WARNING means a quality nudge, not a blocker.

## Priority rule

Same order as the SKILL.md triage step (LISTING_SUPPRESSED, then SEARCH_SUPPRESSED, then ATTRIBUTE_SUPPRESSED, then WARNING; ERROR before WARNING). Lead with the issue that costs the seller the most sales.

## Where issues come from

- Synchronous: returned directly in a listings patch response that failed validation.
- Asynchronous: surfaced via the listings search operation with `includedData=issues`. An ACCEPTED submission can still produce issues during downstream catalog processing, so re-scan to catch them.

Note on available operations: this skill uses only the listings search and listings patch operations. Other SP-API listings operations exist in the wider API but may not be exposed by the connector; use only what the connector provides, and re-scan on demand to catch asynchronous issues.
