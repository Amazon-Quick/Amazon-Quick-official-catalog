---
name: customer-health
display_name: Customer Health
description: "Assess customer health from Salesforce account, renewal, case, task, and health data plus email, calendar, documents, and Slack. Use to judge risk, explain engagement or value trends, or prepare a business review; prospect meeting prep: call-prep."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:c7998a02a1b0b2e613b14946ae988869b397e12c103dfc24b1068171495b6c8b"
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

- Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.

# Customer Health

Two jobs, one data pass: the ongoing "are we okay here?" check, and the quarterly business review that proves value and sets up the next phase. Ground → (read + evidence, ONE turn) → score → output.

## Inputs

- **Account:** name or SFDC ID
- **Mode:** health check (default) or QBR prep
- **Period:** last quarter (default) for trend math

## 1. Ground (hardcoded — Account only)

Ground **only Account** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's health/adoption/renewal/NPS `__c` schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })
```

Step 1 is the authority on names — use exact strings, never guess. Consider scalar `__c` fields worth using (health score, adoption/seat usage, renewal date, ARR, NPS, tier) — these are the same fields a health check might later offer to update, so ground them once and reuse. Standard fields, the `Owner`/`Opportunities`/`Cases` spans, and `LastActivityDate` are reliable across orgs; an org that doesn't use Cases just returns empty `edges`, not an error. Do not output all the field names.

## 2. Read (fill from step 1)

`%ACCOUNT%` = the user's match (1–2 words); when an SFDC Id was given instead of a name, swap every `Name: { like: \"%ACCOUNT%\" }` predicate (the Account root, the `Task` root and each `aggregate` filter) for `Id: { eq: \"...\" }`. One call pulls the account plus its open-renewal-relevant opportunities, recent cases, recent tasks, and complete case and task counts — no separate dispatch per object.

**Field rule (avoids the retry loop):** add grounded custom fields only as `Field__c { value }` (`{ value displayValue }` for currency/picklist). Use the standard `Owner` span already written in the template; never invent a relationship span from a raw `Id`/`__c` field. Insert `<ACCT_CUSTOM>` = confirmed Account `__c { value }` fields.

**Canonical query execution — Quick/Kiro adaptation:** The deep read below is a complete canonical `queryInput`, not an outline. Copy it as one unit and substitute only `%ACCOUNT%` (every occurrence), `<ACCT_CUSTOM>`, or the documented complete exact-Id filter. Omit `<ACCT_CUSTOM>` when no confirmed field applies; do not retype, regenerate, shorten, flatten, or hand-edit the surrounding JSON or GraphQL. Keep `aggregate` a sibling of `query` under `uiapi`.

Before the first dispatch, verify that the nested `queryInput` JSON decodes, every placeholder is resolved or omitted, and `()`, `[]`, and `{}` remain balanced. Do not send a reconstructed request and wait for Salesforce to find its syntax errors. If preflight or Salesforce reports a JSON/GraphQL syntax error, discard that attempted request and rebuild once from this exact template with `<ACCT_CUSTOM>` omitted. Validate the rebuilt request before dispatch; if the standard-field form still fails, report the error and stop rather than repairing braces in place.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 1) { edges { node { Id Name { value } Type { value } Industry { value } AnnualRevenue { value displayValue } LastActivityDate { value } CreatedDate { value } <ACCT_CUSTOM> Owner { Name { value } } Opportunities(first: 20, orderBy: { CloseDate: { order: DESC } }) { edges { node { Id Name { value } Type { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsWon { value } } } } Cases(first: 10, where: { CreatedDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { CreatedDate: { order: DESC } }) { edges { node { CaseNumber { value } Subject { value } Status { value } Priority { value } CreatedDate { value } } } } } } } Task(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, ActivityDate: { gte: { literal: LAST_90_DAYS } } }, first: 200, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } Status { value } IsClosed { value } } } } } aggregate { matchedAccounts: Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }) { edges { node { aggregate { Id { count { value } } } } } } caseTotal: Case(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, CreatedDate: { gte: { literal: LAST_90_DAYS } } }) { edges { node { aggregate { Id { count { value } } } } } } caseOpen: Case(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, CreatedDate: { gte: { literal: LAST_90_DAYS } }, IsClosed: { eq: false } }) { edges { node { aggregate { Id { count { value } } } } } } caseEscalated: Case(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, CreatedDate: { gte: { literal: LAST_90_DAYS } }, Status: { eq: \\\"Escalated\\\" } }) { edges { node { aggregate { Id { count { value } } } } } } caseHighPriority: Case(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, CreatedDate: { gte: { literal: LAST_90_DAYS } }, Priority: { in: [\\\"High\\\", \\\"Critical\\\"] } }) { edges { node { aggregate { Id { count { value } } } } } } taskTotal: Task(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, ActivityDate: { gte: { literal: LAST_90_DAYS } } }) { edges { node { aggregate { Id { count { value } } } } } } taskCompleted: Task(where: { Account: { Name: { like: \\\"%ACCOUNT%\\\" } }, ActivityDate: { gte: { literal: LAST_90_DAYS } }, IsClosed: { eq: true } }) { edges { node { aggregate { Id { count { value } } } } } } } } }\"}" })
```

**Case totals — local correction:** `Cases(first: 10)` returns only the ten most recent cases in the window. Take every Support count from the `aggregate` roots: `caseTotal`, `caseOpen`, `caseEscalated` (Status `Escalated`), and `caseHighPriority` (Priority `High` or `Critical`). Present status or priority read from the rows only as the latest ten, never as the total. If `matchedAccounts` is greater than 1, the totals and tasks span more than one account: rerun this request once with the exact-Id filter for the returned Account `Id` and use its totals and tasks. If an aggregate is missing or errors, mark that count unavailable; never count the capped rows instead.

Empty `edges` on `Account` → broaden `%ACCOUNT%`, or ask the user for the right account. Empty `edges` on `Cases`/`Task` just means none in the window — don't retry, don't treat as an error. The `Task` root (last 90d) is the in-CRM activity cadence behind the Engagement-trend dimension (and the widget engagement chart) — read it even when no external calendar/email connector is present.

**Account tasks — local correction:** The `Task` root filters on the task's Account, so it returns the account's tasks logged on its opportunities and contacts as well as on the account. The Account `Tasks` child returns only tasks logged directly on the account, so it missed most activity.

**Task counts and status — local correction:** The `Task` rows stop at 200 and include open tasks. A task's `ActivityDate` is its due date, so the window also returns open tasks due later. Count only completed tasks (`IsClosed` true) as activity. Take the 90-day numbers from the aggregates: `taskCompleted` completed tasks, and `taskTotal` minus `taskCompleted` open ones. Show open tasks as follow-ups, overdue when their `ActivityDate` is before today. The account's `LastActivityDate` also covers calls and meetings this read doesn't return, and a scheduled meeting can set it to a later date. When it's later than the latest completed task and not after today, give it as the last activity date, and don't report the days since that task as days without contact. Build the weekly chart and the Engagement-trend sparkline from the completed rows by `ActivityDate`. If `taskTotal` is greater than the number of rows returned, the rows hold only the latest tasks: say in the chart caption that weeks before the oldest returned `ActivityDate` are incomplete. If a task count is missing or errors, mark it unavailable; never count the rows instead.

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**Issue step 2 and all of step 2b as tool calls in a single turn — do not wait for the SF read to return before firing the searches.** They're independent (searches key on the account name from the request, not the SF result), so batch them together:
- **email**: threads with this account's contacts, last ~90d → cadence vs prior period, most recent exchange + topic
- **calendar**: meeting count/attendees last ~90d vs prior period — is the champion/exec still showing up
- **docs**: success plan, past QBR decks, recent notes → documented outcomes, open commitments
- **slack**: internal mentions → deal-desk/exec concerns, escalations

Use whatever email/calendar/doc/Slack tools are available; skip silently if none are present (SFDC-only is fine). Be explicit about what this skill can't see: product usage, support-ticket detail, and NPS only count if synced into a CRM field or a connected doc — otherwise mark that dimension "not visible from CRM" rather than guessing. Cite source + date for anything you use.

## 3. Score the health (cite every value; invent nothing)

| Dimension | Signal | Status |
|---|---|---|
| Relationship | champion/exec engagement (evidence), breadth of contacts active | 🟢🟡🔴 |
| Engagement trend | in-CRM completed-task cadence (step 2 `taskCompleted` and completed `Task` rows, last 90d) + meeting/email cadence (evidence) vs prior period | |
| Commercial | renewal proximity (open renewal opp `CloseDate`), open expansion, payment/contract issues | |
| Support | step 2 `aggregate` case counts (total, open, Escalated, High/Critical); aging/priority detail only from the latest-ten rows, labeled as such | |
| Value delivery | documented outcomes vs the success plan (docs), if one exists | |

Overall verdict with the one or two dimensions driving it.

## 4. Output — widget FIRST (the rendered UI is the default)

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
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `headerTitle headerStatus` (header — account name; `headerStatus` is a plain string badge label e.g. \"AT RISK\" / \"HEALTHY\" / \"NEEDS ATTENTION\" — not a variant, the renderer maps the label to a variant automatically) `headerSubtitle` (subtitle with ARR · renewal days · health score+trend) · `chartCaption chartCategories chartSeries` (line chart — weekly engagement/usage trend over 6 weeks from evidence; omit the chart entirely if no cadence signal was gathered) · `meterValue meterTarget meterValueLabel meterTargetLabel meterStatus meterBands` (composite health meter 0–100, bands array with from/to/variant/label covering the full range) · `gridCaption gridRows` (health signals datagrid — `gridRows` is an array, one per Step 3 dimension: `{signal, now (plain string — always a formatted string, never a raw number; use context-appropriate formatting e.g. \"322\", \"18 open\", \"0 / 90d\", \"5 of 12\"), trend(number[6]), note, status:{value,badgeVariant} (value plain string e.g. \"Declining\", \"Rising\", \"Cold\", \"Stalled\", \"Softening\", badgeVariant error/warning on 🔴/🟡)}`; the leading Status column reads each row's `status`) · `calloutTitle calloutDescription ctaPrimaryLabel ctaPrimaryMsg accountUrl` (synthesis callout with two buttons — primary is action/sendMessage with first-person prompt, secondary is action/openLink to the account Lightning URL). Omit any block whose data you lack rather than passing empty arrays.",
  "props": {
    "headerTitle": {
      "description": "Header title — the account name.",
      "type": "string",
      "example": "Account health — Meridian Health"
    },
    "headerStatus": {
      "description": "Header status badge label, a plain string (e.g. \"AT RISK\" / \"HEALTHY\" / \"NEEDS ATTENTION\") — the renderer maps the label to a color; do not pass a variant.",
      "type": "string",
      "example": "AT RISK"
    },
    "headerSubtitle": {
      "description": "Subtitle: ARR · days to renewal · health score + trend.",
      "type": "string",
      "example": "$1.2M ARR · renews in 78 days · health 62, down 11 pts this quarter"
    },
    "chartCaption": {
      "description": "Caption for the weekly engagement/usage trend line chart.",
      "type": "string",
      "example": "Weekly active users — 6-week slide from 410 to 322"
    },
    "chartCategories": {
      "description": "Week labels for the trend chart's x-axis (6 weeks), as strings.",
      "type": "array",
      "items": {
        "type": "string"
      },
      "example": [
        "Wk 1",
        "Wk 2",
        "Wk 3",
        "Wk 4",
        "Wk 5",
        "Wk 6"
      ]
    },
    "chartSeries": {
      "description": "Trend series — one object {name, data}. Omit the whole chart if no cadence signal was gathered.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "description": "Series name.",
            "type": "string"
          },
          "data": {
            "description": "Weekly values — a number array matching chartCategories order.",
            "type": "array",
            "items": {
              "type": "number"
            }
          }
        }
      },
      "example": [
        {
          "name": "Weekly active users",
          "data": [
            410,
            398,
            375,
            360,
            341,
            322
          ]
        }
      ]
    },
    "meterValue": {
      "description": "Composite health score, 0–100 — the meter's current value.",
      "type": "number",
      "example": 62
    },
    "meterTarget": {
      "description": "Health target on the meter.",
      "type": "number",
      "example": 75
    },
    "meterValueLabel": {
      "description": "Display string for the health score.",
      "type": "string",
      "example": "62 / 100"
    },
    "meterTargetLabel": {
      "description": "Display string for the target.",
      "type": "string",
      "example": "75 healthy"
    },
    "meterStatus": {
      "description": "Short health read shown on the meter.",
      "type": "string",
      "example": "at risk"
    },
    "meterBands": {
      "description": "Color bands for the health meter, in order covering 0→100.",
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
          "to": 50,
          "variant": "error",
          "label": "Critical"
        },
        {
          "from": 50,
          "to": 75,
          "variant": "warning",
          "label": "At risk"
        },
        {
          "from": 75,
          "to": 100,
          "variant": "success",
          "label": "Healthy"
        }
      ]
    },
    "gridCaption": {
      "description": "Caption for the health-signals datagrid.",
      "type": "string",
      "example": "Health signals, worst first — trend is last 6 weeks"
    },
    "gridRows": {
      "description": "Health signals — one row per Step 3 dimension. Empty array → the datagrid is omitted.",
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
          "signal": {
            "description": "Signal / dimension name.",
            "type": "string"
          },
          "now": {
            "description": "Current value as a formatted string, never a raw number (e.g. \"322\", \"18 open\", \"0 / 90d\", \"5 of 12\").",
            "type": "string"
          },
          "trend": {
            "description": "Sparkline values — a 6-number array.",
            "type": "array",
            "items": {
              "type": "number"
            }
          },
          "note": {
            "description": "Short evidence note for the signal.",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Declining",
            "badgeVariant": "error"
          },
          "signal": "Weekly active users",
          "now": "322",
          "trend": [
            410,
            398,
            375,
            360,
            341,
            322
          ],
          "note": "Down 21% — champion left in wk 3"
        },
        {
          "status": {
            "value": "Rising",
            "badgeVariant": "error"
          },
          "signal": "Support tickets",
          "now": "18 open",
          "trend": [
            4,
            6,
            9,
            12,
            15,
            18
          ],
          "note": "3 escalated, 2 past SLA"
        },
        {
          "status": {
            "value": "Cold",
            "badgeVariant": "warning"
          },
          "signal": "Exec sponsor touches",
          "now": "0 / 90d",
          "trend": [
            2,
            1,
            1,
            0,
            0,
            0
          ],
          "note": "No exec contact since March"
        },
        {
          "status": {
            "value": "Stalled",
            "badgeVariant": "warning"
          },
          "signal": "Feature adoption",
          "now": "5 of 12",
          "trend": [
            5,
            5,
            5,
            5,
            5,
            5
          ],
          "note": "Flat — never onboarded to analytics"
        },
        {
          "status": {
            "value": "Softening",
            "badgeVariant": "warning"
          },
          "signal": "NPS (last survey)",
          "now": "42",
          "trend": [
            58,
            58,
            51,
            51,
            42,
            42
          ],
          "note": "Slipped from promoter to passive"
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the single most important health read.",
      "type": "string",
      "example": "Renewal is at risk — act this month"
    },
    "calloutDescription": {
      "description": "Synthesis callout body — the read and the recommended move.",
      "type": "string",
      "example": "Usage is down 21%, the champion left in week 3, and there's been no exec touch in 90 days with the renewal 78 days out. Book an exec business review and a re-onboarding on analytics before the quota clock runs down."
    },
    "ctaPrimaryLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft exec business review"
    },
    "ctaPrimaryMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft an exec business review agenda for Meridian Health focused on resetting the relationship and addressing the 21% usage decline before renewal."
    },
    "accountUrl": {
      "description": "Account Lightning URL for the secondary \"View in Salesforce\" button (action/openLink).",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/r/Account/001AX000004pQ2rYAE/view"
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
                      "name": "activity",
                      "size": "xl",
                      "alt": ""
                    }
                  },
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{headerTitle}}",
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
              "text": "{{headerSubtitle}}",
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
                  "chartType": "line",
                  "caption": "{{chartCaption}}",
                  "categories": "{{chartCategories}}",
                  "series": "{{chartSeries}}",
                  "valueFormat": "number",
                  "showValues": false,
                  "showLegend": false
                }
              },
              {
                "definition": "tile/meter",
                "attributes": {
                  "label": "Composite health",
                  "value": "{{meterValue}}",
                  "min": 0,
                  "max": 100,
                  "target": "{{meterTarget}}",
                  "valueFormat": "number",
                  "valueLabel": "{{meterValueLabel}}",
                  "targetLabel": "{{meterTargetLabel}}",
                  "status": "{{meterStatus}}",
                  "size": "lg",
                  "bands": "{{meterBands}}"
                }
              }
            ]
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{gridCaption}}",
              "appearance": "striped",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "signal",
                  "header": "Signal",
                  "type": "text"
                },
                {
                  "key": "now",
                  "header": "Current",
                  "type": "text",
                  "align": "right"
                },
                {
                  "key": "trend",
                  "header": "6-wk trend",
                  "type": "sparkline"
                },
                {
                  "key": "note",
                  "header": "Read",
                  "type": "text"
                }
              ],
              "rows": "{{gridRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "error",
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
                      "label": "View in Salesforce",
                      "iconName": "open-in-new",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/openLink",
                            "attributes": {
                              "url": "{{accountUrl}}"
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

**Health check mode:**
```
# Health: <Account> — 🟢/🟡/🔴
<verdict sentence>
<dimension table with evidence>
## Watch items
- <specific signal, why it matters, suggested action>
## Suggested SFDC updates
- <health/status fields, if grounded> - these live on the Account record: show before/after and confirm before writing, or output as a checklist on a read-only connector
```

**QBR prep mode:** add the meeting kit —
1. **Value delivered** — outcomes since last review, in their metrics, with sources
2. **Adoption story** — what's working, what's underused (only CRM/document-visible facts)
3. **Open items** — Cases resolved/open, commitments from last QBR and their status
4. **Next phase** — the expansion plays (`expansion-whitespace`) and renewal framing (`renewal-radar`) worth raising
5. **Agenda + attendees** — who should be in the room from the stakeholder map, and the asks for their execs
Offer the agenda as a doc and the meeting via `schedule-meeting`.
