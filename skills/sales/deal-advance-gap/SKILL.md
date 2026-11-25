---
name: deal-advance-gap
display_name: Deal Advance Gap (Preview)
description: "Diagnose why one Salesforce opportunity is not advancing, scoped to what was asked: a broad stage-exit review, a specific blocker or gap, or a direct status question, using grounded Opportunity data and available email, documents, and Slack."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:9be2d07391eb2fd1a41c920018c58806ed83e77ce3a2559da36c4d5bf1867756"
id: "1b930110-e61c-4677-98a2-afeeea97cafe"
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
Explain what must happen for one opportunity to advance or close, scoped to what the user asked. A broad ask maps the evidenced stage path and gaps; a specific ask reads only the requested blocker; a direct question returns only its answer and sources.

# Rules:

- **Scope reading and output to the prompt, never a default full deal review.** The `stages` card is the one standing exception: send it on every response, whatever the prompt, whenever stage history is grounded. Beyond that, a broad ask shows the evidenced gaps; a specific ask includes only the matching `gaps` rows; a direct question gets only a title, concise answer, the stage path, and relevant sources. Do not show other data just because you fetched it.
- Apply the human-label rule to Opportunity child records too. State a risk as "Blocking: yes · Severity: High · Status: Mitigating", never `Is_Blocking__c = true`.

# Deal Advance Gap

Forward-looking: against the org's stage exit criteria, what has to happen for this deal to advance — and the shortest path to it. Ground → resolve to one Id (+ evidence, ONE turn) → detail read → map gaps → sequence → output.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields + childRelationships reveal this org's stage/qualification/next-step schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label relationshipName } childRelationships { childObjectApiName relationshipName } } } }\"}" })
```

Step 1 is the authority on names. Note: (a) scalar `__c` fields carrying stage-exit / next-step / blocker / qualification signal — take `{ value }` **and keep each field's `label`**; (b) each lookup's exact `relationshipName` for spanning a related name; (c) each child `relationshipName`. **Build an ApiName→label map now and use the `label` in ALL output** (e.g. "Executive Sponsor", not `Executive_Sponsor__c`; "Target Resolution Date", not `Target_Resolution_Date__c`) — never print a `__c` API name to the user.

## 2a. Resolve to ONE opportunity Id (before the detail read)

Given an SFDC **Id** already → skip to 2b with `Id: { eq: "<Id>" }`. Given a **name**, resolve it first — `first: 1` on a `Name like` only caps the response; it does **not** pick the right deal, so on a multi-match it returns an arbitrary one. Run a bounded, ordered candidate query over open deals, since only an open deal can advance (`%DEALNAME%` = 1–2 distinctive words; when the request also names the account, use `%<account word>%<deal words>%`):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" }, IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { totalCount edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Account { Name { value } } } } } } } }\"}" })
```

- **`totalCount` above the rows returned** → the list is cut off and may not include the requested deal. Narrow `%DEALNAME%` (add the account or another distinctive word) and retry once; if it is still cut off, say how many open deals match and ask for the account. Never ask the user to choose from a cut-off list.
- **Exactly one** candidate → take its `Id`, go to 2b.
- **Several** → list them (Account · Name · Stage · $ · close) and **ask which**; don't guess.
- **None** → broaden `%…%` and retry once.

## 2b. Read the resolved opp by Id (fill from step 1)

Filter by the **exact Id** from 2a (`first: 1` is correct here — the filter is a unique record Id). **Reference-field rules (avoids the retry loop):**
- Scalar/`__c` → `Field__c { value }`. `displayValue` is null for Id fields — don't rely on it.
- Related record's name → span the exact `relationshipName` from Step 1: `<relationshipName> { Name { value } }`. Do NOT append `{ … }` to a raw `Id`/`__c` field.
- No usable relationshipName → take the `__c { value }` (Id) and move on — **do not retry**.

Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed relationship (`<relationshipName> { Name { value } … }` for a lookup; `<childRelationshipName> { edges { node { … } } }` for a child). Standard fields + `OpportunityContactRoles` always work.

**Before dispatching, double-check the query's braces balance** (count `{` vs `}` — they must be equal). Splicing `<OPP_CUSTOM>`/`<REL_BLOCKS>` is where a `}` gets dropped; keep the read flat (no unnecessary nesting).

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } ForecastCategory { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } <REL_BLOCKS> OpportunityHistories(first: 20, orderBy: { CreatedDate: { order: ASC } }) { edges { node { StageName { value } CreatedDate { value } } } } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } Tasks(first: 15, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Status { value } Description { value } TaskSubtype { value } } } } Events(first: 10, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } } } }\"}" })
```

Target = next stage (default) or "to close" if asked.

**Stage order (for the `stages` card).** The history above lists only stages already passed, so it cannot name the target. Read the org's active stages in order, in the same turn as 2a (it does not depend on the Id):

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT MasterLabel, SortOrder, IsClosed, IsWon FROM OpportunityStage WHERE IsActive = true ORDER BY SortOrder" })
```

Resolve the target from that list, using the labels as returned: for "next stage", the first open stage (`IsClosed` false) with a higher `SortOrder` than the current `StageName`, or the won stage (`IsWon` true) when the current stage is the last open one; for "to close", the won stage. If the current stage is already closed or no target can be resolved, send the card without a target.

**Retry contract on `InvalidSyntax` / "offending token `<EOF>`" (the dynamic splice dropped a brace):** construct **one** corrected query and dispatch it **only if its text differs** from the failed one (add the missing `}` — never re-send byte-identical text; an identical retry just burns a round-trip for the same error). If that corrected retry still fails, **stop retrying the spliced shape** — fall back to the fixed, guaranteed-field query below (standard fields + contact roles only, no `<OPP_CUSTOM>`/`<REL_BLOCKS>`), then continue the analysis and note that optional custom risk signals were unavailable:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } ForecastCategory { value } LastActivityDate { value } Account { Name { value } } Owner { Name { value } } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } } } } } } }\"}" })
```

## 2c. Evidence (run IN PARALLEL with 2a — same turn, issue all at once)

**Issue 2a and all of 2c in a single turn** — these searches key on the deal/account name from the *request* (not the SF read), so batch them with candidate resolution; only 2b's detail read waits on the resolved Id. Keyed on the deal/account:
- **email**: last exchange per contact, open commitments in both directions, silence/OOO/departure
- **docs**: latest transcript/notes → decisions, objections, open commitments, competitor mentions
- **slack**: internal blockers — deal desk, legal, security review, pricing approval

Use whatever email/doc/Slack tools are present; if none, skip silently (SF-only is fine). Cite source + date for anything used.

**No extra Salesforce reads.** 2b already returned the CRM state (stage, close, next step, probability, forecast, last-activity, contact roles, recent Tasks/Events, `__c` signals). The org-wide stage list above is not a per-opp read and is allowed. Do NOT dispatch a **separate** per-opp SF follow-up (a standalone `ActivityHistory` / `OpportunityFieldHistory` / Task query) — recent activity already rides along as the `Tasks`/`Events` child edges in the 2b query (same round-trip, no extra call). Read those children as distinct states: a completed Task (Status Completed / past-dated Event) is a done touch; an open Task or a future-dated Task/Event is **🔶 In motion / scheduled**, not done — that's the signal behind "Already in motion". Deeper detail comes from the external evidence above.

## 3. Map gaps against exit criteria (cite every claim; invent nothing)

Exit criteria, qualification framework, and required-stakeholders-for-close are **external knowledge** — infer from the org's own data (StageName picklist, closed-won patterns) or ask the user once. Never invent. For the current stage's exit criteria (and every later stage if target is "to close"), mark each: **✅ Done / 🔶 In motion / ❌ Not started**, with the source and the specific gap. Then check the qualification framework the same way — flag only elements that **block advancement**, not every unknown.

**Row states:** Take every Done, In motion, or Scheduled state from 2b's Tasks and Events. Done needs a completed Task or a past-dated Event; In motion or Scheduled needs an open Task or a future-dated Task or Event for that step. A step that exists only as Next Step text, or a completed touch still awaiting a reply, is Not started.

**Suggested steps:** The documented reads do not return the org's exit criteria. Unless the user names them, present the checklist as suggested steps instead of asking. Base each step on this deal's returned data and cite it. Say "suggested steps" wherever the output would say exit criteria, including `headerSubtitle` and `meterValueLabel` (for example, "1 of 5 suggested steps complete"), and say in the callout that these are not the org's defined criteria.

## 4. Sequence the path

Order gaps into the shortest credible path: whose gap (Us / Customer / internal team), parallel vs. strictly sequential, and the single next action that unblocks the most downstream items. Critical-path length → earliest credible close; flag if that lands after the current CloseDate.

## 5. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] Row states: every row marked In motion or Scheduled names the open or future-dated task or event behind it in its `item` text. If it cannot, set that row to Not started; a completed touch awaiting a reply is never In motion.

The layout is built into the renderer and registered by name. Send only the widget name and its data:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/deal-advance-gap", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, badges, icons, HTML, emojis, or layout keys). `props` must be a nested JSON object, not a string.
- When the widget renders, do not also produce the text fallback.

### What to send

Follow the block order and per-block inclusion rules in the data schema. Omit `labels` in English; in another language, translate every key and every free-text value.

### Scope the blocks to the prompt

| The prompt is… | Send |
|---|---|
| Broad ("What's blocking this deal from advancing to Close?") | `title` + `answer` (bullets) + `stages` and `gaps` when grounded + one applicable tail + `sources` |
| Specific ("What's blocking the legal review?") | `title` + `answer` + `stages` when grounded + only the matching `gaps` rows + `sources` |
| Direct ("What's the current stage?") | `title` + `answer` + `stages` when grounded + `sources`; no `gaps` or tail |

Rules:
- **Always send `stages` when stage history is grounded**, for broad, specific, and direct prompts alike. Do not wait for the user to say "stage". It is the deal's position at a glance and costs no extra query. Omit it only when `OpportunityHistories` was not grounded or returned no rows.
- **Omit a key and its block is not shown.** Never send empty or placeholder values.
- Scope the answer to the question; put evidence for a gap in that row's `detail`.
- For a specific question, fetch only the fields and evidence its matching `gaps` rows need. For every prompt, `OpportunityHistories` stays in the 2b detail read and the active stage order comes from the stage list in 2b, since the `stages` card is always sent. If Step 1 did not ground `OpportunityHistories`, drop it from the read and omit `stages`. Never dispatch any other additional query to fill the card.
- **`gaps[].due` is the date that step is scheduled or due, never a deal-level date.** Take it only from a record or commitment tied to that specific step, in this order, and name the source in that row's `detail` (for example "Due per open Task 'Send redlines'"):
  1. **Task for the step**: the `ActivityDate` (Due Date) of a `Tasks` edge from the Opportunity read, matched to the step by a clear `Subject`/`Description` match (skip loose or ambiguous matches); open or completed. Only the 15 most recent Tasks and 10 most recent Events are read, so a step whose record is not in that window has no Task/Event source.
  2. **Event for the step**: the `ActivityDate` of an `Events` edge (the scheduled meeting or call), matched the same way.
  3. **Dated commitment in email, docs or Slack** for the step (for example "redlines back by Aug 27"). Resolve relative dates ("Friday") against the message date, and cite source and date.
  4. **A step-specific date field**: a Step 1 `__c` date field whose label names the step or milestone, or a date in `NextStep` that names the step.
  - **Never use** `CloseDate`, `LastActivityDate`, stage-change or history dates, a Task's `CreatedDate`, a date you estimate, or a weekday you did not compute from the date.
  - **No source for the step → omit `due`.** Timing that is not a date ("when Priya re-engages") belongs in `detail`, not `due`. Format as a display-ready date ("Aug 27"); add the weekday only when computed from the date.
- Use stage history only when grounded and returned. Never invent stage order, stage age, average duration, dates, owners, or exit criteria.
- **Never drop the `stages` card only because the target is unknown.** Send the passed stages and the current stage, and add a `target` item only when the stage list in 2b resolves one. Build `items` in stage order: each history stage before the current one as `completed` (once each, even if it recurs), the current stage as `current`, then the resolved target as `target`. If a prompt asks for the next stage, the target is that next stage, not Closed Won, unless Closed Won is next.
- `gaps[].status` is `blocked`, `notStarted`, or `completed`; `gaps[].tone` is `error`, `warning`, or `success`. Status must match evidence and remain visibly labelled.
- **Tail.** For a broad "what's blocking this deal" ask, send one `callout`: its `lead` is the single most important blocker or move in one sentence, `text` is the recommended move and why, and `buttonLabel` + `actionMsg` (a first-person request, e.g. "Draft a message to ... to agree owners and dates") give the one primary button. A callout does **not** need a date; when no step has a scheduled date, say so in `text` and recommend agreeing owners and dates, without inventing one. For a specific question, send a plain `nextStep` (no icon, no button) only when a button would not help, or send neither. For a direct question send no tail. Never send both a `callout` and a `nextStep`.
- Values are display-ready strings (currency and dates); names are plain strings. Put record URLs only in `url` fields. Sources without a known record URL omit `url`.
- Before calling, remove keys not in the schema and any `{!…}` or `{{…}}` expressions.

#### Worked examples (the data object only)

**Broad — "What's blocking this deal from advancing to Close?"** (stage history, evidenced path, one urgent move):

```json
{
  "title": "Cedarline is stuck in Negotiation / Review — it's been there 31 days and can't advance to Closed Won while the CFO stays dark.",
  "answer": "- The **$640K Enterprise Sales Cloud Platform** deal reached Negotiation / Review on Jul 24 and hasn't moved in **31 days** — more than double the 14-day stage average.\n- Probability sits at **40%** (deals that close from this stage usually clear 60%+), and the Aug 31 close is **7 days out**.\n- Economic buyer Priya Anand (CFO) shows **no engagement for 3+ weeks**, and the champion reorged out.",
  "stages": { "items": [{"name":"Qualification","state":"completed"},{"name":"Needs Analysis","state":"completed"},{"name":"Proposal / Price Quote","state":"completed"},{"name":"Negotiation / Review","state":"current","detail":"Stuck · 31d"},{"name":"Closed Won","state":"target"}], "summary":"Advancing to **Closed Won** needs the economic buyer re-engaged, phased pricing accepted, and the MSA + order form signed — all currently gated on Priya Anand. The deal has cleared every earlier stage; this is the only one it's stalled in." },
  "gaps": [
    {"status":"blocked","tone":"error","step":"Engage Priya Anand — or an executive who can","due":"Aug 27","detail":"Due per open Task 'Intro to second exec'. Everything downstream is gated on the CFO. If she stays dark, no other gap matters. Play: a second-exec intro via Katie McKee or Robert's former manager."},
    {"status":"notStarted","tone":"warning","step":"Deliver phased-pricing proposal","due":"Aug 27","detail":"Due per open Task 'Deliver phased proposal'. $300K Q3 + $340K Q4 structure, pre-approved by Legal Aug 20 · solves the budget objection and de-risks the \"can't justify\" framing."},
    {"status":"completed","tone":"success","step":"MSA sent to Cedarline Legal","due":"Aug 12","detail":"Completed Task 'Send MSA v3'. MSA v3 delivered Aug 12 · no blockers flagged · counsel review in progress. Ping to lock the signing window once Priya re-engages."},
    {"status":"notStarted","tone":"warning","step":"Capture Priya's success metrics","due":"Aug 28","detail":"Due per scheduled Event 'Metrics call'. If she engages, the first ask is what this must deliver in Q4 for her to defend it to the board · get her metric on the table."},
    {"status":"blocked","tone":"error","step":"Send order form for countersign","due":"Aug 30","detail":"Due per Task 'Send order form'. Can't send until the CFO signs off and the MSA finalizes · templates are ready · send within 48 hours of Priya's yes."}
  ],
  "callout": {"lead":"The critical gap closes Aug 27 — 3 days out — and the CFO has been dark 3 weeks.","text":"Another email is the least-likely-to-work move. Route the phased proposal through Katie McKee so she can walk it into Priya's next staff meeting, and open a second exec path in parallel. Two routes to signature; you only need one to land before the Aug 31 close slips again.","buttonLabel":"Draft the Katie McKee message","actionMsg":"Draft a message to Katie McKee with the phased proposal for Priya's staff meeting, and suggest a second executive path to keep the Cedarline deal on track."},
  "sources": [{"label":"Opportunity: Cedarline — Enterprise Sales Cloud Platform","url":"https://<myDomain>/lightning/r/Opportunity/<Id>/view"},{"label":"Opportunity Field History · stage changes"},{"label":"Contact: Priya Anand (CFO)"},{"label":"Contract: MSA v3 · Cedarline Financial"}]
}
```

**Specific — "What's blocking the legal review?"** (stage path plus only the requested gap):

```json
{"title":"The MSA is with Cedarline Legal; counsel review is still in progress.","stages":{"items":[{"name":"Qualification","state":"completed"},{"name":"Needs Analysis","state":"completed"},{"name":"Proposal / Price Quote","state":"completed"},{"name":"Negotiation / Review","state":"current","detail":"Stuck · 31d"},{"name":"Closed Won","state":"target"}],"summary":"Legal review sits inside **Negotiation / Review**, the last open stage before **Closed Won**."},"answer":"MSA v3 was delivered Aug 12, and no blocker has been reported. The signing window can't lock until Priya re-engages, and the order form is gated behind that same sign-off.","gaps":[{"status":"notStarted","tone":"warning","step":"Confirm the MSA signing window","detail":"Cedarline Legal is reviewing MSA v3; the signing window opens when Priya re-engages (no scheduled date). Cite the returned source and date."},{"status":"blocked","tone":"error","step":"Send order form for countersign","due":"Aug 30","detail":"Due per Task 'Send order form'. Can't send until the CFO signs off and the MSA finalizes · templates are ready · send within 48 hours of Priya's yes."}],"sources":[{"label":"Contract: MSA v3 · Cedarline Legal"}]}
```

**Direct — "What's the current stage?"** (answer plus the stage path):

```json
{"title":"Cedarline is in Negotiation / Review.","answer":"The opportunity is currently in **Negotiation / Review**. The close date is Aug 31.","stages":{"items":[{"name":"Qualification","state":"completed"},{"name":"Needs Analysis","state":"completed"},{"name":"Proposal / Price Quote","state":"completed"},{"name":"Negotiation / Review","state":"current"},{"name":"Closed Won","state":"target"}],"summary":"Three stages cleared; **Negotiation / Review** is the last open stage before **Closed Won**."},"sources":[{"label":"Opportunity · Cedarline — Enterprise Sales Cloud Platform","url":"https://<myDomain>/lightning/r/Opportunity/<Id>/view"}]}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include optional blocks only when grounded and prompt-relevant:
```json
{
  "type": "object",
  "additionalProperties": false,
  "description": "Render in this order: title, answer, optional stages card, optional gaps card, at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Omit a key and its block is not shown. A broad stage-exit review can include both cards; a specific question includes only its matching card; a direct question usually gets no tail and no card. Send display-ready text strings and only claims supported by the Opportunity and cited evidence.",
  "required": ["title", "answer", "sources"],
  "properties": {
    "title": {
      "type": "string",
      "description": "A concise, contextual takeaway answering the prompt. Include ONLY when a grounded answer is available.",
      "example": "Cedarline is stuck in Negotiation / Review and cannot advance while the CFO remains unresponsive."
    },
    "answer": {
      "type": "string",
      "description": "The prompt-scoped answer as 2–4 markdown bullets with bolded key facts for a broad question, or a concise paragraph for a direct question. Include ONLY facts supported by returned Opportunity data or cited evidence.",
      "example": "- The **$640K Enterprise Sales Cloud Platform** deal reached Negotiation / Review on Jul 24 and has not moved in **31 days**.\n- Probability is **40%** and the Aug 31 close is **7 days out**.\n- Economic buyer Priya Anand shows no engagement for 3+ weeks, and the champion left."
    },
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "Fixed interface labels. Omit for English. For another language, include every key translated, preserving the status meaning.",
      "properties": {
        "opportunityStage": { "type": "string", "default": "Opportunity Stage", "description": "Stage-path card eyebrow." },
        "stageState": { "type": "string", "default": "Stage state", "description": "Stage state column heading." },
        "pathToNextStage": { "type": "string", "default": "Path to Next Stage", "description": "Gaps card caption." },
        "status": { "type": "string", "default": "Status", "description": "Gap status column heading." },
        "step": { "type": "string", "default": "Step", "description": "Gap step/reason column heading." },
        "dueDate": { "type": "string", "default": "Due date", "description": "Gap due-date column heading." },
        "completed": { "type": "string", "default": "Completed", "description": "Completed stage state label." },
        "current": { "type": "string", "default": "Current", "description": "Current stage state label." },
        "target": { "type": "string", "default": "Target", "description": "Target stage state label." },
        "blocked": { "type": "string", "default": "Blocked", "description": "Blocked gap status label." },
        "notStarted": { "type": "string", "default": "Not started", "description": "Not-started gap status label." },
        "sources": { "type": "string", "default": "Sources", "description": "Sources accordion label." }
      }
    },
    "stages": {
      "type": "object",
      "additionalProperties": false,
      "description": "Opportunity stage path. Include on every response, whatever the prompt, whenever stage transitions are grounded by returned history; the user does not need to ask for it. Do not invent missing stages, stage duration, or average duration.",
      "required": ["items", "summary"],
      "properties": {
        "items": {
          "type": "array",
          "description": "Ordered stage transitions evidenced by the grounded Opportunity stage history, followed by the current stage and, when the active stage order resolves one, a target. A missing target never removes the card. Include ONLY stages supported by history, the stage order, and current Opportunity state.",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["name", "state"],
            "properties": {
              "name": { "type": "string", "description": "Salesforce stage label as returned." },
              "state": { "type": "string", "enum": ["completed", "current", "target"], "description": "The stage's evidenced relationship to the current Opportunity stage." },
              "detail": { "type": "string", "description": "Optional grounded current-state note, such as elapsed time, only when the source supports it." }
            }
          },
          "example": [
            { "name": "Qualification", "state": "completed" },
            { "name": "Needs Analysis", "state": "completed" },
            { "name": "Proposal / Price Quote", "state": "completed" },
            { "name": "Negotiation / Review", "state": "current", "detail": "Stuck · 31d" },
            { "name": "Closed Won", "state": "target" }
          ]
        },
        "summary": { "type": "string", "description": "Brief explanation of the grounded path to the target stage. Required whenever the stage-path card is sent." }
      }
    },
    "gaps": {
      "type": "array",
      "description": "Ranked path-to-next-stage gaps. Include ONLY when the user asks what blocks advancement or a broad review makes the path materially clearer. Each row needs an evidence-based status, step and reason; `due` is the date that step is scheduled or due (not the deal close date); see the `due` field.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["status", "tone", "step", "detail"],
        "properties": {
          "status": { "type": "string", "enum": ["blocked", "notStarted", "completed"], "description": "Visible status label for the path step. Choose only when supported by evidence." },
          "tone": { "type": "string", "enum": ["error", "warning", "success"], "description": "Status tone: error for blocked, warning for not started, success for completed. The visible status text is still required." },
          "step": { "type": "string", "description": "Concise, display-ready action or completed step." },
          "due": { "type": "string", "description": "Display-ready date this step is scheduled or due, e.g. \"Aug 27\". Source only from: (1) the step's Task ActivityDate, (2) the step's Event ActivityDate, (3) a dated commitment in email/doc/Slack for the step, (4) a step-specific date field or a date in NextStep naming the step. Name the source in `detail`. Never use CloseDate, LastActivityDate, stage/history dates, CreatedDate or an estimated date. Not a date (e.g. \"when X happens\") or no source: omit this key." },
          "detail": { "type": "string", "description": "Evidence and why the step matters. Include source/date in the text when available; never invent a rationale." }
        }
      }
    },
    "callout": {
      "type": "object",
      "additionalProperties": false,
      "description": "The one recommended move, shown with an icon and one primary button. Include for a broad 'what is blocking this deal' ask, whether or not a date exists (never invent one). Omit for a specific or direct question. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": ["lead", "text", "buttonLabel", "actionMsg"],
      "properties": {
        "lead": { "type": "string", "description": "REQUIRED, visible (non-whitespace). The single most important blocker or move, in one evidence-backed sentence. Needs no date." },
        "text": { "type": "string", "description": "REQUIRED, visible (non-whitespace). Recommended move and its grounded rationale." },
        "buttonLabel": { "type": "string", "description": "One concise primary action label." },
        "actionMsg": { "type": "string", "description": "First-person request sent by action/sendMessage." }
      }
    },
    "nextStep": {
      "type": "object",
      "additionalProperties": false,
      "description": "Plain suggestion with no icon or button. Use ONLY for a specific question where a button would not help (never for a direct question), and never alongside a callout.",
      "required": ["text"],
      "properties": {
        "lead": { "type": "string", "description": "Optional short bold lead." },
        "text": { "type": "string", "description": "Plain suggestion and brief rationale. Include ONLY when no urgent callout is sent." }
      }
    },
    "sources": {
      "type": "array",
      "description": "Sources actually used for the answer, in display order. Include at least one source. Add a record URL only when its Id and org domain are known. Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["label"],
        "properties": {
          "label": { "type": "string", "description": "Readable source name and type." },
          "url": { "type": "string", "description": "Optional direct record URL. Keep URLs separate from visible text." }
        }
      },
      "example": [
        { "label": "Opportunity · Cedarline — Enterprise Sales Cloud Platform", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view" },
        { "label": "Opportunity stage history" },
        { "label": "Contact · Priya Anand (CFO)" },
        { "label": "MSA v3 · Cedarline Legal" }
      ]
    }
  }
}
```



## 6. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Advance Gap: <Name> — <current stage> → <target>
**Short answer:** <1–2 lines: advances when X and Y; critical path runs through Z>

## Gaps blocking advancement
| # | Gap | Owner (Us/Customer/team) | Blocking (gate/close req) | Evidence (source+date) |

## Already in motion
- <underway items + expected landing — don't re-ask>

## The path
1. <action — who — by when> (unblocks #n)
   Critical path ~<N> weeks → earliest credible close <date> (flag if after CloseDate)

## Suggested SFDC updates
- NextStep → "<the #1 action>" · CloseDate → <if path math says current date isn't credible>
[Apply manually if read-only.]
```
