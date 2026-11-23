---
name: call-prep
display_name: Call Prep
description: "Build a call brief from Salesforce meeting, account, opportunity, contact, and activity data plus email, documents, and Slack. Use before a customer meeting to understand attendees, deal history, open threads, and discovery needs; rep one-on-one: rep-context."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:bcc9f4eca82c6113d8fa99bffb9311f03d426aa2d36b8420b9a0ba88075095bf"
id: "678ed34a-9b8a-44e6-9d4a-f4a2cd129040"
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

# Call Prep

Resolve meeting → ground → read account → (calendar + email + docs + slack searches, all in ONE turn with the SF read) → assemble brief. Qualification framework (BANT/MEDDIC/etc.), value prop, and competitors are external knowledge — infer from org data or ask once. Never invent.

## 1. Resolve meeting

**Inputs:** a calendar event (by time, title, or "my next call"), OR an account name + time. If neither given, list today's external meetings and ask which one.

**1a. Find the owner (if named rep)**

- **"my next call"** (default) → skip to 1b with `scope: MINE`
- **"[Rep]'s next call"** → resolve one User. Shared/demo orgs collide (one name → base user + regional variants like `(AM)`/`(BK)`). Pull enough to disambiguate:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Email { value } IsActive { value } } } } } } }\"}" })
  ```
  **One match** → take its Id. **Several** → list them (Name · Email · active? · Id) and ask user to pick. Then filter Events by `OwnerId: { eq: \"<UserId>\" }` in 1b.

**1b. Find the meeting**

Build the Event query based on input pattern. All patterns share the node shape (`Id Subject StartDateTime EndDateTime Location WhatId WhoId Description Who { ... on Contact { Id Name AccountId Account } } What { ... on Account { Id Name } ... on Opportunity { Id Name AccountId Account } }`). Combine filters with `and: [...]` when needed.

**Pattern: "my next call"** (scope: MINE, StartDateTime >= TODAY, first: 1):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { StartDateTime: { gte: { literal: TODAY } } }, first: 1, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Pattern: "[Rep]'s next call"** (OwnerId from 1a, StartDateTime >= TODAY, first: 1):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(where: { OwnerId: { eq: \\\"<UserId>\\\" }, StartDateTime: { gte: { literal: TODAY } } }, first: 1, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Pattern: specific event name** (e.g. "City of Hope call") — match Subject with LIKE, widen window to catch it (next 30 days), list if multiple:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { Subject: { like: \\\"%EVENTNAME%\\\" }, StartDateTime: { gte: { literal: TODAY }, lte: { range: { next_n_days: 30 } } } }, first: 10, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```
**One match** → use it. **Several** → list them (Subject · StartDateTime · Id) and ask user to pick. **Zero** → broaden `%EVENTNAME%` or ask user for account name directly.

**Pattern: time-based** (e.g. "call next thursday", "meeting tomorrow") — parse to date range. Use relative date filters:
- **"tomorrow"**: `StartDateTime: { gte: { range: { next_n_days: 1 } }, lte: { range: { next_n_days: 1 } } }`
- **"next thursday"**: compute day offset (if today = Monday, thursday = 3 days out) → `gte: { range: { next_n_days: 3 } }, lte: { range: { next_n_days: 3 } }`
- **"next week"**: `gte: { range: { next_n_days: 7 } }, lte: { range: { next_n_days: 14 } }`

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { StartDateTime: { gte: { range: { next_n_days: <OFFSET_START> } }, lte: { range: { next_n_days: <OFFSET_END> } } } }, first: 10, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```
**One match** → use it. **Several** → list them and ask user to pick.

**Pattern: account name directly** (e.g. "prep for City of Hope", "call with Acme") — no meeting specified. Skip Event query entirely, treat input as customer company name, jump to Step 2.

**Pattern: Event ID** (if user pastes SFDC Id `00U...`) — direct lookup:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(where: { Id: { eq: \\\"<EventId>\\\" } }, first: 1) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Extract:** title (Subject), time (StartDateTime/EndDateTime), WhatId (if `001…` → Account, `006…` → Opportunity), WhoId (Contact), description/agenda, meeting link (Location). From Description text or WhoId email domain, identify customer company.

## 2. Ground (hardcoded — Account only; fire with step 3 if independent)

Ground **only Account** — it always exists. Its field names, labels, and relationship names reveal this org's custom scalar and lookup signals; the standard relationships used below are hardcoded.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

From the result, select relevant scalar Account `__c` fields by API name and label (industry, size, qualification, etc.) and take their `{ value }`. For a relevant custom lookup, retain its exact `relationshipName` for step 3. The standard `Owner`, `Opportunities`, and `Contacts` relationships below need no metadata.

Complete this grounding call before step 3 because `<ACCOUNT_CUSTOM>` depends on its result. Then batch the independent reads as described in steps 3a–3b.

## 3. Read account (template — fill from step 2)

Insert `<ACCOUNT_CUSTOM>` = confirmed scalar `__c { value }` fields (industry, size, qualification signals, etc.); `<REL_BLOCKS>` = relevant confirmed custom lookups using their exact grounded relationship names.

- **Children:** `Opportunities(where: { IsClosed: { eq: false } }, orderBy: { LastModifiedDate: { order: DESC } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } } } }`
- **Children:** `Contacts(where: { Email: { in: [<ATTENDEE_EMAILS>] } }) { edges { node { Name { value } Title { value } Email { value } } } }`
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { <DOMAIN_FILTER> }, first: 1) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } Type { value } Description { value } <ACCOUNT_CUSTOM> <REL_BLOCKS> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { LastModifiedDate: { order: DESC } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } } } } Contacts(where: { Email: { in: [<ATTENDEE_EMAILS>] } }) { edges { node { Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```

Set `<ACTIVITY_ACCOUNT_FILTER>` from the resolved account identity:
- When Step 1 provides the account Id, use `AccountId: { eq: "<AccountId>" }`.
- For direct account-name input, use `Account: { Name: { eq: "<ACCOUNT_NAME>" } }`.
- If the account is ambiguous, resolve it before running the activity read.

Run this activity query and the Account query above as two `dispatch_readonly` calls in the **same tool turn**. They are independent once the account identity is known, so issue them in parallel. Keep Task and Event as root queries rather than nesting `ActivityHistories` under Account.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { recentTasks: Task(where: { <ACTIVITY_ACCOUNT_FILTER> }, orderBy: { ActivityDate: { order: DESC } }, first: 5) { edges { node { Id Subject { value } ActivityDate { value } Description { value } Status { value displayValue } Who { ... on Contact { Id Name { value } Title { value } Email { value } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } recentEvents: Event(where: { <ACTIVITY_ACCOUNT_FILTER> }, orderBy: { StartDateTime: { order: DESC } }, first: 5) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Description { value } Who { ... on Contact { Id Name { value } Title { value } Email { value } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Reference-field rule:** Add scalar custom fields as `Field__c { value }`. Span a relevant custom lookup only through the exact `relationshipName` from step 2: `<relationshipName> { Name { value } }`. If it has no usable relationship name, take the raw Id and move on; do not retry or invent a relationship block.

**If `<DOMAIN_FILTER>` matches more than one Account** (shared/demo orgs collide — duplicate seed data, regional subsidiaries on the same domain), don't silently take `first: 1`. Drop to `first: 10`, Account-level fields only (Name, Website, Owner — no Opportunities/Contacts probe), list the candidates, and ask the user to pick before reading further.

## 3b. Evidence (run IN PARALLEL with step 3 — same turn)

**Issue step 3 and all of step 3b as tool calls in a single turn.** They're independent (searches key on account name/attendee emails, not the SF result):
- **email**: threads with the attendee emails in last 90d → last 2–3 exchanges (date, who, what discussed/committed)
- **docs**: docs mentioning the account name → prioritize files with "transcript", "notes", or "plan" in title, most recent first. Read top 1–2 and extract: key topics, open questions, commitments made.
- **slack**: account name in last 30d → internal context (deal desk threads, exec mentions, support escalations)

Use whatever email/doc/Slack search tools are available. If none present, skip silently (SF-only is fine). Cite source + date for anything you use.

**Perf guardrail:** Do NOT fire additional SF dispatches for `Task` or `EmailMessage` — the two step 3 reads + external evidence have the data.

## 4. Attendee profiles

For each external attendee: their SFDC Contact title, plus a 1–2 line summary of what they likely care about (from title + prior interactions from evidence). Flag anyone who's new (not in SFDC Contacts, no prior email thread).

## 5. Call plan

Based on opportunity stage and the qualification framework (inferred from org data or provided by the user):

- **Objective for this call:** [what should be true after the call that isn't before — e.g. "confirm budget owner and timeline" or "get technical validation scheduled"]
- **3–5 discovery questions:** tailored to the stage and any gaps in the qualification framework. Pull from prior notes if there were unanswered questions.
- **Likely objections:** infer from prior conversations or skip.
- **What to bring:** any doc/proposal/demo that was committed in prior threads.


## 6. Dashboard widget (editorial layout)

When the `display_widget` tool is available (a widget-capable client), render the call-prep brief as a visual widget instead of the Step 7 text. When `display_widget` is unavailable (e.g. a terminal) the Step 7 markdown is the whole output, so produce it only then.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] `props` holds only keys from the schema below, as plain values — no `{!…}`, no `{{…}}`, no layout, colours or icons.
- [ ] Every optional key you included is justified by the prompt (see "Scope the blocks to the prompt"); no empty arrays, empty strings or placeholders.
- [ ] At most one tail: `callout` or `nextStep`, never both.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/call-prep", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, columns, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the Step 7 text only as the fallback when the tool is unavailable (e.g. a terminal).

### The response is lego blocks, in this fixed order

1. `title` (required) — the takeaway for this meeting in one sentence (e.g. "Your 9:00 AM Northpeak Logistics proposal review is on track — …"), never the skill name or "Call Prep: X".
2. `answer` (required) — 2–4 one-sentence `- ` bullets that answer only what was asked, **bold** on the key values (account, time, amount, dates, names).
3. `attendees` (optional **Attendees** card) — one row per person on the invite (Steps 3–4): `name`, `role` (title, plus deal role when evidence supports it), `rsvp`, `watchFor`. When sending attendees, also send `hasAttendeeRsvp` as true if any row has an RSVP, otherwise false.
4. `talkTrack` (optional **Talking Points** card) — the 3–5 things to cover or resolve on this call (Step 5 objective and questions, plus open threads from evidence): `item`, `purpose`. Write each topic as a concise, imperative-led statement that begins with an action verb (e.g., Discuss, Review, Confirm, Explore, Address). Topics may describe a subject to discuss or an outcome to achieve. Never phrase topics as questions.
5. `recentActivity` (optional **Recent Activity** card) — the recent Tasks, Events and email threads (Steps 3 and 3b), at most 5: `items` with `type`, `title`, `date`, `who`, `summary`.
6. The tail, at most one:
   - `callout` — only when something before or on this call is time-sensitive or blocked and the user can act on it;
   - otherwise `nextStep` — a plain line with the one genuinely useful prep move, no button.
7. `sources` (required) — every record and evidence source you used.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("Prep me for my meeting.", "prep me for my next call", "brief me on the Northpeak call") | `title` + `answer` + the cards that carry real signal (`attendees`, `talkTrack`, `recentActivity`) + tail only if it applies (`callout` or `nextStep`) + `sources` |
| Specific ("who's on the call?" → `attendees`; "what should I cover?" / "what should I ask?" → `talkTrack`; "what's happened so far?" → `recentActivity`) | `title` + `answer` + **only** the one matching card + tail only if it applies + `sources` |
| A question with a direct answer ("when is my Northpeak meeting?", "is Marcus coming?") | `title` + `answer` + `sources`; add a card only if it makes the answer faster to grasp |

### What to send

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholders or "N/A"; drop attendees, items or activities you have no data for. No fabricated content.
- **Scope the `answer` too:** a specific prompt gets bullets about that topic only.
- **Scope reading and output to the prompt.** Steps 1–3 still resolve the meeting and account, but a specific ask limits the Step 3b evidence searches to what its card needs ("who's on the call?" needs the attendees and their threads, not docs or Slack). Don't show something just because you fetched it.
- **Tail:** `callout` carries `level` — `tip` (helpful context), `note` (one clear move, the default) or `blocker` (time-sensitive or blocked), the lowest that fits — and at most one button (`buttonLabel` + `actionMsg`, a first-person request). Otherwise send `nextStep` (`lead` is optional). If both are sent only the callout renders, so pick one. A pure lookup ("who's on the call?") usually gets no tail.
- **Display-ready strings:** times with zone ("9:00 AM PT"), dates as "Aug 22 · Fri", amounts as "$285K". Names are plain strings (`Contact.Name.value`), never objects. Source `url`s are Lightning record URLs (`https://<myDomain>/lightning/r/<Object>/<Id>/view`); omit `url` when there is none.
- **Language:** omit `labels` for English. For any other response language, translate every `labels` value in the schema (card and datagrid headings, RSVP values, activity icon names, and `sources`) and keep `Salesforce` unchanged.
- **`attendees[].rsvp`** only when a calendar tool in this session returned the attendee's response status (`accepted`, `tentative`, `declined`, `needsAction`); never infer it from Salesforce records. When you send attendees, set `hasAttendeeRsvp` true if any row has `rsvp`, otherwise false; the false form removes the RSVP column. A deal role ("Economic Buyer", "Champion") goes in `role` only when evidence supports it.
- **`recentActivity.items[].type`:** `event` for Events, `email` for email threads from evidence, `call` only when the Task is explicitly a call, otherwise `task`.
- **Topic wording:** Write each topic as a concise, imperative-led statement that begins with an action verb (e.g., Discuss, Review, Confirm, Explore, Address). Topics may describe a subject to discuss or an outcome to achieve. Never phrase topics as questions.
- **Ranking:** attendees by influence on the decision (external first); `talkTrack` by importance (the call objective first); `recentActivity` most recent first.
- **Before calling:** no `{!…}` or `{{…}}` anywhere in `props`, and no keys outside the schema.

#### Worked examples (the `props` object only)

**Broad — "Prep me for my meeting."** (all three cards carry signal; nothing is time-sensitive, so a plain `nextStep`; trimmed):

```json
{
  "title": "Your 9:00 AM Northpeak Logistics proposal review is on track — three allies in the room and the goal is a path to a Sep 14 signature.",
  "answer": "- You are meeting **Northpeak Logistics** at **9:00 AM PT** on Zoom for a 60-minute proposal review of the **$285K Service Cloud + Dispatch Modernization** opportunity (Proposal / Price Quote, closing Sep 14).\n- The proposal landed Friday and Marcus Reyes, the economic buyer, responded positively.\n- The job today is to walk the full scope and secure his yes on the phased structure — without letting the separate Data Cloud thread derail the close.",
  "attendees": [
    { "name": "Marcus Reyes", "role": "VP Operations · Economic Buyer", "rsvp": "accepted", "watchFor": "Wants ROI framed in ops efficiency, not tech spend. His yes on structure is the goal." },
    { "name": "Neelu Sharma", "role": "Director, Data", "rsvp": "tentative", "watchFor": "Data Cloud interest is a separate thread — don't let it derail today's proposal." }
  ],
  "hasAttendeeRsvp": true,
  "talkTrack": [
    { "item": "Present the phased option, get Marcus's yes on structure", "purpose": "3-phase rollout — $95K Wave 1, $95K Wave 2, $95K Wave 3. Make the ops-timing case; it's the path he asked for." },
    { "item": "Confirm the path to the Sep 14 signature", "purpose": "Get explicit confirmation of the review and approval steps between today and signature." }
  ],
  "recentActivity": {
    "items": [
      { "type": "task", "title": "Proposal sent", "date": "Aug 22 · Fri", "who": "to Marcus Reyes", "summary": "$285K structure with 3-phase rollout, Y2/Y3 escalators at 4%. Receipt acknowledged, no substantive reply yet." },
      { "type": "call", "title": "Technical walk", "date": "Aug 15 · Fri", "who": "Ally Kim + Dana Whitfield", "summary": "Signed off on the integration approach with the existing dispatch stack. No architecture surprises." }
    ]
  },
  "nextStep": { "text": "Before the call, review the phased pricing framing with Ally Kim so she can lead it for an ops-heavy audience, and have the Data Cloud deferral answer ready in case Neelu asks to bundle it in." },
  "sources": [
    { "label": "Event: Proposal review — Northpeak Logistics (calendar)", "url": "https://<myDomain>/lightning/r/Event/<Id>/view" },
    { "label": "Opportunity: Service Cloud + Dispatch Modernization", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view" },
    { "label": "Activities: Northpeak Logistics (Aug 11–24)" }
  ]
}
```

**Specific — "Who's on my Northpeak call?"** (the attendees card only; a lookup, so no tail):

```json
{
  "title": "Four people are on your 9:00 AM Northpeak proposal review — Marcus Reyes's yes is the one that matters.",
  "answer": "- **Marcus Reyes** (VP Operations) is the economic buyer and has accepted.\n- **Dana Whitfield** is your champion; **Neelu Sharma** is still **tentative**.",
  "attendees": [
    { "name": "Marcus Reyes", "role": "VP Operations · Economic Buyer", "rsvp": "accepted", "watchFor": "Wants ROI framed in ops efficiency, not tech spend." },
    { "name": "Dana Whitfield", "role": "Director, Dispatch Systems · Champion", "rsvp": "accepted", "watchFor": "May push to expand self-service portal scope — keep that scoped as a Q4 follow-up." },
    { "name": "Neelu Sharma", "role": "Director, Data", "rsvp": "tentative" },
    { "name": "Ally Kim", "role": "Salesforce Solution Engineer", "rsvp": "accepted", "watchFor": "Owns the technical walkthrough — ask her to lead pricing framing." }
  ],
  "hasAttendeeRsvp": true,
  "sources": [{ "label": "Event: Proposal review — Northpeak Logistics (calendar)", "url": "https://<myDomain>/lightning/r/Event/<Id>/view" }]
}
```

**Specific — "What should I cover on the Northpeak call?"** (the talk-track card only, plus a useful prep move as a plain `nextStep` with no lead):

```json
{
  "title": "Lead with the phased option — Marcus's yes on structure is the path to a Sep 14 signature.",
  "answer": "- Open with the **3-phase rollout** ($95K per wave) and get **Marcus Reyes**'s yes on structure.\n- Confirm scope, decision criteria and the steps to the **Sep 14** signature.",
  "talkTrack": [
    { "item": "Present the phased option, get Marcus's yes on structure", "purpose": "Make the ops-timing case; it's the path he asked for." },
    { "item": "Confirm the path to the Sep 14 signature" }
  ],
  "nextStep": { "text": "Review the phased pricing framing with Ally Kim before the call so she can lead it. Want me to draft talking points?" },
  "sources": [{ "label": "Opportunity: Service Cloud + Dispatch Modernization", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view" }]
}
```
`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, answer, then the optional cards (attendees, talkTrack, recentActivity), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. Format every value as a ready-to-display string (dates, times, amounts); names are plain strings, never objects (use `Contact.Name.value`).",
  "required": ["title", "answer", "sources"],
  "properties": {
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed Call Prep label except the Salesforce product name. Each key's `default` is its English text; a missing or blank key falls back to it. Omit when the user writes in English; for another language, translate every label key in SKILL.md's Language rule.",
      "properties": {
        "attendees": { "type": "string", "default": "Attendees", "description": "Attendee card heading. English: 'Attendees'." },
        "attendee": { "type": "string", "default": "Attendee", "description": "Attendee name column heading. English: 'Attendee'." },
        "rsvp": { "type": "string", "default": "RSVP", "description": "Attendee RSVP column heading. English: 'RSVP'." },
        "watchFor": { "type": "string", "default": "Notes", "description": "Attendee notes column heading. English: 'Notes'." },
        "talkingPoints": { "type": "string", "default": "Talking Points", "description": "Talk-track card heading. English: 'Talking Points'." },
        "topic": { "type": "string", "default": "Topic", "description": "Talk-track item column heading. English: 'Topic'." },
        "details": { "type": "string", "default": "Details", "description": "Talk-track purpose column heading. English: 'Details'." },
        "recentActivity": { "type": "string", "default": "Recent Activity", "description": "Recent activity card heading. English: 'Recent Activity'." },
        "accepted": { "type": "string", "default": "Accepted", "description": "RSVP badge for an accepted invitation. English: 'Accepted'." },
        "tentative": { "type": "string", "default": "Tentative", "description": "RSVP badge for a tentative invitation. English: 'Tentative'." },
        "declined": { "type": "string", "default": "Declined", "description": "RSVP badge for a declined invitation. English: 'Declined'." },
        "noResponse": { "type": "string", "default": "No Response", "description": "RSVP badge when a calendar response is pending. English: 'No Response'." },
        "activityEvent": { "type": "string", "default": "Event", "description": "Accessible name for an event activity icon. English: 'Event'." },
        "activityCall": { "type": "string", "default": "Call", "description": "Accessible name for a call activity icon. English: 'Call'." },
        "activityEmail": { "type": "string", "default": "Email", "description": "Accessible name for an email activity icon. English: 'Email'." },
        "activityTask": { "type": "string", "default": "Task", "description": "Accessible name for a task activity icon. English: 'Task'." },
        "sources": { "type": "string", "default": "Sources", "description": "Word shown on the sources toggle; the renderer appends the count. English: 'Sources'." }
      }
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "description": "REQUIRED. One bold line: the takeaway for this meeting that already answers the question (e.g. 'Your 9:00 AM Northpeak Logistics proposal review is on track — three allies in the room and the goal is a path to a Sep 14 signature.'). Plain text, no markdown. Never the skill name or 'Call Prep: X'."
    },
    "answer": {
      "type": "string",
      "minLength": 1,
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence, that answer ONLY what the user asked. Put **bold** inline on the key values inside each sentence (account, time, amount, dates, names), never on a whole bullet. Do not restate the cards below it. No headings, tables or paragraphs."
    },
    "attendees": {
      "type": "array",
      "description": "OPTIONAL card 'ATTENDEES'. One row per person on the invite, external first, in order of influence on the decision. Include ONLY when the prompt is broad ('prep me for my meeting') or asks who is on the call / who to watch. At most 10 rows.",
      "maxItems": 10,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["name"],
        "properties": {
          "name": { "type": "string", "description": "Display name, plain string (e.g. 'Marcus Reyes')." },
          "role": { "type": "string", "description": "Title, plus the deal role only when evidence supports it, joined with ' · ' (e.g. 'VP Operations · Economic Buyer'). Omit if unknown." },
          "rsvp": { "type": "string", "enum": ["accepted", "tentative", "declined", "needsAction"], "description": "Invite response, only when a calendar tool in this session returned the attendee's response status. Never infer it from Salesforce records. Omit otherwise; the RSVP column shows only when at least one attendee has it. Renders as a labelled pill: accepted → ACCEPTED (green), tentative → TENTATIVE (amber), declined → DECLINED (red), needsAction → NO RESPONSE (grey)." },
          "watchFor": { "type": "string", "description": "One sentence: what this person cares about or might raise, and how to handle it (e.g. 'Wants ROI framed in ops efficiency, not tech spend.'). Omit if there is nothing specific." }
        }
      }
    },
    "hasAttendeeRsvp": {
      "type": "boolean",
      "description": "OPTIONAL derived display flag for the attendees grid. Include whenever `attendees` is included: true when at least one attendee has an `rsvp`, otherwise false. It selects the RSVP-column grid without a brittle fixed-length array expression."
    },
    "talkTrack": {
      "type": "array",
      "description": "OPTIONAL card 'TALKING POINTS'. The 3-5 things to cover or resolve on this call, most important first (the objective first, then open threads). Include ONLY when the prompt is broad or asks what to cover, ask or bring.",
      "maxItems": 5,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["item"],
        "properties": {
          "item": { "type": "string", "description": "The topic, short and bold-weight in the render. Write each topic as a concise, imperative-led statement that begins with an action verb (e.g., Discuss, Review, Confirm, Explore, Address). Topics may describe a subject to discuss or an outcome to achieve. Never phrase topics as questions. (e.g. 'Present the phased option, get Marcus's yes on structure')." },
          "purpose": { "type": "string", "description": "One or two sentences: why it matters and what to get out of it. Omit if the item says it all." }
        }
      }
    },
    "recentActivity": {
      "type": "object",
      "description": "OPTIONAL card 'RECENT ACTIVITY'. The recent touches with this account, as an icon timeline, most recent first. Include ONLY when the prompt is broad or asks what has happened so far / the history.",
      "additionalProperties": false,
      "required": ["items"],
      "properties": {
        "items": {
          "type": "array",
          "description": "Most recent first, at most 5.",
          "maxItems": 5,
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["type", "title", "date"],
            "properties": {
              "type": { "type": "string", "enum": ["task", "event", "call", "email"], "description": "Picks the icon. 'event' for Events (meetings), 'call' only when the Task is explicitly a call, 'email' for email threads from evidence, otherwise 'task'." },
              "title": { "type": "string", "description": "What happened, short (e.g. 'Proposal sent')." },
              "date": { "type": "string", "description": "Display date (e.g. 'Aug 22 · Fri')." },
              "who": { "type": "string", "description": "Who it was with or to (e.g. 'to Marcus Reyes', 'Ally Kim + Dana Whitfield'). Omit if unknown." },
              "summary": { "type": "string", "description": "One-line narrative of what was said or decided. Keep the real content; omit only if there is none." }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive: a bold first sentence followed by normal text, and at most ONE primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something before or on this call is time-sensitive or blocked AND the user can act on it. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "additionalProperties": false,
      "required": ["lead", "text"],
      "properties": {
        "level": { "type": "string", "enum": ["tip", "note", "blocker"], "description": "Emphasis, lowest that fits: 'tip' helpful context, 'note' one clear move (default), 'blocker' time-sensitive or blocked." },
        "lead": { "type": "string", "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period)." },
        "text": { "type": "string", "description": "REQUIRED, visible (non-whitespace). One to three sentences of normal-weight text that follow the bold lead: what, why now, and the move." },
        "buttonLabel": { "type": "string", "description": "Label of the single primary button (e.g. 'Draft the agenda'). Send with actionMsg, or omit both." },
        "actionMsg": { "type": "string", "description": "First-person request sent to chat when the button is clicked." }
      }
    },
    "nextStep": {
      "type": "object",
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button, only when there is a genuinely useful move before or on the call. Use INSTEAD of callout, never both.",
      "additionalProperties": false,
      "required": ["text"],
      "properties": {
        "lead": { "type": "string", "description": "Optional bold lead (the suggested move). Omit to show the text alone." },
        "text": { "type": "string", "description": "One or two sentences: the move and why, ending with an offer to help if natural." }
      }
    },
    "sources": {
      "type": "array",
      "minItems": 1,
      "description": "REQUIRED. Where the answer came from: the Salesforce records and evidence you actually read (event, account, opportunity, contacts, activities), linked where a record URL exists. Shown as a compact 'Salesforce · Sources (N)' toggle. Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["label"],
        "properties": {
          "label": { "type": "string", "description": "Source name (e.g. 'Account: Northpeak Logistics', 'Activities: Northpeak Logistics (Aug 11–24)')." },
          "url": { "type": "string", "description": "Record Lightning URL (`https://<myDomain>/lightning/r/<Object>/<Id>/view`). Omit if none." }
        }
      }
    }
  }
}
```

## 7. Output

Scope this to the prompt too: if the user asked only who's on the call, give only the headline and "Who's in the room"; if they asked only what to cover, give only the headline and "This call". Omit any section whose source wasn't available or that the prompt didn't ask for.

```
# Call Prep: [Account] - [Meeting Title]
[Date Time] | [Attendees]

## Account Snapshot
- [Industry, size, type] | Owner: [Name]
- Open opp: **[Name]** - [Stage] $[Amount] closing [Date]
  Next step (SFDC): [NextStep or "blank"]

## Who's in the room
- **[Name]**, [Title] - [1–2 line context, prior interactions]
- **[Name]**, [Title] - ⚠ NEW (no prior contact)
...

## What's happened so far
- [Date] - [Last call summary from transcript]
- [Date] - [Email thread summary]
- [Date] - [Slack/internal context if any]

## Open threads
- [Unanswered question or commitment from prior notes]
...

## This call
**Objective:** [one sentence]

**Questions to ask:**
1. [Stage-appropriate discovery Q]
...

**Likely objections:** [list]

**Bring:** [any committed deliverables]
```
