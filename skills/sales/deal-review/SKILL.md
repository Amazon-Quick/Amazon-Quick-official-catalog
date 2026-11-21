---
name: deal-review
display_name: Deal Review
description: "Review one deal and judge whether it is real, scoped to what was asked: a full review with a qualification scorecard read, e.g. MEDDIC (or the flags and recent activity when the org has no scorecard), the deal's risks alone, what happened lately, or what to do next, from Salesforce fields, contacts and activity plus email, documents and Slack. For stage-exit gaps and a sequenced path, use deal-advance-gap."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:ad316e1d35f71e0b28f8dcfcae921b083149e6ad32beebea752adbb88eafbb32"
id: "50ea00df-5516-4263-ae33-dbd2e647a88a"
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
Answer what the user asked about one deal (is it real, how qualified it is, what the risks are, what happened lately, or what to do next) in one pass. **Read only what the question needs** and present only that: a review (e.g. "review the Cedarline opportunity. Is it real?") reads the deal and its evidence and shows the verdict with its cards; a specific ask (e.g. "what's the risk on Cedarline?") shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full review.** Skip reads the question doesn't need (each read step says which), and don't show something just because you fetched it.


# Deal Review

Ground → (read + evidence searches, all in ONE turn) → analyze.

## 1. Ground (hardcoded — Opportunity only)

Ground `Opportunity`. Its fields reveal this org's custom deal signals; the fixed standard history query below needs no metadata.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } stages: objectInfos(objectInfoInputs: [{ apiName: \\\"Opportunity\\\", recordTypeIDs: [\\\"012000000000000AAA\\\"], fieldNames: [\\\"StageName\\\"] }]) { fields { ApiName ... on PicklistField { picklistValuesByRecordTypeIDs { recordTypeID picklistValues { label value } } } } } } }\"}" })
```

Step 1 is the authority on names — use exact strings from it, never guess. Select relevant `__c` fields (health, next-step, exec-sponsor, forecast, risk signals, etc.) as `{ value }` and keep each field's `label`. **Build an ApiName→label map now and use the `label` in ALL output** (e.g. render `Executive_Sponsor__c` as "Executive Sponsor", `Health_Score__c` as "Health Score") — never print a `__c` API name to the user.

**Stage order:** `stages` lists the Stage picklist in the org's order, read from the master record type (`012000000000000AAA`). Take `kpiStageNum` from the deal's position in it (two digits, for example `04`) and `kpiStageSub` from the stages after it up to and including Closed Won (for example, "5 stages to close"). Never infer either from general sales knowledge.

Every ask needs this grounding. It also tells you whether the org has a **qualification scorecard**: Opportunity fields whose label or ApiName names a qualification methodology's criteria (e.g. MEDDIC/MEDDPICC: Metrics, Economic Buyer, Decision Criteria, Decision Process, Paper Process, Identify Pain, Champion, Competition). It is a scorecard only when **at least three distinct criteria** each have their own field; select those as `<OPP_CUSTOM>`. One or two matches (e.g. a lone "Competition Notes" field) are ordinary deal fields: read them as evidence, but there is no scorecard.

## 2. Read (fill from step 1)

`%DEALNAME%` = 1–2 words. A confirmed `__c` field → `Field__c { value }`; do not invent or span custom relationships.

Insert `<OPP_CUSTOM>` = relevant confirmed `__c { value }` fields. Standard fields and `OpportunityContactRoles` always work.

Every ask sends this one read: the verdict, the risks and the activity all come from it. A "what should I do?" follow-up reuses what was already read in this conversation and sends nothing new.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 1) { totalCount edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } CreatedDate { value } Type { value displayValue } Probability { value } ForecastCategory { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } Tasks(first: 15, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Status { value } Description { value } TaskSubtype { value } } } } Events(first: 10, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } OpportunityHistories(first: 200, orderBy: { CreatedDate: { order: DESC } }) { edges { node { CreatedDate { value } StageName { value } Amount { value displayValue } PrevAmount { value displayValue } CloseDate { value } PrevCloseDate { value } } } } } } } } } }\"}" })
```

**Multiple matches:** `first: 1` returns one deal even when `totalCount` shows that several matched, and the latest close date can belong to a different deal. When `totalCount` is above 1, run the candidate read below before using the result. If `totalCount` is above 10, its list would be cut off, so first narrow `%DEALNAME%` with the account or other words from the request (for example `%Acme%Renewal%`), never with a name from a returned deal. Then:
- if the list is empty or still cut off (`totalCount` above the rows returned), or narrowing was needed and the request had nothing to narrow with, say how many deals matched and ask for the full deal name or the account instead of listing a partial set;
- if exactly one candidate's `Name` equals the deal name the user gave, take it;
- otherwise, if exactly one candidate is open, take it;
- otherwise list the candidates (Account · Name · Stage · close) and ask which.

Keep the step 2 result when the chosen deal is the one it returned; otherwise rerun the full template with `where: { Id: { eq: "<ID>" } }`.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { totalCount edges { node { Id Name { value } StageName { value displayValue } CloseDate { value } IsClosed { value } Account { Name { value } } } } } } } }\"}" })
```

Empty `edges` → use a broad resolver selecting only `Id Name { value }`, choose the target, then rerun the full template with `where: { Id: { eq: "<ID>" } }`; never run the rich template across multiple matches. The `orderBy: { CloseDate: { order: DESC } }` makes `first: 1` favor the active/current deal on a multi-match name (not an arbitrary stale closed-won). `Task.Description`/`TaskSubtype` carry the "what happened" detail behind each timeline row. The `Tasks`/`Events` children carry the activity timeline — read them as **three separate states** (see next paragraph); a scalar `LastActivityDate` alone can't distinguish an open task or a future meeting from a completed touch.

**Deal history (included in the read above).** The nested `OpportunityHistories` snapshots are already scoped to the selected Opportunity, so they ground whether the CloseDate moved and detect same-day stage jumps without an ID-dependent second dispatch.
A snapshot dated *this* cycle with `CloseDate` different from `PrevCloseDate` = real slippage (penalize); no recent CloseDate change with the current date holding = inherited history, not a current slip (context only). Same-day StageName jumps = signals to surface. Empty/unavailable → don't infer a slip.

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**Issue step 2 and all of step 2b as tool calls in a single turn — do not wait for the SF read to return before firing the searches.** They're independent (searches key on the deal/account name, not the SF result), so batch them together. Keyed on the deal/account name:
- **email**: threads with the account/contacts, last ~60d → last exchange date + topic, objections, commitments
- **docs**: recent transcripts/notes on the account → decisions, objections, competitor mentions
- **slack**: internal mentions → deal-desk/exec/concerns

Use whatever email/doc/Slack search tools are available. If none are present, skip silently (SF-only is fine). Never block on these; cite source + date for anything you use.

A review and a risk ask run these searches; an activity-only ask (e.g. "what's happened on Cedarline lately?") runs only email, and a follow-up reuses earlier results.

## 3. Analyze (cite every value/source; invent nothing)

Signal-adjust from SFDC `Probability`, only on a shown trigger:
`+5` ≥3 contact roles · `+10` economic buyer role · `+10` champion engaged (multiple completed touches, email/Task) · `+10` mutual close plan / exec engaged (email/doc) · `−10` >14d since last **completed** touch · `−15` CloseDate past · `−15` open blocking risk · `−10` open High-sev risk · `−10` single-threaded · `−10` champion quiet 14d+ (email) · `−10` competitor named (doc/email) · `−10` current-cycle CloseDate slip (see guardrail). Floor 5, ceil 95. Show the math.

**Activity — three states, never conflated** (read from the Tasks/Events children, not `LastActivityDate` alone): *completed* = Task `Status` Completed or past-dated Event; *open* = Task not yet Completed; *scheduled* = any Task/Event dated after today. "Days dark", the `−10 >14d`, and `−10 champion quiet` triggers key on the last **completed** touch only — a future QBR or an open task is momentum, not a completed touch, and never resets the clock or counts as one. Surface open tasks and scheduled meetings as positive momentum, not silence.

**Match every adjustment to shown state; current-cycle only.** Apply a trigger only if the data you pulled shows it. Apply the slip penalty only when the deal-history query above shows the *current* CloseDate moved this cycle — a PushCount / stage-cycling count inherited from earlier cycles, with the current date holding, is **not** current slippage; don't penalize it (note it as historical context instead). Distinguish a confirmed blocking risk from one that's merely stale or unknown — don't score both as equally blocking.

Report any grounded `Executive Sponsor` by name.

On a scorecard org, rate each grounded criterion from its field value and the evidence:
- **High** — the field is filled and current evidence confirms it (an engaged, named person; a confirmed number or date).
- **Med** — identified but partial, unresponsive or disrupted.
- **Low** — empty, not validated with the buyer, or contradicted by the evidence (e.g. the named champion left).

**Is it real?** — compare the evidence with `ForecastCategory`. It returns the API value, not the label: `Forecast` = **Commit**, `BestCase` = Best Case, `Pipeline`, `Omitted`, `Closed`; always say the label. A Commit (`Forecast`) deal with any Low criterion, or with no completed buyer touch in 14d+, is not real as a Commit; say where it belongs (Best Case, Pipeline) and why. Without a scorecard, judge it from the risks and the activity states above.

## 4. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/deal-review", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 5 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`criterion`, `state`, `detail`, `_status`, flag and activity text, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| A review, on a scorecard org (e.g. "review the Cedarline opportunity. Is it real?", "how qualified is Cedarline?") | `title` + `answer` + `qualification` + tail only if it applies + `sources` |
| A review, no scorecard | `title` + `answer` + `flags` + `activity` + tail only if it applies + `sources` |
| The risks (e.g. "what's the risk on Cedarline?", "why is it at risk?") | `title` + `answer` + **only** `flags` + `sources` |
| What happened (e.g. "what's happened on Cedarline lately?") | `title` + `answer` + **only** `activity` + `sources` |
| What to do ("what should I do about it?") | `title` + `answer` + `callout` (or `nextStep` when nothing is time-sensitive) + `sources` — no card |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for.
- **`title`** is the verdict (e.g. "Not real as a Commit – …", "$640K closing in 8 days, but …"); **`answer`** is a short paragraph: the amount, stage and days to close, then why. On a no-scorecard org, say so in one clause (e.g. "There's no MEDDIC scorecard on this org, so here's the read from the record itself").
- **`qualification`:** one row per grounded criterion, LOW rows first, then MED, then HIGH. Low is `_tone: "error"`, `_status: "LOW"`; Med is `"warning"`, `"MED"`; High is `"success"`, `"HIGH"`. `criterion` is the field's label, `state` a few words, `detail` the evidence.
- **`flags`:** the evidenced risks, most severe first: `error` when it can stop the close, `warning` for a live threat, `neutral` for context (an inactive contact). `title` is bold (who/what + the fact), `context` a few words after it, `detail` the evidence and consequence.
- **`activity`:** newest first, at most 6 rows, completed touches only (step 3's three states); end with one `muted: true` row, `date: "Since"`, when the buyer has gone quiet since the last row.
- **Tail fork:** `callout` when one move is time-sensitive and the user can act on it (one button, a first-person `actionMsg`); otherwise a `nextStep` line; if nothing applies, neither. A specific ask usually gets no tail; the "what should I do?" ask gets the callout. Never both (if both are sent only the callout renders).
- **Sources:** a record is `https://<myDomain>/lightning/r/<Object>/<Id>/view`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string ("$640K", "Aug 31", "closes in 8 days"); dates are short ("Aug 20"), never ISO. Names are plain strings, never objects.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

The names, amounts and dates below (e.g. Cedarline, Priya Anand, $640K, Aug 31) are illustrative; fill every value from the deal you read.

**Review, scorecard org — e.g. "Review the Cedarline opportunity. Is it real?"** (the qualification card and a callout):

```json
{
  "title": "Not real as a Commit – $640K with zero MEDDIC criteria at High confidence.",
  "answer": "Cedarline is **$640K with 8 days to close**, but **0 of 6 MEDDIC criteria are at High confidence** – three sit at Med, three at Low. The technology is validated (the pilot closed), but the deal has **no champion** and the economic buyer shows **no engagement**. Until that changes it belongs in Best Case, not Commit.",
  "qualification": [
    {"criterion": "Champion", "state": "No champion identified", "detail": "Robert Nkemelu reorged out of the CFO's decision (Jul 2026) · no replacement identified.", "_tone": "error", "_status": "LOW"},
    {"criterion": "Identify Pain", "state": "Not validated with buyer", "detail": "Pain was held by Robert Nkemelu (gone) · Priya Anand's pain not confirmed.", "_tone": "error", "_status": "LOW"},
    {"criterion": "Metrics", "state": "Not confirmed", "detail": "CFO success metrics not captured · ROI case not yet delivered to Priya Anand.", "_tone": "error", "_status": "LOW"},
    {"criterion": "Economic Buyer", "state": "Identified, unresponsive", "detail": "Priya Anand (CFO) confirmed as Decision Maker · no engagement for 3+ weeks since Aug 8.", "_tone": "warning", "_status": "MED"},
    {"criterion": "Decision Criteria", "state": "Partial", "detail": "Pricing/ROI is the stated concern · Vaultline CRM introduced as a competing option.", "_tone": "warning", "_status": "MED"},
    {"criterion": "Decision Process", "state": "Disrupted", "detail": "Board review pending (budget freeze) · procurement gating · champion reorged out.", "_tone": "warning", "_status": "MED"}
  ],
  "callout": {"lead": "8 days to close, 3 criteria at Low confidence.", "text": "With no champion and the economic buyer showing no engagement, the Aug 31 date and the forecast category are both At Risk. Reach Priya Anand today with a repackaged ROI case – a CFO-level email with 2–3 package options and a 30-minute call ask this week.", "buttonLabel": "Draft the CFO ROI outreach", "actionMsg": "Draft a CFO-level email to Priya Anand at Cedarline Financial with a repackaged ROI case, 2–3 package options and a 30-minute call ask this week."},
  "sources": [
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"},
    {"label": "Contact · Priya Anand", "url": "https://<myDomain>/lightning/r/Contact/<Id>/view"},
    {"label": "Activities · last 30 days"}
  ]
}
```

**Review, no scorecard — the same prompt** (flags, recent activity and a callout):

```json
{
  "title": "$640K closing in 8 days, but the deal has gone quiet – no buyer engagement in 16 days.",
  "answer": "Cedarline is a **$640K deal in Negotiation / Review, closing Aug 31**. There's no MEDDIC scorecard on this org, so here's the read from the record itself: the **pilot closed successfully**, but coverage has thinned – the economic buyer shows **no activity in 16 days**, the main contact reorged out, and a competitor was just introduced. The fit is real; the **engagement is the risk**.",
  "flags": [
    {"title": "CFO Priya Anand – no activity in 16 days", "context": "pricing objection unresolved", "detail": "Last logged touch Aug 8 · Aug 26 CFO 1:1 invited but not accepted · she's the decision maker on record and the deal can't close without her.", "tone": "error"},
    {"title": "Vaultline CRM introduced by procurement", "context": "Aug 4", "detail": "Gregory Holt added a competitor to the evaluation 3 weeks after our pilot closed · a lower-cost anchor is now on the table.", "tone": "warning"},
    {"title": "Key contact reorged out", "context": "Robert Nkemelu, Jul 12 · Inactive", "detail": "Carried the pilot; no replacement identified inside Priya's decision circle.", "tone": "neutral"}
  ],
  "activity": [
    {"date": "Aug 20", "text": "Legal pre-approved a phased **$300K + $340K** structure · logged by you."},
    {"date": "Aug 8", "text": "Last outreach to **Priya Anand (CFO)** – pricing/ROI email, no reply."},
    {"date": "Aug 4", "text": "Procurement introduced **Vaultline CRM** into the evaluation."},
    {"date": "Jul 28", "text": "Pilot **closed successfully** · technical validation complete."},
    {"date": "Since", "text": "No inbound from the buying committee in 16 days · no meeting on the calendar.", "muted": true}
  ],
  "callout": {"lead": "8 days to close and no meeting booked.", "text": "The pilot proved the fit, but the deal stalls the moment the buyer goes silent – and it's been 16 days. Reach Priya Anand today with a repackaged ROI case and a 30-minute call ask this week, before the Aug 31 date slips.", "buttonLabel": "Draft the CFO ROI outreach", "actionMsg": "Draft a CFO-level email to Priya Anand at Cedarline Financial with a repackaged ROI case, 2–3 package options and a 30-minute call ask this week."},
  "sources": [
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"},
    {"label": "Contact · Priya Anand", "url": "https://<myDomain>/lightning/r/Contact/<Id>/view"},
    {"label": "Activities · last 30 days"}
  ]
}
```

**Specific — e.g. "What's the risk on Cedarline?"** (only the flags card, no tail):

```json
{
  "title": "Cedarline's risk is the buyer – the CFO has been silent for 16 days.",
  "answer": "The deal can't close without **Priya Anand**, and she hasn't engaged since **Aug 8**. A competitor and a lost champion compound it.",
  "flags": [
    {"title": "CFO Priya Anand – no activity in 16 days", "context": "pricing objection unresolved", "detail": "Last logged touch Aug 8 · Aug 26 CFO 1:1 invited but not accepted · she's the decision maker on record and the deal can't close without her.", "tone": "error"},
    {"title": "Vaultline CRM introduced by procurement", "context": "Aug 4", "detail": "Gregory Holt added a competitor to the evaluation 3 weeks after our pilot closed · a lower-cost anchor is now on the table.", "tone": "warning"},
    {"title": "Key contact reorged out", "context": "Robert Nkemelu, Jul 12 · Inactive", "detail": "Carried the pilot; no replacement identified inside Priya's decision circle.", "tone": "neutral"}
  ],
  "sources": [
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"}
  ]
}
```


`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (qualification, flags, activity), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. Format every value as a ready-to-display string (currency, dates); names are plain strings, never objects.",
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
        "qualification": {
          "type": "string",
          "default": "OPPORTUNITY QUALIFICATION",
          "description": "Heading of the qualification card. English: 'OPPORTUNITY QUALIFICATION'."
        },
        "colConfidence": {
          "type": "string",
          "default": "Confidence level",
          "description": "Qualification table header over the High / Med / Low pills. English: 'Confidence level'."
        },
        "colCriterion": {
          "type": "string",
          "default": "Criterion",
          "description": "Qualification table header. English: 'Criterion'."
        },
        "colDetails": {
          "type": "string",
          "default": "Details",
          "description": "Qualification table header. English: 'Details'."
        },
        "flagsRisks": {
          "type": "string",
          "default": "FLAGS & RISKS",
          "description": "Heading of the flags card. English: 'FLAGS & RISKS'."
        },
        "activity": {
          "type": "string",
          "default": "RECENT ACTIVITY",
          "description": "Heading of the activity card. English: 'RECENT ACTIVITY'."
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
      "description": "REQUIRED. One bold sentence that already answers the question: the verdict and the key fact (e.g. 'Not real as a Commit – $640K with zero MEDDIC criteria at High confidence.'). Never the skill name."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. A 2-4 sentence paragraph with **bold** on the key facts (amount, days to close, criteria counts, who is missing): the verdict first, then why. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "qualification": {
      "type": "array",
      "maxItems": 8,
      "description": "OPTIONAL card 'OPPORTUNITY QUALIFICATION': one row per qualification criterion (e.g. MEDDIC) read from the org's qualification fields, LOW rows first, then MED, then HIGH. Include ONLY when step 1 found a scorecard (at least three criteria fields) AND the prompt is a deal review (e.g. 'review Cedarline', 'is it real?', 'how qualified is it?'). With no scorecard send flags and activity instead. Omit the key otherwise; never an empty array.",
      "items": {
        "type": "object",
        "required": [
          "criterion",
          "detail",
          "_tone",
          "_status"
        ],
        "properties": {
          "criterion": {
            "type": "string",
            "description": "The criterion's label from the org's field (e.g. 'Champion', 'Economic Buyer'). Rendered bold."
          },
          "state": {
            "type": "string",
            "description": "Short muted state under the criterion, a few words (e.g. 'No champion identified', 'Identified, unresponsive')."
          },
          "detail": {
            "type": "string",
            "description": "The evidence: one or two short clauses joined by ' · ', **bold** allowed (e.g. 'Robert Nkemelu reorged out of the CFO's decision (Jul 2026) · no replacement identified.')."
          },
          "_tone": {
            "type": "string",
            "enum": [
              "error",
              "warning",
              "success"
            ],
            "description": "'error' for Low confidence, 'warning' for Med, 'success' for High."
          },
          "_status": {
            "type": "string",
            "description": "The confidence word shown in the pill, upper case, in the user's language (English: 'LOW', 'MED', 'HIGH')."
          }
        }
      }
    },
    "flags": {
      "type": "array",
      "description": "OPTIONAL card 'FLAGS & RISKS': the evidenced risks on the deal, most severe first. Include for a deal review (e.g. 'review Cedarline', 'is it real?') when the org has NO qualification scorecard, or when the prompt asks about the deal's risks ('what's the risk on Cedarline?'). Omit the key otherwise; never an empty array.",
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
    "activity": {
      "type": "array",
      "maxItems": 7,
      "description": "OPTIONAL card 'RECENT ACTIVITY': the deal's recent touches, newest first, at most 6 plus an optional muted 'Since' row, from Tasks/Events and the email/doc searches. Include for a deal review when the org has NO qualification scorecard, or when the prompt asks what happened (e.g. 'what's happened on Cedarline lately?'). Omit the key otherwise; never an empty array.",
      "items": {
        "type": "object",
        "required": [
          "date",
          "text"
        ],
        "properties": {
          "date": {
            "type": "string",
            "description": "Short display date ('Aug 20'), or 'Since' on the closing summary row. Never ISO."
          },
          "text": {
            "type": "string",
            "description": "What happened, one sentence, **bold** allowed on the key fact (e.g. 'Last outreach to **Priya Anand (CFO)** – pricing/ROI email, no reply.')."
          },
          "muted": {
            "type": "boolean",
            "description": "true only on the last row when it summarises the silence since then (e.g. 'No inbound from the buying committee in 16 days · no meeting on the calendar.'). Rendered muted, plain text."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if one move is time-sensitive (a close date is days away, a buyer gone quiet will stall the deal) AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the stake in one sentence, ending with a period, e.g. '8 days to close, 3 criteria at Low confidence.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Draft the CFO ROI outreach')."
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
            "description": "Source name: object · record (e.g. 'Opportunity · Cedarline Financial')."
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

Scope this to the prompt too: a specific ask (e.g. "what's the risk on Cedarline?") gets only the sections that answer it, not the whole review below.

```
# Deal Review: <Name> — <Account>
## Health: 🟢/🟡/🔴 <X>/10 — <one-sentence verdict>
<Stage displayValue> · <Amount displayValue> · <Type> · close <CloseDate> · age <days since CreatedDate>d
Prob: SFDC <P>% → adjusted <Y>% (<±adj: evidence>…). If evidence is genuinely two-sided, say so rather than forcing a single precise number.

## Qualification (BANT/MEDDIC)
| Element | Status | Evidence |
|---|---|---|
| Budget | ✅/⚠️/❌ | <$X confirmed <date>, source / gap> |
| Authority | ✅/⚠️/❌ | <EB name, role, source / gap> |
| Need | ✅/⚠️/❌ | <driver, source / gap> |
| Timeline | ✅/⚠️/❌ | <customer close driver, source / gap> |
Cite the source per row; ❌ only when truly not pulled.

## Strengths
- 1–3 evidenced positives (confirmed BANT, prior wins, engaged champion, momentum) — always populate when present; don't drop positives while keeping risks.

## Activity Timeline
- <date> · <source> · <subject / what happened>  (newest first, from the Tasks/Events children)
- Last **completed** touch: <N>d ago · open tasks: <subject, due> · scheduled: <meeting, date>
Keep the three states separate; a scheduled/open item is not a completed touch.

## Risks
- <Primary confirmed gate (Sev, Status, owner)>; then each open risk <Name (Sev, Status, blocking?)>. Mark confirmed-blocking vs stale/unknown distinctly.

## Missing
- Qualification gaps, single-threading, no MAP, unnamed competitor, missing exec sponsor, procurement owner — whatever affects closure.

## Stakeholders
- <Name (Title, Role)>…

## Stage check
- <matches / ahead of evidence — why>

## Evidence
- <key email/doc/Slack signals w/ date+source, or "CRM only — email/docs/Slack not connected">

## Recommended Next Actions
1. 2–4 actions, each tied to a named gap/risk above with an owner or date

## Suggested SFDC updates
- StageName/NextStep/CloseDate if evidence differs from the record (note if read-only)
```
