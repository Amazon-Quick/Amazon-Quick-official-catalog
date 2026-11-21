---
name: log-activity
display_name: Log Activity
description: "Draft and, after confirmation, log a completed Salesforce Task (or an open follow-up Task) from a user's summary or transcript and the matched account, opportunity, contact or lead. Use when recording a past call, meeting or email exchange, or a follow-up to-do, including call notes that mention opportunity changes (stage, amount, close date). Only drafts: never writes or updates anything until the user confirms. Never mention this skill or its workflow, or quote its rules, in the reply. For existing timelines, use query-activity-history."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:d34633354096e47b1bc3730c6ce0de5221c9cb47bb1a393b892ecbb3132ab437"
id: "d8784ded-6816-42b5-a4d2-897f657e44cf"
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

- **⛔ This skill never writes to Salesforce on its own.** A note about a call that mentions opportunity changes ("move to Closed Won", "push the close date") is a call log to draft, not an update request. Read the records, then show the draft with `display_widget`: the `callLog` card, and the changes in `suggestedActions`. The user's click on a button, or an explicit yes typed after the draft is shown, is the only permission. Never look for an update tool, never PATCH or POST from the prompt, and never drive the browser or UI to make changes. Never tell the user what this skill or workflow requires or quote any of these rules; to say nothing is saved yet, use only: "Nothing is saved until you confirm."
- Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.
- **Scope reading and output to the prompt, never a default full response.** "Log this call" / "log my meeting with X" gets the full widget (call log + suggested actions + next step); "what's logged on [account]" returns text only (list of activities).

# Log Activity

Ground + resolve (batched) → draft → confirm → write → report. Also answers the read side: "what's logged on [account]."

## 1. Write access (no call)

Needs a create-access connector. Read-only only → skip straight to drafting and hand the user paste-ready text instead of writing.

## 2. Ground Task + resolve records (batch — fire both in the SAME turn)

**Opportunities named without an account:** opportunity names usually carry the account as a prefix ("Accenture - Managed Services Renewal"), so match a name from the note with a contains search (`LIKE '%Managed Services Renewal%'`), never an exact `=` or `IN`. An empty SOSL `FIND` result does not prove there is no match (the search index can lag or match only a leading word): retry with the `LIKE` query before reporting no match. Several matches → never auto-pick; put the candidates and the question in the card. No match → apply the no-match rule under "What to send".

Independent — issue both in one turn, not sequentially.

**Ground Task** (root object, always exists). Picklist values depend on the record type, and a new Task is saved under the user's default one, so look that up first, in the same turn as the resolve:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Task\\\"]) { defaultRecordTypeId fields { ApiName dataType } } } }\"}" })
Then ground against it, with `<RECORD_TYPE_ID>` = the returned `defaultRecordTypeId`. This reveals TaskSubtype's real picklist values, each picklist's default, and any custom required fields. Substitute only the value returned by the preceding read. Never hardcode the master record type `012000000000000AAA` when the returned default differs; if Salesforce itself returns that value, use it as the user's actual default. The same call reads the running user (`currentUser` needs **v66.0**):
```


```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } objectInfos(objectInfoInputs: [{apiName: \\\"Task\\\", recordTypeIDs: [\\\"<RECORD_TYPE_ID>\\\"]}]) { fields { ApiName label dataType required ... on PicklistField { picklistValuesByRecordTypeIDs { defaultValue { value } picklistValues { value label } } } } } } }\"}" })
```

Record `currentUser.Id` as `<UID>`, and every `required` picklist field's `defaultValue` (Status, Priority, and any custom ones) as `<PICKLIST_DEFAULTS>`.

**Resolve the account** (standard fields only, no grounding needed) — nest its open Opportunities and Contacts as children in the same call, not a separate round-trip:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 3) { edges { node { Id Name { value } Opportunities(where: { IsClosed: { eq: false } }, first: 10, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } StageName { value displayValue } CloseDate { value } } } } Contacts(first: 20) { edges { node { Id Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```

Skip the resolve call if the user already gave an unambiguous account/opp/contact Id. Multiple account matches, or an ambiguous opp/contact within one → ask, never guess which one a call belongs to. From Step 1's result, note TaskSubtype's valid values and any `required` custom field on Task — those go in the write.

**Lead instead of an account.** When the user names a lead, resolve it in place of the account (same turn as Ground Task), same one/multiple/none disambiguation. A Lead is the `WhoId` alone: a Task on a Lead takes no `WhatId`.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Lead(where: { and: [{ Name: { like: \\\"%LEAD%\\\" } }, { IsConverted: { eq: false } }] }, first: 3) { edges { node { Id Name { value } Company { value } Status { value } } } } } } }\"}" })
```

## 3. Draft (prompt only)

- **Subject:** "[Type]: [topic]" (e.g. "Call: pricing and security review timeline")
- **Type:** Call, Email, or Task (a meeting is `Task`) — written to `TaskSubtype`, a restricted picklist; must match a value Step 2 confirmed
- **Date:** when it happened (default today)
- **Description:** 3-6 bullets — discussed, agreed, their commitments, ours. From the transcript if given, else the user's words.
- **Related to:** WhatId = the resolved Opportunity (or Account if no deal), WhoId = the resolved Contact. For a Lead: WhoId = the Lead, no WhatId
- **Status:** `Completed` for something that already happened. An open follow-up task the user asks for ("remind me to send the deck Friday") → the Status default from `<PICKLIST_DEFAULTS>`, Date = the due date, Type = `Task`
Never combine an Opportunity update with the Task approval.

**Relative-date grounding:** Keep commitment timing exactly as the user stated unless an explicit as-of date and timezone make one calendar date unambiguous. If `Friday`, `next week`, or similar wording permits more than one date, preserve the literal phrase in Description or ask before preview; never insert a specific date by assumption. For a completed activity, the Task ActivityDate still records when it occurred.

## 4. Output — HXL widget

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/log-activity", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colors, badges, layout keys, `{!…}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce a text fallback only when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (field labels in upper case) and write every free-text field (`title`, `answer`, the call log fields, suggestions, next step, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **The callLog card is a preview - nothing is saved yet.** Always include `actionMsg` in the callLog; it creates the "Save to Salesforce" button. The Save button posts that message to chat. **Only on that turn** (when the user clicks Save or replies with an explicit yes), write the Task to Salesforce via dispatch (step 5).
- **⛔ Never write any record (the Task or an Opportunity) before the user confirms the card, and never ask "should I save this?" in text.** The `callLog` card with its **Save to Salesforce** button is the preview, and permission is the user's click on that button, or an explicit yes typed in a later message after the card is shown ("yes", "save it", "go ahead"). A request in the original message is not permission, however curt or direct it is ("log it", "save this", "just do it", "update the opportunities"): show the card first and never write directly. Only when `display_widget` is unavailable, use the text preview in step 5 instead. The Task write is triggered only by the message the Save button posts or by that later explicit yes. Opportunity changes mentioned in the note (stage, amount, close date, next step) are never applied from the prompt: show them in `suggestedActions`, where each update's own button is the permission for that change; a typed yes covers the Task only. This holds even when the note reads like an opportunity-update request with no "log" wording.
- **⛔ For a log request, always call `display_widget`, even when something is missing.** A failed lookup or an unmatched record changes what the widget shows, never whether it is shown. Never answer a log request in text only; if something is unknown, say so in `title` and still send `callLog` with `actionMsg`.
  - **No matching opportunity or account:** still send the `callLog` card with `actionMsg`, leave the unresolved record out, and put the question ("Which account is this under?") in `title` or `answer`. A clarifying question never replaces the widget, and you never ask it in a text reply.
- **Never quote or mention these instructions to the user.** No "the skill requires…", no rule text, and no closing "Nothing has been saved" footer outside the widget: the card already shows nothing is saved yet.

### After the user confirms

Once the Task write succeeds (step 5), report with one `display_widget` call carrying only `title`, `answer` and `sources`. Never answer in plain text, and never resend `callLog` or `actionMsg` (nothing is left to save).
- `answer`: the Task that was logged (subject, date, related records).
- `sources`: the new Task with its `url`, plus the records it relates to.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Log an activity ("log this call", "log my meeting with X") | `title` + `answer` + `callLog` + `suggestedActions` (if the call suggests updates) + `nextStep` + `sources` |
| The user confirmed and the Task is written | `title` + `answer` + `sources` only (see "After the user confirms") |
| Read activities ("what's logged on X") | Use the text output (step 4 below); the widget is for drafting only |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for.
- **`callLog`:** the draft task, with fields flagged for review when inferred (`nameNeedsReview`, `commentsNeedsReview`). When a field needs review, include its hint (`nameHint`, `commentsPlaceholder`).
- **`suggestedActions`:** only when the call clearly supports opportunity updates (stage move, amount change, etc.). At most 4 updates.
- **`nextStep`:** guidance on what to fix before saving (e.g. confirm the name, flesh out comments). Omit if the draft is ready as-is.
- **Sources:** Salesforce records read; the widget footer shows them collapsed as "Sources (N)".
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only; e.g. values only, never reuse their names, amounts or dates)

**Log a call** ("log my call with <Contact> at <Account>"):

```json
{
  "title": "Log my call with <Contact> at <Account>.",
  "answer": "Here's the <Account> call, drafted as a Salesforce call log – two fields need your review before saving.\n\n- I parsed your note into a **Log a Call** task on **<Date>**, related to the **<Opportunity>** opportunity.\n- Most fields came straight from what you said; **Name** and **Comments** are flagged **Needs review**.\n- Nothing is in Salesforce yet – review the draft, save it, then apply the suggested opportunity updates below.",
  "callLog": {
    "subject": "Call: <Topic> – <Account>",
    "callType": "Outbound",
    "dueDate": "YYYY-MM-DD",
    "relatedTo": "<Opportunity Name>",
    "relatedToSub": "<Stage> · <Amount> · close <Date>",
    "name": "<Contact Name>, <Title>",
    "nameNeedsReview": true,
    "nameHint": "Inferred from the <context> – confirm, or switch to <Other Contact> (<Title>).",
    "comments": "Spoke with <Contact> re: <topic>; discussed <points>.",
    "commentsNeedsReview": true,
    "commentsPlaceholder": "Add: points agreed, their commitments, your next steps.",
    "callResult": "<Outcome> · follow-up owed",
    "actionMsg": "Save this call log to Salesforce as a completed Task on the <Opportunity> opportunity."
  },
  "suggestedActions": {
    "context": "FROM THIS CALL",
    "opportunity": "<Opportunity Name>",
    "accountName": "<Account Name>",
    "updates": [
      {
        "field": "AMOUNT",
        "from": "<Old Amount>",
        "to": "<New Amount> (Q3 phased)",
        "reason": "<Contact> accepted a phased structure – <details>. Split the amount so the forecast reflects what actually closes this quarter.",
        "actionMsg": "Update the <Opportunity> opportunity amount to <New Amount> (Q3 phased)."
      },
      {
        "field": "STAGE",
        "from": "<Old Stage>",
        "to": "<New Stage>",
        "reason": "The call reopened an active conversation and a committed deliverable – moving it forward.",
        "actionMsg": "Update the <Opportunity> opportunity stage to <New Stage>."
      }
    ],
    "actionMsg": "Apply all suggested updates to the <Opportunity> opportunity."
  },
  "nextStep": "The two most useful fixes before saving: **confirm the Name** (<Contact> vs. <Other>) and **flesh out Comments** with what each side committed to – richer notes give your manager and future you better context when this deal comes up.",
  "sources": [
    { "label": "Account – <Account Name>" },
    { "label": "Opportunity – <Opportunity Name>" },
    { "label": "Contact – <Contact Name>" }
  ]
}
```

`props` schema (JSON Schema):

{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (callLog, suggestedActions), then nextStep, then sources. Only title, answer and sources are required. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A'. Format every value as a ready-to-display string (dates as YYYY-MM-DD, currency); names are plain strings.",
  "additionalProperties": false,
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One line that frames what's being drafted (e.g. 'Log my call with <Contact> at <Account>.', 'Here's the <Account> call, drafted as a Salesforce call log – two fields need your review before saving.'). Plain text, no markdown. Never the skill name."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. 2-4 short '- ' markdown bullets (or a paragraph for a brief answer): what the draft covers, what you parsed, what needs review. Put **bold** inline on key values. Answer ONLY what was asked. Never mention the skill or workflow, say what it requires, or quote any rule. To say nothing is saved yet, use only: 'Nothing is saved until you confirm.'"
    },
    "callLog": {
      "type": "object",
      "description": "OPTIONAL card showing the drafted call log before saving. Include when logging an activity. This is a PREVIEW - nothing is saved until the user confirms (the Save button's actionMsg, or an explicit yes). Always include actionMsg to create the Save button. Never write to Salesforce before showing this preview. Omit this card when the prompt is asking about activities (read-only query).",
      "additionalProperties": false,
      "required": [
        "subject",
        "callType",
        "dueDate",
        "relatedTo",
        "name",
        "comments",
        "callResult",
        "actionMsg"
      ],
      "properties": {
        "subject": {
          "type": "string",
          "description": "The task subject (e.g. 'Call: Pricing discussion – <Account>')."
        },
        "callType": {
          "type": "string",
          "description": "The call/task type from the TaskSubtype picklist (e.g. 'Outbound', 'Inbound', 'Email')."
        },
        "dueDate": {
          "type": "string",
          "description": "When the activity happened, as YYYY-MM-DD (e.g. '2026-08-24')."
        },
        "relatedTo": {
          "type": "string",
          "description": "The opportunity or account name (e.g. '<Opportunity Name>')."
        },
        "relatedToSub": {
          "type": "string",
          "description": "Muted sub-line under relatedTo: stage, amount, close date for an opportunity (e.g. 'Negotiation / Review · $640K · close Aug 31'). Omit for an account-only relation."
        },
        "name": {
          "type": "string",
          "description": "The contact name and title (e.g. '<Name>, <Title>')."
        },
        "nameNeedsReview": {
          "type": "boolean",
          "description": "true only when the name was inferred and needs confirmation. Shows a 'NEEDS REVIEW' warning badge. Omit or false otherwise."
        },
        "nameHint": {
          "type": "string",
          "description": "Muted hint under the name when nameNeedsReview is true, explaining the inference (e.g. 'Inferred from the pricing context – confirm, or switch to <Other Contact> (Procurement).').  Omit when nameNeedsReview is false."
        },
        "comments": {
          "type": "string",
          "description": "The activity description: what was discussed, as markdown. Keep it concise (3-6 bullets or a short paragraph)."
        },
        "commentsNeedsReview": {
          "type": "boolean",
          "description": "true only when the comments are incomplete and need more detail. Shows a 'NEEDS REVIEW' warning badge. Omit or false otherwise."
        },
        "commentsPlaceholder": {
          "type": "string",
          "description": "Muted hint under comments when commentsNeedsReview is true, prompting what to add (e.g. 'Add: points agreed, their commitments, your next steps.'). Omit when commentsNeedsReview is false."
        },
        "callResult": {
          "type": "string",
          "description": "One-line outcome (e.g. 'Reconnected on pricing · follow-up owed')."
        },
        "actionMsg": {
          "type": "string",
          "description": "REQUIRED. First-person request sent when Save is clicked; this creates the 'Save to Salesforce' button and is the user's explicit yes to write. Never omit - without actionMsg, there is no Save button and the write must not happen (e.g. 'Save this call log to Salesforce as a completed Task on the <Opportunity> opportunity.')."
        }
      }
    },
    "suggestedActions": {
      "type": "object",
      "description": "OPTIONAL card 'SUGGESTED ACTIONS'. Include when the call suggests opportunity updates. Omit otherwise.",
      "additionalProperties": false,
      "required": [
        "updates"
      ],
      "properties": {
        "context": {
          "type": "string",
          "description": "Optional context shown after 'SUGGESTED ACTIONS · ' (e.g. 'FROM THIS CALL'). Omit if not needed."
        },
        "opportunity": {
          "type": "string",
          "description": "The opportunity name (e.g. '<Opportunity Name>'). Omit if showing account-level actions."
        },
        "accountName": {
          "type": "string",
          "description": "The account name (e.g. '<Account Name>'). Omit if already clear from opportunity."
        },
        "updates": {
          "type": "array",
          "description": "The suggested field updates, at most 4. Never an empty array; omit suggestedActions instead.",
          "maxItems": 4,
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "field",
              "to",
              "actionMsg"
            ],
            "properties": {
              "field": {
                "type": "string",
                "description": "The field label, upper case (e.g. 'AMOUNT', 'STAGE', 'CLOSE DATE', 'OWNER')."
              },
              "from": {
                "type": "string",
                "description": "The current value, shown muted before an arrow. Omit when the field is empty."
              },
              "to": {
                "type": "string",
                "description": "The suggested value, shown bold."
              },
              "reason": {
                "type": "string",
                "description": "Muted line below: why this change is suggested, one sentence."
              },
              "actionMsg": {
                "type": "string",
                "description": "First-person request sent when UPDATE is clicked (e.g. 'Update the <Opportunity> amount to $300K (Q3 phased).')."
              }
            }
          }
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent when the bottom Save button is clicked (e.g. 'Apply all suggested updates to the <Opportunity> opportunity.')."
        }
      }
    },
    "nextStep": {
      "type": "string",
      "description": "OPTIONAL plain recommendation text, shown as markdown (e.g. 'The two most useful fixes before saving: **confirm the Name** (<Name> vs. <Other>) and **flesh out Comments** with what each side committed to – richer notes give your manager and future you better context when this deal comes up.'). Omit if not needed."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label (card headings, field labels, buttons, sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English.",
      "additionalProperties": false,
      "properties": {
        "callLogEyebrow": {
          "type": "string",
          "default": "DRAFT CALL LOG - NOT YET SAVED",
          "description": "Eyebrow of the call log card. English: 'DRAFT CALL LOG - NOT YET SAVED'."
        },
        "subject": {
          "type": "string",
          "default": "SUBJECT",
          "description": "Field label. English: 'SUBJECT'."
        },
        "callType": {
          "type": "string",
          "default": "CALL TYPE",
          "description": "Field label. English: 'CALL TYPE'."
        },
        "dueDate": {
          "type": "string",
          "default": "DUE DATE",
          "description": "Field label. English: 'DUE DATE'."
        },
        "relatedTo": {
          "type": "string",
          "default": "RELATED TO",
          "description": "Field label. English: 'RELATED TO'."
        },
        "name": {
          "type": "string",
          "default": "NAME",
          "description": "Field label. English: 'NAME'."
        },
        "comments": {
          "type": "string",
          "default": "COMMENTS",
          "description": "Field label. English: 'COMMENTS'."
        },
        "callResult": {
          "type": "string",
          "default": "CALL RESULT",
          "description": "Field label. English: 'CALL RESULT'."
        },
        "needsReview": {
          "type": "string",
          "default": "NEEDS REVIEW",
          "description": "Badge text. English: 'NEEDS REVIEW'."
        },
        "suggestedActions": {
          "type": "string",
          "default": "SUGGESTED ACTIONS",
          "description": "Eyebrow of the actions card. English: 'SUGGESTED ACTIONS'."
        },
        "opportunity": {
          "type": "string",
          "default": "OPPORTUNITY",
          "description": "Field label. English: 'OPPORTUNITY'."
        },
        "accountName": {
          "type": "string",
          "default": "ACCOUNT NAME",
          "description": "Field label. English: 'ACCOUNT NAME'."
        },
        "save": {
          "type": "string",
          "default": "Save to Salesforce",
          "description": "Save button label. English: 'Save to Salesforce'."
        },
        "update": {
          "type": "string",
          "default": "UPDATE",
          "description": "Update button label. English: 'UPDATE'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Sources toggle word; the renderer appends the count. English: 'Sources'."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. The Salesforce records read, linked. Shown as 'Salesforce · Sources (N)'. Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Account – <Account Name>', 'Opportunity – <Opportunity Name>')."
          },
          "url": {
            "type": "string",
            "description": "Record URL (https://<myDomain>/lightning/r/<SObjectType>/<Id>/view). Omit if none."
          }
        }
      }
    }
  }
}


## 5. Confirm, then write

The `callLog` card from step 4 is the preview. Write only on the message its Save button posts or on an explicit yes typed after the card is shown, never on the original request, however curt. If `display_widget` is unavailable, show the text preview below instead of the card; only an explicit yes to it is permission.

```
📋 Draft Activity Log

Subject: [subject]
Type: [Call/Email/Task]
Status: [Completed, or the open status]
Date: [date]
Related Account: [account name]
Related Opportunity: [opp name + stage + close date, or —]
Related Contact: [contact name, or Lead: lead name + company]

Description:
• [bullet]…

Ready to log this to Salesforce?
```

Never write an Opportunity update in the same turn as the Task; offer it separately.

**Confirmation scope:** This preview and its confirmation (the Save click or an explicit yes) authorize exactly one Task POST containing only the displayed fields. Present only choices to approve that Task, change it, cancel, or preview a separate follow-up; do not offer a combined Task-plus-Opportunity, email, calendar, or other mutation. An Opportunity NextStep change must run separately, show the exact current and proposed values, and obtain a fresh explicit yes. If any Task field changes after preview, show the complete revised draft and ask again.

With `display_widget`, the Save click or an explicit typed yes to the card is the yes.

Only after explicit yes:

```
dispatch(method: "POST", url: "/services/data/v63.0/sobjects/Task",
  body: { "Subject": "[subject]", "Status": "[Completed or the open status]", "OwnerId": "<UID>", "ActivityDate": "[YYYY-MM-DD]", "TaskSubtype": "[value]", "Description": "[bullets]", "WhatId": "[Opportunity or Account Id, omitted for a Lead]", "WhoId": "[Contact or Lead Id]" <PICKLIST_DEFAULTS> <TASK_CUSTOM> })
```

Always send `Status`, `OwnerId` and every other required picklist (`<PICKLIST_DEFAULTS>`, e.g. `"Priority": "Normal"`), even though the Lightning form hides or prefills them: the write is checked against that form's required fields, and an omitted one fails with `REQUIRED_FIELD_MISSING`. `OwnerId` = `<UID>` unless the user names someone else. `<TASK_CUSTOM>` = any Step 2 `required` custom fields on Task, filled from the draft/user. Never send `CallDurationInSeconds` (the Task form doesn't accept it); keep a stated duration in the Description. Creation fails (validation rule, required field) → report the exact error and output the entry as paste-ready text instead. Don't retry blind.

## 6. Report (no re-fetch — build from what you already have)

The create response returns the new Id; you already know every field you wrote. Don't re-query it back.

When `display_widget` is available, report with the widget (step 4, "After the user confirms"); use the text below only when it is unavailable.


```
✅ Logged: "[Subject]" — [Date]
Related to: [Account] / [Opportunity] / [Contact]
Record: https://[instanceUrl]/lightning/r/Task/[returned Id]/view
```



## Read mode — "what's logged on [account/opp]"

Standard fields only, no grounding. Resolve the account (or opportunity, if opp-scoped) by name, nesting its Tasks as children — `Account.Tasks` / `Opportunity.Tasks` are standard child relationships, so this is one call, not a resolve-then-query chain:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 1) { edges { node { Id Name { value } Tasks(first: 20, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } Status { value } Description { value } Owner { ... on User { Name { value } } } } } } } } } } } }\"}" })
```

Swap the root to `Opportunity(where: { Name: { like: \"%OPP%\" } }, first: 1) { edges { node { Tasks(...) {...} } } }` for an opp-scoped ask (same nested block).

Output as a dated list, newest first, one line each; note the last-touch gap if it's longer than 14 days.

## [CUSTOMIZE]

- **Required fields:** Step 2's grounding surfaces org-specific required custom fields on Task automatically — no hardcoded list needed.
- **Event vs Task:** this skill logs completed Tasks. If your org logs meetings as Events instead, switch Step 4's write to create an Event with start/end times from Calendar.
- **Description depth:** default is 3-6 bullets; adjust the target length in Step 3 if your team wants fuller notes.
