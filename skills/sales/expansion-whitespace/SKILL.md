---
name: expansion-whitespace
display_name: Expansion Whitespace
description: "Answer questions about expansion whitespace, scoped to what was asked: coverage of products by account, open white space to pitch, ranked expansion plays, from Salesforce contacts, owned products and opportunities plus recent email, documents and Slack. Use to find evidence-backed whitespace, upsell paths or adjacent teams and products ready for outreach."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:4deb316b76092563ed05419cad86a4e651eb24cd7d10f8f06616cdf18c89245a"
id: "d29a21ce-1ded-4752-8e8e-768dfdd635b6"
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
Answer what the user asked about expansion whitespace (product coverage across their accounts, open white space to pitch, or ranked plays) in one pass. **Read only what the question needs** and present only that: a broad sweep ("where's my expansion whitespace this quarter?") reads and shows the whole book; a specific ask ("what white space does Orion Manufacturing have?", "which of my accounts own Marketing Cloud?") reads and shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full whitespace report.** A broad sweep reads and shows the whole book; a specific ask reads and shows only that. Skip reads the question doesn't need (each read step says which), and don't show something just because you fetched it.
- **Expansion Whitespace text contract.** Aside from the exact required pre-widget notice, the text fallback is the only permitted prose, and it must start with `# Expansion Whitespace`.

# Expansion Whitespace

Resolve account → ground → read → extract products → map whitespace → output. Product catalog derived from OpportunityLineItems — limited to top 5-7 by revenue.

## 1. Resolve the account

Shared/demo orgs collide on name. If user gave Salesforce Id, skip to Step 2. Otherwise:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 10) { edges { node { Id Name { value } Website { value } Type { value } Industry { value } Owner { Name { value } } } } } } } }\"}" })
```

**One match** → take its Id, continue to Step 2.

**Several** → STOP. Before Step 2, determine which account:
- **If user provided $amount or seat count:** Search Opportunities across ALL candidate account Ids to find which has matching renewal/deal:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
    queryParams: { "q": "SELECT Id, AccountId, Account.Name, Name, Amount, CloseDate, StageName FROM Opportunity WHERE AccountId IN ('<ID1>','<ID2>',...) AND (Amount = <USER_AMOUNT> OR Name LIKE '%<USER_PRODUCT>%' OR CloseDate >= TODAY) ORDER BY CloseDate DESC LIMIT 50" })
  ```
  Match by Amount or product name. Take that AccountId, continue to Step 2.

- **Else:** List candidates (Name · Website/Industry · Owner · Id) and ask user to pick.

**None** → broaden name or ask for correct account. Don't guess.

## 2. Ground (hardcoded — Account + Contact)

A direct ownership or coverage ask ("does Summit own Data Cloud?", "which of my accounts own Marketing Cloud?") skips this step and Dispatch A: it needs only the product reads below.

Ground **Account + Contact** (both always exist). Lean projection discovers this org's custom fields without the full schema payload. **Fire as two separate calls** (combined ObjectInfo often overflows):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { fields { ApiName label } } } }\"}" })
```

From the results: note scalar `__c` fields (Success_Segment, License_Utilization, Job_Function, Job_Level, etc.) — take their `{ value }` in the read queries. Without `dataType`/`relationshipName`, you can't perfectly distinguish scalar vs reference fields, but most customs are scalar; reference fields that slip through will show Ids (cryptic but not broken). Standard relationships (`Account`, `Owner`, `Contacts`, `ChildAccounts`) are hardcoded in queries below.

## 3. Read (fill from steps 1–2)

Insert `<ACCOUNT_CUSTOM>` = confirmed scalar `__c { value }` fields on Account; `<CONTACT_CUSTOM>` = confirmed scalar `__c { value }` fields on Contact (role, department, etc.).

**Fire the separate dispatches (A, B and C) in ONE turn** (parallel, no dependency), skipping those the ask doesn't need. Triple-nesting (Account > Opportunities > OpportunityLineItems) commonly fails; split avoids errors.

**Dispatch A — Account + Contacts + ChildAccounts:**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } AnnualRevenue { value displayValue } <ACCOUNT_CUSTOM> Contacts(first: 30) { edges { node { Name { value } Title { value } <CONTACT_CUSTOM> } } } ChildAccounts { edges { node { Name { value } Industry { value } Owner { Name { value } } } } } } } } } } }\"}" })
```

**Dispatch B — Won Opportunities + line items (the actual products/SKUs owned):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Account: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, IsWon: { eq: true } }, first: 30, orderBy: { CloseDate: { order: DESC } }) { edges { node { Name { value } Amount { value } CloseDate { value } StageName { value } Description { value } OpportunityLineItems(first: 50) { edges { node { Quantity { value } TotalPrice { value displayValue } Product2 { Name { value } } } } } } } } } } }\"}" })
```

The `OpportunityLineItems` child (span `Product2` for the SKU name, with `Quantity`/`TotalPrice`) is the real "Owned today" input for the Step 4 grid — one read, no extra round-trip (this is a single child level, not the triple-nesting that overflows). Fall back to `Opportunity.Name` only if the org doesn't use line items (empty `edges`).

**Dispatch C — Open and Closed Lost Opportunities + line items (the coverage matrix's `inPlay` and `lost` cells):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Account: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, IsWon: { eq: false } }, first: 30, orderBy: { CloseDate: { order: DESC } }) { edges { node { Name { value } Amount { value displayValue } CloseDate { value } StageName { value } IsClosed { value } Account { Name { value } } OpportunityLineItems(first: 50) { edges { node { TotalPrice { value displayValue } Product2 { Name { value } } } } } } } } } } }\"}" })
```

Cell state per account and product: `purchased` = line item on a won Opportunity (Dispatch B); `inPlay` = line item on an open Opportunity (`IsClosed` false); `lost` = Closed Lost Opportunity with no purchased or open line item for that product; `whitespace` = only if step 4's evidence rule is met; `empty` otherwise.

Scoping: an own-a-product ask for named accounts needs B alone; a "which accounts own, are pursuing or lack X" ask needs B and C; Dispatch A only when contacts or child accounts feed the answer (white space, plays). For a book sweep, fire B and C with the book scope instead of the account filter.

For book-level sweep: replace Dispatch A `where: { Id: { eq: ... } }` with `scope: MINE` or team filter, limit 20.

## 3b. Evidence (run IN PARALLEL with step 3 — same turn)

**Issue step 3 and all of step 3b as tool calls in a single turn.** They're independent (searches key on account name, not the SF result):
- **email**: threads mentioning teams/use-cases/products not yet sold, **plus recent events/invites/webinars as timing hooks**
- **docs**: recent transcripts/notes → teams/departments mentioned, **job changes, new projects**
- **slack**: internal mentions → expansion plays discussed

Run this only when the ask needs white space or plays; a coverage or direct ownership ask skips it.

Use whatever email/doc/Slack search tools are available. If none present, skip silently (SF-only is fine). Cite source + date for anything you use. **Prioritize evidence from last 90 days for recency/relevance.**

## 3.5. Extract product catalog

From the OpportunityLineItems fetched in steps 3 (Dispatch B and Dispatch C), extract and rank products:

1. **Collect all Product2.Name values** from won opportunities (Dispatch B) and open/lost opportunities (Dispatch C if using HXL widgets)
2. **Aggregate by product name**: For each unique product, calculate:
   - Total revenue (sum of all TotalPrice values)
   - Frequency (count of OpportunityLineItems)
3. **Rank products** by: (1) total revenue DESC, (2) frequency DESC
4. **Take top 5-7 products only** to ensure mobile compatibility
5. **Fallback**: If fewer than 3 products with line items, parse `Opportunity.Name` fields for product keywords (Sales Cloud, Service, Marketing Cloud, Data Cloud, Agentforce, Revenue, Commerce, etc.)
6. **Normalize names**: Strip common prefixes ("Salesforce ", "SFDC ") to get short display names

Use this extracted, limited product list for the coverage matrix and whitespace analysis.

## 4. Map whitespace

Map and rank only what the prompt needs: a coverage ask needs the cell states above, not the dimension grid, ranking or plays.

**Product catalog (derived):** Use the top 5-7 products extracted in step 3.5. Build owned-vs-possible grid:

| Dimension | Owned today | Whitespace | Evidence |
|---|---|---|---|
| Products / SKUs | [SKUs owned, from Dispatch B's OpportunityLineItems (Product2 name · Quantity · TotalPrice); fall back to Opportunity.Name only if no line items] | [catalog items they haven't] | [need signal: mentioned in calls/emails? industry-typical?] |
| Teams / departments | [all contacts from Contacts child: name + title, not just technical subset] | [adjacent teams named in transcripts] | |
| Geography / subsidiaries | [entities under contract, plus reseller contacts if Account Type = reseller] | [child accounts with no spend] | |
| Volume / tier | [seats or usage from `__c`, penetration as exact % = seats/NumberOfEmployees] | [headroom vs employee count or benchmark, Success_Segment__c gap if present] | |

**Only call something whitespace if there is at least one piece of evidence** (stakeholder mentioned the team, transcript named the use case, org structure shows the entity). "They could theoretically buy everything" is not a finding.

## 4b. Cross-dimensional analysis (no extra dispatches — use data already fetched)

**Contact-to-product gap:** Cross-match contact titles/roles against owned products. Flag senior/exec/C-suite titles NOT reflected in product ownership (e.g., CIO with no BI tool seat, VP Sales with no CRM license = upsell hook).

**Child account routing:** For ChildAccounts with different Owner than parent, note AE-to-AE warm intro path (e.g., "Parent CIO → intro to Child Account Owner [Name]").

**Evidence gate:** Render or rank a play only when one evidence record contains a user-supplied catalog item or a product/use case directly named by a dated source, the exact target team/subsidiary/use case named by that source, and `source · date — exact supporting fact`. A contact title, industry, employee count, account health, Opportunity/line-item name or value, or ChildAccount alone does not establish a product-to-target relationship. Treat `Opportunity.Amount` and `OpportunityLineItems.TotalPrice` only as account/product history: never allocate them to a person, team, department, or child account, call them ARR, or derive a value or range without a dated cited source that supplies the explicit mapping and annual-recurring or expansion basis. No qualifying record means no evidence-backed play.

**Motion gate:** `Warm intro` requires dated evidence that an existing contact can introduce a distinct target person or team. If the contact is the target or belongs to the target team, use `Research / re-engage`. `Renewal add-on` requires a returned or dated cited active renewal.

## 5. Rank plays

**Prioritize by sales motion complexity, not just $ size:**
1. **Renewal add-ons** (bundle into active renewal — lowest friction)
2. **Warm intro expansions** (existing contact opens door — medium friction)
3. **Cold new products** (no prior relationship — highest friction)

When evidence strength equal, prefer lower friction. Score on evidence strength, deal size potential, and access. **For reseller/partner accounts in "Owned today", name individual contacts, not just entity.** Top plays get a one-line motion: who to approach, with what message, anchored on which existing success.


## 6. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] Every populated row contains Play, Target, Evidence (`source · date — fact`), and Next step.
- [ ] The no-evidence state has an empty row array and the exact no-play callout.

**Widget transport:** Pass the fully hydrated renderer to `display_widget` as a direct top-level tool call whose `widgetDefinition` is a native JSON object. Never serialize or quote it, and never build or send it through generated code, a shell, a code runner, or temporary files. A returned string, printed preview, or generated file is not a mounted visual and is never a successful render. If the call succeeds, it is the terminal output: stop with no further assistant text. If it returns an error or the tool is unavailable, do not retry, repair, or create a substitute artifact; emit only the section 7 text fallback and stop, and never claim the widget rendered.
- ❌ WRONG: `widgetDefinition: "{\"key\":...}"` (stringified with escaped quotes)
- ✅ RIGHT: `widgetDefinition: {"key":...}` (native object, no quotes around the opening brace)

**Widget gate:** Call `display_widget` once. Every row must satisfy the evidence gate and visibly include its source/date. A direct target uses `Research / re-engage`, not `Warm intro`. With no qualifying record, use `datagridRows: []`, the exact callout `No evidence-backed expansion play identified`, and one request for the missing catalog or dated source. Never add a heatmap, pie, allocation, ARR, fit score, monetary estimate, draft-expansion action, or Opportunity proposal.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/expansion-whitespace", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 7 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`title`, `answer`, `whyNow`, `actionMsg`, `note`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Broad ("Where's my expansion whitespace this quarter?", "expansion whitespace", "where can I expand?") | `title` + `answer` (bullets) + `coverage` + `whitespace` + one tail (`callout` or `suggestedAction`) + `sources` |
| Specific, one account ("What white space does Orion Manufacturing have?") | `title` + `answer` (paragraph) + `whitespace` only + `sources` |
| Specific, coverage ("Which of my accounts own Marketing Cloud?") | `title` + `answer` (paragraph) + `coverage` only (just the products asked about) + `sources` |
| Direct ("Does Summit Health Partners own Data Cloud?") | `title` + `answer` (paragraph) + `sources` — no card, no tail |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for or that does not speed up the answer.
- **Scope the `answer` too:** answer only what was asked; do not restate the cards below it.
- **`coverage`:** `products` are the columns, `accounts` the rows, and `cells` lists only the non-empty pairs: `x` is exactly one entry of `products`, `y` exactly one entry of `accounts`, and a pair you leave out renders as empty. Cell `state` follows the Dispatch C rules in step 3: `purchased` (closed-won product), `inPlay` (open opportunity), `lost` (Closed Lost), `whitespace` (gap worth pitching). `label` is the display-ready amount ("$220K") on `purchased` and `inPlay` cells only; omit it for `whitespace` (dashes) and `lost` (the Closed Lost legend text).
- **`whitespace`:** a row only for a gap that meets step 4's evidence rule (a stakeholder, transcript or org-structure signal); warmest first; `actionMsg` is a first-person request. Never a product the account already owns or is pursuing.
- **Tail fork:** `callout` when one move is time-sensitive and the user can act on it (one button, a first-person `actionMsg`); otherwise a `suggestedAction` line, which is the normal choice for white space; if nothing applies, neither. Never both (if both are sent only the callout renders). A direct or coverage-only ask usually gets no tail.
- **Sources:** a record is `https://<myDomain>/lightning/r/<SObjectType>/<Id>/view`; the book is `https://<myDomain>/lightning/o/Account/list`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string (currency such as "$220K", dates). Names are plain strings, never objects.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included (`labels`, `coverage`, `whitespace`, `callout`, `suggestedAction`) is justified by the prompt.

#### Worked examples (the `props` object only)

**Specific — "What white space does Orion Manufacturing have?"** (a paragraph answer, only the white space card, a `suggestedAction` tail):

```json
{
  "title": "Orion Manufacturing has open white space in Data Cloud and Tableau.",
  "answer": "Orion owns **Sales Cloud ($160K)** and nothing else. The one gap I'd pitch is **Data Cloud + Tableau**: a CIO discussion is open but there is no formal opportunity yet.",
  "whitespace": {"rows": [{"account": "Orion Manufacturing", "product": "Data Cloud + Tableau", "whyNow": "Discussion open with the CIO; no formal opportunity yet. Q4 target.", "actionMsg": "Create an opportunity for Data Cloud + Tableau on Orion Manufacturing."}]},
  "suggestedAction": {"lead": "Open the Data Cloud conversation with the CIO.", "text": "Orion is your warmest white space with a Q4 target. Want me to draft the pitch?"},
  "sources": [{"label": "Account: Orion Manufacturing"}, {"label": "Opportunities and products"}]
}
```

**Specific — "Which of my accounts own Marketing Cloud?"** (a paragraph answer, only the `coverage` card for the one product, no tail; accounts trimmed here):

```json
{
  "title": "None of your 6 accounts own Marketing Cloud yet – two are pursuing it.",
  "answer": "No account has **purchased Marketing Cloud**. **Vantage Retail Group ($520K)** and **Brightwave Media ($410K)** have open opportunities, and Northpeak's pitch came back Closed Lost.",
  "coverage": {
    "products": ["Marketing"],
    "accounts": ["Vantage Retail Group", "Brightwave Media", "Northpeak Logistics", "Orion Manufacturing"],
    "cells": [
      {"x": "Marketing", "y": "Vantage Retail Group", "state": "inPlay", "label": "$520K"},
      {"x": "Marketing", "y": "Brightwave Media", "state": "inPlay", "label": "$410K"},
      {"x": "Marketing", "y": "Northpeak Logistics", "state": "lost"}
    ]
  },
  "sources": [{"label": "Accounts · 6 in book of business"}]
}
```

**Direct — "Does Summit Health Partners own Data Cloud?"** (a paragraph answer, no card, no tail):

```json
{
  "title": "No – Summit Health Partners doesn't own Data Cloud yet.",
  "answer": "Summit owns **Sales Cloud ($140K)** and **Service ($110K)**. Data Cloud is open white space with no opportunity created.",
  "sources": [{"label": "Account: Summit Health Partners"}]
}
```


`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (coverage, whitespace), then at most one tail (callout OR suggestedAction), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A direct question ('does Summit Health own Data Cloud?') usually gets no tail. Format every value as a ready-to-display string (currency, dates); names are plain strings, never objects.",
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
        "coverage": {
          "type": "string",
          "default": "Product Whitespace by Account",
          "description": "Heading of the coverage matrix card. English: 'Product Whitespace by Account'."
        },
        "colAccount": {
          "type": "string",
          "default": "Account",
          "description": "White space table header. English: 'Account'."
        },
        "whitespace": {
          "type": "string",
          "default": "Open White Space",
          "description": "Heading of the white space card. English: 'Open White Space'."
        },
        "colProduct": {
          "type": "string",
          "default": "Product",
          "description": "White space table header. English: 'Product'."
        },
        "colWhyNow": {
          "type": "string",
          "default": "Why now",
          "description": "White space table header. English: 'Why now'."
        },
        "colSuggestedAction": {
          "type": "string",
          "default": "Suggested Action",
          "description": "White space table header. English: 'Suggested Action'."
        },
        "createOpportunity": {
          "type": "string",
          "default": "Create Opportunity",
          "description": "Label of each white space row button. English: 'Create Opportunity'."
        },
        "legendPurchased": {
          "type": "string",
          "default": "Purchased",
          "description": "Legend entry for purchased cells. English: 'Purchased'."
        },
        "legendInPlay": {
          "type": "string",
          "default": "Opportunities",
          "description": "Legend entry for cells with an open opportunity. English: 'Opportunities'."
        },
        "legendWhitespace": {
          "type": "string",
          "default": "White Space",
          "description": "Legend entry, also the text of a white space cell. English: 'White Space'."
        },
        "legendLost": {
          "type": "string",
          "default": "Closed Lost",
          "description": "Legend entry, also the text of a Closed Lost cell. English: 'Closed Lost'."
        },
        "legendEmpty": {
          "type": "string",
          "default": "Empty",
          "description": "Legend entry for empty cells. English: 'Empty'."
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
      "description": "REQUIRED. The takeaway in the user's context, one bold sentence that already answers the question (e.g. 'You have 3 expansion opportunities in flight worth $1.38M – plus open white space across 3 more accounts.'). Never the skill name or 'Expansion Whitespace'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (counts, amounts, account names). A broad sweep gets 2-4 short '- ' bullets; a direct or specific question ('does Summit own Data Cloud?') gets a 1-3 sentence paragraph. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "coverage": {
      "type": "object",
      "description": "OPTIONAL card 'Product Whitespace by Account': a matrix of accounts (rows) by clouds (columns), each cell one state. Include ONLY for a broad sweep or when the prompt asks which accounts own, are pursuing or lack a product. Omit the key otherwise; never empty arrays.",
      "required": [
        "products",
        "accounts",
        "cells"
      ],
      "properties": {
        "products": {
          "type": "array",
          "description": "Column headers, one short name per cloud, in display order (e.g. ['Sales Cloud','Service','Marketing','Data Cloud','Agentforce','Revenue']). **Limited to top 5-7 products by revenue to ensure mobile compatibility.** Shown uppercase. Each cell's x must be one of these, spelled identically.",
          "items": {
            "type": "string"
          }
        },
        "accounts": {
          "type": "array",
          "description": "Row headers, one account name per row, in the order the answer discusses them (e.g. 'Cedarline Financial'). Each cell's y must be one of these, spelled identically.",
          "items": {
            "type": "string"
          }
        },
        "cells": {
          "type": "array",
          "description": "One entry per non-empty cell. Any account/product pair you leave out renders as an empty cell, so send only purchased, inPlay, whitespace and lost pairs.",
          "items": {
            "type": "object",
            "required": [
              "x",
              "y",
              "state"
            ],
            "properties": {
              "x": {
                "type": "string",
                "description": "Product column: exactly one entry of products."
              },
              "y": {
                "type": "string",
                "description": "Account row: exactly one entry of accounts."
              },
              "state": {
                "type": "string",
                "enum": [
                  "purchased",
                  "inPlay",
                  "whitespace",
                  "lost",
                  "empty"
                ],
                "description": "'purchased' = closed-won product, 'inPlay' = open opportunity, 'whitespace' = recommended gap with no opportunity yet, 'lost' = Closed Lost opportunity, 'empty' = nothing to show."
              },
              "label": {
                "type": "string",
                "description": "OPTIONAL. Display-ready amount for 'purchased' and 'inPlay' cells (e.g. '$220K'). Omit for the other states: whitespace shows dashes and lost shows the Closed Lost legend text."
              }
            }
          }
        }
      }
    },
    "whitespace": {
      "type": "object",
      "description": "OPTIONAL card 'Open White Space': accounts and products worth pitching, each with a Create Opportunity button. Include ONLY for a broad sweep or when the prompt asks where to expand or what to pitch. Omit the key otherwise; never an empty rows array.",
      "required": [
        "rows"
      ],
      "properties": {
        "note": {
          "type": "string",
          "description": "OPTIONAL. One or two sentences under the heading: why there is no dollar amount and any common thread (e.g. 'These are open gaps I'd recommend pitching – there's no dollar amount because nothing is in motion. Data Cloud is the common thread across all three.')."
        },
        "rows": {
          "type": "array",
          "description": "One row per gap, warmest first (never an empty array - omit whitespace instead).",
          "items": {
            "type": "object",
            "required": [
              "account",
              "product",
              "whyNow",
              "actionMsg"
            ],
            "properties": {
              "account": {
                "type": "string",
                "description": "Account name (e.g. 'Orion Manufacturing')."
              },
              "product": {
                "type": "string",
                "description": "Product to pitch (e.g. 'Data Cloud + Tableau')."
              },
              "whyNow": {
                "type": "string",
                "description": "One sentence on why this account and why now (e.g. 'Discussion open with the CIO; no formal opportunity yet. Q4 target.')."
              },
              "actionMsg": {
                "type": "string",
                "description": "First-person request sent to chat when Create Opportunity is clicked (e.g. 'Create an opportunity for Data Cloud + Tableau on Orion Manufacturing.')."
              }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. A bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of suggestedAction, never both (if both are sent only the callout renders). Include only if one move is time-sensitive (a close date is days away) AND the user can act on it now. White space is rarely time-sensitive: prefer suggestedAction. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the stake in one sentence, ending with a period, e.g. '$930K of Marketing Cloud closes within two weeks.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Build the Vantage Marketing play')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        }
      }
    },
    "suggestedAction": {
      "type": "object",
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button. Use INSTEAD of callout, never both.",
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead (the suggested move, e.g. 'Protect the two Marketing Cloud opportunities already in flight.')."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning, ending with an offer to help if natural."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: the Salesforce records/lists you actually read, linked. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name: object · record (e.g. 'Accounts · 6 in book of business', 'Account: Vantage Retail Group')."
          },
          "url": {
            "type": "string",
            "description": "Record URL https://<myDomain>/lightning/r/<SObjectType>/<Id>/view, or for a list https://<myDomain>/lightning/o/Account/list. Omit if none."
          }
        }
      }
    }
  },
  "additionalProperties": false
}
```




## 7. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask ("what white space does Orion Manufacturing have?", "which of my accounts own Marketing Cloud?") gets only the sections that answer it, not the whole report below.

Use only when the evidence-first widget is unavailable or errors.

```
# Expansion Whitespace: [Account / scope] — [Account Lightning link]

## Evidence-backed plays
1. **[Play]** — target: [team / subsidiary / use case]
   - Evidence: [source · date — exact supporting fact]
   - Motion: [Renewal add-on / Warm intro / Research / re-engage] — [cited reason]

If no evidence record qualifies, write exactly: `No evidence-backed expansion play identified.`

## Missing evidence
- [Catalog item, product-to-target mapping, dated customer source, or value basis]

## Next safe step
[Ask once for the missing catalog or a dated customer source naming the target and use case.]
```

Never show an unsupported allocation, ARR, monetary estimate, contact-spend relationship, or Opportunity proposal.
