---
name: account-context
display_name: Account Context
description: "Answer questions about a company already in Salesforce, scoped to what was asked: a catch-up or overview, just the open deals, risks, stakeholders, what they own, or triggers to reach out. Use when asked to tell about, catch up on, or brief on an existing account. Not in CRM: research-prospect."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:403bc8ff57404a4e50fb179417ce1a408c015f36e1bb7a68dab31fa5d5897a72"
id: "7b5070de-e505-4b3d-b231-39c5c85f4035"
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
Answer what the user asked about an account — from the Salesforce record, open pipeline, key contacts, recent activity, and (when connected) email, documents, and internal Slack — in one pass.

# Audience:
This skill is used by workers in a sales organization. They want results as fast as possible. Minimize thinking when it's not necessary, hyper focus on getting them the results for the described goal.

# Rules:

- **Scope reading and output to the prompt, never a default full brief.** A broad catch-up reads and shows the overall picture; a specific ask ("just the open deals", "who are the stakeholders") reads, grounds and shows only that area (a deals-only ask touches just Account and Opportunity and needs no email or Slack). Don't fetch unrelated areas, and don't show something just because you fetched it.
- Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.

# Account Context

Resolve to one account, ground its customs, one read by Id, enrich in parallel, synthesize.

## 1. Resolve the account (disambiguate — do NOT probe)

Shared/demo orgs collide on name (duplicate seed data, empty test records like `MBourlon Acme Lab`). Land on a single Id first. One small query, **Account-level fields only** — never pull each candidate's Opportunities/Contacts to see "which is real"; that's a probe, skip it unless the user asks. If the user gave a Salesforce Id, skip this step.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 10) { edges { node { Id Name { value } Website { value } Type { value } Industry { value } LastActivityDate { value } Owner { Name { value } } } } } } } }\"}" })
```

(domain → filter `Website` instead of `Name`.)

- **One clear match** → take its Id, continue.
- **Several plausible matches** → list them (Name · Website · Owner · LastActivityDate · Id link) and ask the user to pick. `LastActivityDate` is your one free liveness tell — a blank/stale row beside a recent one usually flags the dead test record — but let the user decide; don't pick for them.
- **10 rows hit (likely more)** or **empty** → ask the user to narrow or correct the name.

## 2. Ground customs (fire in parallel with step 1)

Get the `__c` fields on every object this read touches — Account (health, tier, segment, ARR, renewal, status, score, region), Opportunity (forecast, competitor, close-plan, deal-health), Contact (buyer role/persona), Task (activity customs), and, for the Products & Whitespace card, the Account ARR and renewal fields — so the read can fetch them. Standard fields and the standard children (`Opportunities`, `Contacts`, `Tasks`) are reliable across orgs; you're grounding **only** for customs worth showing.

Issue these four individual `dispatch_readonly` requests in the same tool turn, in parallel with step 1. Keep one object per `objectInfos` request; combining catalogs can overflow the tool result.

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

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Task\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

**An individual response can still be huge** — person-account orgs add hundreds of `__pc` fields, managed packages add `namespace__` fields (60KB+). **If a tool result overflows** or comes back truncated, scan what came back for `__c` fields whose `label` matches your keywords. Grounding is best-effort (customs are additive): if it's still unwieldy, take the standard fields and move on. Ignore `__pc` and `namespace__` noise when you scan.

## 3. Read the resolved account (by Id — fill from steps 1–2)

A broad ask uses the whole query below; a specific ask keeps the Account header plus only the matching block (Opportunities, or Contacts and the `Task` read) and drops the rest.

Filter by the resolved `Id` (disambiguation is done — no `like`, no `first:1` roulette). Insert the per-object custom tokens from step 2's grounding — `<ACCT_CUSTOM>` on Account, `<OPP_CUSTOM>` on each Opportunity node, `<CONTACT_CUSTOM>` on each Contact node, `<TASK_CUSTOM>` on each Task node — each = that object's confirmed `__c { value }` fields (`{ value displayValue }` for currency/picklist). Omit a token if grounding surfaced no relevant customs for that object.

Preserve the supplied GraphQL documents; replace only `<ID>` and the grounded custom-field placeholders.

**Canonical query integrity:** Treat the literal request below as the canonical template, not an outline. Substitute only the resolved Id and the `<ACCT_CUSTOM>`, `<OPP_CUSTOM>`, `<CONTACT_CUSTOM>`, and `<TASK_CUSTOM>` slots (each a complete, confirmed field selection such as `Health_Score__c { value }`, or omitted when none applies); do not retype, reformat, shorten, or merge or split it, and keep `aggregate` a sibling of `query` under `uiapi`. Before the first dispatch, verify that the nested `queryInput` JSON decodes, every placeholder is resolved or omitted, and `()`, `[]`, and `{}` are balanced. On a JSON or GraphQL syntax error (`InvalidSyntax` or an unexpected `<EOF>`), discard that request and rebuild it once from the literal template using the resolved Id and with all four custom slots omitted; never patch braces in place or route the request through generated code. If the rebuilt request still fails with a syntax error, report the error and stop.

**Rules that avoid the retry loop:**
- Related record's name → span the lookup: `Owner { Name { value } }`. `Account.Owner` and `Opportunity.Owner` are single-target (→ `User`) and span cleanly. Never append `{ … }` to a raw `Id`/`__c` field.
- **Activity owners are polymorphic — don't span them.** `Task.Owner`/`Event.Owner` (and `Who`/`What`) are `User | Group` unions, so `Owner { Name { value } }` fails with `Field 'Name' in type 'Task_Owner' is undefined`. The default query below omits the owner span on Tasks; if you truly need it, use a fragment — `Owner { ... on User { Name { value } } }`. Don't assume symmetry with Opportunity.
- **Any `FieldUndefined` / `undefined in type X`** means that name or shape is wrong for THIS org — don't re-fire it. Re-ground that one object via `objectInfos(apiNames:["<Obj>"]) { fields { ApiName relationshipName referenceToInfos { ApiName } } }` (a `referenceToInfos` listing 2+ targets = polymorphic union → use a fragment), then retry from confirmed names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ID>\\\" } }, first: 1) { edges { node { Id Name { value } Website { value } Industry { value } NumberOfEmployees { value } AnnualRevenue { value displayValue } Type { value } BillingCity { value } BillingCountry { value } Description { value } CreatedDate { value } LastActivityDate { value } Owner { Name { value } Email { value } } <ACCT_CUSTOM> Opportunities(first: 10, where: { IsClosed: { eq: false } }, orderBy: { LastModifiedDate: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } Type { value } LastActivityDate { value } <OPP_CUSTOM> Owner { Name { value } } } } } Contacts(first: 15, orderBy: { LastActivityDate: { order: DESC } }) { edges { node { Id Name { value } Title { value } Email { value } Phone { value } LastActivityDate { value } <CONTACT_CUSTOM> } } } } } } Task(first: 10, where: { AccountId: { eq: \\\"<ID>\\\" }, ActivityDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } Description { value } <TASK_CUSTOM> } } } } aggregate { Opportunity(where: { AccountId: { eq: \\\"<ID>\\\" }, IsClosed: { eq: false } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```

`Opportunities` is bounded open supporting detail; the `aggregate` block rides in the same query (one dispatch) and is authoritative — use `totalCount` and `Amount.sum.value` for the complete open pipeline, not the ten supporting-detail records. `Task` is a top-level read filtered by `AccountId`, so it includes activity logged on the account's opportunities and contacts (an `Account.Tasks` child would only return activity attached to the account itself). It carries no `Owner` span (polymorphic — see rule above). If a block errors, drop it and read recency from `LastActivityDate` — don't retry.

## 4. Enrich (parallel — skip any source not connected; never fabricate)

Fire these together in one turn; skip any whose tool isn't available and note it once at the end. What you retrieve is raw material — the widget shows only the blocks the prompt calls for.
- **Email** — threads to/from the account's domain, last 90d. 5 most recent: date, participants, subject, one-line landing.
- **Documents** — docs mentioning the account: most recent transcript/notes + any account plan / proposal / MSA (title + date + one-line).
- **Slack** — account name, last 60d: relevant threads (deal desk, escalations, exec mentions, win/loss) with links.

### 4b. Products — only for the Products & Whitespace card

Fire these two in the same turn as the step 4 enrichment, **only** when the prompt asks what the account owns/has bought/expansion/whitespace/renewal, or is a broad catch-up. If either errors (object or field absent in this org), drop it and omit the matching list; do not retry.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Account: { Id: { eq: \\\"<ID>\\\" } } }, first: 30, orderBy: { CloseDate: { order: DESC } }) { edges { node { Name { value } IsWon { value } IsClosed { value } CloseDate { value } OpportunityLineItems(first: 20) { edges { node { TotalPrice { value displayValue } Product2 { Name { value } Family { value } } } } } } } } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Product2(where: { IsActive: { eq: true } }, first: 200) { edges { node { Family { value } } } } } } }\"}" })
```

Derive the three lists from those results only, never from memory or the product names you expect:
- **`purchased`** — Product2 `Family` (else `Name`) of line items on opportunities with `IsWon = true`; de-duplicated.
- **`opportunities`** — line items on opportunities with `IsClosed = false`, as `"<Family or Name> · <amount>"` when the line has a `TotalPrice`.
- **`whitespace`** — distinct active catalog `Family` values that appear in neither `purchased` nor `opportunities`; at most 6.

## 5. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/account-context", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`summary`, `detail`, `category`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("catch me up on X", "latest on X", "overview of X", "prep me for X") | `title` + `answer` (the summary, on top) + **every** card you have real data for (`flags`, `openOpportunities`, `productsWhitespace`, `signals`, `stakeholders`) — never drop a card that has data + tail only if it applies + `sources` |
| Specific ("just the open deals", "who are the stakeholders", "any risks?", "what have they bought?", "any news?") | `title` + `answer` + **only** the one matching visualization (`openOpportunities`, `stakeholders`, `flags`, `productsWhitespace`, `signals`) + tail only if it applies + `sources` |
| A question with a direct answer ("when does their contract renew?") | `title` + `answer` + `sources`; add a card only if it makes the answer faster to grasp |

#### Worked examples (the `props` object only)

**Broad — "What's the latest on Cedarline Financial?"** (summary on top, every card that has data, a time-sensitive callout):

```json
{
  "title": "Cedarline is At Risk – a $640K close and a $2.1M renewal both hinge on one unresponsive CFO.",
  "answer": "- A **$640K Enterprise Sales Cloud Platform** deal closes **Aug 31**, but coverage has thinned.\n- The CFO shows **no engagement for 16 days** and the champion reorged out.",
  "flags": [{ "title": "CFO Priya Anand – No engagement, 3+ weeks", "context": "pricing objection unresolved", "detail": "Aug 26 1:1 invited, not accepted.", "tone": "error" }],
  "openOpportunities": { "items": [{ "name": "Enterprise Sales Cloud Platform", "summary": "$640K · closes Aug 31", "detail": "Negotiation / Review · awaiting CFO", "tone": "warning" }] },
  "productsWhitespace": { "purchased": ["Service Cloud", "Slack"], "opportunities": ["Enterprise Sales Cloud · $640K"], "whitespace": ["Agentforce", "Revenue Cloud"] },
  "signals": [{ "category": "Earnings", "title": "Q2 earnings call · Aug 12", "context": "CFO Priya Anand called out \"efficiency initiatives\" as a 2H priority." }],
  "stakeholders": [{ "name": "Priya Anand", "detail": "CFO · Economic Buyer · last touch Aug 8" }],
  "callout": { "lead": "No CFO meeting on the calendar.", "text": "Route a re-engagement invite through Katie McKee before Aug 26.", "buttonLabel": "Send re-engagement via Katie", "actionMsg": "Draft a short re-engagement invite to Katie McKee at Cedarline for Priya Anand's staff meeting." },
  "sources": [{ "label": "Account – Cedarline Financial" }, { "label": "Opportunity – Enterprise Sales Cloud Platform" }]
}
```

**Specific — "Who are the stakeholders at Joja?"** (stakeholders card only, plus a genuinely useful next step as a plain line):

```json
{
  "title": "Joja's buying group is thin: one active sponsor and an inactive exec.",
  "answer": "- **Morgan Lee** (VP Ops) is the active sponsor.\n- **Sam Ortiz** (CFO) has been **inactive since June**.",
  "stakeholders": [
    { "name": "Morgan Lee", "detail": "VP Ops · Sponsor · last touch Oct 2" },
    { "name": "Sam Ortiz", "detail": "CFO · Economic Buyer · last touch Jun 11", "status": "inactive" }
  ],
  "nextStep": { "lead": "Re-engage Sam Ortiz through Morgan.", "text": "Ask Morgan Lee for a CFO intro before the renewal. Want me to draft that note?" },
  "sources": [{ "label": "Contacts – Joja Corporation" }]
}
```



`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (flags, openOpportunities, productsWhitespace, signals, stakeholders), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions; a broad catch-up includes every one of them you have real data for. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A pure list or lookup question usually gets no tail. Format every value as a ready-to-display string (currency, dates); names are plain strings, never objects (use `Account.Owner.Name.value`).",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line: the takeaway in the user's context that already answers the question (e.g. 'Cedarline is At Risk – a $640K close and a $2.1M renewal both hinge on one unresponsive CFO.'). Plain text, no markdown. Never the skill name or 'Account Context: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence, that answer ONLY what the user asked. Put **bold** inline on the key values inside each sentence (amounts, dates, names, counts), never on a whole bullet. Do not restate the cards below it. Answer ONLY what was asked (scope the bullets to the prompt); no headings, tables or paragraphs."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget (card headings, product row labels, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "flagsRisks": {
          "type": "string",
          "default": "FLAGS & RISKS",
          "description": "Heading of the flags card. English: 'FLAGS & RISKS'."
        },
        "openOpportunities": {
          "type": "string",
          "default": "OPEN OPPORTUNITIES",
          "description": "Heading of the open-opportunities card. English: 'OPEN OPPORTUNITIES'."
        },
        "productsWhitespace": {
          "type": "string",
          "default": "PRODUCTS & WHITESPACE",
          "description": "Heading of the products card. English: 'PRODUCTS & WHITESPACE'."
        },
        "purchased": {
          "type": "string",
          "default": "PURCHASED",
          "description": "Row label for products already owned. English: 'PURCHASED'."
        },
        "opportunities": {
          "type": "string",
          "default": "OPPORTUNITIES",
          "description": "Row label for products in open deals. English: 'OPPORTUNITIES'."
        },
        "whitespace": {
          "type": "string",
          "default": "WHITESPACE",
          "description": "Row label for products not owned and not in play. English: 'WHITESPACE'."
        },
        "reasonsToReachOut": {
          "type": "string",
          "default": "REASONS TO REACH OUT",
          "description": "Heading of the signals card. English: 'REASONS TO REACH OUT'."
        },
        "signalCategory": {
          "type": "string",
          "default": "SIGNAL CATEGORY",
          "description": "Column header for the signal's category in the signals card. English: 'SIGNAL CATEGORY'."
        },
        "signal": {
          "type": "string",
          "default": "SIGNAL",
          "description": "Column header for the signal itself in the signals card. English: 'SIGNAL'."
        },
        "stakeholderMap": {
          "type": "string",
          "default": "STAKEHOLDER MAP",
          "description": "Heading of the stakeholder card. English: 'STAKEHOLDER MAP'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "flags": {
      "type": "array",
      "description": "OPTIONAL card 'FLAGS & RISKS'. Include ONLY if the prompt asks about risks/flags/health/what is wrong, or the user asked for a broad catch-up and there are real flags. Omit the key otherwise; never send an empty array. Most severe first.",
      "items": {
        "type": "object",
        "required": [
          "title"
        ],
        "properties": {
          "title": {
            "type": "string",
            "description": "The bold claim of the row: who/what plus the key fact (e.g. 'CFO Priya Anand – No engagement, 3+ weeks', 'Vaultline CRM introduced by procurement'). Rendered bold."
          },
          "context": {
            "type": "string",
            "description": "Optional rest of the title line, rendered after ' – ' in normal weight (e.g. 'Aug 4 · Negative Signal'). Keep it to a few words; put evidence in detail."
          },
          "detail": {
            "type": "string",
            "description": "Small muted line below the title: evidence and consequence, one or two sentences."
          },
          "tone": {
            "type": "string",
            "enum": [
              "error",
              "warning",
              "success",
              "neutral"
            ],
            "description": "Left-rule colour: error (red) = most severe, warning (orange), success (green), neutral (grey) = informational or inactive. Default neutral."
          }
        }
      }
    },
    "openOpportunities": {
      "type": "object",
      "description": "OPTIONAL card 'OPEN OPPORTUNITIES'. Include ONLY if the prompt asks about deals/opportunities/pipeline/forecast, or for a broad catch-up when open deals exist. Omit the key otherwise. Rows carry no links: put the Opportunity record URLs in `sources`.",
      "required": [
        "items"
      ],
      "properties": {
        "items": {
          "type": "array",
          "description": "One row per open opportunity (never an empty array - omit openOpportunities instead).",
          "items": {
            "type": "object",
            "required": [
              "name"
            ],
            "properties": {
              "name": {
                "type": "string",
                "description": "Opportunity name WITHOUT the account prefix: strip a leading '<Account name> - ' / '<Account name> – ' (e.g. 'Joja Corporation - Platform Upsell' -> 'Platform Upsell'). Rendered bold, followed by ' – <summary>'."
              },
              "summary": {
                "type": "string",
                "description": "Amount and close date as ONE phrase in the user's language, written whole because word order differs between languages (e.g. '$640K · closes Aug 31'; French: '640 k$ · clôture le 31 août'). Omit if neither is known."
              },
              "detail": {
                "type": "string",
                "description": "Small muted line: 'Stage · next step · other key notes' (e.g. 'Negotiation / Review · awaiting CFO sign-off'). Do not repeat the amount or close date."
              },
              "tone": {
                "type": "string",
                "enum": [
                  "error",
                  "warning",
                  "success",
                  "neutral"
                ],
                "description": "Left-rule colour by deal health/severity: error (red) = at risk or past due, warning (orange) = needs attention, success (green) = healthy, neutral (grey) = no signal. Default neutral."
              }
            }
          }
        }
      }
    },
    "productsWhitespace": {
      "type": "object",
      "description": "OPTIONAL card 'PRODUCTS & WHITESPACE'. Include ONLY if the prompt asks what the account owns/has bought/expansion/whitespace, or for a broad catch-up when product data exists. Every list must come from the product queries you ran (Closed Won line items / Assets, open-opportunity line items, active catalog families). Omit any list you have no data for, and omit the key when all three are empty.",
      "properties": {
        "purchased": {
          "type": "array",
          "description": "Products/clouds already owned, from Assets or Closed Won opportunity products (light-blue chips). Short product or family names.",
          "items": {
            "type": "string"
          }
        },
        "opportunities": {
          "type": "array",
          "description": "Products in open deals (shown on the OPPORTUNITIES row, outline chips), as 'Product · $amount' when the line has an amount, e.g. 'Enterprise Sales Cloud · $640K'.",
          "items": {
            "type": "string"
          }
        },
        "whitespace": {
          "type": "array",
          "description": "Catalog product families the account neither owns nor has in play (grey chips). At most 6.",
          "items": {
            "type": "string"
          }
        }
      }
    },
    "signals": {
      "type": "array",
      "description": "OPTIONAL card 'REASONS TO REACH OUT'. Include ONLY if the prompt asks for triggers/news/signals/reasons to reach out/what changed, or for a broad catch-up when real signals exist. Omit the key otherwise; never an empty array. Rows carry no links: put source URLs in `sources`.",
      "items": {
        "type": "object",
        "required": [
          "title"
        ],
        "properties": {
          "category": {
            "type": "string",
            "description": "Short tag shown in a small grey uppercase chip on the left, in the user's language. Prefer: Earnings, Exec hire, Board, News, Email, Doc, Slack, Call."
          },
          "title": {
            "type": "string",
            "description": "Bold headline: the event and its date (e.g. 'Q2 earnings call · Aug 12'). Rendered bold. Plain text, no markdown."
          },
          "context": {
            "type": "string",
            "description": "Rest of the headline, rendered after ' – ' in normal weight (e.g. 'CFO Priya Anand called out efficiency initiatives as a 2H priority.'). Plain text, no markdown."
          },
          "detail": {
            "type": "string",
            "description": "Small muted line: why it matters / how to use it in outreach."
          }
        }
      }
    },
    "stakeholders": {
      "type": "array",
      "description": "OPTIONAL card 'STAKEHOLDER MAP'. Include ONLY if the prompt asks about contacts/stakeholders/champions/buying committee/who to talk to, or for a broad catch-up when contacts exist. Omit the key otherwise; never an empty array.",
      "items": {
        "type": "object",
        "required": [
          "name"
        ],
        "properties": {
          "name": {
            "type": "string",
            "description": "Contact name (bold). Struck through when status is 'inactive'."
          },
          "detail": {
            "type": "string",
            "description": "ONE muted line in the user's language: 'Title · role in the deal · last touch <date>' written whole (e.g. 'CFO · Economic Buyer · last touch Aug 8'; French: 'DAF · Décideur économique · dernier contact 8 août'). Omit parts you do not know."
          },
          "status": {
            "type": "string",
            "enum": [
              "inactive"
            ],
            "description": "Set to 'inactive' for a departed contact (name struck through). Omit otherwise."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something is time-sensitive AND the user can act on it. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period)."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences of normal-weight text that follow the bold lead on the same line: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Send re-engagement via Katie')."
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
      "description": "REQUIRED. Where the answer came from: the Salesforce records/lists you actually read, linked (this is where Opportunity/Account record links go). Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Account – Cedarline Financial', 'Open opportunities list')."
          },
          "url": {
            "type": "string",
            "description": "Record or list-view URL. Omit if none."
          }
        }
      }
    }
  }
}
```


## 6. Synthesize — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Lead with current state, not raw data. Omit any section whose source wasn't available. When email/docs/Slack connectors are absent, those sections are empty *by necessity* — note it once at the end (`Note: email/docs/Slack not connected`), don't imply the account is quiet everywhere.

```
# Account Context: [Account Name]

## Current State
[2-3 sentences: where this account is, what's active, the headline]

## Salesforce
- **Owner:** [Name] · **Profile:** [Industry] | [Employees] | [Type][ | custom health/tier if present]
- **Open opps:** [N], $[total]
  - **[Opp Name]** — [Stage] $[Amount] closes [Date] | Next: [NextStep]
- **Recent closed:** [Won/Lost] [Name] $[Amount] ([Date])
- **Last activity:** [Date] — [Subject]

## Key Contacts
| Name | Title | Last Touch | Notes |
|---|---|---|---|

## Recent Correspondence (email)
- [Date] — [Subject] with [Names] — [one-line]

## Documents
- [Title] ([type], modified [Date])

## Internal Chatter (Slack)
- [#channel] [Date] — [one-line] [link]

## Gaps / Flags
- [e.g. "No activity in 30d on $XXk opp" · "NextStep blank" · "single-threaded — 1 contact"]

## Ask the Owner
[If the requester is NOT the owner — draft a Slack DM to the owner. Conversational, lowercase opener, references the specific opp $ and one detail above, offers help. Offer to send it as a Slack draft.]

> hey — was looking at [Account], saw the $[X] opp at [stage]. [one specific detail]. anything you need from me on it?
```
