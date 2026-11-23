---
description: "Catalog tool parameters, segments, the parallel execution model, and the hand-off to Informatica data exploration for reading actual data."
last_updated: 2026-11-13
origin: original
---
# Tools & Execution Model — Full Reference

> Canonical source for SKILL.md §4 (Tools & Segments). Read when the agent is about to issue tool calls (especially multi-round scenarios or data-exploration hand-off).

**Contents:** search_assets — find assets by query + filters · get_asset_details — fetch typed asset by identity · Segments · Batching rules · Parallel execution model · Limitations (state when relevant) · Reading actual data — hand off to informatica-data-exploration · Enriching the hand-off prompt (MANDATORY)

Two read-only discovery tools. This skill does NOT enrich, edit, classify, or certify assets — those are steward workflows outside its scope. When a gap is found, the skill reports it and points to the steward; it never proposes to write to the catalog.

## `search_assets` — find assets by query + filters

Search the catalog by natural language (NL) or keyword. Returns a page of asset summaries — identity, `classType`, name, description, stakeholders, assetGroups — plus optional aggregations for narrowing and `suggested_next_steps` for iterative refinement. Always call this **first** to discover asset identities before drilling into `get_asset_details`.

**Parameters:** `query` (required; `*` = whole catalog), `mode` (`KEYWORD` default, `NL` fallback), `filterSpec` (typed filters — see [asset-types.md](asset-types.md) §3.4, [search-rules.md](search-rules.md)), `aggregationSpec` (max 1 aggregation, ≤20 buckets), `sortSpec` (max 2), `from`, `size` (default 20).

## `get_asset_details` — fetch typed asset by identity

Fetch full details of one asset by identity. Always returns a `resolvedSummary` (identity, name, type, location, description, stakeholders resolved to names/emails, assetGroups, timestamps) plus raw `systemAttributes`. Additional aspects are opt-in via `segments[]` — pick the minimum set for the intent (batching rules in SKILL.md §4).

**Parameters:** `assetIdentity` (required), `identityType` (`INTERNAL` = UUID default, `EXTERNAL` = path), `segments[]` (see below; default is `summary` only).

**Always use internal UUID (the `identity` field from search results) with the default `INTERNAL` identity type.** Do not use `identityType: EXTERNAL` — the `externalId` field includes a `~classType` suffix that the API rejects with 400. Do not attempt to construct external IDs from child asset paths. External IDs are only needed for the `data_explore` hand-off ("Reading actual data" below), where you pass the `externalId` value exactly as returned from search/details — never constructed.

## Segments

- **`summary`** (default) — core identity + lifecycle: name, `classType`, description, `certified`, rating, `assetLifecycle`, timestamps, stakeholders, path.
- **`selfAttributes`** — self-declared attributes: `sourceStatementText` (view SQL), `NumberOfRows`, custom attributes, `businessName`.
- **`stakeholdership`** — full stakeholder list with governance roles (Data Owner, Data Steward, etc.), beyond the truncated `summary` view.
- **`glossary`** — linked business terms with `curationStatus` (`ACCEPTED` | `INFERRED` | `REJECTED`) — the load-bearing signal for meaning verdicts (§2 rule 2 in SKILL.md).
- **`hierarchy`** — declared children along the containment chain: columns under a Table, PK/FK/indexes, SubDomains under a Domain.
- **`neighborhood`** — associations to other assets: declared PK/FK table-to-table joins (`core.PKFK`), glossary links, DQ rules, `RelatedTo`. Excludes `ParentChild`, `DataFlow`, `ClassifiedAs`.
- **`dataClassification`** — PII, PCI, and other sensitivity labels (technical assets only).

## Batching rules

Canonical list: SKILL.md §4 "Batching rules" (always loaded). Combine segments into one call per asset.

## Parallel execution model

Two calls are independent when neither needs a value from the other's response. A **round** is a set of mutually independent calls; a later round needs values from an earlier one.

- **Default (client supports parallel tool calls):** issue all calls in a round together in the **same turn** — do not wait for one to return before sending the next.
- **Client does not support parallel calls:** run the calls in a round one after another, in any order, then move to the next round. Results are identical; only latency differs.
- **Resource fallback:** if a call fails with a resource or concurrency error (429, too many requests, concurrency limit), re-run the failed calls one at a time and stay sequential for the rest of the conversation. If a call still fails when run alone, do not retry again — report it as a tool error for that segment ("unable to retrieve [X]", [search-rules.md](search-rules.md)) and deliver the rest. This is not a steward escalation. Timeouts follow [business-delivery.md](business-delivery.md) "Failure and partial states".

**Round model for BROAD_DISCOVERY (target: 2–3 rounds depending on path):**

Column UUIDs can arrive from two sources — Round 1 search results or Round 2 hierarchy. Which path applies determines whether glossary wiring runs in Round 2 or Round 3.

```
Round 1:  search(topic) + search(dimension terms) + search(fiscal terms)
          ↓ identities resolve — check: did search return column UUIDs?

─── Fast path (columns in Round 1 results — 2 rounds total) ─────────────────
Round 2:  get_asset_details(top asset, [hierarchy, selfAttributes, dataClassification, stakeholdership])
          + get_asset_details(date column, [glossary])      — fiscal wiring
          + get_asset_details(region column, [glossary])    — dimensional wiring
          Column UUIDs already known → glossary runs alongside hierarchy, not after it.

─── Slow path (columns NOT in Round 1 results — 3 rounds) ───────────────────
Round 2:  get_asset_details(top asset, [hierarchy, selfAttributes, dataClassification, stakeholdership])
          + get_asset_details(related dimension table, [hierarchy])
          ↓ column identities resolve from hierarchy
Round 3:  get_asset_details(date column, [glossary])      — fiscal wiring
          + get_asset_details(region column, [glossary])   — dimensional wiring
```

**Rules:**
- All searches in steps 1–2 of the BROAD_DISCOVERY strategy are independent → **all in Round 1** (parallel if supported).
- **Path selection after Round 1:** inspect search results for column/DataElement identities. If the columns you need for glossary wiring (date column, region column, etc.) appeared in Round 1 results, their UUIDs are already known — take the fast path. If search returned only the parent table (common when column names don't match the keyword), take the slow path.
- **Fast path:** all `get_asset_details` calls — hierarchy on the parent, glossary on known columns — are independent → **all in Round 2** (parallel if supported). Do NOT wait for hierarchy to "discover" column UUIDs you already have from search. This removes the Round 3 dependency step entirely.
- **Slow path:** hierarchy fetch in Round 2 → column UUIDs resolve → glossary wiring checks on those columns in Round 3.
- **Do not re-search for columns the hierarchy already gave you.** After Round 2's hierarchy fetch returns the full column list with UUIDs, use those UUIDs directly for Round 3 glossary calls. A separate `search_assets(query="ORDER_DATE")` to find a column UUID that hierarchy already returned is a wasted call.
- Escalation-on-zero (BROAD_DISCOVERY step 3) is inherently sequential — it retries only when the prior call returned zero, so it stays sequential even when the client supports parallel calls.
- Segment batching (SKILL.md §4) still applies — combine segments into one call per asset rather than one call per segment.

## Limitations (state when relevant)

1. No lineage — `DataFlow` is excluded from `neighborhood`.
2. FK/PK objects appear as `hierarchy` children; the join they define ALSO appears in `neighborhood` as a `core.PKFK` table-to-table edge — both are valid evidence of a declared relationship.
3. `neighborhood` excludes `DataFlow` lineage, `ParentChild`, and `ClassifiedAs` associations.
4. No reverse lookup — search by name to find dependents.
5. `data_explore` / `master_data_explore` expose **no structured field for resolved catalog facts** — resolved measures, filters, and date ranges must ride inside the free-text `prompt` (see "Enriching the hand-off prompt" below). The pre-hand-off verification gate below is required because prompt enrichment is not otherwise enforced.

## Reading actual data — hand off to `informatica-data-exploration`

This skill is **metadata-only** — it decides *which* asset is right, trusted, and compliant, and never reads row values. When the user's question needs the **actual data** (row values, counts, aggregates, ranked lists, anti-joins, sampling the contents) — not just picking the asset — hand off to the **`informatica-data-exploration`** MCP *after* discovery has resolved the trusted asset and its identity.

**Sequence (catalog-first, always):** run discovery to pick the right/trusted/compliant asset and resolve its identity → then call `informatica-data-exploration` to read the data → carry the governance verdict forward (do not read data from an asset you flagged FORBIDDEN/CAUTION in the SAFE_USAGE strategy without stating the gate).

**How to call it:**
- Call **`data_explore`** with the request payload.
- If `data_explore` / `master_data_explore` returns a connection or authentication/session error (not connected, session expired, 401), ask the user to reconnect the Informatica data-exploration connection in their client, and retry only after they confirm. Still deliver the catalog findings already resolved. A 403 / `permission_denied` or a `timeout` follows [business-delivery.md](business-delivery.md) "Failure and partial states".

**MANDATORY — always send `external_id` (single asset) or `external_ids` (multiple assets) in the `data_explore` payload.** This is the asset's **EXTERNAL** catalog identity — the `externalId` field, passed unchanged — carried straight through from the `search_assets` / `get_asset_details` response. If `external_id`/`external_ids` is omitted, `data_explore` returns **empty result frames (zero rows) silently — no error is raised**. An empty frame therefore means "the external_id was missing," not "the asset has no data." Never call `data_explore` without it. The `prompt` you send is equally mandatory — it MUST be enriched with the resolved facts (see "Enriching the hand-off prompt" below), never the raw user question. Re-confirm the exact field spelling against the tool schema if a call unexpectedly returns empty.

If `informatica-data-exploration` does not cover the source and another data-access tool for it is available in this session, pass it the resolved asset path and an enriched prompt built as in "Enriching the hand-off prompt" below (follow that tool's own input rules). If the user or the client indicates a data tool for that source exists but is not enabled in this session, ask the user to enable it. Otherwise say so and give the user the resolved asset and the resolved filters to run themselves, rather than reporting the question as unanswerable.

## Enriching the hand-off prompt (MANDATORY)

`external_id` binds the *asset* (see "Reading actual data" above). It does NOT carry anything else discovery resolved. Whenever discovery resolved a fact the query engine needs — a Metric's business-logic formula, a `BusinessTerm`'s `AliasNames`, a fiscal/period term's date range, a dimension term's resolved member list, the specific measure column, or column wiring — the `prompt` argument passed to `data_explore` / `master_data_explore` **MUST be a rewritten, fully-resolved instruction carrying those facts. It MUST NOT be the user's raw question.** Include the resolved table name and external_id, the column mapping (which columns serve the user's business terms), any filters resolved from catalog terms (fiscal period boundaries, region lists), and any governance gates (PII columns to mask, RTBF/consent filters to apply).

**Why this is mandatory, not a nicety.** These tools route on the `prompt` string verbatim; there is **no separate structured field for resolved catalog facts** (see Limitations above). Anything discovery learned is invisible to the agent unless it is written into the prompt string. If the raw question is passed, the agent re-resolves the terms itself — off possibly-stale profiles — and silently returns a wrong number. (Example failure: the raw prompt `"Q2 Sales Revenue for EMEA"` made the agent filter `WHERE LOWER(SALES_REGION)='emea'`, which matched zero rows against country-valued data.)

**Prompt-rewrite template (ASCII only — no em-dashes, no angle brackets in the actual prompt string; both trip the MCP input validator):**

```
Sum MEASURE_COLUMN from TABLE where DIM_COLUMN in (resolved member list)
and DATE_COLUMN between resolved_fiscal_start and resolved_fiscal_end
[and status/scope filters]. Use these exact filter values; do not re-derive
the region or the period from the data.
```

**Worked example (the EMEA case — member list and dates are illustrative; use the values resolved from the tenant's catalog):**

- Raw (WRONG — do not send): `Q2 Sales Revenue for EMEA`
- Enriched (CORRECT): `Sum NET_SALES from FACT_ORDER where SALES_REGION in ('France','Italy','Germany') and ORDER_DATE between 2026-05-01 and 2026-07-31. Use these exact filter values; do not re-derive the region or the period from the data.`

**Negative example (this is the known failure mode, not a valid call).** Emitting `data_explore` with `"prompt": "<the user's raw question>"` — even with `external_id` present — is a defect. Correctly decoding the terms in your visible reasoning is NOT a substitute for putting the resolved facts into the prompt; only the prompt string reaches the engine.

**Pre-hand-off verification gate (silent — run before emitting ANY `data_explore` / `master_data_explore` call; mirrors the Verdict Self-Check in SKILL.md):**

1. If the question involves a measure: does `prompt` contain the resolved **measure column**? If NO → rewrite before sending.
2. If the question uses a dimension term: does `prompt` contain the resolved **dimension member list** (the actual values, e.g. the countries) rather than the business-term label (e.g. "EMEA")? If NO → rewrite.
3. If the question is period-scoped: does `prompt` contain the resolved **fiscal date range** (explicit start and end dates), not a bare period word ("Q2")? If NO → rewrite.
4. Is `prompt` byte-identical or near-identical to the user's **raw question**? If YES → STOP: it has not been enriched — rewrite before sending.
5. Is `external_id` / `external_ids` present (see "Reading actual data" above)? If NO → add it.

This gate is internal only — never print it. Its purpose is to catch an un-enriched hand-off before it reaches the engine, since prompt enrichment is not otherwise enforced.
