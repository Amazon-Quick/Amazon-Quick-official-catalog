---
name: rep-context
display_name: Rep Context
description: "Where do I stand, how am I doing, my progress, my performance, prep me for my 1:1, brief me on, get me ready for my one-on-one, give me my context, or answer questions about a sales rep's own context, scoped to what was asked: where they stand this quarter, their recent activity trend, their open deals, or their quota attainment, from Salesforce opportunities, tasks and events (plus quota data when available). Use when the person named is an internal rep, not a customer contact."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:35823217e94acec89af90681ce1a3cfafbeb727fe39641fe83889bbe85c45fa4"
id: "0b8ed4f8-7abb-4f10-8476-07bb47cf043a"
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
Answer what the user asked about a rep's context (where they stand this quarter, their recent activity trend, their open deals, or how much of quota they have hit) in one pass. **Read only what the question needs** and present only that: a broad ask ("where do I stand this quarter?") reads and shows the whole picture; a specific ask ("show my recent activity trend", "just the open deals") reads and shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full briefing.** A broad ask reads and shows the whole picture; a specific ask reads and shows only that. Skip reads the question doesn't need (each read step says which), and don't show something just because you fetched it.


# Rep Context

Leader's 1:1 prep on one rep — pipeline, activity, where they're stuck. The named person is an INTERNAL rep (not a customer). Ground → read (pipeline + activity, one turn) → needs-help + questions.

## 1. Ground + resolve the rep (one turn)

When the prompt says "my" or "me", the rep is the running user: add `currentUser { Id }` beside `objectInfos` in the call below, set `<REP_ID>` to it, and skip the `User` resolver. An activity-trend ask or a quota-only question needs no Opportunity fields, so drop `objectInfos` from that call.

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's risk/health/next-step `__c` fields — use exact names. **Ground Opportunity and resolve the rep in one request** — `objectInfos` and the `User` resolver are independent `uiapi` siblings in the query below — then hold every rep-scoped read until `<REP_ID>` is resolved.

**Resolve the named rep to one active User.** If the manager supplied a Salesforce User Id, set `<REP_ID>` to it directly. Otherwise resolve a small active-User candidate set first — use the supplied name as a prefix (no leading `%`) in `<REP_PREFIX>`; for an email, swap the `Name` predicate for `Email: { eq: \"<REP_EMAIL>\" }`:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } query { User(where: { Name: { like: \\\"<REP_PREFIX>%\\\" }, IsActive: { eq: true } }, orderBy: { Name: { order: ASC } }, first: 5) { pageResultCount pageInfo { hasNextPage } edges { node { Id Name { value } Email { value } Title { value } } } } } } }\"}" })
```
Auto-select `<REP_ID>` only when exactly one candidate returns, its `Name` exactly matches the supplied full name, and `hasNextPage` is false (for an email lookup, require one exact email match and `hasNextPage: false`). If `pageResultCount` is 0 or the match is ambiguous, show the returned names/emails/titles and ask the manager to choose or supply the full name, email, or User Id — **do not read the rep's book, activity, Slack, or calendar until `<REP_ID>` is resolved.**

## 2. Read the rep's book + activity (one turn, keyed on `<REP_ID>`)

Filter every read by `OwnerId: { eq: "<REP_ID>" }`. Splice confirmed `__c` fields into `<OPP_CUSTOM>`. **Check `{` vs `}` balance before dispatching.** This is a **Top 20 sample** for named deals — the pipeline totals come from the aggregate below, not from counting these rows.

Fire the Top 20 sample and the aggregate below only when a shown block or the answer needs the open book: a broad ask, an open-deals ask, or an answer about pipeline. An activity-trend ask skips both.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { OwnerId: { eq: \\\"<REP_ID>\\\" }, IsClosed: { eq: false } }, orderBy: { Amount: { order: DESC } }, first: 20) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Id } } } } } } } } }\"}" })
```

Fire this SOQL aggregate in the same turn, same owner + `IsClosed` filter as the sample above — it is the authoritative source for `Open: <N> opps, $<total> | by stage: <counts>`:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '<REP_ID>' AND IsClosed = false GROUP BY StageName" })
```

In the SAME turn, fire the rep's recent activity — both Tasks AND Events (last 14d), plus this-quarter closed-won for the "This Q closed" number. These are independent reads keyed on the rep (not on each other), so batch all of them in this one turn — no added round-trip depth:

Fire only the reads a shown block needs. A broad ask fires all of them. An activity-trend ask fires the 14-day activity reads and the prior-14-day counts below, and skips the closed-won and attainment reads. A quota-only question fires only the attainment read (tableauReads) and skips the activity reads. An open-deals ask skips the activity reads.

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT COUNT(Id) cnt FROM Task WHERE OwnerId = '<REP_ID>' AND ActivityDate >= LAST_N_DAYS:14" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT COUNT(Id) cnt FROM Event WHERE OwnerId = '<REP_ID>' AND ActivityDate >= LAST_N_DAYS:14" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT SUM(Amount) amt, COUNT(Id) cnt FROM Opportunity WHERE OwnerId = '<REP_ID>' AND IsWon = true AND CloseDate = THIS_QUARTER" })
```

`<N> activities logged` = the Task `cnt` + Event `cnt` from the COUNT aggregates above. `InvalidSyntax` / "offending token `<EOF>`" → missing a closing `}`; add it and retry.

### Extra reads for the widget blocks (fire each only when its block is requested, in the same turn as the reads above)

**Monthly activity (`activity` block)** — six calendar months, oldest first, the last being the current month to date (today inclusive). One grouped query per type, grouped by day (SOQL rejects `CALENDAR_YEAR`/`CALENDAR_MONTH`/`FISCAL_*` on Task and Event `ActivityDate`). `ActivityDate >= LAST_N_MONTHS:5` starts on the 1st of the month five months back, so the window is six calendar months; `AND ActivityDate <= TODAY` excludes future-dated activity. Each returned row is one day (`ActivityDate`, `cnt`), so a query returns at most one row per distinct day with activity (roughly up to ~185). Bucket rows by the `YYYY-MM` of the `ActivityDate` string as returned (no timezone conversion), sum `cnt` per month, and fill any month with no rows with 0. Build `categories` oldest first and label the last (current) month as partial, e.g. `Nov (partial)`; say in the `note` that the current month is month-to-date. The 14-day and 28-day counts come from their own queries, not from these.
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT ActivityDate, COUNT(Id) cnt FROM Task WHERE OwnerId = '<REP_ID>' AND TaskSubtype = 'Call' AND ActivityDate >= LAST_N_MONTHS:5 AND ActivityDate <= TODAY GROUP BY ActivityDate" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT ActivityDate, COUNT(Id) cnt FROM Task WHERE OwnerId = '<REP_ID>' AND TaskSubtype = 'Email' AND ActivityDate >= LAST_N_MONTHS:5 AND ActivityDate <= TODAY GROUP BY ActivityDate" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT ActivityDate, COUNT(Id) cnt FROM Event WHERE OwnerId = '<REP_ID>' AND ActivityDate >= LAST_N_MONTHS:5 AND ActivityDate <= TODAY GROUP BY ActivityDate" })
```
Calls and Emails are the Task subtypes; Meetings booked are the Events.

**Prior 14 days (`trend` block)** — the cards compare the last 14 days with the 14 before them, per type. The 14-day totals above are not split by type, so fire both windows grouped by subtype:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT TaskSubtype, COUNT(Id) cnt FROM Task WHERE OwnerId = '<REP_ID>' AND TaskSubtype IN ('Call', 'Email') AND ActivityDate >= LAST_N_DAYS:14 GROUP BY TaskSubtype" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT TaskSubtype, COUNT(Id) cnt FROM Task WHERE OwnerId = '<REP_ID>' AND TaskSubtype IN ('Call', 'Email') AND ActivityDate >= LAST_N_DAYS:28 AND ActivityDate < LAST_N_DAYS:14 GROUP BY TaskSubtype" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT COUNT(Id) cnt FROM Event WHERE OwnerId = '<REP_ID>' AND ActivityDate >= LAST_N_DAYS:28 AND ActivityDate < LAST_N_DAYS:14" })
```
The Event count for the last 14 days is the Event `cnt` from the COUNT aggregate above.

**Last 4 quarters (`attainment` block)**
There is no quota source without the Tableau reads, and no quarterly closed-won history either: omit `attainment` and say in `answer` that quota attainment is not available. Do not build `attainment` from the quarter-to-date closed-won number alone.

## 2b. Evidence (same turn — skip silently if absent)

- **Slack**: rep's posts in team/deal channels last 14d — blockers, asks, exec/deal-desk flags. (Ask once which channels if unknown.)
- **calendar**: external meetings last 14d + booked next 7d, if visible.

Skip this evidence for every ask except a broad one; no card or direct answer needs it.

## 3. Analyze (cite records/threads; invent nothing)

From pipeline + activity: largest opp with risk flags (stale LastActivityDate, blank NextStep, single-threaded = ≤1 contact role); any opp a Slack post flags a blocker on; coverage gap if pipeline thin; hygiene if many stale.

Analyze only what the shown blocks and the answer need. For the activity trend, delta = round((last 14 − prior 14) ÷ prior 14 × 100), `tone` `success` when the count is up or flat and `error` when it is down. Coverage = open total ÷ quota remaining, and the quarter's percent attained = attained ÷ quota.

## 4. 1:1 questions

3–4 specific, grounded questions — not "how's pipeline" but "[Account] at [Stage] [N] days, you flagged a security review in Slack — where's that?"

The widget has no questions block. For a broad ask, fold the single most useful move into `nextStep`; a specific ask needs none. The questions are for the text fallback.

## 5. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/rep-context", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`title`, `answer`, `activity.note`, the `trend` card details, `nextStep`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("Give me my context — where do I stand this quarter?", "catch me up on <rep>") | `title` + `answer` (bullets) + `activity` + `attainment` + `openOpportunities` + `nextStep` + `sources` |
| Activity trend ("show my recent activity trend", "how has my activity been lately?") | `title` + `answer` + `trend` + `sources` — no other card |
| Open deals ("just the open deals", "what's in my pipeline?") | `title` + `answer` + `openOpportunities` + `sources` |
| A direct question ("how much of quota have I hit?") | `title` + `answer` (paragraph) + `sources` — no card, no tail |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for or that does not speed up the answer.
- **Scope the `answer` too:** for the activity trend, the answer is the headline movement across the three types, not the pipeline you did not read.
- **`activity`:** only when the prompt asks about activity over time. `categories` are the month labels, oldest first; `series` are Calls, Emails and Meetings booked, each with one number per month; the last category is the current month, labelled partial (e.g. `Nov (partial)`); `note` is a one-or-two sentence markdown caption naming the peak month and any flat line, and says the current month is month-to-date.
- **`attainment`:** `categories` are the last 4 quarters, oldest first, the current one last; `quota` and `attained` are raw numbers, one per quarter. When the prompt calls for the attainment card (a broad ask, per the table above; a direct quota question gets no card) and closed-won quarter history was read, `categories` + `attained` are required. Omit only `quota` when no trusted quota source was read (the card then shows closed-won bars alone), and omit the whole `attainment` when there is no closed-won history. When quota is present, give attainment normally. Only when quota is unavailable, say so plainly in `answer` alongside the closed-won history that is available, and never compute a quota percentage, gap or coverage ratio from it.
- **`trend`:** three cards, Calls, Emails and Meetings booked. `value` is the last-14-day count, `delta` the percent change against the prior 14 days ("+10%", "−31%"; "–" when the prior count is 0), `tone` is `success` when up or flat and `error` when down, and `detail` reads "up from 71 the prior 14 days" or "down from 16 the prior 14 days".
- **`openOpportunities`:** `rows` are the largest open deals first, from the Top 20 sample, up to 15. `amount` is a raw number, `closeDate` a short date ("Aug 31") or "–" when blank, and `stage` and `nextStep` plain text.
- **Tail fork:** `callout` when one move is time-sensitive and the user can act on it (one button, a first-person `actionMsg`, `level` of `tip`, `note` or `blocker`); otherwise a `nextStep` line; if nothing applies, neither. A broad ask usually gets the `nextStep`; a specific ask or a direct question usually gets no tail. Never both (if both are sent, only a valid callout renders: a callout missing a visible lead or text is hidden and the `nextStep` shows instead). A callout needs a visible one-sentence `lead` AND visible `text` (non-whitespace); if either is unavailable, omit the whole `callout` object (never send blank or whitespace-only `lead`/`text`, and never a button without them). Treat whitespace-only values as absent before calling `display_widget`. `buttonLabel`/`actionMsg` are only included once both are present.
- **Sources:** each label names an actual read (a record, an object/list query, or a semantic dataset), never a metric or conclusion: not `Closed won · current Salesforce quarter` or `Quota attainment · last 4 quarters`, but `Opportunity · closed-won this quarter`, `Opportunity · open pipeline`, `Task and Event · activity last 6 months`. When quota or quarterly history come from the semantic dataset, name that dataset (`Sales dataset · quota and closed-won by quarter`); a quarter-to-date Opportunity read does not source a multi-quarter chart. Omit `url` for aggregate queries; do not invent one. A record is `https://<myDomain>/lightning/r/Opportunity/<Id>/view`; the open book is `https://<myDomain>/lightning/o/Opportunity/list`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string (dates, stage labels, the percent in `delta`) except the raw numbers in `attainment` and `openOpportunities.amount`. Names are plain strings, never objects.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

**Broad — "Give me my context — where do I stand this quarter?"** (bulleted answer, the activity, attainment and open-deals blocks, a next step; the opportunity rows are trimmed here):

```json
{
  "title": "You've closed $205K this quarter with 11 deals open – the gap is late-stage execution.",
  "answer": "- You've closed **$205K this quarter** on 2 won opportunities; quota isn't available, so I can't give a percent of quota.\n- You have **$3.65M open across 11 opportunities**.\n- Activity is healthy: **187 touches in the last 14 days** (78 calls, 98 emails, 11 meetings).",
  "activity": {
    "categories": ["Apr", "May", "Jun", "Jul", "Aug", "Sep (partial)"],
    "series": [
      {"name": "Calls", "data": [120, 131, 142, 167, 149, 138]},
      {"name": "Emails", "data": [150, 158, 172, 210, 184, 176]},
      {"name": "Meetings booked", "data": [20, 18, 24, 28, 22, 19]}
    ],
    "note": "Email and call volume have held steady and climbed slightly across the half – July was your peak (210 emails, 167 calls). Meetings booked stay flat and low (18–28/mo), the same conversion gap the 14-day view shows. September is month-to-date."
  },
  "openOpportunities": {
    "rows": [
      {"name": "Platform Expansion", "account": "Cedarline Financial", "amount": 640000, "stage": "Negotiation / Review", "closeDate": "Aug 31", "nextStep": "Get redlines back from Legal; confirm signature date with Priya Anand."},
      {"name": "Ad Sales Cloud + CPQ", "account": "Brightwave Media", "amount": 410000, "stage": "Negotiation / Review", "closeDate": "Aug 31", "nextStep": "Send revised quote; lock the CMO's budget approval."},
      {"name": "Patient Engagement", "account": "Summit Health Partners", "amount": 360000, "stage": "Proposal / Price Quote", "closeDate": "Aug 30", "nextStep": "Walk the proposal with the economic buyer; set a decision date."}
    ]
  },
  "nextStep": {
    "lead": "Coaching next step: work your late-stage deals before adding more.",
    "text": "Six of your eleven opportunities sit in Proposal / Price Quote or Negotiation / Review with no close date. This week, set a realistic close date and a dated next step on each, starting with Cedarline and Brightwave."
  },
  "sources": [
    {"label": "Opportunity · open pipeline", "url": "https://<myDomain>/lightning/o/Opportunity/list"},
    {"label": "Opportunity · closed-won this quarter"},
    {"label": "Task and Event · activity last 6 months"}
  ]
}
```


**Activity trend — "Show my recent activity trend as a quick summary."** (a paragraph answer and the trend cards only):

```json
{
  "title": "Calls and emails are up on the prior 14 days, but meetings booked fell 31%.",
  "answer": "You logged **78 calls (+10%) and 98 emails (+9%)** in the last 14 days, while **meetings booked dropped from 16 to 11** – the activity is there, the conversion to meetings is not.",
  "trend": {
    "cards": [
      {"label": "Calls", "value": "78", "delta": "+10%", "tone": "success", "detail": "up from 71 the prior 14 days"},
      {"label": "Emails", "value": "98", "delta": "+9%", "tone": "success", "detail": "up from 90 the prior 14 days"},
      {"label": "Meetings booked", "value": "11", "delta": "−31%", "tone": "error", "detail": "down from 16 the prior 14 days"}
    ]
  },
  "sources": [
    {"label": "Task and Event · activity last 28 days"}
  ]
}
```

**Open deals — "Just the open deals."** (a paragraph answer and the open-deals block only; the rows are trimmed here):

```json
{
  "title": "You have 11 open deals worth $3.65M, led by Cedarline at $640K.",
  "answer": "**Two deals, Cedarline and Brightwave, hold $1.05M** and both close Aug 31; six more sit in Proposal / Price Quote or Negotiation / Review.",
  "openOpportunities": {
    "rows": [
      {"name": "Platform Expansion", "account": "Cedarline Financial", "amount": 640000, "stage": "Negotiation / Review", "closeDate": "Aug 31", "nextStep": "Get redlines back from Legal; confirm signature date with Priya Anand."},
      {"name": "Ad Sales Cloud + CPQ", "account": "Brightwave Media", "amount": 410000, "stage": "Negotiation / Review", "closeDate": "Aug 31", "nextStep": "Send revised quote; lock the CMO's budget approval."},
      {"name": "Automation Suite", "account": "Northstar Robotics", "amount": 485000, "stage": "Proposal / Price Quote", "closeDate": "–", "nextStep": "Set a close date – stuck in Proposal with no date."}
    ]
  },
  "sources": [
    {"label": "Opportunity · open pipeline", "url": "https://<myDomain>/lightning/o/Opportunity/list"}
  ]
}
```


`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (activity, attainment, trend, openOpportunities), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A direct question ('how much of quota have I hit?') usually gets no tail. Format every value as a ready-to-display string (dates, percentages, counts) except the chart numbers, openOpportunities rows[].amount, which are numbers; names are plain strings, never objects.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "additionalProperties": false,
  "properties": {
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed label of the widget (card headings, table headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "activity": {
          "type": "string",
          "default": "Recent Activity",
          "description": "Heading of the activity chart card. English: 'Recent Activity'."
        },
        "attainment": {
          "type": "string",
          "default": "Quota Attainment",
          "description": "Heading of the attainment chart card. English: 'Quota Attainment'."
        },
        "trend": {
          "type": "string",
          "default": "ACTIVITY TREND · LAST 14 DAYS VS. PRIOR 14",
          "description": "Heading of the activity trend stat cards. English: 'ACTIVITY TREND · LAST 14 DAYS VS. PRIOR 14'."
        },
        "openOpportunities": {
          "type": "string",
          "default": "Open Opportunities",
          "description": "Heading of the open opportunities table card. English: 'Open Opportunities'."
        },
        "colOpportunity": {
          "type": "string",
          "default": "Opportunity",
          "description": "Open opportunities table header. English: 'Opportunity'."
        },
        "colAccount": {
          "type": "string",
          "default": "Account",
          "description": "Open opportunities table header. English: 'Account'."
        },
        "colAmount": {
          "type": "string",
          "default": "Amount",
          "description": "Open opportunities table header. English: 'Amount'."
        },
        "colStage": {
          "type": "string",
          "default": "Stage",
          "description": "Open opportunities table header. English: 'Stage'."
        },
        "colCloseDate": {
          "type": "string",
          "default": "Close Date",
          "description": "Open opportunities table header. English: 'Close Date'."
        },
        "colNextStep": {
          "type": "string",
          "default": "Next Step",
          "description": "Open opportunities table header. English: 'Next Step'."
        },
        "last14": {
          "type": "string",
          "default": "last 14 days",
          "description": "Caption under each trend value. English: 'last 14 days'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (4)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "title": {
      "type": "string",
      "description": "REQUIRED. The takeaway in the user's context, one bold sentence that already answers the question (e.g. 'You're at 26% of quota with 11 deals open — the gap is late-stage execution, not coverage.'). Never the skill name or 'Rep Context'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (percent of quota, amounts, counts). A broad sweep gets 2-4 short '- ' bullets; a specific or direct question ('how much of quota have I hit?') gets a 1-3 sentence paragraph. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "activity": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL card 'Recent Activity': a line chart of calls, emails and meetings booked per month, with a one-paragraph caption. Include ONLY for a broad sweep ('where do I stand this quarter?'). Omit the key otherwise.",
      "required": [
        "categories",
        "series"
      ],
      "properties": {
        "categories": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Month labels in order, oldest first (e.g. ['Apr','May','Jun','Jul','Aug','Sep'])."
        },
        "series": {
          "type": "array",
          "description": "One entry per activity type, each with one number per category (same length as categories).",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "name",
              "data"
            ],
            "properties": {
              "name": {
                "type": "string",
                "enum": [
                  "Calls",
                  "Emails",
                  "Meetings booked"
                ],
                "description": "Activity type shown in the legend."
              },
              "data": {
                "type": "array",
                "items": {
                  "type": "number"
                },
                "description": "Monthly counts as numbers, aligned with categories."
              }
            }
          }
        },
        "note": {
          "type": "string",
          "description": "OPTIONAL. One short markdown caption under the chart naming the peak month and the meetings-booked pattern. Omit if there is nothing to add."
        }
      }
    },
    "attainment": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL card 'Quota Attainment': closed-won amount per quarter as columns, with quota columns when an attributable quota source was read. Include ONLY for a broad sweep. Omit the key otherwise. Closed-won quarterly history renders without quota; never compute a quota percentage or invent a target when quota is absent.",
      "required": [
        "categories",
        "attained"
      ],
      "properties": {
        "categories": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Quarter labels, oldest first (e.g. ['Q4 2025','Q1 2026','Q2 2026','Q3 2026'])."
        },
        "quota": {
          "type": "array",
          "items": {
            "type": "number"
          },
          "description": "OPTIONAL. Quota per quarter as raw numbers (e.g. 900000), aligned with categories. Include ONLY when an attributable quota source was actually read (e.g. the Tableau quota read). Omit the key entirely when no quota source exists; never send zeros, placeholders or an invented target."
        },
        "attained": {
          "type": "array",
          "items": {
            "type": "number"
          },
          "description": "Closed-won amount per quarter as raw numbers (e.g. 950000), aligned with categories."
        }
      }
    },
    "trend": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL card 'ACTIVITY TREND · LAST 14 DAYS VS. PRIOR 14': three stat cards. Include ONLY when the prompt asks for a recent activity trend or quick summary ('show my recent activity trend'). Omit the key otherwise.",
      "required": [
        "cards"
      ],
      "properties": {
        "cards": {
          "type": "array",
          "description": "One card each for Calls, Emails and Meetings booked, in that order.",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "label",
              "value",
              "delta",
              "tone",
              "detail"
            ],
            "properties": {
              "label": {
                "type": "string",
                "description": "Activity type: 'Calls', 'Emails' or 'Meetings booked'."
              },
              "value": {
                "type": "string",
                "description": "Count over the last 14 days as a display string (e.g. '78')."
              },
              "delta": {
                "type": "string",
                "description": "Change versus the prior 14 days with sign (e.g. '+10%', '−31%')."
              },
              "tone": {
                "type": "string",
                "enum": [
                  "success",
                  "error"
                ],
                "description": "'success' when the count rose, 'error' when it fell."
              },
              "detail": {
                "type": "string",
                "description": "Comparison in a few words (e.g. 'up from 71 the prior 14 days')."
              }
            }
          }
        }
      }
    },
    "openOpportunities": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL card 'Open Opportunities': a table of the rep's open opportunities. Include for a broad sweep or when the prompt asks for the open deals. Omit the key otherwise; never an empty rows array.",
      "required": [
        "rows"
      ],
      "properties": {
        "rows": {
          "type": "array",
          "description": "One row per open opportunity, in the order to show.",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "name",
              "account",
              "amount",
              "stage",
              "closeDate",
              "nextStep"
            ],
            "properties": {
              "name": {
                "type": "string",
                "description": "Opportunity name."
              },
              "account": {
                "type": "string",
                "description": "Account name."
              },
              "amount": {
                "type": "number",
                "description": "Amount as a raw number (e.g. 640000); the table formats it as currency."
              },
              "stage": {
                "type": "string",
                "description": "Stage name as shown in Salesforce."
              },
              "closeDate": {
                "type": "string",
                "description": "Close date as a display string (e.g. 'Aug 31'), or '–' when none is set."
              },
              "nextStep": {
                "type": "string",
                "description": "The next step text for the deal."
              }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. A bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if one move is time-sensitive (a close date is days away, a signal will stall the deal) AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text). buttonLabel and actionMsg are only meaningful after visible lead and text exist.",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the stake in one sentence, ending with a period, e.g. '$735K is time-sensitive across 6 days.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Send the Lumina DocuSign')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        },
        "level": {
          "type": "string",
          "enum": [
            "tip",
            "note",
            "blocker"
          ],
          "default": "note",
          "description": "OPTIONAL. Emphasis of the callout: 'tip' (quiet), 'note' (standard, the default), 'blocker' (urgent or blocked). Include only when it is not 'note'."
        }
      }
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
          "description": "Bold lead (the suggested move, e.g. 'Re-engage the CFO first.')."
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
            "description": "Name of an actual read: a Salesforce record ('Opportunity · Cedarline Financial'), a Salesforce object/list query ('Opportunity · open pipeline', 'Task and Event · activity last 6 months'), or a semantic dataset/query when that is the real source. Never a computed metric or conclusion: do NOT use labels such as 'Closed won · current Salesforce quarter' or 'Quota attainment · last 4 quarters'; label the underlying read instead (e.g. 'Opportunity · closed-won this quarter')."
          },
          "url": {
            "type": "string",
            "description": "Record URL https://<myDomain>/lightning/r/<SObjectType>/<Id>/view, or for a list https://<myDomain>/lightning/o/Opportunity/list. Omit if none (e.g. aggregate queries have no record or list URL; never invent one)."
          }
        }
      }
    }
  }
}
```


## 6. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask ("show my recent activity trend", "just the open deals") gets only the lines that answer it, not the whole template below.

```
# Rep Context: <Name>
## Pipeline
- Open: <N> opps, $<total> | by stage: <counts> | This Q closed: $<X> (<N> won)
- Top 3: **<Account>** $<X> <Stage> …
## Last 2 Weeks
- <N> activities logged; <N> external meetings (if calendar visible)
- Slack: <1–2 lines of what they raised — link threads>
## Likely Needs Help On
- **<Account>** $<X> — <specific flag + evidence>
## 1:1 Questions
1. <deal-specific, evidenced>
## Wins to Acknowledge
- <closed / advanced / notable from Slack>
```
