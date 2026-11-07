---
name: account-plan
description: "Build or retrieve an account plan from Salesforce Account, AccountPlan, pipeline, activity, and relationship data, covering vision, priorities, competition, KPIs, and relationship risks. Use to review an existing plan or create one for a customer account."
icon: assets/salesforce.svg
checksum: "sha256:f8476c6793d2e2198925330fa46da9870dcec3e9a8a36c0a462d9a8fa81e7ee4"
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
# Goal:
View or create an `AccountPlan` for a Salesforce Account entirely via the API — the strategic picture (challenges, competitive landscape, industry trends, priorities, vision) and the relationship SWOT.

# Audience:
Sales-org workers who want results fast. Minimize thinking when it's not needed; get them the plan.

# Rules:

- Parallelize independent reads — fire the account resolve and the AccountPlan-custom grounding in ONE turn.
- **Pick View vs Create from the verb before doing anything.** View = show/get/pull up/view/see. Create = create/build/set up/draft/make. Ambiguous → ask which; **never fall through a view request into creating a record.**
- On the create path, flag anything you can't source with `[needs validation]`.
- **`Status` is always `"Not Started"` on creation.** Never create a plan in any other status; lifecycle changes are out of scope.

**Voice/tone (create path only).** The generated narrative fields should read in the org's own house voice, not a generic register. Infer that voice in priority order: (1) **explicit user direction** — if the user dictates tone or wording, follow it verbatim; (2) **this account's existing plan prose**, when V1 already returned a plan (the second-plan case) — the truest house-voice sample you'll have; (3) **`Account.Description`** from step 1, as a light register anchor — it's often short or blank, so lean on it lightly. Absent all three, **default to a clear, plainly-professional register**: direct declarative sentences, concrete and specific, no marketing adjectives ("robust", "cutting-edge"), no filler, no exclamation points. Voice governs **style only** — it never licenses inventing content: numbers, quotes, competitor names, and every other claim still obey the cite-as-queried / `[needs validation]` rule above.

The account's real competitor list and org defaults for plan naming/start date are external knowledge — infer from the org's own data or ask the user once. Never invent them.

# Account Plan

## 1. Resolve the account (fire in parallel with step 2)

If the user gave a Salesforce Id, skip to the path. Otherwise resolve by name — this same read seeds the Create-path context (industry, revenue, employees, description):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 5) { edges { node { Id Name { value } Industry { value } Website { value } Description { value } AnnualRevenue { value displayValue } NumberOfEmployees { value } Type { value } BillingCity { value } BillingCountry { value } Owner { Name { value } } } } } } } }\"}" })
```

- **One match** → take its `Id`, keep the other fields as account context.
- **Multiple** → list candidates (Name · Industry · Website · Owner) and ask which. Don't guess.
- **None** → tell the user no Account by that name exists; ask them to confirm the name or give the Id. Never invent or create an Account.

## 2. Ground AccountPlan customs (fire in parallel with step 1)

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"AccountPlan\\\"]) { fields { ApiName label } } } }\"}" })
```

`AccountPlan` is **feature-gated** — ObjectInfo may not surface it in every org. If this returns an error or empty, that is NOT fatal: skip custom grounding and use the SOQL fallback in V1. Note any `__c` fields whose `label` matches plan/relationship keywords for `<PLAN_CUSTOM>`.

---

# View path

## V1. Query the existing plan (by resolved AccountId)

GraphQL first; insert `<PLAN_CUSTOM>` = confirmed `__c { value }` fields from step 2:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { AccountPlan(where: { AccountId: { eq: \\\"<ID>\\\" } }, first: 5, orderBy: { LastModifiedDate: { order: DESC } }) { edges { node { Id Name { value } Status { value } StartDate { value } LastModifiedDate { value } AccountChallenges { value } AccountCmptvWeaknesses { value } AccountCompetitiveStrengths { value } AccountCompetitors { value } AccountIndustryTrends { value } AccountPrfmIndicators { value } AccountStrategicPriorities { value } AccountVision { value } RelationshipOpportunities { value } RelationshipStrengths { value } RelationshipThreats { value } RelationshipWeaknesses { value } <PLAN_CUSTOM> Account { Name { value } } } } } } } }\"}" })
```

**Fallback (feature-gated object).** If `AccountPlan` isn't UI-API queryable here, use describe-grounded SOQL at **`v63.0`**:

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Id, Name, AccountId, Account.Name, AccountChallenges, AccountCmptvWeaknesses, AccountCompetitiveStrengths, AccountCompetitors, AccountIndustryTrends, AccountPrfmIndicators, AccountStrategicPriorities, AccountVision, RelationshipOpportunities, RelationshipStrengths, RelationshipThreats, RelationshipWeaknesses, StartDate, Status, LastModifiedDate FROM AccountPlan WHERE AccountId = '[Id]' ORDER BY LastModifiedDate DESC" })
```

On `INVALID_TYPE`, **first confirm the request used `v63.0`** (retry at v63.0 if not) — report "AccountPlan is not available in this org" only when a correctly-versioned v63.0 request still returns `INVALID_TYPE`.

- **One plan** → use it. **Multiple** → list (Name · Status · StartDate · LastModifiedDate), default to most-recently-modified and say so. **None** → tell the user there's no plan yet and offer to create one (switch to Create path). Never invent plan content.

## V2. Render → **Step R**. Read-only — never write on this path.

---

# Create path

## C1. Guard against duplicates

Run V1 first. **Plan exists** → render it (Step R) and ask the user to confirm they want a *second* plan before proceeding — don't duplicate without explicit yes. **None** → continue.

## C2. Gather context (one turn — batch the SF read with any web research)

**One GraphQL read** pulls open pipeline + recent activity together as children of the account (replaces two SOQL calls):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ID>\\\" } }, first: 1) { edges { node { Opportunities(where: { IsClosed: { eq: false } }, first: 10, orderBy: { CloseDate: { order: ASC } }) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } Tasks(first: 10, where: { ActivityDate: { gte: { literal: LAST_90_DAYS } } }, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } } } } } } } } } }\"}" })
```

Open opps inform `RelationshipOpportunities`/`RelationshipStrengths`; quiet Tasks inform `RelationshipThreats`. In the same turn, do web research (if a tool is present) to ground the competitive picture, industry trends, and strategic priorities. **Only write claims you can trace to a source** — `[needs validation]` for anything thin, general/inferential phrasing over invented specifics ("likely prioritizing cost reduction given industry headwinds", not "cutting costs 20%"). If the user dictated field values, use them verbatim and generate only the rest.

## C3. Assemble the field map

| Field | Holds |
|---|---|
| `AccountId` | Resolved Id (required FK). |
| `Name` | Default `"{Account Name} Account Plan"` unless the user names it. |
| `AccountChallenges` | Key business challenges. |
| `AccountCmptvWeaknesses` | The account's competitive weaknesses. |
| `AccountCompetitiveStrengths` | The account's competitive strengths. |
| `AccountCompetitors` | Primary competitors. |
| `AccountIndustryTrends` | Relevant industry trends. |
| `AccountPrfmIndicators` | Key performance indicators. |
| `AccountStrategicPriorities` | Strategic priorities. |
| `AccountVision` | Stated or inferred vision. |
| `RelationshipOpportunities` | Opportunities to grow the relationship. |
| `RelationshipStrengths` | Current relationship strengths. |
| `RelationshipThreats` | Threats to the relationship. |
| `RelationshipWeaknesses` | Relationship weaknesses. |
| `StartDate` | Default today, `YYYY-MM-DD`. |
| `Status` | **Always `"Not Started"`.** |

## C4. Confirm — the write gate

Show the assembled field map (narrative + resolved `AccountId`/`Name`) and let the user correct it. **Do not create the record until the user confirms or edits.**

## C5. Create, verify, render

```
dispatch(method: "POST", url: "/services/data/v63.0/sobjects/AccountPlan",
  body: { "AccountId": "[accountId]", "Name": "[Account Name] Account Plan", "AccountChallenges": "…", "AccountCmptvWeaknesses": "…", "AccountCompetitiveStrengths": "…", "AccountCompetitors": "…", "AccountIndustryTrends": "…", "AccountPrfmIndicators": "…", "AccountStrategicPriorities": "…", "AccountVision": "…", "RelationshipOpportunities": "…", "RelationshipStrengths": "…", "RelationshipThreats": "…", "RelationshipWeaknesses": "…", "StartDate": "[today YYYY-MM-DD]", "Status": "Not Started" })
```

Capture the returned `id`, read it back to confirm it persisted, verify `Status` is `Not Started` and `AccountId` matches, then render (**Step R**):

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/sobjects/AccountPlan/[createdPlanId]")
```

---

## Step R — Render (shared)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

The growth meter and objectives are synthesized from what you already gathered — the AccountPlan narrative fields (`AccountStrategicPriorities`, `AccountVision`, relationship fields) become the objective rows and the synthesis callout; the C2 open-pipeline read and `Account.AnnualRevenue` inform the growth figures. FY target and per-objective progress are judgment calls off that narrative, not structured Salesforce fields — reason from the text, mark anything thin `[needs validation]`, and never invent dollar figures. The account-analysis narrative (challenges, competitors, industry trends, performance indicators) isn't carried by the widget — include it in the markdown fallback below. Blank fields stay "blank", never invented.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `planTitle` (e.g. \"Account plan — <Account> FY26\") · `headerStatus` (a short pace badge, e.g. \"BEHIND PACE\"/\"ON PLAN\") · `planSubtitle` (one line: live ARR → target · N objectives · on track on M of N) · **growth meter** `growthValue`/`growthMax`/`growthTarget` (raw numbers in the same unit, e.g. $M — current booked/live revenue, the plan ceiling, and the FY target), `growthValueLabel`/`growthTargetLabel` (display strings like \"$1.6M of $3.0M plan\"), `growthStatus` (e.g. \"53% of plan, behind pace\"), `growthBands` (array of `{from,to,variant,label}` — error/warning/success — covering 0→max in order) · **objectives datagrid** `objRows` (array, one per strategic objective: `{obj, prog: 0-100, owner (plain string — format as the person's display name (e.g. \"Priya Nair\"); names must be plain strings, not objects: use `User.Name.value` from the SF response), due: YYYY-MM-DD, state: {value,badgeVariant}, status:{value,badgeVariant}}`) · **callout** `synthTitle`/`synthDetail` (the plan's single most important read — the long pole and the move), `ctaLabel`/`ctaMsg` (`action/sendMessage`, a first-person next-step prompt), `planUrl` (the Account/AccountPlan Lightning record URL for the \"View in Salesforce\" button).",
  "props": {
    "planTitle": {
      "description": "Page title for the account plan — name the account and plan period (e.g. FY26).",
      "type": "string",
      "example": "Account plan — Meridian Health FY26"
    },
    "headerStatus": {
      "description": "Short pace badge beside the title (e.g. \"BEHIND PACE\" / \"ON PLAN\").",
      "type": "string",
      "example": "BEHIND PACE"
    },
    "planSubtitle": {
      "description": "One-line summary caption: live ARR → target, objective count, and how many are on track.",
      "type": "string",
      "example": "$1.2M live → $3.0M target · 3 objectives · on track on 1 of 3"
    },
    "growthValue": {
      "description": "Current booked/live revenue — a raw number in the meter's unit (e.g. $M).",
      "type": "number",
      "example": 1.6
    },
    "growthMax": {
      "description": "The plan ceiling — the meter's max, a raw number in the same unit as growthValue.",
      "type": "number",
      "example": 3
    },
    "growthTarget": {
      "description": "The FY revenue target — a raw number in the same unit as growthValue.",
      "type": "number",
      "example": 3
    },
    "growthValueLabel": {
      "description": "Display string for the current value (e.g. \"$1.6M of $3.0M plan\").",
      "type": "string",
      "example": "$1.6M of $3.0M plan"
    },
    "growthTargetLabel": {
      "description": "Display string for the target (e.g. \"$3.0M FY target\").",
      "type": "string",
      "example": "$3.0M target"
    },
    "growthStatus": {
      "description": "Short pace read shown on the meter (e.g. \"53% of plan, behind pace\").",
      "type": "string",
      "example": "53% of plan, behind pace"
    },
    "growthBands": {
      "description": "Color bands for the growth meter, in order covering 0→max; each band spans a value range and sets the meter color there.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "from": {
            "description": "Band start value, in the meter's unit.",
            "type": "number"
          },
          "to": {
            "description": "Band end value, in the meter's unit.",
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
          "to": 1.8,
          "variant": "error",
          "label": "Behind"
        },
        {
          "from": 1.8,
          "to": 2.7,
          "variant": "warning",
          "label": "Near"
        },
        {
          "from": 2.7,
          "to": 3,
          "variant": "success",
          "label": "On plan"
        }
      ]
    },
    "objRows": {
      "description": "Strategic objectives — one row per objective. Empty array → the objectives datagrid is omitted.",
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
          "obj": {
            "description": "Objective name / short description.",
            "type": "string"
          },
          "prog": {
            "description": "Progress toward the objective, 0–100.",
            "type": "number"
          },
          "owner": {
            "description": "Objective owner's display name, a plain string (use User.Name.value — never a nested object).",
            "type": "string"
          },
          "due": {
            "description": "Objective due date, ISO YYYY-MM-DD.",
            "type": "string"
          },
          "state": {
            "description": "Status badge cell for the objective.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Status label shown on the badge.",
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
          "status": {
            "value": "Behind",
            "badgeVariant": "error"
          },
          "obj": "Expand to Finance BU",
          "prog": 15,
          "owner": "Priya Nair",
          "due": "2026-12-15",
          "state": {
            "value": "Not started",
            "badgeVariant": "error"
          }
        },
        {
          "status": {
            "value": "On track",
            "badgeVariant": "info"
          },
          "obj": "Land Analytics in Clinical",
          "prog": 40,
          "owner": "Priya Nair",
          "due": "2026-09-30",
          "state": {
            "value": "In discovery",
            "badgeVariant": "info"
          }
        },
        {
          "status": {
            "value": "Ahead",
            "badgeVariant": "success"
          },
          "obj": "Secure exec sponsor (CFO)",
          "prog": 90,
          "owner": "You",
          "due": "2026-08-15",
          "state": {
            "value": "Nearly there",
            "badgeVariant": "success"
          }
        }
      ]
    },
    "synthTitle": {
      "description": "Synthesis callout heading — the plan's single most important read (the long pole).",
      "type": "string",
      "example": "Finance expansion is the plan's long pole"
    },
    "synthDetail": {
      "description": "Synthesis callout body — the long pole and the recommended move.",
      "type": "string",
      "example": "Exec sponsorship is nearly locked and Clinical analytics is moving, but the Finance BU objective — the biggest chunk of the $1.4M gap — hasn't started. Open Finance discovery this quarter or the FY26 target slips."
    },
    "ctaLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft Finance discovery"
    },
    "ctaMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft a discovery request to the Meridian Health Finance BU lead, positioning Analytics expansion as cost-reduction tooling for their Q4 close cycle."
    },
    "planUrl": {
      "description": "Account/AccountPlan Lightning record URL for the \"View in Salesforce\" button.",
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
                  "align": "center",
                  "isWrapped": false
                },
                "children": [
                  {
                    "definition": "tile/icon",
                    "attributes": {
                      "name": "target",
                      "size": "xl",
                      "alt": ""
                    }
                  },
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{planTitle}}",
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
              "text": "{{planSubtitle}}",
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
              "label": "Growth to FY26 target",
              "value": "{{growthValue}}",
              "min": 0,
              "max": "{{growthMax}}",
              "target": "{{growthTarget}}",
              "valueFormat": "currency",
              "valueLabel": "{{growthValueLabel}}",
              "targetLabel": "{{growthTargetLabel}}",
              "status": "{{growthStatus}}",
              "size": "lg",
              "bands": "{{growthBands}}"
            }
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "Strategic objectives and progress",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "obj",
                  "header": "Objective",
                  "type": "text"
                },
                {
                  "key": "prog",
                  "header": "Progress",
                  "type": "databar",
                  "target": 100
                },
                {
                  "key": "owner",
                  "header": "Owner",
                  "type": "avatar"
                },
                {
                  "key": "due",
                  "header": "Due",
                  "type": "date"
                },
                {
                  "key": "state",
                  "header": "State",
                  "type": "badge"
                }
              ],
              "rows": "{{objRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "warning",
              "title": "{{synthTitle}}",
              "description": "{{synthDetail}}"
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
                      "label": "{{ctaLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{ctaMsg}}"
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
                              "url": "{{planUrl}}"
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



Markdown — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED:

```markdown
# [AccountName] — Account Plan
**Status:** [Status]  |  **Start:** [StartDate]

## Vision
[AccountVision]

## Strategic Priorities
- [AccountStrategicPriorities as bullets]

## Account
- **Challenges:** [AccountChallenges]
- **Competitors:** [AccountCompetitors]
- **Competitive strengths:** [AccountCompetitiveStrengths]
- **Competitive weaknesses:** [AccountCmptvWeaknesses]
- **Industry trends:** [AccountIndustryTrends]
- **Performance indicators:** [AccountPrfmIndicators]

## Relationship
| Strengths | Weaknesses |
|---|---|
| [RelationshipStrengths] | [RelationshipWeaknesses] |

| Opportunities | Threats |
|---|---|
| [RelationshipOpportunities] | [RelationshipThreats] |

[View in Salesforce](https://[instanceUrl]/lightning/r/AccountPlan/[Id]/view)
```

Quote any blank field as "blank" rather than omitting it. Always include the record link.
