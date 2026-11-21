---
name: calendar-events
display_name: Calendar Events
description: "Show a schedule from Salesforce Event data with local times, subjects, locations, and linked contacts, accounts or deals, scoped to what was asked. Use to review today's calendar, upcoming meetings, or a past or future schedule; for a broader morning rundown, use daily-briefing."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:1ff6ff4942bdfb0f5eddfdb498d76cd1a20a2ef2a98fb9e998301217a1d626ab"
id: "d985c1e1-1872-4ef4-92e8-daaaf6f1c18a"
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

# Calendar Events

Resolve timezone → compute range (no call) → read Events → render. All dates/times in the user's **local** timezone, not UTC.

- **Scope reading and output to the prompt, never a default full agenda.** Answer what the user asked about their schedule; data you fetched but did not use stays out of the widget (see step 4).

## 1. Resolve timezone

Standard field, no grounding needed:

```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { TimeZoneSidKey { value } } } }\"}" })
```

Derive the current UTC offset from the IANA zone (e.g. `America/Los_Angeles` → `-07:00` or `-08:00`), accounting for DST at the dates in question — use the actual current date from context as the reference. Unresolvable → fall back to UTC (`+00:00`) and say so in `answer` (the only case besides hidden meetings where `answer` is sent).

## 2. Date range (prompt-only — no dispatch)

Anchor to the resolved local timezone:
- **today** → today 00:00–23:59 · **tomorrow** → tomorrow 00:00–23:59
- **this/next/last week** → Mon–Sun of that week · **this month** → 1st–last day
- **specific date** → that date 00:00–23:59 · **explicit range** → as given

Always ISO-8601 with the offset from Step 1 (e.g. `2026-08-04T00:00:00-07:00`).

## 3. Read Events

`scope: MINE` already filters to the current user — no Id lookup needed. `%START%`/`%END%` = Step 2's ISO boundaries. The filter returns every event that overlaps the range (starts before `%END%` and ends at or after `%START%`), so a multi-day event that began before the range still appears. `Who`/`What` are polymorphic unions on Event (stable, not org-specific) — span via inline fragments, never bare:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { StartDateTime: { lt: { value: \\\"%END%\\\" } }, EndDateTime: { gte: { value: \\\"%START%\\\" } } }, orderBy: { StartDateTime: { order: ASC } }, first: 100) { edges { node { Id Subject { value } StartDateTime { value displayValue } EndDateTime { value displayValue } Description { value } Location { value } IsAllDayEvent { value } WhoId { value } WhatId { value } Who { ... on Contact { Name { value } Title { value } } ... on Lead { Name { value } } } What { ... on Account { Name { value } } ... on Opportunity { Name { value } Amount { value displayValue } Account { Name { value } } } } } } } } } } \"}" })
```

Empty `edges` → say "No events found for [range]", don't retry with a broader window unasked.
Cover at most the first 100 meetings in the range: one query, `first: 100`, never paged or split to read more.

## 4. Render — widget first

Call `display_widget` immediately after assembling the event list. Do not write markdown first — only fall back to the Step 5 markdown when the tool is unavailable (e.g. a text-only client).

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/calendar-events", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the Step 5 markdown only as the fallback when the tool is unavailable (e.g. a terminal). Empty `edges` → skip the widget and say "No events found for [range]". Never fabricate events.

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated and write every free-text field (`caption`, `context`, `detail`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Everything comes from the Step 3 rows.** `Subject` → `title`; `StartDateTime`–`EndDateTime` in the Step 1 time zone → `time`, the time range (`IsAllDayEvent` → "All day"); the What Account's `Name`, or the What Opportunity's `Account.Name` → `account`; the What Opportunity's `Name` → `deal`, its `Amount.displayValue` → `amount`, and its `WhatId` → `dealUrl`; the Who `Name` (with the Contact's `Title`) → `attendees`; `Description` → `detail`; a meeting URL in `Location` or `Description` → `joinUrl`. Counts in the `title`/`answer` (meetings, deal-linked meetings) are computed from those rows, never estimated.
- **External vs internal:** a meeting is external when the Event has a Who (Contact/Lead) or a What (Account/Opportunity), and deal-linked when its What is an Opportunity. Only external meetings get a `prepMsg`; an internal meeting gets a `context` line instead of `account`/`deal`.
- **`isNext`** goes on the earliest meeting among those shown whose `StartDateTime` is after the current date-time from context — one row in the whole widget, shown expanded. Compare every meeting's start to now: when the whole range is in the future (e.g. tomorrow, next week), that is the first meeting shown; when some have already started, skip them. If every meeting shown has already started, omit it. Never put it on a meeting that has started. If the context gives only today's date and not the time of day, you cannot tell which of today's meetings have started — then put `isNext` on the earliest meeting shown that is on today's date or later (this is the one case where it may land on a meeting earlier today). Do not leave every row collapsed just because the time of day is unknown; only omit it when every meeting shown is on an earlier date than today.
- **One card for the whole query.** `caption` is its heading: the day when the range asked for is one day (e.g. `Thu, Oct 29`), or the day range when it spans several (e.g. `Oct 29 – Oct 31`). Dates only: no meeting count, no time zone, no other text. `meetings` is one flat list in start-time order, one row per Event; there are no per-day cards.
- **Each row:** `title` is the Event Subject (the row's title) and `time` is its subtitle, a ready-to-display string. When the range is one day, `time` is just the time range (e.g. `9:00 AM – 10:00 AM`). When the range spans several days, start it with the event's date (e.g. `Nov 9 · 9:00 AM – 10:00 AM`). An all-day event shows `All day` in place of the time range (with the date first when the range spans several days). The account, deal and amount (or the `context` line for an internal meeting), the attendees, the description, the deal link and the buttons all appear when the row is expanded.
- **Multi-day events** (the end date in the user's time zone is later than the start date) appear once, as a single row, never repeated on each day. Write its `time` as `Multi Day (Mon D – D)` (e.g. `Multi Day (Nov 7 – 9)`; across months `Multi Day (Oct 30 – Nov 2)`). It sorts by its start; an event that began before the range sorts first. An event that began before the range is never `isNext`.
- **Show at most 20 meetings in total**, in chronological order, even when Step 3 returned more. When Step 3 returned more than 20, send `answer` saying how many are shown out of how many (e.g. "Showing the first 20 of 100 meetings") and that the user can ask for the rest, and have the tail line (callout or `nextStep`) also point to the remaining meetings. If Step 3 returned exactly 100 (the query limit), say "at least 100".

### Scope the blocks to the prompt

The schema marks only `title` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| **Broad schedule** ("what's on my calendar today?", "show my meetings", "this week's schedule") | `title` + `caption` + `meetings` + one tail (`nextStep` or `callout`) + `sources`; add `answer` only when some meetings are not shown (see below) |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block.
- **`answer`:** omit it by default; the `title` and the agenda card are the answer. Send it only when meetings were not shown (more than 20 in the range, or the 100-meeting query limit was reached) or when the time zone fell back to UTC: 2-4 short bullets saying what is missing. Never use it to restate the agenda.
- **Tail (always exactly one):** `callout` when something is time-sensitive and the user can act on it (one button, a first-person `actionMsg`); otherwise a `nextStep` line. Always send one of the two. Never both (if both are sent only the callout renders). `callout` carries `level` — `tip` (helpful context), `note` (one clear move, the default) or `blocker` (time-sensitive or blocked), the lowest that fits.
- **Sources:** a record is `https://<myDomain>/lightning/r/<SObjectType>/<Id>/view` (Event, Opportunity). Omit `url` if you have no Id.
- Format every value as a ready-to-display string (times, amounts). Names are plain strings, never objects.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

**Broad — "What's on my calendar today?"** (one card, the next meeting expanded, a next-step line; no `answer` because every meeting is shown):

```json
{
  "title": "Seven meetings today, back-to-back from 8:30 AM – six touch open deals.",
  "caption": "Thu, Aug 20",
  "meetings": [
    {
      "time": "8:30 AM – 9:00 AM",
      "title": "Pipeline stand-up",
      "context": "Internal team sync · no deal linked"
    },
    {
      "time": "9:00 AM – 9:30 AM",
      "title": "Solution workshop – dispatch modernization",
      "account": "Northpeak Logistics",
      "deal": "Service Cloud + Dispatch",
      "dealUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view",
      "amount": "$285K",
      "attendees": "Marcus Reyes (VP Operations), Dana Whitfield (Director, Dispatch Systems), you.",
      "detail": "Walk the Service Cloud + dispatch-modernization scope and open items. Your first external meeting – prep the workshop deck before the stand-up wraps.",
      "joinUrl": "https://meet.google.com/abc-defg-hij",
      "joinLabel": "Join Google Meet",
      "prepMsg": "Prep me for my 9:00 AM Solution workshop with Northpeak Logistics.",
      "isNext": true
    },
    {
      "time": "9:30 AM – 10:00 AM",
      "title": "Contract redlines & signature walkthrough",
      "account": "Acme Retail",
      "deal": "Agentforce Service Agent Rollout",
      "dealUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view",
      "prepMsg": "Prep me for my 9:30 AM Contract redlines & signature walkthrough with Acme Retail."
    },
    {
      "time": "11:00 AM – 12:00 PM",
      "title": "Data Cloud architecture deep dive",
      "account": "Vertex Financial",
      "deal": "Data Cloud Foundation",
      "dealUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view",
      "prepMsg": "Prep me for my 11:00 AM Data Cloud architecture deep dive with Vertex Financial."
    },
    {
      "time": "1:00 PM – 2:00 PM",
      "title": "InfoSec / HIPAA review",
      "account": "Helios Health",
      "deal": "Service Cloud + Agentforce Expansion",
      "dealUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view",
      "prepMsg": "Prep me for my 1:00 PM InfoSec / HIPAA review with Helios Health."
    },
    {
      "time": "3:00 PM – 4:00 PM",
      "title": "CFO term sheet call",
      "account": "Northwind Logistics",
      "deal": "Agentforce for Field Ops",
      "dealUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view",
      "prepMsg": "Prep me for my 3:00 PM CFO term sheet call with Northwind Logistics."
    },
    {
      "time": "4:30 PM – 5:00 PM",
      "title": "Re-engagement call",
      "account": "Meridian Insurance",
      "deal": "Agentforce Claims Triage",
      "dealUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view",
      "prepMsg": "Prep me for my 4:30 PM Re-engagement call with Meridian Insurance."
    }
  ],
  "nextStep": {
    "lead": "Suggested next step:",
    "text": "your first external meeting is the 9:00 AM Northpeak Logistics workshop – the only deal-valued session this morning at $285K. Review the dispatch-modernization scope and open items before the pipeline stand-up wraps."
  },
  "sources": [
    {
      "label": "Events · Today · 7 meetings"
    },
    {
      "label": "Event · 9:00 AM · Solution workshop",
      "url": "https://<myDomain>/lightning/r/Event/<Id>/view"
    },
    {
      "label": "Opportunity · Service Cloud + Dispatch",
      "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"
    },
    {
      "label": "Event · 3:00 PM · CFO term sheet call",
      "url": "https://<myDomain>/lightning/r/Event/<Id>/view"
    }
  ]
}
```

**Broad — "What does my week look like?"** (one card for the range, the next meeting expanded, a next-step line; the range spans several days, so each `time` starts with its date; no `answer` because every meeting is shown):

```json
{
  "title": "Three meetings this week, two of them on open deals.",
  "caption": "Aug 17 – Aug 23",
  "meetings": [
    { "time": "Tue, Aug 18 · 9:30 AM – 10:00 AM", "title": "Contract redlines & signature walkthrough", "account": "Acme Retail", "deal": "Agentforce Service Agent Rollout", "dealUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view", "prepMsg": "Prep me for my Tuesday 9:30 AM Contract redlines & signature walkthrough with Acme Retail.", "isNext": true },
    { "time": "Tue, Aug 18 · 2:00 PM – 3:00 PM", "title": "Forecast review", "context": "Internal team sync · no deal linked" },
    { "time": "Thu, Aug 20 · 1:00 PM – 2:00 PM", "title": "InfoSec / HIPAA review", "account": "Helios Health", "deal": "Service Cloud + Agentforce Expansion", "dealUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view", "prepMsg": "Prep me for my Thursday 1:00 PM InfoSec / HIPAA review with Helios Health." }
  ],
  "nextStep": {
    "lead": "Suggested next step:",
    "text": "Tuesday's 9:30 AM Acme Retail redlines walkthrough is your first deal meeting – confirm the open redlines are resolved before you walk in."
  },
  "sources": [
    { "label": "Events · This week · 3 meetings" },
    { "label": "Opportunity · Agentforce Service Agent Rollout", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view" },
    { "label": "Opportunity · Service Cloud + Agentforce Expansion", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view" }
  ]
}
```

`props` schema (JSON Schema). Only `title` and `sources` are required; include any other key only when the rules above call for it (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, optional answer, the agenda card (caption + meetings), exactly one tail (callout OR nextStep), then sources. Only title and sources are required. Which optional blocks to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A'. Format every value as a ready-to-display string (times, amounts); names are plain strings, never objects.",
  "required": [
    "title",
    "sources"
  ],
  "properties": {
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed label of the widget (the attendees label, the button labels, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "attendees": {
          "type": "string",
          "default": "Attendees",
          "description": "Bold label before a meeting's attendee list. English: 'Attendees'."
        },
        "join": {
          "type": "string",
          "default": "Join meeting",
          "description": "Join button label when a meeting has no joinLabel. English: 'Join meeting'."
        },
        "prep": {
          "type": "string",
          "default": "Prep for meeting",
          "description": "Prep button label. English: 'Prep for meeting'."
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
      "description": "REQUIRED. The takeaway for the schedule in the user's context, one bold sentence that already answers the question (e.g. 'Seven meetings today, back-to-back from 8:30 AM – six touch open deals.'). Never the skill name or 'Calendar'."
    },
    "answer": {
      "type": "string",
      "description": "OPTIONAL. Omit by default: the title and the agenda cards are the answer. Send only when some meetings are not shown (more than 20 in the range, or the 100-meeting query limit reached) or the time zone fell back to UTC: 2-4 short '- ' bullets with **bold** on the key facts saying what is missing (e.g. 'Showing the first 20 of 34 meetings; ask for the rest'). Never restate the agenda rows."
    },
    "caption": {
      "type": "string",
      "description": "OPTIONAL, sent with `meetings`. The agenda card's heading: the day when the range is one day (e.g. 'Thu, Oct 29'), or the day range when it spans several (e.g. 'Oct 29 – Oct 31'). Dates only, in the user's language: no meeting count, no time zone, no other text."
    },
    "meetings": {
      "type": "array",
      "minItems": 1,
      "description": "OPTIONAL. The agenda: one collapsible row per Event in the range, in start-time order, all in the one card. Include for a broad schedule ask (see the scope table). Omit the key otherwise; never an empty array. (An event that began before the range sorts first.)",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "time",
          "title"
        ],
        "properties": {
          "time": {
            "type": "string",
            "description": "The row's subtitle, ready to display, in the user's local time zone: the time range, 12-hour (e.g. '9:00 AM – 10:00 AM'); 'All day' for an all-day event. When the range covers more than one day, start with the date (e.g. 'Nov 9 · 9:00 AM – 10:00 AM'). A multi-day event shows 'Multi Day (Nov 7 – 9)' (e.g. 'Multi Day (Oct 30 – Nov 2)' across months)."
          },
          "title": {
            "type": "string",
            "description": "The Event Subject, the row's title (e.g. 'Solution workshop – dispatch modernization')."
          },
          "context": {
            "type": "string",
            "description": "Muted line for an internal meeting (no Who and no What), shown first when the row is expanded, in place of account and deal (e.g. 'Internal team sync · no deal linked'). Omit when the meeting has an account or deal."
          },
          "account": {
            "type": "string",
            "description": "Account name: the What Account, or the What Opportunity's Account (e.g. 'Northpeak Logistics'). Shown when the row is expanded."
          },
          "deal": {
            "type": "string",
            "description": "Opportunity name when What is an Opportunity (e.g. 'Service Cloud + Dispatch'). Shown when the row is expanded."
          },
          "dealUrl": {
            "type": "string",
            "description": "The Opportunity record URL https://<myDomain>/lightning/r/Opportunity/<WhatId>/view; shown as a link when the row is expanded. Omit if no Opportunity."
          },
          "amount": {
            "type": "string",
            "description": "Pre-formatted Opportunity amount (e.g. '$285K'). Shown when the row is expanded. Omit if no Opportunity or no Amount."
          },
          "attendees": {
            "type": "string",
            "description": "Who's in the meeting, from the Who (with the Contact's Title) and any names in the Description, ending with 'you' (e.g. 'Marcus Reyes (VP Operations), Dana Whitfield (Director, Dispatch Systems), you.'). Never invent attendees."
          },
          "detail": {
            "type": "string",
            "description": "One or two sentences from the Event Description and the linked deal: what the meeting is for and what to have ready."
          },
          "joinUrl": {
            "type": "string",
            "description": "Meeting link found in the Event Location or Description (an http(s) URL). Adds the Join button. Omit if none."
          },
          "joinLabel": {
            "type": "string",
            "description": "Join button label naming the provider when the URL makes it obvious (e.g. 'Join Google Meet'). Omit to use labels.join."
          },
          "prepMsg": {
            "type": "string",
            "description": "External meetings only (the Event has a Who or a What): first-person request the Prep button sends to chat (e.g. 'Prep me for my 9:00 AM Solution workshop with Northpeak Logistics.'). Omit for internal meetings."
          },
          "isNext": {
            "type": "boolean",
            "description": "true on the earliest meeting shown whose start is after the current date-time (at most one row in the whole widget); that row is shown expanded. When the whole range is in the future, that is the first meeting. Never on a meeting that has started; omit on every other row, and on all rows if every meeting shown has started. If only today's date (not the time of day) is known, use the earliest meeting shown on today's date or later."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "additionalProperties": false,
      "description": "Tail, time-sensitive (send this or nextStep: one of the two is always sent). A bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something is time-sensitive AND the user can act on it. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
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
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button."
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
      "additionalProperties": false,
      "description": "Tail, not time-sensitive (the default tail): a plain suggestion line with NO button. Send this when there is no callout; never both.",
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
      "description": "REQUIRED. Where the answer came from: the Salesforce records you actually read, linked. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name: object · record (e.g. 'Event · 9:00 AM · Solution workshop', 'Opportunity · Service Cloud + Dispatch')."
          },
          "url": {
            "type": "string",
            "description": "Record URL https://<myDomain>/lightning/r/<SObjectType>/<Id>/view. Omit if none."
          }
        }
      }
    }
  }
}
```

### Follow-up: the rest of the meetings (text only)

This section overrides the "widget only" rule above and in the global rules, and the Step 5 heading, for this one case. When the user asks for the meetings that were not shown (e.g. "show the rest"), do NOT call `display_widget`. Reply with text only, using the events already read for that range (read them again with the single Step 3 query if they are no longer available; never page or split the range to read more than 100): the meetings after the first 20, up to the 100th, in chronological order, with a `##` heading per day (`[Day Name], [Mon DD]`) and one bullet per meeting showing only the time, the title and the account. If Step 3 returned exactly 100, end with one line saying the list stops at the first 100 meetings and there may be more in the range.


## 5. Markdown — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

One table per day, times in the resolved local timezone (label `(times in UTC)` if it fell back):

```
# Calendar - [Date Range] (times in [TZ label])

## [Day Name], [Mon DD]
| Time | Event | Location |
|------|-------|----------|
| [Start]–[End] | [Subject] | [Location] |
| All day | [Subject] | — |

**Total events:** [N]
```

Group by day (`##` heading, one table each); all-day rows show `All day`; empty location → `—`; no events → `No events found for [range].`; times `10:00 AM` / `2:30 PM` (12-hour).

## [CUSTOMIZE]

- **Time format:** 12-hour default; switch to 24-hour if preferred.
- **What/Who members:** Step 3 spans `Account`/`Opportunity` (What) and `Contact`/`Lead` (Who) — the common cases. Add another member's inline fragment (e.g. `... on Campaign`) if your org uses it on Event.
