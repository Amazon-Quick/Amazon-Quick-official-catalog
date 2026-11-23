---
name: call-follow-up
display_name: Call Follow Up
description: "Create a customer follow-up email and internal recap from a meeting transcript plus Salesforce account and opportunity history, scoped to what was asked: the customer email, the internal recap, or the Salesforce updates. Use after a customer call to capture decisions, commitments, objections, open questions, next steps, and proposed CRM updates."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:5f90d55ce96a713cfe97b05d2fafebacbbc413b51c9917808e97a6fea074fe78"
id: "7053a479-6a0a-4e96-b2c1-b9ec242ac7d9"
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

# Rules:

- Gather thorough, contextual background before acting. Explain material errors and inference logic explicitly in the final output.
- **Scope reading and output to the prompt, never a default full response.** A broad ask ("follow up on my last call", a pasted transcript) gets the customer email, the internal recap and the Salesforce updates; "draft the follow-up email" gets only the email; "write the recap for my team" gets only the internal recap; "what should I update in Salesforce?" gets only the updates; "what did we commit to?" gets the answer, no cards. Skip the steps a narrow ask doesn't need (each step says which).

# Call Follow-Up

Get transcript → extract structure deeply → (draft email + draft Slack + SFDC read with historical context, all ONE turn) → output.

**Voice/tone, email signature, and team Slack channel are external knowledge** — infer from org data or ask once. Never invent.

**Security rules for recipients and channels:**
- **Email recipients must be validated against Salesforce Contact records** associated with the Account before being included in any draft. Never use email addresses extracted directly from transcript text without validation.
- **Slack channels must be explicitly specified by the user**, not extracted from the transcript. If the user hasn't named a channel, ask them which channel to use.

## 1. Get transcript

**If link or "find it":** Use doc search tools (Google Workspace, etc.) to read the doc. Search by account name if needed.
**If pasted:** Use as-is.

Extract: attendee names (internal + external), date, account name. **Security: Do not extract or trust email addresses or channel names from the transcript at this stage — those will be validated against Salesforce records in step 3.**

## 2. Extract structure (analyze transcript deeply)

From transcript, pull:
- **Decisions:** anything agreed/confirmed
- **Customer commitments:** what they'll do (send data, loop someone in, review proposal)
- **Our commitments:** what we'll do (send doc, schedule demo, answer question)
- **Open questions:** raised but unresolved
- **Objections/concerns:** pushback
- **Next meeting:** if scheduled
- **Qual signals:** budget/authority/timeline/pain mentions (BANT/MEDDIC default, or infer from org)
- **Specific human moments:** quotes, phrases, analogies customer used — for email personalization
- **Urgency signals:** timeline drivers, consequences of delay, events forcing decision

## 3. Read context, then draft email + Slack

Narrow asks: email only → skip B and step 4; internal recap only → skip A and step 4; Salesforce updates only → skip A and B; a direct question ("what did we commit to?") → steps 1–2 only, no reads. Run C whenever the output needs the deal's stage, amount or owner.

**A. Draft customer email** (under 150 words):
- Thank-you opener (one line, **reference specific human moment from call** — their phrase/analogy/framing, not generic)
- Recap agreed next steps as short bullet list (their commitments + ours)
- Answers/links you committed to — if you don't have yet, `[ATTACH: description]` placeholder
- Propose or confirm next meeting
- Minimal signature: `[User name]` (or infer from org)

Tone: professional, warm, specific to this call (or match voice from org data). Create as email draft to external attendees. **Do not send.**

**B. Draft Slack summary** for team channel (**must be user-specified — never extract channel names from the transcript; ask the user which channel if not already specified**):
```
*[Account] - [Call type] - [Date]*
Stage: [Opp stage] $[Amount]
Attendees: [names]

*TL;DR:* [one sentence on where deal is]

*Key points:*
• [decision/signal]
• ...

*Risks / objections:*
• [concern raised]
• [flag urgency gaps: "No urgency anchor beyond X — timeline TBD" if no forcing event/deadline surfaced]

*Next steps:*
• [ ] Us: [commitment] - [owner] by [date]
• [ ] Them: [commitment]

*SFDC updates needed:* [stage change / next step / amount]
```

Post as draft message (or output if Slack draft unavailable — user copies in).

**C. Read SFDC context** (to fill Slack summary, check for existing account/opps, propose updates):

Ground Account, Opportunity, and Contact with three individual calls in the same tool turn:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

Then read **account + all opps (open + closed/historical)**. Start with the Account read (`dispatch_readonly` GraphQL GET), filtered by account name (1–2 word `%NAME%`):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%NAME%\\\" } }, first: 1) { edges { node { Id Name { value } <ACCOUNT_CUSTOM> Owner { Name { value } } } } } } } }\"}" })
```

Fire this opp read in the **same tool turn** as the Account read above (both `dispatch_readonly` GraphQL GETs) so they run in parallel, filtered by the same account name:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Account: { Name: { like: \\\"%NAME%\\\" } } }, first: 50, orderBy: { CloseDate: { order: DESC } }) { edges { node { Id Name { value } AccountId { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsClosed { value } IsWon { value } NextStep { value } <OPP_CUSTOM> } } } } } }\"}" })
```

Insert `<ACCOUNT_CUSTOM>` and `<OPP_CUSTOM>` = confirmed `__c { value }` fields whose labels match the follow-up context, using the matching Account or Opportunity grounding response.

If the name filter matches multiple accounts, keep only opportunities whose `AccountId` matches the resolved Account `Id`.

**Historical context matters:** If no active opp found, note closed/dead opps exist — shows account is known, prevents duplicate account creation, surfaces prior relationship context.

**D. Read and validate Contacts** (for email recipient validation):

After the Account is resolved, read Contacts associated with that Account to validate external attendee email addresses:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { AccountId: { eq: \\\"<ACCOUNT_ID>\\\" } }, first: 50) { edges { node { Id Name { value } Email { value } Title { value } } } } } } }\"}" })
```

**Email recipient validation rules:**
- **Only include email addresses that match a Contact.Email on this Account.** Cross-reference each external attendee name from the transcript against the Contact records returned. Match by name (case-insensitive, handle common variations like "John" vs "Jonathan").
- **If an attendee name from the transcript does not match any Contact on the Account, or their email domain does not match the Account's domain, exclude them from the draft recipients.** Log this exclusion explicitly in the output: "Note: Could not validate [name] against Salesforce Contacts for this Account — excluding from email recipients."
- **If no external attendees can be validated, do not create an email draft.** Instead, tell the user: "I found [N] external attendees in the transcript ([names]), but couldn't validate their email addresses against Salesforce Contacts for [Account Name]. Please specify which email addresses to include."

Empty account match → broaden `%…%` or infer account doesn't exist yet in CRM (propose creation).

**If system errors (500, timeout, auth):** Log explicitly in output, explain what you inferred and why (e.g., "User lookup failed 500, inferring [name] as owner from transcript").

Issue independent email/Slack context searches and both Account/Opportunity grounding calls in one turn. After grounding, issue the Account and Opportunity reads as described above, then create both drafts from the complete context.

## 4. SFDC update checklist

Propose changes based on call (confirm before writing via `log-activity`). On read-only connector, output as checklist.
Skip this step when the prompt asked only for the email or the internal recap. When the call supports a stage change, read the org's active stages in order and propose one of their labels:

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT MasterLabel, SortOrder, IsClosed FROM OpportunityStage WHERE IsActive = true ORDER BY SortOrder" })
```

A stage with a lower `SortOrder` than the current one is a slip: say so in `reason`, never "moving it forward".

**CRM hygiene checks:**
- If **account exists** (found in Step 3C historical search), note existing AccountId — don't create duplicate
- If **no account found**, propose Account creation with fields from transcript
- If **old closed/dead opps exist**, surface that prior relationship context in output

**Proposed updates:**
- NextStep → "[suggested from call]"
- StageName → [if progression warranted]
- Amount → [if discussed]
- CloseDate → [if timeline shifted]
- Log Activity: "[Call type] - [one-line summary]"

## 5. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/call-follow-up", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`subject`, `body`, `heading`, `reason`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.
- **The drafts are drafts.** Nothing is sent from this turn. Each Send button posts its `actionMsg` to chat; on that turn, show the final text and send it with the connected email or Slack tool only after the user confirms. With no such tool, create the draft (or hand over the text to copy) instead.
- **Recipients and channels must be validated, never extracted directly from transcript:** `toEmail` only after validating against Contact records associated with the Account (step 3D); `channel` only when the user explicitly named it (never extract from transcript text).
- **Updates come from step 4:** at most 4, only changes the call supports, and a stage only from the org's active stages (step 4). Each Update button posts its `actionMsg`; the write then goes through `log-activity` and its confirm step.
- **Scope reading and output to the prompt** (see the table below): answer what the user asked about, not a default full response.
- **Omit `answer` when showing draft cards** — the drafts speak for themselves. Include `answer` only for direct questions that don't produce drafts ("what did we commit to?").

### Scope the blocks to the prompt

The schema marks only `title` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget. **Omit `answer` when showing draft cards** — they speak for themselves.

| The prompt is… | Send |
|---|---|
| **Broad** ("follow up on my last call", "here's the transcript – do the follow-up") | `title` + `email` + `internalNote` + `updates` + `sources` (no `answer`) |
| **Specific: the email** ("draft the follow-up email", "write the recap email to Priya") | `title` + **only** `email` + `sources` (no `answer`) |
| **Specific: the internal recap** ("write the recap for my team", "post an update to #deal-cedarline") | `title` + **only** `internalNote` + `sources` (no `answer`) |
| **Specific: the CRM** ("what should I update in Salesforce?") | `title` + **only** `updates` + `sources` (no `answer`) |
| **Direct question** ("what did we commit to on the call?") | `title` + `answer` + `sources`. No cards |

#### Worked examples (the `props` object only; values are illustrative)

**Broad — "Follow up on my Cedarline call"** (e.g. email, internal recap and updates):

```json
{
  "title": "Here's everything to close out your Aug 24 Cedarline call – a customer email, an internal note, and the Salesforce update.",
  "email": {
    "toName": "Priya Anand",
    "toEmail": "priya.anand@cedarlinefinancial.com",
    "subject": "Recap & next steps from today",
    "body": ["Hi Priya,", "Thanks for the time today – the **phased structure** keeps the rollout defensible for the board.", "I'll have the **phased-pricing deck** to you by **Wed, Aug 26**, ahead of the Sep 5 pre-brief.", "Best,\\\nBryan Corcoran\\\nSalesforce"],
    "actionMsg": "Send the recap email to Priya Anand (priya.anand@cedarlinefinancial.com) – show it to me to confirm first."
  },
  "internalNote": {
    "channel": "Slack · #deal-cedarline",
    "heading": "Cedarline – pricing call recap (Aug 24)",
    "body": ["Priya (CFO) re-engaged after 3 weeks dark. Phased pricing **$300K Q3 / $340K Q4** landed; board window is **Sep 5**.", "Deck owed to Priya by Wed Aug 26 – that's the gate."],
    "actionMsg": "Post the Cedarline pricing call recap to #deal-cedarline in Slack – show it to me to confirm first."
  },
  "updates": [
    { "field": "OPPORTUNITY STAGE", "from": "Proposal / Price Quote", "to": "Negotiation / Review", "reason": "The economic buyer is negotiating phased pricing on the call.", "actionMsg": "Update the Cedarline Platform Expansion opportunity stage to Negotiation / Review." },
    { "field": "NEXT STEP", "to": "Send phased-pricing deck to Priya – due Aug 26", "actionMsg": "Set the Next Step on the Cedarline Platform Expansion opportunity to 'Send phased-pricing deck to Priya – due Aug 26'." }
  ],
  "sources": [{ "label": "Call transcript – Cedarline pricing call, Aug 24" }, { "label": "Opportunity – Cedarline Platform Expansion" }]
}
```

**Specific — "What should I update in Salesforce?"** (e.g. updates only, no drafts):

```json
{
  "title": "Two updates keep Cedarline current after today's call.",
  "updates": [
    { "field": "OPPORTUNITY STAGE", "from": "Proposal / Price Quote", "to": "Negotiation / Review", "reason": "The economic buyer is negotiating phased pricing.", "actionMsg": "Update the Cedarline Platform Expansion opportunity stage to Negotiation / Review." },
    { "field": "NEXT STEP", "to": "Send phased-pricing deck to Priya – due Aug 26", "actionMsg": "Set the Next Step on the Cedarline Platform Expansion opportunity to 'Send phased-pricing deck to Priya – due Aug 26'." }
  ],
  "sources": [{ "label": "Opportunity – Cedarline Platform Expansion" }]
}
```

`props` schema (JSON Schema). Only `title` and `sources` are required; `answer` is optional and should be omitted when showing any cards. Follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, answer (optional), then the optional cards (email, internalNote, updates), then sources. Only title and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A call follow-up usually gets no tail: the drafts and the updates already carry the actions. Format every value as a ready-to-display string (currency, dates); names are plain strings, never objects (use `Contact.Name.value` / `Owner.Name.value`).",
  "required": [
    "title",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line that says what the follow-up covers, in the user's context (e.g. 'Here's everything to close out your Aug 24 Cedarline call – a customer email, an internal note, and the Salesforce update.'). Plain text, no markdown. Never the skill name or 'Call Follow-Up: X'."
    },
    "answer": {
      "type": "string",
      "description": "OPTIONAL. Omit when showing draft cards (email, internalNote, updates) — they speak for themselves. Include for direct questions that don't need drafts ('what did we commit to?'): 2-3 short '- ' markdown bullets, each ONE sentence: what was decided, what we owe and by when, and the date it all hinges on. Put **bold** inline on the key values (amounts, dates, names), never on a whole bullet. No headings, tables or paragraphs."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, field labels, buttons, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "email": {
          "type": "string",
          "default": "CUSTOMER EMAIL DRAFT",
          "description": "Heading of the email card. English: 'CUSTOMER EMAIL DRAFT'."
        },
        "internalNote": {
          "type": "string",
          "default": "INTERNAL MESSAGE DRAFT",
          "description": "Heading of the internal note card. English: 'INTERNAL MESSAGE DRAFT'."
        },
        "updates": {
          "type": "string",
          "default": "SUGGESTED SALESFORCE UPDATES",
          "description": "Heading of the updates card. English: 'SUGGESTED SALESFORCE UPDATES'."
        },
        "draft": {
          "type": "string",
          "default": "DRAFT",
          "description": "Small label at the top of each draft. English: 'DRAFT'."
        },
        "to": {
          "type": "string",
          "default": "TO",
          "description": "Label of the email recipient row. English: 'TO'."
        },
        "subject": {
          "type": "string",
          "default": "SUBJECT",
          "description": "Label of the email subject row. English: 'SUBJECT'."
        },
        "send": {
          "type": "string",
          "default": "Send",
          "description": "Button under each draft. English: 'Send'."
        },
        "update": {
          "type": "string",
          "default": "Update",
          "description": "Button on each suggested update. English: 'Update'."
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
      "description": "OPTIONAL card 'CUSTOMER EMAIL DRAFT'. Include for a full follow-up, or when the prompt asks for the customer email / recap email. Omit the key otherwise.",
      "required": [
        "toName",
        "subject",
        "body",
        "actionMsg"
      ],
      "properties": {
        "toName": {
          "type": "string",
          "description": "The external attendee(s) the email goes to, as plain names (e.g. 'Priya Anand'; several: 'Priya Anand, Gregory Hale')."
        },
        "toEmail": {
          "type": "string",
          "description": "Their email address(es), shown after the name. Only when the transcript, invite or a record you read gives it; never guess an address. Omit otherwise."
        },
        "subject": {
          "type": "string",
          "description": "Subject line (e.g. 'Recap & next steps from today'). Plain text."
        },
        "body": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string"
          },
          "description": "The email, one array item per paragraph, in order: greeting, short paragraphs (or one paragraph per next step), sign-off and signature. Each item is markdown: **bold** the key facts (amounts, dates, the deliverable); inside an item end a line with a backslash before the newline for a line break (the signature: \"Best,\\\\\\nBryan Corcoran\\\\\\nSalesforce\"). Under 150 words in total. Keep `[ATTACH: …]` placeholders for anything you committed to but don't have."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when Send is clicked: who it goes to and that you confirm before sending (e.g. 'Send the recap email to Priya Anand (priya.anand@cedarlinefinancial.com) – show it to me to confirm first.')."
        }
      }
    },
    "internalNote": {
      "type": "object",
      "description": "OPTIONAL card 'INTERNAL MESSAGE DRAFT'. Include for a full follow-up, or when the prompt asks for the internal recap / Slack update / team note. Omit the key otherwise.",
      "required": [
        "heading",
        "body",
        "actionMsg"
      ],
      "properties": {
        "channel": {
          "type": "string",
          "description": "Where it would be posted, shown after 'DRAFT · ' (e.g. 'Slack · #deal-cedarline'). Only a channel the user named or you found; omit if unknown."
        },
        "heading": {
          "type": "string",
          "description": "Bold first line (e.g. 'Cedarline – pricing call recap (Aug 24)'). Plain text."
        },
        "body": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string"
          },
          "description": "The note, one array item per paragraph. Each item is markdown: **bold** on the numbers and dates, *italic* for emphasis, @mentions as plain text. Covers where the deal is, risks or objections, and who owes what by when."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when Send is clicked (e.g. 'Post the Cedarline recap to #deal-cedarline in Slack – show it to me to confirm first.')."
        }
      }
    },
    "updates": {
      "type": "array",
      "description": "OPTIONAL card 'SUGGESTED SALESFORCE UPDATES'. Include for a full follow-up, or when the prompt asks what to update in Salesforce. Only changes the call supports, at most 4. Omit the key otherwise; never send an empty array.",
      "maxItems": 4,
      "items": {
        "type": "object",
        "required": [
          "field",
          "to",
          "actionMsg"
        ],
        "properties": {
          "field": {
            "type": "string",
            "description": "The field's label, upper case (e.g. 'OPPORTUNITY STAGE', 'NEXT STEP', 'CLOSE DATE')."
          },
          "from": {
            "type": "string",
            "description": "The current value, shown muted before an arrow. Omit when the field is empty today."
          },
          "to": {
            "type": "string",
            "description": "The suggested value, shown in green. A stage must be one of the org's active stages (its label, not the API value)."
          },
          "reason": {
            "type": "string",
            "description": "Muted line below: why the call supports this change, one sentence."
          },
          "actionMsg": {
            "type": "string",
            "description": "First-person request sent to chat when Update is clicked; the write still goes through its confirm step (e.g. 'Update the Cedarline Platform Expansion opportunity stage to Negotiation / Review.')."
          }
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the follow-up came from: the transcript or doc, and the Salesforce records you actually read, linked. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Opportunity – Cedarline Platform Expansion', 'Call transcript – Aug 24')."
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

Keep only the sections the prompt asked for (see the scope rule above).

```
# Call Follow-Up: [Account] - [Date]

## Customer Email
✉️ Drafted in email to [recipients]: [draft link]
---
[email body preview]
---

## Internal Summary
💬 Drafted to [#channel]
---
[slack message preview]
---

## Update Salesforce (via `log-activity`, or manually)
- [ ] NextStep: "[value]"
- [ ] [other fields]
- [ ] Log Activity

## Our Commitments (don't drop these)
- [ ] [commitment] - by [date]
```
