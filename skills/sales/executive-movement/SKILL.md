---
name: executive-movement
display_name: Executive Movement (Preview)
description: "Answer executive-change questions scoped to what was asked: a sweep of your accounts, one account, or one executive. Confirms moves against dated external sources, ties them to Salesforce contacts, accounts and open deals, and recommends the follow-up. Use to catch leadership changes, assess relationship risk or growth when a known contact moves, or prepare outreach. Separates confirmed changes from unverified signals and never writes to the CRM."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:7903a2e47de95182e48f237d021ed8a822751475cc1f895e5ff22f267cb6bcc2"
id: "11019627-a7e7-48ae-9f8e-aa9bad7c913e"
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

- **Scope reading and output to the prompt, never a default full sweep.** A portfolio question reads open deals and researches the top accounts; one account or one executive reads only that scope. Show only the blocks the question needs, and never show a block merely because data was fetched.
- **Confirmed vs. unconfirmed is a hard line.** A change is confirmed only when a dated statement from a reputable outlet, a connected data provider (e.g. BoardEx, ZoomInfo) or the company itself says so. Anything else is mixed (sources or the CRM conflict) or unconfirmed. Always show source, change date (when known) and freshness. Never invent a change, a source or a date.
- **Read-only; never overwrite the CRM.** Record updates are proposals for confirmation or stewardship review. Preserve prior affiliations and history, and flag conflicts rather than replacing data. Say plainly that nothing was written.

# Executive Movement

Scope (portfolio / one account / one executive) → ground Contact + Account → read CRM (ONE turn) → research externally (ONE turn) → verify, prioritize → render. Everything here reads and recommends; nothing is a completed action.

## 1. Scope the request

- **Portfolio** ("any executive changes at my accounts?") → Step 3a, `scope: MINE`.
- **One account** (name, Id, or a pasted record URL) → Step 3b.
- **One executive** (name, plus company if ambiguous) → Step 3c.

Default review period: **last 6 months**; use the user's period when given. Ask once, in a single message, only when an account or executive is ambiguous or a name matches several records; never guess an executive, company or move.
A narrow ask skips the other scopes' reads, the Account ObjectInfo when no account fields are needed, and external research on accounts outside the question.

## 2. Ground Contact + Account (ONE turn, parallel)

Both always exist (naming a missing object fails the whole call); their `__c` fields reveal this org's relationship schema (buying role, relationship owner, prior account, tier/segment).

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

Scan each result by eye; do not script it. If it overflows or comes back truncated, skip custom-field grounding and proceed with standard fields only; don't keep retrying. Select the scalar `__c` fields carrying relationship signal and add them as `<CONTACT_CUSTOM>` / `<ACCOUNT_CUSTOM>`.

## 3. Read the CRM (fire the reads for your scope in ONE turn)

**3a. Portfolio.** "My accounts" means the accounts on the user's own open opportunities. Read them, rank accounts by total open amount, and keep the **top 10**. An empty result follows the `MINE` rule in the global rules: stop and ask which scope.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Account { Id Name { value } <ACCOUNT_CUSTOM> } } } } } } }\"}" })
```

Then read the contacts of those accounts (one call, `Id: { in: [...] }`, `first: 10` accounts, `Contacts(first: 25)`):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { in: [<ACCOUNT_IDS>] } }, first: 10) { edges { node { Id Name { value } Owner { Name { value } } Contacts(first: 25) { edges { node { Id Name { value } Title { value } Email { value } LastActivityDate { value } <CONTACT_CUSTOM> } } } } } } } } }\"}" })
```

**3b. One account.** Read the account, its contacts and its open opportunities:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { <ACCOUNT_FILTER> }, first: 5) { edges { node { Id Name { value } Industry { value displayValue } <ACCOUNT_CUSTOM> Owner { Name { value } } Contacts(first: 50) { edges { node { Id Name { value } Title { value } Email { value } LastActivityDate { value } <CONTACT_CUSTOM> } } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 20) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } } } } } } }\"}" })
```

`<ACCOUNT_FILTER>` = `Id: { eq: \\\"<ACCOUNT_ID>\\\" }` or `Name: { like: \\\"%COMPANY%\\\" }`.

**3c. One executive.** Find the contact, its account, owner, open deals, and any same-name contact under another account (a prior affiliation the firm already knows; keep them all as history):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { <CONTACT_FILTER> }, first: 10) { edges { node { Id Name { value } Title { value } Email { value } LastActivityDate { value } <CONTACT_CUSTOM> Account { Id Name { value } <ACCOUNT_CUSTOM> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } } } } } } } }\"}" })
```

`<CONTACT_FILTER>` = `Name: { like: \\\"%NAME%\\\" }`, `Email: { eq: \\\"<EMAIL>\\\" }`, or `and: [{ Name: { like: \\\"%NAME%\\\" } }, { Account: { Name: { like: \\\"%COMPANY%\\\" } } }]`.

When an executive moves **to** a company, resolve that destination account too (same Account shape). If it is not in the CRM, say "new company not in CRM": that is a growth opening.

## 4. Research externally (same turn as Step 3)

Default to the web-search tools for the external check. If a connected data provider (e.g. BoardEx, ZoomInfo) is available, use it as a supplement to corroborate or date a finding, never as the only source. If no research tool exists, skip it and say the external check could not run. Search each contact (by name and company) in scope, newest first, within the review period. For every change keep attached through to output:

- **Former** and **new** role or affiliation, and the **change date** when stated.
- **Source** and **freshness**: very fresh (14 days or less), fresh (90 days or less), dated (older). Freshness is measured from the change date, else the publication date.
- **Status**: `confirmed`, `mixed` or `unconfirmed` (definitions in the Rules). Keep both claims when sources conflict, and when the CRM title disagrees with a confirmed source. Quote a missing date as unknown; never fill it in.

Match each external change to CRM contacts by name plus company, never by name alone; when the match is uncertain say so in `executiveDetail`.

## 5. Prioritize and assess

Rank by material impact: relationship significance (owner, activity, buying role, prior affiliations), account importance (tier, segment), and open-opportunity exposure (amount, stage, close date). For each change state the **risk** (e.g. the only mapped contact or economic buyer leaving before a close date) or the **growth** opening (a known buyer landing at a target account) and a specific next move with a suggested owner. A contact missing from the CRM for a confirmed change is a net-new relationship opportunity.

Prepare record updates as proposals only, with a "needs confirmation" marker on anything unverified or in conflict.

## 6. Render — widget first

Call `display_widget` immediately after assembling the changes. Do not write markdown first — only fall back to Step 7 when the tool is unavailable. A single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/executive-movement", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (layout, HTML, colors, badges, icons, or `{!…}` / `{{…}}` expressions).
- **`props` is a nested JSON object, NOT a string.** Parse a JSON string before the call.
- The widget is the output. Step 7 is only a fallback when `display_widget` is unavailable or fails.

### What to send

Follow the block order and inclusion rules in the schema below, in this fixed order:

1. `title` (required): one sentence answering the question, leading with the most material change. Never the skill name.
2. `answer` (required): 2-4 short `- ` bullets with **bold** counts, accounts and dates; empty only when the title fully answers.
3. `executiveChanges` (optional): the table of changes, most material first, verification pill and rail per row.
4. `relationshipMap` (optional): contact cards with an explicit stance pill; account scope only.
5. `stakeholders` (optional): Stakeholder / Role / Change / Next step; account scope only.
6. `callout` OR `nextStep` (optional): never both.
7. `sources` (required): the Salesforce records and external articles actually read.

**Language:** when the user writes in English, omit `labels`. For any other language, send every `labels` key translated (headings in upper case) and write all free text in that language. Never join translated text with English fragments.

### Scope the blocks to the prompt

| The prompt is… | Send |
|---|---|
| Portfolio (e.g. "Any executive changes at my accounts I should know about?") | `title` + `answer` + `executiveChanges` + `callout` when a change threatens a dated deal, else `nextStep` + `sources` |
| One account (e.g. "What are the executive movements at Cedarline Financial?") | `title` + `answer` (may be empty) + `relationshipMap` + `stakeholders` + `nextStep` or `callout` + `sources` |
| One executive (e.g. "Did Jordan Reyes leave Cedarline?") | `title` + `answer` + one `executiveChanges` row + `nextStep` + `sources`; no other card |
| Direct (e.g. "Who replaced the CFO at Orion?") | `title` + `answer` + `nextStep` if a concrete move is supported + `sources` |

Rules:
- Omit a key and its block is not shown. Never send empty arrays, placeholders, "N/A" or unrelated cards. When nothing changed in scope, send `title` + `answer` saying so (and that the external check covered the period) + `sources`.
- Counts in the title and answer are computed from the rows you send. Order rows by impact, and keep `maxItems` (8 changes, 6 contacts).
- Visible names and values are plain strings extracted from `.value` fields. Never send response objects, markdown links or raw Lightning URLs in visible text; put a record URL only in a source `url`.
- `relationshipMap` stance is `Unknown` unless a grounded stance or buyer-relationship value exists. A champion needs demonstrated advocacy, not a supportive tone.
- The tail is exclusive: `callout` only for a time-sensitive action (level `note`, never `blocker`), with at most one primary button whose `actionMsg` is first-person; otherwise `nextStep`, usually an offer to draft outreach.
- Before calling, verify no `{!…}` or `{{…}}` in `props`, no keys outside the schema, and every optional key is justified by the prompt.

#### Worked examples (the data object only)

The names, amounts and dates below are illustrative; every value comes from the records and sources actually read.

**Portfolio — "Any executive changes at my accounts I should know about?"**

```json
{
  "title": "3 leadership changes across your accounts in the last 6 months – and your only contact at Cedarline just left, 2 weeks before a $640K renewal.",
  "answer": "- **2 changes are confirmed** from dated press: Cedarline Financial and Orion Manufacturing.\n- **1 is mixed**: sources conflict on whether Brightwave's CMO departed or is on leave.\n- The urgent one is **Cedarline**: your economic buyer departed and the **$640K renewal closes in 2 weeks**.",
  "executiveChanges": [
    {"status": "confirmed", "executive": "Jordan Reyes", "executiveDetail": "Bloomberg · 2026-08-11 · fresh", "account": "Cedarline Renewal – $640K", "accountDetail": "closes 2026-10-27", "change": "VP Finance, Cedarline → departed; destination undisclosed", "impact": "Your only mapped contact and economic buyer is gone two weeks before the renewal."},
    {"status": "confirmed", "executive": "Marcus Ellery", "executiveDetail": "CNBC · 2026-10-14 · very fresh", "account": "Orion Renewal + Sales Cloud – $230K", "change": "Promoted to **COO**, Orion Manufacturing", "impact": "Marcus sponsored the original rollout – a friendly now owns operations."},
    {"status": "mixed", "executive": "Katie McKee", "executiveDetail": "LinkedIn vs. press · exact date unclear", "account": "Brightwave Ad Sales Cloud + CPQ – $410K", "change": "Chief Marketing Officer, Brightwave – **departure vs. medical leave**, sources conflict", "impact": "Katie is the working sponsor on an active deal. Confirm before updating the record."}
  ],
  "callout": {"lead": "Secure the Cedarline renewal now – your champion has left.", "text": "The $640K renewal closes 2026-10-27 with no current sponsor. Re-establish a contact this week. Nothing has been written to Salesforce.", "level": "note", "buttonLabel": "Draft outreach to find a new sponsor", "actionMsg": "Draft an outreach email to the new decision-maker at Cedarline Financial to re-establish contact before the renewal closes on 2026-10-27."},
  "sources": [{"label": "Opportunities · my open deals"}, {"label": "Bloomberg · 2026-08-11"}, {"label": "CNBC · 2026-10-14"}]
}
```

**One account — "What are the executive movements at Cedarline Financial?"**

```json
{
  "title": "One confirmed change at Cedarline – and it's the worst one: Jordan Reyes, your only real relationship and economic buyer, has left two weeks before the $640K renewal.",
  "answer": "",
  "relationshipMap": [
    {"name": "Jordan Reyes", "role": "VP Finance · economic buyer · signed the original deal", "sentiment": "Supportive", "tone": "success"},
    {"name": "Rachel Stein", "role": "Chief Digital Officer · inherits budget authority for the renewal", "sentiment": "Neutral", "tone": "info"}
  ],
  "stakeholders": {"items": [
    {"name": "Jordan Reyes", "role": "VP Finance · economic buyer", "change": "Departed Aug 11; destination undisclosed", "next": "Ask for a warm handoff to Rachel Stein; propose marking him inactive for stewardship review."},
    {"name": "Rachel Stein", "role": "Chief Digital Officer", "change": "Inherited renewal decision; now the decision-maker", "next": "Re-introduce this week – the renewal closes Oct 27."}
  ]},
  "nextStep": {"text": "Jordan's exit left you single-threaded at the wrong moment. Want me to draft a re-introduction to Rachel that references the existing deal?"},
  "sources": [{"label": "Account · Cedarline Financial"}, {"label": "Contacts · Cedarline Financial"}, {"label": "Bloomberg · 2026-08-11"}]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include optional keys only when the prompt and evidence call for them (see the scope table):

```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, answer, optional executiveChanges, optional relationshipMap, optional stakeholders, then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Omit a key and its block is not shown; never send empty arrays, empty strings except answer when the contextual title fully answers, placeholders or N/A, and never include a block the prompt did not ask for. A portfolio or single-executive question gets executiveChanges; an account-scoped question gets relationshipMap and stakeholders (plus executiveChanges only when it adds rows beyond the stakeholders table). A direct question usually gets no tail. Format every value as display-ready text; names are plain strings, never response objects, links or raw Ids.",
  "required": ["title", "answer", "sources"],
  "properties": {
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed label of the widget (card headings, table headers, verification words and the sources footer); each key's default is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; otherwise translate every key and follow the Language rule in SKILL.md.",
      "properties": {
        "executiveChanges": {"type": "string", "default": "Executive changes", "description": "Executive-changes card heading. English: 'Executive changes'."},
        "colVerification": {"type": "string", "default": "Verification", "description": "Executive-changes verification column header. English: 'Verification'."},
        "colExecutive": {"type": "string", "default": "Executive", "description": "Executive-changes executive column header. English: 'Executive'."},
        "colAccount": {"type": "string", "default": "Account or opportunity", "description": "Executive-changes account column header. English: 'Account or opportunity'."},
        "colChange": {"type": "string", "default": "Change", "description": "Change column header, used by both tables. English: 'Change'."},
        "colImpact": {"type": "string", "default": "Impact", "description": "Executive-changes impact column header. English: 'Impact'."},
        "confirmed": {"type": "string", "default": "Confirmed", "description": "Verification word for status 'confirmed'. English: 'Confirmed'."},
        "mixed": {"type": "string", "default": "Mixed", "description": "Verification word for status 'mixed'. English: 'Mixed'."},
        "unconfirmed": {"type": "string", "default": "Unconfirmed", "description": "Verification word for status 'unconfirmed'. English: 'Unconfirmed'."},
        "relationshipMap": {"type": "string", "default": "Relationship map", "description": "Relationship-map card heading. English: 'Relationship map'."},
        "stakeholders": {"type": "string", "default": "Stakeholders", "description": "Stakeholder table card heading and caption. English: 'Stakeholders'."},
        "colStakeholder": {"type": "string", "default": "Stakeholder", "description": "Stakeholder table's name column header. English: 'Stakeholder'."},
        "colRole": {"type": "string", "default": "Role", "description": "Stakeholder table's role column header. English: 'Role'."},
        "colNextStep": {"type": "string", "default": "Next step", "description": "Stakeholder table's next-action column header. English: 'Next step'."},
        "sourcesOrigin": {"type": "string", "default": "Salesforce + web sources", "description": "Text beside the cloud icon in the sources footer. English: 'Salesforce + web sources'."},
        "sources": {"type": "string", "default": "Sources", "description": "Word shown on the sources toggle; the renderer appends the count. Send the word only, no number. English: 'Sources'."}
      }
    },
    "title": {
      "type": "string",
      "description": "REQUIRED. One sentence with the takeaway in the user's context, leading with the most material change. Never use the skill name."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-only markdown. For portfolio questions use 2-4 short '- ' bullets with bold on counts, account names and dates (how many are confirmed, mixed and unconfirmed, and which one is urgent). Do not repeat card contents. Use an empty string only when the contextual title already fully answers the question, as in the account-scoped mock."
    },
    "executiveChanges": {
      "type": "array",
      "maxItems": 8,
      "description": "OPTIONAL card 'EXECUTIVE CHANGES'. Include for a portfolio sweep ('any executive changes at my accounts?') or a single-executive check. Rows are ordered by material impact (relationship strength, account importance, open-opportunity exposure), highest first. Omit the key when no change was found, and never send an empty array.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["status", "executive", "executiveDetail", "account", "change", "impact"],
        "properties": {
          "status": {
            "type": "string",
            "enum": ["confirmed", "mixed", "unconfirmed"],
            "description": "REQUIRED verification level. confirmed = a dated statement from a reputable outlet, connected data provider or the company itself. mixed = sources conflict (for example departure vs. leave) or the Salesforce record disagrees. unconfirmed = a single undated or low-reliability mention. Never present a signal as confirmed."
          },
          "executive": {"type": "string", "description": "REQUIRED. Executive display name as a plain string."},
          "executiveDetail": {"type": "string", "description": "REQUIRED. Muted line under the name: source, date and freshness, e.g. 'Bloomberg · 2026-08-11 · fresh'. Freshness is 'very fresh' (14 days or less), 'fresh' (90 days or less) or 'dated'. When the date is unknown say so, e.g. 'Industry roundup · date unclear · validate'; never invent a date."},
          "account": {"type": "string", "description": "REQUIRED. Account name, or the most exposed open opportunity with its amount, e.g. 'Cedarline Renewal – $640K'."},
          "accountDetail": {"type": "string", "description": "OPTIONAL muted line under the account, e.g. 'closes 2026-10-27' or 'primary account'. Omit if nothing grounded."},
          "change": {"type": "string", "description": "REQUIRED. Plain text with only **bold** spans (no links or other markdown): former role to new role or status, with **bold** on the new role or key word, e.g. 'Named **Chief Revenue Officer**, Vantage Retail Group (new role)'. For mixed rows name both claims."},
          "impact": {"type": "string", "description": "REQUIRED. Relationship risk or growth implication for the rep in one or two sentences, tied to a grounded deal, date or role."}
        }
      }
    },
    "relationshipMap": {
      "type": "array",
      "maxItems": 6,
      "description": "OPTIONAL card 'RELATIONSHIP MAP'. Include ONLY for an account-scoped question or when the user asks who is affected at an account. Each card shows name, role and buying role, and an explicit stance pill. Order by decision relevance. Omit the key when there are no relevant contacts; never send an empty array.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["name", "sentiment", "tone"],
        "properties": {
          "name": {"type": "string", "description": "Contact display name as a plain string."},
          "role": {"type": "string", "description": "OPTIONAL display-ready title and grounded buying role, e.g. 'VP Finance · economic buyer · signed the original deal'. Do not invent roles."},
          "sentiment": {"type": "string", "enum": ["Supportive", "Neutral", "Unsupportive", "Unknown"], "description": "REQUIRED stance pill text. Use Unknown unless a grounded stance or buyer-relationship value exists. Supportive does not mean Champion."},
          "tone": {"type": "string", "enum": ["error", "success", "info", "secondary"], "description": "REQUIRED pill tone matching the text: error for Unsupportive, success for Supportive, info for Neutral, secondary for Unknown. The text carries the meaning; never rely on color alone."}
        }
      }
    },
    "stakeholders": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL card 'STAKEHOLDERS'. Include ONLY for an account-scoped question, with the contacts affected by or newly relevant to a change. Narrow layouts stack the same four fields per contact. Omit the key when there are no relevant contacts; never send an empty items array.",
      "required": ["items"],
      "properties": {
        "items": {
          "type": "array",
          "maxItems": 6,
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["name", "role", "change", "next"],
            "properties": {
              "name": {"type": "string", "description": "Contact display name as a plain string."},
              "role": {"type": "string", "description": "One muted line: title and grounded buying role. Do not invent."},
              "change": {"type": "string", "description": "What changed for this person, e.g. 'Departed Aug 11; destination undisclosed'. Send '–' when the contact has not changed."},
              "next": {"type": "string", "description": "Specific next relationship action grounded in the evidence. Record updates are proposals only; never state one as done."}
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL tail for a time-sensitive action the user can take now, such as a champion leaving before a close date. Use INSTEAD of nextStep, never both. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": ["lead", "text"],
      "properties": {
        "lead": {"type": "string", "description": "REQUIRED, visible (non-whitespace). Bold one-sentence urgent action or risk."},
        "text": {"type": "string", "description": "REQUIRED, visible (non-whitespace). Why it matters and the immediate move, in one to three sentences. State that nothing has been written to Salesforce when a record update is proposed."},
        "level": {"type": "string", "enum": ["tip", "note"], "description": "OPTIONAL emphasis: note for one clear move (the default), tip for helpful context."},
        "buttonLabel": {"type": "string", "description": "OPTIONAL primary action label, e.g. 'Draft outreach to find a new sponsor'. Include only with actionMsg."},
        "actionMsg": {"type": "string", "description": "OPTIONAL first-person message sent when the primary action is clicked. Include only with buttonLabel."}
      }
    },
    "nextStep": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL non-urgent tail: a useful relationship move with no button, usually an offer to draft outreach. Use INSTEAD of callout, never both.",
      "required": ["text"],
      "properties": {
        "lead": {"type": "string", "description": "OPTIONAL short bold lead. Omit for a single plain paragraph."},
        "text": {"type": "string", "description": "The suggested next relationship move and brief rationale."}
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Salesforce records and external sources actually read. Rendered in a collapsed 'Salesforce + web sources · Sources (N)' footer. Use scalar labels and put URLs only in url fields. Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["label"],
        "properties": {
          "label": {"type": "string", "description": "Plain source label, e.g. 'Account · Cedarline Financial', 'Opportunity · Cedarline Renewal', 'Bloomberg · 2026-08-11'."},
          "url": {"type": "string", "description": "OPTIONAL absolute Salesforce record URL or published article URL that was read. Do not repeat it in visible text."}
        }
      }
    }
  }
}
```

## 7. Output — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope the fallback to the prompt: give the headline and only the sections that answer the question.

Links are inline markdown (`[Executive](contactUrl)`, `[Account](accountUrl)`, `[Opportunity](oppUrl)`) using each record's Lightning URL, `https://[instanceUrl]/lightning/r/<SObject>/<Id>/view`. Quote an unknown change date as `—`. Label each row **Confirmed**, **Mixed** or **Unconfirmed**.

```
# Executive Movement: [Executive / Account / Your accounts] — [N] changes ([C] confirmed, [M] mixed, [U] unconfirmed)

**Reviewed** [scope] · [review period] · sources: [BoardEx / ZoomInfo / press / …]

| Verification | Executive | Account or opportunity | Change | Impact |
|---|---|---|---|---|
| Confirmed | [Jordan Reyes](contactUrl) · Bloomberg · 2026-08-11 · fresh | [Cedarline Renewal – $640K](oppUrl) · closes 2026-10-27 | VP Finance → departed | Only mapped contact gone before the renewal |
| Mixed | [Katie McKee](contactUrl) · LinkedIn vs. press | [Brightwave](accountUrl) | CMO – departure vs. leave | Sponsor on an active deal; confirm first |
| Unconfirmed | [Priya Anand](contactUrl) · industry roundup · validate | [Northpeak](accountUrl) | Reported move to advisory role | Don't act yet |

## Most material change
[1-2 sentences: the highest-impact change and the recommended first move.]

## Proposed record updates (need confirmation / stewardship review)
- [Contact] — [proposed update]. **Preserve the prior affiliation as history; do not overwrite.** Nothing has been written to Salesforce.

## Suggested next step
Draft outreach to the affected contact (run `draft-outreach`), or ask me to draft it now.
```
