---
name: salesforce-hygiene-check
display_name: Salesforce Hygiene Check (Preview)
description: "Audit open Salesforce opportunities for past-due close dates and opportunities with no logged activity in 14+ days, scoped to what was asked: a full hygiene check, just the overdue opportunities, or just the stale ones, with a suggested fix for each. Use to check pipeline data quality or plan CRM cleanup before a forecast review, without changing records."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:cf5375d2d596cd1a0a00c4361a08006db55b2728e811f65b7fac7582bd58c648"
id: "b2a132bc-a85b-42a6-8333-015564ce2cba"
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
# Goal:
Answer what the user asked about their pipeline's hygiene (which open opportunities are past their close date, which have had no logged activity in 14+ days, and the fix for each) in one pass. **Answer what the user asked about** and present only that: a full check ("run a hygiene check on my pipeline") shows both; a specific ask ("which deals are past their close date?", "which deals have gone quiet?") shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full check.** Don't show something just because you fetched it.
- **The checks follow the rules in step 3, never a guess:** the same fields always put an opportunity in the same table.


# Salesforce Hygiene Check

Read-only audit of open opps → fix checklist you apply yourself (nothing is written). Ground → one read → run checks → output.

## 1. Ground (hardcoded — Opportunity only)

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's `__c` hygiene fields (competitor, required-per-stage, next-step trackers) — use exact names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

## 2. Read the open book (one call, scope: MINE)

`scope: MINE` = running user's book (no user lookup). Splice confirmed `__c` fields into `<OPP_CUSTOM>`. **Check `{` vs `}` balance before dispatching** — splicing custom fields is where a brace drops.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 200) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } CreatedDate { value } Type { value } LeadSource { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Role { value } Contact { Name { value } } } } } } } } } } }\"}" })
```

`InvalidSyntax` / "offending token `<EOF>`" → missing a closing `}`; add it and retry.

**Deterministic hygiene:** Apply Step 3's activity threshold as strictly more than 14 days; worked examples do not supply runtime thresholds, formulas, or severity. Without separately returned history or formulas, omit unchanged-field, stage-age, median-cycle, and stage-criteria claims. For exclusive hygiene state, use Critical for an objectively past CloseDate or Amount exactly zero; otherwise use Needs attention for blank Amount, blank NextStep, activity older than 14 days, no returned Contact Role, or one returned Contact Role. Critical takes precedence, and Clean means no supported flag. Call one returned role `one returned Contact Role`, not complete single-threading, unless connection completeness is established. Count every issue independently, but include each flagged Opportunity once; retain secondary issues in its fix text. Label the Amount sum `flagged pipeline Amount`, never `at risk`, unless a returned risk field or explicit formula supports that term.

## 3. Run checks (per opp)

Two checks, from fields you already read (today = the run date):
- **Overdue** — `CloseDate` is before today.
- **Stale** — `LastActivityDate` is blank or more than 14 days ago. A blank value means nothing was ever logged: show it as "No activity logged".

On a full check, first match wins, so an opportunity lands in at most one table. On a narrow ask, apply only the asked rule to every open opportunity.

Everything else is clean. A $0 or blank Amount on a flagged opportunity goes into its suggested fix (step 4), not a separate check.

## 4. Suggest values (cite real names — never generic "champion")

Per flagged opp, one suggested fix: **Overdue** — reset the `CloseDate` to a realistic date for its stage; on a $0 or blank Amount, add the Amount or close it as lost · **Stale** — a fresh, dated Next Step naming a real contact only if you read one.

## 5. Widget (default output when `display_widget` is present: AWS Quick)

**Widget transport:** Pass the fully hydrated renderer to `display_widget` as a direct top-level tool call whose `widgetDefinition` is a native JSON object. Never serialize or quote it, and never build or send it through generated code, a shell, a code runner, or temporary files. A returned string, printed preview, or generated file is not a mounted visual and is never a successful render. If the call succeeds, it is the terminal output: stop with no further assistant text. If it returns an error or the tool is unavailable, do not retry, repair, or create a substitute artifact; emit only the section 6 text fallback and stop, and never claim the widget rendered.
- ❌ WRONG: `widgetDefinition: "{\"key\":...}"` (stringified with escaped quotes)
- ✅ RIGHT: `widgetDefinition: {"key":...}` (native object, no quotes around the opening brace)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/salesforce-hygiene-check", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`close`, `lastUpdated`, `next`, `lead`, `text`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| A full check ("run a hygiene check on my pipeline", "what needs cleaning up before my forecast call?") | `title` + `answer` (one bullet per card) + `overdue` + `stale` + tail only if it applies + `sources` |
| Overdue only ("which deals are past their close date?") | `title` + `answer` + **only** `overdue` + tail only if it applies + `sources` |
| Stale only ("which deals have gone quiet?", "which deals look stalled?") | `title` + `answer` + **only** `stale` + tail only if it applies + `sources` |
| Missing amounts, blank Next Steps, stuck stages | Not covered here — say so and point to `deal-review` |
| Contacts or single-threading | Not covered here — say so and point to `stakeholder-map` |
| A team or manager ask ("hygiene on my team") | Not covered here — say so and point to `team-pipeline` |
| Anything else about one deal ("is this deal real?") | Not covered here — say so and point to `deal-review` |
| A question with a direct answer ("how many of my opps are past their close date?") | `title` + `answer` (paragraph) + `sources` — no card, no tail |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for. A check that finds nothing is said in `answer`, not sent as an empty card.
- **`overdue` / `stale`:** the opportunities from step 3, each with its suggested fix from step 4 in `next`. `account` is the bold line and `name` the opportunity under it. `close` and `lastUpdated` are relative to today ("6 weeks ago"), never ISO; `lastUpdated` is "No activity logged" when `LastActivityDate` is blank.
- **Tail fork:** `callout` when overdue opportunities are still counted in the open pipeline and the user can fix them now (one button, a first-person `actionMsg` that asks to see the changes before anything is written). Otherwise a `nextStep` line (e.g. refresh the Next Steps on the stale deals; `lead` is optional); if nothing applies, neither. A narrow ask usually gets no tail. Never both (if both are sent only the callout renders).
- **Nothing is written from this turn.** The callout button posts its `actionMsg` to chat; each change then goes through its confirm step.
- **Sources:** the open pipeline is `https://<myDomain>/lightning/o/Opportunity/list`; a record is `https://<myDomain>/lightning/r/Opportunity/<Id>/view`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string ("$640K", "6 weeks ago"). Names are plain strings, never objects. Never send a color.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

The names, amounts and dates below (e.g. Cedarline, $640K, 6 weeks ago) are illustrative; fill every value from the pipeline you read.

**Full check — e.g. "Run a hygiene check on my pipeline"** (both cards and a callout):

```json
{
  "title": "8 of your 11 open opportunities have a hygiene issue that distorts your forecast.",
  "answer": "- **3 opportunities ($1.03M) have a Close Date already in the past** with no updated Next Step, so they still sit in your open pipeline and overstate it.\n- **5 opportunities ($1.34M) have had no logged activity in over 14 days** – flagged as stalled on the manager report.",
  "overdue": [
    {"account": "Cedarline Financial", "name": "Enterprise Sales Cloud Platform", "amount": "$640K", "close": "6 weeks ago", "stage": "Negotiation / Review", "next": "Reset Close Date to Dec 15; confirm signature timeline with Priya Anand."},
    {"account": "Brightwave Media", "name": "Ad Sales Cloud + CPQ", "amount": "$410K", "close": "7 weeks ago", "stage": "Negotiation / Review", "next": "Push Close Date out one cycle; send updated quote for CMO sign-off."},
    {"account": "Vantage Retail Group", "name": "Loyalty", "amount": "$0", "close": "8 weeks ago", "stage": "Discovery", "next": "Add an Amount or close as lost – a $0 Discovery deal past close is stale."}
  ],
  "stale": [
    {"account": "Cascade Energy", "name": "Data Cloud + Tableau", "amount": "$530K", "lastUpdated": "8 weeks ago", "stage": "Proposal / Price Quote", "next": "Follow up on the proposal; confirm budget owner and decision date."},
    {"account": "Orion Manufacturing", "name": "Renewal + Sales Cloud", "amount": "$230K", "lastUpdated": "8 weeks ago", "stage": "Value Proposition", "next": "Book the QBR with Susan Kessler to re-establish the business case."}
  ],
  "callout": {"lead": "$1.03M across 3 opportunities has a Close Date in the past but is still counted in your open pipeline.", "text": "Until each Close Date is corrected and a current Next Step is set, these distort the forecast your manager pulls – fix them before the next review. I can set each Close Date to its next realistic date and draft a fresh Next Step for you to approve.", "buttonLabel": "Fix the 3 past-due Close Dates", "actionMsg": "Set each of my 3 past-due Close Dates to its next realistic date and draft a fresh Next Step for each – show me the changes to approve first."},
  "sources": [
    {"label": "Opportunities · open pipeline", "url": "https://<myDomain>/lightning/o/Opportunity/list"},
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"}
  ]
}
```

**Stale only — e.g. "Which deals have gone quiet?"** (only the stale card and a plain next step):

```json
{
  "title": "5 of your open opportunities have had no logged activity in over 14 days.",
  "answer": "**$1.34M** has had no logged activity in over 14 days and reads as stalled on your manager's report – the oldest is **Northpeak Logistics** at 10 weeks.",
  "stale": [
    {"account": "Cascade Energy", "name": "Data Cloud + Tableau", "amount": "$530K", "lastUpdated": "8 weeks ago", "stage": "Proposal / Price Quote", "next": "Follow up on the proposal; confirm budget owner and decision date."},
    {"account": "Northpeak Logistics – Portal", "name": "Customer Portal", "amount": "$90K", "lastUpdated": "10 weeks ago", "stage": "Needs Analysis", "next": "Confirm the project is still active; set a discovery call."}
  ],
  "nextStep": {"lead": "Refresh the five stale Next Steps.", "text": "Each draft above is a suggestion. Want me to apply them for you to approve one by one?"},
  "sources": [{"label": "Opportunities · open pipeline", "url": "https://<myDomain>/lightning/o/Opportunity/list"}]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, answer, then the optional cards (overdue, stale), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. Format every value as a ready-to-display string (amounts, relative dates); names are plain strings, never objects. Never send a color.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed label of the widget (card headings, the stale card's note, table headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "overdue": {
          "type": "string",
          "default": "OVERDUE OPPORTUNITIES",
          "description": "Heading of the overdue card. English: 'OVERDUE OPPORTUNITIES'."
        },
        "stale": {
          "type": "string",
          "default": "STALE OPPORTUNITIES",
          "description": "Heading of the stale card. English: 'STALE OPPORTUNITIES'."
        },
        "staleNote": {
          "type": "string",
          "default": "No logged activity in 14+ days reads as a stalled deal on your manager's report. Each one below needs a fresh, dated action for you to approve.",
          "description": "Muted note under the stale card's heading. English: 'No logged activity in 14+ days reads as a stalled deal on your manager's report. Each one below needs a fresh, dated action for you to approve.'"
        },
        "colOpportunity": {
          "type": "string",
          "default": "Opportunity Name",
          "description": "Table header (both cards). English: 'Opportunity Name'."
        },
        "colAmount": {
          "type": "string",
          "default": "Amount",
          "description": "Table header (both cards). English: 'Amount'."
        },
        "colClose": {
          "type": "string",
          "default": "Close Date",
          "description": "Overdue table header. English: 'Close Date'."
        },
        "colLastUpdated": {
          "type": "string",
          "default": "Last Activity",
          "description": "Stale table header. English: 'Last Activity'."
        },
        "colStage": {
          "type": "string",
          "default": "Stage",
          "description": "Table header (both cards). English: 'Stage'."
        },
        "colNextStep": {
          "type": "string",
          "default": "Suggested Action",
          "description": "Table header (both cards) for the suggested fix column. English: 'Suggested Action'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "title": {
      "type": "string",
      "description": "REQUIRED. The hygiene takeaway, one bold sentence that already answers the question (e.g. '8 of your 11 open opportunities have a hygiene issue that distorts your forecast.'). Never the skill name."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (counts, amounts, the 14-day rule). A broad ask gets one short '- ' bullet per card you send (e.g. '- **3 opportunities ($1.03M) have a Close Date already in the past** with no updated Next Step, so they still sit in your open pipeline and overstate it.'); a direct question ('how many of my opps are past their close date?') gets a 1-3 sentence paragraph. Answer ONLY what the user asked; do not restate the rows of the cards below it."
    },
    "overdue": {
      "type": "array",
      "description": "OPTIONAL card 'OVERDUE OPPORTUNITIES': open opportunities whose Close Date is already in the past. Include ONLY for a full hygiene check or if the prompt asks about past-due / overdue close dates. Omit the key otherwise. Oldest close date first; never an empty array.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "account",
          "amount",
          "close",
          "next"
        ],
        "properties": {
          "account": {
            "type": "string",
            "description": "Account name, the bold line (e.g. 'Cedarline Financial')."
          },
          "name": {
            "type": "string",
            "description": "Opportunity name, the muted line under the account (e.g. 'Enterprise Sales Cloud Platform')."
          },
          "amount": {
            "type": "string",
            "description": "Pre-formatted amount (e.g. '$640K'); '$0' when the Amount is blank or zero."
          },
          "close": {
            "type": "string",
            "description": "How long ago the Close Date passed, relative to today (e.g. '6 weeks ago', '5 days ago'). Never ISO."
          },
          "stage": {
            "type": "string",
            "description": "Stage display value (e.g. 'Negotiation / Review')."
          },
          "next": {
            "type": "string",
            "description": "The suggested fix in one or two sentences, citing real contact names (e.g. 'Reset Close Date to Dec 15; confirm signature timeline with Priya Anand.')."
          }
        }
      }
    },
    "stale": {
      "type": "array",
      "description": "OPTIONAL card 'STALE OPPORTUNITIES': open opportunities, not already in overdue, whose last logged activity is blank or more than 14 days ago (on a full check, not already in overdue; a narrow ask includes every match). Include ONLY for a full hygiene check or if the prompt asks about stale / stalled / quiet deals. Omit the key otherwise. Oldest activity first; never an empty array.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "account",
          "amount",
          "lastUpdated",
          "next"
        ],
        "properties": {
          "account": {
            "type": "string",
            "description": "Account name, the bold line (e.g. 'Cascade Energy')."
          },
          "name": {
            "type": "string",
            "description": "Opportunity name, the muted line under the account (e.g. 'Data Cloud + Tableau')."
          },
          "amount": {
            "type": "string",
            "description": "Pre-formatted amount (e.g. '$530K')."
          },
          "lastUpdated": {
            "type": "string",
            "description": "How long ago the last activity was logged, relative to today (e.g. '8 weeks ago'), or 'No activity logged' when there is none. Never ISO."
          },
          "stage": {
            "type": "string",
            "description": "Stage display value (e.g. 'Proposal / Price Quote')."
          },
          "next": {
            "type": "string",
            "description": "A fresh, dated Next Step, one or two sentences, naming a real contact only if you read one (e.g. 'Book the QBR with Susan Kessler to re-establish the business case.')."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if overdue opportunities are still counted in the open pipeline AND the user can fix them now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period, e.g. '$1.03M across 3 opportunities has a Close Date in the past but is still counted in your open pipeline.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the fix you can apply (e.g. 'Until each Close Date is corrected and a current Next Step is set, these distort the forecast your manager pulls – fix them before the next review. I can set each Close Date to its next realistic date and draft a fresh Next Step for you to approve.')."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Fix the 3 past-due Close Dates')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked (e.g. 'Set each of my 3 past-due Close Dates to its next realistic date and draft a fresh Next Step for each – show me the changes to approve first.')."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button. Use INSTEAD of callout, never both.",
      "required": [
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Optional bold lead (the suggested move, e.g. 'Refresh the five stale Next Steps.'). Omit to show the text alone."
        },
        "text": {
          "type": "string",
          "description": "One to three sentences of reasoning, ending with an offer to help if natural."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: the Salesforce records/lists you actually read, linked (this is where Opportunity record links go). Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name: object · record or list (e.g. 'Opportunities · open pipeline', 'Opportunity · Cedarline Financial')."
          },
          "url": {
            "type": "string",
            "description": "Record URL https://<myDomain>/lightning/r/Opportunity/<Id>/view, or for a list https://<myDomain>/lightning/o/Opportunity/list. Omit if you have no Id."
          }
        }
      }
    }
  }
}
```


## 6. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask gets only the table that answers it; a direct question gets only the answer lines. Validate counts: overdue + stale + clean = total open.

```
**<title — the hygiene takeaway in one sentence>**
- <one bullet per table you show, with the count and amount in bold>

## Overdue opportunities
| Opportunity | Amount | Close Date | Stage | Suggested Action |
|---|---|---|---|---|
| **<Account>** — <Opp> | <Amount> | <N weeks ago> | <Stage> | <suggested fix> |

## Stale opportunities (no logged activity in 14+ days)
| Opportunity | Amount | Last Activity | Stage | Suggested Action |
|---|---|---|---|---|
| **<Account>** — <Opp> | <Amount> | <N weeks ago> | <Stage> | <fresh Next Step> |

> ⚠️ **<the caution in one sentence>** <what to fix and the offer to apply it>

Sources: <Opportunity list / records you read, linked>
```

Recommendations only — apply manually on a read-only connector.
