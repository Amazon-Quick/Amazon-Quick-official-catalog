---
name: deal-signals
display_name: Deal Signals (Preview)
description: "Answer questions about the signals on a rep's open deals, scoped to what was asked: a weekly sweep of worrying and positive signals with the book health score, the health score alone, what is wrong with one account, or what to do about it, from Salesforce close dates, activity, next steps and forecast fields plus email, documents and Slack."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:66e73b788fac306cf0fdc1abab54e86ce18d9801687c1e77536529167d66677a"
id: "71653933-d296-4c6f-a15f-1ab338e09738"
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
Answer what the user asked about their deals' signals (which deals are showing worrying signals this week, the book's health score, what's wrong with one account, or what to do about it) in one pass. **Read only what the question needs** and present only that: a broad sweep ("any deals showing worrying signals this week?") reads and shows the whole book; a specific ask ("what's wrong with Cedarline?", "what's my book health score?") reads and shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full sweep.** A broad sweep reads and shows the whole book; a specific ask reads and shows only that. Skip reads the question doesn't need (each read step says which), and don't show something just because you fetched it.

# Deal Signals

Ground → (read + evidence, one turn) → check thresholds → digest. Scope: my book (default), or a tier/team if asked. Since: last run, else 7 days.

## 1. Ground (hardcoded — Opportunity only) + running user's Id

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's custom signal fields — don't assume names. Fetch `currentUser.Id` in the SAME call (used to account-scope the book in step 2), so this stays one round-trip:

```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Record `currentUser.Id` as `<UID>`. Note scalar `__c` fields relevant to signals (renewal date, competitor, champion, deal-desk/legal-hold). **Resolve the next-step field `<NEXTSTEP>` — prefer a custom field over standard `NextStep`:** first a `__c` field whose `label` or ApiName reads like a next step (e.g. `Next_Step__c` labeled "Next Step"); else the standard `NextStep`. A custom next-step field implies the org built its own next-step logic and reps actually fill it in, whereas the standard `NextStep` is frequently left empty — preferring the custom one is why the "stale commitment" signal fires on the field reps actually use, not a permanently-blank standard one. Use exact names from this result.

## 2. Read the open book (one call, scope: MINE)

`scope: MINE` = the running user's book (no user lookup needed). Add confirmed `__c { value }` fields into `<OPP_CUSTOM>`, and select the resolved next-step field as `<NEXTSTEP> { value }` (default `NextStep { value }`). **Also account-scope the book:** add `Account: { OwnerId: { eq: \"<UID>\" } }` to the `where` so the sweep only covers opps on accounts the rep currently owns. When an account is reassigned, Salesforce moves `Account.OwnerId` but not the open opps' `OwnerId`, so `scope: MINE` alone keeps surfacing stale "zombie" deals on accounts the rep no longer manages. For a tier/team scope (asked for explicitly), drop `scope: MINE` AND this account-owner clause and filter on the requested owner/team instead — a manager reviewing a team wants every deal regardless of account owner.

Every ask sends this one read: the health score and a one-account answer both need the whole book's signals. A one-account ask keeps only that account's opps from the result; a "what should I do about it?" follow-up reuses what was already read in this conversation and sends nothing new.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, Account: { OwnerId: { eq: \\\"<UID>\\\" } } }, first: 100) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } <NEXTSTEP> { value } LastActivityDate { value } LastModifiedDate { value } ForecastCategory { value } <OPP_CUSTOM> Account { Name { value } } } } } } } }\"}" })
```

## 2b. Evidence (same turn, only for CRM-flagged accounts — keeps the sweep fast)

After threshold checks flag accounts, in ONE turn fire (parallel, if tools present): **email** (last reply from us / **inbound from them with no reply from us in 3+ business days** / bounce / OOO / departure), **docs/transcripts** (competitor mention), **slack** (deal-desk/exec concerns). Keyed on the flagged account names. No tools present → skip silently.

A one-account ask fires the evidence for that account only; a "what should I do about it?" follow-up fires none.

**Email evidence:** When an email tool is available, run the 2b email search for the flagged accounts; it is part of the sweep, not optional. If no email tool is available or the search fails, add one line saying email was not checked (under the ✅ line in the digest, or in the widget callout), so inbound-waiting, champion-risk, and competitor signals are not implied clear.

**No extra Salesforce reads.** Step 2 already returned every CRM field the thresholds need (LastActivityDate, CloseDate, LastModifiedDate, NextStep, ForecastCategory, `__c` signals). Do NOT dispatch per-opp SF follow-ups (EmailMessage / Task / OpportunityFieldHistory / activity queries) — each is a serial round-trip. Evidence here is ONLY the external email/doc/slack connectors above; if those aren't present, skip.

## 3. Check thresholds (compute explicit dates from today — never quarter-relative)

Per open opp, fire a signal only when the record shows the trigger:
- **Gone quiet** — LastActivityDate >14d ago (or null) AND CloseDate within 90d
- **Inbound waiting** — customer emailed us and we haven't replied in 3+ business days (email evidence; the ball is on our side)
- **Danger zone** — CloseDate ≤21d out and stage still early
- **Overdue** — CloseDate < today
- **Slipped** — CloseDate moved out / recent LastModifiedDate date change
- **Stale commitment** — NextStep unchanged 21d+
- **Champion risk** — primary contact left/quiet (email/OOO evidence)
- **Renewal opening** — renewal entering lead-time window
- **Competitor mention** — named in recent email/transcript

Positive momentum, from the same fields (no extra read):
- **Rising** — no negative signal fired AND LastActivityDate within 7d AND `<NEXTSTEP>` names a dated step within the next 14d.

Then, over the whole swept book:
- **Assessment** — each open deal is **negative** (any negative signal fired), **positive** (Rising) or **neutral** (neither).
- **Health score** = round(5 + 5 × (positive − negative) ÷ open deals swept), a number 0–10: 5 is a neutral book, 0 all negative, 10 all positive (e.g. 7 negative and 2 positive of 11 → round(5 + 5 × −5 ÷ 11) = 3). With no open deals there is no score: send no `health` card, never a 0 or 5, and say in `answer` that the book has no open deals.
- **Trend** — call the book "falling" or "trending down" only when negative deals outnumber positive ones (score below 5); otherwise say it is holding.

Assemble only what the prompt needs from this.

## 4. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/deal-signals", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 5 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`signals`, `detail`, `detected`, `accountSignals.heading`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("any deals showing worrying signals this week?", "deal signals", "what changed in my book?") | `title` + `answer` (bullets) + `health` + `signals` + tail only if it applies + `sources` |
| The book's health ("what's my book health score?", "how healthy is my book?") | `title` + `answer` (paragraph: the score and why) + `sources` — no card, no tail |
| One account or deal ("what's wrong with Cedarline?", "why is Lumina flagged?") | `title` + `answer` (paragraph) + **only** `accountSignals` + `sources` (that deal) |
| What to do ("what should I do about it?", "what's my next move?") | `title` + `answer` (paragraph) + `callout` (or `nextStep` when nothing is time-sensitive) + `sources` — no card |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for or that does not speed up the answer.
- **Scope the `answer` too:** for "what's my book health score?", the answer is the score, the trend and the one reason — not the per-deal signals you also read.
- **`health`:** `score` is the step 3 health score as a number; `marker` is "Today · <score>"; `reason` is one sentence with the reason in **bold** (how many of the swept deals are negative and how many positive).
- **`signals`:** one row per opportunity with a fired signal. `sentiment` is `atRisk` when a negative signal puts a close this week in danger or 2 or more negative signals fired, `needsAttention` for any other negative signal, and `healthy` for a positive (Rising) deal; it renders as the Sentiment badge and the row's left rail. Negative rows first (most signals, then soonest close), then positive. At most 10 rows; when more fired, keep the 10 most urgent and give the full count in `answer`. `tag` only when 2 or more signals fired on the deal.
- **`accountSignals`:** the signals on the one deal asked about, one item each, strongest first. `tone` is `error` when the signal puts a close this week at risk, `warning` for other negative signals, `success` for positive momentum.
- **Tail fork:** `callout` when one move is time-sensitive and the user can act on it (one button, a first-person `actionMsg`); otherwise a `nextStep` line; if nothing applies, neither. A specific ask usually gets no tail; the "what should I do?" ask gets the callout. Never both (if both are sent only the callout renders).
- **Sources:** a record is `https://<myDomain>/lightning/r/Opportunity/<Id>/view`; the book is `https://<myDomain>/lightning/o/Opportunity/list`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string (currency, dates, "closes 8/31") except `health.score`, which is a number. Names are plain strings, never objects. `detected` is relative ("Today", "3 days ago"), never ISO.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

**Broad — "Any deals showing worrying signals this week?"** (bulleted answer, both cards, a callout, several sources; the signals table is trimmed here):

```json
{
  "title": "Seven deals are flashing warning signals – and Cedarline is stacking three.",
  "answer": "- Overall health is a **3 out of 10 and falling**.\n- Across your 11 open opps, **7 deals have negative signals** this week and 2 are showing positive momentum.\n- The risk isn't evenly spread: **$735K is time-sensitive** – Lumina closes tomorrow and Cedarline is compounding three red signals at once.",
  "health": {
    "score": 3,
    "marker": "Today · 3",
    "reason": "It's a **3 because 7 of your 11 deals are negative and only 2 positive this week** – most of the book needs attention."
  },
  "signals": [
    {"opportunity": "Cedarline", "tag": "3 signals", "deal": "$640K · Neg/Review · closes 8/31", "detected": "Today", "signals": "Champion Robert Nkemelu re-orged out · CFO Priya Anand silent **16d** · Vaultline CRM introduced by procurement.", "sentiment": "atRisk"},
    {"opportunity": "Lumina Software", "deal": "$95K · Neg/Review · closes 8/24", "detected": "Today", "signals": "Closes **tomorrow** · DocuSign not sent per Next Step · Jessica Tam on the signing call.", "sentiment": "atRisk"},
    {"opportunity": "Northpeak Dispatch", "deal": "$265K · Proposal · closes 9/14", "detected": "Today", "signals": "Presenting to **Marcus Reyes** Aug 24 · rollout pricing aligned.", "sentiment": "healthy"}
  ],
  "callout": {
    "lead": "$735K is time-sensitive across 6 days.",
    "text": "Lumina ($95K) closes tomorrow with DocuSign unsent, and Cedarline ($640K) is compounding three negative signals. Send the Lumina DocuSign first to lock the sure thing, then re-engage Cedarline's CFO before the signals stall the deal.",
    "buttonLabel": "Send the Lumina DocuSign",
    "actionMsg": "Draft the DocuSign send for the Lumina Software order form so it's in Jessica Tam's inbox before tomorrow's signing call."
  },
  "sources": [
    {"label": "Opportunities · 11 open", "url": "https://<myDomain>/lightning/o/Opportunity/list"},
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"},
    {"label": "Opportunity · Lumina Software", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"},
    {"label": "Activities · last 7 days"}
  ]
}
```

**Direct — "What's my book health score?"** (a paragraph answer, no card, no tail):

```json
{
  "title": "Your book health score is 3 out of 10 – and it's trending down.",
  "answer": "**7 of your 11 open deals** are showing negative signals this week, and only 2 have positive momentum. The drag is concentrated: **Cedarline and Lumina hold $735K** of the at-risk money.",
  "sources": [
    {"label": "Opportunities · 11 open", "url": "https://<myDomain>/lightning/o/Opportunity/list"}
  ]
}
```

**Specific — "What's wrong with Cedarline?"** (a paragraph answer, only the account card):

```json
{
  "title": "Cedarline is stacking three negative signals at once.",
  "answer": "Your champion is gone, the CFO has gone quiet, and procurement brought in a competitor – all on a **$640K deal closing 8/31**.",
  "accountSignals": {
    "heading": "CEDARLINE SIGNALS THIS WEEK",
    "items": [
      {"signal": "Champion lost", "detail": "Robert Nkemelu reorged out", "tone": "warning"},
      {"signal": "CFO dark", "detail": "Priya Anand silent 16 days", "tone": "warning"},
      {"signal": "Competitor introduced", "detail": "Vaultline CRM via procurement", "tone": "warning"}
    ]
  },
  "sources": [
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"}
  ]
}
```

**Next move — "What should I do about it?"** (after the Cedarline answer; a paragraph and the callout, no card):

```json
{
  "title": "Re-engage Priya Anand this week – she's the deal now.",
  "answer": "With Robert gone, **the CFO is your only path to signature** before 8/31. A short ROI recap gives her a reason to reply and puts you ahead of Vaultline.",
  "callout": {
    "lead": "Cedarline closes 8/31 – the CFO has been silent for 16 days.",
    "text": "Send Priya a short ROI recap and ask for 20 minutes this week.",
    "buttonLabel": "Draft the CFO re-engagement",
    "actionMsg": "Draft a re-engagement email to Priya Anand, CFO at Cedarline Financial, with an ROI recap to restart the $640K deal."
  },
  "sources": [
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"}
  ]
}
```



`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (health, signals, accountSignals), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A direct question ('what's my book health score?') usually gets no tail. Format every value as a ready-to-display string (currency, dates) except health.score, which is a number; names are plain strings, never objects.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, scale captions, table headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "health": {
          "type": "string",
          "default": "OVERALL HEALTH",
          "description": "Heading of the health card. English: 'OVERALL HEALTH'."
        },
        "scaleLow": {
          "type": "string",
          "default": "Danger · 0",
          "description": "Caption under the left end of the health scale. English: 'Danger · 0'."
        },
        "scaleMid": {
          "type": "string",
          "default": "Neutral · 5",
          "description": "Caption under the middle of the health scale. English: 'Neutral · 5'."
        },
        "scaleHigh": {
          "type": "string",
          "default": "Healthy · 10",
          "description": "Caption under the right end of the health scale. English: 'Healthy · 10'."
        },
        "signals": {
          "type": "string",
          "default": "SIGNALS ACROSS OPPORTUNITIES",
          "description": "Heading of the signals table card. English: 'SIGNALS ACROSS OPPORTUNITIES'."
        },
        "colSentiment": {
          "type": "string",
          "default": "Sentiment",
          "description": "Signals table header over the sentiment badge column. English: 'Sentiment'."
        },
        "atRisk": {
          "type": "string",
          "default": "At risk",
          "description": "Badge for an at-risk deal. English: 'At risk'."
        },
        "needsAttention": {
          "type": "string",
          "default": "Needs attention",
          "description": "Badge for a deal that needs attention. English: 'Needs attention'."
        },
        "healthy": {
          "type": "string",
          "default": "Healthy",
          "description": "Badge for a healthy deal. English: 'Healthy'."
        },
        "colOpportunity": {
          "type": "string",
          "default": "Opportunity",
          "description": "Signals table header. English: 'Opportunity'."
        },
        "colDetected": {
          "type": "string",
          "default": "Detected date",
          "description": "Signals table header. English: 'Detected date'."
        },
        "colSignals": {
          "type": "string",
          "default": "Signals",
          "description": "Signals table header. English: 'Signals'."
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
      "description": "REQUIRED. The takeaway in the user's context, one bold sentence that already answers the question (e.g. 'Seven deals are flashing warning signals – and Cedarline is stacking three.'). Never the skill name or 'Deal Signals'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (score, counts, amounts, names). A broad sweep gets 2-4 short '- ' bullets; a direct or specific question ('what's my book health score?', 'what's wrong with Cedarline?') gets a 1-3 sentence paragraph. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "health": {
      "type": "object",
      "description": "OPTIONAL card 'OVERALL HEALTH': one sentence on why the book scores what it does, over a danger-to-healthy scale with a marker at the score. Include ONLY for a broad sweep ('any deals showing worrying signals this week?', 'deal signals'). A direct 'what's my book health score?' puts the score in title and answer instead, no card. Omit the key otherwise.",
      "required": [
        "score",
        "marker",
        "reason"
      ],
      "properties": {
        "score": {
          "type": "number",
          "minimum": 0,
          "maximum": 10,
          "description": "Book health score 0-10 as a NUMBER: 5 is neutral, lower when negative deals outnumber positive ones (see the score rule in the skill instructions)."
        },
        "marker": {
          "type": "string",
          "description": "Caption over the marker (e.g. 'Today · 3')."
        },
        "reason": {
          "type": "string",
          "description": "One markdown sentence with the reason in **bold** (e.g. \"It's a **3 because 7 of your 11 deals are showing negative signals this week** – most of the book needs attention.\")."
        }
      }
    },
    "signals": {
      "type": "array",
      "description": "OPTIONAL card 'SIGNALS ACROSS OPPORTUNITIES': one row per opportunity with a fired signal, falling first (most signals, then soonest close), then rising. Include ONLY for a broad sweep. Omit the key otherwise; never an empty array.",
      "items": {
        "type": "object",
        "required": [
          "opportunity",
          "deal",
          "detected",
          "signals",
          "sentiment"
        ],
        "properties": {
          "opportunity": {
            "type": "string",
            "description": "Account or opportunity name as the rep says it (e.g. 'Cedarline')."
          },
          "tag": {
            "type": "string",
            "description": "OPTIONAL. Signal count when 2 or more fired on this deal (e.g. '3 signals'). Omit for a single signal."
          },
          "deal": {
            "type": "string",
            "description": "Amount · short stage · close, joined by ' · ' (e.g. '$640K · Neg/Review · closes 8/31')."
          },
          "detected": {
            "type": "string",
            "description": "When the newest signal was detected, relative (e.g. 'Today', '3 days ago'). Never ISO YYYY-MM-DD."
          },
          "signals": {
            "type": "string",
            "description": "The fired signals with their evidence, joined by ' · ', ending with a period; **bold** at most the one or two decisive facts (e.g. 'Closes **tomorrow** · DocuSign not sent per Next Step.'). Write signal names and facts in sentence case (e.g. 'Overdue since 8/20'), never all caps."
          },
          "sentiment": {
            "type": "string",
            "enum": [
              "atRisk",
              "needsAttention",
              "healthy"
            ],
            "description": "REQUIRED. Row assessment shown as the Sentiment badge and the left rail: 'atRisk' when a negative signal puts a close this week in danger or 2 or more negative signals fired; 'needsAttention' for any other negative signal; 'healthy' for positive momentum only."
          }
        }
      }
    },
    "accountSignals": {
      "type": "object",
      "description": "OPTIONAL card '<ACCOUNT> SIGNALS THIS WEEK': the signals that fired on one named account or deal. Include ONLY when the prompt asks about one account or deal ('what's wrong with Cedarline?'). Omit the key otherwise; never an empty items array.",
      "required": [
        "heading",
        "items"
      ],
      "properties": {
        "heading": {
          "type": "string",
          "description": "Card heading in upper case, in the user's language (e.g. 'CEDARLINE SIGNALS THIS WEEK')."
        },
        "items": {
          "type": "array",
          "description": "One entry per fired signal, newest first (never an empty array - omit accountSignals instead).",
          "items": {
            "type": "object",
            "required": [
              "signal",
              "detail",
              "tone"
            ],
            "properties": {
              "signal": {
                "type": "string",
                "description": "Signal name in a few words (e.g. 'Champion lost', 'CFO dark', 'Competitor introduced')."
              },
              "detail": {
                "type": "string",
                "description": "The evidence in a few words (e.g. 'Robert Nkemelu reorged out', 'Priya Anand silent 16 days')."
              },
              "tone": {
                "type": "string",
                "enum": [
                  "error",
                  "warning",
                  "success"
                ],
                "description": "Rail color: 'error' when it puts this week's close at risk, 'warning' for other negative signals, 'success' for positive momentum."
              }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if one move is time-sensitive (a close date is days away, a signal will stall the deal) AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the stake in one sentence, ending with a period, e.g. '$735K is time-sensitive across 6 days.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Send the Lumina DocuSign')."
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
          "description": "Bold lead (the suggested move, e.g. 'Re-engage the CFO first.')."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning, ending with an offer to help if natural."
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
            "description": "Source name: object · record (e.g. 'Opportunities · 11 open', 'Opportunity · Cedarline Financial')."
          },
          "url": {
            "type": "string",
            "description": "Record URL https://<myDomain>/lightning/r/<SObjectType>/<Id>/view, or for a list https://<myDomain>/lightning/o/Opportunity/list. Omit if none."
          }
        }
      }
    }
  }
}
```


## 5. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask ("what's wrong with Cedarline?", "what's my book health score?") gets only the lines that answer it, not the whole digest below.

Per fired signal, surface the trigger value **plus one or two supporting facts** from the Step 2 record (all already fetched — no new read), separated by ` • ` so the evidence is scannable, not a single condensed fact. Blank line between the 🔴 and 🟡 groups.

```
# Deal Signals — <today> — <scope>

🔴 Act today
- **<Account / Opp>** — <signal> — <StageName label> • $<Amount> • close <CloseDate> • last activity <LastActivityDate> • next step <NextStep> → <action>

🟡 This week
- **<Account / Opp>** — <signal> — <trigger value> • <supporting fact> • <supporting fact> → <action>

✅ Nothing else crossed a threshold (<N> opps swept)
```
Link each record. A touch → `draft-outreach`/`schedule-meeting`. Scheduled run: lead with count of new items since last run; a quiet digest is success.

**Complete digest:** List every deal that fired a signal, under its strongest signal; lower-priority deals in the same group may share one line, but never drop a flagged deal to shorten the digest. Always end with the ✅ line. Before sending, check that the number of deals listed equals the number that fired a signal.
