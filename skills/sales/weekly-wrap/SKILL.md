---
name: weekly-wrap
display_name: Weekly Wrap (Preview)
description: "Answer questions about a rep's or team's sales week from Salesforce opportunity and calendar activity plus email, documents and Slack, scoped to what was asked: how the week went, what moved (wins, losses, advances, slips), or what closes next week. Use to review a week, prepare for Monday or draft an internal update."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:0ca25b7f574e25c88c6403be75090eb2b04205134c885bd392b0bedd84d43183"
id: "034f9b9b-6a0e-4405-87eb-99e3deba2f7f"
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
Answer what the user asked about the week (how it went, what moved, or what closes next week) in one pass. **Read only what the question needs** and present only that: a broad ask ("wrap up my week") reads and shows the whole week; a specific ask ("what's closing next week?") reads and shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full recap.** Skip the reads the question doesn't need (each step says which), and don't show something just because you fetched it.


# Weekly Wrap

Ground → resolve scope (team only) → (TWO parallel SFDC reads + email/doc evidence, ALL in ONE turn) → assemble + flag → output. Keep the six detail roots and six aggregate roots in separate requests so each stays below the GraphQL fetcher limit.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's close/loss-reason `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } childRelationships { childObjectApiName relationshipName } } } }\"}" })
```

Note any scalar `__c` fields worth surfacing (close/loss reason, stage-context note). Standard fields and the `Account` span are reliable across orgs.
Also note `<HISTORY_CHILD>` = the `relationshipName` whose `childObjectApiName` is `OpportunityHistory` (commonly `OpportunityHistories`); step 2 nests it.

## 1b. Resolve scope (team only — skip for "my week")

- **"my week"** (default) → `scope: MINE` on every root below, no lookup needed.
- **"team"** → resolve direct reports once:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { ManagerId: { eq: \\\"<CURRENT_USER_ID>\\\" }, IsActive: { eq: true } }, first: 50) { edges { node { Id Name { value } } } } } } }\"}" })
  ```
  Capture the Ids as `<TEAM_USER_IDS>`; swap every `scope: MINE` in step 2 for `OwnerId: { in: [<TEAM_USER_IDS>] }`. If your org's team hierarchy isn't ManagerId-based, resolve the roster once from context instead of guessing.

## 2. Read — pipeline movement + calendar in TWO dispatches; evidence in the SAME turn

**Why two:** a GraphQL request allows at most 10 subqueries ([Salesforce GraphQL query limits](https://developer.salesforce.com/docs/platform/graphql/guide/query-limits.html)). Six detail roots plus six aggregate roots in one request fails with `ExecutionAborted: The number of data fetchers in the query is 12, exceed the data fetcher limitation 10`. Fire the detail read and the aggregate read below as two `dispatch_readonly` GET GraphQL calls in the same parallel tool turn. Don't merge them back into one request.

**Detail read, six aliased roots:** closed, new, touched (moved), and closing-next-week Opportunities, plus this-week and next-week meetings. `LastModifiedDate` on still-open opps is the movement signal; the `touchedThisWeek` root nests `<HISTORY_CHILD>` (stage and close-date history, for the from→to in `changes`) and `OpportunityContactRoles` (a contact role created this week = a stakeholder added). Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields from step 1. If step 1 grounded no `<HISTORY_CHILD>`, drop it from the query and report "active this week, now at [Stage]" without an arrow.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { closedThisWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } newThisWeek: Opportunity(scope: MINE, where: { CreatedDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CreatedDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } touchedThisWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, LastModifiedDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } LastModifiedDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } <HISTORY_CHILD>(first: 10, orderBy: { CreatedDate: { order: DESC } }) { edges { node { StageName { value } CloseDate { value } CreatedDate { value } } } } OpportunityContactRoles(first: 10) { edges { node { CreatedDate { value } Contact { Name { value } Title { value } } } } } } } } closingNextWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { eq: { literal: NEXT_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } meetingsThisWeek: Event(scope: MINE, where: { ActivityDate: { eq: { literal: THIS_WEEK } } }, orderBy: { StartDateTime: { order: ASC } }, first: 50) { edges { node { Id Subject { value } StartDateTime { value } Location { value } WhatId { value } } } } meetingsNextWeek: Event(scope: MINE, where: { ActivityDate: { eq: { literal: NEXT_WEEK } } }, orderBy: { StartDateTime: { order: ASC } }, first: 50) { edges { node { Id Subject { value } StartDateTime { value } Location { value } WhatId { value } } } } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate {  closedAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: THIS_WEEK } } }, groupBy: { IsWon: { group: true } }) { edges { node { aggregate { IsWon { value } Id { count { value } } Amount { sum { value } } } } } } newAgg: Opportunity(scope: MINE, where: { CreatedDate: { eq: { literal: THIS_WEEK } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } } touchedAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, LastModifiedDate: { eq: { literal: THIS_WEEK } } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } Amount { sum { value } } } } } } closingAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { eq: { literal: NEXT_WEEK } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } } meetingsThisWeekAgg: Event(scope: MINE, where: { ActivityDate: { eq: { literal: THIS_WEEK } } }) { edges { node { aggregate { Id { count { value } } } } } } meetingsNextWeekAgg: Event(scope: MINE, where: { ActivityDate: { eq: { literal: NEXT_WEEK } } }) { edges { node { aggregate { Id { count { value } } } } } } } } }\"}" })
```

**Team scope** → swap every `scope: MINE` above for `OwnerId: { in: [\"<TEAM_USER_IDS>\"] }`.

**Aggregate read: the second dispatch above, paired root-for-root with the `query {}` detail (two dispatches, not twelve).** The six first:50 `query {}` roots are bounded example rows, not the count/$ source — Net $, won/lost, new, touched (by stage), and closing-next-week counts **and amounts** come from the paired `aggregate {}` roots instead: `closedAgg` (grouped by `IsWon`), `newAgg`, `touchedAgg` (grouped by `StageName`), `closingAgg`, `meetingsThisWeekAgg`, `meetingsNextWeekAgg`. The team-scope swap above (`scope: MINE` → `OwnerId: { in: [...] }`) applies to the `aggregate {}` roots too.

**Grouping fallback — only if the aggregate read errors.** `closedAgg` groups on `IsWon` and `touchedAgg` on `StageName`; grouping a boolean/picklist throws `DataFetchingException` in some orgs. If the query errors on either grouped root, re-fire just that total as a SOQL `GROUP BY` (own scope shown; team scope → `OwnerId IN (<TEAM_USER_IDS>)`), which groups cleanly:

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT IsWon, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '<CURRENT_USER_ID>' AND IsClosed = true AND CloseDate = THIS_WEEK GROUP BY IsWon" })
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '<CURRENT_USER_ID>' AND IsClosed = false AND LastModifiedDate = THIS_WEEK GROUP BY StageName" })
```

**If the aggregate request returns no usable `data`**, don't stop at the two SOQL totals. A grouped root's `DataFetchingException` can surface as top-level `errors` with `data` null or absent, which takes the other four aggregate roots down with it. The detail read is a separate dispatch, so its rows are unaffected. Re-fire the aggregate request with `closedAgg` and `touchedAgg` removed, keeping the four non-grouped roots (`newAgg`, `closingAgg`, `meetingsThisWeekAgg`, `meetingsNextWeekAgg`), then take the closed-by-`IsWon` and touched-by-`StageName` totals from the two SOQL `GROUP BY` calls above. That recovers the detail rows and all six totals without the roots that trigger the exception.

If an aggregate root's `count` exceeds 50, label its paired detail root's rows "Top 50 of `<count>`" in step 3 — never derive the count/$ from the capped detail rows themselves. If an aggregate root errors (and the grouping fallback above doesn't apply or also fails), mark that total unavailable and avoid complete-population wording — do **not** fall back to summing/counting the capped rows.

**In the SAME turn**, fire (independent, don't wait on the read above):
- **email** — customer-domain threads touched this week (count + top senders).
- **docs/Slack** — if available, anything noteworthy this week per account. Use whatever connector tools are present; skip silently if none.
- **Einstein Opportunity Score** — only when the closing-next-week table is shown. A separate call, so an org without Einstein (no `OpportunityScore` object) fails only this read. **If the call fails with any error (400, INVALID_FIELD, "No such column", etc.), silently continue without the score column—do not surface the error to the user or mention Einstein unavailability in your output.** Team scope → `OwnerId IN (<TEAM_USER_IDS>)`:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
    queryParams: { "q": "SELECT OpportunityId, Score FROM OpportunityScore WHERE OpportunityId IN (SELECT Id FROM Opportunity WHERE OwnerId = '<CURRENT_USER_ID>' AND IsClosed = false AND CloseDate = NEXT_WEEK)" })
  ```

Narrow asks read less. "How much did I close?" needs only `closedAgg` and `closedThisWeek`; "what's closing next week?" needs only `closingNextWeek`, `closingAgg`, `meetingsNextWeek` and the score read; "what moved?" needs the closed, new and touched roots. Drop the roots a narrow ask doesn't need from the query (keep each detail root's paired aggregate) and skip the email and docs/Slack evidence for every ask except a broad one.

## 3. Assemble + flag (record only; reconcile totals; invent nothing)

- **Closed** — won/lost counts and Net $ from the `closedAgg` root (`count`/`sum` per `IsWon` branch; Net = the won branch's `sum` − nothing, lost isn't subtracted, just reported). Detail rows (✅ won / ❌ lost, with loss reason if an `__c` field surfaced it) from `closedThisWeek` — label "Top 50 of `<count>`" if the won+lost total exceeds 50.
- **Moved** — per-stage counts and $ from the `touchedAgg` root, grouped by `StageName` (`count`/`sum` per stage; total = Σ`count`). Detail: open opps modified this week, grouped by current stage, from `touchedThisWeek` (label "Top 50 of `<count>`" if it exceeds 50). **From→to comes only from `<HISTORY_CHILD>`:** the stage or close date before this week is the newest history row created before this week's Monday; a move back to an earlier stage (picklist order), or a later close date, is a slip, never an advance. With no history row, report "active this week, now at [Stage]" and never fabricate an arrow. A contact role created this week is a stakeholder added; going from one contact role to two is "de-singled". Adding a contact role doesn't touch the opportunity, so these show only on opps also edited this week; never claim no deal gained a stakeholder.
- **New** — count and $ from the `newAgg` root (`count`/`sum`). Detail: account, amount, starting stage, from `newThisWeek` (same cap label).
- **Activity** — meeting count from the `meetingsThisWeekAgg` root's `count` (eyeball `meetingsThisWeek` Subject/Location for internal-only noise, e.g. standups, and don't count those as customer activity — but the aggregate itself still reflects the raw total), plus the email thread count from evidence.
- **Monday** — meeting count from the `meetingsNextWeekAgg` root's `count`, detail from `meetingsNextWeek` (time, subject, account if `WhatId` resolves); closing-next-week count and $ from the `closingAgg` root (`count`/`sum`), detail from `closingNextWeek` opps; plus any `NextStep` text already in hand that names a date next week (scan, don't re-query).

**Grounded widget mode:** Build each activity series only from dated returned rows: Meetings from `meetingsThisWeek`, and Calls or Emails only from available connectors that returned dated selected-week evidence. Omit an unavailable series instead of filling it with zero; when detail count `R` differs from its matching aggregate count `C`, label that series as returned `R of C` rather than complete. Remove only the `tile/waterfall` block unless an attributable prior baseline and direct evidence for every displayed Won, New pipeline, Slipped, and Lost delta are available; missing waterfall evidence is not a text-fallback condition, so call `display_widget` with the remaining header, chart, grid, callout, and both buttons. Render each open `touchedThisWeek` row as `status: {"value":"Active","badgeVariant":"info"}`, `event: {"value":"Active this week","badgeVariant":"info"}`, and note `Now at <current Stage>`; never label it Slipped, Close moved, or from→to without history. A returned count of zero may be shown as zero, but a null/unavailable sum remains omitted rather than becoming `$0`.

## 4. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/weekly-wrap", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 5 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`title`, `answer`, the `metrics` labels and details, the `changes` rows, the tail, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("wrap up my week", "how did my team's week go?") | `title` + `answer` (bullets) + `metrics` + `changes` + `closingSoon` + `callout` or `nextStep` + `sources` |
| The scoreboard ("how did I do this week?") | `title` + `answer` + `metrics` + `sources` |
| What moved ("what moved this week?", "what slipped?") | `title` + `answer` + `changes` + `sources` |
| Next week ("what's closing next week?") | `title` + `answer` + `closingSoon` + `sources`, plus a `callout` when one of those deals needs a move before Monday |
| A direct question ("how much did I close this week?") | `title` + `answer` (paragraph) + `sources` — no card, no tail |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for.
- **Numbers come from the aggregates, not the capped rows** (step 3): closed $, meetings, and the closing-next-week count and $. Deals advanced is the exception: count the `touchedThisWeek` rows whose history shows a forward stage move (slips don't count).
- **`metrics`:** up to four tiles in order: Closed this week, Deals advanced, Customer meetings, Closing next week (leave out one you have no data for). Customer meetings leaves out the internal-only events you saw in `meetingsThisWeek`; if you can't tell, label the tile "Meetings". `detail` uses only what you read (e.g. "1 won · 1 lost", "<Account> → <Stage>", "3 booked next week"); name a target only when the user gave one.
- **`changes`:** up to 6 rows, most important first: wins, losses and slips before advances. An arrow in `context` only from the history you read (step 3). On a broad ask, a deal closing next week with no meeting booked in `meetingsNextWeek` is a `warning` row.
- **`closingSoon`:** every open opportunity closing next week, largest first. Set `scored: true` and fill `score` only when the score read returned rows; otherwise omit both.
- **Tail fork:** `callout` when one move is time-sensitive before next week and the user can act on it (one button, a first-person `actionMsg`); otherwise a `nextStep` line; if nothing applies, neither. Never both (if both are sent only the callout renders).
- **Sources:** a record is `https://<myDomain>/lightning/r/Opportunity/<Id>/view`; a list is `https://<myDomain>/lightning/o/Opportunity/list`. Omit `url` if you have no Id.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only; e.g. values, never reuse their names, amounts or dates)

**Broad — "Wrap up my week."** (bulleted answer, every card and a callout; rows trimmed here):

```json
{
  "title": "Quiet week closing nothing, but $1.41M is set to close next week.",
  "answer": "- The week of Aug 18 booked **$0 in closed-won**, with nothing lost either.\n- **Northpeak advanced to Proposal** and **Vantage Retail added a second stakeholder**.\n- You held **4 customer meetings**, and 3 more are booked for next week.\n- The real story is next week: **three opportunities worth $1.41M close by Aug 30**, led by Cedarline Financial, which slipped again.",
  "metrics": [
    {"label": "Closed this week", "value": "$0", "tone": "warning", "detail": "0 won · 0 lost"},
    {"label": "Deals advanced", "value": "1", "tone": "success", "detail": "Northpeak → Proposal"},
    {"label": "Customer meetings", "value": "4", "tone": "neutral", "detail": "3 booked next week"},
    {"label": "Closing next week", "value": "$1.41M", "tone": "warning", "detail": "3 opps · by Aug 30"}
  ],
  "changes": [
    {"title": "Northpeak advanced", "context": "Value Proposition → Proposal / Price Quote · $285K · closes Sep 14", "detail": "Marcus Reyes committed to review.", "tone": "success"},
    {"title": "Cedarline slipped again", "context": "close date pushed Aug 22 → Aug 29 · $640K", "detail": "Second push this month; the CFO hasn't replied in 3 weeks.", "tone": "error"}
  ],
  "closingSoon": {
    "scored": true,
    "items": [
      {"name": "Cedarline Financial", "stage": "Negotiation / Review", "close": "Aug 29", "amount": "$640K", "score": "20"}
    ]
  },
  "callout": {
    "lead": "Cedarline ($640K) closes Aug 29 with an Einstein Opportunity Score of 20 – the CFO has been silent for 3 weeks.",
    "text": "It's the largest and lowest-scoring deal in next week's window. Re-engage CFO Priya Anand before Monday so procurement and Legal have time to clear.",
    "buttonLabel": "Draft the Cedarline re-engagement",
    "actionMsg": "Draft a re-engagement email to Priya Anand, CFO at Cedarline Financial, addressing the open pricing objection before the Aug 29 close."
  },
  "sources": [
    {"label": "Opportunities · Closed and changed this week", "url": "https://<myDomain>/lightning/o/Opportunity/list"}
  ]
}
```

**Next week — "What's closing next week?"** (a paragraph answer and the closing-soon table only; this org has no Einstein scores; rows trimmed here):

```json
{
  "title": "Three opportunities worth $1.41M close next week, led by Cedarline at $640K.",
  "answer": "**Cedarline ($640K) and Brightwave ($410K) both close Aug 29** in Negotiation / Review; Summit Health Partners ($360K) closes Aug 30 and still needs its exec readout booked.",
  "closingSoon": {
    "items": [
      {"name": "Cedarline Financial", "stage": "Negotiation / Review", "close": "Aug 29", "amount": "$640K"},
      {"name": "Brightwave Media", "stage": "Negotiation / Review", "close": "Aug 29", "amount": "$410K"}
    ]
  },
  "sources": [
    {"label": "Opportunities · Closing next week", "url": "https://<myDomain>/lightning/o/Opportunity/list"}
  ]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, answer, then the optional cards (metrics, changes, closingSoon), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A direct question ('how much did I close this week?') usually gets no tail. Format every value as a ready-to-display string (currency, dates); names are plain strings, never objects.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. The takeaway of the week in one bold sentence that already answers the question (e.g. 'Quiet week closing nothing, but $1.41M is set to close next week.'). Never the skill name or 'Weekly Wrap'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (amounts, counts, names). A broad ask gets 2-4 short '- ' bullets; a direct question ('how much did I close this week?') gets a 1-3 sentence paragraph. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "metrics": {
      "type": "array",
      "description": "OPTIONAL card 'KEY METRICS': the week's scoreboard, one tile each, in this order: closed this week, deals advanced, customer meetings, closing next week; leave out a tile you have no data for. Include for a broad wrap ('wrap up my week') or when the prompt asks how the week went ('how did I do this week?'). Omit the key otherwise; never an empty array.",
      "maxItems": 4,
      "items": {
        "type": "object",
        "required": [
          "label",
          "value"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Tile label (e.g. 'Closed this week', 'Deals advanced', 'Customer meetings', 'Closing next week'); shown upper case."
          },
          "value": {
            "type": "string",
            "description": "The big number as a display string (e.g. '$0', '1', '4', '$1.41M')."
          },
          "tone": {
            "type": "string",
            "enum": [
              "error",
              "warning",
              "success",
              "neutral"
            ],
            "description": "Colour of the value: warning (orange) = behind or at risk (e.g. nothing closed, or a large amount closing next week on at-risk deals); success (green) = progress (e.g. a deal advanced or won); error (red) = a loss; neutral (the default) = anything else."
          },
          "detail": {
            "type": "string",
            "description": "Small muted line under the value, from data you read (e.g. '1 won · 1 lost', 'Northpeak → Proposal', '3 next week', '3 opps · by Aug 30'). Name a target only when the user gave one; never invent one."
          }
        },
        "additionalProperties": false
      }
    },
    "changes": {
      "type": "array",
      "description": "OPTIONAL card 'OPPORTUNITY CHANGES': what moved this week, most important first, up to 6 rows. Include for a broad wrap or when the prompt asks what moved, slipped, advanced, won or lost ('what moved this week?'). Omit the key otherwise; never an empty array.",
      "maxItems": 6,
      "items": {
        "type": "object",
        "required": [
          "title"
        ],
        "properties": {
          "title": {
            "type": "string",
            "description": "The bold claim of the row: the account plus what happened (e.g. 'Northpeak advanced', 'Cedarline slipped again', 'Summit exec readout not booked'). Rendered bold."
          },
          "context": {
            "type": "string",
            "description": "Optional rest of the title line, rendered after ' – ' in normal weight: the change and amount (e.g. 'Value Proposition → Proposal / Price Quote · $285K · closes Sep 14'). An arrow only from the stage or close-date history you read."
          },
          "detail": {
            "type": "string",
            "description": "Small muted line below the title: evidence or consequence in one sentence (e.g. 'Marcus Reyes committed to review.')."
          },
          "tone": {
            "type": "string",
            "enum": [
              "error",
              "warning",
              "success",
              "neutral"
            ],
            "description": "Colour of the row's left rule: success (green) = won, advanced, or a stakeholder added; error (red) = lost or slipped (close date pushed out, stage moved back); warning (orange) = at risk but not yet slipped (a missing meeting or next step); neutral (grey, the default) = anything else."
          }
        },
        "additionalProperties": false
      }
    },
    "closingSoon": {
      "type": "object",
      "description": "OPTIONAL card 'OPPORTUNITIES CLOSING SOON': the open opportunities closing next week. Include for a broad wrap or when the prompt asks what closes next week ('what's closing next week?'). Omit the key otherwise.",
      "required": [
        "items"
      ],
      "properties": {
        "scored": {
          "type": "boolean",
          "description": "true only when the Einstein Opportunity Score read returned scores: adds the Opportunity Score column and its footnote. Omit otherwise."
        },
        "items": {
          "type": "array",
          "description": "One table row per open opportunity closing next week, largest amount first (never an empty array - omit closingSoon instead).",
          "items": {
            "type": "object",
            "required": [
              "name"
            ],
            "properties": {
              "name": {
                "type": "string",
                "description": "Account name (e.g. 'Cedarline Financial')."
              },
              "stage": {
                "type": "string",
                "description": "Stage display value (e.g. 'Negotiation / Review')."
              },
              "close": {
                "type": "string",
                "description": "Pre-formatted close date (e.g. 'Aug 29'). Never ISO YYYY-MM-DD."
              },
              "amount": {
                "type": "string",
                "description": "Pre-formatted amount (e.g. '$640K')."
              },
              "score": {
                "type": "string",
                "description": "Einstein Opportunity Score 0-100 as a string (e.g. '20'); '–' when that opportunity has no score. Only with scored: true."
              }
            },
            "additionalProperties": false
          }
        }
      },
      "additionalProperties": false
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something is time-sensitive before next week AND the user can act on it. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period, e.g. 'Cedarline ($640K) closes Aug 29 with an Einstein Opportunity Score of 20 – the CFO has been silent for 3 weeks.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Draft the Cedarline re-engagement')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        }
      },
      "additionalProperties": false
    },
    "nextStep": {
      "type": "object",
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button. Use INSTEAD of callout, never both.",
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
      },
      "additionalProperties": false
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: the Salesforce records/lists you actually read, linked (this is where Opportunity/Account record links go). Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). When email/Slack connectors were unavailable, add one source with no url saying so (e.g. 'Email & Slack not connected – Salesforce only'). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name: object · record (e.g. 'Opportunity · <Opportunity Name>', 'Opportunities · Closing next week', 'Events · This week and next')."
          },
          "url": {
            "type": "string",
            "description": "Record URL https://<myDomain>/lightning/r/<SObjectType>/<Id>/view, or for a list https://<myDomain>/lightning/o/Opportunity/list. Omit if none."
          }
        },
        "additionalProperties": false
      }
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, table headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "metrics": {
          "type": "string",
          "default": "KEY METRICS",
          "description": "Heading of the scoreboard card. English: 'KEY METRICS'."
        },
        "changes": {
          "type": "string",
          "default": "OPPORTUNITY CHANGES",
          "description": "Heading of the changes card. English: 'OPPORTUNITY CHANGES'."
        },
        "closingSoon": {
          "type": "string",
          "default": "OPPORTUNITIES CLOSING SOON",
          "description": "Heading of the closing-soon card. English: 'OPPORTUNITIES CLOSING SOON'."
        },
        "colOpportunity": {
          "type": "string",
          "default": "Opportunity",
          "description": "Closing-soon table header. English: 'Opportunity'."
        },
        "colStage": {
          "type": "string",
          "default": "Stage",
          "description": "Closing-soon table header. English: 'Stage'."
        },
        "colClose": {
          "type": "string",
          "default": "Close Date",
          "description": "Closing-soon table header. English: 'Close Date'."
        },
        "colAmount": {
          "type": "string",
          "default": "Amount",
          "description": "Closing-soon table header. English: 'Amount'."
        },
        "colScore": {
          "type": "string",
          "default": "Opportunity Score",
          "description": "Closing-soon table header. English: 'Opportunity Score'."
        },
        "scoreNote": {
          "type": "string",
          "default": "Einstein Opportunity Score · 0–100, higher is more likely to close",
          "description": "Footnote under the closing-soon table when scores are shown. English: 'Einstein Opportunity Score · 0–100, higher is more likely to close'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      },
      "additionalProperties": false
    }
  }
}
```

## 5. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask ("what's closing next week?", "what moved?") gets only the sections that answer it, not the whole template below. Under Moved, show from→to only from the history you read.

```
# Week of [Mon date] - [Scope]

## Closed
- ✅ **[Account]** $[X] WON
- ❌ **[Account]** $[X] lost - [reason if in SFDC]
**Net: $[won total]**

## Moved (active this week, no history = no from→to)
- **[Account]** now at [Stage] ($[X])
...

## New
- **[Account]** $[X] created at [Stage]
...

## Activity
[N] customer meetings, [N] customer email threads

## Monday
- [Time] [Meeting] - [Account if resolved]
- Closing next week: [Account] $[X], [Account] $[X]
- NextStep due: [list]
```

If "post to Slack" - format the above for Slack (bold via asterisks, bullets) and create a draft to the team channel from config. User reviews and posts.
