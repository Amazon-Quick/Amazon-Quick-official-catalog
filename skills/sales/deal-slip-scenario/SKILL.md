---
name: deal-slip-scenario
display_name: Deal Slip Scenario
description: "Model the impact of a deal slipping, shrinking or being lost from Salesforce pipeline and forecast data plus an available quota, including the gap and substitutes. Use to test downside scenarios, plan a backfill or judge whether the number still holds."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:6decd00c7eda22c6ddaef3c0e960538f4b7f7bee515555070ec2dc9434499a62"
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

# Deal Slip Scenario


# Rules:


# Deal Slip Scenario

Ground → read baseline → resolve exactly one scenario deal → apply scenario → output. The open baseline read is also the resolver. **Do not run a separate per-Opportunity lookup** — it already carries every field this workflow may use.

## 1. Ground (hardcoded — Opportunity only)

Ground **Opportunity** (for pipeline fields). Always exists. One call:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

**If it overflows**, the result auto-persists to a temp file **outside the bash mount** — don't shell to it (`cat`/`python3`/`ls` will fail, it's not on that mount). Read it back with the Read tool only, and go straight to that — don't retry bash first. If the Read tool can't load it either, skip custom-field grounding and proceed with standard fields only; don't keep retrying.

From the result, select relevant Opportunity `__c` fields by API name and label (risk, timing, health, etc.) and take their `{ value }`. The `Account` and `Owner` relationships below are standard and hardcoded.

## 2. Read baseline (templated, one turn)

Fire these as tool calls in **one turn** (independent). Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields (risk, health, timing signals, etc.).

**Date filters take a `DateInput` object, never a bare string** (`gte: \"2026-07-01\"` fails `WrongType … must be an object type`). For the current-quarter bounds below, use the exact-date form on both ends: `{ value: \"YYYY-MM-DD\" }`. Multiple ops on one field (`gte`/`lte`) AND automatically — no `and: [...]` wrapper needed around them.

**Open opps this quarter (ordered by forecast category then amount):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 200) { pageInfo { hasNextPage } totalCount edges { node { Id Name { value } StageName { value displayValue } ForecastCategoryName { value } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } } }\"}" })
```

**Forecast category — local correction:** The read returns `ForecastCategoryName` (Pipeline, Best Case, Commit, Closed, Omitted), the category reps see. `ForecastCategory` returns internal values, such as `Forecast` for Commit, that are not labels.

**Closed-won this period (for booked baseline):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsWon: { eq: true }, CloseDate: { gte: { value: \\\"<Q_START>\\\" }, lte: { value: \\\"<Q_END>\\\" } } }, first: 200) { pageInfo { hasNextPage } totalCount edges { node { Id Name { value } Amount { value } Account { Name { value } } } } } } } }\"}" })
```

`scope: MINE` = current user (default), with no User lookup. For a named rep whose Id is already disambiguated, remove `scope: MINE` and add `OwnerId: { eq: "<USER_ID>" }` inside `where`; never probe users to guess.

### 2a. Resolve exactly one scenario Opportunity (hard gate)

Use the returned open-opportunity connection as the resolver. Do this before showing baseline values, asking for quota, applying the scenario, evaluating substitutes, or producing a widget or fallback.

- If either baseline connection has `pageInfo.hasNextPage = true`, the totals are incomplete. State which result is limited to its first 200 rows, ask for a narrower period or authorized scope, and stop.
- If the request supplies a 15- or 18-character Opportunity Id with prefix `006`, select the deal only when exactly one returned open row has that exact `Id`. With no exact match, say that the supplied deal was not returned in the current scope and quarter, ask the user to check the Id, scope, or period, and stop. Never issue a separate Id lookup or substitute another deal.
- Otherwise, if the request supplies a complete Opportunity name, select it only when exactly one returned row has that exact `Name.value`. If several rows have that name, use returned `Account.Name.value` only as a discriminator and ask the user to choose; do not pick by amount, order, recency, stage, or probability.
- With no supplied deal identity, auto-select only when the complete open result contains exactly one row. Zero open rows take the empty-`MINE` scope branch. For two through ten rows, show only each returned `Name.value`, `Account.Name.value` when present, and Id-backed Opportunity link, then ask one question to choose. Above ten rows, state `totalCount` and ask for the exact Opportunity name or Id without presenting a partial candidate list.

Every unresolved branch stops after its one bounded question. Do not show amounts, stages, dates, baseline totals, scenario conclusions, substitute claims, or a quota question in the same turn. On the user's next turn, map their choice to exactly one Id from the frozen returned candidate set and continue from the existing baseline rows without another Salesforce read.

A zero-row closed-won result is a valid booked baseline of zero; it does not trigger the empty-`MINE` scope branch.

Compute baseline only after the hard gate passes:
- **Booked** = Σ closed-won `Amount.value`
- **Commit total** = Booked + Σ open opps where `ForecastCategoryName.value = "Commit"`
- **Best case total** = Commit total + Σ `ForecastCategoryName.value = "Best Case"`
- **Open pipeline total** = Σ all open opps `Amount.value`
- **Coverage ratio** = Open pipeline total ÷ (Quota − Booked)

If quota isn't in org data, ask once after one scenario Opportunity is resolved, then stop before steps 3–6. Preserve the selected Id and baseline rows; when the user supplies quota, resume without another Salesforce read. Do not show scenario math, substitute claims, a widget, or fallback before quota is available.

## 3. Apply scenario

Remove or restate the named deal(s):
- **Slip:** subtract from this period's buckets; note it lands next period
- **Reduced amount:** replace Amount with user's revised figure
- **Lost:** subtract entirely

Recompute commit total, gap to quota, coverage ratio.

## 4. Find substitute pipeline

What in the existing open pipeline could realistically backfill this period:
- Best Case deals with recent activity (`LastActivityDate` within 14 days) and `CloseDate` inside period
- Deals one stage away from commit where timing looks achievable
- Be honest about timing: deal needing 6 weeks doesn't rescue quarter with 3 weeks left

## 5. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Slip Scenario: [Deal] - [slips / cut to $X / lost]

## Before vs After
| | Baseline | Scenario | Δ |
|---|---|---|---|
| Booked | $[X] | $[X] | - |
| Commit total | $[X] | $[X] | -$[X] |
| Gap to quota | $[X] | $[X] | +$[X] |
| Coverage ratio | [X.X]x | [X.X]x | |

## Verdict
[One sentence: still on plan / at risk / not recoverable this period without new pipeline]

## Substitute pipeline (what could backfill)
- **[Account]** $[X] - [bucket] - [why it's plausible this period, what has to happen, by when]
- ...
- Realistic backfill total: $[X] of the $[X] gap

## What to do this week
1. [Highest-leverage action to either save the slipping deal or accelerate a substitute - specific]
2. ...

## If it slips anyway
- Next-period commit starts at $[X] including this deal - [note any knock-on risk, e.g. stacked renewals or capacity]
```


## 6. Dashboard widget (data-viz tiles)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

**Tokens:**
- `{{title}}`, `{{headerStatus}}`, `{{subtitle}}` — scenario header (derived from deal names, commit vs quota)
- `{{meterLabel}}`, `{{meterValue}}`, `{{meterMax}}`, `{{meterTarget}}`, `{{meterValueLabel}}`, `{{meterTargetLabel}}`, `{{meterStatus}}`, `{{meterBands}}` — meter showing commit vs quota if all slip (bands = array of `{ from, to, variant, label }` for Miss/Close/Make zones)
- `{{waterfallCaption}}`, `{{waterfallStart}}` (object `{ label, value }`), `{{waterfallSteps}}` (array of `{ label, delta }` with negative deltas for slips), `{{waterfallEnd}}` (object `{ label }`) — waterfall from today's commit to downside
- `{{datagridCaption}}`, `{{datagridRows}}` — at-risk deals, each row: `{ deal, amount, close, prob, block, status:{value,badgeVariant}}` (high-risk: `status:{value:"High",badgeVariant:"error"}`; medium: `status:{value:"Medium",badgeVariant:"warning"}`)
- `{{calloutTitle}}`, `{{calloutDescription}}`, `{{primaryButtonLabel}}`, `{{primaryButtonContent}}`, `{{secondaryButtonLabel}}`, `{{secondaryButtonContent}}` — synthesis callout with action buttons
- `{{meterMax}}` > `{{meterTarget}}` so "Make" band has width

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): The widget template is embedded below — a widget-definition envelope whose leaf values carry {{token}} placeholders. Resolve every {{token}} to a literal (no {{…}}/{!…} left), then call `display_widget({ resourceType: \"dynamic\", widgetDefinition: <hydrated> })` once. A value that is *only* a {{token}} becomes the typed literal — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string is interpolated as text.\n- `{{title}}`, `{{headerStatus}}`, `{{subtitle}}` — scenario header (derived from deal names, commit vs quota)\n- `{{meterLabel}}`, `{{meterValue}}`, `{{meterMax}}`, `{{meterTarget}}`, `{{meterValueLabel}}`, `{{meterTargetLabel}}`, `{{meterStatus}}`, `{{meterBands}}` — meter showing commit vs quota if all slip (bands = array of `{ from, to, variant, label }` for Miss/Close/Make zones)\n- `{{waterfallCaption}}`, `{{waterfallStart}}` (object `{ label, value }`), `{{waterfallSteps}}` (array of `{ label, delta }` with negative deltas for slips), `{{waterfallEnd}}` (object `{ label }`) — waterfall from today's commit to downside\n- `{{datagridCaption}}`, `{{datagridRows}}` — at-risk deals, each row: `{ deal, amount, close, prob, block, status:{value,badgeVariant}}` (high-risk: `status:{value:\"High\",badgeVariant:\"error\"}`; medium: `status:{value:\"Medium\",badgeVariant:\"warning\"}`)\n- `{{calloutTitle}}`, `{{calloutDescription}}`, `{{primaryButtonLabel}}`, `{{primaryButtonContent}}`, `{{secondaryButtonLabel}}`, `{{secondaryButtonContent}}` — synthesis callout with action buttons\n- `{{meterMax}}` > `{{meterTarget}}` so \"Make\" band has width\n- [ ] Every `{{token}}` replaced, no `{!…}` expressions",
  "props": {
    "title": {
      "description": "Header title — the slip scenario (derived from deal names, commit vs quota).",
      "type": "string",
      "example": "Slip scenario — what if the top 3 push?"
    },
    "headerStatus": {
      "description": "Header status badge.",
      "type": "string",
      "example": "WOULD MISS"
    },
    "subtitle": {
      "description": "Scenario subhead — commit vs quota if at-risk deals slip.",
      "type": "string",
      "example": "Commit $12.6M vs $13.0M quota · modeling the 3 deals most likely to slip"
    },
    "meterLabel": {
      "description": "Label for the commit-vs-quota meter.",
      "type": "string",
      "example": "Commit vs quota if all three slip"
    },
    "meterValue": {
      "description": "Commit if all at-risk deals slip — the meter's current value.",
      "type": "number",
      "example": 9.3
    },
    "meterMax": {
      "description": "The meter's max (set > target so the \"Make\" band has width).",
      "type": "number",
      "example": 13
    },
    "meterTarget": {
      "description": "Quota target marker on the meter.",
      "type": "number",
      "example": 13
    },
    "meterValueLabel": {
      "description": "Display string for the downside commit.",
      "type": "string",
      "example": "$9.3M — 72% of quota"
    },
    "meterTargetLabel": {
      "description": "Display string for the quota target.",
      "type": "string",
      "example": "$13.0M quota"
    },
    "meterStatus": {
      "description": "Short read shown on the meter (Miss / Close / Make).",
      "type": "string",
      "example": "would miss by $3.7M"
    },
    "meterBands": {
      "description": "Color bands for the meter, in order covering 0→max (Miss / Close / Make zones).",
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
          "to": 11.05,
          "variant": "error",
          "label": "Miss"
        },
        {
          "from": 11.05,
          "to": 13,
          "variant": "warning",
          "label": "Close"
        },
        {
          "from": 13,
          "to": 13,
          "variant": "success",
          "label": "Make"
        }
      ]
    },
    "waterfallCaption": {
      "description": "Caption for the commit-to-downside waterfall.",
      "type": "string",
      "example": "From today's commit to the downside case, deal by deal"
    },
    "waterfallStart": {
      "description": "Waterfall start bar — object { label, value } (today's commit).",
      "type": "object",
      "example": {
        "label": "Commit today",
        "value": 12.6
      }
    },
    "waterfallSteps": {
      "description": "Waterfall steps — one per slipping deal, with negative deltas.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "label": {
            "description": "Step label (the slipping deal).",
            "type": "string"
          },
          "delta": {
            "description": "Amount change for this step (negative for a slip).",
            "type": "number"
          }
        }
      },
      "example": [
        {
          "label": "Cobalt slips",
          "delta": -1.8
        },
        {
          "label": "Meridian slips",
          "delta": -1
        },
        {
          "label": "Alto slips",
          "delta": -0.5
        }
      ]
    },
    "waterfallEnd": {
      "description": "Waterfall end bar — object { label } (downside commit).",
      "type": "object",
      "example": {
        "label": "Downside"
      }
    },
    "datagridCaption": {
      "description": "Caption for the at-risk deals datagrid.",
      "type": "string",
      "example": "The three at-risk deals and what holds them"
    },
    "datagridRows": {
      "description": "At-risk deals that could slip — one row per deal. Empty array → the datagrid is omitted.",
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
          "deal": {
            "description": "Deal name.",
            "type": "string"
          },
          "amount": {
            "description": "Deal amount (number).",
            "type": "number"
          },
          "close": {
            "description": "Close date, ISO YYYY-MM-DD.",
            "type": "string"
          },
          "prob": {
            "description": "Win probability (number).",
            "type": "number"
          },
          "block": {
            "description": "The blocker putting the deal at risk.",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "High",
            "badgeVariant": "error"
          },
          "deal": "Cobalt Robotics renewal",
          "amount": 1800000,
          "close": "2026-07-30",
          "prob": 70,
          "block": "No dated next step, legal not started"
        },
        {
          "status": {
            "value": "Medium",
            "badgeVariant": "warning"
          },
          "deal": "Meridian Health platform",
          "amount": 1000000,
          "close": "2026-08-15",
          "prob": 55,
          "block": "Exec sponsor unconfirmed"
        },
        {
          "status": {
            "value": "Medium",
            "badgeVariant": "warning"
          },
          "deal": "Alto Financial expansion",
          "amount": 500000,
          "close": "2026-08-05",
          "prob": 45,
          "block": "Waiting on security review"
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the scenario's key risk.",
      "type": "string",
      "example": "One save flips the quarter"
    },
    "calloutDescription": {
      "description": "Synthesis callout body — the risk and the move.",
      "type": "string",
      "example": "Holding Cobalt alone keeps commit at $11.1M — inside striking distance. Pull the legal review forward this week and lock a dated next step; it's the single highest-leverage move on the board."
    },
    "primaryButtonLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft the plan"
    },
    "primaryButtonContent": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft a plan to pull the Cobalt legal review forward and lock a dated next step this week."
    },
    "secondaryButtonLabel": {
      "description": "Secondary button label.",
      "type": "string",
      "example": "List at-risk deals"
    },
    "secondaryButtonContent": {
      "description": "Content/target for the secondary button.",
      "type": "string",
      "example": "List the three at-risk opportunities in Salesforce and summarize their current states."
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
                      "name": "alert-triangle",
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
                  "variant": "error"
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
                  "size": "lg",
                  "bands": "{{meterBands}}"
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
                  "key": "deal",
                  "header": "Deal",
                  "type": "text"
                },
                {
                  "key": "amount",
                  "header": "Commit",
                  "type": "currency",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "close",
                  "header": "Close",
                  "type": "date"
                },
                {
                  "key": "prob",
                  "header": "Slip risk",
                  "type": "databar",
                  "target": 100
                },
                {
                  "key": "block",
                  "header": "What's blocking",
                  "type": "text"
                }
              ],
              "rows": "{{datagridRows}}"
            }
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
                      "label": "{{primaryButtonLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{primaryButtonContent}}"
                            }
                          }
                        ]
                      }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{secondaryButtonLabel}}",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{secondaryButtonContent}}"
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

**Self-verification:**
- [ ] Numeric attributes are numbers, not strings
- [ ] Meter `max` > `target`, "Make" band spans `[quota, max]`
- [ ] Risky rows carry a leading `status` object; low-risk rows carry neither
- [ ] Text produced only when `display_widget` is unavailable (terminal fallback)
