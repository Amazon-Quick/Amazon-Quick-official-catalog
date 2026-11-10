---
name: forecast-narrative
display_name: Forecast Narrative
description: "Build a forecast-call brief from Salesforce opportunity aggregates, top-deal samples and field history, covering the number, bucket movement, risks and asks. Use to explain a rep or team's forecast; for a broader pipeline and coaching view, use team-pipeline."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:dbc3e3288d23feb81468f4509c7d2aea502b710eb17610872feddc148e69cea2"
id: "ski-adef666ba672442fa597ef9fe7216901"
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


# Forecast Narrative

Ground → resolve one exact period → aggregate the number + sample the deals (ONE turn) → narrative. Scope: my forecast (default), or a named rep/team. Period: an exact half-open Date interval, or current/next fiscal quarter only with grounded boundaries.

## 0. Resolve the forecast period (hard gate)

Use one frozen as-of instant, one IANA timezone, and explicit start-inclusive/end-exclusive fiscal boundaries from the user or trusted context. Treat `CloseDate` as a Salesforce Date.

- Exact interval `[<START_INCLUSIVE>, <END_EXCLUSIVE>)` → `%QSTART% = <START_INCLUSIVE>` and `%QEND_EXCLUSIVE% = <END_EXCLUSIVE>`.
- `this/current fiscal quarter` → select the supplied fiscal interval containing the frozen local as-of date.
- `next fiscal quarter` → select the supplied fiscal interval immediately after the containing quarter. With `as_of=2026-10-21T16:00:00Z`, `America/New_York`, current `[2026-10-01, 2027-01-01)`, and next `[2027-01-01, 2027-04-01)`, use the latter for `next quarter`.

If the as-of instant, timezone, requested exact boundary, or needed fiscal interval is unavailable or contradictory, ask for the missing value and stop before any Salesforce business read. Never assume calendar quarters, reuse the containing quarter for `next quarter`, pass the exclusive end through `lte`, or derive fiscal dates from general knowledge. Display the same start-inclusive/end-exclusive interval in the output.

## 1. Ground (hardcoded — Opportunity only)

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's ForecastCategory/StageName picklists + any custom forecast/override `__c` fields — use exact names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

## 2. AGGREGATE the number, SAMPLE the deals — ISSUE BOTH IN ONE TURN

**Don't compute the number from a `first: N` page.** A raw pull caps at its page (`first: 200` returns 200 rows, not the book) — summing that page silently under-reports the total on a large book, and the first page isn't the whole set. Salesforce aggregates the totals server-side; use that for the number, and pull only a small bounded sample for the per-deal commentary.

`scope: MINE` = running user's book (no user lookup). `%QSTART%`/`%QEND_EXCLUSIVE%` = the resolved period's first included Date and first excluded Date in `YYYY-MM-DD`. Use `gte` plus `lt` in every `CloseDate` predicate. Bound **both** ends of `CloseDate` — an open-ended `gte` pulls later-period deals into the number. **Named rep/team:** swap `scope: MINE` for `OwnerId: { eq: \"<UserId>\" }`; for a team rollup, add `Owner { Name { value } }` to the sample so each deal attributes to its rep.

**2a. The number — aggregate by ForecastCategory (accurate at any volume).** One row per forecast bucket: count + $ sum. This is "The Number" table and it reconciles by construction — no page cap, no client-side sum of a truncated page.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { aggregate { Opportunity(scope: MINE, where: { CloseDate: { gte: { value: \\\"%QSTART%\\\" }, lt: { value: \\\"%QEND_EXCLUSIVE%\\\" } } }, groupBy: { ForecastCategory: { group: true } }) { edges { node { aggregate { ForecastCategory { value } Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```
`ForecastCategory` maps to the buckets: **Closed** = Closed Won (in the bank), **Commit**, **Best Case**, **Pipeline**; **Omitted** = drop (closed-lost/omitted). Org doesn't populate `ForecastCategory` → swap `groupBy` to `StageName` and infer buckets from the stage map (ask once if unclear). **If the `aggregate` query errors** (some orgs throw `DataFetchingException` grouping a picklist) → don't re-fire the same shape; fall to the SOQL `GROUP BY` equivalent:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT ForecastCategory, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '%OWNERID%' AND CloseDate >= %QSTART% AND CloseDate < %QEND_EXCLUSIVE% GROUP BY ForecastCategory" })
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
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, CloseDate: { gte: { value: \\\"%QSTART%\\\" }, lt: { value: \\\"%QEND_EXCLUSIVE%\\\" } } }, orderBy: { Amount: { order: DESC } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } ForecastCategory { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } } } } } } }\"}" })
```

`InvalidSyntax` / "offending token `<EOF>`" → missing a closing `}`; add it and retry (once, with corrected text — never re-send identical text).

## 3. Bucket (in-prompt — no extra reads)

**The Number comes from 2a's aggregate** — count + $ per bucket (Closed Won / Commit / Best Case / Pipeline), whole-book and reconciled; drop the Omitted/closed-lost row. **Per-deal commentary comes from 2b's sample** — the top-by-Amount Commit and Best Case deals (the ones that matter for the call). Prefer `ForecastCategory`; else infer from `StageName` (never invent bucketing — infer from the org's stages or ask once). Say the per-deal lines are the top deals sampled, while the bucket totals are whole-book from the aggregate.

## 4. Changes + commentary

Prior snapshot pasted → diff it (up / slipped / added / lost). Without a snapshot, run field history only when the requested period is current or past and one exact DateTime interval plus owner scope are grounded. `OpportunityFieldHistory.CreatedDate` is a DateTime: derive `%HISTORY_START%` and `%HISTORY_END_EXCLUSIVE%` as independently offset UTC instants from the frozen timezone, and set `%HISTORY_SCOPE%` to the selected Opportunity owner predicate. For the running user this is `Opportunity.OwnerId = '<currentUser.Id>'`; named-rep/team branches must use only their resolved owner Ids. Never run an org-wide history query.

If the requested period starts after the frozen as-of instant, no in-period history can exist yet: skip the delta without calling history. If any history boundary or owner scope is unavailable, skip the delta rather than guessing. Otherwise issue this exact bounded read:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT OpportunityId, Field, OldValue, NewValue, CreatedDate FROM OpportunityFieldHistory WHERE CreatedDate >= %HISTORY_START% AND CreatedDate < %HISTORY_END_EXCLUSIVE% AND %HISTORY_SCOPE% AND Field IN ('StageName','Amount','CloseDate') ORDER BY CreatedDate DESC" })
```
Derive moved-up / slipped / added / lost from those rows. Per **Commit**/**Best Case** deal, one grounded line — status, what's needed, risk (cite `NextStep`/`LastActivityDate`). Link each deal. **Leader/team rollup across many reps:** cap per-deal commentary to top 5 by Amount per rep.

## 5. Widget (default output when `display_widget` is present: Cowork/desktop/web)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

**Widget payload — Quick/Kiro adaptation:** pass the hydrated widget to `display_widget` as an object, never as JSON text. If you assembled it as text, parse it into an object before the call.
- ❌ WRONG: `widgetDefinition: "{\"renderer\":{...}}"` (stringified with escaped quotes)
- ✅ RIGHT: `widgetDefinition: {"renderer":{...}}` (native object, no quotes around opening brace)

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): strings `title headerStatus subtitle meterLabel meterValueLabel meterTargetLabel meterStatus waterfallCaption datagridCaption calloutTitle calloutDescription primaryButtonLabel primaryButtonContent secondaryButtonLabel secondaryButtonContent` · numbers `meterValue meterMax meterTarget` · objects `waterfallStart` ({label,value}) `waterfallEnd` ({label}) · arrays `meterBands` ([{from,to,variant,label}]) `waterfallSteps` ([{label,delta}]) `datagridRows` ([{name (plain string — format as the opportunity name (e.g. \"Meridian Health platform\"); names must be plain strings, not objects: use `Opportunity.Name.value` from the SF response),amount,prob,close(YYYY-MM-DD),call:{value,badgeVariant}, status:{value,badgeVariant}}] — set `status:{value:\"At risk\",badgeVariant:\"warning\"}` for at-risk rows: Best Case, or Commit with blank NextStep or 7d+ stale LastActivityDate; healthy Commit rows omit status).",
  "props": {
    "title": {
      "description": "Header title for the forecast narrative.",
      "type": "string",
      "example": "Q3 forecast — Dana Ruiz"
    },
    "headerStatus": {
      "description": "Header status badge.",
      "type": "string",
      "example": "88% TO QUOTA"
    },
    "subtitle": {
      "description": "One-line forecast summary.",
      "type": "string",
      "example": "Commit $8.8M against $10.0M quota · +$400K since last week"
    },
    "meterLabel": {
      "description": "Label for the forecast-coverage meter.",
      "type": "string",
      "example": "Commit vs quota"
    },
    "meterValue": {
      "description": "Forecast/coverage value — the meter's current value.",
      "type": "number",
      "example": 8.8
    },
    "meterMax": {
      "description": "The meter's max.",
      "type": "number",
      "example": 10
    },
    "meterTarget": {
      "description": "Quota/target marker on the meter.",
      "type": "number",
      "example": 10
    },
    "meterValueLabel": {
      "description": "Display string for the value.",
      "type": "string",
      "example": "$8.8M commit — 88% of $10.0M quota"
    },
    "meterTargetLabel": {
      "description": "Display string for the target.",
      "type": "string",
      "example": "$10.0M quota"
    },
    "meterStatus": {
      "description": "Short read shown on the meter.",
      "type": "string",
      "example": "gap to quota $1.2M"
    },
    "meterBands": {
      "description": "Color bands for the meter, in order covering 0→max.",
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
          "to": 8,
          "variant": "error",
          "label": "Short"
        },
        {
          "from": 8,
          "to": 9.5,
          "variant": "warning",
          "label": "Close"
        },
        {
          "from": 9.5,
          "to": 10,
          "variant": "success",
          "label": "Made"
        }
      ]
    },
    "waterfallCaption": {
      "description": "Caption for the forecast waterfall.",
      "type": "string",
      "example": "How the number builds: closed → commit → best case → total pipeline"
    },
    "waterfallStart": {
      "description": "Waterfall start bar — object { label, value }.",
      "type": "object",
      "example": {
        "label": "Closed",
        "value": 5200000
      }
    },
    "waterfallSteps": {
      "description": "Waterfall steps — one per contribution/change.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "label": {
            "description": "Step label.",
            "type": "string"
          },
          "delta": {
            "description": "Amount change for this step (signed).",
            "type": "number"
          }
        }
      },
      "example": [
        {
          "label": "+ Commit",
          "delta": 3600000
        },
        {
          "label": "+ Best case",
          "delta": 2100000
        },
        {
          "label": "+ Pipeline",
          "delta": 4300000
        }
      ]
    },
    "waterfallEnd": {
      "description": "Waterfall end bar — object { label }.",
      "type": "object",
      "example": {
        "label": "Total open"
      }
    },
    "datagridCaption": {
      "description": "Caption for the deals datagrid.",
      "type": "string",
      "example": "Commit deals — what has to land to make the number"
    },
    "datagridRows": {
      "description": "Deals in the forecast — one row per deal. Empty array → the datagrid is omitted.",
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
          "amount": {
            "description": "Deal amount (number).",
            "type": "number"
          },
          "prob": {
            "description": "Win probability (number).",
            "type": "number"
          },
          "close": {
            "description": "Close date, ISO YYYY-MM-DD.",
            "type": "string"
          },
          "call": {
            "description": "Forecast-category badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Forecast category label (e.g. Commit / Best Case / Pipeline).",
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
          }
        }
      },
      "example": [
        {
          "name": "Meridian Health platform",
          "amount": 2400000,
          "prob": 60,
          "close": "2026-08-05",
          "call": {
            "value": "Commit",
            "badgeVariant": "success"
          }
        },
        {
          "name": "Cobalt Robotics renewal",
          "amount": 1800000,
          "prob": 75,
          "close": "2026-07-30",
          "call": {
            "value": "Commit",
            "badgeVariant": "success"
          }
        },
        {
          "status": {
            "value": "9d stale",
            "badgeVariant": "warning"
          },
          "name": "Alto Financial seats",
          "amount": 900000,
          "prob": 55,
          "close": "2026-08-08",
          "call": {
            "value": "Best case",
            "badgeVariant": "warning"
          }
        },
        {
          "name": "Pier 9 expansion",
          "amount": 600000,
          "prob": 40,
          "close": "2026-07-31",
          "call": {
            "value": "Best case",
            "badgeVariant": "warning"
          }
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the forecast's key risk or move.",
      "type": "string",
      "example": "Gap closes if Alto and Pier 9 convert to Commit"
    },
    "calloutDescription": {
      "description": "Synthesis callout body.",
      "type": "string",
      "example": "The $1.2M gap shrinks to zero if the two Best Case deals (Alto Financial at $900K and Pier 9 at $600K) both land. Alto is 9 days stale — next action needed this week or it slips to Q4. Pier 9 needs exec sponsorship before close date."
    },
    "primaryButtonLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft forecast email"
    },
    "primaryButtonContent": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft a forecast email for Q3 covering the $8.8M commit, the $1.2M gap, and the two Best Case deals that could close it (Alto Financial and Pier 9 expansion)."
    },
    "secondaryButtonLabel": {
      "description": "Secondary button label.",
      "type": "string",
      "example": "Review at-risk deals"
    },
    "secondaryButtonContent": {
      "description": "Content/target for the secondary button.",
      "type": "string",
      "example": "Show me the Alto Financial and Pier 9 deals in detail, including their stage, next steps, and what needs to happen to move them to Commit."
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
                "definition": "tile/badge",
                "attributes": {
                  "label": "{{headerStatus}}",
                  "variant": "warning"
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
              "showValues": true,
              "size": "lg",
              "start": "{{waterfallStart}}",
              "steps": "{{waterfallSteps}}",
              "end": "{{waterfallEnd}}"
            }
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
                  "header": "Deal",
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
                  "key": "prob",
                  "header": "Prob.",
                  "type": "number",
                  "align": "right"
                },
                {
                  "key": "close",
                  "header": "Close",
                  "type": "date"
                },
                {
                  "key": "call",
                  "header": "My call",
                  "type": "badge"
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


## 6. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

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

ForecastCategory should change? Offer `update-opportunity` (one field, on confirmation). "What if <deal> slips?" → `deal-slip-scenario`. Submission stays manual.
