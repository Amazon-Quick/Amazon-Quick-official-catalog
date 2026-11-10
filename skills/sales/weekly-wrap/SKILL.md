---
name: weekly-wrap
display_name: Weekly Wrap
description: "Build a weekly sales recap from Salesforce opportunity and calendar activity plus email, documents and Slack, covering wins, losses, deal activity and next week's priorities. Use to review a rep's or team's week, prepare for Monday or draft an internal update."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:2b6bff1a3e3bfd2763e81db9982f20c0798d42327dbd6eda04e1f8ba90d2d0f0"
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


# Weekly Wrap

Ground → resolve scope (team only) → (TWO parallel SFDC reads + email/doc evidence, ALL in ONE turn) → assemble + flag → output. Keep the six detail roots and six aggregate roots in separate requests so each stays below the GraphQL fetcher limit.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's close/loss-reason `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Note any scalar `__c` fields worth surfacing (close/loss reason, stage-context note). Standard fields and the `Account` span are reliable across orgs.

## 1b. Resolve scope (team only — skip for "my week")

- **"my week"** (default) → `scope: MINE` on every root below, no lookup needed.
- **"team"** → resolve direct reports once:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { ManagerId: { eq: \\\"<CURRENT_USER_ID>\\\" }, IsActive: { eq: true } }, first: 50) { edges { node { Id Name { value } } } } } } }\"}" })
  ```
  Capture the Ids as `<TEAM_USER_IDS>`; swap every `scope: MINE` in step 2 for `OwnerId: { in: [<TEAM_USER_IDS>] }`. If your org's team hierarchy isn't ManagerId-based, resolve the roster once from context instead of guessing.

## 2. Read — pipeline movement + calendar in TWO dispatches; evidence in the SAME turn

**Why two:** a GraphQL request allows at most 10 subqueries ([Salesforce GraphQL query limits](https://developer.salesforce.com/docs/platform/graphql/guide/query-limits.html)). Six detail roots plus six aggregate roots in one request fails with `ExecutionAborted: The number of data fetchers in the query is 12, exceed the data fetcher limitation 10` (verified v60.0–v68.0). Fire the detail read and the aggregate read below as two `dispatch_readonly` GET GraphQL calls in the same parallel tool turn. Don't merge them back into one request.

**Detail read, six aliased roots:** closed, new, touched (moved), and closing-next-week Opportunities, plus this-week and next-week meetings. No `OpportunityHistory` read: `LastModifiedDate` on still-open opps is the movement signal, so there's no second object to ground or query. Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields from step 1.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { closedThisWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } newThisWeek: Opportunity(scope: MINE, where: { CreatedDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CreatedDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } touchedThisWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, LastModifiedDate: { eq: { literal: THIS_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } LastModifiedDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } closingNextWeek: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { eq: { literal: NEXT_WEEK } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } <OPP_CUSTOM> Account { Name { value } } } } } meetingsThisWeek: Event(scope: MINE, where: { ActivityDate: { eq: { literal: THIS_WEEK } } }, orderBy: { StartDateTime: { order: ASC } }, first: 50) { edges { node { Id Subject { value } StartDateTime { value } Location { value } WhatId { value } } } } meetingsNextWeek: Event(scope: MINE, where: { ActivityDate: { eq: { literal: NEXT_WEEK } } }, orderBy: { StartDateTime: { order: ASC } }, first: 50) { edges { node { Id Subject { value } StartDateTime { value } Location { value } WhatId { value } } } } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { closedAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { eq: { literal: THIS_WEEK } } }, groupBy: { IsWon: { group: true } }) { edges { node { aggregate { IsWon { value } Id { count { value } } Amount { sum { value } } } } } } newAgg: Opportunity(scope: MINE, where: { CreatedDate: { eq: { literal: THIS_WEEK } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } } touchedAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, LastModifiedDate: { eq: { literal: THIS_WEEK } } }, groupBy: { StageName: { group: true } }) { edges { node { aggregate { StageName { value } Id { count { value } } Amount { sum { value } } } } } } closingAgg: Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { eq: { literal: NEXT_WEEK } } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } } meetingsThisWeekAgg: Event(scope: MINE, where: { ActivityDate: { eq: { literal: THIS_WEEK } } }) { edges { node { aggregate { Id { count { value } } } } } } meetingsNextWeekAgg: Event(scope: MINE, where: { ActivityDate: { eq: { literal: NEXT_WEEK } } }) { edges { node { aggregate { Id { count { value } } } } } } } } }\"}" })
```

**Team scope** → swap every `scope: MINE` above for `OwnerId: { in: [\"<TEAM_USER_IDS>\"] }`.

**Aggregate read: the second dispatch above, paired root-for-root with the `query {}` detail (two dispatches, not twelve).** The six first:50 `query {}` roots are bounded example rows, not the count/$ source — Net $, won/lost, new, touched (by stage), and closing-next-week counts **and amounts** come from the paired `aggregate {}` roots instead: `closedAgg` (grouped by `IsWon`), `newAgg`, `touchedAgg` (grouped by `StageName`), `closingAgg`, `meetingsThisWeekAgg`, `meetingsNextWeekAgg`. The team-scope swap above (`scope: MINE` → `OwnerId: { in: [...] }`) applies to the `aggregate {}` roots too.

**Grouping fallback — only if the aggregate read errors.** `closedAgg` groups on `IsWon` and `touchedAgg` on `StageName`; grouping a boolean/picklist throws `DataFetchingException` in some orgs. If the query errors on either grouped root, re-fire just that total as a SOQL `GROUP BY` (own scope shown; team scope → `OwnerId IN (<TEAM_USER_IDS>)`), which groups cleanly:

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT IsWon, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '<CURRENT_USER_ID>' AND IsClosed = true AND CloseDate = THIS_WEEK GROUP BY IsWon" })
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '<CURRENT_USER_ID>' AND IsClosed = false AND LastModifiedDate = THIS_WEEK GROUP BY StageName" })
```

**If the aggregate request returns no usable `data`**, don't stop at the two SOQL totals. A grouped root's `DataFetchingException` can surface as top-level `errors` with `data` null or absent, which takes the other four aggregate roots down with it. The detail read is a separate dispatch, so its rows are unaffected. Re-fire the aggregate request with `closedAgg` and `touchedAgg` removed, keeping the four non-grouped roots (`newAgg`, `closingAgg`, `meetingsThisWeekAgg`, `meetingsNextWeekAgg`). Then take the closed-by-`IsWon` and touched-by-`StageName` totals from the two SOQL `GROUP BY` calls above. That recovers all six totals without the roots that trigger the exception.

If an aggregate root's `count` exceeds 50, label its paired detail root's rows "Top 50 of `<count>`" in step 3 — never derive the count/$ from the capped detail rows themselves. If an aggregate root errors (and the grouping fallback above doesn't apply or also fails), mark that total unavailable and avoid complete-population wording — do **not** fall back to summing/counting the capped rows.

**In the SAME turn**, fire (independent, don't wait on the read above):
- **email** — customer-domain threads touched this week (count + top senders).
- **docs/Slack** — if available, anything noteworthy this week per account. Use whatever connector tools are present; skip silently if none.

## 3. Assemble + flag (record only; reconcile totals; invent nothing)

- **Closed** — won/lost counts and Net $ from the `closedAgg` root (`count`/`sum` per `IsWon` branch; Net = the won branch's `sum` − nothing, lost isn't subtracted, just reported). Detail rows (✅ won / ❌ lost, with loss reason if an `__c` field surfaced it) from `closedThisWeek` — label "Top 50 of `<count>`" if the won+lost total exceeds 50.
- **Moved** — per-stage counts and $ from the `touchedAgg` root, grouped by `StageName` (`count`/`sum` per stage; total = Σ`count`). Detail: open opps modified this week, grouped by current stage, from `touchedThisWeek` (label "Top 50 of `<count>`" if it exceeds 50). **No `OpportunityHistory` = no from→to transition** — report "active this week, now at [Stage]," never fabricate a stage-change arrow.
- **New** — count and $ from the `newAgg` root (`count`/`sum`). Detail: account, amount, starting stage, from `newThisWeek` (same cap label).
- **Activity** — meeting count from the `meetingsThisWeekAgg` root's `count` (eyeball `meetingsThisWeek` Subject/Location for internal-only noise, e.g. standups, and don't count those as customer activity — but the aggregate itself still reflects the raw total), plus the email thread count from evidence.
- **Monday** — meeting count from the `meetingsNextWeekAgg` root's `count`, detail from `meetingsNextWeek` (time, subject, account if `WhatId` resolves); closing-next-week count and $ from the `closingAgg` root (`count`/`sum`), detail from `closingNextWeek` opps; plus any `NextStep` text already in hand that names a date next week (scan, don't re-query).

**Grounded widget mode — Quick/Kiro adaptation:** Build each activity series only from dated returned rows: Meetings from `meetingsThisWeek`, and Calls or Emails only from available connectors that returned dated selected-week evidence. Omit an unavailable series instead of filling it with zero; when detail count `R` differs from its matching aggregate count `C`, label that series as returned `R of C` rather than complete. Remove only the `tile/waterfall` block unless an attributable prior baseline and direct evidence for every displayed Won, New pipeline, Slipped, and Lost delta are available; missing waterfall evidence is not a text-fallback condition, so call `display_widget` with the remaining header, chart, grid, callout, and both buttons. Render each open `touchedThisWeek` row as `status: {"value":"Active","badgeVariant":"info"}`, `event: {"value":"Active this week","badgeVariant":"info"}`, and note `Now at <current Stage>`; never label it Slipped, Close moved, or from→to without history. A returned count of zero may be shown as zero, but a null/unavailable sum remains omitted rather than becoming `$0`.

## 4. Output — widget FIRST (the rendered UI is the default)

Call `display_widget` now with the data you collected. Do not write markdown first — call immediately. Only fall back to markdown if the tool is unavailable.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below. Call `display_widget` in **dynamic** mode with it. It is a skeleton: replace every `{{token}}` placeholder with a fully-resolved literal computed from the week's data — this echo path does no expression compilation, so no `{!…}` bindings.

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
                  "name": "calendar",
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
              "width": "md"
            },
            "children": [
              {
                "definition": "tile/chart",
                "attributes": {
                  "chartType": "column",
                  "caption": "{{activityCaption}}",
                  "categories": "{{activityCategories}}",
                  "series": "{{activitySeries}}",
                  "valueFormat": "number",
                  "showLegend": true
                }
              },
              {
                "definition": "tile/waterfall",
                "attributes": {
                  "caption": "{{waterfallCaption}}",
                  "valueFormat": "currency",
                  "size": "lg",
                  "start": "{{waterfallStart}}",
                  "steps": "{{waterfallSteps}}",
                  "end": "{{waterfallEnd}}"
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
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "deal",
                  "header": "Deal",
                  "type": "text"
                },
                {
                  "key": "amount",
                  "header": "Amount",
                  "type": "currency",
                  "align": "right"
                },
                {
                  "key": "event",
                  "header": "What happened",
                  "type": "badge"
                },
                {
                  "key": "note",
                  "header": "Note",
                  "type": "text"
                }
              ],
              "rows": "{{dealRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "success",
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
                      "label": "{{button1Label}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{button1Content}}"
                            }
                          }
                        ]
                      }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{button2Label}}",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{button2Content}}"
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

What each block shows, from data you already have:

- **Header** — an icon (calendar), page-title text (`{{title}}`, e.g. "Weekly wrap — week of Jul 20"), and a one-line caption subhead (`{{subtitle}}`) summarizing closed $, won/lost counts, pipeline added, and activity count, with a separator.
- **Two graphs in a wrapped row**:
  - **Column chart** — "Daily activity — calls, emails, and meetings" (`{{activityCaption}}`): `{{activityCategories}}` (weekdays), `{{activitySeries}}` (3 series: Calls, Emails, Meetings with daily counts), `valueFormat:"number"`, with legend.
  - **Waterfall** — "How commit moved this week" (`{{waterfallCaption}}`): `{{waterfallStart}}` (Last Mon value), `{{waterfallSteps}}` (Won/New pipe/Slipped out/Lost deltas), `{{waterfallEnd}}` (This Mon), `valueFormat:"currency"`, size lg.
- **Datagrid** (`{{dealRows}}`) — "This week's closed and moved deals" (`{{datagridCaption}}`). Columns: Deal (text), Amount (currency, right-aligned), What happened (badge), Note (text). Every row carries a leading `status` object (`{value,badgeVariant}` — value Won/Lost/Slipped, badgeVariant success/error/warning); the leading Status column reads each row's `status`.
- **One synthesis callout** (`variant:"success"`) — `{{calloutTitle}}` (the week's single most important read) and `{{calloutDescription}}`. It carries two real buttons: "Draft Slack post" (`{{button1Label}}` / `{{button1Content}}`, `action/sendMessage`) and "Prep Monday plan" (`{{button2Label}}` / `{{button2Content}}`, `action/sendMessage`).

**Hydration rules:**
1. Start from the embedded template above — a valid-JSON widget-definition envelope whose leaf values carry `{{token}}` placeholders.
2. Resolve every `{{token}}`. A value that is **only** a `{{token}}` (chart `categories`/`series`, waterfall `start`/`steps`/`end`, datagrid `rows`) becomes the resolved **typed** literal — numbers stay numbers, arrays stay arrays. A `{{token}}` **inside** a larger string is interpolated as text.
3. `{{activitySeries}}` is an array of series objects — each with `name` (string) and `data` (array of numbers). `{{waterfallSteps}}` is an array of step objects — each with `label` (string) and `delta` (number). `{{dealRows}}` is an array of deal objects — each with `deal` (plain string — format as the account or opportunity name (e.g. "Vertex Manufacturing"); names must be plain strings, not objects: use `Account.Name.value` from the SF response), `amount` (number), `event` (`{ value, badgeVariant }`), `note` (text), and `status` (`{value,badgeVariant}` — value Won/Lost/Slipped, badgeVariant success/error/warning).
4. The result is hydrated widget definition (no `{{…}}` placeholders remain). Then call:

```
display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated renderer.json> })
```

**Binding rules:**
- Resolve every `{{token}}` to a literal before calling — numbers stay numbers (`{{waterfallStart}}.value`, each step's `delta`, each row's `amount`), arrays stay arrays (`{{activityCategories}}`, `{{activitySeries}}`, `{{waterfallSteps}}`, `{{dealRows}}`), strings stay strings.
- Chart series: each object has `name` (string) and `data` (array of numbers, one per category). Categories are weekday labels (Mon-Fri).
- Waterfall: `{{waterfallStart}}` is `{ label, value }`, `{{waterfallSteps}}` is an array of `{ label, delta }` (deltas can be positive or negative), `{{waterfallEnd}}` is `{ label }` (final value is computed).
- Datagrid rows: one per deal that closed/moved this week. `amount` is a raw number. The What happened badge (`event.badgeVariant`) reflects outcome — `"success"` (Won), `"error"` (Lost), `"warning"` (Slipped). `status` fills the leading Status column. Rank rows by outcome (Won first, Lost second, Slipped last).
- Callout buttons: both are `action/sendMessage` with first-person `content` prompts (`{{button1Content}}`, `{{button2Content}}`, e.g. "Draft a Slack post for…"). Never leave a button decorative.
- No fabricated content — quote blank fields as blank rather than inventing them; drop deals you have no data for.


## 5. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Week of [Mon date] - [Scope]

## Closed
- ✅ **[Account]** $[X] WON
- ❌ **[Account]** $[X] lost - [reason if in SFDC]
**Net: $[won total]**

## Moved (active this week, no history = no from→to)
- **[Account]** now at [Stage] ($[X])
...

## New
- **[Account]** $[X] created at [Stage]
...

## Activity
[N] customer meetings, [N] customer email threads

## Monday
- [Time] [Meeting] - [Account if resolved]
- Closing next week: [Account] $[X], [Account] $[X]
- NextStep due: [list]
```

If "post to Slack" - format the above for Slack (bold via asterisks, bullets) and create a draft to the team channel from config. User reviews and posts.
