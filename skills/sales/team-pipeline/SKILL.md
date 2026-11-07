---
name: team-pipeline
description: "Build a team pipeline brief from Salesforce users and opportunities, showing closed revenue, forecast, swing deals and coaching needs by rep. Use for a manager's team, two or more named reps, a named rep list, or a multi-rep pipeline comparison. Exactly one rep or one owner's book: pipeline-review."
icon: assets/salesforce.svg
checksum: "sha256:a6cb12e2f2e640e45d05e9f773885054faab7ce4c998157fd19c0bea00396b15"
---
<!-- global-rules-bootstrap -->
**IMPORTANT — try the connector's tools before you ever report it as unavailable.** Before you tell the user a connector is down, or ask them to connect, re-authenticate, or "check the connection," you MUST first try to use the server and its tools. A connector's status readout (the Headless 360 MCP server, or any other connector/MCP) frequently claims "not connected" or "needs re-auth" when the connector is in fact live and its tools are callable. Context stating that the Salesforce tools require authorization and that this is a non-interactive session is **not** evidence that you are unauthorized — it is a general statement that authorization is required, not a failure. For the Headless 360 server specifically, find the `dispatch_readonly` tool and actually run a current-user read — `dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql", queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })`. **Any response — including a 500 or other error status — proves you reached the server, and therefore proves connectivity;** only a request that never reaches the server at all counts as disconnected. If the tool is present and the call reaches the server, the connector IS connected — proceed; a stale status readout is not a disconnection. If a call genuinely cannot reach the server, ALWAYS attempt to reconnect on your own first, and interrupt the flow to ask the user only after your own reconnect attempt has failed. Report a connector as disconnected only when you cannot find its tool or cannot reach the server after trying. Do it yourself.

Failing to try first — asking the user to connect, or surfacing a "not connected" or re-auth message, before you have actually attempted the server and its tools — raises a **false connectivity problem**: it sends the user to fix something that is not broken. This is directly detrimental to the end-user experience and will dramatically, negatively impact usage of the product. Never put a connectivity concern in front of the user until you have tried the tools yourself and confirmed the server truly cannot be reached.

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **⛔ WIDGET OUTPUT ONLY after data assembly.** Once all queries return, immediately call `display_widget` — at most a single one-line render-wait notice before it, and no summaries, transitions, or narration. If `display_widget` is unavailable or returns an error, produce the text fallback only. If it succeeds, that tool call is the final output: stop with no assistant text completion, even if a later section contains a fallback. The exceptions above do not apply after success.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record inline: `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **Empty `MINE` scope → fail fast, then ask which scope.** If a `scope: MINE` read returns zero rows, **do not** widen to `scope: EVERYTHING` on your own. Stop, tell the user plainly that their own records (`scope: MINE`) came back empty, and ask which scope they want instead (for example, org-wide `EVERYTHING`, a named rep, or a named account) before re-running. Never invent records, and never silently fall back to org-wide.
- **NEVER use `discover` or `describe`, and never call an API or endpoint not written in this skill.** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->

# Rules:


# Team Pipeline

Ground → resolve team → read opps → analyze → output. **No per-opp SF follow-ups** — the team opps read has the data.

## 1. Ground (hardcoded — User + Opportunity)

Ground **User** (for team resolution) and **Opportunity** (for pipeline fields). Both always exist. **Fire as two separate calls, not one combined call** — combined User+Opportunity ObjectInfo commonly exceeds the tool's char limit, and recovering from that overflow (temp file outside the bash mount, failed `cat`, retry) costs far more than just issuing two calls up front. Same turn, same shape, one `apiNames` each:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"User\\\"]) { fields { ApiName label dataType relationshipName } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label dataType relationshipName } } } }\"}" })
```

**If either still overflows**, the result auto-persists to a temp file **outside the bash mount** — don't shell to it (`cat`/`python3`/`ls` will fail, it's not on that mount). Read it back with the Read tool only, and go straight to that — don't retry bash first. If the Read tool can't load it either, skip custom-field grounding for that object and proceed with standard fields only; don't keep retrying.

From the result: (a) scalar `__c` fields (quota, forecast, risk, etc.) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's Name.

## 2. Resolve team

**"my team"** (default) — reps where Manager = current user:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { and: [{ ManagerId: { eq: \\\"<CURRENT_USER_ID>\\\" } }, { IsActive: { eq: true } }] }, first: 50) { edges { node { Id Name { value } Email { value } <USER_CUSTOM> } } } } } }\"}" })
```

**Exact rep names only** (disambiguate — do NOT probe): shared/demo orgs collide hard on name (one name → base user plus regional variants like `(AM)`/`(BK)`/`(SG)`). Run this resolver once per exact rep name supplied by the user and pull enough candidates to disambiguate at a glance — never pull each candidate's pipeline to guess which is real. If the user supplies only a role or territory, stop and ask for the exact rep names; the implemented resolver filters `User.Name` only and cannot resolve a role or territory:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Title { value } IsActive { value } } } } } } }\"}" })
```

**One exact active Name match** → take its Id. **Zero, several, or only inactive matches** → list returned candidates (Name · Title · active? · Id) and ask the user to pick or provide another exact name. Don't guess.

**Roster scope and caps — Quick/Kiro correction:** Both roster requests are bounded: the manager path uses `first: 50`, and each exact-name resolver uses `first: 10`. If a response fills its cap, treat it as potentially capped rather than complete; say so and ask for the exact rep names needed before claiming a complete roster. A user-supplied exact list can define the requested roster, but a capped search result cannot silently define the whole team.

Insert `<USER_CUSTOM>` = confirmed scalar `__c { value }` fields (quota, etc.). Capture the Ids — they become the owner filter in step 3.

## 3. Read team opps — AGGREGATE the rollup, SAMPLE team-wide top deals, ISSUE ALL IN ONE TURN

**Do not pull the whole team's book as raw records.** A team of 5+ reps with 200 open opps returns well past the point a tool result overflows and auto-persists to a temp file (then you can't shell to it — it's outside the bash mount; same overflow `pipeline-review` hit). Salesforce aggregates server-side — use it for the complete in-period scoreboard math; only one small, bounded, team-wide sample of concrete deals comes back as raw records, for swing-deal specifics and evidence-backed flags.

Fire these as tool calls in **one turn** (independent, all filtered by the team-user Ids from step 2). Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields (risk, coaching signals, etc.) on the sample query only — aggregates don't need them.

**Date filters take a `DateInput` object, never a bare string** (`gte: \"2026-07-01\"` fails `WrongType … must be an object type`). For the current-quarter bounds below, use the exact-date form on both ends: `{ value: \"YYYY-MM-DD\" }`. Multiple ops on one field (`gte`/`lte`) AND automatically — no `and: [...]` wrapper needed around them.

**Rollup by forecast category (GraphQL aggregate — folded into the team-wide first-60 sample request below).** `ExpectedRevenue` (Amount × Probability, a standard field) sums straight to the Weighted column — no client-side probability math. This rollup rides in the sample query (below) as an `aggregate` sibling of the detail read — one dispatch returns both. It yields one row per rep × actual returned forecast category. Per rep: Commit $ = that rep's returned `Commit`-category `Amount.sum`; Best-case $ = the returned `BestCase` row; Weighted = Σ `ExpectedRevenue.sum` across that rep's aggregate rows.

**Closed-won this period, per rep (GraphQL aggregate).** Feeds the scoreboard's Closed column:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsWon: { eq: true }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } Amount { sum { value } } } } } } } } }\"}" })
```

**Team-wide Amount-descending first-60 sample + complete forecast-category rollup (ONE request).** The aggregate rollup gives complete in-period scoreboard numbers for the selected owners; the detail side gives one global team-wide sample of named deals for swing-deal writeups, evidence-backed risk/hygiene overlap, and Monday questions. Cap detail hard (`first: 60`, biggest first) so it never overflows — it is not top-N per rep and can crowd out a rep's rows. **`orderBy` takes only ONE field** — a multi-field array (`orderBy: [{...},{...},{...}]`) fails `WrongType ... must be an object type`; sort by `Amount` alone and associate each sampled row with its returned `Owner.Name`. The forecast-category rollup rides in this same request as an `aggregate` sibling of detail — read Commit/Best-Case/Weighted from its complete aggregate edges and named deals only from detail rows.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 60) { edges { node { Id Name { value } StageName { value displayValue } ForecastCategory { value } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } CreatedDate { value } Probability { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, groupBy: { OwnerId: { group: true }, ForecastCategory: { group: true } }) { edges { node { aggregate { OwnerId { value } ForecastCategory { value } Id { count { value } } Amount { sum { value } } ExpectedRevenue { sum { value } } } } } } } } }\"}" })
```

Map each aggregate `OwnerId` → rep name using the User list from step 2; associate each detail row by its returned `Owner.Name` — no extra lookup needed.

**Team-wide sample scope — Quick/Kiro correction:** Let `R` be the number of returned detail rows and `C` be the sum of `Id.count.value` across the matching in-period forecast-category aggregate rows. Only when `R == C` may the detail rows be called complete for exactly the selected owners and period. Otherwise describe every row-derived deal, Account, stage, activity, risk, hygiene overlap, Monday question, average, and swing claim as "among the team-wide top R by Amount"; never generalize it per rep or to the complete in-period/full-open book. The aggregate remains authoritative for complete in-period count, Amount, Commit, Best Case, and Weighted totals.

**If a GraphQL `aggregate` query errors** (some orgs throw grouping a picklist/Id field), don't retry the same shape — fall to the SOQL `GROUP BY` equivalent, which groups cleanly. **For the combined sample request specifically**, the grouped `aggregate` sibling (`OwnerId`/`ForecastCategory`) can take the whole request down with it — re-fire the sample as the detail `query` alone (drop the `aggregate` block) to keep the named deals, and get the per-rep rollup from this SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT OwnerId, ForecastCategory, COUNT(Id) cnt, SUM(Amount) amt, SUM(ExpectedRevenue) weighted FROM Opportunity WHERE OwnerId IN (<TEAM_USER_IDS>) AND IsClosed = false AND CloseDate >= <Q_START> AND CloseDate <= <Q_END> GROUP BY OwnerId, ForecastCategory" })
```
(Closed-won the same way: swap `IsClosed = false` for `IsWon = true` and drop the `ForecastCategory` group.)

**Hygiene counts (GraphQL aggregate, full book — feeds step 6, not detail-sample-limited).** The team-wide top-60 sample above skews toward the biggest deals; these three reads return per-rep numerators across the full open book so stale/past-close/blank-NextStep flags are not limited to that sample. They do not return a matching full-open denominator. `<STALE_CUTOFF>` = today − 14 days, `<TODAY>` = today, both as `DateInput` (`{ value: "YYYY-MM-DD" }`):
```
-- Stale 14d+, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, LastActivityDate: { lte: { value: \\\"<STALE_CUTOFF>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })

-- Past CloseDate, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, CloseDate: { lt: { value: \\\"<TODAY>\\\" } } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })

-- Blank NextStep, per rep
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(where: { OwnerId: { in: [<TEAM_USER_IDS>] }, IsClosed: { eq: false }, NextStep: { eq: null } }, groupBy: { OwnerId: { group: true } }) { edges { node { aggregate { OwnerId { value } Id { count { value } } } } } } } } }\"}" })
```
Fire these in the same turn as the rollup/closed-won/sample queries above. If `aggregate` errors on any of the three, fall to SOQL `COUNT(Id) ... GROUP BY OwnerId` with the matching WHERE (same fallback pattern as the rollup above).

**Perf guardrail:** Do NOT fire per-opp SF follow-ups (`EmailMessage`, `Task`, `OpportunityFieldHistory`) — the rollups + sample above already have the data. Email/doc/Slack searches for flagged accounts only (step 3b).

## 3b. Evidence (dependent wave unless Account names were already known)

**Evidence dependency — Quick/Kiro correction:** Account-keyed email/document/Slack searches require the top 3–5 at-risk Account names. If those names first arrive in the step-3 detail result, wait for step 3, then issue all available searches together in a later wave; record that dependency and do not claim source-required same-turn parallelism. Only when the exact Account names were independently known before step 3 may these searches share the step-3 turn. Search by exact returned `Account.Name.value`:
- **slack**: internal mentions in team channel (if configured) → reps already flagging something

Use whatever email, document, and Slack search tools are available. If none are present, skip silently. Cite source + date for anything you use.

## 4. Per-rep scoreboard

**Scoreboard formulas and cohort boundaries — Quick/Kiro correction:** Build each rep's scoreboard from the complete selected-owner, selected-period aggregates, never from the bounded detail rows:

| Rep | Closed | Commit | Weighted | Gap | Attainment | Call (policy only) |
|---|---|---|---|---|---|---|

- **Closed** = that rep's `Amount.sum.value` from the closed-won aggregate; a missing owner row is zero only when the aggregate succeeded for the complete requested roster.
- **Commit** = that rep's `Amount.sum.value` for the actual returned `ForecastCategory.value == "Commit"`; if the complete category aggregate has no Commit row for that rep, use zero.
- **Weighted** = the sum of that rep's returned `ExpectedRevenue.sum.value` values across all actual forecast-category aggregate rows; do not recompute it from sampled rows.
- For a positive sourced or user-supplied quota, **gap = Closed + Commit − quota**. A negative gap is a shortfall; disclose that sign convention anywhere Gap is shown.
- For a positive quota, **attainment = 100 × Closed / quota**. State the rounding used for display.
- If shown, **weighted coverage = 100 × Weighted / quota**, labeled exactly `Weighted coverage`; do not substitute open Amount, Commit, or a sample-derived numerator.

Keep these in-period values separate from full-open hygiene numerators. Never combine a stale/past-close/blank-NextStep count with the in-period aggregate count or detail count to claim `all`, `every`, a percentage, or a denominator. If quotas are not in Salesforce, ask once and remember them for the session; do not infer them.

Use the user's supplied period label exactly in titles/captions; do not add `FY`, a fiscal quarter, or a week number that the user or returned data did not supply. Use one explicit as-of date and timezone for every day count, stale cutoff, and days-left calculation, and surface that basis when any such value is shown.

**Policy-neutral presentation — Quick/Kiro correction:** Worked examples below provide shape only, never runtime labels, thresholds, formulas, or values. Unless an attributable user/team rule defines pace/status thresholds and meter bands, set `headerStatus:"PIPELINE SNAPSHOT"` with `headerStatusVariant:"info"`, omit every row `status` object, pass no meter bands (or an empty array when the renderer requires the optional key), and use factual meter label/value/status wording. Do not copy `Behind`, `At risk`, `Ahead`, or 60/90 bands from examples. If an attributable policy exists, state it and apply it consistently before using qualitative calls or bands.

## 5. Deals that decide the quarter

Identify 3–5 sampled Opportunities that could swing the selected period: large Amount × late current stage × negative rep gap × closing in the period. These are row-derived claims, so apply the `R == C` completeness rule above and otherwise label them as selected from the team-wide top-`R` Amount sample. For each, write three lines:

- **Why it matters:** if the rep's formula-defined gap is negative, use `100 × Opportunity Amount / abs(gap)` and state the rounded result (for example, "$X is N% of [rep]'s shortfall"); otherwise omit the percentage rather than inventing a denominator.
- **Risk:** [specific thing that could kill it, from returned fields or dated external evidence]
- **Do this:** [one concrete leader action — "ask [rep] when they last talked to procurement; offer to send exec note if it's been 5+ days"]

The "do this" is the point. Be specific enough that the leader can act without further research. A currently past-due `CloseDate` supports only `past close date`; never say `slipped`, `pushed`, or `moved` without history or a prior CloseDate.

## 6. Team-level flags

- **Commit deals with returned risk evidence:** any sampled Commit-category deal with a returned risk flag or dated external evidence — apply the sample qualifier unless `R == C`
- **Coaching signals:** reps with the largest raw full-open stale/past-close/blank-NextStep counts or a formula-defined negative gap; do not turn raw counts into percentages without a matching full-open denominator
- **Hygiene:** rank reps by the three raw full-open aggregate counts, kept separate from the in-period cohort; name specific sampled Accounts only where their returned rows overlap and label the sample scope
- **Big swings:** use `Amount > 2 × average` only when the average's cohort is named. If `R == C`, average may be complete in-period aggregate `Amount.sum / Id.count` for the selected owners; otherwise use and label the team-wide top-`R` sample average, or omit the claim

Never describe a full-open numerator as `all` or `every` open Opportunity unless a matching full-open denominator was returned and reconciled.

## 7. Monday questions

For each rep with a formula-defined negative gap or a sampled deal carrying specific returned risk evidence, write ONE question phrased the way the leader would actually ask it in a 1:1 or Slack. Ground it in that returned deal and apply the sample qualifier when `R != C`; keep it conversational, not interrogative. Examples: "where's the [Account] security review at — saw it's been a couple weeks" / "do you need anything from me on [Account] or is it just waiting on them."

Search Slack for each rep's recent posts in the team channel from config — if they already flagged something, reference it instead of re-asking.


## 8. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

Chart series are actual returned forecast categories, not sales stages: create one `{name, data}` object for each distinct `ForecastCategory.value` present in the complete aggregate (for example `Pipeline`, `BestCase`, or `Commit`), using that category's raw `Amount.sum.value` per rep in `chartCategories` order and zero only for a missing rep/category row in a successful complete aggregate. Never bucket or relabel `StageName`, and never force Proposal / Negotiation / Closing. Datagrid `plan`/`closed`/`commit`/`gap` values are raw currency numbers, `attain` is the formula-defined 0–100+ percentage, and `status` is omitted unless an attributable policy defines it. Build `recordLinkButtons` with one complete User button per displayed rep followed by one complete Opportunity button per displayed swing deal, using each exact returned Name/Id and type-specific Lightning URL.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Worked examples provide shape only, never runtime values, formulas, thresholds, or labels. Authoring guidance (from the skill): `title` uses the user-supplied period label exactly · `headerStatus` and `headerStatusVariant` carry a policy-grounded badge or the neutral PIPELINE SNAPSHOT/info pair · `subtitle` is a factual, cohort-qualified one-line summary · `chartCaption chartCategories chartSeries` describe rep names plus one raw-Amount series per actual returned ForecastCategory value · `meterLabel meterValue meterMax meterTarget meterValueLabel meterTargetLabel meterStatus meterBands` use factual sourced values; `meterBands` is optional and omitted/empty without an attributable policy · `datagridCaption datagridRows` describe one row per rep with `{rep, plan, closed, commit, gap, attain, status?}` where names are exact `User.Name.value`, gap is Closed + Commit − quota, attainment is 100 × Closed / quota, and status is omitted without an attributable policy · `recordLinkButtons` contains one exact User link per displayed rep followed by one exact Opportunity link per displayed swing deal · `calloutTitle calloutDescription ctaPrimaryLabel ctaPrimaryMsg ctaSecondaryLabel ctaSecondaryMsg` carry sample-qualified synthesis and the two retained sendMessage actions.",
  "props": {
    "title": {
      "description": "Page title using the user-supplied period label exactly; do not invent fiscal or week labels.",
      "type": "string",
      "example": "Team pipeline — Q3 2026"
    },
    "headerStatus": {
      "description": "Policy-grounded header label; use PIPELINE SNAPSHOT when no attributable pace/status policy exists.",
      "type": "string",
      "example": "PIPELINE SNAPSHOT"
    },
    "headerStatusVariant": {
      "description": "Header badge variant; use info for the neutral PIPELINE SNAPSHOT and warning/error/success only from an attributable status policy.",
      "type": "string",
      "enum": [
        "neutral",
        "primary",
        "secondary",
        "outline",
        "success",
        "info",
        "warning",
        "error"
      ],
      "example": "info"
    },
    "subtitle": {
      "description": "Factual summary using the exact requested period and one explicit as-of date/timezone when day counts appear.",
      "type": "string",
      "example": "Q3 2026 · $3.22M closed of $6.0M plan · 3 reps · as of 2026-07-24 UTC"
    },
    "chartCaption": {
      "description": "Caption identifying the selected period and actual returned forecast-category breakdown by rep.",
      "type": "string",
      "example": "Q3 2026 open Amount by rep and forecast category"
    },
    "chartCategories": {
      "description": "Rep names for the chart's x-axis, as strings.",
      "type": "array",
      "items": {
        "type": "string"
      },
      "example": [
        "Priya",
        "Marcus",
        "Dana",
        "Tom",
        "Sara",
        "Jon"
      ]
    },
    "chartSeries": {
      "description": "One series per actual returned ForecastCategory value, with raw Opportunity Amount per rep in chartCategories order; never derive series from StageName.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "description": "Exact returned ForecastCategory value, such as Pipeline, BestCase, or Commit.",
            "type": "string"
          },
          "data": {
            "description": "Raw Amount sums per rep for this returned category; a number array matching chartCategories.",
            "type": "array",
            "items": {
              "type": "number"
            }
          }
        }
      },
      "example": [
        {
          "name": "Pipeline",
          "data": [
            900000,
            1100000,
            700000,
            600000,
            500000,
            400000
          ]
        },
        {
          "name": "BestCase",
          "data": [
            500000,
            700000,
            900000,
            500000,
            400000,
            300000
          ]
        },
        {
          "name": "Commit",
          "data": [
            200000,
            300000,
            400000,
            300000,
            300000,
            200000
          ]
        }
      ]
    },
    "meterLabel": {
      "description": "Factual label for closed Amount versus the selected team plan.",
      "type": "string",
      "example": "Closed versus plan"
    },
    "meterValue": {
      "description": "Team closed-won Amount for the selected period, as a raw currency number.",
      "type": "number",
      "example": 3220000
    },
    "meterMax": {
      "description": "Team plan/quota as a raw currency number; may equal meterTarget.",
      "type": "number",
      "example": 6000000
    },
    "meterTarget": {
      "description": "Team plan/quota target as a raw currency number; may equal meterMax.",
      "type": "number",
      "example": 6000000
    },
    "meterValueLabel": {
      "description": "Factual closed-versus-plan label with formula-defined attainment.",
      "type": "string",
      "example": "$3.22M closed of $6.0M plan — 54% attained"
    },
    "meterTargetLabel": {
      "description": "Display label for the sourced or user-supplied team plan.",
      "type": "string",
      "example": "$6.0M plan"
    },
    "meterStatus": {
      "description": "Factual meter description; qualitative pace wording requires an attributable policy.",
      "type": "string",
      "example": "Closed Amount versus supplied plan"
    },
    "meterBands": {
      "description": "Optional policy-grounded color bands. Use an empty array or omit the attribute when no attributable threshold policy exists; never copy worked-example thresholds into runtime output.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "from": {
            "description": "Band start value.",
            "type": "number"
          },
          "to": {
            "description": "Band end value.",
            "type": "number"
          },
          "variant": {
            "description": "Band color.",
            "type": "string",
            "enum": [
              "error",
              "warning",
              "success"
            ]
          },
          "label": {
            "description": "Short policy-grounded band label.",
            "type": "string"
          }
        }
      },
      "example": []
    },
    "datagridCaption": {
      "description": "Caption naming the selected period and explaining that negative position values are shortfalls.",
      "type": "string",
      "example": "Per-rep Q3 2026 scoreboard · negative position means shortfall"
    },
    "datagridRows": {
      "description": "One row per resolved rep. Omit status unless an attributable team policy defines it; an empty array omits the datagrid.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "status": {
            "description": "Optional policy-grounded Status badge; omit when no attributable status policy exists.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Policy-grounded status label.",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Policy-grounded badge color.",
                "type": "string",
                "enum": [
                  "neutral",
                  "primary",
                  "secondary",
                  "outline",
                  "success",
                  "info",
                  "warning",
                  "error"
                ]
              }
            }
          },
          "rep": {
            "description": "Exact User.Name.value for the resolved rep, as a plain string.",
            "type": "string"
          },
          "plan": {
            "description": "Sourced or user-supplied rep quota as a raw currency number.",
            "type": "number"
          },
          "closed": {
            "description": "Selected-period closed-won Amount from the complete aggregate.",
            "type": "number"
          },
          "commit": {
            "description": "Selected-period Amount for the actual returned Commit forecast category.",
            "type": "number"
          },
          "gap": {
            "description": "Closed + Commit − quota; a negative raw currency number is a shortfall.",
            "type": "number"
          },
          "attain": {
            "description": "100 × Closed / positive quota, with disclosed rounding.",
            "type": "number"
          }
        }
      },
      "example": [
        {
          "rep": "Priya Nair",
          "plan": 2000000,
          "closed": 820000,
          "commit": 640000,
          "gap": -540000,
          "attain": 41
        },
        {
          "rep": "Marcus Lee",
          "plan": 2000000,
          "closed": 1180000,
          "commit": 500000,
          "gap": -320000,
          "attain": 59
        },
        {
          "rep": "Dana Ruiz",
          "plan": 1800000,
          "closed": 1240000,
          "commit": 420000,
          "gap": -140000,
          "attain": 69
        }
      ]
    },
    "recordLinkButtons": {
      "description": "Complete tile/button blocks: one User action/openLink per displayed rep followed by one Opportunity action/openLink per displayed swing deal, each labeled from and targeting the same exact returned Name/Id.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "definition": {
            "type": "string",
            "enum": [
              "tile/button"
            ]
          },
          "attributes": {
            "type": "object"
          }
        }
      },
      "example": [
        {
          "definition": "tile/button",
          "attributes": {
            "label": "Open rep Priya Nair",
            "iconName": "open-in-new",
            "variant": "secondary",
            "actions": {
              "click": [
                {
                  "definition": "action/openLink",
                  "attributes": {
                    "url": "https://org.lightning.force.com/lightning/r/User/005000000000001AAA/view"
                  }
                }
              ]
            }
          }
        },
        {
          "definition": "tile/button",
          "attributes": {
            "label": "Open opportunity Cobalt Robotics — Platform Expansion",
            "iconName": "open-in-new",
            "variant": "secondary",
            "actions": {
              "click": [
                {
                  "definition": "action/openLink",
                  "attributes": {
                    "url": "https://org.lightning.force.com/lightning/r/Opportunity/006000000000001AAA/view"
                  }
                }
              ]
            }
          }
        }
      ]
    },
    "calloutTitle": {
      "description": "Factual synthesis heading grounded in the selected-period aggregate and returned detail cohort.",
      "type": "string",
      "example": "3 returned deals carry the largest Amount"
    },
    "calloutDescription": {
      "description": "Cohort-qualified synthesis using current returned fields and dated evidence; never infer movement from a current CloseDate.",
      "type": "string",
      "example": "Cobalt Robotics ($1.8M, Priya), Meridian Health ($2.4M, Marcus), and Alto Financial ($0.9M, Dana) are the largest returned deals. Use their current stages, dates, and attributable evidence for follow-up."
    },
    "ctaPrimaryLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft team review note"
    },
    "ctaPrimaryMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft a team review note covering the returned swing deals, with specific evidence-backed unblock recommendations for each rep."
    },
    "ctaSecondaryLabel": {
      "description": "Secondary button label (action/sendMessage).",
      "type": "string",
      "example": "Open pipeline summary"
    },
    "ctaSecondaryMsg": {
      "description": "First-person prompt the secondary button sends (action/sendMessage).",
      "type": "string",
      "example": "Summarize the team's pipeline by returned forecast category, quota gap, and raw hygiene counts."
    }
  }
}
```
```json
{
  "renderer": {
    "componentOverrides": {
      "$": {
        "type": "mosaic",
        "definition": "tile/widget",
        "children": [
          {
            "definition": "tile/row",
            "attributes": {
              "gap": "sm",
              "align": "center",
              "justify": "between",
              "isWrapped": true
            },
            "children": [
              {
                "definition": "tile/row",
                "attributes": {
                  "gap": "sm",
                  "align": "center"
                },
                "children": [
                  {
                    "definition": "tile/icon",
                    "attributes": {
                      "name": "dashboard",
                      "size": "xl",
                      "alt": ""
                    }
                  },
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{title}}",
                      "variant": "h1"
                    }
                  }
                ]
              },
              {
                "definition": "tile/badge",
                "attributes": {
                  "label": "{{headerStatus}}",
                  "variant": "{{headerStatusVariant}}"
                }
              }
            ]
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "{{subtitle}}",
              "variant": "caption",
              "color": "muted"
            }
          },
          {
            "definition": "tile/separator"
          },
          {
            "definition": "tile/column",
            "attributes": {
              "gap": "md"
            },
            "children": [
              {
                "definition": "tile/chart",
                "attributes": {
                  "chartType": "column",
                  "caption": "{{chartCaption}}",
                  "categories": "{{chartCategories}}",
                  "series": "{{chartSeries}}",
                  "stackMode": "stacked",
                  "valueFormat": "compact",
                  "showValues": false
                }
              },
              {
                "definition": "tile/meter",
                "attributes": {
                  "label": "{{meterLabel}}",
                  "value": "{{meterValue}}",
                  "min": 0,
                  "max": "{{meterMax}}",
                  "target": "{{meterTarget}}",
                  "valueFormat": "currency",
                  "valueLabel": "{{meterValueLabel}}",
                  "targetLabel": "{{meterTargetLabel}}",
                  "status": "{{meterStatus}}",
                  "bands": "{{meterBands}}"
                }
              }
            ]
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{datagridCaption}}",
              "appearance": "striped",
              "size": "sm",
              "defaultSort": {
                "key": "gap",
                "direction": "asc"
              },
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "rep",
                  "header": "Rep",
                  "type": "avatar"
                },
                {
                  "key": "plan",
                  "header": "Plan",
                  "type": "currency",
                  "align": "right"
                },
                {
                  "key": "closed",
                  "header": "Closed",
                  "type": "currency",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "commit",
                  "header": "Commit",
                  "type": "currency",
                  "align": "right"
                },
                {
                  "key": "gap",
                  "header": "Gap to plan",
                  "type": "currency",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "attain",
                  "header": "Attainment",
                  "type": "databar",
                  "target": 100
                }
              ],
              "rows": "{{datagridRows}}"
            }
          },
          {
            "definition": "tile/column",
            "attributes": {
              "gap": "sm"
            },
            "children": [
              {
                "definition": "tile/text",
                "attributes": {
                  "text": "Team and swing records",
                  "variant": "section-title"
                }
              },
              {
                "definition": "tile/row",
                "attributes": {
                  "gap": "sm",
                  "align": "center",
                  "isWrapped": true
                },
                "children": "{{recordLinkButtons}}"
              }
            ]
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "warning",
              "title": "{{calloutTitle}}",
              "description": "{{calloutDescription}}"
            },
            "children": [
              {
                "definition": "tile/row",
                "attributes": {
                  "gap": "sm",
                  "align": "center",
                  "isWrapped": true
                },
                "children": [
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{ctaPrimaryLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{ctaPrimaryMsg}}"
                            }
                          }
                        ]
                      }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{ctaSecondaryLabel}}",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{ctaSecondaryMsg}}"
                            }
                          }
                        ]
                      }
                    }
                  }
                ]
              }
            ]
          }
        ]
      }
    }
  }
}
```

Self-verification before calling:
- [ ] One attainment meter only; `value`, `max`, and `target` are raw currency numbers. `target` may equal `max` when both are the team plan. `meterBands` is empty/omitted unless an attributable threshold policy supplies every bound and label.
- [ ] Chart has a visible forecast-category caption, `stackMode: "stacked"`, and exactly one series per actual returned `ForecastCategory.value`, with one raw-dollar value per rep matching `chartCategories` order. No series comes from StageName or a worked example.
- [ ] Every datagrid currency cell is a raw number (not `{ value, display }` — the type annotation handles formatting); each gap equals Closed + Commit − quota, and each attainment value equals 100 × Closed / positive quota.
- [ ] Without an attributable status policy, the header is `PIPELINE SNAPSHOT`/`info` and every row omits `status`. With a policy, every badge and band cites and follows that same policy.
- [ ] `recordLinkButtons` contains one exact User link per displayed rep followed by one exact Opportunity link per displayed swing deal; labels and Ids come from the same returned records. Neither action is clicked during rendering.
- [ ] Blocks with no data are omitted rather than populated from examples; an empty optional `meterBands` array is allowed for policy-neutral output.
- [ ] Order is header → separator → (chart | meter) column → reps grid → team/swing record links → callout last.



## 9. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Team Pipeline - [user-supplied period label]
Target $[X] | Closed $[X] | [N] days left as of [date/timezone, if grounded]

## Scoreboard
| Rep | Closed | Commit | Weighted | Gap | Attainment | Call |
|---|---|---|---|---|---|---|
| [linked User Name] | $[X] | $[X] | $[X] | $[X; negative = shortfall] | [X]% | [policy-grounded value or —] |
...
| **Team** | **$[X]** | **$[X]** | **$[X]** | **$[X]** | **[X]%** | |

## Deals That Decide the Quarter
**[linked Opportunity Name / Account]** - $[X], [current Stage], [Rep]
  Why it matters: [formula-defined math, with sample scope]
  Risk: [specific returned or dated evidence; a past date is labeled past close, never slipped]
  → **Do this:** [one concrete leader action]

[repeat 3–5x]

## Risk Flags
- Close-date movement: not checked — no history or prior CloseDate was queried
- Last activity on/before [cutoff]: [raw count] open opps - [sample-qualified Account examples]
- Past close date: [raw count] open opps need hygiene before the call
- Blank Next Step: [raw count] open opps

## Monday Questions
- **[Rep]:** "[one question, conversational, deal-grounded, and sample-qualified when needed]"
- **[Rep]:** "[...]"

## If you want to dig
- Per-rep detail: ask "just [rep name]"
- Full at-risk detail: choose one rep and ask "show [rep name]'s at-risk pipeline"
```
