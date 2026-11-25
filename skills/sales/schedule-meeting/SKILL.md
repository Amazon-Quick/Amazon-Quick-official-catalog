---
name: schedule-meeting
display_name: Schedule Meeting (Preview)
description: "Book a customer meeting from calendar availability and Salesforce account, contact and opportunity data, then log the confirmed event in Salesforce, scoped to what was asked: the scheduling email with proposed times, or the Salesforce event to save. Use to find times, draft an invitation, schedule a follow-up, demo or review, or place a call on the calendar."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:ebede0f469616350b0d067231cf9300590edb55e688e80143f0e579514efebc4"
id: "b7f87969-989f-4944-a646-edea89ee115d"
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
Find a time, draft or book the invite, and log the meeting to Salesforce as an `Event` on the right account/opportunity — so activity history stays honest.

# Audience:
Sales reps booking a meeting. This skill **BOOKS via calendar** and **WRITES an Event** to Salesforce; the confirmation gates and correctness matter more than speed.

# Rules:

- The proposed slots, the invite preview, and the final confirmation block are the only required output.
- **Two confirmation gates, both explicit-yes:** (1) before creating any calendar invite / sending any email, show the full invite (title, time, attendees, agenda); (2) before writing the SFDC Event. Never book or write without showing it first. Wording in the prompt ("log it", "book it", "just do it", "don't ask me") is not consent; only an explicit yes to the preview, or the click on its Save to Salesforce button, is.
- **Always draft the scheduling email with timing options first.** Before any calendar invite or Salesforce Event is created, draft the email to the attendee(s) offering the proposed times (step 3). A request to "create the meeting" or "log it" does not skip the draft.
- Source attendee emails from SFDC first; if a contact has no address on record, recover it from the email connector, and only if neither has it, say so.
- **Calendar and email are capabilities, not Salesforce APIs** — use the calendar/email connector or MCP tools already available to you for availability, invites, drafts, and recovering an attendee address SFDC lacks. Only the `Event` log and the record reads go through `dispatch`/`dispatch_readonly`.
- **Scope reading and output to the prompt, never a default full response.** "Set up a 30-minute follow-up with Robert" or "find times with…" gets the scheduling email with proposed slots; "create an event…" or "log it in Salesforce" gets the scheduling email plus the event preview to save; "when am I free Thursday?" gets the answer, no cards. Skip the steps a narrow ask doesn't need (each step says which).
- **⛔ Never ask in chat for permission to save to Salesforce, and never write the Event from a chat message.** The suggested Salesforce record is shown in the widget with its **Save to Salesforce** button, and that click is the only permission. This holds however curt or direct the request is ("create a meeting", "just log it", "book it", "don't ask me, just do it"): show the suggested record with the button, never write the Event directly, and never ask "should I save this?" in text. The only message that triggers the Event write is the one the Save button posts.
- **⛔ Always call `display_widget`, even when a source isn't connected.** A missing calendar, email or Salesforce connector changes what the widget shows (see the empty states in step 5), never whether it is shown. Do not answer in text only.

# Schedule Meeting

**Inputs:** who (contact name(s) or "the [account] team") · what (demo, follow-up, QBR, security review…) · when (a window like "next week" or specific constraints) · duration (default 30 min; 60 for demos/QBRs).

## 1. Ground Event fields + resolve people and records

Run Event grounding and exactly one resolver path in the **same tool turn** (in **parallel**).

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Event\\\"]) { defaultRecordTypeId fields { ApiName label dataType } } } }\"}" })
```

**Account supplied:** `<ACCOUNT_FILTER>` = `Id: { eq: "<ACCOUNT_ID>" }`, or `Name: { like: "%[account]%" }` if no Id.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { <ACCOUNT_FILTER> }, first: 10) { edges { node { Id Name { value } BillingCity { value } BillingState { value } Industry { value } } } } } } }\"}" })
```

**Only contact name(s) supplied:** run once per attendee in parallel; use its Account Id below.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { Name: { like: \\\"%[name]%\\\" } }, first: 10) { edges { node { Id Name { value } Title { value } Account { Id Name { value } } } } } } } }\"}" })
```

Resolve one Account; ask on zero/multiple Account or Contact matches. Contact-only matches must share it; never guess.

## 1b. Read people and open opportunities

In the **same tool turn** (in **parallel**), run Opportunity and one Contact request per attendee with the same exact `<ACCOUNT_ID>`. Set `<CONTACT_SELECTOR>` to: resolved contact → `, Id: { eq: "<CONTACT_ID>" }`; account supplied → `, Name: { like: "%[name]%" }`; "the account team" → omit.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { AccountId: { eq: \\\"<ACCOUNT_ID>\\\" } <CONTACT_SELECTOR> }, first: 10) { edges { node { Id Name { value } Email { value } Title { value } } } } } } }\"}" })
```

Resolve each named attendee to one Contact; ask on zero/multiple matches.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { AccountId: { eq: \\\"<ACCOUNT_ID>\\\" }, IsClosed: { eq: false } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } } } } } } }\"}" })
```

Get attendee emails from SFDC; if a contact record has no address, recover it from the email connector. If neither has it, say so — never invent one. If multiple open opps, ask which one this meeting belongs to.

Narrow asks: the scheduling email only → skip the Opportunity read; an availability question ("when am I free Thursday?") → skip steps 1–1b and go to step 2.

## 2. Find the time

Pull your calendar availability in the requested window (calendar tool). Propose 2–3 specific slots, avoiding existing meeting blocks and respecting working hours. Honor any stated customer preferences (timezone, no Fridays).
When the user already gave the time (e.g. "create an event for Oct 29 at 2 PM"), don't propose slots: check only that time and flag a conflict.

## 3. Draft the email first, then book

- **Always draft first:** draft an email to the attendee(s) offering the slots, or the one time the user gave (use `voice-profile` tone if configured). It is required before any invite or Event, including when the user asked straight away to create the meeting. Lands as a draft, never sent automatically.
- **Direct invite:** only after the email draft is shown and the user asks to book a time, create the calendar event (attendees, agenda in the description, video link if the calendar adds one). Show the full invite and get an explicit yes **before** creating it.

## 4. Log it in Salesforce

After the invite exists, create the matching SFDC `Event` — confirm before writing:

```
dispatch(method: "POST", url: "/services/data/v63.0/sobjects/Event",
         body: { "Subject": "[title]", "StartDateTime": "[ISO8601]", "EndDateTime": "[ISO8601]", "WhoId": "[primary contact Id]", "WhatId": "[opportunity or account Id]" })
```

Include `"Type": "[type]"` in the Event write and show it on the suggested record **only when `Type` is in step 1's Event field list**, which lists only the fields the user can access. When `Type` is not in that list the field is hidden for this user: leave `Type` out of the write and `type` out of the card, never invent or force a value, and keep the **Save to Salesforce** button. When it is in the list, **Type is never blank — it defaults to `"Meeting"`** when the user didn't name one. When the user named a meeting type, read the Type picklist values for the user's default Event record type (`defaultRecordTypeId` from step 1's Event grounding), match on `label`, and send `value`. When the user didn't name a type, default to `"Meeting"` if that value exists in the picklist; otherwise use the first active value. Event Type is often an unrestricted picklist, so the write would accept a made-up value — always validate against the record type's values. **A Type lookup that fails, returns nothing or can't be matched is not a blocker:** send `type: "Meeting"`, keep the **Save to Salesforce** button, and never say the save is unavailable or withhold the card for want of a Type. Only a rejected write (after the click) is reported. Never substitute the master record type `012000000000000AAA`: it lists every value in the org, including ones the user's record type rejects on save.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(objectInfoInputs: [{apiName: \\\"Event\\\", recordTypeIDs: [\\\"<RECORD_TYPE_ID>\\\"]}]) { fields { ApiName ... on PicklistField { picklistValuesByRecordTypeIDs { picklistValues { value label } } } } } } }\"}" })
```

Saving the Event in Salesforce does not put the meeting on the calendar. If there is no invite yet and the user wants one, that is gate 1 (step 3). With the widget, the suggested Salesforce record is the confirmation: show it in the event card with its **Save to Salesforce** button and stop. Do not ask for permission in text (no "should I log this?", no "are you sure?"). The click is the user's explicit yes, so when the message the button posts arrives, write the Event immediately and show the saved card. Never write the Event on any other message, even one that says "create it" or "log it".

On a read-only connector, output the Event details as a paste-ready block instead of writing. Then confirm:

## 5. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/schedule-meeting", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`body`, `subject`, `when`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.
- **The email is a draft.** Nothing is sent from this turn. The Send button posts its `actionMsg` to chat; on that turn, show the final text and send it with the connected email tool only after the user confirms. **No Send button without an email tool:** when none of the email tools you can see is connected (Gmail, Outlook or any other), omit `email.actionMsg` so the renderer hides the Send button, and never offer a send you can't do. The draft stays on screen to copy.
- **The event card is the preview for gate 2, and the only way to save.** Send it with `actionMsg`, and with `type` whenever the Event `Type` field is accessible (step 4), before writing; Save posts that message, and that turn writes the Event (step 4). When `Type` is accessible, `type` is required in the preview and is never blank — default to "Meeting" when the user didn't name a type; when it is not accessible, send the card with `actionMsg` and no `type`. Never replace the card with a text question or a text-only preview, even when the user asks bluntly to create the meeting. Never leave out `actionMsg`, or `type` when `Type` is accessible, for any reason (a failed Type read, an uncertain record, a missing calendar): without `actionMsg` the card shows no Save button. If something is genuinely unknown, say so in `title` and still send them. After the write succeeds, send the card again without `actionMsg` or `type`, with a "Saved…" title and the new Event in `sources`, linked.
- **The email draft comes first.** A request to create or log the event gets the email card (step 3) above the event card in the same widget, never the event card alone.
- **A missing connector is a blocker to report, not a reason to skip the widget.** Do the Salesforce part anyway (steps 1–1b: resolve the account, contacts and opportunity), then render the widget with the blocker stated in `title` (e.g. "Your calendar isn't connected, so I can't propose times – here are the Acme contacts I found."). Never answer in text only, and never say the skill can't run without the calendar.
  - **Calendar not connected:** no proposed times and no "Calendar availability" in `sources`. For a scheduling or create ask, send the email card with a body asking the attendees which windows work (never invented times), plus the event card with Save when the user asked to log the meeting. For an availability question or any ask with no card, send `answer` bullets listing the contacts you resolved (name, title, email) and the opportunity, with the Salesforce records in `sources`.
  - **No email tool connected (any provider):** still show the email card, but without `actionMsg` so there is no Send button, and say in `title` that the draft can't be sent from here.
  - **Record reads empty:** send what you have and name what's missing in `title`.
- **Slots, attendees and records come from what you read:** slots from the calendar availability (step 2), `with` and `relatedTo` from the Contact and Opportunity reads (step 1b). Never invent an address, a slot or a record.
- **No answer bullets when a card is shown;** `answer` is only for a direct question with no card.
- **Scope reading and output to the prompt** (see the table below): answer what the user asked about, not a default full response.

### Scope the blocks to the prompt

The schema marks only `title` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| **Propose times** ("set up a 30-minute follow-up with Robert", "find times with the Cedarline team") | `title` + **only** `email` + `sources` |
| **Create the event** ("create an event: a 30-minute event with Robert", "log it in Salesforce") | `title` + `email` (drafted first, with the time or times) + `event` with `actionMsg` and `type` (when Type is accessible) + `sources` |
| **After Save** (the Save button's message, once the write succeeds) | `title` ("Saved…") + `event` without `actionMsg` + `sources` (with the saved Event) |
| **Direct question** ("when am I free Thursday?") | `title` + `answer` + `sources`. No cards |
| **A source isn't connected** (calendar, email) | Whatever the ask above calls for, built from the Salesforce data, with the blocker in `title`; with no card, `answer` lists the contacts. Never text only |

#### Worked examples (the `props` object only; values are illustrative)

**Propose times — "Set up a 30-minute follow-up with Robert Nkemelu at Cedarline"** (e.g. the email only):

```json
{
  "title": "Here's a scheduling email to Robert Nkemelu with two proposed times – send it, or tell me what to change.",
  "email": {
    "body": ["Hi Robert,", "I'd love to grab 30 minutes to pick up the Sales Cloud thread and align on next steps. A couple of options on my side:", "· **Tuesday, Oct 27 · 9:00–9:30 AM PT**\\\n· **Tuesday, Oct 27 · 11:00–11:30 AM PT**", "If neither works, send me a window that does and I'll make it happen.", "Best,\\\nBryan Corcoran\\\nSalesforce"],
    "actionMsg": "Send the scheduling email to Robert Nkemelu (robert.nkemelu@cedarline.com) – show it to me to confirm first."
  },
  "sources": [{ "label": "Contact – Robert Nkemelu" }, { "label": "Calendar availability" }]
}
```

**Create the event — "Create an event: a 30-minute event with Robert"** (the email draft first, then the preview with Save):

```json
{
  "title": "Done – a scheduling email to Robert Nkemelu is drafted, and a 30-minute event is ready to save to Salesforce for Oct 29 at 2:00 PM.",
  "email": {
    "body": ["Hi Robert,", "I'd love to grab 30 minutes to pick up the Sales Cloud thread. Does this work?", "· **Thursday, Oct 29 · 2:00–2:30 PM PT**", "If not, send me a window that does and I'll make it happen.", "Best,\\\nBryan Corcoran\\\nSalesforce"],
    "actionMsg": "Send the scheduling email to Robert Nkemelu (robert.nkemelu@cedarline.com) – show it to me to confirm first."
  },
  "event": {
    "subject": "Follow-up – Cedarline Sales Cloud",
    "when": "Thu, Oct 29, 2026 · 2:00–2:30 PM PT",
    "with": "Robert Nkemelu (Cedarline Financial)",
    "relatedTo": { "label": "Opportunity: Enterprise Sales Cloud Platform", "url": "https://<instance>/lightning/r/Opportunity/<OPP_ID>/view" },
    "type": "Meeting",
    "actionMsg": "Save this event to Salesforce: Follow-up – Cedarline Sales Cloud, Thu Oct 29 2:00–2:30 PM PT, with Robert Nkemelu, on Enterprise Sales Cloud Platform."
  },
  "sources": [{ "label": "Contact – Robert Nkemelu" }, { "label": "Opportunity – Enterprise Sales Cloud Platform" }]
}
```

`props` schema (JSON Schema). Only `title` and `sources` are required; follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, the optional answer, then the optional cards (email, event), then sources. Only title and sources are required. Which card to include: see the scope table in the skill instructions; a response usually has one card. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A scheduling response gets no tail: the card carries the action. Format every value as a ready-to-display string (dates, times with time zone); names are plain strings, never objects (use `Contact.Name.value`).",
  "required": [
    "title",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line that says what is ready and what happens next, in the user's context (e.g. 'Here's a scheduling email to Robert Nkemelu with two proposed times – send it, or tell me what to change.' / 'Done – a 30-minute event with Robert Nkemelu is ready to save to Salesforce for Oct 29 at 2:00 PM.'). Plain text, no markdown. Never the skill name."
    },
    "answer": {
      "type": "string",
      "description": "OPTIONAL. Omit when a card is shown: the card already carries the detail. Only for a direct question with no card (e.g. 'when am I free Thursday?'): 1-3 short '- ' markdown bullets, **bold** on the times and names."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, field labels, buttons, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "email": {
          "type": "string",
          "default": "EMAIL DRAFT",
          "description": "Heading of the email card. English: 'EMAIL DRAFT'."
        },
        "draft": {
          "type": "string",
          "default": "DRAFT",
          "description": "Small label at the top of the email draft. English: 'DRAFT'."
        },
        "send": {
          "type": "string",
          "default": "Send",
          "description": "Button under the email draft. English: 'Send'."
        },
        "event": {
          "type": "string",
          "default": "NEW SALESFORCE EVENT",
          "description": "Heading of the event card. English: 'NEW SALESFORCE EVENT'."
        },
        "subject": {
          "type": "string",
          "default": "SUBJECT",
          "description": "Label of the event subject row. English: 'SUBJECT'."
        },
        "when": {
          "type": "string",
          "default": "WHEN",
          "description": "Label of the event date/time row. English: 'WHEN'."
        },
        "with": {
          "type": "string",
          "default": "WITH",
          "description": "Label of the event attendee row. English: 'WITH'."
        },
        "relatedTo": {
          "type": "string",
          "default": "RELATED TO",
          "description": "Label of the related record row. English: 'RELATED TO'."
        },
        "type": {
          "type": "string",
          "default": "TYPE",
          "description": "Label of the event type row. English: 'TYPE'."
        },
        "save": {
          "type": "string",
          "default": "Save to Salesforce",
          "description": "Button under the event. English: 'Save to Salesforce'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "email": {
      "type": "object",
      "description": "OPTIONAL card 'EMAIL DRAFT'. Include when the prompt asks to set up, propose or find times for a meeting by email, and always before the event card when the prompt asks to create or log the meeting. Omit the key otherwise.",
      "required": [
        "body"
      ],
      "properties": {
        "body": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string"
          },
          "description": "The email, one array item per paragraph, in order: greeting, why we're meeting, the proposed slots, a fallback line, sign-off and signature. Each item is markdown. The slots are ONE item, one line per slot as `· **Tuesday, Oct 27 · 9:00–9:30 AM PT**`, ending each line but the last with a backslash before the newline; use the same line break for the signature (\"Best,\\\\\\nBryan Corcoran\\\\\\nSalesforce\"). Slots come from the calendar availability you read, 2–3 of them, with the time zone. If the calendar isn't connected, the slots item is one line asking the attendee which windows work for them – never invented times. Under 120 words in total."
        },
        "actionMsg": {
          "type": "string",
          "description": "REQUIRED whenever any email tool is connected; OMIT it when none is, which hides the Send button (the draft stays visible). First-person request sent to chat when Send is clicked: who it goes to and that you confirm before sending (e.g. 'Send the scheduling email to Robert Nkemelu (robert.nkemelu@cedarline.com) – show it to me to confirm first.')."
        }
      }
    },
    "event": {
      "type": "object",
      "description": "OPTIONAL card 'NEW SALESFORCE EVENT'. Include when the prompt asks to create, book or log the meeting in Salesforce: first as a preview with `actionMsg` (the Save button), then, after the write succeeds, again without `actionMsg` and with the saved record in `sources`. Omit the key otherwise.",
      "required": [
        "subject",
        "when"
      ],
      "properties": {
        "subject": {
          "type": "string",
          "description": "The Event Subject (e.g. 'Follow-up – Cedarline Sales Cloud'). Plain text."
        },
        "when": {
          "type": "string",
          "description": "Date, time range and time zone (e.g. 'Thu, Oct 29, 2026 · 2:00–2:30 PM PT')."
        },
        "with": {
          "type": "string",
          "description": "The contact the event is with, and their account (e.g. 'Robert Nkemelu (Cedarline Financial)'). Several: comma-separated."
        },
        "relatedTo": {
          "type": "object",
          "description": "The opportunity or account the event is logged on (WhatId). Omit if none.",
          "required": [
            "label"
          ],
          "properties": {
            "label": {
              "type": "string",
              "description": "Record type and name (e.g. 'Opportunity: Enterprise Sales Cloud Platform')."
            },
            "url": {
              "type": "string",
              "description": "Record URL. Omit if you have no Id."
            }
          }
        },
        "type": {
          "type": "string",
          "description": "REQUIRED when showing the event preview (with `actionMsg`) and the Event Type field is accessible to the user (listed in step 1's Event field list); omit it when the field is hidden, never invent a value. The Event Type picklist value that will be written (e.g. 'Meeting'). Read it from the user's Event record type when they named a type; otherwise default to 'Meeting'. Omit only after the event is saved (when `actionMsg` is absent)."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when Save is clicked; it is the user's yes to the write (e.g. 'Save this event to Salesforce: Follow-up – Cedarline Sales Cloud, Thu Oct 29 2:00–2:30 PM PT, with Robert Nkemelu, on Enterprise Sales Cloud Platform.'). Omit once the event is saved."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. What the response came from: the Salesforce records you actually read (contact, account, opportunity, the saved event), linked, plus 'Calendar availability' when you used it. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Contact – Robert Nkemelu', 'Opportunity – Enterprise Sales Cloud Platform', 'Calendar availability')."
          },
          "url": {
            "type": "string",
            "description": "Record or document URL. Omit if none."
          }
        }
      }
    }
  }
}
```

## 6. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Keep only what the prompt asked for (see the scope rule above): the proposed slots and email draft, the event preview, or this confirmation:

```
✅ Booked: [Title] - [date/time]
Calendar: [event created / draft email in email]
Salesforce: Event logged on [Account] / [Opportunity] - [link]
```
