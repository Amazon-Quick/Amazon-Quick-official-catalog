---
name: customer-health
display_name: Customer Health
description: "Assess customer health from Salesforce account, renewal, case, task, and health data plus email, calendar, documents, and Slack, scoped to what was asked: the verdict, what is driving it, or a business-review kit. Use to judge risk, explain engagement or value trends, or prepare a business review; prospect meeting prep: call-prep."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:888ec77fb03f105ebc388df3f8a51e2bf6951b3f149d4a3cc7201b8f2d962273"
id: "f7053ede-94e4-4fde-a9d2-db6aab218efd"
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

- **Scope reading and output to the prompt, never a default full health report.** A broad ask ("run a health check", "what's driving the score") shows the overall read and every category signal; "why did engagement drop?" shows only the matching signal rows; "is X healthy?" gets the verdict and the reason. Think in lego blocks: a broad ask shows every block that carries real signal; a specific ask shows only the block(s) it names; a direct question gets no blocks. Don't show something just because you fetched it.
- Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.

# Customer Health

Two jobs, one data pass: the ongoing "are we okay here?" check, and the quarterly business review that proves value and sets up the next phase. Ground → (read + evidence, ONE turn) → score → output.

## Inputs

- **Account:** name or SFDC ID
- **Mode:** health check (default) or QBR prep
- **Period:** last quarter (default) for trend math

## 1. Ground (hardcoded — Account only)

Ground **only Account** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's health/adoption/renewal/NPS `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. Consider scalar `__c` fields worth using (health score, adoption/seat usage, renewal date, ARR, NPS, tier) — these are the same fields a health check might later offer to update, so ground them once and reuse. Standard fields, the `Owner`/`Opportunities`/`Cases` spans, and `LastActivityDate` are reliable across orgs; an org that doesn't use Cases just returns empty `edges`, not an error. Do not output all the field names.

## 2. Read (fill from step 1)

`%ACCOUNT%` = the user's match (1–2 words); when an SFDC Id was given instead of a name, swap every `Name: { like: \"%ACCOUNT%\" }` predicate (the Account root and each `aggregate` filter) for `Id: { eq: \"...\" }`. One call pulls the account plus its open-renewal-relevant opportunities, recent cases, and complete case counts — no separate dispatch per object.

**Field rule (avoids the retry loop):** add grounded custom fields only as `Field__c { value }` (`{ value displayValue }` for currency/picklist). Use the standard `Owner` span already written in the template; never invent a relationship span from a raw `Id`/`__c` field. Insert `<ACCT_CUSTOM>` = confirmed Account `__c { value }` fields.

Treat this GraphQL read template as literal. Replace only `%ACCOUNT%` (every occurrence), `<ACCT_CUSTOM>`, or the documented exact-Id filter. Do not reconstruct, shorten, flatten, or remove its trailing closing delimiters.

**Canonical query integrity:** Treat the literal request below as the canonical template, not an outline. Substitute only `%ACCOUNT%` (every occurrence), `<ACCT_CUSTOM>`, or the documented complete exact-Id filter; do not retype, reformat, shorten, or merge or split it. Before the first dispatch, verify that the nested `queryInput` JSON decodes, every placeholder is resolved or omitted, and `()`, `[]`, and `{}` are balanced. On a JSON or GraphQL syntax error (`InvalidSyntax` or an unexpected `<EOF>`), discard that request and rebuild it once from the literal template with `<ACCT_CUSTOM>` omitted; never patch braces in place or route the request through generated code. If the rebuilt request still fails with a syntax error, report the error and stop.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 1) { edges { node { Id Name { value } Type { value } Industry { value } AnnualRevenue { value displayValue } LastActivityDate { value } CreatedDate { value } <ACCT_CUSTOM> Owner { Name { value } } Opportunities(first: 20, orderBy: { CloseDate: { order: DESC } }) { edges { node { Id Name { value } Type { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsWon { value } } } } Cases(first: 10, where: { CreatedDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { CreatedDate: { order: DESC } }) { edges { node { CaseNumber { value } Subject { value } Status { value } Priority { value } CreatedDate { value } } } } Tasks(first: 20, where: { ActivityDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } } } } } } } } aggregate { matchedAccounts: Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }) { edges { node { aggregate { Id { count { value } } } } } } caseTotal: Case(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, CreatedDate: { gte: { literal: LAST_90_DAYS } } }) { edges { node { aggregate { Id { count { value } } } } } } caseOpen: Case(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, CreatedDate: { gte: { literal: LAST_90_DAYS } }, IsClosed: { eq: false } }) { edges { node { aggregate { Id { count { value } } } } } } caseEscalated: Case(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, CreatedDate: { gte: { literal: LAST_90_DAYS } }, Status: { eq: \\\"Escalated\\\" } }) { edges { node { aggregate { Id { count { value } } } } } } caseHighPriority: Case(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, CreatedDate: { gte: { literal: LAST_90_DAYS } }, Priority: { in: [\\\"High\\\", \\\"Critical\\\"] } }) { edges { node { aggregate { Id { count { value } } } } } } } } }\"}" })
```


**Case totals:** `Cases(first: 10)` returns only the ten most recent cases in the window. Take every Support count from the `aggregate` roots: `caseTotal`, `caseOpen`, `caseEscalated` (Status `Escalated`), and `caseHighPriority` (Priority `High` or `Critical`). Present status or priority read from the rows only as the latest ten, never as the total. If `matchedAccounts` is greater than 1, the totals span more than one account: rerun this request once with the exact-Id filter for the returned Account `Id` and use its totals. If an aggregate is missing or errors, mark that count unavailable; never count the capped rows instead.
Empty `edges` on `Account` → broaden `%ACCOUNT%`, or ask the user for the right account. Empty `edges` on `Cases`/`Tasks` just means none in the window — don't retry, don't treat as an error. The `Tasks` child (last 90d) is the in-CRM activity cadence behind the Engagement-trend dimension (and the widget engagement chart) — read it even when no external calendar/email connector is present.

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**Issue step 2 and all of step 2b as tool calls in a single turn — do not wait for the SF read to return before firing the searches.** They're independent (searches key on the account name from the request, not the SF result), so batch them together:
- **email**: threads with this account's contacts, last ~90d → cadence vs prior period, most recent exchange + topic
- **calendar**: meeting count/attendees last ~90d vs prior period — is the champion/exec still showing up
- **docs**: success plan, past QBR decks, recent notes → documented outcomes, open commitments
- **slack**: internal mentions → deal-desk/exec concerns, escalations

Use whatever email/calendar/doc/Slack tools are available; skip silently if none are present (SFDC-only is fine). Be explicit about what this skill can't see: product usage, support-ticket detail, and NPS only count if synced into a CRM field or a connected doc — otherwise mark that dimension "not visible from CRM" rather than guessing. Cite source + date for anything you use.

## 3. Score the health (cite every value; invent nothing)

| Dimension | Signal | Status |
|---|---|---|
| Relationship | champion/exec engagement (evidence), breadth of contacts active | 🟢🟡🔴 |
| Engagement trend | in-CRM `Tasks` cadence (step 2, last 90d) + meeting/email cadence (evidence) vs prior period | |
| Commercial | renewal proximity (open renewal opp `CloseDate`), open expansion, payment/contract issues | |
| Support | step 2 `aggregate` case counts (total, open, Escalated, High/Critical); aging/priority detail only from the latest-ten rows, labeled as such | |
| Value delivery | documented outcomes vs the success plan (docs), if one exists | |

Overall verdict with the one or two dimensions driving it.

### Calculating trends

For each dimension in the signals output, assign a `trend` value based on comparing the current period (last 90 days) to the prior period (the 90 days before that):

- **Engagement:** Compare task/email/meeting count in last 90d vs prior 90d. **falling** if current is <70% of prior; **rising** if current is >130% of prior; **steady** otherwise.
- **Relationship:** Compare champion engagement frequency (meetings, emails) in last 90d vs prior 90d. **falling** if key contacts became inactive or champion left; **rising** if new champions engaged or breadth expanded; **steady** if similar engagement level.
- **Commercial:** Compare open renewal/expansion opportunity movement. **falling** if renewal approaching with no activity, or deals slipping past close dates; **rising** if new expansion opps or renewal progressing; **steady** if no significant change.
- **Support:** Compare case volume and priority in last 90d vs prior 90d. **falling** if high-priority cases opened or cases aging; **rising** if case volume dropped or priorities resolved; **steady** if similar case load.
- **Value delivery:** Based on documented outcomes vs commitments. **falling** if commitments missed or no progress documented; **rising** if outcomes documented and goals achieved; **steady** if on track or not visible from CRM.

When you lack data to calculate a trend (e.g., no prior period data, or dimension not visible from CRM), default to **steady** and state in the signal text that the trend is not visible from available data.

## 4. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

**Widget transport:** Pass the fully hydrated renderer to `display_widget` as a direct top-level tool call whose `widgetDefinition` is a native JSON object. Never serialize or quote it, and never build or send it through generated code, a shell, a code runner, or temporary files. A returned string, printed preview, or generated file is not a mounted visual and is never a successful render. If the call succeeds, it is the terminal output: stop with no further assistant text. If it returns an error or the tool is unavailable, do not retry, repair, or create a substitute artifact; emit only the section 5 text fallback and stop, and never claim the widget rendered.
- ❌ WRONG: `widgetDefinition: "{\"key\":...}"` (stringified with escaped quotes)
- ✅ RIGHT: `widgetDefinition: {"key":...}` (native object, no quotes around the opening brace)

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/customer-health", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 5 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings and column headers in upper case) and write every free-text field (`overall`, `signals`, `nextStep`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. `overall.status` picks the status word and its colour, and a signal's `trend` picks its rail, arrow and colour — never put colour words in the text. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.
- **Rate the account on one scale: `overall.status` is `healthy`, `moderate` or `unhealthy`.** It says how the account is doing, nothing else: not what to do (that is `nextStep`) and not how urgent it is. Judge it from the step 3 dimensions you could support, weighing the ones that matter most for this account:
  - `unhealthy` when they are mostly poor, e.g. no active champion, a high-priority case sitting open, deals past their close dates, a renewal close with no recent activity.
  - `healthy` when they are mostly good and none is clearly poor.
  - `moderate` when they are mixed, or when too little is visible from CRM to call it either way.
  Base the rating only on what you read: do not make up a number to justify it. Use the same word in the `title` (e.g. "Cedarline is unhealthy – …"), never "at risk", "critical" or "watch".
- **Signals come from the step 3 scoring,** one row per dimension you could actually support, falling first. A dimension that is not visible from CRM is stated as such in its `text`, never guessed. Never invent a score, a cohort median or a point change: use only numbers present in a synced CRM field or a cited document, otherwise describe the trend in words.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| **Broad** ("run a health check on X", "how healthy is X, and why?", "what's driving the score?", QBR prep) | `title` (the verdict with the score or status) + `answer` + `overall` + `signals` + `nextStep` if there is a clear move + `sources`; for a QBR, offer the meeting kit (section 5) as a follow-up |
| **Specific: the overall read** ("what's the overall health?", "give me the verdict") | `title` + `answer` + **only** `overall` + `sources` |
| **Specific: the drivers** ("why did engagement drop?", "who is our champion at X?", "any open cases?", "what's hurting renewal?") | `title` + `answer` + **only** the `signals` rows that bear on it (no `overall`) + `sources` |
| **Specific: what to do** ("what should I do about X's health?") | `title` + `answer` + `nextStep` + `sources`; add the one or two `signals` rows that justify it |
| **Direct question** ("is X healthy?", "is X at risk?") | `title` + `answer` + `sources`. No cards |

#### Worked examples (the `props` object only)

**Health check — "How healthy is Cedarline?"** (overall read, category signals, a plain next step):

```json
{
  "title": "Cedarline is unhealthy – health fell to 26/100 the week we lost the champion.",
  "answer": "- Overall health is **26 out of 100** against a cohort median of **68**.\n- Engagement held until **Jul 12**, then dropped the week **Robert Nkemelu** reorged out.\n- Support is steady, so this is a **sponsor loss, not a satisfaction problem**.",
  "overall": { "intro": "Cedarline's overall health is", "status": "unhealthy", "text": "**Well below the cohort** – the drop lines up with the week the champion reorged out. **2 signal categories are falling**; support is steady." },
  "signals": [
    { "trend": "falling", "category": "Relationship", "text": "**No champion:** Robert Nkemelu reorged out in July; new CFO Priya Anand not yet engaged.", "buttonLabel": "Draft a re-sponsor plan", "actionMsg": "Draft a re-sponsor plan for Cedarline that names a new champion in Priya Anand's org." },
    { "trend": "falling", "category": "Engagement", "text": "**0 tasks in 90 days:** 40+ days inactive before the Aug 17 call.", "buttonLabel": "Log a re-engagement task", "actionMsg": "Log a re-engagement task on the Cedarline account." },
    { "trend": "steady", "category": "Support", "text": "**0 open cases:** clean, but no natural touchpoints to re-engage on." }
  ],
  "nextStep": { "lead": "This is a sponsor loss, not a satisfaction issue.", "text": "The fix is re-sponsoring at the CFO level. Want me to build a re-sponsor plan?" },
  "sources": [{ "label": "Account – Cedarline Financial" }, { "label": "Call – Aug 17" }]
}
```

**Specific — "Any open cases at Joja?"** (no cards):

```json
{
  "title": "Joja has no open cases – support is clean.",
  "answer": "- **0 open cases** in the last 90 days; the last one closed **Jun 3**.",
  "sources": [{ "label": "Account – Joja Industries" }]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (overall, signals), then at most one tail (nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A single-fact question (\"is Cedarline healthy?\") usually gets just title + answer + sources. Format every value as a ready-to-display string (dates as 'Jul 12'); names are plain strings, never objects (use `Contact.Name.value` / `Owner.Name.value`).",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line: the verdict on the account's health in the user's context, with the score and the one thing driving it (e.g. 'Cedarline is unhealthy – health fell to 26/100 the week we lost the champion.'). Plain text, no markdown. Never the skill name or 'Customer Health: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence, that answer ONLY what the user asked (the score vs. the cohort, when and why it moved, which categories are falling, what is steady). Put **bold** inline on the key values inside each sentence (scores, point changes, dates, names), never on a whole bullet. Do not restate every row of the signals card. No headings, tables or paragraphs."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, column headers, status and trend words, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "overallHealth": {
          "type": "string",
          "default": "OVERALL HEALTH",
          "description": "Heading of the overall-health card. English: 'OVERALL HEALTH'."
        },
        "accountSignals": {
          "type": "string",
          "default": "ACCOUNT SIGNALS",
          "description": "Heading of the signals card. English: 'ACCOUNT SIGNALS'."
        },
        "trend": {
          "type": "string",
          "default": "TREND",
          "description": "Signals column header. English: 'TREND'."
        },
        "category": {
          "type": "string",
          "default": "CATEGORY",
          "description": "Signals column header. English: 'CATEGORY'."
        },
        "signals": {
          "type": "string",
          "default": "SIGNALS",
          "description": "Signals column header. English: 'SIGNALS'."
        },
        "falling": {
          "type": "string",
          "default": "Falling",
          "description": "Trend word for a signal with trend 'falling'. English: 'Falling'."
        },
        "steady": {
          "type": "string",
          "default": "Steady",
          "description": "Trend word for a signal with trend 'steady'. English: 'Steady'."
        },
        "rising": {
          "type": "string",
          "default": "Rising",
          "description": "Trend word for a signal with trend 'rising'. English: 'Rising'."
        },
        "unhealthy": {
          "type": "string",
          "default": "Unhealthy",
          "description": "Status word for overall.status 'unhealthy'. English: 'Unhealthy'."
        },
        "moderate": {
          "type": "string",
          "default": "Moderate",
          "description": "Status word for overall.status 'moderate'. English: 'Moderate'."
        },
        "healthy": {
          "type": "string",
          "default": "Healthy",
          "description": "Status word for overall.status 'healthy'. English: 'Healthy'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "overall": {
      "type": "object",
      "description": "OPTIONAL card 'OVERALL HEALTH': a lead-in line ending in the health status word (coloured by `status`) followed by one markdown paragraph. Include for a broad ask (a health check, what is driving the score, a QBR) and when the prompt asks for the overall read. Omit when the prompt asks about one specific driver or a single fact.",
      "required": [
        "status",
        "text"
      ],
      "properties": {
        "intro": {
          "type": "string",
          "description": "Plain text before the status word on the first line, written whole in the user's language (e.g. \"Cedarline's overall health is\"). Omit to show the status word alone."
        },
        "status": {
          "type": "string",
          "enum": [
            "unhealthy",
            "moderate",
            "healthy"
          ],
          "description": "How the account is doing overall, on one scale: unhealthy (red), moderate (orange), healthy (green). It rates the account's state only: not what to do about it (that is `nextStep`) and not how urgent it is. unhealthy = the dimensions that matter most for this account are mostly poor; healthy = mostly good and none clearly poor; moderate = mixed, or too little is visible from CRM to call it either way. Picks the status word (from labels) and its colour. Never put the status word or a colour word in `intro` or `text`."
        },
        "text": {
          "type": "string",
          "description": "Markdown that continues the same paragraph after the status word (shown as '<intro> <status>. <text>'), so start it with a capital letter and do not repeat the status (e.g. '**Well below the cohort** – the sharp drop lines up with the week the champion reorged out in July. **4 signal categories are falling** across ...'). **Bold** on the key phrases; one short paragraph."
        }
      }
    },
    "signals": {
      "type": "array",
      "description": "OPTIONAL card 'ACCOUNT SIGNALS': one row per health category (Relationship, Engagement, Commercial, Value delivery, Support), falling first. Include every category the data supports for a broad ask (health check, what is driving the score, QBR); for a specific driver question send only the matching rows. Omit when the prompt asks only for the overall read. Never an empty array, never invent a category.",
      "items": {
        "type": "object",
        "required": [
          "trend",
          "category",
          "text"
        ],
        "properties": {
          "trend": {
            "type": "string",
            "enum": [
              "falling",
              "steady",
              "rising"
            ],
            "description": "Direction of the category over the period. Drives the left rail, the arrow and the trend word with its colour: falling = red, steady = grey, rising = green."
          },
          "category": {
            "type": "string",
            "description": "Bold category name in the user's language (e.g. 'Relationship', 'Engagement', 'Commercial', 'Value delivery', 'Support')."
          },
          "text": {
            "type": "string",
            "description": "Markdown evidence, 1-2 sentences: a **bold lead** with the key fact, then the supporting detail (e.g. '**No champion:** Robert Nkemelu reorged out in July; new CFO Priya Anand not yet engaged – no response for 3 weeks.'). If a signal is not visible from CRM say so instead of guessing."
          },
          "buttonLabel": {
            "type": "string",
            "description": "Label of the optional outline button under the text, an action that addresses this signal (e.g. 'Draft a re-sponsor plan'). Send only together with `actionMsg`, and only for signals worth acting on; usually not for steady ones."
          },
          "actionMsg": {
            "type": "string",
            "description": "First-person request sent to chat when the button is clicked (e.g. 'Draft a re-sponsor plan for Cedarline that names a new champion in Priya Anand's org.')."
          }
        }
      }
    },
    "nextStep": {
      "type": "object",
      "description": "OPTIONAL tail: a plain suggestion paragraph with NO button, only when there is a genuinely useful next move (e.g. what the pattern means and an offer to build the plan).",
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead: the diagnosis or suggested move, ending with a period (e.g. 'This is a sponsor loss, not a satisfaction issue.')."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning, ending with an offer to help if natural."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the health read came from: the Salesforce records you actually read, linked (this is where the Account record link goes), plus any email/call/doc you cited. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Account – Cedarline Financial', 'Opportunity – Cedarline Renewal', 'Call – Aug 17')."
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


## 5. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

**Health check mode:**
```
# Health: <Account> — 🟢/🟡/🔴
<verdict sentence>
<dimension table with evidence>
## Watch items
- <specific signal, why it matters, suggested action>
## Suggested SFDC updates
- <health/status fields, if grounded> - these live on the Account record: show before/after and confirm before writing, or output as a checklist on a read-only connector
```

**QBR prep mode:** add the meeting kit —
1. **Value delivered** — outcomes since last review, in their metrics, with sources
2. **Adoption story** — what's working, what's underused (only CRM/document-visible facts)
3. **Open items** — Cases resolved/open, commitments from last QBR and their status
4. **Next phase** — the expansion plays (`expansion-whitespace`) and renewal framing (`renewal-radar`) worth raising
5. **Agenda + attendees** — who should be in the room from the stakeholder map, and the asks for their execs
Offer the agenda as a doc and the meeting via `schedule-meeting`.
