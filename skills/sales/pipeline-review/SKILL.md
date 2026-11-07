---
name: pipeline-review
description: "Build exactly one rep's current pipeline assessment from Salesforce stage aggregates, deal samples and closed-deal history, covering coverage, hygiene and risks. Use only for the current user's own book or one named rep. Two or more named reps, a rep list, team, or multi-rep comparison: team-pipeline. For changes over time: deal-signals."
icon: assets/salesforce.svg
checksum: "sha256:3d60c96a7d8cec47bf65436277b8acea8818695bc0b3ff82450c11d469cd0fdf"
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

- Resolve scope to one owner before the read; if a named rep is ambiguous, ask — don't guess or probe.
- Reconcile headline totals with the detail rows.

# Pipeline Review

Ground → resolve scope → (aggregate the book + sample the top deals, ONE turn) → assemble + flag → output. This is one rep's pipeline — for "my team's pipeline" use team-pipeline; for "what changed" use deal-signals.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's stage/risk/activity `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. Note scalar `__c` fields worth rolling up (stage-entry date, risk, health, forecast). **Response can be large** on customized orgs — if it truncates and auto-persists to a temp file, that file is **outside the bash mount**: don't shell to it (`cat`/`jq`/`python3`/`ls` will fail, it's not on that mount). Read it back with the **Read tool only**, go straight there — don't retry bash first — and scan for `__c` fields whose `label` matches your keywords. Grounding is best-effort (customs are additive); if the Read tool can't load it either, take the standard fields and move on. Stage buckets come from the `StageName` values the reads return; standard fields, `Account`/`Owner` spans, and `OpportunityContactRoles` are reliable across orgs.

## 1b. Resolve scope

- **"my pipeline"** (default) → add `scope: MINE` to the query root — no user-Id lookup.
- **named rep** → resolve one User. Pull enough to disambiguate at a glance — shared/demo orgs collide hard (one name → base user plus regional variants like `(AM)`/`(BK)`/`(SG)`):
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Title { value } IsActive { value } } } } } } }\"}" })
  ```
  **One match** → take its Id. **Several** → list them (Name · Title · active? · Id) and ask the user to pick; the suffix/title is usually the tell. Don't pick or probe their pipelines to guess. Then filter opps by `OwnerId: { eq: \"<UserId>\" }`.
- **team** → out of scope; hand to team-pipeline.

## 2. Read (fill from step 1) — AGGREGATE the book, SAMPLE the top deals, ISSUE ALL IN ONE TURN

**Do not pull the whole book as raw records.** A rep with 100+ open opps returns 75KB+, which overflows the tool result and auto-persists to a temp file (then you can't shell to it — it's outside the bash mount; you'd have to read it back directly). Salesforce aggregates server-side — use it. The stats come from aggregate rows (a handful, not hundreds); only a small, bounded sample of concrete deals comes back as raw records.

Fire these as tool calls in **one turn** (independent). Insert `<OPP_CUSTOM>` = confirmed `__c { value }` fields on the sample query only (aggregates don't need them).

**2a. Whole-book rollup by stage (GraphQL aggregate — folded into the 2b request).** No `CloseDate` filter for a health view — a `THIS_QUARTER` filter silently drops deals as quarter boundaries move. If the user names a period, add explicit `CloseDate: { gte: … lte: … }`. This rollup rides in the 2b query as an `aggregate` sibling of the sample (one dispatch returns both); it yields one row per stage — stage name, count, $ sum — the by-stage table and the open total (Σ), with no extra record pull.

**2b. Top-N sample per stage + whole-book stage rollup (ONE request).** The rollup gives the shape; the sample gives named deals to point at. Cap the sample hard (`first: 40`, biggest first) so it never overflows — this is a sample, not the book. Order by `Amount DESC`; take the top few per stage when you present. The 2a stage `aggregate` rides in this same request as a sibling of the sample — read the by-stage counts/sums and open total from its `aggregate` edges and `totalCount`, the named deals from the sample rows.

**Combined-request integrity — Quick/Kiro adaptation (candidate-style experiment):**

- **Prepare:** Treat the inline literal 2b request below as authoritative. Before constructing it, load `references/combined-request.md` as a mechanically identical construction copy. If the sibling cannot be loaded, use the inline request. Substitute only grounded `<OPP_CUSTOM>` fields and the documented scope/date values; do not add fields, roots, or calls.
- **Validate before dispatch:** Decode `queryInput` and require valid outer JSON, no unresolved placeholders, one `uiapi.query.Opportunity` sample root and one sibling `uiapi.aggregate.Opportunity` stage root, the same resolved owner/date predicates on both roots, and structurally closed GraphQL.
- **If validation fails before dispatch:** Do not dispatch. Reload the unchanged sibling copy once, or the inline authority if the sibling was unavailable, repeat only the documented substitutions, and validate once more. Do not repair individual braces, compose another GraphQL request, or enter the aggregate fallback.
- **If Salesforce returns `InvalidSyntax` or unexpected `<EOF>`:** Treat it as reconstruction or truncation, not unsupported aggregation, and retry once from the unchanged literal template without brace repair.
- **If the validated canonical request returns a real aggregate execution error:** Use only the documented detail-only 2b request plus the exact SOQL stage rollup below; never author a standalone GraphQL stage-rollup request.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, first: 40, orderBy: { Amount: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } CreatedDate { value } NextStep { value } LastActivityDate { value } Type { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Id } } } } } } } aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```

**2c. Closed-baseline win rate (GraphQL aggregate, last full quarter).** Counts grouped by won/lost — no record pull, zero date math (`eq: { literal: LAST_QUARTER }`; widen only if asked):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: LAST_QUARTER } } }, groupBy: { IsWon: { group: true } }) { edges { node { aggregate { IsWon { value } Id { count { value } } Amount { sum { value } } } } } } } } }\"}" })
```

**2d. Whole-book hygiene by stage (GraphQL aggregate).** Blank-`NextStep` count per stage across the entire book — so the hygiene finding is book-wide, not "among the top 40 sampled". No date math:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, NextStep: { eq: null } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } } } } } } } }\"}" })
```
(Same `OwnerId` swap for a named rep. A stale-by-stage rollup is also expressible with a computed `LastActivityDate: { lt: "<today−14d>" }` cutoff grouped by StageName — but null-activity rows won't match `lt`, so it under-counts never-touched deals; blank-NextStep is the clean whole-book signal.)

**Named rep** → swap every `scope: MINE` for `OwnerId: { eq: \"<UserId>\" }`. **Empty** 2a `edges`/`totalCount: 0` → no open pipeline for this scope; say so plainly, skip the rest.

**If a GraphQL `aggregate` query errors** (some orgs throw `DataFetchingException` grouping a picklist/Id field), don't retry the same shape — fall to the SOQL `GROUP BY` equivalent, which groups picklists cleanly. **For the 2b combined request specifically**, the grouped `aggregate` sibling (`StageName`) can take the whole request down with it — re-fire 2b as the detail `query` alone (drop the `aggregate` block) to keep the sample, and get the by-stage rollup from this SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE IsClosed = false AND OwnerId = '<UserId>' GROUP BY StageName" })
```
(Own scope → resolve the current user's Id first, or filter by `Owner.Name`; SOQL has no `scope: MINE`.) Win rate the same way: `SELECT IsWon, COUNT(Id) cnt FROM Opportunity WHERE IsClosed = true AND CloseDate = LAST_QUARTER AND OwnerId = '<UserId>' GROUP BY IsWon`.

## 3. Assemble + flag (record only; reconcile totals; invent nothing)

- **By stage** — straight from 2a's aggregate rows: count, $ sum per stage. Σ of stage $ = open total (they come from the same query, so they reconcile by construction). **Blank-NextStep per stage is whole-book from 2d** — report those counts as book-wide. Staleness/aging per-stage aren't in an aggregate; report those from the 2b sample and **say they're "among the top N sampled," not whole-book**.
- **Top deals per stage** — from the 2b sample, name the biggest 2–3 opps in each stage (Account · $ · close · next-step state · type) so the rep sees concrete deals, not just totals.
- **At-risk opps** — from the 2b sample, flag any that hit: stale (no activity 14d+) · past `CloseDate` · blank `NextStep` · **single-threaded (`OpportunityContactRoles` edge count ≤ 1)**. **If a flag matches nearly the whole sample** (e.g. every opp has a blank `NextStep`, common in lightly-maintained orgs), report it once as a **systemic finding** — use 2d's book-wide blank-NextStep count for that line ("next-step blank on N of M open — hygiene gap") — and rank the at-risk list by $, rather than dumping dozens of identical-looking rows.

**At-risk ranking — Quick/Kiro adaptation (candidate-style experiment):**

- **Build:** Transform the returned 2b Opportunity nodes directly into one candidate collection keyed by Id; never hand-author or retype an intermediate tuple or row list. Include every sampled Id matching any source risk before truncation. Copy each `Name.value`, Amount, CloseDate, stage, and supporting risk field from that same Id, including punctuation. Past close means `CloseDate` is earlier than the as-of date. Sort the complete qualifying collection by returned Amount descending, then truncate for display.
- **Validate before hydration:** For every candidate and displayed row, compare Name, Amount, CloseDate, stage, and risk inputs with the same returned Id. Require no later row to have a larger Amount. Treat 2b detail-node findings as `among the top R sampled` unless sample edge count equals `totalCount`; when they are equal, reconcile every matching row's count and sum. Use whole-book wording only for the 2a aggregate/SOQL rollup and 2d hygiene aggregate, never for a capped detail sample.
- **If validation fails:** Discard the derived candidate/display collection and rebuild it once from the original Id-keyed returned nodes. Make no Salesforce call, do not patch or retype individual rows, and repeat validation before hydrating the unchanged widget.
- **Coverage** — weighted open pipeline (from 2a totals × stage probability if grounded, else raw open $) vs quota (only if the user gives one) or vs last-quarter closed $ from 2c; 3× remaining-gap heuristic; note if under.

**Probability grounding — Quick/Kiro adaptation:** `objectInfos` field metadata proves only that a field exists; it supplies no Opportunity probability value or stage-probability mapping. Compute weighted pipeline only from numeric probability values selected and returned by a literal documented request or from an explicit user-supplied mapping—never add `Probability` or `LastStageChangeDate` outside the documented placeholder substitutions and never infer default stage percentages. Without that evidence, show raw open pipeline only; without a quota or nonzero prior-quarter closed baseline, omit the coverage ratio and meter.
- **Velocity** — from 2c: win rate = won ÷ (won+lost) counts. **Cycle time / median: don't compute it** — no API (GraphQL aggregate or SOQL) supports median or date subtraction, and reconstructing it means pulling every closed record (the overflow we're avoiding). Only report an average cycle if grounding surfaced a numeric sales-cycle `__c` field you can `avg` in the aggregate. Stage→stage conversion needs stage history; omit — don't fabricate.

**Stage age — Quick/Kiro adaptation:** Populate each row's `age` only from a selected and returned stage-entry date whose grounded label has that meaning. `LastActivityDate` supports days idle in the risk text, not days in stage. If no stage-entry date was returned, remove `age` from every row and remove the `Days in stage` column while retaining the rest of the datagrid; never rename or repurpose that column as days idle.

## 4. Output — widget FIRST (the rendered UI is the default)

**Renderer transport — Quick/Kiro adaptation:** Pass the fully hydrated renderer directly as the native `widgetDefinition` object in the `display_widget` call; never serialize or quote it and never route it through a code block. If that call succeeds, it is the terminal output: stop immediately with no assistant text, including no render-success line, recap, or button suggestion. If it returns any error, do not create or open a substitute artifact or try another rendering path: emit only the Step 5 text fallback and stop; never claim that the widget rendered.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] Every {{token}} replaced with a resolved literal — no {{…}}, no {!…}.
- [ ] Numeric attributes (meter value/max/target, meter band from/to, datagrid amount/age) are numbers, not strings.
- [ ] Any "Win rate" / "Last-Q Win Rate" value shown in the widget or accompanying text is a 0–100 percentage computed as `won_count ÷ (won_count + lost_count) × 100`. If either count is unavailable, omit the win-rate line.
- [ ] The meter bands span [0, max] and the chart series data matches categories length.
- [ ] Every risky datagrid row carries a leading status:{value,badgeVariant} (badgeVariant error/warning); healthy rows omit it.
- [ ] The callout carries resolved title/description, and both buttons are real actions (sendMessage/openLink).
- [ ] The Step 5 text is produced only when `display_widget` is unavailable (the terminal fallback) — not alongside a rendered widget.

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `pageTitle` (e.g. \"Pipeline review — Dana Ruiz\"), `pageSubtitle` (one-line summary: \"$6.4M open across 18 opps · weighted $2.1M · closes this quarter\") · `chartCaption`, `chartCategories` (array of stage names), `chartSeries` (array with one object `{ name, data }` where data is number[] matching categories) · `coverageValue` (number), `coverageMax` (number), `coverageTarget` (number, typically 3.0), `coverageValueLabel` (e.g. \"2.4× open pipeline to $2.7M gap\"), `coverageTargetLabel` (e.g. \"3.0× target\"), `coverageStatus` (string: \"under-covered\" or \"covered\"), `coverageBands` (array of `{ from, to, variant, label }`, variants warning/success, spanning 0→max) · `datagridCaption` (e.g. \"At-risk opps: stalled, past close date, or missing next step\"), `datagridRows` (array, one per at-risk opp: `{name (plain string — format as the opportunity name (e.g. \"Meridian Health platform\"); names must be plain strings, not objects: use `Opportunity.Name.value` from the SF response), stage:{value,badgeVariant}, amount(number), age(number days in stage), close(\"YYYY-MM-DD\"), risk, status:{value,badgeVariant} (badgeVariant error/warning for risky rows or omit)}`) · `calloutVariant` (\"info\"), `calloutTitle` (e.g. \"Monday focus\"), `calloutDescription` (week's priorities), `primaryButtonLabel`, `primaryButtonMsg` (first-person prompt for sendMessage, e.g. \"Draft an email to...\"), `viewOppsUrl` (Opportunities list URL: `https://<myDomain>/lightning/o/Opportunity/list`). Omit any block whose data you lack rather than passing empty arrays; each `status` word must land in its meter band (under-covered/covered).",
  "props": {
    "pageTitle": {
      "description": "Page title (e.g. \"Pipeline review — Dana Ruiz\").",
      "type": "string",
      "example": "Pipeline review — Dana Ruiz"
    },
    "pageSubtitle": {
      "description": "One-line summary: open amount, opp count, weighted value, timeframe.",
      "type": "string",
      "example": "$6.4M open across 18 opps · weighted $2.1M · closes this quarter"
    },
    "chartCaption": {
      "description": "Caption for the pipeline-by-stage chart.",
      "type": "string",
      "example": "Open pipeline by stage; largest at Proposal, tapering to Closing"
    },
    "chartCategories": {
      "description": "Stage names for the chart's x-axis.",
      "type": "array",
      "items": {
        "type": "string"
      },
      "example": [
        "Qualification",
        "Proposal",
        "Negotiation",
        "Closing"
      ]
    },
    "chartSeries": {
      "description": "Chart series — one object {name, data}; data matches chartCategories.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "description": "Series name.",
            "type": "string"
          },
          "data": {
            "description": "Amount per stage — a number array matching chartCategories.",
            "type": "array",
            "items": {
              "type": "number"
            }
          }
        }
      },
      "example": [
        {
          "name": "Open $",
          "data": [
            1600000,
            2400000,
            1600000,
            800000
          ]
        }
      ]
    },
    "coverageValue": {
      "description": "Pipeline coverage ratio — the meter's current value (e.g. 2.4).",
      "type": "number",
      "example": 2.4
    },
    "coverageMax": {
      "description": "The meter's max.",
      "type": "number",
      "example": 5
    },
    "coverageTarget": {
      "description": "Coverage target (typically 3.0).",
      "type": "number",
      "example": 3
    },
    "coverageValueLabel": {
      "description": "Display string for coverage (e.g. \"2.4× open pipeline to $2.7M gap\").",
      "type": "string",
      "example": "2.4× open pipeline to $2.7M gap"
    },
    "coverageTargetLabel": {
      "description": "Display string for the target (e.g. \"3.0× target\").",
      "type": "string",
      "example": "3.0× target"
    },
    "coverageStatus": {
      "description": "Coverage read — under-covered or covered.",
      "type": "string",
      "enum": [
        "under-covered",
        "covered"
      ],
      "example": "under-covered"
    },
    "coverageBands": {
      "description": "Color bands for the coverage meter, in order spanning 0→max.",
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
            "description": "Short band label.",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "from": 0,
          "to": 3,
          "variant": "warning",
          "label": "Under"
        },
        {
          "from": 3,
          "to": 5,
          "variant": "success",
          "label": "Covered"
        }
      ]
    },
    "datagridCaption": {
      "description": "Caption for the at-risk opps datagrid.",
      "type": "string",
      "example": "At-risk opps: stalled, past close date, or missing next step"
    },
    "datagridRows": {
      "description": "At-risk opps (stalled, past close, or missing next step) — one row per opp. Empty array → the datagrid is omitted.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "status": {
            "description": "Leading Status badge cell; omit on normal rows.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Status label.",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Badge color.",
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
          "name": {
            "description": "Opportunity name, a plain string (use Opportunity.Name.value — never a nested object).",
            "type": "string"
          },
          "stage": {
            "description": "Stage badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Stage label.",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Badge color.",
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
          "amount": {
            "description": "Deal amount (number).",
            "type": "number"
          },
          "age": {
            "description": "Days in current stage (number).",
            "type": "number"
          },
          "close": {
            "description": "Close date, ISO YYYY-MM-DD.",
            "type": "string"
          },
          "risk": {
            "description": "Why the opp is at risk.",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Stalled",
            "badgeVariant": "error"
          },
          "name": "Meridian Health platform",
          "stage": {
            "value": "Proposal",
            "badgeVariant": "info"
          },
          "amount": 2400000,
          "age": 41,
          "close": "2026-08-05",
          "risk": "⚠ 41d in stage, no exec sponsor"
        },
        {
          "status": {
            "value": "At risk",
            "badgeVariant": "warning"
          },
          "name": "Cobalt Robotics renewal",
          "stage": {
            "value": "Negotiation",
            "badgeVariant": "warning"
          },
          "amount": 1800000,
          "age": 22,
          "close": "2026-07-30",
          "risk": "⚠ close date in 6d, redlines open"
        },
        {
          "name": "Pier 9 expansion",
          "stage": {
            "value": "Proposal",
            "badgeVariant": "info"
          },
          "amount": 600000,
          "age": 18,
          "close": "2026-07-31",
          "risk": "Legal review of MSA"
        },
        {
          "status": {
            "value": "At risk",
            "badgeVariant": "warning"
          },
          "name": "Northwind logistics",
          "stage": {
            "value": "Qualification",
            "badgeVariant": "neutral"
          },
          "amount": 450000,
          "age": 55,
          "close": "2026-09-15",
          "risk": "⚠ 55d, single-threaded"
        }
      ]
    },
    "calloutVariant": {
      "description": "Callout color; typically \"info\".",
      "type": "string",
      "enum": [
        "error",
        "warning",
        "success",
        "info",
        "recommended"
      ],
      "example": "info"
    },
    "calloutTitle": {
      "description": "Synthesis callout heading (e.g. \"Monday focus\").",
      "type": "string",
      "example": "Monday focus"
    },
    "calloutDescription": {
      "description": "Synthesis callout body — the week's priorities.",
      "type": "string",
      "example": "Confirm the Meridian exec sponsor call before it ages out of Proposal, and get Cobalt redlines back this week — it closes in 6 days. Coverage is thin at 2.4×; two more qualified Proposal-stage opps would close the gap."
    },
    "primaryButtonLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft sponsor ask"
    },
    "primaryButtonMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft an email to the Meridian Health platform sponsor to confirm next week's call and set the agenda."
    },
    "viewOppsUrl": {
      "description": "Opportunities list-view Lightning URL for the \"View in Salesforce\" button.",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/o/Opportunity/list"
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
              "isWrapped": false
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
                  "text": "{{pageTitle}}",
                  "variant": "h1"
                }
              }
            ]
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "{{pageSubtitle}}",
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
                  "valueFormat": "compact",
                  "showValues": true,
                  "showLegend": false
                }
              },
              {
                "definition": "tile/meter",
                "attributes": {
                  "label": "Coverage vs remaining gap",
                  "value": "{{coverageValue}}",
                  "min": 0,
                  "max": "{{coverageMax}}",
                  "target": "{{coverageTarget}}",
                  "valueLabel": "{{coverageValueLabel}}",
                  "targetLabel": "{{coverageTargetLabel}}",
                  "status": "{{coverageStatus}}",
                  "bands": "{{coverageBands}}"
                }
              }
            ]
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{datagridCaption}}",
              "appearance": "striped",
              "defaultSort": {
                "key": "amount",
                "direction": "desc"
              },
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "name",
                  "header": "Opportunity",
                  "type": "text"
                },
                {
                  "key": "stage",
                  "header": "Stage",
                  "type": "badge"
                },
                {
                  "key": "amount",
                  "header": "Amount",
                  "type": "currency",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "age",
                  "header": "Days in stage",
                  "type": "number",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "close",
                  "header": "Close",
                  "type": "date"
                },
                {
                  "key": "risk",
                  "header": "Risk",
                  "type": "text"
                }
              ],
              "rows": "{{datagridRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "{{calloutVariant}}",
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
                      "label": "{{primaryButtonLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{primaryButtonMsg}}"
                            }
                          }
                        ]
                      }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "View in Salesforce",
                      "iconName": "open-in-new",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/openLink",
                            "attributes": {
                              "url": "{{viewOppsUrl}}"
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


## 5. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Pipeline Review — <Scope> — <Period>

## Summary
Open: <N> opps, $<total> · weighted $<weighted> · coverage <N>× <✅ / ⚠ under 3×> · at-risk <N>, $<sum>

## By stage (whole book)
<Stage> · <N> opps · $<sum>
…  (Σ stage $ = $<total>, Σ opps = <N> — from the rollup)

## Top deals per stage (sampled, biggest first)
<Stage>: <Account> $<X> close <Date> · <next-step state> · <Type>; <Account> $<X> close <Date> …
… (name the biggest 2–3 opps per stage — the sample holds them)

## At-risk (from sample, biggest first)
<Account> · <Stage> · $<X> · close <Date> · <flags> → <action>
…  (Σ at-risk $ = $<sum>)
[If a flag hits nearly all sampled: one line — "Systemic: next-step blank on all <N> sampled — hygiene gap", don't list every row.]

## Conversion Signal (last-Q baseline)
Win rate <N%> (won <N> ÷ won+lost <N>, from 2c)[ · avg cycle <N>d only if a cycle-days field was grounded]. Stage→stage conversion needs stage history — omit, don't fabricate.

## Focus
1. Highest-$ at-risk + action
2. Biggest / most-exposed stage + action
3. Coverage gap if under 3×
```
