---
name: win-loss-review
display_name: Win Loss Review
description: "Build a win-loss analysis from closed Salesforce opportunities, stage history, call transcripts and email, showing win rates, loss stages, objections and deal patterns. Use to explain wins and losses, compare segments or identify coaching and process changes. Also load as conditional support for handle-objection prompts such as a buyer saying we're too expensive; do not run history reads until handle-objection's evidence gate permits them."
author: Salesforce
roles:
  - role/sales
icon: assets/salesforce.svg
checksum: "sha256:6d032a9d06c9da7d649c816c33ca4cdabc74a815cfec974527832153122d8d71"
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
- **Empty `MINE` scope → fail fast, then ask for a bounded scope.** If a `scope: MINE` read returns zero rows, stop, tell the user plainly that their own records came back empty, and ask whether they want a named rep or an explicit team roster before re-running. Never invent records, use `scope: EVERYTHING`, run without an owner filter, or silently widen to org-wide.
- **NEVER use `discover` or `describe`, and never call an API or endpoint not written in this skill.** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->
# Rules:

- Reconcile headline totals with the detail rows.

# Win-Loss Review

Ground → resolve scope → (read + evidence, ONE turn) → find patterns → output. Look across recently closed opportunities only within the selected owner scope for patterns a leader can act on.

## Inputs

- **Scope:** the running user's own book for an unqualified `for me`, `my`, or no-scope request (default); an explicitly requested team with a grounded roster; or one specific named rep
- **Period:** last quarter (default) or specified range
- **Focus:** all / wins only / losses only

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's loss-reason `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } childRelationships { childObjectApiName relationshipName } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. Note the scalar `__c` field(s) that carry a loss-reason/lost-reason category — that's `<OPP_CUSTOM>` below. If none is grounded, omit it and rely on transcript/email evidence for loss reasons instead.

## 2. Read (fill from step 1)

Compute explicit `gte`/`lte` date-literal boundaries for the review period from today's date — do not use a relative literal like `LAST_N_DAYS:90`, because it silently drifts the window as today moves.

Select exactly one owner scope before issuing the closed-deal read:

- **Current user (default):** For an unqualified `for me`, `my`, or no-scope request, use the literal closed-deal request below unchanged with `scope: MINE`.
- **Explicit team:** Proceed only when an explicitly grounded, nonempty roster supplies the active User Ids for the requested team. Use `OwnerId: { in: [<TEAM_USER_IDS>] }`. If no such roster is available, ask for the team roster and do not issue the closed-deal read. Never use `scope: EVERYTHING` or an unfiltered org-wide query.
- **Named rep:** Resolve the user-supplied name against active Users with this literal standard-field request. Replace `%REP_NAME%` with a GraphQL-string-escaped contains pattern built from the supplied name, including the surrounding `%` wildcards; do not alter the request shape.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { and: [{ IsActive: { eq: true } }, { Name: { like: \\\"%REP_NAME%\\\" } }] }, first: 2, orderBy: { Name: { order: ASC } }) { edges { node { Id Name { value } IsActive { value } } } } } } }\"}" })
```

Apply the resolver result before the review:

- **0 rows:** Ask for a different or more complete rep name; do not issue the closed-deal read.
- **1 row:** Select that active User's returned `Id` and continue.
- **2 rows:** The query is capped at two, so this means several matches. Ask the user to choose one returned `Name`; do not issue the closed-deal read until exactly one returned active User is selected.

For a named rep, use `OwnerId: { eq: "<USER_ID>" }`. For either non-default branch, transform only the literal closed-deal request below: remove `scope: MINE, `, insert the selected `OwnerId` predicate immediately after `where: { `, and preserve the closed/date predicates, ordering, fields, history child, and row cap unchanged. The transformed request must contain exactly one owner predicate and no `scope` argument.

One call pulls every closed opportunity in the window — with `Account` spanned for industry/size AND the stage-history child nested (no separate round-trip). **Loss death-stage:** a lost opp's closing `StageName` is just "Closed Lost", so "where losses die" must come from the stage-history child — the last **non-closed** `StageName` before close. Nest `<HISTORY_CHILD>` = the OpportunityHistory child's exact `relationshipName` from Step 1 grounding (commonly `OpportunityHistories`); keep its `first:` small (history rows are tiny, but the child rides on up to 200 parents).

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: true }, CloseDate: { gte: { value: \\\"%START%\\\" }, lte: { value: \\\"%END%\\\" } } }, first: 200, orderBy: { Amount: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } CreatedDate { value } LeadSource { value } Type { value } IsWon { value } <OPP_CUSTOM> Account { Name { value } Industry { value } NumberOfEmployees { value } } Owner { Name { value } } <HISTORY_CHILD>(first: 15, orderBy: { CreatedDate: { order: DESC } }) { edges { node { StageName { value } CreatedDate { value } } } } } } } } } }\"}" })
```

Empty `edges` → no closed deals in this window/scope; say so plainly, skip the rest. `first: 200` is a bounded sample; if it truncates on a very high-volume team, note the cap rather than imply full coverage. **If the history child is empty/unavailable**, fall back to the record's final `StageName` for the death-stage line and omit the median-days-in-stage column — don't fire a separate history round-trip.

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**After the owner scope is ready, issue the closed-deal read from step 2 and all of step 2b as tool calls in a single turn — do not wait for the closed-deal read to return before firing the searches.** They key on the account/rep names from the request, not the Salesforce result:
- **docs**: call transcripts for the largest wins and losses (will narrow to the top 5 each once step 2 returns names, but a first broad pass can start now on account names already known from the request)
- **email**: late-stage threads on the same accounts → stated objections, loss reasons

Use whatever doc/email tools are available; skip silently if none are present (SFDC-only is fine). Cite source + date for anything you use.

## 3. Find patterns (record only; reconcile totals; invent nothing)

- **Win rate** overall and by: rep, lead source, deal size band, industry, type (new vs expansion)
- **Loss stage distribution:** where do losses die — the last **non-closed** `StageName` in each lost opp's history child (NOT "Closed Lost"). Most at Discovery? at Proposal? (Fall back to final `StageName` only if history is unavailable.)
- **Median days in stage:** from consecutive history-row `CreatedDate` deltas (omit if no history child).
- **Cycle length:** median days (`CloseDate` − `CreatedDate`) for wins vs losses
- **Size:** median Amount for wins vs losses
- **Qualitative:** for the 5 largest losses and 5 largest wins (by Amount, from step 2), pull the evidence gathered in 2b — stated loss reasons (competitor, budget, timing, no decision), objections in losses but not wins, what wins had in common. Cite specifics: "[Account] - lost at Proposal, transcript on [date] shows pricing objection with no follow-up."

**Grounded output mode — Quick/Kiro adaptation:** Scope-consistency gate: use the owner scope selected in step 2 for the closed-deal read, calculations, evidence selection, widget labels, and text fallback; never mix, widen, or relabel scopes. Keep every full source block when its inputs are grounded. Otherwise: omit the loss-reason donut unless every displayed slice has attributable reason evidence and reconciles to the loss count; omit the deal-size chart unless the user or team supplies deterministic band boundaries; omit death-stage/stage-duration when history has no non-closed stage; omit cycle duration when any used CreatedDate/CloseDate order is invalid; and never turn an unqueried reason, competitor, or history value into `Not captured`, `Closed Lost`, or another value. Reduce largest-loss rows to the grounded columns among exact Name, raw Amount, and Lost status when dependent fields are unavailable. Remove only the Report button when no Report Id/URL is grounded, retain the independent sendMessage action and callout, and add one `action/openLink` button labeled `Open <exact Opportunity.Name.value>` for every displayed loss using its returned Id. Missing dependent blocks are not a text-fallback condition: call `display_widget` with the remaining grounded widget, and keep the richer source shape whenever qualifying evidence exists.

## 4. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

Layout note: the loss-reason donut runs with `showLegend:false` and sits in a row beside a text column (`donutAsideTitle` + `donutAside`); the win-rate column chart is full-width, preceded by a caption pair (`chartAsideTitle` + `chartAside`). A column chart must be full-width to keep its axis, value labels, and bar height legible — do not put it in a shared row.

Tokens: `title` (page-title text, e.g. "Win / loss review — last 2 quarters") · `subtitle` (one-line caption with closed count, win rate, won/lost $ totals) · `donutAsideTitle donutAside` (short title + one-sentence breakdown beside the loss-reason donut; because the legend is off, `donutAside` must name every slice with its count in prose — a colorblind reader relies on it) · `pieCaption pieSlices` (pie chart — `slices` is `[{label, value, role?}]`; top reason carries `role:"highlight"`) · `chartAsideTitle chartAside` (short title + one-sentence takeaway above the full-width win-rate chart; interpret the shape — e.g. the decline with deal size — rather than re-listing every band) · `chartCaption chartCategories chartSeries` (column chart — `categories` is size-band labels, `series` is an array with one object: `{name:"Win rate", data:[...numbers...]}` — these are win-RATE percentages, not deal counts) · `datagridCaption lossRows` (datagrid — `rows` is `[{name (plain string — format as the opportunity name (e.g. "Meridian Health platform"); names must be plain strings, not objects: use `Opportunity.Name.value` from the SF response), amount, stage:{value, badgeVariant}, reason, comp, status:{value:"Lost",badgeVariant:"error"}}]`, largest first; `amount` is a raw number; `comp` is competitor name or "—" for no-decision losses) · `calloutTitle calloutDescription button1Label button1Content reportUrl` (callout — primary button is `action/sendMessage` with a first-person `content` prompt; `reportUrl` is a Win/Loss report Lightning URL `https://<myDomain>/lightning/r/Report/<Id>/view`, opens new tab). Omit any block whose data you lack rather than passing empty arrays.

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
                  "name": "trending-up",
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
            "definition": "tile/row",
            "attributes": {
              "gap": "lg",
              "align": "center",
              "isWrapped": false
            },
            "children": [
              {
                "definition": "tile/column",
                "attributes": {
                  "width": "auto"
                },
                "children": [
                  {
                    "definition": "tile/piechart",
                    "attributes": {
                      "variant": "donut",
                      "caption": "{{pieCaption}}",
                      "valueFormat": "number",
                      "showLegend": false,
                      "slices": "{{pieSlices}}"
                    }
                  }
                ]
              },
              {
                "definition": "tile/column",
                "attributes": {
                  "gap": "sm",
                  "align": "start",
                  "width": "stretch"
                },
                "children": [
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{donutAsideTitle}}",
                      "variant": "section-title"
                    }
                  },
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{donutAside}}",
                      "variant": "body",
                      "color": "muted"
                    }
                  }
                ]
              }
            ]
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "{{chartAsideTitle}}",
              "variant": "section-title"
            }
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "{{chartAside}}",
              "variant": "body",
              "color": "muted"
            }
          },
          {
            "definition": "tile/chart",
            "attributes": {
              "chartType": "column",
              "caption": "{{chartCaption}}",
              "categories": "{{chartCategories}}",
              "series": "{{chartSeries}}",
              "valueFormat": "number",
              "showValues": true,
              "showLegend": false
            }
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{datagridCaption}}",
              "appearance": "striped",
              "size": "sm",
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
                  "key": "amount",
                  "header": "Amount",
                  "type": "currency",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "stage",
                  "header": "Died at",
                  "type": "badge"
                },
                {
                  "key": "reason",
                  "header": "Reason",
                  "type": "text"
                },
                {
                  "key": "comp",
                  "header": "Lost to",
                  "type": "text"
                }
              ],
              "rows": "{{lossRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "info",
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
                      "label": "View in Salesforce",
                      "iconName": "open-in-new",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/openLink",
                            "attributes": {
                              "url": "{{reportUrl}}"
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
# Win-Loss Review — <Scope> — <Period>
**Headline:** <the pattern that matters most, 2 sentences>

## Win Rate
| Cut | Win Rate | n |
|---|---|---|
| Overall | <pct>% | <N> |
| By rep / source / size band / industry | <pct>% | <N> |

## Where Losses Die
| Stage | % of losses | Median days in stage |
|---|---|---|
| <Stage> | <pct>% | <N>d |
(Stage = last non-closed stage from history; omit the median-days column if no history child.)

## Loss Reasons
| Reason | Count | Example |
|---|---|---|
| <Reason> | <N> | <Account>: <one-line evidence w/ date+source> |

## What Wins Have In Common
- <pattern> (<N of M> wins) …

## Largest Losses
- **<Account>** $<X> — died at <Stage> — <one-line evidence>

## Recommended Actions
1. Systemic — <process/enablement tied to the headline>
2. Coaching — <which rep, on what>
3. Data — <what to start capturing>
```
