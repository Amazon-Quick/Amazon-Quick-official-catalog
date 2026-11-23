---
name: deal-slip-scenario
display_name: Deal Slip Scenario
description: "Answer which deals are slipping and what a slip costs, scoped to what was asked: which open deals are at risk of slipping and why, how much of the pipeline is at risk, or what happens to the number if a deal slips, shrinks or is lost, from Salesforce pipeline and forecast data plus an available quota, including the gap and substitutes."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:d046fe4f3d794eaf3628b4918bc977cec78ec34512dba11e832b4074b5f0628f"
id: "15ffc699-e5ea-4d21-a310-6cdc45c1a51f"
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

# Deal Slip Scenario

# Goal:
Answer what the user asked about slipping deals (which deals are at risk of slipping and why, how much of the pipeline is at risk, or what a named deal slipping, shrinking or being lost does to the number) in one pass. **Read only what the question needs** and present only that: a review ("which of my deals are slipping, and why?") reads and shows the whole picture; a specific ask ("what if Cedarline slips?", "how much of my pipeline is at risk?") reads and shows only that.


# Rules:

- **Scope reading and output to the prompt, never a default full review.** Skip reads the question doesn't need (each read step says which), and don't show something just because you fetched it.
- **Slip risk follows the rules in step 3, never a guess:** the same fields always give the same HIGH / MEDIUM / on-track call.


# Deal Slip Scenario

Ground → read baseline → apply scenario → output. **No per-opp follow-ups** — the opp reads have the data.

## 1. Ground (hardcoded — Opportunity only)

Ground **Opportunity** (for pipeline fields). Always exists. One call:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

**If it overflows** or comes back truncated, skip custom-field grounding and proceed with standard fields only; don't keep retrying.

From the result, select relevant Opportunity `__c` fields by API name and label (risk, timing, health, etc.) and take their `{ value }`. The `Account` and `Owner` relationships below are standard and hardcoded.

## 2. Read baseline (templated, one turn)

Fire these as tool calls in **one turn** (independent). Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields (risk, health, timing signals, etc.).

**Date filters take a `DateInput` object, never a bare string** (`gte: \"2026-07-01\"` fails `WrongType … must be an object type`). For the current-quarter bounds below, use the exact-date form on both ends: `{ value: \"YYYY-MM-DD\" }`. Multiple ops on one field (`gte`/`lte`) AND automatically — no `and: [...]` wrapper needed around them.

**Open opps this quarter (ordered by forecast category then amount):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 200) { edges { node { Id Name { value } StageName { value displayValue } ForecastCategory { value } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } } }\"}" })
```

**Closed-won this period (for booked baseline):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsWon: { eq: true }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, first: 200) { edges { node { Id Name { value } Amount { value } Account { Name { value } } } } } } } }\"}" })
```

Both reads are needed for every ask: the open opps flag the deals and size the scenario, closed-won gives the booked floor.

`scope: MINE` = current user (default), with no User lookup. For a named rep whose Id is already disambiguated, remove `scope: MINE` and add `OwnerId: { eq: "<USER_ID>" }` inside `where`; never probe users to guess. Compute baseline:
- **Booked** = Σ closed-won `Amount.value`
- **Commit total** = Booked + Σ open opps where `ForecastCategory.value = "Commit"`
- **Best case total** = Commit total + Σ `ForecastCategory.value = "BestCase"`
- **Open pipeline total** = Σ all open opps `Amount.value`
- **Coverage ratio** = Open pipeline total ÷ (Quota − Booked)

If quota isn't in org data, ask once.

## 3. Apply scenario

**Flag slip risk first** (open deals closing this period; today = the run date), from fields you already read. First match wins:
- **HIGH** — past its `CloseDate`; or `LastActivityDate` 14+ days ago or blank; or closes within 7 days with `NextStep` blank or naming a blocker (or a grounded risk `__c` field says at risk).
- **MEDIUM** — `LastActivityDate` 7–13 days ago; or `NextStep` blank; or closes within 30 days at `Probability` under 50%.
- **On track** — everything else.

At risk = HIGH + MEDIUM. **"Which deals are slipping?"** = the flagged deals; **"what if all of them slip?"** = the full review's scenario (every flagged deal removed). A named-deal ask removes only that deal. A narrow ask ("how much is at risk?") stops after the flags; only a scenario ask needs the rest of this step.

Remove or restate the named deal(s):
- **Slip:** subtract from this period's buckets; note it lands next period
- **Reduced amount:** replace Amount with user's revised figure
- **Lost:** subtract entirely

Recompute commit total, gap to quota, coverage ratio.

## 4. Find substitute pipeline

Only a review or a scenario ask ("what if X slips?", "can I backfill?") needs substitutes; skip this step otherwise.

What in the existing open pipeline could realistically backfill this period:
- Best Case deals with recent activity (`LastActivityDate` within 14 days) and `CloseDate` inside period
- Deals one stage away from commit where timing looks achievable
- Be honest about timing: deal needing 6 weeks doesn't rescue quarter with 3 weeks left

## 5. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask ("how much of my pipeline is at risk?", "will I still make quota if Cedarline slips?") gets only the lines that answer it; "which deals are slipping?" lists the flagged deals with their risk and why.

```
# Slip Scenario: [Deal] - [slips / cut to $X / lost]

## Before vs After
| | Baseline | Scenario | Δ |
|---|---|---|---|
| Booked | $[X] | $[X] | - |
| Commit total | $[X] | $[X] | -$[X] |
| Gap to quota | $[X] | $[X] | +$[X] |
| Coverage ratio | [X.X]x | [X.X]x | |

## Verdict
[One sentence: still on plan / at risk / not recoverable this period without new pipeline]

## Substitute pipeline (what could backfill)
- **[Account]** $[X] - [bucket] - [why it's plausible this period, what has to happen, by when]
- ...
- Realistic backfill total: $[X] of the $[X] gap

## What to do this week
1. [Highest-leverage action to either save the slipping deal or accelerate a substitute - specific]
2. ...

## If it slips anyway
- Next-period commit starts at $[X] including this deal - [note any knock-on risk, e.g. stacked renewals or capacity]
```


## 6. Dashboard widget (data-viz tiles)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/deal-slip-scenario", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 5 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`summary`, part labels, `_status`, `next`, bar labels, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| A slip review ("which of my deals are slipping, and why?", "what's at risk this quarter?") | `title` + `answer` (bullets) + `deals` + `health` + `impact` (flagged deals removed, max 6 steps: 5 largest + "Other (N deals)") + tail only if it applies + `sources` |
| A named-deal scenario ("what if Cedarline slips?", "what if Summit is cut to $200K?", "what if we lose Orion?") | `title` + `answer` + **only** `impact` (that deal removed or cut) + `nextStep` with the best backfill when one exists + `sources` |
| How much is at risk ("how much of my pipeline is at risk?") | `title` + `answer` + **only** `health` + `sources` |
| A question with a direct answer ("will I still make quota if Cedarline slips?", "what's my coverage?") | `title` + `answer` (paragraph) + `sources` — no card, no tail |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for.
- **Overflow:** the `deals` table shows at most 8. For the other flagged deals give only their count in `answer` (e.g. "+25 more flagged"); never list them there, and add no trailing caveats or limits paragraph.
- **`deals`:** the flagged deals from step 3, HIGH first then MEDIUM, biggest first; `_tone` `error` + `_status` "HIGH", or `warning` + "MEDIUM". `close` is the date and days left ("Sep 30 · 37d"). `next` puts the move in **bold** first, then why.
- **`health`:** `atRisk` = the flagged deals, `onTrack` = the other open deals; the two values add up to the open total. The renderer colors them red and green.
- **`impact`:** for a review, `start` is "Full potential" (booked + every open deal this period) and one step per flagged deal, **capped at 6 steps**: with 6 or fewer flagged deals, one step each; with more, the 5 largest by amount as their own steps plus one last step labelled "Other (N deals)" whose `delta` is the sum of the rest (N ≥ 2). `end` still equals `start` minus every flagged deal, so the bars add up; for a named deal, `start` is today's commit and one step for that deal (a cut is the lost amount, with `sublabel` "(cut)"; a loss `sublabel` "(lost)"). `end` is the remainder ("On-track floor", "If Cedarline slips"). Send `quota` / `quotaLabel` only when quota came from the quota read or the user. `summary` is one sentence comparing the end bar with quota when known (bold the amounts); it shows under the bars on mobile, where the chart draws no quota line.
- **Tail fork:** `callout` when one move protects the period and the user can act on it now (one button, a first-person `actionMsg`); otherwise a `nextStep` line (e.g. the best substitute from step 4); if nothing applies, neither. A narrow ask usually gets no tail. Never both (if both are sent only the callout renders).
- **Coverage and substitutes have no card:** put what the prompt needs from them in `answer` or `nextStep`.
- **Sources:** the open pipeline is `https://<myDomain>/lightning/o/Opportunity/list`; a record is `https://<myDomain>/lightning/r/Opportunity/<Id>/view`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string ("$640K", "Sep 30 · 37d") except the `health` and `impact` amounts, which are numbers. Names are plain strings, never objects. Never send a color.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

The names, amounts and dates below (e.g. Cedarline, $640K, Sep 30) are illustrative; fill every value from the pipeline you read.

**Review — e.g. "Which of my deals are slipping, and why?"** (all three cards and a callout):

```json
{
  "title": "$1.23M across three deals is at risk of slipping – more than half your open pipeline.",
  "answer": "- **$1.23M of $1.93M open** sits at risk of slipping.\n- **Cedarline ($640K)** is the biggest exposure: the CFO has been unresponsive 3+ weeks.",
  "deals": {
    "items": [
      {"account": "Cedarline Financial", "name": "Enterprise Sales Cloud Platform", "amount": "$640K", "close": "Sep 30 · 37d", "stage": "Negotiation / Review", "next": "**Send the phased proposal** ($300K Q3 / $340K Q4) and escalate for a sign-off date before Sep 30.", "_tone": "error", "_status": "HIGH"},
      {"account": "Summit Health Partners", "name": "Patient Engagement", "amount": "$360K", "close": "Aug 30 · 6d", "stage": "Negotiation / Review", "next": "**Find a second contact** – Dr. Whitmore hasn't replied to 2 emails since 8/8.", "_tone": "error", "_status": "HIGH"},
      {"account": "Orion Manufacturing", "name": "Renewal + Sales Cloud Expansion", "amount": "$230K", "close": "Sep 20 · 27d", "stage": "Proposal/Price Quote", "next": "**Re-engage at the QBR 9/2** and lock a firm close date – no buyer activity in 9 days.", "_tone": "warning", "_status": "MEDIUM"}
    ]
  },
  "health": {
    "atRisk": {"value": 1230000, "label": "$1.23M at risk", "count": "3 deals", "names": "Cedarline, Summit Health, Orion"},
    "onTrack": {"value": 695000, "label": "$695K on track", "count": "2 deals", "names": "Brightwave, Northpeak Logistics"}
  },
  "impact": {
    "start": {"label": "Full potential", "value": 2020000},
    "steps": [{"label": "Cedarline", "delta": -640000}, {"label": "Summit", "delta": -360000}, {"label": "Orion", "delta": -230000}],
    "end": {"label": "On-track floor"},
    "quota": 800000, "quotaLabel": "$800K quota",
    "summary": "On-track floor of **$790K** lands just under your **$800K** quota."
  },
  "callout": {"lead": "Cedarline has 37 days to its Sep 30 close and no CFO sign-off scheduled.", "text": "Send the phased proposal – $300K in Q3 + $340K in Q4 – to keep 47% of the deal in-quarter and hold Q3 attainment at 100%.", "buttonLabel": "Draft phased proposal to Cedarline CFO", "actionMsg": "Draft a phased proposal email to the Cedarline Financial CFO: $300K in Q3 and $340K in Q4, with a request for a sign-off date before Sep 30."},
  "sources": [
    {"label": "Opportunities · 5 open (this quarter)", "url": "https://<myDomain>/lightning/o/Opportunity/list"},
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"}
  ]
}
```

**Named deal — e.g. "What if Cedarline slips?"** (only the impact card and a backfill line):

```json
{
  "title": "If Cedarline slips, commit drops to $865K – still $65K over your $800K quota.",
  "answer": "Losing **Cedarline ($640K)** to Q4 takes commit from **$1.51M to $865K**. You'd still clear the **$800K** quota, but with almost no cushion.",
  "impact": {
    "start": {"label": "Commit today", "value": 1505000},
    "steps": [{"label": "Cedarline", "delta": -640000, "sublabel": "(slips)"}],
    "end": {"label": "If Cedarline slips"},
    "quota": 800000, "quotaLabel": "$800K quota",
    "summary": "Commit lands at **$865K** – just **$65K** over your **$800K** quota."
  },
  "nextStep": {"lead": "Backfill from Northpeak.", "text": "Northpeak ($285K, proposal in review, active this week) is the most plausible pull-in before Sep 30. Want me to draft the push?"},
  "sources": [{"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"}]
}
```

**How much is at risk — e.g. "How much of my pipeline is at risk?"** (only the health card, no tail):

```json
{
  "title": "$1.23M of your $1.93M open pipeline is at risk of slipping.",
  "answer": "**Three deals** are flagged – mostly **Cedarline ($640K)**.",
  "health": {
    "atRisk": {"value": 1230000, "label": "$1.23M at risk", "count": "3 deals", "names": "Cedarline, Summit Health, Orion"},
    "onTrack": {"value": 695000, "label": "$695K on track", "count": "2 deals", "names": "Brightwave, Northpeak Logistics"}
  },
  "sources": [{"label": "Opportunities · 5 open (this quarter)", "url": "https://<myDomain>/lightning/o/Opportunity/list"}]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (deals, health, impact), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. Format every value as a ready-to-display string (currency, dates) except the health and impact amounts, which are numbers; names are plain strings, never objects. Never send a color: the renderer colors the cards (at risk red, on track green, slipping deals red).",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, table headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "deals": {
          "type": "string",
          "default": "OPEN OPPORTUNITIES",
          "description": "Heading of the deals card; English: 'OPEN OPPORTUNITIES'."
        },
        "colRisk": {
          "type": "string",
          "default": "Slip risk",
          "description": "Deals table header of the risk pill column. English: 'Slip risk'."
        },
        "colOpportunity": {
          "type": "string",
          "default": "Opportunity",
          "description": "Deals table header. English: 'Opportunity'."
        },
        "colAmount": {
          "type": "string",
          "default": "Amount",
          "description": "Deals table header. English: 'Amount'."
        },
        "colClose": {
          "type": "string",
          "default": "Close Date",
          "description": "Deals table header. English: 'Close Date'."
        },
        "colStage": {
          "type": "string",
          "default": "Stage",
          "description": "Deals table header. English: 'Stage'."
        },
        "colNextStep": {
          "type": "string",
          "default": "Suggested Action",
          "description": "Deals table header. English: 'Suggested Action'."
        },
        "health": {
          "type": "string",
          "default": "PIPELINE HEALTH",
          "description": "Heading of the pipeline health card; English: 'PIPELINE HEALTH'."
        },
        "impact": {
          "type": "string",
          "default": "SLIP IMPACT BY OPPORTUNITY",
          "description": "Heading of the slip impact card. English: 'SLIP IMPACT BY OPPORTUNITY'."
        },
        "stepAtRisk": {
          "type": "string",
          "default": "at risk",
          "description": "Second line under each slipping deal in the slip impact chart, unless the step sets its own sublabel. English: 'at risk'."
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
      "description": "REQUIRED. The slip takeaway, one bold sentence that already answers the question (e.g. '$1.23M across three deals is at risk of slipping – more than half your open pipeline.'). Never the skill name."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (amounts, deal names, dates, quota). A broad ask gets at most 2 short '- ' bullets: the headline number and the single biggest driver; a direct question ('will I still make quota if Cedarline slips?') gets 1-2 sentences. Answer ONLY what the user asked; never repeat deal rows, amounts, dates or quota math that the cards below already show. When more deals are flagged than the table shows, give only the count of the rest (e.g. '+25 more flagged'), never list them; no trailing caveats or limits paragraph."
    },
    "deals": {
      "type": "object",
      "description": "OPTIONAL card 'OPEN OPPORTUNITIES'. Include ONLY if the prompt asks which deals are slipping or at risk and why, or for a full slip review. Omit the key otherwise.",
      "required": [
        "items"
      ],
      "properties": {
        "items": {
          "type": "array",
          "maxItems": 8,
          "description": "One row per open deal flagged by the slip-risk rules in the skill instructions, HIGH first, then MEDIUM, biggest first within each; at most 8 (never an empty array - omit deals instead).",
          "items": {
            "type": "object",
            "required": [
              "account",
              "amount",
              "_tone",
              "_status"
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
                "description": "Pre-formatted amount (e.g. '$640K')."
              },
              "close": {
                "type": "string",
                "description": "Close date and days left (e.g. 'Sep 30 · 37d'); 'past due' when before today. Never ISO."
              },
              "stage": {
                "type": "string",
                "description": "Stage display value (e.g. 'Negotiation / Review')."
              },
              "next": {
                "type": "string",
                "description": "Why it is slipping and the move, in one or two sentences, with the move in **bold** first (e.g. '**Send the phased proposal** ($300K Q3 / $340K Q4) and escalate to the CFO's chief of staff for a sign-off date before Sep 30.')."
              },
              "_tone": {
                "type": "string",
                "enum": [
                  "error",
                  "warning"
                ],
                "description": "Slip risk from the rules: error = HIGH, warning = MEDIUM."
              },
              "_status": {
                "type": "string",
                "description": "The risk word on the pill, in the user's language (e.g. 'HIGH', 'MEDIUM')."
              }
            }
          }
        }
      }
    },
    "health": {
      "type": "object",
      "description": "OPTIONAL card 'PIPELINE HEALTH'. Include ONLY if the prompt asks how much is at risk, for a full slip review, or which deals are slipping when the split helps. Omit the key otherwise.",
      "required": [
        "atRisk",
        "onTrack"
      ],
      "properties": {
        "atRisk": {
          "type": "object",
          "description": "The flagged (HIGH + MEDIUM) open deals, drawn red.",
          "required": [
            "value",
            "label"
          ],
          "properties": {
            "value": {
              "type": "number",
              "description": "The amount as a number (e.g. 1230000)."
            },
            "label": {
              "type": "string",
              "description": "Amount and words, shown inside the bar and in the legend (e.g. '$1.23M at risk')."
            },
            "count": {
              "type": "string",
              "description": "Deal count after the label in the legend (e.g. '3 deals')."
            },
            "names": {
              "type": "string",
              "description": "The deals' account names, comma-separated, under the legend label (e.g. 'Cedarline, Summit Health, Orion')."
            }
          }
        },
        "onTrack": {
          "type": "object",
          "description": "The other open deals, drawn green.",
          "required": [
            "value",
            "label"
          ],
          "properties": {
            "value": {
              "type": "number",
              "description": "The amount as a number (e.g. 695000)."
            },
            "label": {
              "type": "string",
              "description": "Amount and words, shown inside the bar and in the legend (e.g. '$695K on track')."
            },
            "count": {
              "type": "string",
              "description": "Deal count after the label in the legend (e.g. '2 deals')."
            },
            "names": {
              "type": "string",
              "description": "The deals' account names, comma-separated, under the legend label (e.g. 'Brightwave, Northpeak Logistics')."
            }
          }
        }
      }
    },
    "impact": {
      "type": "object",
      "description": "OPTIONAL card 'SLIP IMPACT'. Include for a full slip review and for 'what if <deal> slips / is cut / is lost?' and 'will I still make quota?'. Omit the key otherwise.",
      "required": [
        "start",
        "steps",
        "end"
      ],
      "properties": {
        "start": {
          "type": "object",
          "required": [
            "label",
            "value"
          ],
          "description": "The first bar: closed won plus every open deal in the period ('Full potential'), or today's commit for a named-deal scenario.",
          "properties": {
            "label": {
              "type": "string",
              "description": "Bar label (e.g. 'Full potential', 'Commit today')."
            },
            "value": {
              "type": "number",
              "description": "Its amount as a number (e.g. 2020000)."
            }
          }
        },
        "steps": {
          "type": "array",
          "maxItems": 6,
          "description": "One step per deal that slips, is cut or is lost, biggest first; delta is negative; at most 6. If more than 6 deals are flagged, send the 5 largest as their own steps plus one final step that sums the rest, labelled 'Other (N deals)' where N is how many it holds (at least 2); with 6 or fewer, one step per deal and no bucket. Drawn red with the 'at risk' label under the name unless a step sets its own sublabel. Never an empty array.",
          "items": {
            "type": "object",
            "required": [
              "label",
              "delta"
            ],
            "properties": {
              "label": {
                "type": "string",
                "description": "Account short name (e.g. 'Cedarline')."
              },
              "delta": {
                "type": "number",
                "description": "Amount lost from this period, negative (e.g. -640000; a cut to $400K of a $640K deal is -240000)."
              },
              "sublabel": {
                "type": "string",
                "description": "Optional second line instead of 'at risk' (e.g. '(cut)', '(lost)')."
              }
            }
          }
        },
        "end": {
          "type": "object",
          "required": [
            "label"
          ],
          "description": "The last bar, drawn green; the renderer computes its value.",
          "properties": {
            "label": {
              "type": "string",
              "description": "Bar label (e.g. 'On-track floor', 'If Cedarline slips')."
            }
          }
        },
        "quota": {
          "type": "number",
          "description": "Quota as a number (e.g. 800000), drawn as a dashed line. Only from the quota read or a quota the user stated; omit if you have none."
        },
        "quotaLabel": {
          "type": "string",
          "description": "Label on the quota line (e.g. '$800K quota'). Send only with quota."
        },
        "summary": {
          "type": "string",
          "description": "One markdown sentence with **bold** amounts comparing the end bar with quota when known (e.g. 'On-track floor of **$790K** lands just under your **$800K** quota.'). Shown under the bars on mobile, where the chart has no quota line."
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if one move protects the period AND the user can act on it now (e.g. phase the biggest at-risk deal before its close date). Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period, e.g. 'Cedarline has 37 days to its Sep 30 close and no CFO sign-off scheduled.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Draft phased proposal to Cedarline CFO')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button. Use INSTEAD of callout, never both.",
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead (the suggested move, e.g. 'Backfill from Northpeak.')."
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
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name: object · record or list (e.g. 'Opportunities · Q3 forecast by category', 'Opportunity · Brightwave Media', 'Opportunity field history · this quarter')."
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
