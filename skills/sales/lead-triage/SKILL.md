---
name: lead-triage
display_name: Lead Triage
description: "Which leads are worth my time, who should I focus on, prioritize my leads, or answer questions about open leads and prospects, from Salesforce Lead, Account and activity data, research and email engagement, scoped to what was asked: a ranked worklist, who needs a reply today, one lead's priority and owner, or the best next action. Use when qualifying new leads, assessing ICP fit and intent, choosing an owner or deciding the response speed and next step."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:0c05aa49cb0c45012c98a7fc32cc95575433746fcb1ebe0ed018e56572069808"
id: "773aabea-c936-44ca-84f8-0c80161e8e5d"
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

- **Scope reading and output to the prompt, never a default full triage.** A broad ask ("who should I focus on next?") reads the open queue and shows the ranked worklist; a specific ask ("which leads need a reply today?") shows only the matching rows; a direct question ("who owns Acme?") reads and shows only what it needs. Don't fetch unrelated areas, and don't show something just because you fetched it.

# Lead Triage

Ground → read Lead + Account → enrich → score → route. **No per-lead follow-ups** — the reads have the data.

## 1. Ground (hardcoded — Lead and Account)

A direct-answer ask about only one side ("is Acme already an account?") grounds and reads just that object; skip the other's grounding and read.

Ground **Lead** and **Account** (for ICP fields). Both always exist. Issue these independent requests in the **same tool turn** so they run in **parallel**:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Lead\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

**If either overflows** or comes back truncated, skip custom-field grounding and proceed with standard fields only; don't keep retrying.

From each response, select relevant `__c` fields by API name and label (segment, industry, employee count, lead score, MQL status, etc.) and take their `{ value }`. The `Owner` spans below are standard and hardcoded.

## 2. Read lead + matching account (templated, one turn)

Fire these as tool calls in **one turn** (independent). Insert `<LEAD_CUSTOM>` = confirmed scalar `__c` fields on Lead, `<ACCOUNT_CUSTOM>` = confirmed scalar `__c` fields on Account.

**Lead (by identifier user provided — Id, email, or name+company):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Lead(where: { <LEAD_FILTER> }, first: 1) { edges { node { Id Name { value } Company { value } Title { value } Email { value } LeadSource { value } Status { value } CreatedDate { value } <LEAD_CUSTOM> Owner { ... on User { Name { value } } ... on Group { Name { value } } } } } } } } }\"}" })
```

**Account (by company name or domain):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { or: [{ Name: { like: \\\"%<COMPANY>%\\\" } }, { Website: { like: \\\"%<DOMAIN>%\\\" } }] }, first: 5) { edges { node { Id Name { value } Type { value } <ACCOUNT_CUSTOM> Owner { Name { value } } } } } } } }\"}" })
```

`<LEAD_FILTER>` = build from user input: `Id: { eq: "<id>" }` OR `Email: { eq: "<email>" }` OR `and: [{ Name: { like: "%<name>%" } }, { Company: { like: "%<company>%" } }]`

If Account exists with Owner → existing relationship, routing = coordinate with that owner.

**Web research (parallel with SF reads):** Use web search/fetch if available to find company size, industry, funding, recent news. Fire in SAME turn as SF reads. If tools absent, skip silently.

**Email search (parallel):** Use email search if available to find prior threads from this domain. Fire in SAME turn. If tool absent, skip silently.

Web research and email search are raw material for ranking: a narrow ask that doesn't rank leads ("who owns Acme?", "is Acme already an account?") skips both. Never fabricate what they would have returned.

## 2b. Read the open queue (broad asks only)

For a broad ask ("who should I focus on next?", "which leads should I work first?", "triage my queue"), read the user's whole open queue instead of one lead. A narrow ask about one named lead skips this step and uses step 2 as is. Insert the confirmed scalar `__c` fields from step 1 as `<LEAD_CUSTOM>` and `<ACCOUNT_CUSTOM>`; omit a token when grounding surfaced none. Fire these three in **one turn**, in parallel with the web and email enrichment:

**Open leads (mine, not converted):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Lead(scope: MINE, where: { IsConverted: { eq: false } }, orderBy: { LastActivityDate: { order: DESC } }, first: 50) { edges { node { Id Name { value } Title { value } Company { value } Industry { value } NumberOfEmployees { value } LeadSource { value } Status { value } CreatedDate { value } LastActivityDate { value } <LEAD_CUSTOM> } } totalCount } } } }\"}" })
```

**Prospect accounts (mine) and their most recent contacts:**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(scope: MINE, where: { Type: { eq: \\\"Prospect\\\" } }, orderBy: { LastActivityDate: { order: DESC } }, first: 50) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } LastActivityDate { value } <ACCOUNT_CUSTOM> Contacts(first: 3, orderBy: { LastActivityDate: { order: DESC } }) { edges { node { Id Name { value } Title { value } LastActivityDate { value } } } } } } totalCount } } } }\"}" })
```

**Recent activity and open commitments (last 90 days):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Task(scope: MINE, where: { ActivityDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { ActivityDate: { order: DESC } }, first: 100) { edges { node { Id Subject { value } ActivityDate { value } Status { value } IsClosed { value } TaskSubtype { value } Description { value } WhoId { value } WhatId { value } } } } } } }\"}" })
```

- The queue size is the `totalCount` of the leads plus the prospect accounts; say "top N of M" only with counts you read. If a read is truncated at 50, say so rather than guessing the total.
- The last meaningful interaction of a lead is its most recent Task, Event or email you can tie to it (by `WhoId`/`WhatId`, or by the email thread); fall back to `LastActivityDate` with no detail. With none of those (null `LastActivityDate`, no Task, Event or email), `last` is exactly "No last activity found" and `lastDetail` is omitted: never write "blank" or "Last Activity is blank", and never use Created date or Status as `lastDetail`. An open Task (`IsClosed` false) past its `ActivityDate` is an overdue commitment.
- "Since your last review" has no stored date: use the date the user gives, else the last 7 days, and name the window. Never invent a review date.
- If a read errors (object or field absent in this org), drop it, rank from what you have, and say what was missing. Do not retry.

## 3. Score ICP fit

Against ICP (ask user once if not inferrable from org data):

| Dimension | Fit | Evidence |
|---|---|---|
| Industry | ✅ / ⚠️ / ❌ | [from Account/web] |
| Size | ✅ / ⚠️ / ❌ | [from Account custom/web] |
| Persona (title) | ✅ / ⚠️ / ❌ | [from Lead.Title] |
| Disqualifiers | ✅ none / ❌ [which] | [check against ICP] |

## 4. Score intent

| Signal | Strength |
|---|---|
| Source quality | High (demo request, referral) / Med (content, event) / Low (list, cold) |
| Message specificity | Specific use case / Generic interest / None |
| Prior engagement | Email thread / SFDC history / None |
| Timing trigger | Recent funding, hiring, exec change / None |

## 5. Assign priority

Calibration: P0 ≈ top 20%, P1 ≈ next 25%, P2 ≈ remaining.

- **P0:** Strong ICP fit AND high intent (specific ask, demo request, or hot trigger)
- **P1:** Strong fit with medium intent, OR moderate fit with high intent
- **P2:** Moderate fit with low intent, or fit unclear
- **DQ:** Hard disqualifier hit

Override: if Account exists with owner → routing = "coordinate with [owner]"

### Assign a priority to each lead for the worklist

Rank the open queue on fit, intent, engagement and open commitments (not a lead score alone), then give each lead exactly one priority. Use these definitions:

- **Urgent:** a time-sensitive signal the user can answer today: an inbound request or reply awaiting a response, a booked meeting that needs prep, an overdue follow-up on an engaged lead, or fresh strong-intent activity (repeat opens, a content click) with no reply yet.
- **High:** strong fit plus a fresh trigger or engagement, but not in a cadence yet and nothing time-critical.
- **Medium:** previously active (a cadence, a meeting) and now stalled: the last reply is old (over about 30 days) or the follow-up date has passed, while fit is still good.
- **Low:** moderate or unclear fit with low intent, missing key data, or an explicit request to hold.
- **DQ:** a hard ICP disqualifier. Leave it out of the worklist and mention the count in the answer.

Order the worklist Urgent, High, Medium, Low; within a priority level by urgency, then fit. Show the top 10 unless the user asks for more or fewer. Where a judgment rests on an inference or a data gap (for example intent inferred from attendance, a blank title), say so in that row's `why` and mention it in the `answer`; never present an inference as a fact.


## 6. Render

Call `display_widget` now with the data you collected. Do not write markdown first — call immediately. Only fall back to markdown if the tool is unavailable.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/lead-triage", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 7 text only as the fallback when the tool is unavailable (e.g. a terminal). Never fabricate leads or fields.

### The response is lego blocks, in this fixed order

`title` → `answer` → optional `worklist` card → at most one tail (`callout` or `nextStep`) → `sources`.

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`title`, `answer`, `why`, `action`, `nextStep`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Everything comes from the reads and the priority assignment.** `Name` → `name`; `Title` and `Company` → `detail` ("Title unknown" when blank, "(Prospect)" after the company of a Prospect account); the signal that set its priority → `why`; the most recent interaction → `last` and `lastDetail` (a real quote only if you read it); the move → `action`; the priority → `_status` and `_tone` (Urgent `error`, High `warning`, Medium `info`, Low `default`). The worklist card title is the label `labels.worklistHeading` ("PROSPECTS" in English, omitted with the rest of `labels`): never add counts or "TOP N OF M" to it. Counts in the `title` and `answer` are computed from the rows you read, never estimated.
- **The `answer` bullets match the card:** the queue size and how many you surfaced, what changed since the window you used, and the priority counts. Where a judgment rests on an inference or a data gap, say so (it is also stated in that row's `why`).

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("who should I focus on next?", "which leads should I work first?", "triage my queue") | `title` + `answer` + `worklist` (top 10, all four priority levels that apply) + tail only if it applies + `sources` |
| Specific ("which leads need a reply today?", "who has gone quiet?") | `title` + `answer` + `worklist` with **only** the rows that match (one priority level) + tail only if it applies + `sources` |
| One named lead ("triage Alex Mercer", "is Acme a good lead?") | `title` + `answer` + `worklist` with that one row + tail only if it applies + `sources` |
| A question with a direct answer ("is Acme already an account?", "who owns Acme?") | `title` + `answer` + `sources`; add a card only if it makes the answer faster to grasp |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block.
- **Tail fork:** `callout` when something is time-sensitive and the user can act on it (one button, a first-person `actionMsg`); otherwise a `nextStep` line when there is a genuinely useful move; if nothing applies, neither. Never both (if both are sent only the callout renders).- **Sources:** a record is `https://<myDomain>/lightning/r/<SObjectType>/<Id>/view` (Lead, Account); a list is `https://<myDomain>/lightning/o/<SObjectType>/list`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string (dates as "Oct 18"). Names are plain strings, never objects (use `Owner.Name.value`).
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

**Broad — "Who should I focus on next across all my leads and prospects?"** (bulleted answer, the worklist, a next-step line; four rows shown here, up to ten in practice):

```json
{
  "title": "Of your 47 open prospects, 10 are worth your time this week – and 3 need a reply today, led by a pricing request from Northpeak that's already a day overdue.",
  "answer": "- You have **47 open prospects** in your territory. I assigned each a priority based on urgency, fit, intent, and relationship – and surfaced the **top 10** for this week. The rest can wait.\n- **Since your last review (Oct 13):** 2 prospects replied with buying intent (Northpeak, Cascade), 1 booked a meeting (Harborview), and 2 went quiet past your follow-up date (Meridian, Lumina).\n- They fall into four priority levels: **Urgent (3)**, **High (3)**, **Medium (2)**, and **Low (2)**.",
  "worklist": {
    "items": [
      {
        "name": "Elena Ruiz",
        "detail": "Director, RevOps · Northpeak Logistics",
        "why": "Replied Oct 18 asking for pricing on the Logistics Cloud bundle – your follow-up was due Oct 19. **1 day overdue.**",
        "last": "Oct 18 · inbound email",
        "lastDetail": "\"Can you send pricing for 150 seats?\"",
        "action": "Send the pricing one-pager today; propose two times to walk it through.",
        "_tone": "error",
        "_status": "URGENT"
      },
      {
        "name": "Robert Lang",
        "detail": "VP Patient Experience · Summit Health Partners",
        "why": "Strong fit; attended your Oct 8 webinar and stayed for Q&A. Not yet in a cadence. Intent is inferred from attendance – no direct reply yet.",
        "last": "Oct 8 · webinar attendee",
        "action": "Reference a question he raised in the webinar; offer a tailored follow-up.",
        "_tone": "warning",
        "_status": "HIGH"
      },
      {
        "name": "James Okafor",
        "detail": "VP Finance · Meridian Insurance",
        "why": "Was in an active cadence; stalled after 3 touches. Last reply was **42 days ago** and your follow-up date has passed.",
        "last": "Sep 8 · last reply",
        "lastDetail": "\"Circle back next quarter\"",
        "action": "Send a low-pressure break-up or value-add; it's now \"next quarter\".",
        "_tone": "info",
        "_status": "MEDIUM"
      },
      {
        "name": "Alex Mercer",
        "detail": "Title unknown · Acme (Prospect)",
        "why": "Decent company fit, but no confirmed title, source, or intent yet – below your Warm threshold.",
        "last": "No last activity found",
        "action": "Leave in nurture.",
        "_tone": "default",
        "_status": "LOW"
      }
    ]
  },
  "nextStep": {
    "lead": "Work the three Urgent leads first – they're the fastest path to a qualified conversation.",
    "text": "All three have shown real intent this week, so a timely, specific reply moves each forward today. I'll hold outreach and record changes until you approve them. Want me to draft all three Urgent messages so you can review and send in one pass?"
  },
  "sources": [
    { "label": "Leads – open in your territory", "url": "https://<myDomain>/lightning/o/Lead/list" },
    { "label": "Accounts – Prospects", "url": "https://<myDomain>/lightning/o/Account/list" },
    { "label": "Activity – last 90 days" }
  ]
}
```

**Specific — "Which leads need a reply today?"** (only the Urgent rows, no other priority levels):

```json
{
  "title": "Three leads need a reply today – Northpeak's pricing request is already a day overdue.",
  "answer": "- **Elena Ruiz (Northpeak)** asked for pricing on **Oct 18**; your follow-up was due **Oct 19**.\n- **Thomas Byrne (Harborview)** has a discovery call on **Oct 22** and wants an agenda first.\n- **Marcus Cortez (Cascade Energy)** clicked the Data Cloud case study on **Oct 19** and hasn't heard back.",
  "worklist": {
    "items": [
      {
        "name": "Elena Ruiz",
        "detail": "Director, RevOps · Northpeak Logistics",
        "why": "Replied Oct 18 asking for pricing – your follow-up was due Oct 19. **1 day overdue.**",
        "last": "Oct 18 · inbound email",
        "lastDetail": "\"Can you send pricing for 150 seats?\"",
        "action": "Send the pricing one-pager today; propose two times to walk it through.",
        "_tone": "error",
        "_status": "URGENT"
      },
      {
        "name": "Thomas Byrne",
        "detail": "CFO · Harborview",
        "why": "Booked a discovery call for **Oct 22** and asked for an agenda beforehand.",
        "last": "Oct 17 · meeting booked",
        "action": "Send a short agenda and one CFO-relevant proof point before the call.",
        "_tone": "error",
        "_status": "URGENT"
      },
      {
        "name": "Marcus Cortez",
        "detail": "VP Data & Analytics · Cascade Energy",
        "why": "Opened your last email 4× and clicked the Data Cloud case study Oct 19 – no reply yet.",
        "last": "Sep 30 · your outbound",
        "action": "Send a short, specific follow-up referencing the case study he clicked.",
        "_tone": "error",
        "_status": "URGENT"
      }
    ]
  },
  "nextStep": {
    "text": "Start with Elena Ruiz since hers is already overdue. Want me to draft all three replies?"
  },
  "sources": [
    { "label": "Leads – open in your territory", "url": "https://<myDomain>/lightning/o/Lead/list" },
    { "label": "Activity – last 90 days" }
  ]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, answer, then the optional worklist card, then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional blocks to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A pure lookup question usually gets no tail. Format every value as a ready-to-display string (dates, counts); names are plain strings, never objects (use `Owner.Name.value`).",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line: the takeaway in the user's context that already answers the question (e.g. 'Of your 47 open prospects, 10 are worth your time this week – and 3 need a reply today.'). Plain text, no markdown. Never the skill name or 'Lead Triage: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence, that answer ONLY what the user asked. Put **bold** inline on the key values inside each sentence (counts, names, priority names), never on a whole bullet. Do not restate the worklist row by row. Answer ONLY what was asked (scope the bullets to the prompt); no headings, tables or paragraphs."
    },
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed label of the widget (column headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "worklistHeading": {
          "type": "string",
          "default": "PROSPECTS",
          "description": "Title of the worklist card. English: 'PROSPECTS'. Never add counts, 'LEADS &' or 'TOP N OF M'."
        },
        "colStatus": {
          "type": "string",
          "default": "PRIORITY",
          "description": "Column header of the priority pill in the worklist. English: 'PRIORITY'."
        },
        "colProspect": {
          "type": "string",
          "default": "PROSPECT",
          "description": "Column header of the person and company. English: 'PROSPECT'."
        },
        "colWhyNow": {
          "type": "string",
          "default": "WHY THIS PRIORITY",
          "description": "Column header of the reason for this lead's priority. English: 'WHY THIS PRIORITY'."
        },
        "colLastInteraction": {
          "type": "string",
          "default": "LAST ACTIVITY",
          "description": "Column header of the last interaction. English: 'LAST ACTIVITY'."
        },
        "colNextAction": {
          "type": "string",
          "default": "SUGGESTED ACTION",
          "description": "Column header of the recommended action. English: 'SUGGESTED ACTION'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (4)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "worklist": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL card with the ranked worklist: one row per lead or prospect to act on, most urgent first. Include for any prompt that ranks, triages or asks who to focus on, contact or reply to (one lead or many). Omit the key otherwise (e.g. a pure 'what is Acme's industry?' lookup); never an empty items array.",
      "required": [
        "items"
      ],
      "properties": {
        "items": {
          "type": "array",
          "description": "One row per lead or prospect, ordered by urgency then fit. Group order: Urgent, High, Medium, Low. Never an empty array - omit worklist instead.",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "name",
              "why",
              "action",
              "_tone",
              "_status"
            ],
            "properties": {
              "name": {
                "type": "string",
                "description": "Lead or contact name, rendered bold."
              },
              "detail": {
                "type": "string",
                "description": "Muted line under the name: 'Title · Company' (e.g. 'Director, RevOps · Northpeak Logistics'). Use 'Title unknown' when the title is blank; add '(Prospect)' after the company when the Account is a Prospect. Omit parts you do not know."
              },
              "why": {
                "type": "string",
                "description": "Why this lead matters now: one or two short clauses, **bold** allowed on the key fact (e.g. 'Replied Oct 18 asking for pricing – your follow-up was due Oct 19. **1 day overdue.**')."
              },
              "last": {
                "type": "string",
                "description": "The last meaningful interaction as 'Date · type' (e.g. 'Oct 18 · inbound email', 'Sep 8 · last reply'). When there is no Task, Event, email or LastActivityDate to tie to the lead, send exactly 'No last activity found'. Never write 'blank', 'null' or 'Last Activity is blank'."
              },
              "lastDetail": {
                "type": "string",
                "description": "Line under `last`: a real quote or one-line landing (e.g. 'Can you send pricing for 150 seats?', 'Net-new relationship'). Omit if you have nothing real to quote. Never fill it with record metadata such as Created date or Lead Status, and always omit it when `last` is 'No last activity found'."
              },
              "action": {
                "type": "string",
                "description": "The one recommended next action for this lead, one short sentence (e.g. 'Send the pricing one-pager today; propose two times to walk it through.')."
              },
              "_tone": {
                "type": "string",
                "enum": [
                  "error",
                  "warning",
                  "info",
                  "default"
                ],
                "description": "Colour of the status pill and rail: 'error' for Urgent, 'warning' for High, 'info' for Medium, 'default' (grey) for Low."
              },
              "_status": {
                "type": "string",
                "description": "The priority word shown in the pill, upper case, in the user's language (English: 'URGENT', 'HIGH', 'MEDIUM', 'LOW')."
              }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL tail, time-sensitive. A bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something is time-sensitive (an overdue reply, a meeting tomorrow) AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the stake in one sentence, ending with a period)."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Draft the three Urgent messages')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button, only when there is a genuinely useful next move (e.g. work the Urgent rows first, then offer to draft the messages). Use INSTEAD of callout, never both.",
      "required": [
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead (the suggested move, e.g. 'Work the three Urgent leads first.'). Optional."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning, ending with an offer to help if natural (e.g. 'Want me to draft the three Urgent messages so you can review and send in one pass?')."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: the Salesforce records and lists you actually read (Leads, Accounts, activity), linked where you have an Id. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Leads – open in your territory', 'Account – Acme')."
          },
          "url": {
            "type": "string",
            "description": "Record or list-view URL. Omit if you have no Id."
          }
        }
      }
    }
  }
}
```





## 7. Output

Text fallback, only when `display_widget` is unavailable. Scope it to the prompt like the widget: a broad ask gets the worklist table below, a narrow ask only the matching rows, and a direct question a sentence. Omit any section the prompt didn't call for.

```
# Lead Triage: [N] to act on

**[One-sentence answer]**

| Priority | Lead | Why this priority | Last activity | Suggested action |
|---|---|---|---|---|
| [Urgent / High / Medium / Low] | [Name — Title, Company] | [reason] | [date · type — quote] | [action] |

## Suggested SFDC updates
[Apply with write skills, or manually if read-only.]
- Lead Status → [value]
- Lead Owner → [name]
- [Notes field] → "[triage summary]"
```

If routing to teammate, offer to draft Slack message to lead-handoff channel (ask user for channel if not known).
