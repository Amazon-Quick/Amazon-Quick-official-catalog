---
name: forecast-narrative
display_name: Forecast Narrative
description: "Answer questions about a rep's or team's forecast, scoped to what was asked: a full walk-through (worst / commit / best case against quota, how the number builds, the deals driving it), where commit stands against quota, what's in the commit, or what changed, from Salesforce opportunity aggregates, top-deal samples and field history. For a broader pipeline and coaching view, use team-pipeline."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:f61d8251c7035b7dab3f7dc0d70881bf76c062fa4a58f32df2ae4b12e1759a1d"
id: "adef666b-a672-442f-a597-ef9fe7216901"
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
Answer what the user asked about the forecast (where the number lands against quota, how it builds from closed to best case, which deals carry it, or what changed) in one pass. **Read only what the question needs** and present only that: a walk-through ("walk me through my Q3 forecast") reads and shows the whole picture; a specific ask ("what's in my commit?", "what changed since last week?") reads and shows only that.

# Rules:

- **Scope reading and output to the prompt, never a default full brief.** A walk-through reads and shows the whole forecast; a specific ask reads and shows only that. Skip reads the question doesn't need (each read step says which), and don't show something just because you fetched it.
- **Quota is never estimated.** Use a quota only if the user stated it; otherwise show the forecast without quota. Do not query `ForecastingQuota`.


# Forecast Narrative

Ground → aggregate the number + sample the deals (ONE turn) → narrative. Scope: my forecast (default), or a named rep/team. Period: current quarter (default).

## 1. Ground (hardcoded — Opportunity only)

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's ForecastCategory/StageName picklists + any custom forecast/override `__c` fields — use exact names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

## 2. AGGREGATE the number, SAMPLE the deals — ISSUE BOTH IN ONE TURN

A narrow ask fires only the reads it needs: commit-vs-quota, gap and "what's my commit number" asks need only 2a; "what's in my commit" and which-deals asks need 2a and 2b. A walk-through fires both.

**Don't compute the number from a `first: N` page.** A raw pull caps at its page (`first: 200` returns 200 rows, not the book) — summing that page silently under-reports the total on a large book, and the first page isn't the whole set. Salesforce aggregates the totals server-side; use that for the number, and pull only a small bounded sample for the per-deal commentary.

`scope: MINE` = running user's book (no user lookup). `%QSTART%`/`%QEND%` = quarter's first/last day as explicit `YYYY-MM-DD` (never a quarter-relative literal — a bare `THIS_QUARTER` silently empties as boundaries move). Bound **both** ends of `CloseDate` — an open-ended `gte` pulls next-quarter+ deals into the current number. **Named rep/team:** swap `scope: MINE` for `OwnerId: { eq: \"<UserId>\" }`; for a team rollup, add `Owner { Name { value } }` to the sample so each deal attributes to its rep.

**2a. The number — aggregate by ForecastCategory (accurate at any volume).** One row per forecast bucket: count + $ sum. This is "The Number" table and it reconciles by construction — no page cap, no client-side sum of a truncated page.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { CloseDate: { gte: { value: \\\"%QSTART%\\\" }, lte: { value: \\\"%QEND%\\\" } } }, groupBy: { ForecastCategory: { group: true } }) { edges { node { aggregate { ForecastCategory { value } Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```
`ForecastCategory` maps to the buckets: **Closed** = Closed Won (in the bank), **Commit**, **Best Case**, **Pipeline**; **Omitted** = drop (closed-lost/omitted). Org doesn't populate `ForecastCategory` → swap `groupBy` to `StageName` and infer buckets from the stage map (ask once if unclear). **If the `aggregate` query errors** (some orgs throw `DataFetchingException` grouping a picklist) → don't re-fire the same shape; fall to the SOQL `GROUP BY` equivalent:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT ForecastCategory, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '%OWNERID%' AND CloseDate >= %QSTART% AND CloseDate <= %QEND% GROUP BY ForecastCategory" })
```
SOQL has no `scope: MINE`, so scope it by owner Id — without the `OwnerId` clause this fallback returns the whole org, not your book. `%OWNERID%` = the running user's Id for "my forecast"; resolve it with one `currentUser` read (needs **v66.0** — the GraphQL endpoint otherwise pins v65.0, so bump the version for this one call):
```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })
```
For a named rep/team, `%OWNERID%` is the `UserId` you already resolved for 2a's `OwnerId: { eq }` (or filter `Owner.Name` instead) — no `currentUser` lookup needed.

**2b. Sample the deals for commentary (bounded raw — Commit/Best Case lines).** The aggregate gives the number; this gives named deals to comment on. Cap hard (`first: 50`, biggest first) so it never overflows — this is a sample, not the book. Splice confirmed `__c` fields into `<OPP_CUSTOM>`. **Check `{` vs `}` balance before dispatching** — splicing `<OPP_CUSTOM>` is where a brace drops.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"%QSTART%\\\" }, lte: { value: \\\"%QEND%\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } ForecastCategory { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } } }\"}" })
```

`InvalidSyntax` / "offending token `<EOF>`" → missing a closing `}`; add it and retry (once, with corrected text — never re-send identical text).

## 3. Bucket (in-prompt — no extra reads)

Assemble only what the prompt needs. The scenarios are **Worst = Closed Won**, **Commit = Closed Won + Commit**, **Best = Commit + Best Case**, all from 2a. This path has no quota read: use a quota only if the user stated it, otherwise leave quota and % of quota out.

**The Number comes from 2a's aggregate** — count + $ per bucket (Closed Won / Commit / Best Case / Pipeline), whole-book and reconciled; drop the Omitted/closed-lost row. **Per-deal commentary comes from 2b's sample** — the top-by-Amount Commit and Best Case deals (the ones that matter for the call). Prefer `ForecastCategory`; else infer from `StageName` (never invent bucketing — infer from the org's stages or ask once). Say the per-deal lines are the top deals sampled, while the bucket totals are whole-book from the aggregate.

## 4. Changes + commentary

Only a walk-through and a "what changed / what moved / what slipped" ask read field history; every other specific ask skips the query below. Per-deal commentary is only for the deals you will show.

Prior snapshot pasted → diff it (up / slipped / added / lost). No snapshot → pull this quarter's field history for the delta (SOQL only — `OpportunityFieldHistory` has no GraphQL form), and only skip the section if that too is empty/unavailable:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT OpportunityId, Field, OldValue, NewValue, CreatedDate FROM OpportunityFieldHistory WHERE CreatedDate >= %QSTART%T00:00:00Z AND Field IN ('StageName','Amount','CloseDate') ORDER BY CreatedDate DESC" })
```
Derive moved-up / slipped / added / lost from those rows. Per **Commit**/**Best Case** deal, one grounded line — status, what's needed, risk (cite `NextStep`/`LastActivityDate`). Link each deal. **Leader/team rollup across many reps:** cap per-deal commentary to top 5 by Amount per rep.

## 5. Widget (default output when `display_widget` is present: AWS Quick)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/forecast-narrative", props: <object matching the schema below> })
```

- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected.
- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (row `label`/`sub`/`pct`, `build` step labels, `category`, `next`, `summary`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| A walk-through ("walk me through my Q3 forecast", "how's my forecast looking?", "prep me for the forecast call") | `title` + `answer` (bullets) + `scenarios` + `build` + `deals` + tail only if it applies + `sources` |
| Commit against quota ("where does commit stand against quota?", "will I make my number?") | `title` + `answer` + **only** `scenarios` + `sources` |
| How the number builds ("how does my number build from closed to best case?") | `title` + `answer` + **only** `build` + `sources` |
| The deals ("what's in my commit?", "which deals matter this quarter?") | `title` + `answer` + **only** `deals` + `sources` (the deals) |
| A question with a direct answer ("what's my gap to quota?", "what's my commit number?", "what changed since last week?") | `title` + `answer` (paragraph) + `sources` — no card, no tail |

Rules:
- **Omit a key and its block is not shown.** Never send empty arrays, empty strings, placeholder text, or "N/A" to fill a block, and never send a card the prompt did not ask for.
- **Scope the `answer` too:** for "what's my gap to quota?", the answer is the gap and what closes it — not the deal list or the changes you also read.
- **Changes have no card:** what moved up, slipped, was added or lost (step 4) goes in `answer` when the prompt asks for it, or as one bullet in a walk-through.
- **Concentration:** if one deal is about 40% or more of the Commit total, say so in `title` or the first bullet — a single-deal quarter is the headline, not a footnote.
- **`scenarios`:** the three rows from step 3, Worst / Commit / Best, as numbers plus pre-formatted `amount`. `max` is a round number at or above the larger of Best Case and quota. Send `quota`, `quotaLabel` and each row's `pct` only when quota came from the forecast/quota answer or the user; otherwise leave them all out and lead the `title` with the Commit amount. Never send a color: the renderer colors each bar from its value against quota.
- **`build`:** `closedWon`, then `commit` (open Commit) and `bestCase` (Best Case) as numbers; the renderer draws the steps and the Best Case total, which must equal the Best scenario. A step's `label` is the account when the bucket is one sampled deal ("Brightwave"), else the deal count ("3 deals"); omit a bucket that is empty. `quota` follows the scenarios rule. `summary` compares Commit and Best Case with quota when known; it shows under the bars on mobile, where the chart draws no quota line.
- **`deals`:** from the deal sample — Commit deals first, then Best Case, then at most two Pipeline deals that could pull in; biggest first, at most 8. `next` is step 4's one grounded line (status, what's needed, risk). For a team rollup, add the owner to `name` ("Ad Sales Cloud + CPQ · Dana Ruiz").
- **Tail fork:** `callout` when one move is time-sensitive and the user can act on it (e.g. the Commit rests on a deal closing within 7 days with an open blocker; one button, a first-person `actionMsg`); otherwise a `nextStep` line; if nothing applies, neither. A specific ask usually gets no tail. Never both (if both are sent only the callout renders).
- **Sources:** the forecast aggregate is `https://<myDomain>/lightning/o/Opportunity/list`; a record is `https://<myDomain>/lightning/r/Opportunity/<Id>/view`. Omit `url` if you have no Id.
- Format every value as a ready-to-display string ("$410K", "75%", "Aug 31"; dates never ISO) except the `scenarios` and `build` amounts, which are numbers. Names are plain strings, never objects.
- Before calling: `props` has no `{!…}`/`{{…}}`, no keys outside the schema, and every optional key you included is justified by the prompt.

#### Worked examples (the `props` object only)

The names, amounts and dates below (e.g. Brightwave, Cedarline, $800K) are illustrative; fill every value from the forecast you read.

**Walk-through, quota known — e.g. "Walk me through my Q3 forecast – where does commit stand against quota?"** (all three cards and a next-step line):

```json
{
  "title": "Your Commit covers 63% of quota – and a single $640K deal decides whether you beat it.",
  "answer": "- Against an **$800K Q3 quota**, you've got **$95K Closed Won** and **$505K Commit** – a **$295K gap** your Commit alone doesn't close.\n- Your Commit rests almost entirely on one deal: **Brightwave Media ($410K)**, closing Aug 31.\n- Best Case reaches **$1.15M (143% of quota)**, but that upside hinges on **Cedarline Financial ($640K)**.",
  "scenarios": {
    "max": 1500000, "quota": 800000, "quotaLabel": "Quota $800K",
    "rows": [
      {"label": "Worst Case", "sub": "Closed Won only", "value": 95000, "amount": "$95K", "pct": "12% of quota"},
      {"label": "Commit", "sub": "Closed + likely wins", "value": 505000, "amount": "$505K", "pct": "63% of quota"},
      {"label": "Best Case", "sub": "Commit + upside", "value": 1145000, "amount": "$1.15M", "pct": "143% of quota"}
    ]
  },
  "build": {
    "closedWon": 95000, "commit": {"label": "Brightwave", "value": 410000}, "bestCase": {"label": "Cedarline", "value": 640000}, "quota": 800000,
    "summary": "Commit totals **$505K** – under the **$800K** quota; Best Case reaches **$1.15M**, clearing it."
  },
  "deals": {
    "items": [
      {"category": "Commit", "account": "Brightwave Media", "name": "Ad Sales Cloud + CPQ", "amount": "$410K", "prob": "75%", "close": "Aug 31", "next": "MSA in redlines since Aug 12; book Elena Cortez signing to lock the Commit."},
      {"category": "Best Case", "account": "Cedarline Financial", "name": "Enterprise Sales Cloud Platform", "amount": "$640K", "prob": "30%", "close": "Aug 31", "next": "Priya Anand silent 3 wks; re-engage by Aug 27 – the swing deal that lifts you to Best Case."},
      {"category": "Pipeline", "account": "Northpeak Logistics", "name": "Service Cloud + Dispatch", "amount": "$285K", "prob": "45%", "close": "Sep 14", "next": "Proposal in review with Marcus Reyes. On track."}
    ]
  },
  "nextStep": {"lead": "Lock the Commit, then chase the swing deal.", "text": "Brightwave ($410K) is your entire open Commit – if it slips, attainment falls from 63% toward 12%. Cedarline ($640K) is the swing: win it and you clear quota, lose it and Best Case collapses to Commit. Want me to model what happens if Cedarline slips to Q4?"},
  "sources": [
    {"label": "Opportunities · Q3 forecast by category", "url": "https://<myDomain>/lightning/o/Opportunity/list"},
    {"label": "Opportunity · Brightwave Media", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"},
    {"label": "Opportunity · Cedarline Financial", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"}
  ]
}
```

**Specific, no quota — e.g. "Where does commit stand against quota?" on the default path with no stated quota** (only the scenarios card, no quota line, no tail):

```json
{
  "title": "Your Q3 Commit is $505K – one $410K deal carries most of it.",
  "answer": "**$95K is Closed Won** and **$410K is in Commit**, almost all of it Brightwave Media closing Aug 31. I don't have your quota in Salesforce – tell me the number and I'll show the gap.",
  "scenarios": {
    "max": 1500000,
    "rows": [
      {"label": "Worst Case", "sub": "Closed Won only", "value": 95000, "amount": "$95K"},
      {"label": "Commit", "sub": "Closed + likely wins", "value": 505000, "amount": "$505K"},
      {"label": "Best Case", "sub": "Commit + upside", "value": 1145000, "amount": "$1.15M"}
    ]
  },
  "sources": [{"label": "Opportunities · Q3 forecast by category", "url": "https://<myDomain>/lightning/o/Opportunity/list"}]
}
```

**Direct — e.g. "What changed since last week?"** (paragraph answer, no card, no tail):

```json
{
  "title": "Commit is down $360K since last week – Summit Health slipped to Best Case.",
  "answer": "**Summit Health Partners ($360K)** moved from Commit to Best Case on Aug 22 after the exec readout was pushed, and **Orion Manufacturing** moved its close date from Sep 20 to Oct 15. Nothing was added or lost.",
  "sources": [
    {"label": "Opportunity field history · this quarter"},
    {"label": "Opportunity · Summit Health Partners", "url": "https://<myDomain>/lightning/r/Opportunity/<Id>/view"}
  ]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt"):

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional cards (scenarios, build, deals), then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Which optional cards to include: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A', and never a card the prompt did not ask for. A direct question ('what's my gap to quota?') usually gets no card and no tail. Format every value as a ready-to-display string (currency, dates) except the scenario and build amounts, which are numbers; names are plain strings, never objects.",
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
        "scenarios": {
          "type": "string",
          "default": "QUOTA ATTAINMENT BY SCENARIO",
          "description": "Heading of the scenarios card when quota is known. English: 'QUOTA ATTAINMENT BY SCENARIO'."
        },
        "scenariosNoQuota": {
          "type": "string",
          "default": "SCENARIOS",
          "description": "Heading of the scenarios card without quota (dollar amounts only, no attainment). English: 'SCENARIOS'."
        },
        "build": {
          "type": "string",
          "default": "FORECAST BY CATEGORY",
          "description": "Heading of the forecast-by-category card. English: 'FORECAST BY CATEGORY'."
        },
        "closedWon": {
          "type": "string",
          "default": "Closed Won",
          "description": "First bar of the build chart. English: 'Closed Won'."
        },
        "stepCommit": {
          "type": "string",
          "default": "(Commit)",
          "description": "Second line under the Commit step of the build chart. English: '(Commit)'."
        },
        "stepBestCase": {
          "type": "string",
          "default": "(Best Case)",
          "description": "Second line under the Best Case step of the build chart. English: '(Best Case)'."
        },
        "bestCaseTotal": {
          "type": "string",
          "default": "Best Case",
          "description": "Last bar of the build chart. English: 'Best Case'."
        },
        "quota": {
          "type": "string",
          "default": "Quota",
          "description": "Label on the quota line of the build chart. English: 'Quota'."
        },
        "short": {
          "type": "string",
          "default": "Short",
          "description": "Standing of a scenario under half of quota (red bar); read out to screen readers. English: 'Short'."
        },
        "belowQuota": {
          "type": "string",
          "default": "Below quota",
          "description": "Standing of a scenario from half of quota up to quota (orange bar); read out to screen readers. English: 'Below quota'."
        },
        "aboveQuota": {
          "type": "string",
          "default": "Above quota",
          "description": "Standing of a scenario at or above quota (green bar); read out to screen readers. English: 'Above quota'."
        },
        "deals": {
          "type": "string",
          "default": "OPPORTUNITIES",
          "description": "Heading of the deals card. English: 'OPPORTUNITIES'."
        },
        "colCategory": {
          "type": "string",
          "default": "Forecast Category",
          "description": "Deals table header. English: 'Forecast Category'."
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
        "colProb": {
          "type": "string",
          "default": "Probability",
          "description": "Deals table header. English: 'Probability'."
        },
        "colClose": {
          "type": "string",
          "default": "Close Date",
          "description": "Deals table header. English: 'Close Date'."
        },
        "colNextStep": {
          "type": "string",
          "default": "Next Step",
          "description": "Deals table header. English: 'Next Step'."
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
      "description": "REQUIRED. The forecast takeaway, one bold sentence that already answers the question (e.g. 'Your Commit covers 63% of quota – and a single $640K deal decides whether you beat it.'). Never the skill name or 'Forecast Narrative'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (amounts, % of quota, deal names, dates). A broad ask gets 2-4 short '- ' bullets; a direct question ('what's my gap to quota?', 'what changed since last week?') gets a 1-3 sentence paragraph. Answer ONLY what the user asked; do not restate the cards below it."
    },
    "scenarios": {
      "type": "object",
      "description": "OPTIONAL card 'QUOTA ATTAINMENT BY SCENARIO' (without quota: 'SCENARIOS'). Include ONLY if the prompt asks for a forecast walk-through, where commit stands against quota, whether the number will land, or worst/commit/best case. Omit the key otherwise.",
      "required": [
        "max",
        "rows"
      ],
      "properties": {
        "max": {
          "type": "number",
          "description": "Right end of every row's bar, a round number at or above the largest of the Best Case total and quota (e.g. 1500000)."
        },
        "quota": {
          "type": "number",
          "description": "Quota for the period as a number (e.g. 800000). Only from a forecast/quota read or a quota the user stated; omit if you have neither, never estimate it. With quota, each bar is colored by the renderer from its value: under half of quota red, up to quota orange, at or above quota green. Without it the bars are grey."
        },
        "quotaLabel": {
          "type": "string",
          "description": "Accessible name of the quota line (e.g. 'Quota $800K'). Send only with quota."
        },
        "rows": {
          "type": "array",
          "description": "Exactly the three scenarios in this order: Worst Case (Closed Won only), Commit (Closed Won + Commit), Best Case (Commit + Best Case).",
          "minItems": 3,
          "maxItems": 3,
          "items": {
            "type": "object",
            "required": [
              "label",
              "value",
              "amount"
            ],
            "properties": {
              "label": {
                "type": "string",
                "description": "Scenario name, the bold line (e.g. 'Worst Case', 'Commit', 'Best Case')."
              },
              "sub": {
                "type": "string",
                "description": "What the scenario counts, the muted line under the name (e.g. 'Closed Won only', 'Closed + likely wins', 'Commit + upside')."
              },
              "value": {
                "type": "number",
                "description": "The scenario total as a number (e.g. 95000)."
              },
              "amount": {
                "type": "string",
                "description": "The scenario total pre-formatted, the bold figure on the right (e.g. '$505K')."
              },
              "pct": {
                "type": "string",
                "description": "Share of quota under the figure (e.g. '63% of quota'). Send only with quota."
              }
            }
          }
        }
      }
    },
    "build": {
      "type": "object",
      "description": "OPTIONAL card 'FORECAST BY CATEGORY' (how the number builds from Closed Won to Best Case). Include ONLY if the prompt asks for a forecast walk-through or how the number builds (closed to commit to best case). Omit the key otherwise.",
      "required": [
        "closedWon"
      ],
      "properties": {
        "closedWon": {
          "type": "number",
          "description": "Closed Won amount as a number (e.g. 95000), the first bar."
        },
        "commit": {
          "type": "object",
          "description": "The open Commit step. Omit when there is no open Commit.",
          "required": [
            "label",
            "value"
          ],
          "properties": {
            "label": {
              "type": "string",
              "description": "The deal's account when the bucket is one deal (e.g. 'Brightwave'), else the deal count (e.g. '3 deals')."
            },
            "value": {
              "type": "number",
              "description": "Open Commit amount as a number (e.g. 410000)."
            }
          }
        },
        "bestCase": {
          "type": "object",
          "description": "The Best Case step. Omit when there is no Best Case.",
          "required": [
            "label",
            "value"
          ],
          "properties": {
            "label": {
              "type": "string",
              "description": "The deal's account when the bucket is one deal (e.g. 'Cedarline'), else the deal count (e.g. '2 deals')."
            },
            "value": {
              "type": "number",
              "description": "Best Case amount as a number (e.g. 640000)."
            }
          }
        },
        "quota": {
          "type": "number",
          "description": "Quota as a number (e.g. 800000), drawn as a dashed line. Same rule as scenarios.quota: omit if you have none."
        },
        "summary": {
          "type": "string",
          "description": "One markdown sentence with **bold** amounts, comparing Commit and Best Case with quota when known (e.g. 'Commit totals **$505K** – under the **$800K** quota; Best Case reaches **$1.15M**, clearing it.'). Shown under the bars on mobile, where the chart has no quota line."
        }
      }
    },
    "deals": {
      "type": "object",
      "description": "OPTIONAL card 'OPPORTUNITIES'. Include ONLY if the prompt asks for a forecast walk-through, what is in the commit, or which deals matter. Omit the key otherwise.",
      "required": [
        "items"
      ],
      "properties": {
        "items": {
          "type": "array",
          "description": "One table row per sampled open deal that matters for the call: Commit deals first, then Best Case, then the largest Pipeline deals that could pull in; biggest first within each; at most 8 (never an empty array - omit deals instead).",
          "maxItems": 8,
          "items": {
            "type": "object",
            "required": [
              "category",
              "account",
              "amount"
            ],
            "properties": {
              "category": {
                "type": "string",
                "description": "Forecast category label (e.g. 'Commit', 'Best Case', 'Pipeline')."
              },
              "account": {
                "type": "string",
                "description": "Account name, the bold line (e.g. 'Brightwave Media')."
              },
              "name": {
                "type": "string",
                "description": "Opportunity name, the muted line under the account (e.g. 'Ad Sales Cloud + CPQ')."
              },
              "amount": {
                "type": "string",
                "description": "Pre-formatted amount (e.g. '$410K')."
              },
              "prob": {
                "type": "string",
                "description": "Probability (e.g. '75%')."
              },
              "close": {
                "type": "string",
                "description": "Pre-formatted close date (e.g. 'Aug 31'). Never ISO YYYY-MM-DD."
              },
              "next": {
                "type": "string",
                "description": "Status, what's needed and the risk in one or two short sentences, from NextStep and LastActivityDate (e.g. 'MSA in redlines since Aug 12; book Elena Cortez signing to lock the Commit.'). Use 'None set' when NextStep is blank and there is nothing else to say."
              }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something is time-sensitive AND the user can act on it (e.g. the Commit rests on one deal closing this week with an open blocker). Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period, e.g. 'Brightwave closes in 3 days – the MSA is still in redlines.')."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Book the Brightwave signing')."
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
          "description": "Bold lead (the suggested move, e.g. 'Lock the Commit, then chase the swing deal.')."
        },
        "text": {
          "type": "string",
          "description": "One to three sentences of reasoning, ending with an offer to help if natural (e.g. 'Want me to model what happens if Cedarline slips to Q4?')."
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


## 6. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Scope this to the prompt too: a specific ask ("what's in my commit?", "what changed since last week?") gets only the sections that answer it, not every section below. Show quota and % of quota only when quota came from the forecast/quota answer or the user.

```
# Forecast — <Scope> — <Period>
## The Number
| | $ | # |
|---|---|---|
| Closed Won | $<X> | <N> |
| Commit | $<X> | <N> |
| Best Case | $<X> | <N> |
| Pipeline | $<X> | <N> |
| **Commit Total** | **$<Closed+Commit>** | |

## Changes Since Last Week
- ⬆/⬇/✅/❌ <Deal> … (or "No prior snapshot — skipping delta")

## Commit Deals
- **<Account>** $<X> closing <Date> — <status, what's needed, risk>

## Best Case Deals
- **<Account>** $<X> — <what gets it to commit>

## Risk to Commit
- <Deal + specific risk + mitigation>

## On the Radar
- <Pipeline/Best-Case deals that could pull INTO the number if accelerated, or slip OUT — the upside/downside not yet in Commit>

## Asks
- <exec help / resourcing / unblocks>
```
**Concentration callout:** if a single deal is a large share (~40%+) of the Commit number, call it out explicitly — a single-deal quarter is a risk headline, not a footnote.

"What if <deal> slips?" → `deal-slip-scenario`. Submission stays manual.
