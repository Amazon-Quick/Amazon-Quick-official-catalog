---
name: daily-briefing
display_name: Daily Briefing
description: "What does my day look like, what should I focus on today, daily briefing, prep me for today, morning rundown, or answer what needs the rep today, scoped to what was asked: a full morning rundown, the #1 move, the next call, slipping deals, or what's closing soon, from Salesforce events, near-term and overdue deals, commitments, and unread customer email. Schedule-only requests: calendar-events."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:f826c78e2ca86eb0e1a073881962b1f56090c932859a46009ad50d0d54a561e9"
id: "5324fc41-ff5d-4467-9bba-4d3fadb71ec8"
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
Answer what the user asked about their day — today's meetings, deals closing soon or past due, and (when connected) customer email — in one pass. **Read only what the question needs** and present only that: a broad rundown ("kick off my day", "what needs me today?") reads and shows the whole day; a specific ask ("what's my #1 move?", "who's on my next call?", "which deals are slipping?") reads and shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full briefing.** A broad rundown reads and shows the whole day; a specific ask ("what's my #1 move?", "who's on my next call?") reads and shows only that. Skip reads the question doesn't need, and don't show something just because you fetched it (see step 5).
- Parallelize everything independent. This is a morning routine — speed matters; fire the running-user lookup, calendar, closing-soon, and inbox in ONE turn.
- **Anchor today's meetings to the current time.** "Now" is the current time in the rep's timezone (`TimeZoneSidKey`, 2e); `StartDateTime`/`EndDateTime` are UTC, so convert them. A meeting whose `EndDateTime` is before now has already happened: say so ("your 12:00 PM ET with Northpeak already happened") and point at its follow-up if one is owed, never at prepping for it. One under way is "on now". The next call is the first meeting whose `StartDateTime` is after now. When meetings are in the answer, state the current time ("It's 1:15 PM ET") and cover both what has passed and what is still ahead; if every meeting has ended, say the rest of the day is clear.

# Daily Briefing

Ground → (calendar + closing-soon + inbox, ALL in ONE turn) → match meetings to accounts (one batched turn) → flag → output. This is today's rundown, not a pipeline review — keep closing-soon and past-due detail rows bounded, and pair each list with a population aggregate for count and Amount totals.

## 1. Ground (hardcoded — Opportunity only; fire with the step-2 batch)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Reveals this org's stage/next-step/activity `__c` names so the closing-soon read can surface them; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. **Response can be large** on customized orgs — if it overflows or comes back truncated, scan what came back for `__c` fields whose `label` matches your keywords. Grounding is best-effort (customs are additive): if it's still unwieldy, take the standard fields and move on. Standard fields (`Amount`, `CloseDate`, `StageName`, `NextStep`, `LastActivityDate`) and `Account`/`Owner` spans are reliable across orgs.

## 2. Read — running user + calendar + closing-soon + past-due + inbox, ISSUE ALL IN ONE TURN

Five independent reads (plus step 1) — batch them in a single turn, firing only the ones the prompt needs: a broad rundown fires all five; "who's on my next call?" needs 2a + 2e only; "which deals are slipping?" / "what's closing?" need 2b + 2c + 2e and no calendar or inbox. When 2a isn't fired, skip step 3. Insert `<OPP_CUSTOM>` = confirmed `__c { value }` fields.

**2a. Today's calendar** — today's meetings for the running user. There is **no `/connect/calendar/...` REST resource on this server** — read the calendar from the `Event` object via GraphQL (below), or a dedicated calendar connector tool if one is present. Do NOT guess a REST path or reach for `discover` on a 404; the query here is the path.

**Shape gotcha — `Event.What`/`Event.Who` are polymorphic** (`Event_What` / `Event_Who` unions) and expose **no `Name` span**: `What { Name { value } }` throws a schema error. Pull the raw `WhatId` / `WhoId` scalars instead. Inline fragments on the union do work: `What { ... on Opportunity { AccountId { value } } }` returns an Opportunity link's account (an empty `What` for any other type). `WhatId` is your best account link — a `001…` Id is an Account, `006…` an Opportunity (use its `What.AccountId`) — resolve it directly in step 3 (no domain-guessing for those). Get attendee email domains from the `Description`/`Location` text, or an `EventRelation` child if you need invitees.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { ActivityDate: { eq: { literal: TODAY } } }, first: 50, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } What { ... on Opportunity { AccountId { value } } } Description { value } } } } } } }\"}" })
```

`scope: MINE` returns events **you own** (organize). Meetings where you're only an invitee live under `EventRelation` and may not appear here — an empty calendar usually means that or a genuinely clear day, not a failure; say which. Extract each event's external-attendee email domains, its `WhatId`, and (for an Opportunity `WhatId`) its `What.AccountId`; those are the input to step 3.

**Event identity:** Treat each returned Event Id as one calendar record. Do not collapse records merely because Subject, start time, or account match: reconcile the meeting KPI, section heading, and rendered entries to the distinct returned Ids. Describe same-time records as overlapping; call one a duplicate only when a returned field or connected calendar result explicitly establishes that identity. Classify a meeting as internal or external only from returned attendee or domain evidence; when no participant evidence exists, leave attendee type unknown.

**2b. Closing soon** — the rep's open opps closing in the next 14 days. A small filtered set — pull concrete rows (`first: 50`), not an aggregate.
**2b. Closing soon** — the rep's open opps closing in the next 14 days. Keep concrete rows bounded at `first: 50` and take population count/Amount from the paired aggregate in the same request.

**Date filters take a `DateInput` object, never a bare string** (`gte: \"…\"` fails `WrongType … must be an object type`). Three forms, each nested under a comparison op (`gte`/`lte`/`eq`); multiple ops on one field are AND'd automatically (no `and: [...]` wrapper):
- **relative window** (preferred here — no client-side date math): `{ range: { next_n_days: 14 } }` / `{ range: { last_n_days: 30 } }`. Keys come in `last_n_*` / `next_n_*` / `n_*_ago` families over `days|weeks|months|quarters|years` (e.g. `last_n_months: 3`, `n_days_ago: 2`).
- **relative period**: `{ literal: LAST_QUARTER }` (or `THIS_QUARTER`, `TODAY`, …).
- **exact date**: `{ value: \"YYYY-MM-DD\" }`.

**Canonical query integrity:** Treat the literal request below as the canonical template, not an outline. Substitute only `<OPP_CUSTOM>` and the documented date values; do not retype, reformat, shorten, or merge or split it. Before the first dispatch, verify that the nested `queryInput` JSON decodes, every placeholder is resolved or omitted, and `()`, `[]`, and `{}` are balanced. On a JSON or GraphQL syntax error (`InvalidSyntax` or an unexpected `<EOF>`), discard that request and rebuild it once from the literal template with `<OPP_CUSTOM>` omitted and the same date substitutions; never patch braces in place or route the request through generated code. If the rebuilt request still fails with a syntax error, report the error and stop.

So "closing in the next 14 days" = `CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 14 } } }`:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 14 } } } }, first: 50, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } } } } } aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 14 } } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value displayValue } } } } } totalCount } } } }\"}" })
```
(To widen the window, change `next_n_days`; for a named period the user gives, swap to the exact-date form `{ value: \"YYYY-MM-DD\" }` on both bounds.)

**2c. Past due** — the rep's open opps with close date in the past (still not closed); 2b starts at today, so this is the only read that finds them. Keep concrete rows bounded at `first: 50` and take population count/Amount from the paired aggregate in the same request. They have no card of their own: a past-due deal is a `needsMove` row with tone `error`, and the `answer` says so (or "nothing is past due"):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { lt: { literal: TODAY } } }, first: 50, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } } } } } aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { lt: { literal: TODAY } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value displayValue } } } } } totalCount } } } }\"}" })
```

**Amount ranking:** Before any `largest`, `second-largest`, `top`, or `highest-value` Opportunity claim, compare the raw numeric `Amount.value` for every relevant returned row keyed by Id and sort descending; never hand-pick a row, treat a missing Amount as zero, or omit a larger visible value. When a read returned its full `first: 50` rows, more may exist: say `among the N shown` or omit the ranking, and do the same when any relevant Amount is missing. Copy the selected row's returned Name and Amount unchanged.

**Population totals:** For each 2b/2c result, let `R` be returned detail edges, `C` be aggregate `Id.count.value` (or `totalCount`), and `T` be aggregate `Amount.sum`. Use `C` and `T` for every count and total shown for that list (labels, summary, closing-pipeline KPI). When `R < C`, say `showing R of C` and `T total`; qualify any detail-derived gap count as `among the R shown`. If the aggregate is absent or errors while detail rows are usable, say `R shown` and, if useful, `$S across shown rows`; never present `R`, `$S`, null, or an unavailable aggregate as a complete population total or zero.

**2d. Inbox signal** — unread email from the last 48h whose sender domain matches an account you own (email tool). Sender, subject, domain only — don't read bodies (that's `inbox-sweep`).

**Inbox check:** When an email tool is available, run this inbox read and step 3's "you owe them" search; they are part of the briefing, not optional. Report the result in the follow-ups stat (`kpiFollowupsLine`/`kpiFollowupsSub`) and the owe/inbox block (the Inbox section in the text fallback), using `inboxClear` when nothing is found. If no email tool is available or the search fails, keep that stat and block and say the inbox was not checked. Never drop them silently.

**2e. Running user** — who's the briefing for, their name, and timezone. The running-user record needs **no Id** — `currentUser` always resolves to the signed-in user. It requires **v66.0** specifically (the GraphQL endpoint otherwise pins v65.0 — bump the version in the URL for this one call):
```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id Name { value } Email { value } TimeZoneSidKey { value } } } }\"}" })
```
Use `Name` for the briefing title/date header; `TimeZoneSidKey` to render "today" and last-touch ages in the rep's zone (2b/2c's windows are resolved server-side, so no client date math); `Email` domain as a fallback when matching your own account inbox in 2d.

## 3. Meeting context — ONE batched turn (depends on 2a's domains)

Resolve every meeting's account in **one** query (not per-meeting), OR-ing two kinds of match together: (a) any `WhatId` from 2a that is an Account (`001…`) → `Id: { eq }`, or an Opportunity (`006…`) → its `What.AccountId` from 2a, same `Id` list; (b) the external-attendee domains → `Website` `like`. Prefer the direct `WhatId` link when present — it's exact; fall back to domain match only for meetings with no usable `WhatId`.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { or: [ { Id: { in: [\\\"<WhatId account 001…>\\\"] } }, { Website: { like: \\\"%domain1%\\\" } }, { Website: { like: \\\"%domain2%\\\" } } ] }, first: 25) { edges { node { Id Name { value } Website { value } LastActivityDate { value } Opportunities(where: { IsClosed: { eq: false } }, first: 5, orderBy: { Amount: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } } } } } } }\"}" })
```
In the same turn, per matched account: **docs** search (most recent transcript/notes/plan — title + one-line) and **"you owe them"** email search (sent-mail promises to those attendees — "I'll send/get you/intro" — still unfulfilled). No account match → `(no CRM match — net new or personal)`.

## 4. Flag (record only; cite; invent nothing)

Flag only the areas the prompt covers.

- **Closing soon** — flag blank `NextStep` or stale (`LastActivityDate` 7d+).
- **Inbox** — count customer-domain unreads; list the top 3 by matched-opp `Amount`.
- **Per meeting** — time · title · attendees · account · open-opp stage+$ · last touch · one-line "why it matters" · **you owe** (or "nothing outstanding") · **walk in asking** (the one thing to get, given stage + context). A meeting that has already ended (see Rules) gets its follow-up instead of a walk-in ask.

## 5. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/daily-briefing", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`detail`, `closes`, `next`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("kick off my day", "what actually needs me today?", "daily briefing", "morning rundown") | `title` + `answer` (bullets) + `needsMove` and `closingSoon` when they have rows + tail only if it applies + `sources` |
| Slipping / at risk ("which deals are slipping?", "what needs attention?") | `title` + `answer` + **only** `needsMove` + `sources` (the list) |
| Closing ("what's closing this week?", "what's in the next 14 days?") | `title` + `answer` + **only** `closingSoon` + `sources` (the list) |
| A question with a direct answer ("what's my #1 move today?", "who's on my next call?", "anything past due?") | `title` + `answer` (paragraph) + `sources` (the one record) — no card |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for or that does not speed up the answer.
- **Scope the `answer` too:** for "who's on my next call?", the answer is that meeting — not the pipeline, inbox, or other meetings you also read.
- **Meetings, past-due deals, "you owe them" promises, and inbox signal have no card of their own:** put what the prompt needs from them in `answer`, or make one the reason in a `needsMove` row's `detail` ("signing call 9:00 AM", "2 unanswered emails since Aug 8"), or say "nothing is past due".
- **`needsMove[].detail` is exactly `<Stage> · <reason for prioritization>`:** the stage, one ` · `, then the single reason the deal is on the list in a few words ("Negotiation / Review · DocuSign not sent before 9:00 AM call"). No third part, no full sentences; the rest belongs in `answer` or the callout.
- **`needsMove[].closes` is one phrase with no ` · `:** "closes today", "closes Oct 30". Only a past-due row keeps the dot format ("Oct 20 · 9d past").
- **`needsMove[].tone` comes from the opportunity fields you read, first match wins:** `error` = slipping (past its `CloseDate`, or `LastActivityDate` 7d+ ago, or `NextStep` blank); `warning` = closes within 3 days with an action still open today (unsigned paperwork, an unprepped call); `success` = on track (activity in the last 3 days and a `NextStep` set) and in the list only because one small move closes it; otherwise `neutral`. Order rows by close date, soonest first.
- **Tail fork:** `callout` when something is time-sensitive and the user can act on it (one button, a first-person `actionMsg`); otherwise a `nextStep` line; if nothing applies, neither. Never both (if both are sent only the callout renders).
- **Sources:** a record is `https://<myDomain>/lightning/r/<SObjectType>/<Id>/view` (Opportunity, Event, Account); a list ("Opportunities · Closing in 14 days") is `https://<myDomain>/lightning/o/Opportunity/list`. Omit `url` if you have no Id. When email or Slack wasn't connected, add one source with no `url`: "Email & Slack not connected – Salesforce only".
- Format every value as a ready-to-display string (currency, dates; `closingSoon.items[].close` is "Aug 30 · 6d"). Names are plain strings, never objects. `closingSoon.items[].next` is "None set" when `NextStep` is blank.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

**Broad — "Kick off my day – what actually needs me today?"** (bulleted answer, both cards, a time-sensitive callout, several sources):

```json
{
  "title": "One deal closes today; three others are slipping.",
  "answer": "- It's **8:10 AM PT** and your one meeting, the Lumina signing call, is still ahead.\n- The only sure thing on the board is **Lumina – $95K, signing call at 9:00 AM.** Send the order form before the call and it's booked.\n- Everything else this week is about keeping three At Risk deals engaged.\n- **$865K** is closing in the next 14 days and nothing is past due.",
  "needsMove": [
    { "name": "Lumina Software", "amount": "$95K", "closes": "closes today", "detail": "Negotiation / Review · DocuSign not sent before 9:00 AM call", "tone": "warning" },
    { "name": "Summit Health Partners", "amount": "$360K", "closes": "closes Aug 30", "detail": "Proposal / Price Quote · 2 unanswered emails since Aug 8", "tone": "error" },
    { "name": "Brightview Media", "amount": "$410K", "closes": "closes Aug 31", "detail": "Negotiation / Review · MSA redlines idle since Aug 12", "tone": "error" }
  ],
  "closingSoon": { "items": [
    { "name": "Lumina Software", "stage": "Negotiation / Review", "close": "Aug 24 · today", "amount": "$95K", "next": "Send DocuSign; confirm start date" },
    { "name": "Summit Health Partners", "stage": "Proposal / Price Quote", "close": "Aug 30 · 6d", "amount": "$360K", "next": "Book exec readout with Dr. Whitmore" },
    { "name": "Brightview Media", "stage": "Negotiation / Review", "close": "Aug 31 · 7d", "amount": "$410K", "next": "Chase legal on MSA redlines; schedule signing" }
  ] },
  "callout": { "lead": "Lumina closes today – signing call 9:00 AM, DocuSign not sent.", "text": "Send the order form now so it's in Jessica Tam's inbox before the call, or the close date is At Risk. Then draft the Summit exec-readout ask.", "buttonLabel": "Send the Lumina DocuSign", "actionMsg": "Send the Lumina Software DocuSign order form to Jessica Tam before the 9:00 AM signing call." },
  "sources": [
    { "label": "Opportunity · Lumina Software", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view" },
    { "label": "Event · 9:00 AM · Lumina signing call", "url": "https://<myDomain>/lightning/r/Event/<Id>/view" },
    { "label": "Opportunities · Closing in 14 days", "url": "https://<myDomain>/lightning/o/Opportunity/list" },
    { "label": "Email & Slack not connected – Salesforce only" }
  ]
}
```

**Direct — "What's my #1 move today?"** (paragraph answer, no card, no tail, one source):

```json
{
  "title": "Send the Lumina DocuSign before your 9:00 AM signing call.",
  "answer": "Lumina Software – **$95K, closes today.** The order form isn't out yet, and the signing call is your only meeting. Get it into Jessica Tam's inbox before 9:00 AM and the deal is booked. Just say the word and I'll send the Lumina DocuSign for you.",
  "sources": [{ "label": "Opportunity · Lumina Software", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view" }]
}
```

**Direct — "Who's on my next call?"** (paragraph answer about that meeting only, the event as the source):

```json
{
  "title": "Jessica Tam – Lumina signing call, 9:00–9:30 AM PT.",
  "answer": "She's the sole external attendee (**Economic Buyer**). It's the **$95K Lumina Software** signing that closes today.",
  "sources": [{ "label": "Event · 9:00 AM · Contact: Jessica Tam", "url": "https://<myDomain>/lightning/r/Event/<Id>/view" }]
}
```

**Specific — "Which deals are slipping?"** (the needsMove card only, the list as the source, no tail):

```json
{
  "title": "Three deals are slipping – $865K closing in 14 days.",
  "answer": "All three close within 14 days and each has stalled. Summit and Brightview are the biggest risk; Lumina still closes today if the DocuSign goes out.",
  "needsMove": [
    { "name": "Lumina Software", "amount": "$95K", "closes": "closes today", "detail": "Negotiation / Review · DocuSign not sent before 9:00 AM call", "tone": "warning" },
    { "name": "Summit Health Partners", "amount": "$360K", "closes": "closes Aug 30", "detail": "Proposal / Price Quote · 2 unanswered emails since Aug 8", "tone": "error" },
    { "name": "Brightview Media", "amount": "$410K", "closes": "closes Aug 31", "detail": "Negotiation / Review · MSA redlines idle since Aug 12", "tone": "error" }
  ],
  "sources": [{ "label": "Opportunities · Closing in 14 days", "url": "https://<myDomain>/lightning/o/Opportunity/list" }]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (needsMove, closingSoon), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A direct question ('who's on my next call?') usually gets no tail. Format every value as a ready-to-display string (currency, dates); names are plain strings, never objects.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, table headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "needsMove": {
          "type": "string",
          "default": "YOUR PRIORITIES FOR TODAY",
          "description": "Heading of the priorities card. English: 'YOUR PRIORITIES FOR TODAY'."
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
        "colNextStep": {
          "type": "string",
          "default": "Next Step",
          "description": "Closing-soon table header. English: 'Next Step'."
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
      "description": "REQUIRED. The takeaway for today in the user's context, one bold sentence that already answers the question (e.g. 'One deal closes today; three others are slipping.'). Never the skill name or 'Daily Briefing'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (amounts, times, names). A broad ask gets 2-4 short '- ' bullets; a direct question ('what's my #1 move?', 'who's on my next call?') gets a 1-3 sentence paragraph. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "needsMove": {
      "type": "array",
      "description": "OPTIONAL card 'YOUR PRIORITIES FOR TODAY'. Include ONLY if the prompt asks what needs attention/what is slipping/at risk/today's priorities, or the user asked for a broad rundown and there are deals needing action today. Omit the key otherwise; never an empty array. Ordered by close date, soonest first.",
      "items": {
        "type": "object",
        "required": [
          "name"
        ],
        "properties": {
          "name": {
            "type": "string",
            "description": "Account name, the row's bold title (e.g. 'Lumina Software')."
          },
          "amount": {
            "type": "string",
            "description": "Pre-formatted opportunity amount (e.g. '$95K')."
          },
          "closes": {
            "type": "string",
            "description": "When it closes, as one whole phrase in the user's language with no ' · ' inside (e.g. 'closes today', 'closes Oct 30'); shown after the amount. Only a past-due row keeps the dot format (e.g. 'Oct 20 · 9d past')."
          },
          "detail": {
            "type": "string",
            "description": "Small grey line, exactly '<Stage> · <reason for prioritization>': the stage, then the one reason this deal is on the list in a few words (e.g. 'Negotiation / Review · DocuSign not sent before 9:00 AM call'). No third part, no full sentences."
          },
          "tone": {
            "type": "string",
            "enum": [
              "error",
              "warning",
              "success",
              "neutral"
            ],
            "description": "Colour of the row's left rule, from the opportunity fields, first match wins: error (red) = slipping: past its CloseDate, LastActivityDate 7d+ ago, or NextStep blank; warning (orange) = closes within 3 days with an action still open today; success (green) = on track (activity in the last 3 days and a NextStep set); neutral (grey, the default) = anything else."
          }
        }
      }
    },
    "closingSoon": {
      "type": "object",
      "description": "OPTIONAL card 'OPPORTUNITIES CLOSING SOON'. Include ONLY if the prompt asks what is closing/this week's or this month's pipeline/closing soon, or for a broad rundown when deals close in the next 14 days. Omit the key otherwise.",
      "required": [
        "items"
      ],
      "properties": {
        "items": {
          "type": "array",
          "description": "One table row per open opportunity closing in the next 14 days, soonest first (never an empty array - omit closingSoon instead).",
          "items": {
            "type": "object",
            "required": [
              "name"
            ],
            "properties": {
              "name": {
                "type": "string",
                "description": "Account name (e.g. 'Summit Health Partners')."
              },
              "stage": {
                "type": "string",
                "description": "Stage display value (e.g. 'Negotiation / Review')."
              },
              "close": {
                "type": "string",
                "description": "Pre-formatted close date plus days left (e.g. 'Aug 24 · today', 'Aug 30 · 6d'). Never ISO YYYY-MM-DD."
              },
              "amount": {
                "type": "string",
                "description": "Pre-formatted amount (e.g. '$360K')."
              },
              "next": {
                "type": "string",
                "description": "The next step to take (e.g. 'Book exec readout with Dr. Whitmore'). Use 'None set' when NextStep is blank."
              }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something is time-sensitive today AND the user can act on it. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period, e.g. 'Lumina closes today – DocuSign not sent.')."
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
      "description": "REQUIRED. Where the answer came from: the Salesforce records/lists you actually read, linked (this is where Opportunity/Account record links go). Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). When email/Slack connectors were unavailable, add one source with no url saying so (e.g. 'Email & Slack not connected – Salesforce only'). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name: object · record (e.g. 'Opportunity · Lumina Software', 'Event · 9:00 AM · Contact: Jessica Tam', 'Opportunities · Closing in 14 days')."
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


## 6. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: lead with the one-line answer, then only the sections the question covers (e.g. "who's on my next call?" gets that one meeting; "which deals are slipping?" gets only the at-risk closing-soon rows). The template below is the broad rundown.

```
# Daily Briefing — [Date]

## Today's Meetings ([N]) — as of [current time]
[Time] **[Title]** — [Attendees][ · done, if it has ended]
  Account: [Name] · Opp: [Stage] $[Amount] closes [Date] · Last touch: [N]d ago[ · context from doc]
  You owe: [unfulfilled promise, or "nothing outstanding"]
  → Walk in asking: [the one thing]
…

## Opportunities Closing Soon
- **[Account]** — [Stage] $[Amount] closes [Date] · Next: [NextStep or "⚠ BLANK"] · Last activity: [N]d[ "⚠ 7+d stale"]
…

## Inbox ([N] unread from customers)
- [Sender] @ [Account] — "[Subject]" (opp $[Amount])
…  Run `inbox-sweep` to triage and draft replies.
```
