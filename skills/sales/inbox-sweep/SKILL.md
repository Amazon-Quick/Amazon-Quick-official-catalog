---
name: inbox-sweep
display_name: Inbox Sweep
description: "Answer what in the inbox needs the rep, scoped to what was asked: a full sweep, only the threads that need a reply, or a reply to one thread, as a prioritized response queue and email drafts from unread threads, sent-mail voice patterns and Salesforce account and opportunity context. Use when sweeping or triaging an inbox, finding messages needing replies or drafting several customer responses."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:aa59856a55ef1651f65c3b7bfe9549f8a470fb773d49be1bd2b47a17ff16c04a"
id: "3ead03da-211a-494a-80b2-72a3818b946c"
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
Answer what the user asked about their inbox (what needs a reply, what to send first, how much is noise, or a reply to one thread) in one pass. **Read only what the question needs** and present only that: a broad sweep (e.g. "sweep my inbox", "triage my email") reads the whole lookback and shows the queue with its cards; a specific ask (e.g. "draft a reply to Harry Datwani") shows only that thread.

# Rules:

- **Scope reading and output to the prompt, never a default full sweep.** Skip reads the question doesn't need (each read step says which), and don't show something just because you fetched it.

# Inbox Sweep

Unread customer emails → classify, prioritize, draft replies (into email). Cap 25 emails / 10 drafts per sweep. Lookback: 72h default.

## 1. Voice + candidate emails (one turn)

Read ~30–40 recent **external** sent emails to build an implicit style profile (greeting, length, sign-off, formality) — don't show it, just match it. In the same turn, search inbox: **unread, last <lookback>, not from your internal domain**.

Also in the same turn, **count every unread email in the same lookback** (counts only, no bodies) and bucket each one: **automated** (newsletter, no-reply or other auto-sent mail, from any domain), else **internal** (your domain), else **external**. These three counts are the widget's `unreadBySource`; never skip the count for a broad sweep, and skip it when the prompt is about one thread (e.g. "draft a reply to Harry Datwani").

## 2. Match senders to Accounts

Collect the candidate sender domains, then ONE Account read matching them (drop `scope: MINE` for a broader sweep).

**Note:** When using `scope: MINE`, do not query `currentUser` for scoping; the scope already identifies the running user's records. Follow the global connectivity rule before reporting the connector unavailable.

**Note:** Salesforce record `Id` is a scalar. When an ID is needed, select it as bare `Id`; never use the invalid `Id { value }` form.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(scope: MINE, first: 200) { edges { node { Name { value } Website { value } Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, first: 5, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } Amount { value displayValue } StageName { value displayValue } CloseDate { value } NextStep { value } } } } } } } } }}\"}" })
```

Match only by normalized sender domain and a returned Account's `Website`. Do not infer a match from Account or Opportunity names; when no exact domain match is returned, do not attach an Account, Opportunity, amount, or stage to that email. The open `Opportunities` child (same read) grounds Step 4 prioritization (Amount, soonest CloseDate) and fills the output **Opp** column (`$<Amount> · <StageName label>`) — no per-account follow-up read.
Each matched Opportunity's `Id` (same read) links it in the widget (`oppUrl`, `sources`).

## 3. Classify each (read the full thread, not just the latest)

- **Needs reply — deal**: question/request/decision on an active opp → draft
- **Needs reply — scheduling**: proposing/confirming a time → draft availability
- **Needs reply — support**: product/technical → draft ack + flag support handoff
- **FYI only**: CC/newsletter/auto → archive
- **Intro / new inbound**: first contact → route to `lead-triage`
- **Couldn't draft**: needs info only the user has → surface the blocking question
- **Sensitive — skip**: personnel/legal/exec → flag, don't draft

## 4. Prioritize (within needs-reply)

Open opp closing ≤30d > explicit deadline/urgency > larger Amount > older unread.

## 5. Draft replies (priority order, cap 10)

Full thread context; match voice; answer the ask directly + confirm next step; <120 words; **draft in-thread (reply), never send**. Scheduling → propose 2–3 calendar slots. Support → brief ack + "looping in <support>". SFDC logging stays a `log-activity` handoff (never write inline).

## 6. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/inbox-sweep", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 7 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`context`, `note`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| A broad sweep (e.g. "sweep my inbox", "triage my email") | `title` + `answer` (bullets) + `threads` + `unreadBySource` + tail only if it applies + `sources` |
| What needs a reply (e.g. "what needs a response?", "draft replies to my customer emails") | `title` + `answer` + `threads` + `unreadBySource` + `sources` |
| One thread (e.g. "draft a reply to Harry Datwani") | `title` + `answer` (paragraph) + `threads` with only that thread + `sources` — no tail |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for.
- **`threads`:** only Needs reply (deal, scheduling, support) and Couldn't draft threads, in step 4's priority order, at most 25. FYI, new inbound, sensitive and SFDC-logging items have no row: say what the prompt needs from them in `answer` (e.g. "2 new inbound – run `lead-triage`", "1 sensitive thread skipped"). `draft` is the reply step 5 drafted into the thread; a Couldn't draft row sends `note` (why, then the blocking question) instead.
- **`unreadBySource`** is step 1's three counts; `answer` can cite the total and how many need a reply. Always send it for a broad sweep.
- **Tail fork:** `callout` when one reply is time-sensitive and the user can act on it (one button, a first-person `actionMsg`); otherwise a `nextStep` line that says which drafts to send first; if nothing applies, neither. Never both (if both are sent only the callout renders). `callout` carries `level` — `tip` (helpful context), `note` (one clear move, the default) or `blocker` (time-sensitive or blocked), the lowest that fits.
- **Sources:** an Opportunity is `https://<myDomain>/lightning/r/Opportunity/<Id>/view`; add one source with no `url` for the mail read (e.g. "Email · unread, last 72 hours"). Omit `url` if you have no Id.
- Format every value as a ready-to-display string ("3 days"). Names are plain strings, never objects.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

The names, companies and wait times below (e.g. Harry Datwani, Deloitte, 3 days) are illustrative; fill every value from the threads you read.

**Broad — e.g. "Sweep my inbox"** (bulleted answer, both cards, a next-step line):

```json
{
  "title": "Three external threads need a reply; the rest is automated noise.",
  "answer": "- In the **last 72 hours** you have **37 unread**, but only **3 external threads** actually need you – the other 34 are internal or automated.\n- The live one is **Harry Datwani (Deloitte)**, whose pilot thread moved last night.\n- **Ben Ashkenazy (Redapt)** has a call invite sitting **3 days**, and **Ryan Powell (Accenture)** has waited **3 days** on a Chicago follow-up.\n- Replies for Deloitte and Redapt are drafted in-thread – expand a thread to review.",
  "threads": [
    {"name": "Harry Datwani", "company": "Deloitte", "subject": "Re: Pilot – Deloitte + Salesforce + Redapt", "opp": "Deloitte 1P Customer Pilot", "oppUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view", "context": "thread moved last night", "draft": "Harry – thanks for the confirmation last night. Katrina and I are aligned on adding Ben Ashkenazy from Redapt to the daily standup starting Wednesday. I'll get the meeting invite out by end of day today and share the pilot workspace link separately. Anything you want me to raise with Redapt before then?"},
    {"name": "Ben Ashkenazy", "company": "Redapt", "subject": "Call with Bryan (Salesforce)", "context": "meeting invite unanswered", "draft": "Ben – apologies for the slow reply; the call slipped my inbox last week. Happy to connect – would Thursday at 10:00 AM or Friday at 2:00 PM PT work for you?"},
    {"name": "Ryan Powell", "company": "Accenture", "subject": "Re: Chicago Follow-up", "context": "relationship, no active opportunity", "note": "No draft prepared – Ryan is asking what you agreed in Chicago, and that isn't in the thread or in Salesforce. What did you commit to at the Aug 14 meeting?"}
  ],
  "unreadBySource": {"external": 5, "internal": 8, "automated": 24},
  "nextStep": {"lead": "Review and send Harry Datwani's draft first.", "text": "It's grounded in last night's thread and keeps the Deloitte pilot moving. Then send the Redapt reply to clear the 3-day-old call invite, and answer Ryan's question so you can close out Accenture."},
  "sources": [
    {"label": "Opportunity · Deloitte 1P Customer Pilot", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"},
    {"label": "Email · unread, last 72 hours"}
  ]
}
```

**One thread — e.g. "Draft a reply to Harry Datwani"** (paragraph answer, that thread only, no tail):

```json
{
  "title": "Your reply to Harry Datwani is drafted in the Deloitte pilot thread.",
  "answer": "Harry confirmed last night that **Ben Ashkenazy (Redapt)** joins the daily standup from **Wednesday**. The draft confirms it, commits to the invite **by end of day today**, and asks what to raise with Redapt first.",
  "threads": [
    {"name": "Harry Datwani", "company": "Deloitte", "subject": "Re: Pilot – Deloitte + Salesforce + Redapt", "opp": "Deloitte 1P Customer Pilot", "oppUrl": "https://<myDomain>/lightning/r/Opportunity/<Id>/view", "context": "thread moved last night", "draft": "Harry – thanks for the confirmation last night. Katrina and I are aligned on adding Ben Ashkenazy from Redapt to the daily standup starting Wednesday. I'll get the meeting invite out by end of day today and share the pilot workspace link separately. Anything you want me to raise with Redapt before then?"}
  ],
  "sources": [
    {"label": "Opportunity · Deloitte 1P Customer Pilot", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"},
    {"label": "Email · Re: Pilot – Deloitte + Salesforce + Redapt"}
  ]
}
```


`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"); a broad sweep always sends `unreadBySource`:

```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, answer, then the optional cards (threads, unreadBySource), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. Format every value as a ready-to-display string (dates, counts); names are plain strings, never objects.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed label of the widget (card headings, legend words, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "needsReply": {
          "type": "string",
          "default": "EMAILS THAT NEED A REPLY",
          "description": "Heading of the threads card. English: 'EMAILS THAT NEED A REPLY'."
        },
        "draft": {
          "type": "string",
          "default": "DRAFT",
          "description": "Heading of the drafted-reply box inside a thread. English: 'DRAFT'."
        },
        "unreadBySource": {
          "type": "string",
          "default": "UNREAD EMAILS BY TYPE",
          "description": "Heading of the unread-by-type card. English: 'UNREAD EMAILS BY TYPE'."
        },
        "external": {
          "type": "string",
          "default": "external",
          "description": "Legend word after the external count, e.g. '5 external'. English: 'external'."
        },
        "internal": {
          "type": "string",
          "default": "internal",
          "description": "Legend word after the internal count, e.g. '8 internal'. English: 'internal'."
        },
        "automated": {
          "type": "string",
          "default": "automation / newsletter",
          "description": "Legend words after the automated count, e.g. '24 automation / newsletter'. English: 'automation / newsletter'."
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
      "description": "REQUIRED. One bold sentence that already answers the question: the takeaway and the key fact (e.g. 'Three external threads need a reply; the rest is automated noise.'). Never the skill name."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (counts, names, companies, wait times): 2-4 short '- ' bullets for a broad sweep, a short paragraph for a specific ask. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "threads": {
      "type": "array",
      "maxItems": 25,
      "description": "OPTIONAL card 'EMAILS THAT NEED A REPLY': one row per thread classified Needs reply (deal, scheduling, support) or Couldn't draft, in step 4's priority order. Each row expands to its drafted reply (or the note on why there is none); the first row opens expanded. Include for a broad sweep or when the prompt asks what needs a reply. Omit the key otherwise; never an empty array.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "name",
          "subject"
        ],
        "properties": {
          "name": {
            "type": "string",
            "description": "Sender's name (e.g. 'Harry Datwani'). Leads the row heading."
          },
          "company": {
            "type": "string",
            "description": "The matched Account's name, or the sender's company from the thread when there is no CRM match (e.g. 'Deloitte'). Leads the row's second line, before context."
          },
          "subject": {
            "type": "string",
            "description": "Email subject line, plain text (e.g. 'Re: Pilot – Deloitte + Salesforce + Redapt')."
          },
          "opp": {
            "type": "string",
            "description": "The matched open opportunity's name (e.g. 'Deloitte 1P Customer Pilot'). Omit when no opportunity matched."
          },
          "oppUrl": {
            "type": "string",
            "description": "Opportunity record URL https://<myDomain>/lightning/r/Opportunity/<Id>/view. Omit when there is no Id."
          },
          "context": {
            "type": "string",
            "description": "A few muted words on why the thread matters now (e.g. 'thread moved last night', 'meeting invite unanswered')."
          },
          "draft": {
            "type": "string",
            "description": "The full reply step 5 drafted into the email thread. Send it for every thread step 5 drafted (cap 10); omit it for Couldn't draft and for threads past the draft cap."
          },
          "note": {
            "type": "string",
            "description": "Couldn't draft only: why there is no draft, ending with the blocking question for the user. Rendered muted in place of the draft."
          }
        }
      }
    },
    "unreadBySource": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL card 'UNREAD EMAILS BY TYPE': one proportion bar of every unread email in the lookback, split external / internal / automated (step 1's all-unread count). Include for a broad sweep or when the prompt asks how much of the inbox is noise. Omit the key otherwise.",
      "required": [
        "external",
        "internal",
        "automated"
      ],
      "properties": {
        "external": {
          "type": "number",
          "description": "Unread emails from people outside your domain."
        },
        "internal": {
          "type": "number",
          "description": "Unread emails from people inside your domain."
        },
        "automated": {
          "type": "number",
          "description": "Unread newsletters, no-reply and other automated mail, from any domain."
        }
      }
    },
    "callout": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL tail, time-sensitive. A bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if one reply is time-sensitive (an explicit deadline, or a thread on an open opp closing within 30 days) AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
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
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button. Use INSTEAD of callout, never both.",
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead (the suggested move, e.g. 'Review and send Harry Datwani's draft first.')."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning: the order to clear the queue in, and why."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: the Salesforce records you actually read, linked, plus the mailbox you swept. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name: object · record (e.g. 'Opportunity · Deloitte 1P Customer Pilot', 'Email · unread, last 72 hours')."
          },
          "url": {
            "type": "string",
            "description": "Record URL https://<myDomain>/lightning/r/<SObjectType>/<Id>/view. Omit if none (e.g. the mailbox)."
          }
        }
      }
    }
  }
}
```


## 7. Output — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask (e.g. "draft a reply to Harry Datwani") gets only the lines that answer it, not every section below.

```
# Inbox Sweep — <N> customer emails (<lookback>)
## Drafted Replies (<N>)
| Pri | From | Account | Subject | Opp | Draft |
## FYI Only (<N>) — safe to archive
## New Inbound (<N>) — run lead-triage
## Couldn't Draft — need your input (<N>)  · <blocking question>
## Sensitive — skipped (<N>)  · <why>
## Flagged for Support (<N>)
## Suggested SFDC logging (via `log-activity`, or manually)
- <Account>: Log Activity "Inbound email — <subject>"
```

All replies are drafts — review and send from email.
