---
description: "How to choose search mode, filters, and result size, and how to handle zero, very large, or ambiguous results."
last_updated: 2026-11-13
origin: original
---
# Search Rules & Ambiguity Handling — Full Reference

> Canonical source for SKILL.md §11 (Search Key Rules, including its Ambiguity bullet). Read when the agent is about to issue a search call and needs to pick mode/filters/size, or when handling zero/ambiguous results.

## Mode selection (by query shape, not by intent)

Pick the mode that matches what the user actually typed:

- **Concrete noun / entity / specific asset name** ("revenue", "orders", "EMEA", `CUSTOMER_MASTER`) → **KEYWORD** with `aggregationSpec` on `core.classType`. Cheapest, fastest, most precise; the majority of first-turn discovery prompts land here.
- **Multi-word concept phrase** ("product performance", "sales and profitability", "customer lifetime value") → **NL**. KEYWORD on the compound returns zero, and splitting the tokens loses the concept.
- **Question-shaped or fitness-shaped prompt** ("which tables have PII", "where's the trusted revenue data", "what's authoritative for orders") → **NL**. Tokens aren't in asset names; NL matches descriptions and parses intent. NL drops `filterSpec`, so when the user asks for trusted data, run single-word KEYWORD searches on the topic nouns with `certified:true` ([strategies.md](strategies.md) BROAD_DISCOVERY step 2).
- **Supertype words used generically** ("tables", "columns", "files", "domains", "glossary terms" — used as type words, not as specific asset names) → **NL**. Only NL resolves supertype-level intent per [asset-types.md](asset-types.md) §3.4 A.
- **Cold-start / topic-less** ("what data do we have?", "show me the trusted estate") → **trust census** (`query="*"`, `filterSpec={certified:true}`, `aggregationSpec=[{name:"agg", attributeNames:["core.classType"]}]`). This is when the census earns its keep — as the answer, not a preamble.

## Compound phrase hard rule

**Canonical definition: BROAD_DISCOVERY step 2 in [strategies.md](strategies.md).**

Do NOT search multi-word compound phrases as a single KEYWORD query — they return 0 results. Either split into individual single-word KEYWORD searches (issued together in one round) or route the full phrase to NL mode. This is enforced as a mandatory gate in the strategy, not a best practice.

## Trust filtering

`certified:true` restricts any topic-scoped search to the trusted subset — apply it inline when the user asks for trusted data. Do NOT run a `query="*"` census as a preamble to a topic-scoped search — that's a wasted call.

## Read aggregation buckets

Before next call. Small named = signal. Large generic = noise.

## Filter rules

- `certified:true` excludes non-datasets (never on glossary probes).
- `assetLifecycle:["Published"]` works on all types.
- **Do not use `filterSpec.types`** — the server ignores it (silent no-op). Canonical: [asset-types.md](asset-types.md) §3.4 B. Use NL mode for supertype-level intent.

## Size guidelines

- probe = 5, discovery = 10, pagination = 20 max. Never > 20.

## Free aggregations

Every search returns `origin`, `resourceType`, and `assetLifecycle` buckets even with NO `aggregationSpec` — read them to route the next call before paying for another search.

## Buckets vs. size

Aggregation buckets are complete at any `size`, and `total_matches` is accurate for `size ≥ 1`. Do NOT set `size=0` to "just get counts" — use `size=1` for complete buckets + an accurate total + one sample row.

## Grain check on column names

When the user's question is period-scoped ("last quarter", "in March", "year on year", "MoM", "YoY"), read the top candidate's column names — from the hierarchy segment — and grain-check before committing:

- `TOTAL_*`, `LIFETIME_*`, `*_TO_DATE` → cumulative measures. **Cannot answer a period-scoped question.**
- `L7D_*`, `L30D_*`, `L90D_*` → rolling windows relative to `CURRENT_DATE()`. **`L90D` is NOT "last quarter"** — it's the trailing 90 days ending today. Column descriptions sometimes claim these "support quarterly reviews"; read the definition, not the marketing.
- `DATE_KEY` / `DATE_VALUE` / `*_DATE` grain columns → sum to any calendar or fiscal period. **This is what a period-scoped question needs.**

For views/aggregates, also read `sourceStatementText` in `selfAttributes` — it carries the actual metric definition (status filters, currency conversion, join path) that the user must reproduce if they query source tables directly.

## NumberOfRows: 0

From `selfAttributes` on a Dataset it means empty OR never profiled — you can't tell which. Report it as a gap; do NOT recommend the asset without noting this.

## certified:true on the wrong class

Certification is dataset-only (§1 principle 3 in SKILL.md). A `certified:true` probe on `BusinessTerm`, `Domain`, `Policy`, `Column` etc. returns zero not because the tenant has a gap but because the filter itself excludes those classes. Before reporting "no certified match," check what class you were probing; on non-datasets re-run with `assetLifecycle:["Published"]` as the trust signal.

## Source expansion

When you find a relevant asset, check its origin/resource — other assets in the same source likely form a connected domain. Search the same origin to find them.

## Never bare `query="*"` with `certified:true` for a topic-scoped search

With no query term the ranking is arbitrary and the result set is paginated — the asset you want can sit outside the first page. Pair the certification filter WITH your search terms. The one exception is the cold-start census, where `*` IS the question.

---

## Handling Ambiguity

**Canonical definition: BROAD_DISCOVERY step 3 in [strategies.md](strategies.md).**

- **Zero results → follow the escalation order.** Filter-first: if `certified:true` or `classType` was applied, retry the SAME mode WITHOUT those filters before switching modes (surfaces UNCERTIFIED/UNTYPED gaps). Mode switch: only after filter-drop also returned zero — KEYWORD zero → NL; NL zero → KEYWORD on concrete nouns. Do NOT retry a compound phrase as another KEYWORD compound (see compound phrase hard rule above). If still empty after both, report honestly.
- Hundreds of matches → narrow via aggregation buckets, or add `certified:true` filter to surface the trusted subset
- Multiple terms → list all, flag conflicts
- No certified → say so, offer best uncertified
- No glossary term → do NOT substitute generic definition (a bannered general definition is given only if the user accepts the `term_not_found` offer — [business-delivery.md](business-delivery.md) "Failure and partial states")
- Conflicting signals → report both, let user decide
- Tool error → "unable to retrieve [X]" — never guess
- Found one relevant asset → expand from same origin/resource to find connected assets in the same domain
