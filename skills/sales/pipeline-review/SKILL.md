---
name: pipeline-review
display_name: Pipeline Review
description: "Answer questions about one rep's current pipeline, scoped to what was asked: a full review (stage spread and stalled deals), how much is at risk, which deals are stalled, or the biggest lever, from Salesforce stage aggregates, deal samples and closed-deal history. For changes over time, use deal-signals."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:afffe4fa9267b3003d8263e982dad7309a65e811140b6b11c881cda3c0882233"
id: "edaf42b7-8acc-4f36-a5d7-4ffa29cc14ed"
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
# Goal:
Answer what the user asked about their pipeline (how it is spread across stages, how much is at risk, which deals are stalled, coverage, or the next move) in one pass. **Read only what the question needs** and present only that: a broad review ("review my pipeline for the quarter", "where's the risk?") reads and shows the whole picture; a specific ask ("which deals are stalled?", "how much of my pipeline is at risk?") reads and shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full review.** A broad review reads and shows the whole book; a specific ask reads and shows only that. Skip reads the question doesn't need (each read step says which), and don't show something just because you fetched it.
- Resolve scope to one owner before the read; if a named rep is ambiguous, ask — don't guess or probe.
- Reconcile headline totals with the detail rows.

# Pipeline Review

Ground → resolve scope → (aggregate the book + sample the top deals, ONE turn) → assemble + flag → output. This is one rep's pipeline — for "my team's pipeline" use team-pipeline; for "what changed" use deal-signals.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's stage/risk/activity `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. Note scalar `__c` fields worth rolling up (stage-entry date, risk, health, forecast). **Response can be large** on customized orgs — if it overflows or comes back truncated, scan what came back for `__c` fields whose `label` matches your keywords. Grounding is best-effort (customs are additive): if it's still unwieldy, take the standard fields and move on. Stage buckets come from the `StageName` values the reads return; standard fields, `Account`/`Owner` spans, and `OpportunityContactRoles` are reliable across orgs.

## 1b. Resolve scope

- **"my pipeline"** (default) → add `scope: MINE` to the query root — no user-Id lookup.
- **named rep** → resolve one User. Pull enough to disambiguate at a glance — shared/demo orgs collide hard (one name → base user plus regional variants like `(AM)`/`(BK)`/`(SG)`):
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Title { value } IsActive { value } } } } } } }\"}" })
  ```
  **One match** → take its Id. **Several** → list them (Name · Title · active? · Id) and ask the user to pick; the suffix/title is usually the tell. Don't pick or probe their pipelines to guess. Then filter opps by `OwnerId: { eq: \"<UserId>\" }`.
- **team** → out of scope; hand to team-pipeline.

## 2. Read (fill from step 1) — AGGREGATE the book, SAMPLE the top deals, ISSUE ALL IN ONE TURN

**Do not pull the whole book as raw records.** A rep with 100+ open opps returns 75KB+, which overflows the tool result. Salesforce aggregates server-side — use it. The stats come from aggregate rows (a handful, not hundreds); only a small, bounded sample of concrete deals comes back as raw records.

A narrow ask fires only the reads it needs: at-risk, stalled-deal and biggest-lever asks need only 2b (it carries the stage aggregate); win rate needs 2c; book-wide hygiene needs 2d. A broad review fires all three.

Fire these as tool calls in **one turn** (independent). Insert `<OPP_CUSTOM>` = confirmed `__c { value }` fields on the sample query only (aggregates don't need them).

**2a. Whole-book rollup by stage (GraphQL aggregate — folded into the 2b request).** No `CloseDate` filter for a health view — a `THIS_QUARTER` filter silently drops deals as quarter boundaries move. If the user names a period, add explicit `CloseDate: { gte: … lte: … }`. This rollup rides in the 2b query as an `aggregate` sibling of the sample (one dispatch returns both); it yields one row per stage — stage name, count, $ sum — the by-stage table and the open total (Σ), with no extra record pull.

**2b. Top-N sample per stage + whole-book stage rollup (ONE request).** The rollup gives the shape; the sample gives named deals to point at. Cap the sample hard (`first: 40`, biggest first) so it never overflows — this is a sample, not the book. Order by `Amount DESC`; take the top few per stage when you present. The 2a stage `aggregate` rides in this same request as a sibling of the sample — read the by-stage counts/sums and open total from its `aggregate` edges and `totalCount`, the named deals from the sample rows.

**Canonical query integrity:** Treat the literal request below as the canonical template, not an outline. Substitute only grounded `<OPP_CUSTOM>` fields and the documented scope and date values; do not retype, reformat, shorten, or merge or split it, and keep `aggregate` a sibling of `query` under `uiapi`. Before the first dispatch, verify that the nested `queryInput` JSON decodes, every placeholder is resolved or omitted, and `()`, `[]`, and `{}` are balanced. On a JSON or GraphQL syntax error (`InvalidSyntax` or an unexpected `<EOF>`), discard that request and rebuild it once from the literal template with the same substitutions; never patch braces in place or route the request through generated code. If the rebuilt request still fails with a syntax error, report the error and stop.

A syntax error (`InvalidSyntax` or an unexpected `<EOF>`) means the request was reconstructed or truncated, not that GraphQL aggregate is unsupported. Only when the canonical request returns an aggregate execution error may you use the detail-only 2b request plus the SOQL rollup below; never author a standalone GraphQL stage-rollup request.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, first: 40, orderBy: { Amount: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } CreatedDate { value } NextStep { value } LastActivityDate { value } Type { value } Probability { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Id } } } } } } } aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```

**2c. Closed-baseline win rate (GraphQL aggregate, last full quarter).** Counts grouped by won/lost — no record pull, zero date math (`eq: { literal: LAST_QUARTER }`; widen only if asked):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: LAST_QUARTER } } }, groupBy: { IsWon: { group: true } }) { edges { node { aggregate { IsWon { value } Id { count { value } } Amount { sum { value } } } } } } } } }\"}" })
```

**2d. Whole-book hygiene by stage (GraphQL aggregate).** Blank-`NextStep` count per stage across the entire book — so the hygiene finding is book-wide, not "among the top 40 sampled". No date math:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, NextStep: { eq: null } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } } } } } } } }\"}" })
```
(Same `OwnerId` swap for a named rep. A stale-by-stage rollup is also expressible with a computed `LastActivityDate: { lt: "<today−14d>" }` cutoff grouped by StageName — but null-activity rows won't match `lt`, so it under-counts never-touched deals; blank-NextStep is the clean whole-book signal.)

**Named rep** → swap every `scope: MINE` for `OwnerId: { eq: \"<UserId>\" }`. **Empty** 2a `edges`/`totalCount: 0` → no open pipeline for this scope; say so plainly, skip the rest.

**If a GraphQL `aggregate` query errors** (some orgs throw `DataFetchingException` grouping a picklist/Id field), don't retry the same shape — fall to the SOQL `GROUP BY` equivalent, which groups picklists cleanly. **For the 2b combined request specifically**, the grouped `aggregate` sibling (`StageName`) can take the whole request down with it — re-fire 2b as the detail `query` alone (drop the `aggregate` block) to keep the sample, and get the by-stage rollup from this SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE IsClosed = false AND OwnerId = '<UserId>' GROUP BY StageName" })
```
(Own scope → resolve the current user's Id first, or filter by `Owner.Name`; SOQL has no `scope: MINE`.) Win rate the same way: `SELECT IsWon, COUNT(Id) cnt FROM Opportunity WHERE IsClosed = true AND CloseDate = LAST_QUARTER AND OwnerId = '<UserId>' GROUP BY IsWon`.

## 3. Assemble + flag (record only; reconcile totals; invent nothing)

Assemble only what the prompt needs; the bullets below are the full review.

- **By stage** — straight from 2a's aggregate rows: count, $ sum per stage. Σ of stage $ = open total (they come from the same query, so they reconcile by construction). **Blank-NextStep per stage is whole-book from 2d** — report those counts as book-wide. Staleness/aging per-stage aren't in an aggregate; report those from the 2b sample and **say they're "among the top N sampled," not whole-book**.
- **Top deals per stage** — from the 2b sample, name the biggest 2–3 opps in each stage (Account · $ · close · next-step state · type) so the rep sees concrete deals, not just totals.
- **At-risk opps** — from the 2b sample, flag any that hit: stale (no activity 14d+) · past `CloseDate` · blank `NextStep` · **single-threaded (`OpportunityContactRoles` edge count ≤ 1)**. **If a flag matches nearly the whole sample** (e.g. every opp has a blank `NextStep`, common in lightly-maintained orgs), report it once as a **systemic finding** — use 2d's book-wide blank-NextStep count for that line ("next-step blank on N of M open — hygiene gap") — and rank the at-risk list by $, rather than dumping dozens of identical-looking rows.

**At-risk ranking:** Derive counts and display rows by transforming the returned Opportunity nodes keyed by Id; never hand-author or retype an intermediate tuple or row list, and copy each `Name.value`, Amount, and CloseDate exactly, including punctuation. When the sample's edge count equals `totalCount`, count and sum every matching row and reconcile the headline with the rows; otherwise label the finding sampled. Build candidates from every sampled Opportunity matching any risk above, even when a pervasive risk is summarized once, sort the complete set by returned Amount descending before truncating, and self-check that no later row is larger than an earlier row.

- **Coverage** — weighted open pipeline (from 2a totals × stage probability if grounded, else raw open $) vs quota (only if the user gives one) or vs last-quarter closed $ from 2c; 3× remaining-gap heuristic; note if under.
- **Velocity** — from 2c: win rate = won ÷ (won+lost) counts. **Cycle time / median: don't compute it** — no API (GraphQL aggregate or SOQL) supports median or date subtraction, and reconstructing it means pulling every closed record (the overflow we're avoiding). Only report an average cycle if grounding surfaced a numeric sales-cycle `__c` field you can `avg` in the aggregate. Stage→stage conversion needs stage history; omit — don't fabricate.

## 4. Output — widget FIRST (the rendered UI is the default)

**Widget transport:** Pass the fully hydrated renderer to `display_widget` as a direct top-level tool call whose `widgetDefinition` is a native JSON object. Never serialize or quote it, and never build or send it through generated code, a shell, a code runner, or temporary files. A returned string, printed preview, or generated file is not a mounted visual and is never a successful render. If the call succeeds, it is the terminal output: stop with no further assistant text. If it returns an error or the tool is unavailable, do not retry, repair, or create a substitute artifact; emit only the section 5 text fallback and stop, and never claim the widget rendered.
- ❌ WRONG: `widgetDefinition: "{\"key\":...}"` (stringified with escaped quotes)
- ✅ RIGHT: `widgetDefinition: {"key":...}` (native object, no quotes around the opening brace)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/pipeline-review", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 5 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`why`, `next`, `close`, `_status`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("review my pipeline for the quarter", "where's the risk?", "how healthy is my pipeline?") | `title` + `answer` (bullets) + `byStage` + `stalledDeals` (`layout: "table"`) when deals are flagged + tail only if it applies + `sources` |
| Stalled / at-risk deals ("which deals are stalled?", "what's slipping?") | `title` + `answer` + **only** `stalledDeals` (`layout: "list"`) + `sources` (the deals) |
| Stage spread ("how is my pipeline spread across stages?") | `title` + `answer` + **only** `byStage` + `sources` (the list) |
| A question with a direct answer ("how much of my pipeline is at risk?", "what's my biggest lever this week?", "am I covered for the quarter?", "what's my win rate?") | `title` + `answer` (paragraph) + `callout` only for the biggest-lever ask + `sources` — no card |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for or that does not speed up the answer.
- **Scope the `answer` too:** for "how much is at risk?", the answer is the at-risk total and where it sits — not coverage, win rate, or hygiene you also read.
- **Coverage, win rate and hygiene have no card:** put what the prompt needs from them in `answer` ("coverage 2.4× against the remaining gap", "win rate 38% last quarter", "next step blank on 14 of 40 open").
- **At risk = the step 3 at-risk flags** (stale 14d+, past `CloseDate`, blank `NextStep`, single-threaded). The at-risk total is the sum of the flagged deals' amounts.
- **`byStage`:** stages in sales-process order with each stage's open amount as a number. Send `atRisk` only when one stage holds most of the at-risk money: that stage's amount goes in `atRisk` and `null` takes its place in `open`.
- **`stalledDeals`:** the flagged deals, biggest first, at most 5. On a broad review list the flagged deals of the stage that holds the risk. **Table** rows carry the deal's close probability from `Probability`: `_tone` `success` with `_status` "High" at 70% or more, `warning` with "Med" at 40–69%, `error` with "Low" below 40%. **List** rows: `_tone` is `error` with `_status` "At risk" when the deal is past its `CloseDate` or closes within 14 days; otherwise `warning` with `_status` "Stalled".
- **Tail fork:** a broad review gets a `nextStep` line (bold lead, no button, no icon) when one move stands out; only the biggest-lever ask gets the `callout` (one button, a first-person `actionMsg`); if nothing applies, neither. A specific ask usually gets no tail. Never both (if both are sent only the callout renders).
- **Sources:** a record is `https://<myDomain>/lightning/r/Opportunity/<Id>/view`; the book is `https://<myDomain>/lightning/o/Opportunity/list`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string except the `byStage` amounts, which are numbers. Names are plain strings, never objects. `stalledDeals.items[].next` is "None set" when `NextStep` is blank.
- **Value formats (apply to every row; the mock values in the examples are illustrative only):** `amount` is compact — `$` + number + `K`/`M`, no thousands separators. `close` is short month + day + days left, never a year or ISO date. In a table row `account` is the bold title and `name` the subtitle under it; in `next`, wrap only the action in `**…**` and leave the stuck-reason plain.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

**Broad — "Review my pipeline for the quarter. Where's the risk?"** (bulleted answer, both cards, a next-step line, several sources):

```json
{
  "title": "$1.41M of your pipeline is at risk – and it's stacked in one stage.",
  "answer": "- **$2.63M open** across 8 opportunities.\n- The money and the risk sit together: **Negotiation / Review holds $1.14M**.\n- **2 of the 3 deals** in that stage are stalled.",
  "byStage": {
    "stages": ["Prospecting", "Qualification", "Needs Analysis", "Value Proposition", "Id. Decision Makers", "Perception Analysis", "Proposal / Price Quote", "Negotiation / Review"],
    "open": [180000, 210000, 90000, 155000, 120000, 95000, 645000, null],
    "atRisk": [null, null, null, null, null, null, null, 1140000]
  },
  "stalledDeals": {
    "layout": "table",
    "items": [
      {
        "account": "Cedarline Financial",
        "name": "Enterprise Sales Cloud Platform",
        "amount": "$640K",
        "next": "Stale 43d · new CFO sponsor unresponsive 3 wks. Draft ROI-repack outreach.",
        "close": "Aug 31 · 7d",
        "stage": "Negotiation / Review",
        "_tone": "error",
        "_status": "Low"
      },
      {
        "account": "Brightview Media",
        "name": "Ad Sales Cloud + CPQ",
        "amount": "$410K",
        "next": "MSA redlines returned 8/12 · no movement since (18d stale). Nudge Elena Cortez for signing call.",
        "close": "Aug 31 · 7d",
        "stage": "Negotiation / Review",
        "_tone": "warning",
        "_status": "Med"
      }
    ]
  },
  "nextStep": {
    "lead": "Reopen the biggest deal first.",
    "text": "Cedarline is the biggest lever – $640K stalled on a CFO with no engagement, and getting that sponsor back in the conversation is the highest-value move before the quarter closes. Want me to draft a re-engagement plan for it?"
  },
  "sources": [
    {
      "label": "Opportunities · 8 open (this quarter)",
      "url": "https://<myDomain>/lightning/o/Opportunity/list"
    },
    {
      "label": "Opportunity · Cedarline Financial",
      "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"
    },
    {
      "label": "Opportunity · Brightview Media",
      "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"
    }
  ]
}
```

**Direct — "How much of my pipeline is at risk?"** (paragraph answer, no card, no tail, the book as the source):

```json
{
  "title": "$1.41M of your $2.63M open pipeline is at risk.",
  "answer": "Of **$2.63M open across 8 opportunities, $1.41M is at risk** – concentrated in Negotiation / Review, which holds $1.14M on its own.",
  "sources": [
    {
      "label": "Opportunities · 8 open",
      "url": "https://<myDomain>/lightning/o/Opportunity/list"
    }
  ]
}
```

**Specific — "Which deals are stalled?"** (the stalledDeals list only, the deals as sources, no tail):

```json
{
  "title": "Two Negotiation deals are stalled – $1.05M between them.",
  "answer": "Both sit in **Negotiation / Review** and haven't moved.",
  "stalledDeals": {
    "layout": "list",
    "items": [
      {
        "account": "Cedarline Financial",
        "amount": "$640K",
        "why": "CFO dark · 16 days silent",
        "_tone": "warning",
        "_status": "Stalled"
      },
      {
        "account": "Brightview Media",
        "amount": "$410K",
        "why": "In Legal · MSA idle since 8/12",
        "_tone": "warning",
        "_status": "Stalled"
      }
    ]
  },
  "sources": [
    {
      "label": "Opportunity · Cedarline Financial",
      "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"
    },
    {
      "label": "Opportunity · Brightview Media",
      "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"
    }
  ]
}
```

**Direct — "What's my biggest lever this week?"** (paragraph answer, a callout with one button, no card):

```json
{
  "title": "Reopen Cedarline – $640K on a dark CFO.",
  "answer": "It's the single highest-value move: **$640K stalled** on a dark CFO. Get that conversation back open before the quarter closes.",
  "callout": {
    "lead": "Cedarline closes Aug 31 – the CFO has been silent for 16 days.",
    "text": "Send a short ROI recap to re-engage the new CFO sponsor this week.",
    "buttonLabel": "Draft the CFO re-engagement",
    "actionMsg": "Draft a re-engagement email to the new CFO at Cedarline Financial with an ROI recap to restart the $640K deal."
  },
  "sources": [
    {
      "label": "Opportunity · Cedarline Financial",
      "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"
    }
  ]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (byStage, stalledDeals), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A direct question ('how much of my pipeline is at risk?') usually gets no tail. Format every value as a ready-to-display string (currency, dates) except the byStage chart amounts, which are numbers; names are plain strings, never objects.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, chart series names, table headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "byStage": {
          "type": "string",
          "default": "OPEN PIPELINE BY STAGE",
          "description": "Heading of the by-stage chart card. English: 'OPEN PIPELINE BY STAGE'."
        },
        "seriesOpen": {
          "type": "string",
          "default": "Open pipeline",
          "description": "Chart series name (read by screen readers and tooltips; no legend is drawn) for the stages that are not the risk stage. English: 'Open pipeline'."
        },
        "seriesAtRisk": {
          "type": "string",
          "default": "Where the risk sits",
          "description": "Chart series name (read by screen readers and tooltips; no legend is drawn) for the highlighted risk stage. English: 'Where the risk sits'."
        },
        "openOpportunities": {
          "type": "string",
          "default": "OPEN OPPORTUNITIES",
          "description": "Heading of the deals card (table and list). English: 'OPEN OPPORTUNITIES'."
        },
        "colStatus": {
          "type": "string",
          "default": "Close Probability",
          "description": "Stalled-deals table header over the _status badges (High / Med / Low). English: 'Close Probability'."
        },
        "colAccount": {
          "type": "string",
          "default": "Account",
          "description": "Header of the stalled-deals list's Account column, read by screen readers (the list hides its header row; the table has no Account column). English: 'Account'."
        },
        "colOpportunity": {
          "type": "string",
          "default": "Opportunity",
          "description": "Stalled-deals table header. English: 'Opportunity'."
        },
        "colAmount": {
          "type": "string",
          "default": "Amount",
          "description": "Stalled-deals table header. English: 'Amount'."
        },
        "colNextStep": {
          "type": "string",
          "default": "Next Step",
          "description": "Stalled-deals table header. English: 'Next Step'."
        },
        "colClose": {
          "type": "string",
          "default": "Close Date",
          "description": "Stalled-deals table header. English: 'Close Date'."
        },
        "colStage": {
          "type": "string",
          "default": "Stage",
          "description": "Stalled-deals table header. English: 'Stage'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "title": {
      "type": "string",
      "description": "REQUIRED. The takeaway for the pipeline in the user's context, one bold sentence that already answers the question (e.g. '$1.41M of your pipeline is at risk – and it's stacked in one stage.'). Never the skill name or 'Pipeline Review'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (amounts, counts, stages, names). A broad review gets 2-4 short '- ' bullets; a direct question ('how much is at risk?', 'what's my biggest lever?') gets a 1-3 sentence paragraph. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "byStage": {
      "type": "object",
      "description": "OPTIONAL card 'OPEN PIPELINE BY STAGE · AMOUNT': a horizontal bar per stage with its amount printed. Include ONLY for a broad review ('review my pipeline', 'where's the risk?', 'pipeline health') or when the prompt asks how the pipeline is spread across stages. Omit the key otherwise.",
      "required": [
        "stages",
        "open"
      ],
      "properties": {
        "stages": {
          "type": "array",
          "description": "Stage display values in sales-process order, earliest first (e.g. ['Prospecting', 'Qualification', 'Negotiation / Review']). One entry per stage with open pipeline.",
          "items": {
            "type": "string"
          }
        },
        "open": {
          "type": "array",
          "description": "Open amount per stage as a NUMBER (e.g. 1140000), same length and order as stages. Put null at the risk stage's position when atRisk is sent.",
          "items": {
            "type": [
              "number",
              "null"
            ]
          }
        },
        "atRisk": {
          "type": "array",
          "description": "OPTIONAL. Highlights the one stage where the at-risk money sits: same length as stages, that stage's amount at its position and null everywhere else. Omit when no single stage holds the risk.",
          "items": {
            "type": [
              "number",
              "null"
            ]
          }
        }
      }
    },
    "stalledDeals": {
      "type": "object",
      "description": "OPTIONAL card 'OPEN OPPORTUNITIES': the flagged deals from the sample, biggest first. Include ONLY for a broad review (layout 'table') or when the prompt asks which deals are stalled, slipping or at risk (layout 'list'). Omit the key otherwise; never an empty items array.",
      "required": [
        "layout",
        "items"
      ],
      "properties": {
        "layout": {
          "type": "string",
          "enum": [
            "table",
            "list"
          ],
          "description": "'table' for a broad review (close probability, opportunity, amount, next step, close date, stage); 'list' for a stalled/at-risk ask (account – amount, and why it is stuck)."
        },
        "items": {
          "type": "array",
          "description": "One entry per flagged deal, biggest amount first (never an empty array - omit stalledDeals instead).",
          "items": {
            "type": "object",
            "required": [
              "account",
              "amount",
              "_tone",
              "_status"
            ],
            "properties": {
              "account": {
                "type": "string",
                "description": "Table: the bold title of the Opportunity cell (the account name, e.g. 'Cedarline Financial'). List: the account name."
              },
              "name": {
                "type": "string",
                "description": "Table only: the opportunity name, shown as the muted subtitle under the bold account (e.g. 'Enterprise Sales Cloud Platform')."
              },
              "amount": {
                "type": "string",
                "description": "Compact pre-formatted amount: $ + number + K or M, no thousands separators (e.g. '$640K', '$1.2M'; never '$640,000')."
              },
              "next": {
                "type": "string",
                "description": "Table only: what is stuck, then the move, from NextStep and days since last activity. Wrap only the action (the move) in markdown bold '**…**'; the stuck-reason stays plain (e.g. 'Stale 43d · CFO sponsor unresponsive 3 wks. **Draft ROI-repack outreach.**'). 'None set' (no bold) when NextStep is blank."
              },
              "close": {
                "type": "string",
                "description": "Table only: short month and day with no year, then days left (e.g. 'Aug 31 · 7d', 'Aug 12 · 5d late'). Never a year, never ISO YYYY-MM-DD."
              },
              "stage": {
                "type": "string",
                "description": "Stage display value (e.g. 'Negotiation / Review'). Table only."
              },
              "why": {
                "type": "string",
                "description": "Why it is stuck, a few words joined by ' · ' (e.g. 'CFO dark · 16 days silent'). List only."
              },
              "_tone": {
                "type": "string",
                "enum": [
                  "error",
                  "warning",
                  "success"
                ],
                "description": "Row status tone (see the tone rule in the skill instructions). Table: the close-probability tone (success High, warning Med, error Low); list: error or warning only."
              },
              "_status": {
                "type": "string",
                "description": "The status word shown with the tone, in the user's language. Table (English): 'High' for success, 'Med' for warning, 'Low' for error. List (English): 'At risk' for error, 'Stalled' for warning."
              }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail for the biggest-lever ask only (not on a broad review). Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the move in one sentence, ending with a period, e.g. 'Reopen Cedarline – $640K on a dark CFO.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Draft the CFO re-engagement')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "description": "OPTIONAL tail, the default for a broad review: a plain suggestion line with a bold lead, NO button and NO icon. Use INSTEAD of callout, never both.",
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead (the suggested move, e.g. 'Reopen the biggest deal first.')."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning, ending with an offer to help if natural."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: the Salesforce records/lists you actually read, linked (this is where Opportunity record links go). Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name: object · record (e.g. 'Opportunities · 8 open', 'Opportunity · Cedarline Financial')."
          },
          "url": {
            "type": "string",
            "description": "Record URL https://<myDomain>/lightning/r/<SObjectType>/<Id>/view, or for a list https://<myDomain>/lightning/o/Opportunity/list. Omit if none."
          }
        }
      }
    }
  }
}
```


## 5. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask ("which deals are stalled?", "how much is at risk?") gets only the lines that answer it, not every section below.

```
# Pipeline Review — <Scope> — <Period>

## Summary
Open: <N> opps, $<total> · weighted $<weighted> · coverage <N>× <✅ / ⚠ under 3×> · at-risk <N>, $<sum>

## By stage (whole book)
<Stage> · <N> opps · $<sum>
…  (Σ stage $ = $<total>, Σ opps = <N> — from the rollup)

## Top deals per stage (sampled, biggest first)
<Stage>: <Account> $<X> close <Date> · <next-step state> · <Type>; <Account> $<X> close <Date> …
… (name the biggest 2–3 opps per stage — the sample holds them)

## At-risk (from sample, biggest first)
<Account> · <Stage> · $<X> · close <Date> · <flags> → <action>
…  (Σ at-risk $ = $<sum>)
[If a flag hits nearly all sampled: one line — "Systemic: next-step blank on all <N> sampled — hygiene gap", don't list every row.]

## Conversion Signal (last-Q baseline)
Win rate <N%> (won <N> ÷ won+lost <N>, from 2c)[ · avg cycle <N>d only if a cycle-days field was grounded]. Stage→stage conversion needs stage history — omit, don't fabricate.

## Focus
1. Highest-$ at-risk + action
2. Biggest / most-exposed stage + action
3. Coverage gap if under 3×
```
