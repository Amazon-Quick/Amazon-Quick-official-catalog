---
name: team-pipeline
display_name: Team Pipeline
description: "Answer questions about a manager’s team pipeline, scoped to what was asked: rep attainment, stage distribution, or opportunities needing attention and coaching. Use for a manager's team, two or more named reps, a named rep list, or a multi-rep pipeline comparison. Exactly one rep or one owner's book: pipeline-review."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:cbc1bf74a0ef1b488fa2d796fda858071bae39db0268db9e5b28c5af3f9e0bc1"
id: "b11ae934-3c6a-44c5-bacb-b00ff81e4517"
---
<!-- global-rules-bootstrap -->

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **⛔ WIDGET OUTPUT ONLY after data assembly.** Once all queries return, immediately call `display_widget` — at most a single one-line render-wait notice before it, and no summaries, transitions, or narration. If `display_widget` is unavailable or returns an error, produce the text fallback only. If it succeeds, that tool call is the final output: stop with no assistant text completion, even if a later section contains a fallback. The exceptions above do not apply after success.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record inline: `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **One idea per sentence.** In all generated content, if a sentence needs re-reading, it is carrying too much: split it.
- **Don't repeat the visual.** When a visualization or widget renders, the text around it tells the user what to conclude from the data. Do not restate numbers they can already see.
- **Use plain language.** Choose terms any reader understands on first read, with no domain knowledge or cultural context required. Avoid jargon and colloquialisms, and make labels signal what follows. Test: would a reader unfamiliar with the idiom understand the term and know what content to expect? Use "No engagement", not "went dark" or "ghosted".
- **Reproduce Salesforce terminology exactly.** Use the field labels, object names, and stage values the data returns; do not paraphrase them. Spell out acronyms on first use unless the term is an industry framework (for example, MEDDIC).
- **Empty `MINE` scope → fail fast, then ask which scope.** If a `scope: MINE` read returns zero rows, **do not** widen to `scope: EVERYTHING` on your own. Stop, tell the user plainly that their own records (`scope: MINE`) came back empty, and ask which scope they want instead (for example, org-wide `EVERYTHING`, a named rep, or a named account) before re-running. Never invent records, and never silently fall back to org-wide.
- **While following this skill, don't call `discover` or `describe`, and don't call any API or endpoint not written here. This file already has every query and widget reference you need. (Outside this skill, they're available as normal.)** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->
<!-- response-formatting -->
## Response formatting

- **Number formatting:** Format numbers for readability across the entire response, including values retrieved directly from Salesforce fields. Abbreviate large numbers with a suffix for their scale: K (thousand), M (million), B (billion), T (trillion), and the next suffix up for anything larger, never leaving a big number unabbreviated or spelling it out in full (e.g., $120K, $1.25M, $2.4B, $1.3T), and round percentages to whole numbers unless decimals are required for meaningful comparison.
- **Empty table cells (structured data tables only):** keep empty states terse and never explain them inside a table cell.
  - AI-generated cells: write "Not enough data" when the returned data cannot support a grounded answer (for example, a Suggested Action cell when no recommendation can be supported).
  - Cells filled directly from CRM fields: leave the cell blank when the source field was queried and confirmed empty or null. Keep valid values such as 0.

# Rules:

- **Scope reading and output to the prompt, never a default full response. Read only what the question needs** and present only that. Resolve the team and period once, then run only the reads below that serve the question.
- Keep one team, fiscal period and currency across comparisons. Never add unconverted currencies; use verified converted amounts or explain the limitation and omit the combined chart.
- Never infer a quota, a territory, a buyer objection or a legal blocker. Missing activity is not proof of a silent champion. A suggested next move is a recommendation.

# Team Pipeline

Ground → resolve team → read opps → analyze → output. **No per-opp SF follow-ups** — the team opps read has the data.

## 1. Ground (hardcoded — User + Opportunity)
Ground only objects needed by the selected reads. A team pipeline question needs User and Opportunity; a direct team-membership lookup needs only User. Narrow stage or hygiene asks skip quota/custom forecast fields and evidence enrichment.

Ground **User** (for team resolution) and **Opportunity** (for pipeline fields). Both always exist. **Fire as two separate calls, not one combined call** — combined User+Opportunity ObjectInfo commonly exceeds the tool's char limit, and recovering from that overflow costs far more than just issuing two calls up front. Same turn, same shape, one `apiNames` each:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"User\\\"]) { fields { ApiName label dataType relationshipName } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label dataType relationshipName } } } }\"}" })
```

**If either still overflows** or comes back truncated, skip custom-field grounding and proceed with standard fields only; don't keep retrying. This applies per object: the one that didn't overflow keeps its custom fields.

From the result: (a) scalar `__c` fields (quota, forecast, risk, etc.) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's Name.

## 2. Resolve team
Reuse already resolved team IDs and period. Ask on ambiguous rep names; never inspect candidate pipelines to choose a person. Do not fetch quotas for a stage-only, count-only or attention-only ask.

**"my team"** (default) — reps where Manager = current user:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { and: [{ ManagerId: { eq: \\\"<CURRENT_USER_ID>\\\" } }, { IsActive: { eq: true } }] }, first: 50) { edges { node { Id Name { value } Email { value } <USER_CUSTOM> } } } } } }\"}" })
```

**A named list, role, or territory** (disambiguate — do NOT probe): shared/demo orgs collide hard on name (one name → base user plus regional variants like `(AM)`/`(BK)`/`(SG)`). Pull enough to disambiguate at a glance — never pull each candidate's pipeline to guess which is real:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Title { value } IsActive { value } } } } } } }\"}" })
```

**One match per name** → take its Id. **Several** → list them (Name · Title · active? · Id) and ask the user to pick; the suffix/title is usually the tell. Don't guess.

Insert `<USER_CUSTOM>` = confirmed scalar `__c { value }` fields (quota, etc.). Capture the Ids — they become the owner filter in step 3.

## 3. Read team opps — AGGREGATE the rollup, SAMPLE the top deals, ISSUE ALL IN ONE TURN
Choose the independent reads before issuing calls in one turn:
- Rep comparison: category rollup + closed-won aggregate + verified per-rep quotas from User/custom scalar fields or the user. Skip deal details and hygiene. For the combined request below, remove the detail `query` sibling when no sample is needed.
- Stage distribution: only the full-book stage aggregate below. Skip category, closed-won, quota, sample and hygiene reads.
- Attention/coaching: bounded deal sample + relevant hygiene aggregates; remove the category `aggregate` sibling when no scoreboard is needed. Skip closed-won/quota and stage reads. A specific overdue/stalled ask applies the same risk predicate to its bounded sample, so large healthy deals cannot crowd out all matching rows.
- A direct count or amount: only its aggregate; no sample, quota or evidence.
- Broad team review: category and closed-won aggregates, stage aggregate, sample and full-book hygiene counts.

**Full-book open pipeline by actual sales stage and rep** (only for `byStage`). After grounding OwnerId, StageName, Amount, IsClosed and CloseDate in step 1, validate this single read-only SOQL statement and dispatch it. Use the exact same team and period as the category rollup. Never sum the top-60 sample to populate this chart. If grouping is incomplete/limited, omit the chart and explain the limitation.

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT OwnerId, StageName, SUM(Amount) amt FROM Opportunity WHERE OwnerId IN (<TEAM_USER_IDS>) AND IsClosed = false AND CloseDate >= <Q_START> AND CloseDate <= <Q_END> GROUP BY OwnerId, StageName" })
```

Use StageName display labels and order exposed by grounding; if order is unavailable, use a deterministic order and do not invent stage ranks. Join on OwnerId; categories are stages and series are reps. When team membership or aggregates exceed the documented limits, disclose partial coverage and omit full-team claims.

**Do not pull the whole team's book as raw records.** A team of 5+ reps with 200 open opps returns well past the point a tool result overflows (same overflow `pipeline-review` hit). Salesforce aggregates server-side — use it for the scoreboard math; only a small, bounded sample of concrete deals comes back as raw records, for swing-deal specifics and at-risk flags.

Fire these as tool calls in **one turn** (independent, all filtered by the team-user Ids from step 2). Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields (risk, coaching signals, etc.) on the sample query only — aggregates don't need them.

**Date filters take a `DateInput` object, never a bare string** (`gte: \"2026-07-01\"` fails `WrongType … must be an object type`). For the current-quarter bounds below, use the exact-date form on both ends: `{ value: \"YYYY-MM-DD\" }`. Multiple ops on one field (`gte`/`lte`) AND automatically — no `and: [...]` wrapper needed around them.

**Rollup by forecast category (GraphQL aggregate — folded into the top-N sample request below).** `ExpectedRevenue` (Amount × Probability, a standard field) sums straight to the Weighted column — no client-side probability math. This rollup rides in the sample query (below) as an `aggregate` sibling of the detail read — one dispatch returns both. It yields one row per rep × forecast category. Forecast Category API values map to display labels: `Pipeline` → Pipeline, `BestCase` → Best Case, `Forecast` → **Commit**, `Closed` → Closed. The `Forecast` row IS the Commit row; never report Commit as missing or unverified because no row is literally named `Commit`. Per rep: Commit $ = that rep's `Forecast`-category `Amount.sum` (label Commit); Best-case $ = the `BestCase` row; Weighted = Σ `ExpectedRevenue.sum` across that rep's rows (omit Weighted when `ExpectedRevenue` is unavailable; that never blocks `byRep`).

**Closed-won this period, per rep (GraphQL aggregate).** Feeds the scoreboard's Closed column:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsWon: { eq: true }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } Amount { sum { value } } } } } } } } }\"}" })
```

**Top-N sample per rep + forecast-category rollup (ONE request).** The rollup gives the scoreboard numbers; the sample gives named deals for the swing-deal writeups, at-risk flags, hygiene flags, and Monday questions below. Cap the sample hard (`first: 60`, biggest first) so it never overflows — this is a sample, not the book. **`orderBy` takes only ONE field** — a multi-field array (`orderBy: [{...},{...},{...}]`) fails `WrongType ... must be an object type`; sort by `Amount` alone and group by owner client-side from the `Owner.Name` on each row. The forecast-category rollup rides in this same request as an `aggregate` sibling of the sample — read the per-rep Commit/Best-Case/Weighted numbers from its edges, the named deals from the sample rows.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 60) { edges { node { Id Name { value } StageName { value displayValue } ForecastCategory { value } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } CreatedDate { value } Probability { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, groupBy: { OwnerId: { group: true }, ForecastCategory: { group: true } }) { edges { node { aggregate { OwnerId { value } ForecastCategory { value } Id { count { value } } Amount { sum { value } } ExpectedRevenue { sum { value } } } } } } } } }\"}" })
```

Map each row's `OwnerId` → rep name using the User list from step 2 — no extra lookup needed.

**Team-wide sample scope:** Let `R` be the number of returned detail rows and `C` be the sum of `Id.count.value` across the matching in-period forecast-category aggregate rows. Only when `R == C` may the detail rows be called complete for exactly the selected owners and period. Otherwise describe every row-derived deal, Account, stage, activity, risk, hygiene overlap, Monday question, average, and swing claim as "among the team-wide top R by Amount"; never generalize it per rep or to the complete in-period/full-open book. The aggregate remains authoritative for complete in-period count, Amount, Commit, Best Case, and Weighted totals.

**If a GraphQL `aggregate` query errors** (some orgs throw grouping a picklist/Id field), don't retry the same shape — fall to the SOQL `GROUP BY` equivalent, which groups cleanly. **For the combined sample request specifically**, the grouped `aggregate` sibling (`OwnerId`/`ForecastCategory`) can take the whole request down with it — re-fire the sample as the detail `query` alone (drop the `aggregate` block) to keep the named deals, and get the per-rep rollup from this SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT OwnerId, ForecastCategory, COUNT(Id) cnt, SUM(Amount) amt, SUM(ExpectedRevenue) weighted FROM Opportunity WHERE OwnerId IN (<TEAM_USER_IDS>) AND IsClosed = false AND CloseDate >= <Q_START> AND CloseDate <= <Q_END> GROUP BY OwnerId, ForecastCategory" })
```
(Closed-won the same way: swap `IsClosed = false` for `IsWon = true` and drop the `ForecastCategory` group.)

**Hygiene counts (GraphQL aggregate, full book — feeds step 6, not sample-limited).** The top-60 sample above skews toward the biggest deals; these three counts cover every open opp so stale/overdue/blank-NextStep flags aren't undercounted. `<STALE_CUTOFF>` = today − 14 days, `<TODAY>` = today, both as `DateInput` (`{ value: "YYYY-MM-DD" }`):
```
-- Stale 14d+, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, LastActivityDate: { lte: { value: \\\"<STALE_CUTOFF>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })

-- Past CloseDate, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { lt: { value: \\\"<TODAY>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })

-- Blank NextStep, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, NextStep: { eq: null } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })
```
Fire these in the same turn as the rollup/closed-won/sample queries above. If `aggregate` errors on any of the three, fall to SOQL `COUNT(Id) ... GROUP BY OwnerId` with the matching WHERE (same fallback pattern as the rollup above).

**Perf guardrail:** Do NOT fire per-opp SF follow-ups (`EmailMessage`, `Task`, `OpportunityFieldHistory`) — the rollups + sample above already have the data. Email/doc/Slack searches for flagged accounts only (step 3b).

## 3b. Evidence (run after step 3 returns)
Skip evidence for attainment-only, stage-only and direct fact asks. For attention/coaching, run this step after step 3 returns and search only the flagged account names it surfaced. Never guess account names. Tableau still completes its query waves before evidence.

**Run step 3b after step 3 returns.** Then fire email/doc/Slack searches for top 3–5 at-risk accounts only, as tool calls in a single turn:
- **slack**: internal mentions in team channel (if configured) → reps already flagging something

Use whatever Slack search tools are available. If none present, skip silently. Cite source + date for anything you use.

## 4. Per-rep scoreboard
Skip this for stage-only, attention-only and direct hygiene asks. **Projected attainment = (Closed Won + incremental Commit) / positive verified rep quota.** Best Case is upside, excluded from projected attainment; coverage is open pipeline / quota. Format the answer with these denominators stated. A team percentage is summed projected / summed comparable quotas, never an average of rep percentages. If any quota is unavailable, omit the team percentage and identify the missing quota without blocking the other cards.

For `byRep`, use disjoint Closed, Commit, Best Case and remaining Pipeline contributions. The SOQL/GraphQL category rollup is already incremental; on Tableau, confirm whether forecast totals are cumulative and subtract only when their semantics and scope are verified. On the Tableau path, never reconstruct a missing forecast/quota row (answer 7) from category slices; on the SOQL/GraphQL path the category rollup is the source, so use it. Omit an unavailable category rather than treating unknown as zero. **Quota is optional for `byRep`: with no quota, still send the card** — segments from Closed, Commit, Best Case and Pipeline, `projected` = Closed + Commit, a `projectedLabel`, and no `quota` or `attainment`. A missing quota, an unavailable `ExpectedRevenue`, or reps with identical figures never justifies omitting the card. Set one common max at least as large as every full stack and quota. Missing/zero quota means no marker and no percentage. Show rep segment/territory only if it was read. Use consistent category labels and colors across all reps: Closed = `tone: "success"`, Commit = `tone: "success"` with `soft: true`, Best Case = `tone: "info"`, remaining Pipeline = `tone: "info"` with `soft: true`. These reuse the design-token status and action marks (soft is the same mark mixed toward the card surface); never invent colors. Build `byRep.legend` from the union of categories actually present in any rep’s segments, not only the last rep; each entry has the same label, tone and soft flag as its segments.

For each rep, compute and assign a one-word **Call**:

| Rep | Closed | Commit | Weighted | vs Quota | Call |
|---|---|---|---|---|---|

- **Weighted** = sum of (Amount × Probability/100) across open opps
- **Call** = Ahead (closed ≥ quota or weighted comfortably covers gap) / On-track / Behind
- Tip: if a rep's Commit > Weighted, their stages are probably optimistic — challenge it.

If quotas aren't in SFDC, reuse a quota the user gave or omit quota markers and percentages; do not block a stage or hygiene answer to ask for quota.

## 5. Deals that decide the quarter
Skip this for rep-attainment-only, stage-only and direct fact asks; a broad review or attention/coaching ask uses only the bounded sample and cited evidence.

Identify the 3–5 opps that swing the number: large Amount × late stage × rep-needs-it × closing this period. For each, write three lines:

- **Why it matters:** [the math — "$X is N% of [rep]'s gap"]
- **Risk:** [specific thing that could kill it, from evidence]
- **Do this:** [one concrete leader action — "ask [rep] when they last talked to procurement; offer to send exec note if it's been 5+ days"]

The "do this" is the point. Be specific enough that the leader can act without further research.

## 6. Team-level flags
Skip this for attainment-only and stage-only asks. Full-book hygiene counts may span a broader date range than the period chart: label that scope explicitly and never imply those totals are quarter-filtered. Named deals remain a bounded sample.

- **At-risk Commit deals:** any Commit-category deal with risk flags — these threaten the number
- **Coaching signals:** reps with high stale-% (from the hygiene aggregates above, full book) or low coverage
- **Hygiene:** reps ranked by the stale/past-CloseDate/blank-NextStep aggregate counts (full book, not the sample) — name specific accounts from the top-60 sample where they overlap
- **Big swings:** deals >2x average that could make or break the quarter

## 7. Monday questions
Skip this unless the prompt asks for coaching or a broad review yields an actionable risk. Use existing evidence; do not re-search every rep by default.

For each Behind or At-risk rep, write ONE question phrased the way the leader would actually ask it in a 1:1 or Slack. Grounded in a specific deal, conversational, not interrogative. Examples: "where's the [Account] security review at — saw it's been a couple weeks" / "do you need anything from me on [Account] or is it just waiting on them."

Search Slack for each rep's recent posts in the team channel from config — if they already flagged something, reference it instead of re-asking.


## 8. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is registered by name. **Send data only**, using this call once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/team-pipeline", props: <object matching the schema below> })
```

`props` must be a nested JSON object, NOT a string. Never send layout, HTML, icons, colors or expressions in data. When the widget succeeds, do not repeat its contents as text.

### What to send

### The response is lego blocks, in this fixed order

1. `title`: one bold sentence already answering the question, never the skill name.
2. `answer`: 2–4 short markdown bullets, key facts in **bold**, scoped to the question.
3. Optional `byRep`, `byStage`, `attention`, in that order; one card per key.
4. At most one tail: actionable, time-sensitive `callout` with one primary button and a first-person `actionMsg`, OR a quiet `nextStep` without a button.
5. `sources`: only records, lists and evidence actually read, collapsed as Sources (N). Include record URLs only when their IDs are known.

### Scope the blocks to the prompt

A prompt that combines asks, or fits no row below, is treated as Broad.

| The prompt is… | Send / read |
|---|---|
| Broad ("how's my team's pipeline looking this quarter?") | `title` + `answer` + `byRep` + `byStage` + `attention`; tail only for a useful move; `sources`. Run the broad-review reads. Send `byRep` whenever the forecast-category rollup returned data for at least one rep; quota is not needed. |
| Rep comparison ("who is behind quota?") | Only `byRep`, plus the required head and sources. Skip stage, sample, hygiene and evidence. |
| Stage distribution ("show open pipeline by stage") | Only `byStage`, plus the required head and sources. Read the full-book stage aggregate only after team resolution/grounding. |
| Attention ("which deals need attention?") | Only `attention`, plus the required head and sources; tail only if actionable. Read the bounded risk sample and relevant hygiene aggregates, not quota or stage totals. |
| Direct fact ("how many deals are past due?", "what's our open pipeline?") | `title` + `answer` + `sources`, no cards or tail. Run only the matching aggregate. |

- **Omit a key and its block is not shown.** Never fill it with empty arrays, placeholders or "N/A". Data retrieved for another purpose stays out of the response.
- Scope the bullets too. An attainment question does not need a coaching report.
- Preformat display amounts, percentages and dates; numeric chart amounts stay raw currency numbers. Resolve names to plain strings.
- Omit unknown quotas and their percentages, quota line and caption; never divide by zero. The "Projected Attainment" footnote shows only when some rep has a quota percent. With a quota, send `attainment` as one string "<pct> of <quota>" (e.g. "29% of $800K"); the renderer adds the "attainment" caption, so omit `attainmentCaption`.
- `byRep.max` still required: send largest complete stack or known quota × ~1.1. The renderer recomputes the final axis from the data (headroom, clean step; a $4.53M stack → $5M), so an approximate value is fine.
- Use the same period and currency for compared figures.
- A pure list or lookup usually gets no tail. Never send both `callout` and `nextStep`.
- In English, omit `labels`. Otherwise translate every label and all free-text fields, including segment labels, stage labels, sources and the first-person action message.

#### Worked examples

**Broad team review**

```json
{
  "title": "Your team projects 56% of quota with 38 days left — Shannon needs the most help.",
  "answer": "- Across **3 reps**, you have **$410K closed won** and **$7.9M open pipeline** against a **$2.4M team quota**.\n- Closed plus Commit lands at **$1.336M (56%)**; adding Best Case reaches **$2.152M**, a **$248K gap**, with **3.3× open coverage**.\n- **Marcus Levine projects 75%** and **Bryan Corcoran 63%**, while **Shannon Mathews projects 29%** and owns **8 of 11** past-due deals across the full book.",
  "byRep": {
    "max": 5000000,
    "items": [
      {
        "name": "Shannon Mathews",
        "detail": "Enterprise · Manufacturing",
        "projected": 232000,
        "attainment": "29% of $800K",
        "quota": 800000,
        "segments": [
          {
            "label": "Closed",
            "value": 85000,
            "tone": "success"
          },
          {
            "label": "Commit",
            "value": 147000,
            "tone": "success",
            "soft": true
          },
          {
            "label": "Best Case",
            "value": 250000,
            "tone": "info"
          },
          {
            "label": "Pipeline",
            "value": 1603000,
            "tone": "info",
            "soft": true
          }
        ],
        "projectedLabel": "$232K"
      },
      {
        "name": "Bryan Corcoran",
        "detail": "Enterprise · FS + Retail",
        "projected": 504000,
        "attainment": "63% of $800K",
        "quota": 800000,
        "segments": [
          {
            "label": "Closed",
            "value": 95000,
            "tone": "success"
          },
          {
            "label": "Commit",
            "value": 409000,
            "tone": "success",
            "soft": true
          },
          {
            "label": "Best Case",
            "value": 316000,
            "tone": "info"
          },
          {
            "label": "Pipeline",
            "value": 875000,
            "tone": "info",
            "soft": true
          }
        ],
        "projectedLabel": "$504K"
      },
      {
        "name": "Marcus Levine",
        "detail": "Enterprise · Healthcare",
        "projected": 600000,
        "attainment": "75% of $800K",
        "quota": 800000,
        "segments": [
          {
            "label": "Closed",
            "value": 230000,
            "tone": "success"
          },
          {
            "label": "Commit",
            "value": 370000,
            "tone": "success",
            "soft": true
          },
          {
            "label": "Best Case",
            "value": 250000,
            "tone": "info"
          },
          {
            "label": "Pipeline",
            "value": 3680000,
            "tone": "info",
            "soft": true
          }
        ],
        "projectedLabel": "$600K"
      }
    ],
    "legend": [
      {
        "label": "Closed",
        "tone": "success"
      },
      {
        "label": "Commit",
        "tone": "success",
        "soft": true
      },
      {
        "label": "Best Case",
        "tone": "info"
      },
      {
        "label": "Pipeline",
        "tone": "info",
        "soft": true
      }
    ]
  },
  "byStage": {
    "stages": [
      "Prospecting",
      "Qualification",
      "Needs Analysis",
      "Value Proposition",
      "Id. Decision Makers",
      "Perception Analysis",
      "Proposal/Price Quote",
      "Negotiation/Review"
    ],
    "series": [
      {
        "name": "Shannon Mathews",
        "data": [
          200000,
          250000,
          160000,
          170000,
          100000,
          100000,
          450000,
          570000
        ]
      },
      {
        "name": "Bryan Corcoran",
        "data": [
          100000,
          150000,
          100000,
          150000,
          100000,
          100000,
          300000,
          600000
        ]
      },
      {
        "name": "Marcus Levine",
        "data": [
          600000,
          650000,
          550000,
          500000,
          450000,
          350000,
          450000,
          750000
        ]
      }
    ]
  },
  "attention": [
    {
      "name": "Meridian Insurance",
      "amount": "$530K",
      "stage": "Negotiation / Review",
      "owner": "Shannon Mathews",
      "evidence": "Past due 17d (Aug 7); no updated Next Step.",
      "need": "Re-date or disqualify after confirming the close plan.",
      "tone": "error"
    },
    {
      "name": "Cascade Energy",
      "amount": "$410K",
      "stage": "Proposal / Price Quote",
      "owner": "Shannon Mathews",
      "evidence": "Past due 10d (Aug 14); no updated Next Step.",
      "need": "Confirm a new close date and the next buyer action.",
      "tone": "error"
    }
  ],
  "callout": {
    "lead": "11 deals are past their close date — 8 of them are Shannon’s.",
    "text": "The full-book overdue count includes $1.24M owned by Shannon. Meridian Insurance ($530K) and Cascade Energy ($410K) need confirmed close dates or disqualification. With 38 days to quarter close, make cleanup and qualification the next 1:1 topic.",
    "buttonLabel": "Review Shannon’s at-risk deals",
    "actionMsg": "Show me Shannon Mathews’s at-risk deals, starting with Meridian Insurance and Cascade Energy, and recommend the next action for each."
  },
  "sources": [
    {
      "label": "Team opportunity forecast-category and stage aggregates"
    },
    {
      "label": "Rep quotas and team users"
    },
    {
      "label": "Full-book overdue and stale-deal counts"
    },
    {
      "label": "Top open opportunities sampled for coaching"
    }
  ]
}
```

**Specific prompt: show open pipeline by stage**

```json
{
  "title": "The largest stage is Negotiation/Review at $1.92M.",
  "answer": "- **Negotiation/Review holds $1.92M**, led by **Marcus Levine at $750K**.\n- These are **full-book open opportunities this quarter**, grouped by actual sales stage.",
  "byStage": {
    "stages": [
      "Prospecting",
      "Qualification",
      "Needs Analysis",
      "Value Proposition",
      "Id. Decision Makers",
      "Perception Analysis",
      "Proposal/Price Quote",
      "Negotiation/Review"
    ],
    "series": [
      {
        "name": "Shannon Mathews",
        "data": [
          200000,
          250000,
          160000,
          170000,
          100000,
          100000,
          450000,
          570000
        ]
      },
      {
        "name": "Bryan Corcoran",
        "data": [
          100000,
          150000,
          100000,
          150000,
          100000,
          100000,
          300000,
          600000
        ]
      },
      {
        "name": "Marcus Levine",
        "data": [
          600000,
          650000,
          550000,
          500000,
          450000,
          350000,
          450000,
          750000
        ]
      }
    ]
  },
  "sources": [
    {
      "label": "Quarter open-opportunity stage aggregate"
    }
  ]
}
```

**Direct prompt: how many deals are past due?**

```json
{
  "title": "11 open deals are past their close date across the full book.",
  "answer": "- **Shannon Mathews owns 8** of the team’s **11 past-due deals**.\n- This count covers **all open deals**, including those outside this quarter.",
  "sources": [
    {
      "label": "Full-book overdue opportunity counts by rep"
    }
  ]
}
```

`props` schema (JSON Schema). Title, answer and sources are always sent; send the other keys according to the prompt-type table above:

```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, answer, byRep, byStage, attention (cards chosen by the prompt type in the scope table), at most one tail (callout OR nextStep), then sources. Only title, answer and sources are always present; which cards are sent depends on the prompt type. Omit a key and its block is not shown. Format display strings before sending, except numeric chart amounts, quota, max, projected and palette indices. Direct factual asks usually get no cards and no tail. Never invent quotas, evidence, stage totals or complete-book coverage from a sample.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line: the takeaway in the user's context that already answers the question (e.g. 'Cedarline is At Risk – a $640K close and a $2.1M renewal both hinge on one unresponsive CFO.'). Plain text, no markdown. Never the skill name or 'Account Context: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence, that answer ONLY what the user asked. Put **bold** inline on the key values inside each sentence (amounts, dates, names, counts), never on a whole bullet. Do not restate the cards below it. Answer ONLY what was asked (scope the bullets to the prompt); no headings, tables or paragraphs."
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something is time-sensitive AND the user can act on it. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period)."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences of normal-weight text that follow the bold lead on the same line: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Send re-engagement via Katie')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button, only when there is a genuinely useful next move. Use INSTEAD of callout, never both.",
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead (the suggested move)."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning, ending with an offer to help if natural."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: the Salesforce records/lists you actually read, linked (this is where Opportunity/Account record links go). Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Account – Cedarline Financial', 'Open opportunities list')."
          },
          "url": {
            "type": "string",
            "description": "Record or list-view URL. Omit if none."
          }
        }
      }
    },
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Omit in English; otherwise translate every label and every free-text phrase, including chart and series labels.",
      "required": [],
      "properties": {
        "byRep": {
          "type": "string",
          "default": "PROJECTED QUOTA ATTAINMENT BY REP",
          "description": "Translated label. English: 'PROJECTED QUOTA ATTAINMENT BY REP'. Shown when at least one rep has a quota percent."
        },
        "byRepForecast": {
          "type": "string",
          "default": "FORECAST BY REP",
          "description": "Translated label for the rep card when no rep has a quota. English: 'FORECAST BY REP'."
        },
        "projectedCaption": {
          "type": "string",
          "default": "Closed + Commit",
          "description": "Translated caption under a rep's projected amount when that rep has no quota. English: 'Closed + Commit'."
        },
        "byStage": {
          "type": "string",
          "default": "OPEN PIPELINE BY STAGE",
          "description": "Translated label. English: 'OPEN PIPELINE BY STAGE'."
        },
        "attention": {
          "type": "string",
          "default": "OPPORTUNITIES THAT NEED ATTENTION",
          "description": "Translated label. English: 'OPPORTUNITIES THAT NEED ATTENTION'."
        },
        "closed": {
          "type": "string",
          "default": "Closed",
          "description": "Translated label. English: 'Closed'."
        },
        "commit": {
          "type": "string",
          "default": "Commit",
          "description": "Translated label. English: 'Commit'."
        },
        "bestCase": {
          "type": "string",
          "default": "Best Case",
          "description": "Translated label. English: 'Best Case'."
        },
        "pipeline": {
          "type": "string",
          "default": "Pipeline",
          "description": "Translated label. English: 'Pipeline'."
        },
        "attainment": {
          "type": "string",
          "default": "attainment",
          "description": "Translated label shown under the attainment value. English: 'attainment'."
        },
        "quota": {
          "type": "string",
          "default": "Quota",
          "description": "Translated label. English: 'Quota'."
        },
        "needs": {
          "type": "string",
          "default": "Suggestion",
          "description": "Translated label. English: 'Suggestion'."
        },
        "attainmentNote": {
          "type": "string",
          "default": "Projected Attainment is Closed + Commit",
          "description": "Translated label. English: 'Projected Attainment is Closed + Commit'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Translated label. English: 'Sources'."
        }
      }
    },
    "byRep": {
      "type": "object",
      "additionalProperties": false,
      "description": "Card 'PROJECTED QUOTA ATTAINMENT BY REP'. Send for broad team reviews and rep attainment/coverage comparisons. Omit for stage-only, attention-only and direct-fact prompts, and when the forecast-category rollup returned no data; never an empty array. Quota is optional: unknown quotas have no percentage or marker, but the card is still sent. The API value `Forecast` is the Commit category.",
      "required": [
        "max",
        "items",
        "legend"
      ],
      "properties": {
        "hasAttainment": {
          "type": "boolean",
          "description": "Set by the renderer, never send: true when any rep has a quota percent. Controls the attainment formula footnote."
        },
        "max": {
          "type": "number",
          "exclusiveMinimum": 0,
          "description": "Shared raw-currency axis maximum. The renderer recomputes it from the data (so a rough value is fine), with headroom: the larger of the largest complete stack and every known quota, times about 1.1, rounded up to the next clean axis step (e.g. a $4.53M largest stack gives $5M)."
        },
        "items": {
          "type": "array",
          "minItems": 1,
          "description": "Reps sorted by projected attainment ascending when quotas are known; otherwise explain the ordering.",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "description": "",
            "required": [
              "name",
              "projected",
              "segments",
              "projectedLabel"
            ],
            "properties": {
              "name": {
                "type": "string",
                "description": "Rep display name, a plain string."
              },
              "detail": {
                "type": "string",
                "description": "Grounded territory or segment; omit when unavailable."
              },
              "projected": {
                "type": "number",
                "minimum": 0,
                "description": "Closed Won + incremental Commit. Never include Best Case."
              },
              "attainment": {
                "type": "string",
                "description": "Projected / verified positive quota as one preformatted string: percent plus quota, e.g. '29% of $800K'. Shown in red below quota, green at/above, with the 'attainment' caption underneath. Omit if quota is unknown or zero; without quota there is no percent, no quota marker and no caption."
              },
              "quota": {
                "type": "number",
                "description": "Verified rep quota, in raw currency. Omit when unknown or zero; never infer or split team quota.",
                "exclusiveMinimum": 0
              },
              "attainmentCaption": {
                "type": "string",
                "description": "OPTIONAL override for the caption under the attainment value. Normally omit: the caption defaults to labels.attainment ('attainment')."
              },
              "segments": {
                "type": "array",
                "minItems": 1,
                "description": "Disjoint Closed, incremental Commit, incremental Best Case, and remaining Pipeline contributions, in that order. Never put cumulative forecasts here. Omit unavailable categories; do not turn unknown into zero.",
                "items": {
                  "type": "object",
                  "additionalProperties": false,
                  "description": "",
                  "required": [
                    "label",
                    "value",
                    "tone"
                  ],
                  "properties": {
                    "label": {
                      "type": "string",
                      "description": "Forecast category, translated; never a sales stage."
                    },
                    "value": {
                      "type": "number",
                      "minimum": 0,
                      "description": "Raw currency amount; category contributions must be disjoint."
                    },
                    "tone": {
                      "type": "string",
                      "enum": [
                        "success",
                        "info"
                      ],
                      "description": "Stable forecast-category color from the design-token marks: Closed = success, Commit = success with soft, Best Case = info, remaining Pipeline = info with soft. The renderer owns the actual colors."
                    },
                    "soft": {
                      "type": "boolean",
                      "description": "true for the lighter tint: Commit (of success) and Pipeline (of info). Omit for Closed and Best Case."
                    }
                  }
                }
              },
              "projectedLabel": {
                "type": "string",
                "description": "Closed + Commit as formatted currency; displayed when no verified quota percentage exists."
              }
            }
          }
        },
        "legend": {
          "type": "array",
          "minItems": 1,
          "description": "Union of category labels across every rep, in Closed, Commit, Best Case, Pipeline order; use the same tone and soft flag as the corresponding segments. Never derive only from the final rep.",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "label",
              "tone"
            ],
            "properties": {
              "label": {
                "type": "string",
                "description": "Category label matching the segments, translated."
              },
              "tone": {
                "type": "string",
                "enum": [
                  "success",
                  "info"
                ],
                "description": "Same tone as the matching segments."
              },
              "soft": {
                "type": "boolean",
                "description": "Same soft flag as the matching segments."
              }
            }
          }
        }
      }
    },
    "byStage": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL card 'OPEN PIPELINE BY STAGE'. Include for broad team reviews or stage/rep distribution questions. Omit the key otherwise; never an empty array. Keep the same team, period, currency and rep order as the other cards.",
      "required": [
        "stages",
        "series"
      ],
      "properties": {
        "stages": {
          "type": "array",
          "minItems": 1,
          "description": "Stage categories from the full-book aggregate, never forecast categories.",
          "items": {
            "type": "string",
            "description": "Actual org StageName display label, in grounded stage order."
          }
        },
        "series": {
          "type": "array",
          "minItems": 1,
          "description": "One series per rep in stable order. Use full-book stage totals, never sample sums.",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "description": "",
            "required": [
              "name",
              "data"
            ],
            "properties": {
              "name": {
                "type": "string",
                "description": "Rep display name; match the team resolution."
              },
              "data": {
                "type": "array",
                "minItems": 1,
                "description": "One value per stage, same length and order as stages.",
                "items": {
                  "type": "number",
                  "minimum": 0,
                  "description": "Raw currency at the corresponding stage; zero means a verified empty bucket."
                }
              }
            }
          }
        }
      }
    },
    "attention": {
      "type": "array",
      "minItems": 1,
      "description": "OPTIONAL card 'OPPORTUNITIES THAT NEED ATTENTION'. Include for broad team reviews with evidenced risks, or asks for at-risk/stalled/overdue deals or coaching. Omit the key otherwise; never an empty array. This is a bounded sample; full-book hygiene counts come from aggregates.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "description": "",
        "required": [
          "name",
          "owner",
          "evidence",
          "need"
        ],
        "properties": {
          "name": {
            "type": "string",
            "description": "Opportunity name, plain text; never invent a deal from an account name."
          },
          "amount": {
            "type": "string",
            "description": "Formatted currency; omit if unavailable."
          },
          "stage": {
            "type": "string",
            "description": "Grounded StageName display label."
          },
          "owner": {
            "type": "string",
            "description": "Resolved rep display name."
          },
          "evidence": {
            "type": "string",
            "description": "Specific risk with dates or age, grounded in NextStep, CloseDate, LastActivityDate or cited evidence. Describe a missing LastActivityDate as no activity logged, not a fabricated age."
          },
          "need": {
            "type": "string",
            "description": "One recommended leader action. Identify it as a recommendation, never an action already taken."
          },
          "tone": {
            "type": "string",
            "enum": [
              "error",
              "warning",
              "success",
              "neutral"
            ],
            "description": "Severity rail; evidence text must also name the risk."
          }
        }
      }
    }
  }
}
```


## 9. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED
Scope reading and output to the prompt here too. A narrow ask gets only its answer and relevant sections; direct counts get no scoreboard, stage chart, deal sample or coaching section. Do not invent a CloseDate change without field-history evidence. Explain unavailable quota or partial team coverage and cite only data actually read.

```
# Team Pipeline - [Period]
Target $[X] | Closed $[X] | [N] days left

## Scoreboard
| Rep | Closed | Commit | Weighted | Gap | Call |
|---|---|---|---|---|---|
| [Name] | $[X] | $[X] | $[X] | $[X] | Behind |
...
| **Team** | **$[X]** | **$[X]** | **$[X]** | **$[X]** | |

## Deals That Decide the Quarter
**[Account]** - $[X], [Stage], [Rep]
  Why it matters: [the math]
  Risk: [specific, evidenced]
  → **Do this:** [one concrete leader action]

[repeat 3–5x]

## Risk Flags
- Pushed dates: [N] opps moved CloseDate this week
- Stale 14d+: [N] opps - [Account, Account, ...]
- Past close date: [N] opps need hygiene before the call

## Monday Questions
- **[Rep]:** "[one question, conversational, deal-grounded]"
- **[Rep]:** "[...]"

## If you want to dig
- Per-rep detail: ask "just [rep name]"
- Full at-risk list: run pipeline-review with team scope
```
