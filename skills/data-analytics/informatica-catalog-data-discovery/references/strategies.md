---
description: "Step-by-step procedures for each discovery intent, call budgets, a worked discovery example, and gap report examples."
last_updated: 2026-11-13
origin: original
---
# Strategy Procedures — Full Reference

> Canonical source for SKILL.md §7 (Strategies). Read when the agent has classified the intent and needs the full procedure for that strategy.

**Contents:** BROAD_DISCOVERY · AUTHORITY_COMPARE · FIELD_MEANING · FIELD_RELIABILITY · TRUST_ASSESSMENT · FRESHNESS · RELATIONSHIPS · IMPACT_ANALYSIS · PROVENANCE · ROOT_CAUSE · OWNERSHIP · SENSITIVITY · POLICY · SAFE_USAGE · COMPLIANCE_FLAG · Worked illustration — period-scoped BROAD_DISCOVERY (wasteful vs corrected) · Gap report examples

## BROAD_DISCOVERY

1. **Term extraction — include dimensional terms.** From the question, extract every catalog-relevant term: business concepts ("revenue", "customer") AND dimensional / qualifying terms ("EMEA", "last quarter", "by category"). Do NOT drop dimensional terms as filtering-only noise — the catalog governs them too (Fiscal Quarter, Region, Product Category typically exist as glossary terms, business domains, or reference dimensions), and dropping them loses the exact governance context that answers the question. Every extracted term is a candidate query for steps 2–4, and each should be resolved against BOTH technical assets (tables, columns, files, reports) AND business assets (glossary terms, domains, policies). The highest-value hit shape is a technical asset that carries a linked business glossary term — physical location + governed meaning in one place — rank this shape first when reporting (step 7).
2. **⟦ROUND 1 — independent calls⟧ One topic-scoped search PLUS all dimensional/fiscal term searches.** Issue the topic search AND the dimensional term searches (e.g. EMEA, fiscal — single words, per the gate below) together if the client supports parallel calls, otherwise one after another — they have no data dependency.

   **Hard rule — compound-phrase gate (apply before routing).** If any extracted topic is a multi-word phrase ("sales revenue", "customer orders", "product performance"), do NOT pass it as a single KEYWORD query — KEYWORD matches token-by-token and multi-word compounds return 0 results. Two options: (a) split into individual single-word KEYWORD searches, each in Round 1 (preferred when each word is a meaningful asset name), or (b) route the full phrase to NL mode (preferred when the words form one concept, e.g. "customer lifetime value"). This is a hard gate, not a tip — violating it wastes a call and returns zero.

   Route each search by shape:
   - Single noun / entity / named-asset shape → `search_assets(query=<term>, mode=KEYWORD, size=10, aggregationSpec=[{name:"agg", attributeNames:["core.classType"]}])`
   - Multi-word concept phrase (if not split above) → `search_assets(query=<user's phrasing>, mode=NL, size=10, aggregationSpec=[{name:"agg", attributeNames:["core.classType"]}])`
   - Cold-start / topic-less prompt only → trust census (`query="*"`, `filterSpec={certified:true}`, `aggregationSpec=[{name:"agg", attributeNames:["core.classType"]}]`)
   Apply `filterSpec={certified:true}` inline when the user is asking for trusted data. Read the returned assets AND the `core.classType` buckets you requested plus the free `origin` / `resourceType` / `assetLifecycle` buckets before spending another call.
3. **Escalation on zero.** Diagnose the cause — filter or mode — before retrying:
   - **Filter-first escalation (when `certified:true` or `classType` filter was applied):** retry the SAME mode WITHOUT those filters. If results appear, the data exists but is not certified/typed — report as an UNCERTIFIED or UNTYPED gap alongside the results. Do NOT switch to NL mode to work around a filter problem — NL silently drops `filterSpec`, which hides the certification gap instead of surfacing it.
   - **Mode escalation (when no restrictive filter was applied, or filter-drop also returned zero):** KEYWORD zero → retry as NL with the user's original phrasing. NL zero → fall back to KEYWORD on concrete nouns from the question.
   - **Still zero after both:** state honestly that the tenant has no match; do NOT invent one.
   - **Column-to-parent derivation (when escalation returns DataElements but no parent Dataset).** Certification is dataset-only (§1 principle 3 in SKILL.md), so dropping the `certified:true` filter often surfaces columns (e.g. NET_SALES) whose parent table (FACT_ORDER) didn't match the keyword. When results contain DataElements but no Dataset: (a) read the column's `location` / `path` from the search result — it names the parent table and its origin; (b) use the parent table name + origin to resolve the Dataset in the next round (origin-scoped search per step 4, or `get_asset_details` if the parent UUID is already in the column's hierarchy). Do NOT issue a separate broad search for the parent — the column's location already tells you where it lives. Report the parent as UNCERTIFIED if the original certified search missed it.
4. **Origin-scoped follow-up searches.** When a previous call has resolved an asset's `origin` or `resource`, use `filterSpec={origin:[<origin_id>]}` to scope all subsequent searches to that source. This applies to two scenarios:
   - **Sibling discovery (finding co-located assets):** `search_assets(query="*", filterSpec={origin:[<origin_id>]}, size=10)` to surface the full connected domain from the same source. Use KEYWORD on related table names found in descriptions.
   - **Known-asset resolution (finding a specific asset within a resolved source):** when you know an asset name from a prior result (e.g. a parent table from a column's location, a dimension table from a description) and you know its origin, search origin-scoped: `search_assets(query="FACT_ORDER", mode=KEYWORD, filterSpec={origin:[<origin_id>]}, size=5)`. This is cheaper and more precise than a broad search — it eliminates same-name assets from other sources and avoids polluting results with staging duplicates.
5. Read aggregation buckets: small named bucket = curated, large generic = staging
6. **⟦ROUND 2 — independent calls; see [tools-and-execution.md](tools-and-execution.md) fast/slow path⟧ Fitness pre-scan (do NOT defer to later turns):** if the prompt implies the data will be USED — e.g. "for a campaign", "present to leadership", "target customers", "where's the customer/product data" — proactively run a fitness pass on the top asset so THIS turn's answer also covers business meaning, sensitivity/PII, ownership/policy, AND the specific governance traps the catalog exists to surface. A first-turn discovery answer that surfaces only findability (and defers meaning/sensitivity/policy to "later turns") is INCOMPLETE — the user asked a fitness question, answer it now.

   **Before issuing Round 2 calls, check which path applies ([tools-and-execution.md](tools-and-execution.md) "Parallel execution model"):**
   - **Fast path (column UUIDs already known from Round 1 search results):** issue hierarchy fetch on the parent AND glossary wiring checks on known columns all in this round (parallel if supported). Do NOT wait for hierarchy to "discover" column UUIDs you already have — that adds an unnecessary dependency step.
   - **Slow path (Round 1 returned only the parent table, not columns):** issue hierarchy fetch in this round; column UUIDs resolve from the hierarchy response; glossary wiring moves to step 6(e)/Round 3.

   Run:
   - (a) `get_asset_details(segments=[hierarchy, selfAttributes, dataClassification, stakeholdership])` — lists fields, the view definition (`sourceStatementText`, needed for the grain check in (d)), PII/sensitivity labels, and owner in one call. **Note:** hierarchy returns all child column UUIDs. If you need column UUIDs for glossary checks in step 6(d)/(e), read them from THIS response — do NOT issue a separate search for a column that hierarchy already returned.
   - (b) **Trap drill-down (mandatory when a field name is ambiguous or geo/demographic-sounding — e.g. REGION, AREA, CODE, CATEGORY, TYPE):** `get_asset_details(segments=[glossary])` on those child fields. A benign-looking column can carry a glossary term revealing HIDDEN_SENSITIVITY (classic: REGION actually encodes *Religion* → special-category). Do NOT report field meaning from the column name alone — confirm from the field-level glossary term (SENSITIVITY strategy step 4).
   - (c) **Compliance-flag scan (mandatory for any contact/campaign/targeting use):** inspect the hierarchy field names for consent / RTBF / opt-out / do-not-contact / suppression columns (COMPLIANCE_FLAG strategy). Report whether they are PRESENT (state the gating rule) or ABSENT (a NO_COMPLIANCE_FLAG gap that must be escalated before outreach) — do NOT merely say "no flags found" without calling it a gap.
   - (d) **Grain check + fiscal-term resolution (mandatory when the question is period-scoped — "last quarter", "in March", "YoY", "MoM", "Q2"; independent of the fitness trigger).** Two sub-checks, both required:
     - **Grain capability:** From the same hierarchy fetch, apply the grain-check heuristic from [search-rules.md](search-rules.md) (`TOTAL_*` / `LIFETIME_*` cumulative → cannot answer; `L7D_*` / `L30D_*` / `L90D_*` rolling → **not** "last quarter"; `DATE_KEY` / `DATE_VALUE` / `*_DATE` grain → period-capable). On views/aggregates, also read `sourceStatementText` in `selfAttributes` for the true metric definition. Report a GRAIN_MISMATCH gap if the candidate cannot answer the period the user asked about — even if every other signal is green.
     - **Fiscal-term resolution (column-glossary-first, NEVER agent knowledge).** The agent MUST NOT interpret period terms ("Q2", "quarterly", "last quarter", "FY") using its own calendar knowledge. Resolution order:
       1. **Column glossary first:** `get_asset_details(segments=[glossary])` on the date/period column (e.g. ORDER_DATE). **On the fast path, this call is in the same round as step 6(a) — the column UUID is already known from Round 1.** On the slow path, this call waits for step 6(a)'s hierarchy to provide the column UUID and runs in Round 3/step 6(e).
       2. **Search fallback:** If no fiscal term is linked to the column, reuse the Round 1 fiscal search result if there was one; otherwise search for one: `search_assets(query="fiscal", mode=KEYWORD, filterSpec={classType:["com.infa.ccgf.models.governance.BusinessTerm"], assetLifecycle:["Published"]})`. If found → use the definition but flag the column link as missing (TERM_NOT_WIRED gap).
       3. **No term at all:** If neither path yields a fiscal/period term → report as a FISCAL_TERM_MISSING gap. State "no fiscal calendar definition exists in the catalog — confirm the period boundary with the data steward before running." Do NOT fall back to generic calendar quarters (Jan–Mar, Apr–Jun, etc.).
   - (e) **⟦ROUND 3 — independent calls; slow path only⟧ Dimensional-term wiring check (mandatory when a glossary term was resolved by search, not by glossary segment).** On the fast path these checks already ran in Round 2 — skip this step. On the slow path, column UUIDs are now available from step 6(a)'s hierarchy response. Issue ALL wiring checks (fiscal + dimensional) in this round (together if supported). When a dimensional or fiscal term (e.g. "Fiscal Quarter", "EMEA") was found via `search_assets` on glossary terms, verify it is actually **linked** to the candidate table's relevant column by fetching `get_asset_details(segments=[glossary])` on that column (e.g. ORDER_DATE for fiscal terms, SALES_REGION for geo terms). A glossary term found by search but not wired to the column is a **floating definition** — weaker evidence than a linked term. Report the wiring status:
     - **Wired:** term appears in the column's glossary with `curationStatus: ACCEPTED` → strong: the governed meaning is formally connected to the data.
     - **Floating:** term exists in the catalog but is not linked to the column → report as a TERM_NOT_WIRED gap. The definition is still the tenant's authoritative meaning (Published > Draft), but the absence of a link means no steward has formally connected it to this data path. State this clearly; do NOT silently treat a floating term as equivalent to a wired one.
   This drill-down is expected to cost 2–4 calls on a first-turn fitness prompt — that is within budget and required; do NOT stop at the single combined call if traps remain unconfirmed.
7. Report: assets grouped by resource with certification/rating, presenting connected domains together; when the pre-scan ran, include the fitness signals (meaning, sensitivity, ownership/policy)

## AUTHORITY_COMPARE

1. For each candidate (max 3): `get_asset_details(segments=[selfAttributes, stakeholdership, glossary])` — add `dataClassification` for technical (Dataset) candidates, used by the Classification signal below
2. **Eligibility gates (hard — must pass to be called authoritative).** Datasets: `certified: true`. All other types (business term, domain, policy): `assetLifecycle: Published`. Datasets carry both signals — check both. A candidate failing its gate is NOT disqualified from the answer, but it cannot win the authority claim; surface it as "best available (not authoritative because [gate that failed])."
3. **Among gate-passing candidates, present ALL signals as an evidence table.** None are optional — the goal is a defensible comparison, not an argmax. Only invoke the tiebreaker order below when candidates are genuinely indistinguishable on the evidence:
   - **Governed meaning** — linked glossary term(s) with `curationStatus: ACCEPTED` (INFERRED = partial, REJECTED = zero; a `description` does NOT substitute for a term, per §2 rule 10 in SKILL.md)
   - **Stakeholdership** — assigned Data Owner / Data Steward present
   - **Business name** — `core.businessName` populated
   - **Description** — non-empty `description` (documentation, not governance)
   - **Classification** — `dataClassification` populated with sensitivity / PII labels (technical assets only). Counts as documentation completeness — an unclassified sensitive-looking asset is less trustworthy than a classified one, even before the label's content matters.
   - **Rating** — steward/user rating value
   - **Recency** — most recent updates
4. Declare winner with the full evidence table shown per candidate (not just the deciding factor). Flag remaining gaps on the winner AND on the runners-up.

## FIELD_MEANING

1. `get_asset_details(segments=[hierarchy])` → get columns. Can be used to see hierarchy of any assets.
2. Pick top 3–5 relevant fields
3. Per field: `get_asset_details(segments=[glossary, selfAttributes])`
4. Assess: term present? Aligned or MEANING_MISMATCH? No term = UNDOCUMENTED
5. Report: field → term mapping table

## FIELD_RELIABILITY

1. Per field (max 3): `get_asset_details(segments=[glossary, selfAttributes, neighborhood])` — neighborhood carries DQ-rule associations; selfAttributes carries profiling/null stats. Trust is not glossary-only.
2. **MANDATORY Verdict Checkpoint — complete this table per field BEFORE writing any prose:**

| Check | Evidence (copy from tool response) | Result |
|-------|-----------------------------------|--------|
| Glossary term(s) exist? | [list from `glossary` array, or "empty"] | YES (count) / NO |
| If YES, single term: does it align with column name + datatype? | [state term name vs column name + datatype] | ALIGNED / CONTRADICTING |
| If YES, multiple terms: do they conflict with each other? | [list all term names] | CONFLICTING / CONSISTENT |
| Business name exists? | [value from `core.businessName` or "none"] | YES / NO |
| Business name aligns with column name? | [compare] | YES / NO / N/A |
| Data-quality / profiling / rating signal present? | [DQ rule from `neighborhood`; null-rate/row-count from `selfAttributes`; asset rating — else "none"] | YES (list) / NO |

3. **Apply verdict — use the FIRST matching rule (stop immediately):**
   - Multiple terms that conflict with each other or with the column's technical meaning → **AMBIGUOUS**
   - Single term contradicts column name/datatype → **MEANING_MISMATCH**
   - Single term aligns with column name/datatype → **RELIABLE**
   - Zero glossary terms → **UNDOCUMENTED** (regardless of how intuitive the column name is)

   Even when the verdict is UNDOCUMENTED, still report any DQ/profiling/rating signal found as **PARTIAL trust evidence** (it does NOT upgrade the verdict, per §2 rule 8 in SKILL.md): e.g. "RATING is UNDOCUMENTED — no glossary term or business name; the only trust signal is a 0% null rate from profiling, which is insufficient for reliance without steward curation." Answer the user's "can I rely on it?" using the quality signals, not just the absence of a term.

4. **Response structure (output in this exact order):**

   **A. Verdict (lead with this — user reads this first)**
   State the reliability conclusion plainly, including warnings and uncertainties. Use direct cautionary language for non-RELIABLE fields. Examples:
   - "Be careful: RATING has no business name or glossary term (undocumented — a fitness-for-use gap). ID is mapped to two conflicting terms, 'Incident Details' and 'ItemID,' so its meaning is ambiguous until curated."
   - "CUSTOMER_ID is reliable — aligned with glossary term 'Customer Identifier' (ACCEPTED)."
   - "PRICE has a MEANING_MISMATCH: the column is numeric (NUMBER 8,2) but is linked to 'Prospective Customers' — do not trust the business metadata for this field."

   **B. Evidence & Decision Parameters (show your work)**
   Per field, show the checkpoint table (from step 2), then:
   - What glossary terms / business names were found
   - Which decision-tree rule matched and why
   - If multiple candidates or terms were considered: list them with the score/reason each was accepted or rejected

   Example format:
   | Field | Glossary Terms Found | Business Name | Decision Rule | Verdict |
   |-------|---------------------|---------------|---------------|---------|
   | RATING | (none) | (none) | Zero terms → UNDOCUMENTED | UNDOCUMENTED |
   | ID | "Incident Details", "ItemID" | "ItemID" | Multiple conflicting terms → AMBIGUOUS | AMBIGUOUS |

   For rejected interpretations, state why:
   - "ID could be read as 'ItemID' (aligned with PK + business name), but 'Incident Details' is also ACCEPTED — two conflicting governed meanings cannot both be correct, so the field is AMBIGUOUS until one is removed."

   **C. Gaps**
   List every gap found per SKILL.md §10 Part 3 (Gaps), or state that none were found.

   **D. Next Actions**
   Concrete steps to resolve gaps or proceed:
   - What the user should do (e.g., "confirm with data steward," "do not use for reporting until curated")
   - What curation the catalog needs (e.g., "steward should remove 'Incident Details' term from ID," "steward should add a 'Product Rating' term to RATING") — surface as a steward-side ask; this skill does not perform the fix.

5. **DO NOT** add qualifiers like "but it's probably fine," "you can still use it," or "Yes as the [X]" to any non-RELIABLE verdict. The verdict is the final word.

#### Negative Example (DO NOT do this):

```
WRONG: RATING has no glossary term but the description says "average customer rating"
so it's obviously the product rating → verdict: RELIABLE

CORRECT verdict: "Be careful: RATING has no business name or glossary term
(undocumented — a fitness-for-use gap). You cannot rely on it without steward confirmation."

CORRECT evidence: glossary=[] | businessName=none | Rule: zero terms → UNDOCUMENTED
CORRECT next action: "Link a 'Product Rating' glossary term to formalize the meaning."
```

## TRUST_ASSESSMENT

1. `get_asset_details(segments=[selfAttributes, stakeholdership, glossary])` — one call. (`summary` is always returned and provides `modifiedOn` for Freshness scoring.)
2. Score (0–10): Certification(+2) + Lifecycle(+2) + Freshness(+2) + Documentation(+2) + Ownership(+1) + Glossary(+1)
3. **Component scoring rules (each is explicit — no intermediate values unless stated):**
   - Certification: `certified: true` → +2, else +0
   - Lifecycle: `Published` → +2, `Draft` → +1, `Obsolete` or absent → +0
   - Freshness (from `modifiedOn`; prefer source-refresh timestamp from `selfAttributes` if available): <30d → +2 | ≥30d and <90d → +1.5 | ≥90d and <180d → +1 | ≥180d and <365d → +0.5 | ≥365d → +0
   - Documentation: `businessName` present → +1, `description` present → +1 (max +2)
   - Ownership: any governance role assigned (Data Owner or Data Steward) → +1, else +0
   - Glossary: ≥1 term with `curationStatus: ACCEPTED` → +1, `INFERRED` only → +0.5, none → +0
4. **Labels (threshold-based):** ≥8 Production-ready | ≥5 Sound with gaps | ≥3 Use with caution | <3 Not ready
5. **Certification guard:** a dataset scoring ≥8 but NOT certified is capped at "Sound with gaps (certification gap)" — certification is the primary trust signal (§1 principle 3 in SKILL.md) and a hard gate in AUTHORITY_COMPARE; labeling an uncertified asset "Production-ready" would contradict both.
6. Output tree-format verdict with per-factor scores

## FRESHNESS

1. Use timestamps from state if available; else `get_asset_details(segments=[selfAttributes])`
2. Compare across related assets — flag if derived is older than source
3. Report: timestamp table with staleness assessment

## RELATIONSHIPS

1. Per dataset: `get_asset_details(segments=[hierarchy, neighborhood])`
2. Hierarchy → PK/FK children = "declared relationship"
3. Neighborhood → RelatedTo = "catalog-inferred relationship"
4. State honestly if lineage not available

## IMPACT_ANALYSIS

1. `search_assets(query=<asset/field name>)` → find referencing assets
2. `get_asset_details(segments=[hierarchy, neighborhood])` for top references
3. Classify: FK = enforced | RelatedTo = inferred | name-only = possible

## PROVENANCE

1. `get_asset_details(segments=[hierarchy, neighborhood, selfAttributes])` — one call
2. Read: FK/PK → source tables, RelatedTo → upstream, sourceStatementText → SQL
3. **Feeder search (when neighborhood shows no lineage — expected, since DataFlow is excluded, see [tools-and-execution.md](tools-and-execution.md) "Limitations"):** do NOT stop at "not documented." Actively `search_assets` for candidate upstream feeders by name — the FK-referenced source tables, and any staging / aggregate / job asset whose name echoes the fact (e.g. `*sales*`, `*aggregate*`, `orders*`, mapping/mapplet names). Then `get_asset_details(segments=[selfAttributes])` on the best match to read its build logic/SQL.
4. Only if no feeder is discoverable by name: "derivation not documented in the catalog — confirm with steward"

## ROOT_CAUSE

1. Review state: meaning mismatches, undocumented assets, stale timestamps
2. Build causal chain from established facts
3. Only call tools if chain has gaps (max 2 calls)
4. Report: "likeliest root cause is [X] because [catalog evidence]" — label as hypothesis

## OWNERSHIP

1. `get_asset_details(segments=[stakeholdership])`
2. Present → report names/roles. Absent → "No governance owner assigned."
3. Suggest checking schema/resource level if gap found

## SENSITIVITY

1. Use hierarchy from state or fetch: `get_asset_details(segments=[hierarchy, dataClassification])`
2. If dataClassification populated → report labels. If empty → "No classification applied" (UNCLASSIFIED gap)
3. Assess fields by name/glossary even without classification:
   - RESTRICTED: race, religion, gender, ethnicity, health (special category)
   - PERSONAL: SSN, email, phone, DOB, name, address (PII)
   - SAFE: city, country, job, product category (non-personal)
4. Cross-reference glossary: REGION→Religion = HIDDEN_SENSITIVITY
5. If no formal classification: "Assessment inferred from field names/glossary — confirm with DPO"

## POLICY

1. `search_assets(query=<domain>, filterSpec={classType:["com.infa.ccgf.models.governance.Policy"]}, size=5)`
2. If found: `get_asset_details(segments=[selfAttributes])` → read scope/constraints
3. If not found: try broader terms ("data protection", "privacy")
4. Cross-reference with sensitivity: PII → restricted handling, special category → lawful basis
5. Never invent policy. Label as "implied by classification" vs "stated in policy [name]"

## SAFE_USAGE

Primarily synthesis from conversation state. Only call tools if field analysis is incomplete.

1. Partition fields into:
   - **FORBIDDEN:** MEANING_MISMATCH where true meaning is sensitive; special-category without lawful basis; true meaning ≠ intended use
   - **CAUTION:** AMBIGUOUS (dual terms); PII (needs consent); undocumented sensitive-sounding
   - **PERMISSIBLE:** Aligned terms + no sensitivity flags; non-personal attributes
2. Add conditions: exclude RTBF=true, obtain consent for contact fields, don't segment on forbidden
3. Report: structured guide (CAN use / MUST NOT use / needs resolution / prerequisites)
4. **Restate the gate explicitly:** end with the applicable policy (name, or "implied by PII/special-category classification") AND the required approval/owner — e.g. "Gated on: marketing-use policy [implied by PII classification] + steward approval; no owner is assigned, so escalate before sending." A safe-usage answer that omits the policy + approval gate is incomplete.
5. **When the ask is Data-Q&A (counts, ranked lists, anti-joins):** do NOT stop at "cannot run it." Two paths: (a) if the actual data should be read, hand off the resolved asset to the `informatica-data-exploration` MCP (see [tools-and-execution.md](tools-and-execution.md) "Reading actual data") — remember `data_explore` requires `external_id`/`external_ids` or it returns empty frames silently, and the prompt MUST be enriched with the resolved facts (see [tools-and-execution.md](tools-and-execution.md) "Enriching the hand-off prompt"); (b) otherwise deliver the precise recipe: lead with the business-language answer (which governed asset, how they join, which records are excluded and why, plus the caveats — safe fields, RTBF/consent exclusions), then give the exact join/anti-join key(s) and the SQL that WOULD answer it in a secondary section ([business-delivery.md](business-delivery.md) "Persona and register"). The executed result or the recipe IS the deliverable.

## COMPLIANCE_FLAG

1. Scan hierarchy for patterns: RTBF, CONSENT, OPT_IN, OPT_OUT, DO_NOT_CONTACT, SUPPRESSION, ERASURE_FLAG
2. If found: `get_asset_details(segments=[glossary, selfAttributes])` to confirm purpose
3. Report with operational guidance (business wording in the primary answer; the exact filter in a secondary section — [business-delivery.md](business-delivery.md) "Persona and register"):
   - RTBF → "Exclude anyone who has asked to be forgotten before outreach" (filter: `WHERE RTBF IS NULL OR RTBF = FALSE`)
   - Consent → "Only contact people who have given consent" (filter: `WHERE CONSENT = TRUE`)
   - None found → "No compliance flags — escalate before campaign" (NO_COMPLIANCE_FLAG gap)

---

## Worked illustration — period-scoped BROAD_DISCOVERY (wasteful vs corrected)

Illustrative only — asset, resource and column names are generic. The prescriptive flow is BROAD_DISCOVERY steps 1–7 above; this shows how those steps play out on one question.

Example question, over a messy multi-vertical tenant: *"What's our customer revenue in EMEA last quarter?"*

**Wasteful path (~13 calls, one after another):**
1. Broad glossary sweep on `revenue` → ~120 mostly-`Draft` demo terms
2. Broad glossary sweep on `customer` → same shape, all noise
3. Unfiltered search on the dimensional term `EMEA` across all asset types → 259 matches, all staging columns
4. NL retry on "customer revenue" → drifts semantically, returns weather-forecast tables matching on "forecast" + "region"
5. NL retry on "EMEA customer revenue last quarter" → server error on the compound structural query
6–13. More broad searches; aggregations from earlier calls never re-read; the winning asset (a curated `V_CUSTOMER_REVENUE` view) reached by luck on call ~13.

**Failure modes on display:** broad glossary sweep before any signal; searched a dimensional term as if it were a data asset instead of resolving it as a glossary term; ignored the aggregation buckets already in the response; used NL for a structural query; never grain-checked or wiring-checked.

**Corrected path (~7–8 calls in 3 rounds):**
1. **Round 1 — independent searches, issued together (steps 1–2).** The user wants a reportable number, so the dataset searches filter on `certified:true`. "customer revenue" is a compound phrase, so it is split into single-word KEYWORD searches; the dimensional and fiscal terms are resolved as glossary terms:
   - `search_assets(query="revenue", mode=KEYWORD, filterSpec={certified:true}, size=10, aggregationSpec=[{name:"agg", attributeNames:["core.classType"]}])`
   - `search_assets(query="customer", mode=KEYWORD, filterSpec={certified:true}, size=10, aggregationSpec=[{name:"agg", attributeNames:["core.classType"]}])`
   - `search_assets(query="EMEA", mode=KEYWORD, filterSpec={classType:["com.infa.ccgf.models.governance.BusinessTerm"], assetLifecycle:["Published"]})` → the region term and its member countries
   - `search_assets(query="fiscal", mode=KEYWORD, filterSpec={classType:["com.infa.ccgf.models.governance.BusinessTerm"], assetLifecycle:["Published"]})` (single word — the compound-phrase gate applies to glossary searches too, and NL would drop the filter) → the tenant's fiscal-calendar term with the date range for "last quarter". Do NOT add `certified:true` to glossary searches — terms are never certified, so the filter returns zero and you would wrongly conclude no definition exists.
2. **Read before spending another call (steps 3 and 5).** Read the free `origin` buckets in the response (only one `aggregationSpec` is allowed per call, so it is spent on `core.classType`): the `sales_mart` bucket has 4 hits — small, purpose-named, curated; ignore `staging_warehouse` (48 hits, generic name, staging noise). If a certified search had returned zero, retry the same mode without `certified:true` and report an UNCERTIFIED gap (filter-first escalation) — do not switch to NL. The certified searches returned only datasets, no column UUIDs → **slow path**.
3. **Round 2 — fitness pre-scan on the top hit (step 6a, d).** `get_asset_details(<UUID of V_CUSTOMER_REVENUE>, [hierarchy, selfAttributes, dataClassification, stakeholdership])`. `sourceStatementText` gives the actual revenue definition (status filter, currency conversion, join path); `hierarchy` gives the column list and UUIDs — grain check: `ORDER_DATE` present → period-capable. Optionally, in the same round, an origin-scoped sibling walk (`search_assets(query="*", filterSpec={origin:[<origin_id>]}, size=10)`, step 4) — justified because the bucket was small; it can surface a daily-grain aggregate that keyword ranking buried. **1–2 calls.**
4. **Round 3 — wiring checks, issued together (step 6e).** `get_asset_details(<UUID of ORDER_DATE>, [glossary])` + `get_asset_details(<UUID of SALES_REGION>, [glossary])` (UUIDs from the Round 2 hierarchy). Wired with `ACCEPTED` → strong evidence; the term exists but is not linked → TERM_NOT_WIRED gap. **2 calls.**
5. **Deliver.** Hand off to `data_explore` with the `external_id` and an enriched prompt carrying the measure column, the resolved EMEA member list and the fiscal start/end dates ([tools-and-execution.md](tools-and-execution.md) "Enriching the hand-off prompt"), or deliver the recipe with its SQL in a secondary section.

**General shape:** search to choose a *neighborhood*; aggregations to confirm it; `hierarchy` to exhaust it; glossary to pin and wire the definitions; then hand off with the resolved identity + an enriched prompt, or deliver the recipe with its SQL in a secondary section. Anti-patterns to fail against: broad glossary sweeps, compound phrases as one KEYWORD query, dimensional terms searched as data assets, ignoring aggregations, NL for structural queries, skipping the grain or wiring check on a period-scoped question.

## Gap report examples

Example rows for SKILL.md §10 Part 3 (Gaps). Severity levels are defined there.

| Gap Type | Asset/Field | Detail | Severity |
|----------|------------|--------|----------|
| UNDOCUMENTED | e.g., RATING | No glossary term, no business name | High — meaning unverified |
| AMBIGUOUS | e.g., ID | Two conflicting terms: "ItemID" + "Incident Details" | High — cannot determine governed meaning |
| MEANING_MISMATCH | e.g., PRICE | Column is NUMBER(8,2) but linked to "Prospective Customers" | Critical — metadata actively misleading |
| UNOWNED | e.g., FCT_ORDERS_BY_PRODUCT | No stakeholders assigned | Medium — no escalation path |
| UNCLASSIFIED | e.g., EMAIL | Likely PII but no data classification applied | High — compliance risk |
