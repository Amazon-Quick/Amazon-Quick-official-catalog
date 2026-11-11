---
name: rep-context
display_name: Rep Context
description: "Catch a manager up on one of their sales reps before a 1:1: the rep's pipeline, recent activity, what they are working on, and where they need help, with suggested questions. Use when the person named is an internal rep, not a customer contact."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:c748adee6ff794e2d5e316c36b25ec321023551a2920709776a6c3f6414e2f75"
id: "0b8ed4f8-7abb-4f10-8476-07bb47cf043a"
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


# Rep Context

Leader's 1:1 prep on one rep — pipeline, activity, where they're stuck. The named person is an INTERNAL rep (not a customer). Ground → read (pipeline + activity, one turn) → needs-help + questions.

## 1. Ground + resolve the rep (one turn)

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's risk/health/next-step `__c` fields — use exact names. **Ground Opportunity and resolve the rep in one request** — `objectInfos` and the `User` resolver are independent `uiapi` siblings in the query below — then hold every rep-scoped read until `<REP_ID>` is resolved.

**Resolve the named rep to one active User.** If the manager supplied a Salesforce User Id, set `<REP_ID>` to it directly. Otherwise resolve a small active-User candidate set first — use the supplied name as a prefix (no leading `%`) in `<REP_PREFIX>`; for an email, swap the `Name` predicate for `Email: { eq: \"<REP_EMAIL>\" }`:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } query { User(where: { Name: { like: \\\"<REP_PREFIX>%\\\" }, IsActive: { eq: true } }, orderBy: { Name: { order: ASC } }, first: 5) { pageResultCount pageInfo { hasNextPage } edges { node { Id Name { value } Email { value } Title { value } } } } } } }\"}" })
```
Auto-select `<REP_ID>` only when exactly one candidate returns, its `Name` exactly matches the supplied full name, and `hasNextPage` is false (for an email lookup, require one exact email match and `hasNextPage: false`). If `pageResultCount` is 0 or the match is ambiguous, show the returned names/emails/titles and ask the manager to choose or supply the full name, email, or User Id — **do not read the rep's book, activity, Slack, or calendar until `<REP_ID>` is resolved.**

## 2. Read the rep's book + activity (one turn, keyed on `<REP_ID>`)

Filter every read by `OwnerId: { eq: "<REP_ID>" }`. Splice confirmed `__c` fields into `<OPP_CUSTOM>`. **Check `{` vs `}` balance before dispatching.** This is a **Top 20 sample** for named deals — the pipeline totals come from the aggregate below, not from counting these rows.

**Sample scope and exact calculations — Quick/Kiro adaptation:** Let `R` be the returned Opportunity rows (at most 20) and `C` be the sum of stage-aggregate counts. Only aggregate stage/count/Amount and this-quarter won values describe the complete book. Every claim derived from row-only CloseDate, NextStep, LastActivityDate, Account, or Contact Role data must say `among the top R of C sampled` when `R < C`; never present a sampled count, ratio, or generalization as all `C` deals. Transform rows keyed by Opportunity Id, preserve exact returned Opportunity and Account names, and include every matching sampled row in account sums before formatting. Do not call a deal `healthiest`, claim conversion/coverage/pace, or assign a performance label without a returned field or explicit deterministic formula. Populate `age` only as days since LastActivityDate against one explicit as-of date/timezone, label it `Days since activity`, and omit it when LastActivityDate is blank.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { OwnerId: { eq: \\\"<REP_ID>\\\" }, IsClosed: { eq: false } }, orderBy: { Amount: { order: DESC } }, first: 20) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } OpportunityContactRoles { edges { node { Id } } } } } } } } }\"}" })
```

Fire this SOQL aggregate in the same turn, same owner + `IsClosed` filter as the sample above — it is the authoritative source for `Open: <N> opps, $<total> | by stage: <counts>`:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amt FROM Opportunity WHERE OwnerId = '<REP_ID>' AND IsClosed = false GROUP BY StageName" })
```

In the SAME turn, fire the rep's recent activity — both Tasks AND Events (last 14d), plus this-quarter closed-won for the "This Q closed" number. These are independent reads keyed on the rep (not on each other), so batch all of them in this one turn — no added round-trip depth:

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT COUNT(Id) cnt FROM Task WHERE OwnerId = '<REP_ID>' AND ActivityDate >= LAST_N_DAYS:14" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT COUNT(Id) cnt FROM Event WHERE OwnerId = '<REP_ID>' AND ActivityDate >= LAST_N_DAYS:14" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT SUM(Amount) amt, COUNT(Id) cnt FROM Opportunity WHERE OwnerId = '<REP_ID>' AND IsWon = true AND CloseDate = THIS_QUARTER" })
```

`<N> activities logged` = the Task `cnt` + Event `cnt` from the COUNT aggregates above. `InvalidSyntax` / "offending token `<EOF>`" → missing a closing `}`; add it and retry.

## 2b. Evidence (same turn — skip silently if absent)

- **Slack**: rep's posts in team/deal channels last 14d — blockers, asks, exec/deal-desk flags. (Ask once which channels if unknown.)
- **calendar**: external meetings last 14d + booked next 7d, if visible.

## 3. Analyze (cite records/threads; invent nothing)

From pipeline + activity: largest opp with risk flags (stale LastActivityDate, blank NextStep, single-threaded = ≤1 contact role); any opp a Slack post flags a blocker on; coverage gap if pipeline thin; hygiene if many stale.

## 4. 1:1 questions

3–4 specific, grounded questions — not "how's pipeline" but "[Account] at [Stage] [N] days, you flagged a security review in Slack — where's that?"

## 5. Widget (default output when `display_widget` is present: Cowork/desktop/web)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

**Two-graph data mode — approved local correction:** Use attainment mode only when an attributable source supplies a plan/target plus historical quarter values and a deterministic status formula. Otherwise use no-attainment mode; never copy schema examples or derive plan, attainment, pace, conversion, or trend from current open pipeline.

- **Attainment mode:** set `headerStatus`/`headerStatusVariant`, `subtitle`, `chartCaption`, `chartCategories`, `chartSeries`, and `chartValueFormat:"percent"` only from the supplied plan/history/formula. Keep the pie as pipeline Amount by stage with currency values.
- **No-attainment mode (default for the documented Salesforce reads):** set `headerStatus:"PIPELINE SNAPSHOT"`, `headerStatusVariant:"info"`, and a subtitle containing only aggregate open count/Amount, current-quarter won count/Amount, Task+Event count, and explicit sample scope. Sort stage aggregate groups by Amount descending for `chartCategories`; set `chartSeries` to one numeric `Open pipeline` Amount series, `chartCaption:"Open pipeline $ by stage"`, and `chartValueFormat:"currency"`. Use the same groups' counts for `pieSlices`, highlight a largest-count slice, set `pieCenter` to the aggregate open count as a string, `pieCenterLabel:"Open deals"`, `pieCaption:"Open deal count by stage"`, and `pieValueFormat:"number"`. This retains exactly two grounded graphs and every independent widget block.

**Deal identity and links — approved local correction:** Each `gridRows` item uses exact `Opportunity.Name.value` as `deal`, exact `Account.Name.value` as `account`, and that same Opportunity's returned Id for its link. Build `recordLinkButtons` as one complete `tile/button` per displayed grid row, in identical order, labeled `Open <exact Opportunity Name>` with `iconName:"open-in-new"`, `variant:"secondary"`, and one `action/openLink` to `https://<myDomain>/lightning/r/Opportunity/<Id>/view`. Never shorten a name, use an Account Id/list URL, merge same-account rows, or omit a displayed row's link. Set `gridAgeHeader:"Days since activity"`; status badges may name only deterministic row facts such as Past close, No next step, or Single-threaded, and must not claim health or pace.

The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. The widget is the output when `display_widget` is available; produce the text below only as the fallback when it's unavailable (e.g. a terminal). Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left), then call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once. A value that is *only* a `{{token}}` (chart categories/series, piechart slices, datagrid rows, record-link buttons) becomes the typed literal — arrays stay arrays, numbers stay numbers; a `{{token}}` inside a larger string is interpolated as text.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `{{pageTitle}}` header title (users icon) + `{{headerStatus}}` status badge with `{{headerStatusVariant}}` + `{{subtitle}}` grounded summary; two wrapped graphs — column chart with `{{chartCaption}}`, `{{chartCategories}}`, `{{chartSeries}}`, and `{{chartValueFormat}}`, plus piechart with `{{pieCaption}}`, `{{pieCenterLabel}}`, `{{pieCenter}}`, `{{pieSlices}}`, and `{{pieValueFormat}}`; `{{gridRows}}` top-open-deals datagrid (`[{ deal, account, amount, stage, age, next, status? }]`, where `deal` is exact Opportunity.Name and `account` is exact Account.Name, ranked by Amount); `{{gridAgeHeader}}` labels age as days since activity; `{{recordLinkButtons}}` carries one Opportunity openLink button per displayed row; `{{synthTitle}}`/`{{synthDescription}}` synthesis callout (variant warning) with two action/sendMessage buttons — primary `{{primaryLabel}}`/`{{primaryPrompt}}` (biggest gap / pipeline generation), secondary `{{secondaryLabel}}`/`{{secondaryPrompt}}` (most urgent deal / unstick the stalled deal). Before calling: every `{{token}}` resolved (no `{{…}}`/`{!…}`); exactly 2 graphs (column + piechart); datagrid `amount`/`age` numbers and `stage` a badge object, rows carry a leading `status` object where needed; one recordLinkButtons openLink button exists per grid row; callout has 2 real sendMessage buttons; the text section below is produced only when `display_widget` is unavailable.",
  "props": {
    "pageTitle": {
      "description": "Header title for the rep-context view.",
      "type": "string",
      "example": "Rep snapshot — Priya Nair"
    },
    "headerStatus": {
      "description": "Grounded status label; use PIPELINE SNAPSHOT in no-attainment mode unless an explicit formula supports a performance status.",
      "type": "string",
      "example": "PIPELINE SNAPSHOT"
    },
    "headerStatusVariant": {
      "description": "Badge variant: info in no-attainment mode; use warning/error/success only from an explicit performance-status formula.",
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
      "description": "Grounded summary. In no-attainment mode use aggregate open count/Amount, current-quarter won count/Amount, Task+Event count, and sample scope only.",
      "type": "string",
      "example": "Q4 · $3.0M open across 2 deals · $0 closed-won this quarter · 6 activities logged in 14 days"
    },
    "chartCaption": {
      "description": "Attainment caption when sourced; otherwise Open pipeline $ by stage.",
      "type": "string",
      "example": "Open pipeline $ by stage"
    },
    "chartValueFormat": {
      "description": "Column chart value format for the chosen data mode.",
      "type": "string",
      "enum": [
        "percent",
        "currency",
        "number"
      ],
      "example": "currency"
    },
    "chartCategories": {
      "description": "Column chart categories: quarter labels in attainment mode or stage names sorted by Amount descending in no-attainment mode.",
      "type": "array",
      "items": {
        "type": "string"
      },
      "example": [
        "Qualification",
        "Prospecting",
        "Value Proposition"
      ]
    },
    "chartSeries": {
      "description": "One column-chart series. Use sourced attainment percentages or aggregate open-pipeline Amounts for the selected mode.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "description": "Series name.",
            "type": "string"
          },
          "data": {
            "description": "Numeric values matching chartCategories and chartValueFormat.",
            "type": "array",
            "items": {
              "type": "number"
            }
          }
        }
      },
      "example": [
        {
          "name": "Open pipeline",
          "data": [
            4326000,
            3982000,
            2910000
          ]
        }
      ]
    },
    "pieCaption": {
      "description": "Open pipeline by stage in attainment mode or Open deal count by stage in no-attainment mode.",
      "type": "string",
      "example": "Open deal count by stage"
    },
    "pieValueFormat": {
      "description": "Pie value format for the selected data mode.",
      "type": "string",
      "enum": [
        "currency",
        "number"
      ],
      "example": "number"
    },
    "pieCenterLabel": {
      "description": "Center label for the selected data mode.",
      "type": "string",
      "example": "Open deals"
    },
    "pieCenter": {
      "description": "Formatted pipeline Amount in attainment mode or aggregate open-deal count as a string in no-attainment mode.",
      "type": "string",
      "example": "28"
    },
    "pieSlices": {
      "description": "One stage slice using Amount in attainment mode or count in no-attainment mode; highlight a deterministic largest slice. Empty array omits the pie.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "label": {
            "description": "Stage label.",
            "type": "string"
          },
          "value": {
            "description": "Stage value.",
            "type": "number"
          },
          "role": {
            "description": "Optional emphasis; set \"highlight\" on the largest/riskiest stage.",
            "type": "string",
            "enum": [
              "normal",
              "highlight"
            ]
          }
        }
      },
      "example": [
        {
          "label": "Qualification",
          "value": 5,
          "role": "highlight"
        },
        {
          "label": "Prospecting",
          "value": 5
        },
        {
          "label": "Value Proposition",
          "value": 4
        }
      ]
    },
    "gridAgeHeader": {
      "description": "Header for age computed as days since LastActivityDate.",
      "type": "string",
      "example": "Days since activity"
    },
    "gridRows": {
      "description": "Top sampled open Opportunities — one exact returned Opportunity per row, amount-descending. Empty array omits the datagrid.",
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
            "description": "Exact Opportunity.Name.value, never shortened or reconstructed.",
            "type": "string"
          },
          "account": {
            "description": "Exact Account.Name.value for the same Opportunity row.",
            "type": "string"
          },
          "amount": {
            "description": "Deal amount (number).",
            "type": "number"
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
                "description": "Badge color: warning=stalled/Negotiation, info=Proposal/advancing.",
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
          "age": {
            "description": "Days since LastActivityDate against the explicit as-of date; omit when LastActivityDate is blank.",
            "type": "number"
          },
          "next": {
            "description": "Next step (text).",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Coach",
            "badgeVariant": "warning"
          },
          "deal": "Cobalt Robotics — New Business Platform",
          "account": "Cobalt Robotics",
          "amount": 1800000,
          "stage": {
            "value": "Negotiation",
            "badgeVariant": "warning"
          },
          "age": 71,
          "next": "Redlines to legal"
        },
        {
          "status": {
            "value": "Advance",
            "badgeVariant": "info"
          },
          "deal": "Delta Systems — Expansion Analytics",
          "account": "Delta Systems",
          "amount": 600000,
          "stage": {
            "value": "Proposal",
            "badgeVariant": "info"
          },
          "age": 34,
          "next": "Book exec demo"
        },
        {
          "status": {
            "value": "At risk",
            "badgeVariant": "error"
          },
          "deal": "Harbor Freight Co — Renewal Operations",
          "account": "Harbor Freight Co",
          "amount": 400000,
          "stage": {
            "value": "Proposal",
            "badgeVariant": "info"
          },
          "age": 52,
          "next": "Stalled 18d — requalify"
        }
      ]
    },
    "recordLinkButtons": {
      "description": "One complete tile/button per displayed Opportunity, in grid order, opening that exact returned Opportunity Id.",
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
            "label": "Open Cobalt Robotics — New Business Platform",
            "iconName": "open-in-new",
            "variant": "secondary",
            "actions": {
              "click": [
                {
                  "definition": "action/openLink",
                  "attributes": {
                    "url": "https://org.lightning.force.com/lightning/r/Opportunity/006000000000000AAA/view"
                  }
                }
              ]
            }
          }
        }
      ]
    },
    "synthTitle": {
      "description": "Synthesis callout heading — the biggest gap.",
      "type": "string",
      "example": "Top-20 sample needs hygiene review"
    },
    "synthDescription": {
      "description": "Synthesis callout body.",
      "type": "string",
      "example": "Among the top 20 of 28 sampled deals, three are past close and four have blank next steps; review those exact records without extrapolating to the unsampled eight."
    },
    "primaryLabel": {
      "description": "Primary button label (action/sendMessage) — biggest gap / pipeline generation.",
      "type": "string",
      "example": "Draft pipeline plan"
    },
    "primaryPrompt": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft a pipeline review plan for Priya Nair using the aggregate totals and the explicitly labeled top-20 sample."
    },
    "secondaryLabel": {
      "description": "Secondary button label (action/sendMessage) — most urgent deal.",
      "type": "string",
      "example": "Unstick Harbor deal"
    },
    "secondaryPrompt": {
      "description": "First-person prompt the secondary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft coaching notes for the Harbor Freight Co deal which has stalled 18 days and needs requalifying."
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
            "attributes": { "gap": "sm", "align": "center", "justify": "between", "isWrapped": true },
            "children": [
              {
                "definition": "tile/row",
                "attributes": { "gap": "sm", "align": "center" },
                "children": [
                  { "definition": "tile/icon", "attributes": { "name": "users", "size": "xl", "alt": "" } },
                  { "definition": "tile/text", "attributes": { "text": "{{pageTitle}}", "variant": "h1" } }
                ]
              },
              { "definition": "tile/badge", "attributes": { "label": "{{headerStatus}}", "variant": "{{headerStatusVariant}}" } }
            ]
          },
          { "definition": "tile/text", "attributes": { "text": "{{subtitle}}", "variant": "caption", "color": "muted" } },

          { "definition": "tile/separator" },

          {
            "definition": "tile/column",
            "attributes": { "gap": "md" },
            "children": [
              {
                "definition": "tile/chart",
                "attributes": {
                  "chartType": "column",
                  "caption": "{{chartCaption}}",
                  "categories": "{{chartCategories}}",
                  "series": "{{chartSeries}}",
                  "valueFormat": "{{chartValueFormat}}",
                  "showValues": true,
                  "showLegend": false
                }
              },
              {
                "definition": "tile/piechart",
                "attributes": {
                  "caption": "{{pieCaption}}",
                  "variant": "donut",
                  "valueFormat": "{{pieValueFormat}}",
                  "centerLabel": "{{pieCenterLabel}}",
                  "centerValue": "{{pieCenter}}",
                  "slices": "{{pieSlices}}"
                }
              }
            ]
          },

          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "Top open deals — where to coach",
              "appearance": "striped",
              "defaultSort": { "key": "amount", "direction": "desc" },
              "columns": [
                { "key": "status", "header": "Status", "type": "badge" },
                { "key": "deal", "header": "Opportunity", "type": "text" },
                { "key": "account", "header": "Account", "type": "text" },
                { "key": "amount", "header": "Amount", "type": "currency", "align": "right", "sortable": true },
                { "key": "stage", "header": "Stage", "type": "badge" },
                { "key": "age", "header": "{{gridAgeHeader}}", "type": "number", "align": "right" },
                { "key": "next", "header": "Next step", "type": "text" }
              ],
              "rows": "{{gridRows}}"
            }
          },

          {
            "definition": "tile/column",
            "attributes": { "gap": "sm" },
            "children": [
              { "definition": "tile/text", "attributes": { "text": "Opportunity records", "variant": "section-title" } },
              {
                "definition": "tile/row",
                "attributes": { "gap": "sm", "align": "center", "isWrapped": true },
                "children": "{{recordLinkButtons}}"
              }
            ]
          },

          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "warning",
              "title": "{{synthTitle}}",
              "description": "{{synthDescription}}"
            },
            "children": [
              {
                "definition": "tile/row",
                "attributes": { "gap": "sm", "align": "center", "isWrapped": true },
                "children": [
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{primaryLabel}}",
                      "variant": "primary",
                      "actions": { "click": [ { "definition": "action/sendMessage", "attributes": { "content": "{{primaryPrompt}}" } } ] }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{secondaryLabel}}",
                      "variant": "secondary",
                      "actions": { "click": [ { "definition": "action/sendMessage", "attributes": { "content": "{{secondaryPrompt}}" } } ] }
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
# Rep Context: <Name>
## Pipeline
- Open: <N> opps, $<total> | by stage: <counts> | This Q closed: $<X> (<N> won)
- Top 3: **<Account>** $<X> <Stage> …
## Last 2 Weeks
- <N> activities logged; <N> external meetings (if calendar visible)
- Slack: <1–2 lines of what they raised — link threads>
## Likely Needs Help On
- **<Account>** $<X> — <specific flag + evidence>
## 1:1 Questions
1. <deal-specific, evidenced>
## Wins to Acknowledge
- <closed / advanced / notable from Slack>
```
