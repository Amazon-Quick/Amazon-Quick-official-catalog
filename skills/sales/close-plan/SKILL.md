---
name: close-plan
display_name: Close Plan
description: "Build a dated mutual action plan and customer-facing business case from Salesforce opportunity data plus transcripts, email, documents, and Slack, scoped to what was asked: whether the close date holds, the path to signature and who owns each step, or why buy and why now. Use to test the close date, map the path to signature, or quantify return."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:667d9e3092873529976305ad3a0a364d3ae0e694e01a765a3d7a879efe48b495"
id: "4197dd88-4d80-4851-8323-2be87085cd92"
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

- **Scope reading and output to the prompt, never a default full plan.** A broad ask ("build a close plan", "can we hit the date?") shows the progress meter and the steps; "how are we tracking?" shows only the progress; "what's left / who owns what" shows only the steps; "why buy / build the ROI" is the business case. Think in lego blocks: a broad ask shows every block that carries real signal; a specific ask shows only the block(s) it names; a direct question gets no blocks. Don't show something just because you fetched it.
- Resolve to ONE opportunity before the deep read. When the name is ambiguous, ask the user to pick — don't guess.

# Close Plan

Ground → read opp → gather evidence (all ONE turn) → draft business case + MAP.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists. Its fields reveal this org's real custom and lookup schema; don't assume object names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

From the result: (a) scalar `__c` fields (business-case data, why-now, ROI, etc.) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's Name. The standard contact-role child is hardcoded below.

## 2. Read opp + evidence (issue ALL in one turn)

`%DEALNAME%` = 1–2 words. Reference-field rules: scalar → `Field__c { value }`; related name → span via the exact `relationshipName`: `<relationshipName> { Name { value } }`. Only span relationships Step 1 returned. If no usable relationshipName, take the `__c { value }` (the Id) and move on.

Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed custom lookup relationship. Standard fields + `OpportunityContactRoles` always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } Description { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } <REL_BLOCKS> OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } } } } } } }\"}" })
```

Empty `edges` → broaden `%…%`.

**Evidence (in PARALLEL with step 2 — same turn):** Fire email/doc/Slack searches keyed on the deal/account name; these don't depend on the SF result. Use whatever tools are present; if none, skip silently.

- **Call transcripts / proposals:** customer's stated problems, success metrics, quantified pain, who said what.
- **Email:** commitments already made in writing, procurement/legal/security threads.
- **Slack:** internal deal-desk/exec mentions, concerns.
- **deal-advance-gap output** (if run this session): its known gaps feed the mutual action plan directly — don't re-derive them.

## 3. Draft business case

**Value prop, differentiators, required stakeholders for close, and internal approval chain are external knowledge — infer from the org's own data or ask the user once. Never invent it.**

In the customer's language, grounded in their own words (cite the call/email each point comes from):

1. **Current state and cost of it** - the problem as they described it, quantified where they gave numbers
2. **Desired outcome** - their success metrics, their timeline drivers (the why-now)
3. **Proposed solution** - what they're buying, mapped to each outcome
4. **Investment and return** - price vs. the quantified value; keep the math simple and attributable
5. **Risk of waiting** - what the delay costs in their terms
6. **Why us** - only differentiators they have actually reacted to

Flag every claim that has no customer evidence behind it — those are the points to validate on the next call, not assert in the doc.

## 4. Draft mutual action plan

Work backward from the target signature date (default: opportunity CloseDate) through both sides' steps: remaining validation, security review, legal redlines, procurement, signatures, plus any internal approvals the user mentions. Each row: step, owner (us / customer / named person), target date, status. Flag the steps whose dates make the CloseDate impossible.

## 5. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/close-plan", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings and status pills in upper case) and write every free-text field (`detail`, `side`, `doneLabel`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. A step's `status` picks its pill, rule and colour — never put colour words in the text. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.
- **Pick each step's `status` from its real state:** `notStarted` (not begun, including steps nobody has scheduled yet), `blocked` (cannot move until something else happens, or overdue and stuck), `inProgress` (underway or scheduled), `completed` (done). Put the reason in `detail` (e.g. "Blocked on CFO endorsement").
- **Always set `pace.tone`:** `error` (red) when the plan is behind pace or the date is at risk, `warning` (orange) only when it is tight but still on track, `success` (green) when on pace. A "behind by N days" label is always `error`.
- **Steps come from the plan you drafted in step 4,** sorted by due date and ending with the signature. `pace.done` / `pace.total` are counts of those same steps — compute them, never estimate.
- **Every step gets a `side`** (`Us`, `Them` or `Both`, in the user's language), decided from what the step is — never leave it blank.
- **Fill `owner` from data you read, not from guesswork:** the Opportunity `Owner.Name` for your side's steps, the `OpportunityContactRoles` contact whose role fits the step (e.g. the Economic Buyer for signature), or the person who committed to it in a call, email or Slack thread. Omit `owner` only when none of these names one.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| **Broad** ("build a close plan for X", "close plan", "can we still hit the date?", "where do we stand on closing X?") | `title` (the verdict on the date) + `answer` + `pace` + `steps` + `callout` if a step's date gates the close (else `nextStep`) + `sources` |
| **Specific: progress only** ("how are we tracking?", "are we behind?", "how far along is the plan?") | `title` + `answer` + **only** `pace` + tail only if it applies + `sources` |
| **Specific: the steps** ("what's left to sign?", "who owns what?", "what's blocking signature?") | `title` + `answer` + **only** `steps` + tail only if it applies + `sources` |
| **Direct question or the business case** ("when is the next step due?", "why buy / why now", "build the ROI story") | `title` + `answer` (the case in 2-4 bullets, each grounded in the customer's words) + `sources`; offer the full customer-facing doc (section 6). No cards |

#### Worked examples (the `props` object only)

**Close plan — "Build me a close plan for the Cedarline deal"** (pace + steps, the gating step as a callout):

```json
{
  "title": "You can still hit Aug 31 – but only if the CFO deck goes out today.",
  "answer": "- You're **1 of 6 steps done** with **8 days left** – behind pace by **3 days**.\n- The ROI deck to Priya Anand is **overdue** and the CFO 1:1 **isn't scheduled**.",
  "pace": { "done": 1, "total": 6, "tone": "error", "doneLabel": "**1 of 6** steps done", "paceLabel": "Behind by 3 days · **6 of 6** by 8/31" },
  "steps": [
    { "status": "notStarted", "step": "Send CFO ROI deck", "detail": "Re-packaged proposal to Priya Anand", "side": "Us", "owner": "Bryan Corcoran", "due": "Aug 24" },
    { "status": "notStarted", "step": "CFO 1:1 → Priya Anand", "detail": "30m to walk through the re-packaged model", "side": "Both", "owner": "Priya Anand", "due": "Aug 26" },
    { "status": "notStarted", "step": "Execute signatures – close", "detail": "Signatures + countersign", "side": "Them", "owner": "Priya Anand", "due": "Aug 31" }
  ],
  "callout": { "lead": "The CFO 1:1 by Aug 26 is the real deadline.", "text": "Procurement, legal and signature all wait on Priya's endorsement; miss it and the close slips to Q4.", "buttonLabel": "Draft the CFO ROI deck + 1:1 invite", "actionMsg": "Draft the re-packaged CFO ROI deck cover email to Priya Anand and a 1:1 invite for before Aug 26." },
  "sources": [{ "label": "Opportunity – Enterprise Sales Cloud Platform" }, { "label": "Call – Aug 20 pricing review" }]
}
```

**Specific — "What's left before Joja can sign?"** (steps only, a plain next step):

```json
{
  "title": "Two steps left before Joja signs, both on their side.",
  "answer": "- Security review is **in progress** with **Sam Ortiz**, due **Oct 24**.\n- The order form goes out once it clears; signature target is **Oct 31**.",
  "steps": [
    { "status": "inProgress", "step": "Security review sign-off", "side": "Them", "owner": "Sam Ortiz", "due": "Oct 24" },
    { "status": "notStarted", "step": "Execute signatures – close", "side": "Them", "owner": "Morgan Lee", "due": "Oct 31" }
  ],
  "nextStep": { "lead": "Confirm the security review date with Sam.", "text": "A one-line check-in keeps Oct 31 honest. Want me to draft it?" },
  "sources": [{ "label": "Opportunity – Joja Platform Upsell" }]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (pace, steps), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A pure business-case or single-fact question usually gets no cards. Format every value as a ready-to-display string (dates as 'Aug 24'); names are plain strings, never objects (use `Contact.Name.value` / `Owner.Name.value`).",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line: the verdict on the close date in the user's context, naming the one thing it hinges on (e.g. 'You can still hit Aug 31 – but only if the CFO deck goes out today.'). Plain text, no markdown. Never the skill name or 'Close Plan: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence, that answer ONLY what the user asked (pace vs. the date, which steps are red and why, what has to happen this week). Put **bold** inline on the key values inside each sentence (counts, days, dates, names, 'overdue'), never on a whole bullet. Do not restate every row of the steps card. No headings, tables or paragraphs."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, column headers, status pills, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "closePlanPace": {
          "type": "string",
          "default": "CLOSE PLAN PROGRESS",
          "description": "Heading of the progress card. English: 'CLOSE PLAN PROGRESS'."
        },
        "pathToSignature": {
          "type": "string",
          "default": "CLOSE PLAN STEPS",
          "description": "Heading of the steps card. English: 'CLOSE PLAN STEPS'."
        },
        "status": {
          "type": "string",
          "default": "STATUS",
          "description": "Steps column header. English: 'STATUS'."
        },
        "step": {
          "type": "string",
          "default": "STEP",
          "description": "Steps column header. English: 'STEP'."
        },
        "side": {
          "type": "string",
          "default": "SIDE",
          "description": "Steps column header. English: 'SIDE'."
        },
        "owner": {
          "type": "string",
          "default": "OWNER",
          "description": "Steps column header. English: 'OWNER'."
        },
        "due": {
          "type": "string",
          "default": "DUE DATE",
          "description": "Steps column header. English: 'DUE DATE'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        },
        "notStarted": {
          "type": "string",
          "default": "NOT STARTED",
          "description": "Status pill for a step with status 'notStarted'. English: 'NOT STARTED'."
        },
        "blocked": {
          "type": "string",
          "default": "BLOCKED",
          "description": "Status pill for a step with status 'blocked'. English: 'BLOCKED'."
        },
        "inProgress": {
          "type": "string",
          "default": "IN PROGRESS",
          "description": "Status pill for a step with status 'inProgress'. English: 'IN PROGRESS'."
        },
        "completed": {
          "type": "string",
          "default": "COMPLETED",
          "description": "Status pill for a step with status 'completed'. English: 'COMPLETED'."
        }
      }
    },
    "pace": {
      "type": "object",
      "description": "OPTIONAL card 'CLOSE PLAN PROGRESS': steps done vs. total on a bar, and whether the plan is ahead or behind. Include for a broad ask (a close plan, whether the date is realistic) and when the prompt asks how the deal is tracking. Omit when the prompt asks only about the steps, and for a pure business-case question.",
      "required": [
        "done",
        "total",
        "doneLabel"
      ],
      "properties": {
        "done": {
          "type": "number",
          "description": "Number of steps completed (fills the bar)."
        },
        "total": {
          "type": "number",
          "description": "Total number of steps in the plan (the bar's full length)."
        },
        "tone": {
          "type": "string",
          "enum": [
            "error",
            "warning",
            "success"
          ],
          "description": "Pace colour: error (red) = behind pace / the date is at risk, warning (orange) = tight, success (green) = on pace. Default warning.",
          "default": "warning"
        },
        "doneLabel": {
          "type": "string",
          "description": "Left caption under the bar, markdown, bold on the count (e.g. '**1 of 6** steps done'). Written whole in the user's language."
        },
        "paceLabel": {
          "type": "string",
          "description": "Right caption under the bar, markdown: the pace verdict and the landing (e.g. 'Behind by 3 days · **6 of 6** by 8/31'). Written whole in the user's language. Omit if unknown."
        }
      }
    },
    "steps": {
      "type": "array",
      "description": "OPTIONAL card 'CLOSE PLAN STEPS': the mutual action plan, one row per step, sorted by due date (earliest first), ending with the signature. Include for a broad ask (a close plan, path to signature) and when the prompt asks what's left / who owns what / what's blocking. Omit when the prompt asks only how the deal is tracking; never an empty array.",
      "items": {
        "type": "object",
        "required": [
          "step",
          "status",
          "side"
        ],
        "properties": {
          "status": {
            "type": "string",
            "enum": [
              "notStarted",
              "blocked",
              "inProgress",
              "completed"
            ],
            "description": "Drives the status pill and the left rule: notStarted (orange) = not begun yet, including steps not scheduled; blocked (red) = cannot move until something else happens, or overdue and stuck; inProgress (blue) = underway or scheduled; completed (green) = done."
          },
          "step": {
            "type": "string",
            "description": "Bold step name, short (e.g. 'Send CFO ROI deck', 'CFO 1:1 → Priya Anand')."
          },
          "detail": {
            "type": "string",
            "description": "Small muted line under the step: what it is or what it depends on (e.g. 'Blocked on CFO endorsement'). Omit if nothing useful."
          },
          "side": {
            "type": "string",
            "description": "REQUIRED on every step. Who carries the step, in the user's language: 'Us' (your team does it), 'Them' (the customer does it) or 'Both' (a joint step such as a meeting or a redline cycle). Decide it from what the step is; it is never unknown."
          },
          "owner": {
            "type": "string",
            "description": "Named owner (person). Resolve it from data you read: the Opportunity Owner for your side's steps, the OpportunityContactRoles contact whose role fits the step (e.g. the Economic Buyer for signature) or the person who committed to it in a call, email or Slack thread. Omit only if none of those names the step's owner; never invent one."
          },
          "due": {
            "type": "string",
            "description": "Target date, short (e.g. 'Aug 24')."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive: the real deadline. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if a step's date gates the close AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence: the gating date in one sentence, ending with a period (e.g. 'The CFO 1:1 by Aug 26 is the real deadline.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences of normal-weight text after the bold lead: what waits on it, what slipping costs, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Draft the CFO ROI deck + 1:1 invite')."
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
      "description": "REQUIRED. Where the plan came from: the Salesforce records you actually read, linked (this is where the Opportunity record link goes), plus any call/email/doc you cited. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Opportunity – Enterprise Sales Cloud Platform', 'Call – Aug 20 pricing review')."
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
# Close Plan: [Opp Name] - [Account]

## Business Case (customer-facing doc)

### Current State
[Problem as they described it, quantified where they gave numbers]

### Desired Outcome
[Their success metrics, their timeline drivers]

### Proposed Solution
[What they're buying, mapped to each outcome]

### Investment and Return
[Price vs. quantified value — simple math, attributable]

### Risk of Waiting
[What the delay costs in their terms]

### Why Us
[Only differentiators they reacted to]

**Claims to validate:** [Every claim with no customer evidence]

## Mutual Action Plan (shared table)

| Step | Owner | Target Date | Status |
|------|-------|-------------|--------|
| [Remaining validation] | [us/customer/name] | [date] | [status] |
| [Security review] | | | |
| [Legal redlines] | | | |
| [Procurement] | | | |
| [Signatures] | | | |
| [Internal approvals] | | | |

**Date conflicts:** [Steps whose dates make CloseDate impossible]

## Suggested SFDC updates
- NextStep → "[next dated step from the plan]"
- CloseDate → [if backward plan says current date not credible]
[Apply manually if read-only.]

## Draft email to champion
[Sharing the action plan and asking them to confirm owners on their side]
```

**Offer to create the artifacts as shareable documents** if a docs connector is present (capability call, not an SF read — skip silently if absent): the business case as a customer-facing doc, and the mutual action plan as a co-ownable table. Degrade to the inline markdown above when no docs tool is available.
