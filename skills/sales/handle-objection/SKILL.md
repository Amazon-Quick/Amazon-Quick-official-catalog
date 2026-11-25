---
name: handle-objection
display_name: Handle Objection (Preview)
description: "Build a grounded response to a customer objection from the current deal, win-loss history, customer evidence and approved internal documents, scoped to what was asked: what is really being said, the ways to respond, or the proof points to use. Use when interpreting pricing, timing, trust or competitive pushback and preparing a talk track or written reply."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:711ea318b014a1ae520e04b21756754cc9318961ab66959af795e9e10e59dad1"
id: "094d821d-0d2d-43e1-b1a6-0427fabf6110"
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

- **Scope reading and output to the prompt, never a default full response.** A broad ask (a live objection) shows the ways to respond and the supporting points; "how do I respond?" shows only the ways to respond; "what proof do I have?" shows only the supporting points; "what are they really saying?" gets the read, no cards. Think in lego blocks: a broad ask shows every block that carries real signal; a specific ask shows only the block(s) it names; a direct question gets no blocks. Don't show something just because you fetched it.
- Resolve to ONE deal before the deep read. When the name is ambiguous, ask the user to pick — don't guess.

# Handle Objection

A grounded response, not a script: what the objection means, how deals like it went, and your own customers' evidence that answers it. Inputs: **the objection** (their words / email / transcript) and **the deal** (opp for context). Common objections/competitors/differentiators are external — infer from org data or ask once; never invent. **Read-only:** this skill never writes to Salesforce; drafting remains delegated to `draft-outreach`.

## 1. Classify what's really being said

Map to type: price/value · timing/priority · competitive · risk/trust · authority ("check with…") · status quo. Distinguish an **objection** (reason not to buy) from a **negotiation move** (reason to buy cheaper) — the response differs.

## 2. Pull direct evidence first

Use only a selected Opportunity as the deal. After exactly one Opportunity is selected (a current-turn Opportunity Id with prefix `006`, or a candidate the user picked after disambiguation) and read by exact Id, search only for direct, customer-specific evidence of this objection: the user's supplied source, an attributable customer email/transcript/note, or returned `Description` text or a document that explicitly records the customer's words, reason, goal, or metric for this deal. Candidate lists and literal deal context are identification/context only. A user paraphrase such as "the customer says it is too expensive" establishes the objection text but is not direct evidence of the reason, speaker, channel, approver, or intended recipient. Stage, Amount, Probability, Close Date, Next Step, Closed Won/Lost, owner, Contact title/role, account association, activity subject, and amount/outcome correlation never qualify as direct evidence.

### No direct evidence found

Stop evidence collection. Do not invoke or use `win-loss-review`, do not gather account-wide opportunities, contacts, or activities to fill the gap, and ignore any such data already returned. Do not infer history, causation, thresholds, stakeholders, buying authority, implementation, or recommendations from CRM context. Go directly to the no-direct-evidence response in step 3.

### Direct evidence found

Only after at least one qualifying source is found, gather the source evidence in parallel and use only claims that the returned source states directly:

- **Win/loss** (`win-loss-review`): only dated, attributable evidence that explicitly documents this objection, why the deal ended, or what action changed the outcome; amount/outcome patterns alone are unusable.
- **Customer voice** (`customer-voice`): verbatim quotes speaking to this exact concern.
- **Docs**: case studies, ROI, security/compliance already cleared for external use.
- **The deal itself**: explicit customer-stated pain, goals, or metrics for this deal.

Every dynamic claim must carry its inline source or Salesforce record link and exact supporting field/date. Closed Won/Lost, Next Step, amounts, stages, contact titles, and correlations retain only their literal meanings and cannot support causal or prescriptive language. If a required claim has no direct source, omit it.

## 3. Build the response

**Selected-deal gate:** Neither response template below is available until exactly one Opportunity has been selected (a current-turn `006` Id, or a candidate the user picked after disambiguation) and read by exact Id. If the deal is unresolved (zero, multiple, or truncated candidates, or no detail row), output only the clarification or partial-list question and stop. Do not classify the objection, search for objection evidence, or emit even the no-direct-evidence response from the user's paraphrase alone.

### No-direct-evidence response

When step 2 finds no qualifying source, use exactly this section structure and meaning, substituting only the user's objection wording. Do not add CRM facts, people, history, proof, recommendations, closing offers, or suggested actions.

```
# Objection: "<user-provided wording>" (user-provided paraphrase)
## What's underneath it
This is a price/value objection. The underlying reason and whether it is an objection or a negotiation move are not established.
## The response
"I hear you. When you say the price is too high, is the concern the available budget or whether the expected value supports the investment? What would you need to see or change to decide?"
## Proof points to have ready
No directly documented customer proof point for this objection was found.
## What history says
No directly documented win/loss history explains this objection; amount/outcome patterns were not used.
## Don't
- Don't infer a reason, threshold, approver, recipient, loss cause, or recommended concession from CRM amounts, outcomes, stages, contacts, activities, or Next Step text.
```

End immediately after `Don't`. Do not add a next-step menu, follow-up offer, question, button, CTA, or action.

### Direct-evidence response

Use only after the evidence gate passes. Use the response shape below, and cite each claim beside the sentence or bullet it supports; a general caveat does not cure an unsupported claim.

Draft the response from the evidence, then size it to the prompt (see the scope table in section 5):

1. **What's underneath it** — the real concern; objection vs negotiation move.
2. **Ways to respond** — 2-3 plays, best first: acknowledge → answer with their own stated goals → question that moves it forward. Mark the one you would lead with.
3. **Proof points** — customer quote / case study / metric, each with its source.
4. **If it's a competitor** — where they're strong (be honest) and where this customer's needs don't match it.
5. **What history says** and **what not to do** — from win/loss: what winning reps did next; the response that historically loses (overdiscounting, feature-dumping, arguing).

Objection arrived in writing? Offer to draft the reply via `draft-outreach`.

## 5. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/handle-objection", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings and the badge in upper case) and write every free-text field (`headline`, `detail`, `evidence`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, badges, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. `recommended: true` on a play picks its badge — never write "recommended" into the text. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.
- **Plays and proof come from your own evidence in step 2,** never invented: every supporting point names its source, and a play leans on what this customer already told you. Mark at most one play `recommended`.
- **Scope reading and output to the prompt** (see the table below): answer what the user asked about, not a default full response.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| **Broad** (a live objection: "they said we're too expensive", "how do I handle…", a pasted email) | `title` (the reframe) + `answer` (what's underneath it, objection vs negotiation move) + `plays` + `supportingPoints` + `callout` if there is a dated trigger the user can act on (else `nextStep`) + `sources` |
| **Specific: the read** ("what are they really saying?", "is this a real objection or a negotiating move?") | `title` + `answer` + `nextStep` only if useful + `sources`. No cards |
| **Specific: the response** ("how should I respond?", "what's my play?") | `title` + `answer` + **only** `plays` + tail only if it applies + `sources` |
| **Specific: the proof** ("what evidence do I have?", "any customer quotes on this?") | `title` + `answer` + **only** `supportingPoints` + `sources` |
| **Competitor in the deal** ("[competitor] is in the deal") | `title` + `answer` (where they're strong, where this customer's needs don't match) + `plays` + `supportingPoints` + `sources` |

#### Worked examples (the `props` object only)

**Live objection — "Priya says the budget is frozen and mentioned Vaultline"** (plays, proof, a dated escalation callout):

```json
{
  "title": "The pilot already proved value – this is a structuring conversation, not a re-evaluation.",
  "answer": "- Priya's email is **both** a genuine CFO concern (board-level budget freeze) **and** a negotiation move – procurement introduced Vaultline 3 weeks ago to create leverage.\n- The pilot closed at $75K – they've **already voted yes on the technology**.\n- Don't re-sell – restructure.",
  "plays": [
    { "headline": "ROI reframe – anchor to the pilot, use her own delay-cost model", "recommended": true, "detail": "Acknowledge the budget reality, then walk back to the pilot she validated. Anchor on **her own $600K/quarter delay-cost**." },
    { "headline": "Phased structure – split the deal across her budget cycles", "detail": "**Phase 1 $300K now, Phase 2 $340K in Q4** – keeps the full $640K in play instead of discounting to $500K." }
  ],
  "supportingPoints": [
    { "headline": "The pilot itself – 47% pipeline lift, $2.4M efficiency", "evidence": "Q2 pilot dashboard · Cedarline's own numbers · Priya's team validated the model 5/18." },
    { "headline": "Phased-deal structure pre-approved by Legal", "evidence": "Y2/Y3 escalators at 4% cleared 8/20 · pricing team OK'd the $300K + $340K split for FS accounts." }
  ],
  "callout": { "lead": "No response by Aug 27 → escalate to an exec-sponsor path.", "text": "Three weeks of no engagement plus a competitor introduced is a deal going Inactive. Lead with the ROI reframe, not a discount.", "buttonLabel": "Draft the reframe email", "actionMsg": "Draft the ROI reframe email to Priya Anand anchored on the pilot results and her own $600K/quarter delay-cost model." },
  "sources": [{ "label": "Opportunity – Cedarline Financial Platform Expansion" }, { "label": "Email – Priya Anand, Aug 6" }]
}
```

**Specific — "Is this a real objection or a negotiating move?"** (the read only, a plain next step):

```json
{
  "title": "Treat it as a negotiating move – the technology is already approved.",
  "answer": "- The pilot closed at **$75K** and the champion is still engaged.\n- The price pushback arrived **the same week** procurement added a competitor.",
  "nextStep": { "lead": "Test it with one question.", "text": "Ask Priya what budget cycle the deal would need to land in. Want me to draft it?" },
  "sources": [{ "label": "Opportunity – Cedarline Financial Platform Expansion" }]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (plays, supportingPoints), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A pure 'what is really being said' question usually gets no cards. Format every value as a ready-to-display string (currency, dates); names are plain strings, never objects (use `Contact.Name.value` / `Owner.Name.value`).",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line: the reframe or verdict that already answers the question in the user's context (e.g. 'The pilot already proved value – this is a structuring conversation, not a re-evaluation.'). Plain text, no markdown. Never the skill name or 'Handle Objection: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence, that say what is really being said (objection vs negotiation move), what the customer already told you, and the stance to take. Put **bold** inline on the key values inside each sentence (amounts, dates, names), never on a whole bullet. Do not restate the cards below it. Answer ONLY what was asked (scope the bullets to the prompt); no headings, tables or paragraphs."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, the recommended badge, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "waysToRespond": {
          "type": "string",
          "default": "WAYS TO RESPOND",
          "description": "Heading of the plays card. English: 'WAYS TO RESPOND'."
        },
        "recommended": {
          "type": "string",
          "default": "RECOMMENDED",
          "description": "Badge on the play marked `recommended`. English: 'RECOMMENDED'."
        },
        "supportingPoints": {
          "type": "string",
          "default": "SUPPORTING POINTS",
          "description": "Heading of the supporting-points card. English: 'SUPPORTING POINTS'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "plays": {
      "type": "array",
      "description": "OPTIONAL card 'WAYS TO RESPOND'. Include ONLY if the prompt asks how to respond / what to say / how to handle the objection. 2-3 plays, best first. Omit the key otherwise; never send an empty array.",
      "items": {
        "type": "object",
        "required": [
          "headline"
        ],
        "properties": {
          "headline": {
            "type": "string",
            "description": "The bold name of the play, with its angle after an en dash (e.g. 'ROI reframe – anchor to the pilot, use her own delay-cost model'). Plain text."
          },
          "recommended": {
            "type": "boolean",
            "description": "true on at most ONE play, the one you would lead with; shows a green RECOMMENDED badge next to the headline. Omit on the others."
          },
          "detail": {
            "type": "string",
            "description": "Muted line below the headline: how to run the play, one or two sentences. Markdown: put **bold** on the key facts (amounts, the customer's own numbers)."
          }
        }
      }
    },
    "supportingPoints": {
      "type": "array",
      "description": "OPTIONAL card 'SUPPORTING POINTS'. Include ONLY if the prompt asks for proof/evidence/ammunition, or you are building a full response and have real evidence from the deal, win/loss history, customer quotes or approved documents. Every row needs a source. Omit the key otherwise; never send an empty array.",
      "items": {
        "type": "object",
        "required": [
          "headline"
        ],
        "properties": {
          "headline": {
            "type": "string",
            "description": "The bold proof point with its key number (e.g. 'The pilot itself – 47% pipeline lift, $2.4M efficiency'). Plain text."
          },
          "evidence": {
            "type": "string",
            "description": "Muted line below: where it comes from and why it persuades (e.g. 'Q2 pilot dashboard · Cedarline's own numbers · Priya's team validated the model 5/18.')."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive: a deadline or escalation trigger. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if there is a dated trigger AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence: the trigger and the move in one sentence, ending with a period (e.g. 'No response by Aug 27 → escalate to an exec-sponsor path.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences of normal-weight text after the bold lead: why it matters and what to lead with."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Draft the reframe email')."
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
      "description": "REQUIRED. Where the response came from: the Salesforce records you actually read, linked (this is where the Opportunity record link goes), plus any win/loss analysis, customer quote, email or doc you cited. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Opportunity – Enterprise Sales Cloud Platform', 'Email – Priya Anand, Aug 6')."
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

```
# Objection: "<their words>"
## What's underneath it
<1–2 sentences: the real concern; objection vs negotiation>
## The response
<talk track in your voice, 3–5 sentences: acknowledge → answer with their own stated goals + one proof point → question that moves it forward>
## Proof points to have ready
- <customer quote / case study / metric — with source>
## If it's <competitor>
- Where they're strong (be honest) + where this customer's needs don't match it; the trap question that surfaces the difference
## What history says
<from win/loss: how often this objection appears in wins vs losses, and what winning reps did next>
## Don't
- <the response that historically loses this — overdiscounting, feature-dumping, arguing>
```
