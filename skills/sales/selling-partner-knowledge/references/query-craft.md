---
description: "How to turn a developer's SP-API question into effective natural-language searches of the knowledge base: phrasing rules, choosing the approach by intent, triaging by confidence, and handling genuine gaps."
last_updated: "2026-09-15"
origin: original
---

# Query craft: searching the SP-API knowledge base well

The main knob you control on the search operation is the query string, so retrieval quality depends almost entirely on phrasing.

## Rules
1. Natural-language questions, not keyword fragments. The index is tuned for well-formed questions.
   - Good: "How do I subscribe to order change notifications?"
   - Weak: "order notification subscribe"
2. Keep each query under about 30 words. Long queries dilute relevance.
3. Preserve technical identifiers exactly: operation names, parameters, error codes, capitalization (getOrders, x-amzn-RateLimit-Limit, QuotaExceeded). Do not paraphrase an identifier.
4. One intent per query. If the developer asked a multi-part question, search each part separately rather than cramming them together.
5. Spend the budget on distinct phrasings, not pagination. If the first phrasing is thin, reformulate 3 to 5 times with different angles before concluding the docs lack the topic:
   - the concept: "How does the Feeds API upload flow work?"
   - the operation: "createFeedDocument request and response"
   - the section: browse the section instead of searching
   - the symptom: "Why does my feed stay in IN_PROGRESS status?"

## Choosing the approach by intent
- Concept / how it works: search, then fetch the top hits and synthesize.
- Getting started / onboarding / registration: browse the section first (no search).
- Which API for a use case: search the use case, map to APIs, present a decision table.
- Exact API contract / schema: get the operation spec by operationId, or search the schema doc.
- Does-X-support / availability: identify the dimensions (marketplace, API, feature variant), search each, present the breakdown; do not force a single yes/no when support is partial.

## Triaging results
- Rank by confidence. Anchor the answer on VERY_HIGH and HIGH; use MEDIUM and LOW only as leads to verify by fetching the doc.
- Read before you answer. Snippets are for triage; fetch the chosen document ids and answer from the full content, with the url as the citation.
- When searches disagree, present the relevant findings rather than silently picking one.

## When the docs genuinely do not cover it
After 3 to 5 varied searches with no good hit: state what is missing, give any partial guidance the docs do support, point to the official resources (see design-and-code.md), and do not fill the gap from general knowledge.
