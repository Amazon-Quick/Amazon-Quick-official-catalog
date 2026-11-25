---
name: query-activity-history
display_name: Query Activity History (Preview)
description: "Build an interaction timeline from closed Salesforce Tasks and Events on one Account, Contact, Lead or Opportunity, with dates, people and notes, scoped to what was asked: the cadence and gaps, the individual activities, or just the last touch. Use when inspecting what happened on a record or reviewing its activity. To create an entry, use log-activity."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:ba09e912695bac4b87b47d3460b4e9c6625a98dda22c3d45eb05743a696f4334"
id: "47862f45-e018-4a89-a570-e750cd0fc117"
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
# Goal:
Pull and summarize the `ActivityHistory` for ONE `Account`, `Contact`, `Lead`, or `Opportunity` — the timeline of closed Tasks and Events on that record.

# Audience:
Sales-org workers who want results fast. Minimize thinking when it's not needed; get them the timeline.

# Rules:

- **Scope reading and output to the prompt, never a default full timeline.** A broad ask ("show me the activity history", "recent activity on X", "what's going on with X", "catch me up on touches with X") shows the calendar and the activity list; "show me the activities" shows only the list; "how often are we touching X / anything going quiet" shows only the calendar; "when did we last talk?" is a one-line answer. Think in lego blocks: a broad ask shows every block that carries real signal; a specific ask shows only the block(s) it names; a direct question gets no blocks. Don't show something just because you fetched it.
- **Only these four parents expose `ActivityHistories`: `Account`, `Contact`, `Lead`, `Opportunity`.** Any other object → stop and tell the user; don't attempt the query.
- `ActivityHistory` is a **child subquery only** — it can't be queried standalone, and UI-API GraphQL doesn't expose it, so this skill uses **SOQL at `v63.0`**. Every field below is standard and fixed; no schema grounding is needed.
- Render `ActivitySubtype` (Call/Email/Task/Event), NOT `ActivityType` — the latter is often empty.
- A blank/absent history is a valid "no activity" result, not an error.

# Query Activity History

## 1. Validate the object

`objectName` must be one of `Account`, `Contact`, `Lead`, `Opportunity` (key prefixes `001`/`003`/`00Q`/`006`). Anything else → stop, tell the user only those four are supported, don't query.

## 2. Resolve the record

If the user gave an Id matching the object's prefix, use it. Otherwise look up by name (`Name` works for all four — compound for Contact/Lead):

**Resolver provenance:** Treat a parent Id as supplied only when it appears in the current user turn or its attached record context, or when the literal resolver below returns it in this run. Never substitute model memory, a prior conversation, or a cached Id for the resolver. When the current request names a record without an Id, run the resolver now, keep resolver and history reads sequential, and follow the one/multiple/none branches without silently choosing.

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
         queryParams: { "q": "SELECT Id, Name FROM [objectName] WHERE Name LIKE '%[match]%' LIMIT 5" })
```

- **One match** → use its `Id`. **Multiple** → list (Name · Id) and ask which. **None** → tell the user no `[objectName]` by that name exists; never invent or create one.

## 3. Query activity history

Subquery from the resolved parent (standard fields, no grounding):

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
         queryParams: { "q": "SELECT (SELECT ActivityDate, ActivitySubtype, ActivityType, CompletedDateTime, Description, Subject, OwnerId, Owner.Name, CreatedById, CreatedBy.Name, WhoId, Who.Name, StartDateTime, EndDateTime, LastModifiedDate FROM ActivityHistories ORDER BY ActivityDate DESC NULLS LAST, LastModifiedDate DESC LIMIT 500) FROM [objectName] WHERE Id = '[recordId]'" })
```

- **On error `"There is an implementation restriction on ActivityHistories"`** (very large history) → report the platform restriction and stop. The query already contains `LIMIT 500`; do not append a second limit, repeat the same request, or invent an unvalidated lower bound.
- Response is one parent record with a nested `ActivityHistories` collection. Absent/empty collection = valid "no activity", not an error.
- Use `ActivitySubtype` for the type; `ActivityType` is often blank.
- **Day counts:** pick one as-of date and timezone from the current host context for "today", the 12-week window, and every day count or age. If either is unavailable, show the latest absolute `ActivityDate` and omit relative-age wording.

## 4. Render → **Step R**.

## Step R — Render

**Widget transport:** Pass the fully hydrated renderer to `display_widget` as a direct top-level tool call whose `widgetDefinition` is a native JSON object. Never serialize or quote it, and never build or send it through generated code, a shell, a code runner, or temporary files. A returned string, printed preview, or generated file is not a mounted visual and is never a successful render. If the call succeeds, it is the terminal output: stop with no further assistant text. If it returns an error or the tool is unavailable, do not retry, repair, or create a substitute artifact; emit only the Markdown fallback below and stop, and never claim the widget rendered.
- ❌ WRONG: `widgetDefinition: "{\"key\":...}"` (stringified with escaped quotes)
- ✅ RIGHT: `widgetDefinition: {"key":...}` (native object, no quotes around the opening brace)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/query-activity-history", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the Markdown below only as the fallback when the tool is unavailable (e.g. a terminal). `TotalCount = 0` → skip the widget and render only the empty-state markdown below. Never fabricate activities.

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (card headings in upper case) and write every free-text field (`description`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. An activity's `type` picks its icon and type word; a calendar day in `days` is drawn as an activity day. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.
- **Everything comes from the Step 3 rows.** `ActivitySubtype` → `type` (lower case: `call`, `event`, `task`, `email`); `ActivityDate` → `date` and the calendar day; `Who.Name` → `who`; `Subject` plus a trimmed `Description` → `description`. Counts in the `answer` (activities, weeks, gap length) are computed from those rows, never estimated. `viewRecordUrl` is `https://<myDomain>/lightning/r/<ObjectName>/<recordId>/view` (use it as the record source's `url`).

### How to compute `calendar`

Only when the prompt needs it (see the table). Send the dates; the renderer draws the months, weekday names and empty days.

1. **Window:** the 12 weeks (84 days) ending today. `to` is today, `from` is 83 days before it.
2. **`days`:** one entry per day with at least one activity from the Step 3 rows, as `{ "date": "YYYY-MM-DD", "value": <number of activities that day> }`. Leave quiet days out.
3. **Quiet stretches are not drawn:** do not send quiet days; if there is a gap, state it in the `answer` using the real dates from the rows.
4. **Check before sending:** `to` is today and `from` is 83 days earlier; every date is a real `YYYY-MM-DD` inside `from`..`to`; the dates match the Step 3 activity dates; any gap you describe in the `answer` falls between the dates you sent.

Example: two activities on Jul 9 and one each on Aug 17 and Aug 24, 2026, with today Aug 24: `{ "from": "2026-06-02", "to": "2026-08-24", "days": [ {"date":"2026-07-09","value":2}, {"date":"2026-08-17","value":1}, {"date":"2026-08-24","value":1} ] }`.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| **Broad** ("show me the activity history for X", "recent activity on X", "what's going on with X?", "activity on X", "catch me up on touches with X") | `title` + `answer` + `calendar` + `activities` + `callout` if a dated commitment is open + `sources` |
| **Specific: the activities** ("show me the activities for X", "what happened on this deal?", "recent calls and emails", "summarize activity for X") | `title` + `answer` + **only** `activities` + tail only if it applies + `sources`. No `calendar` |
| **Specific: cadence** ("how often are we touching X?", "anything going quiet on X?", "is there a gap?", "how engaged are we?") | `title` (the verdict on the pattern) + `answer` + **only** `calendar` + `callout` if a dated commitment is open + `sources`. No `activities` |
| **Single fact** ("when did we last talk to X?", "who was on the last call?") | `title` + `answer` (one sentence) + `sources`. No cards |

#### Worked examples (the `props` object only)

**Cadence — "Anything going quiet on Cedarline?"** (calendar + activities, the open commitment as a callout):

```json
{
  "title": "A 39-day silence lines up exactly with the reorg.",
  "answer": "Only **4 activities in 12 weeks**, and a hard gap from **Jul 9 to Aug 17**. You re-opened the thread today with a pricing call – and Priya asked for a revised model by **Aug 27**.",
  "calendar": { "from": "2026-06-02", "to": "2026-08-24", "days": [ {"date": "2026-07-09", "value": 2}, {"date": "2026-08-17", "value": 1}, {"date": "2026-08-24", "value": 1} ] },
  "activities": [
    {"type": "call", "date": "Aug 24, 2026", "who": "Priya Anand", "description": "Pricing discussion – re-engagement call on pricing tier & contract length. Priya asked for a revised commercial model by Aug 27."},
    {"type": "event", "date": "Aug 17, 2026", "description": "Customer call – Cedarline pricing and ROI. 45-min walkthrough with Priya + procurement rep · first contact after the July gap."},
    {"type": "task", "date": "Jul 9, 2026", "who": "Gregory Holt", "description": "Procurement confirmed board review pending – scheduled Jul 21 · Gregory said he'd loop back after; no follow-up logged."},
    {"type": "task", "date": "Jul 9, 2026", "who": "Robert Nkemelu", "description": "Last substantive Cedarline meeting (champion still in seat) – deep discovery on quota + territory model · Robert reorged out of the account 3 days later."}
  ],
  "callout": {"lead": "Priya asked for a revised model by Aug 27.", "text": "Today's pricing call ended a 39-day period of no engagement – this is the thread that reopened the deal. Schedule the follow-up now to lock the Aug 27 commitment before it lapses.", "buttonLabel": "Schedule the Aug 27 follow-up", "actionMsg": "Schedule a follow-up with Priya Anand at Cedarline for Aug 27 to walk through the revised commercial model."},
  "sources": [
    {"label": "Account – Cedarline Financial"},
    {"label": "Activity history – 4 closed activities"},
    {"label": "Contact – Priya Anand"}
  ]
}
```

**Specific — "What was the last thing we logged on Priya Anand?"** (a single fact, no cards):

```json
{
  "title": "The last logged touch was a pricing call with Priya on Aug 24.",
  "answer": "Your last activity on Priya Anand is a **Call on Aug 24, 2026** about pricing tier and contract length; nothing is logged since.",
  "sources": [
    {"label": "Contact – Priya Anand"}
  ]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (calendar, activities), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A single-fact question (when was the last touch?) usually gets no tail and no cards. Format every value as a ready-to-display string (dates as 'Aug 24, 2026'); names are plain strings, never objects (use `Who.Name`, not the relationship object).",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line: the takeaway about this record's activity in the user's context (e.g. 'A 39-day silence lines up exactly with the reorg.'). Plain text, no markdown. Never the skill name or 'Activity History: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown, rendered under the title: ONE short paragraph of 1-3 sentences that answers ONLY what the user asked (volume, gaps, last touch, what changed), with **bold** inline on the key facts (counts, date ranges, names, dates). No bullets, headings or tables. Do not restate the cards below it."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, legend words, activity types, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "activityHistory": {
          "type": "string",
          "default": "ACTIVITY HISTORY",
          "description": "Heading of the heatmap card. English: 'ACTIVITY HISTORY'."
        },
        "allActivities": {
          "type": "string",
          "default": "ALL ACTIVITIES",
          "description": "Heading of the activities list card. English: 'ALL ACTIVITIES'."
        },
        "call": {
          "type": "string",
          "default": "Call",
          "description": "Type word on a call row. English: 'Call'."
        },
        "event": {
          "type": "string",
          "default": "Event",
          "description": "Type word on an event (meeting) row. English: 'Event'."
        },
        "task": {
          "type": "string",
          "default": "Task",
          "description": "Type word on a task row. English: 'Task'."
        },
        "email": {
          "type": "string",
          "default": "Email",
          "description": "Type word on an email row. English: 'Email'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        },
        "calendarCaption": {
          "type": "string",
          "default": "Each square is a day; blue days had activity",
          "description": "Small caption under the calendar squares. English: 'Each square is a day; blue days had activity'."
        },
        "noActivity": {
          "type": "string",
          "default": "No activity",
          "description": "Legend word for an outlined day with no activity. English: 'No activity'."
        },
        "activity": {
          "type": "string",
          "default": "Activity",
          "description": "Legend word for a blue day with at least one activity. English: 'Activity'."
        },
        "outsideRange": {
          "type": "string",
          "default": "Not in range",
          "description": "Legend word for a grey day outside the queried window. English: 'Not in range'."
        }
      }
    },
    "calendar": {
      "type": "object",
      "description": "OPTIONAL card 'ACTIVITY HISTORY': a month-by-month calendar of when activity happened (blue days had activity, outlined days had none, grey days fall outside the window), plus a legend. Include for a broad ask (\"show me the activity history\") and for cadence questions (how often we touch the account, anything going quiet, gaps, engagement over time). Omit when the prompt asks only for the activities list, or for a single fact. Window and day rules: see 'How to compute `calendar`' in the skill instructions.",
      "required": [
        "from",
        "to",
        "days"
      ],
      "additionalProperties": false,
      "properties": {
        "from": {
          "type": "string",
          "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
          "description": "First day shown, YYYY-MM-DD: 83 days before `to`, so the window is 12 weeks."
        },
        "to": {
          "type": "string",
          "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
          "description": "Last day shown, YYYY-MM-DD: today."
        },
        "days": {
          "type": "array",
          "maxItems": 120,
          "description": "One entry per day that had at least one activity, any order. Quiet days are left out and drawn empty.",
          "items": {
            "type": "object",
            "required": [
              "date",
              "value"
            ],
            "additionalProperties": false,
            "properties": {
              "date": {
                "type": "string",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                "description": "The activity day, YYYY-MM-DD, within from..to."
              },
              "value": {
                "type": "integer",
                "minimum": 1,
                "description": "Number of activities that day (the Step 3 rows with that ActivityDate)."
              }
            }
          },
          "minItems": 0
        }
      }
    },
    "activities": {
      "type": "array",
      "minItems": 1,
      "maxItems": 10,
      "description": "OPTIONAL card 'ALL ACTIVITIES': the individual closed Tasks/Events, newest first, one row each. Include for a broad ask (\"show me the activity history\") and when the prompt asks what happened, for the list/timeline or the latest touches. Omit for a pure cadence or gap question (the calendar answers that). Never an empty array; at most 10 rows (the most recent / most relevant).",
      "items": {
        "type": "object",
        "required": [
          "type",
          "date"
        ],
        "properties": {
          "type": {
            "type": "string",
            "enum": [
              "call",
              "event",
              "task",
              "email"
            ],
            "description": "Activity kind from ActivitySubtype: picks the round icon and the type word. call = Call, event = Event (meeting), task = Task, email = Email."
          },
          "date": {
            "type": "string",
            "description": "The activity date, ready to display (e.g. 'Aug 24, 2026')."
          },
          "who": {
            "type": "string",
            "description": "The contact the activity was with (Who.Name), plain string. Omit when none."
          },
          "description": {
            "type": "string",
            "description": "One or two lines of plain text on what happened: the Subject, plus the key point from the Description, trimmed to about 200 characters. Omit when both are blank."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if the activity pattern is time-sensitive (a commitment with a date, a gap that is still open) AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
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
      "description": "REQUIRED. Where the answer came from: the Salesforce record whose ActivityHistories you read, linked, plus any other record you cited. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Account – Cedarline Financial', 'Activity history (4 records)')."
          },
          "url": {
            "type": "string",
            "description": "Record or list-view URL. Omit if none."
          }
        }
      }
    }
  }
}
```



Markdown — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED. Apply the formatting rules below:

```markdown
# Activity History: [RecordName] ([ObjectName])
**[TotalCount] activities**  |  **Last:** [LastActivityDate]  |  **Owner:** [OwnerName]

| Date | Type | Subject | Owner | With |
|---|---|---|---|---|
| [ActivityDate] | [ActivitySubtype] | [Subject] | [Owner.Name] | [Who.Name or —] |
| … | | | | |
```

- One row per activity, most recent first (sorted by `ActivityDate` desc, then `LastModifiedDate` desc).
- Show at most **20**; if `TotalCount > 20` append `…and [N] older activities not shown`.
- `TotalCount = 0` → render only `No activity history found for [RecordName].`
- Label undated activities "Undated"; omit the "With" cell when `Who.Name` is null.
- Append each non-empty `Description` as a short sub-bullet under its row (truncate at 200 chars), or add a Description column inline — don't drop it (the widget path shows it).
