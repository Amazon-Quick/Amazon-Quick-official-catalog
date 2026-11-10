---
name: stakeholder-map
display_name: Stakeholder Map
description: "Build a stakeholder map from Salesforce contacts and roles plus email, calendar, calls and Slack, showing influence, stance, gaps and access paths. Use to identify decision makers, assess single-threading or plan introductions. Account brief: account-context."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:d6b5da9416a1d9dbeef0dea3615b06764a89bbb3f5f92442c44d75ae6c52b2ea"
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

# Stakeholder Map

`account-context` lists contacts; this skill models the deal. Ground → (read + evidence, all in ONE turn) → classify → analyze.

## 1. Ground and resolve

Ground **only Contact** — it always exists (naming a missing custom object fails the whole call). Its fields reveal this org's role/sentiment/influence schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

For **deal scope**, run Contact ObjectInfo and one of these two resolvers in the **same tool turn (parallel)**; both list the newest close dates first. Replace `%DEALNAME%` with the deal name as the user gave it, keeping a `%` wildcard on each side. When the request names the deal's account, including as the first part of the deal name, use the rest of the deal name for `%DEALNAME%`, replace `%DEAL_ACCOUNT%` with the account name as the user gave it, and run the second resolver. Otherwise run the first:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { edges { node { Id Name { value } AccountId { value } Account { Id Name { value } } StageName { value } CloseDate { value } Owner { Id Name { value } } } } totalCount } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" }, Account: { Name: { like: \\\"%DEAL_ACCOUNT%\\\" } } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { edges { node { Id Name { value } AccountId { value } Account { Id Name { value } } StageName { value } CloseDate { value } Owner { Id Name { value } } } } totalCount } } } }\"}" })
```

- **Exactly one returned row and `totalCount = 1`** → keep its exact `Id` as `<OPPORTUNITY_ID>` and `AccountId` as `<ACCOUNT_ID>`.
- **Several rows or `totalCount > 1`** → list name, account, stage, close date, and owner and ask the user to choose. If the total exceeds the returned rows, say the list is partial and ask for a more distinctive name or the account. Do not guess.
- **No rows** → ask for a more distinctive name or the account. Do not substitute another deal.

Step 1 is the authority on names — use exact strings from it, never guess. From the result, get: (a) scalar `__c` fields (role, sentiment, influence, seniority, etc.) — take their `{ value }`; (b) any org-specific lookup's exact `relationshipName` to span for a related record's name.

## 2. Read (fill from step 1) — TWO parallel calls for deal scope, ONE for account scope

NEVER combine these into a single query. Run them as separate `dispatch_readonly` calls issued in the same turn (parallel). Combining `Contacts` + `Opportunities` with nested `OpportunityContactRoles` in one query will exceed the GraphQL parser's token limit.

**Reference-field rules (avoids the retry loop):**
- A scalar/`__c` field → `Field__c { value }`. `displayValue` is null for Id fields here — don't rely on it.
- To get a **related record's name**, span via the exact `relationshipName` from Step 1. Do NOT append `{ ... }` to a raw `Id`/`__c` field.
- Only span relationships Step 1 actually returned. No usable relationshipName → take the `__c { value }` (the Id) and move on — **do not retry**. `ReportsTo` (standard self-lookup) and the `OpportunityContactRoles`/`Contacts` child relationships below are standard — always available, no grounding needed.

Insert `<CONTACT_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed org-specific relationship.

**Deal scope**:

**Call A — OCR contacts on the deal:**

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPPORTUNITY_ID>\\\" } }, first: 1) { edges { node { Id Name { value } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Id Name { value } Title { value } Email { value } Phone { value } ReportsTo { Name { value } Title { value } } <CONTACT_CUSTOM> } } } } } } } } } }\"}" })
```

**Call B — full account contact roster (for gap analysis):**

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, first: 1) { edges { node { Id Name { value } Contacts(first: 50) { edges { node { Id Name { value } Title { value } Email { value } <CONTACT_CUSTOM> } } } } } } } } }\"}" })
```

**Account scope** (`%ACCOUNTNAME%` = 1-2 words from the account name):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNTNAME%\\\" } }, first: 1) { edges { node { Id Name { value } Contacts { edges { node { Id Name { value } Title { value } Email { value } Phone { value } ReportsTo { Name { value } Title { value } } <CONTACT_CUSTOM> <REL_BLOCKS> } } } } } } } } }\"}" })
```

Empty `edges` → broaden `%ACCOUNTNAME%`, or ask the user for the right identifier.

## 2b. Evidence (parallel with step 2 after deal resolution)

Issue Call A, Call B, and all of step 2b as tool calls in a single turn. For account scope, issue the Account read and evidence calls together.
- **email**: per contact, last exchange date and direction (did they reply?)
- **calendar**: who has actually attended meetings
- **docs**: call transcripts — who spoke, what stance they took
- **slack**: colleagues who have their own relationships at this account

Use whatever email/calendar/doc/Slack tools are available; skip silently if none are present (SFDC-only is fine). Cite source + date for anything you use.

## 3. Classify each person (cite every claim; invent nothing)

| Person | Title | Deal role | Engagement | Stance | Evidence |
|---|---|---|---|---|---|
| [name] | [title] | Champion / Economic buyer / Evaluator / Influencer / Blocker / Unknown | Active (met <14d) / Warm / Cold / Never met | 🟢 / 🟡 / 🔴 / ? | [last meeting, email reply, transcript quote] |

Rules: a "champion" must have done something for you (made an intro, shared internal info, pushed a meeting) - advocacy in one call doesn't qualify. Mark "Unknown" honestly rather than guessing stance. Required stakeholders for close and target buyer titles are external knowledge — infer from the org's own data or ask the user once, never invent.

## 4. Find the gaps and the paths

- **Missing roles:** which required stakeholders have no identified person (no economic buyer, no security/legal contact, no exec sponsor)
- **Single-thread risk:** how many people have actually engaged in the last 30 days
- **Access paths to the missing people:** who on the map reports to or works with them (via `ReportsTo`, titles), which colleague has a relationship (from Slack), whether a past champion moved into that org, what a warm intro would look like
- **Dark contacts:** people who attended meetings or appear in email threads but aren't in SFDC at all - list them for creation

## 5. Widget (default output when `display_widget` is present: Cowork/desktop/web)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left — this echo path compiles no bindings), then call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once. A value that is *only* a `{{token}}` (`xLabels`/`yLabels`/`domain`/`cells`/`rows`) becomes the typed literal — arrays stay arrays, numbers stay numbers; a `{{token}}` inside a larger string is interpolated as text. Spirit layout: header + muted one-line subhead, one heatmap (stakeholders by power × support), one stakeholders datagrid, one synthesis callout with two buttons. Cite every value; fabricate nothing — quote a blank field as blank, drop contacts you have no data for.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `{{title}}` header page-title (e.g. \"Stakeholder map — Cobalt Robotics\"); `{{subtitle}}` muted caption summarizing the map (8 contacts · 2 champions, 1 detractor · buyer engaged); `{{heatmapCaption}}` heatmap caption; `{{xLabels}}`/`{{yLabels}}` heatmap axes (x [\"Detractor\",\"Neutral\",\"Supporter\"], y [\"High power\",\"Mid power\",\"Low power\"]); `{{cells}}` array of `{ x, y, value, valueLabel }`, one per occupied cell (diverging scale, midpoint 0) — **`valueLabel` = abbreviated title or role for a single occupant (e.g. \"CEO\", \"CIO\", \"Dir Ops\", \"CFO+VP\" when two people share a cell). For cells with 3+ people use a count label (\"3 users\"). Heatmap is for spatial scan (where are supporters/detractors/gaps?), datagrid below has full names/roles/detail.**; `{{domain}}` 2-element `[min, max]` for that scale (e.g. [-2, 2]); `{{datagridCaption}}` datagrid caption; `{{rows}}` array of stakeholder objects — `name` (plain string — format as the person's display name (e.g. \"Dana Kwon\"); names must be plain strings, not objects: use `Contact.Name.value` from the SF response), `role` (text), `stance` `{ value, badgeVariant }` (success Champion, error Detractor, secondary Neutral, info Supporter), `last` (ISO `YYYY-MM-DD`), `next` (text), `status` (`{value,badgeVariant}` — value Mobilized/Risk/Uncovered/Covered, badgeVariant success/error/warning/info/default); `{{calloutTitle}}`/`{{calloutDescription}}` synthesis callout (variant error); `{{ctaPrimaryLabel}}`/`{{ctaPrimaryMsg}}` primary button (`action/sendMessage`, first-person prompt e.g. \"Draft an exec-to-exec meeting invite for…\"); `{{salesforceUrl}}` secondary \"View in Salesforce\" button (`action/openLink`, the account's Lightning URL `https://<myDomain>/lightning/r/Account/<Id>/view` — omit this button if you lack the Id). Verify before calling: no `{{…}}`/`{!…}` remain; arrays are arrays and numbers numbers; every row cites real data.",
  "props": {
    "title": {
      "description": "Header page title (e.g. \"Stakeholder map — Cobalt Robotics\").",
      "type": "string",
      "example": "Stakeholder map — Cobalt Robotics"
    },
    "subtitle": {
      "description": "Muted caption summarizing the map (contact / champion / detractor counts, buyer engagement).",
      "type": "string",
      "example": "8 contacts · 2 champions, 1 detractor · economic buyer engaged"
    },
    "heatmapCaption": {
      "description": "Caption for the power×stance heatmap.",
      "type": "string",
      "example": "Stakeholders by influence and support — top-right is a mobilized champion, bottom-right a powerful detractor to neutralize"
    },
    "xLabels": {
      "description": "Heatmap X-axis labels — stance (Detractor / Neutral / Supporter). Keep each ≤12 chars — column headers sit in narrow equal-width columns and do NOT truncate, so long labels overrun into the neighbor.",
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 12
      },
      "example": [
        "Detractor",
        "Neutral",
        "Supporter"
      ]
    },
    "yLabels": {
      "description": "Heatmap Y-axis labels — power (High / Mid / Low). Keep each ≤16 chars; long labels widen the row-label gutter and squeeze the grid.",
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 16
      },
      "example": [
        "High power",
        "Mid power",
        "Low power"
      ]
    },
    "domain": {
      "description": "Color-scale domain as [min, max] (diverging scale, e.g. [-2, 2]).",
      "type": "array",
      "items": {
        "type": "number"
      },
      "example": [
        -2,
        2
      ]
    },
    "cells": {
      "description": "One entry per occupied power×stance cell (diverging scale, midpoint 0). Omit empty cells.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "x": {
            "description": "Stance label (matches an entry in xLabels).",
            "type": "string"
          },
          "y": {
            "description": "Power label (matches an entry in yLabels).",
            "type": "string"
          },
          "value": {
            "description": "Cell value on the diverging scale — drives the color.",
            "type": "number"
          },
          "valueLabel": {
            "description": "Very short in-cell label — MUST be ≤10 chars including spaces. Heatmap cells are small and this text does NOT wrap or shrink, so anything longer runs past the cell edge. Use a terse title abbreviation (e.g. \"CEO\", \"CIO\", \"CFO+VP\", \"Dir Ops\", \"VP Sales\") — abbreviate long roles (\"Web Dev Mgr\" → \"Dev Mgr\"); for 2+ people in a cell use a count (\"2 users\"). Full names/roles live in the datagrid below.",
            "type": "string",
            "maxLength": 10
          }
        }
      },
      "example": [
        {
          "x": "Supporter",
          "y": "High power",
          "value": 2,
          "valueLabel": "CFO+VP"
        },
        {
          "x": "Neutral",
          "y": "High power",
          "value": 0,
          "valueLabel": "CEO"
        },
        {
          "x": "Detractor",
          "y": "High power",
          "value": -2,
          "valueLabel": "CIO"
        },
        {
          "x": "Supporter",
          "y": "Mid power",
          "value": 2,
          "valueLabel": "Dir Ops"
        },
        {
          "x": "Neutral",
          "y": "Mid power",
          "value": 0,
          "valueLabel": "Dir Sec"
        },
        {
          "x": "Supporter",
          "y": "Low power",
          "value": 1,
          "valueLabel": "2 users"
        },
        {
          "x": "Neutral",
          "y": "Low power",
          "value": 0,
          "valueLabel": "Analyst"
        }
      ]
    },
    "datagridCaption": {
      "description": "Caption for the stakeholder datagrid.",
      "type": "string",
      "example": "Key players, coverage and next touch"
    },
    "rows": {
      "description": "Stakeholders — one row per person. Empty array → the datagrid is omitted.",
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
            "description": "Person's display name, a plain string (use Contact.Name.value — never a nested object).",
            "type": "string"
          },
          "role": {
            "description": "Role / title (text).",
            "type": "string"
          },
          "stance": {
            "description": "Stance badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Stance label (Champion / Detractor / Neutral / Supporter).",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Badge color: success=Champion, error=Detractor, secondary=Neutral, info=Supporter.",
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
          "last": {
            "description": "Last-touch date, ISO YYYY-MM-DD.",
            "type": "string"
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
            "value": "Mobilized",
            "badgeVariant": "success"
          },
          "name": "Dana Kwon",
          "role": "CFO — econ. buyer",
          "stance": {
            "value": "Champion",
            "badgeVariant": "success"
          },
          "last": "2026-07-22",
          "next": "Confirm on price Friday"
        },
        {
          "status": {
            "value": "Mobilized",
            "badgeVariant": "success"
          },
          "name": "Raj Patel",
          "role": "VP Engineering",
          "stance": {
            "value": "Champion",
            "badgeVariant": "success"
          },
          "last": "2026-07-21",
          "next": "Arm with ROI one-pager"
        },
        {
          "status": {
            "value": "Risk",
            "badgeVariant": "error"
          },
          "name": "Lena Brooks",
          "role": "CIO",
          "stance": {
            "value": "Detractor",
            "badgeVariant": "error"
          },
          "last": "2026-07-10",
          "next": "Exec-to-exec meeting"
        },
        {
          "status": {
            "value": "Uncovered",
            "badgeVariant": "warning"
          },
          "name": "Sam Osei",
          "role": "CEO",
          "stance": {
            "value": "Neutral",
            "badgeVariant": "neutral"
          },
          "last": "2026-06-30",
          "next": "Sponsor a briefing"
        },
        {
          "status": {
            "value": "Covered",
            "badgeVariant": "info"
          },
          "name": "Mia Torres",
          "role": "Director, Ops",
          "stance": {
            "value": "Supporter",
            "badgeVariant": "info"
          },
          "last": "2026-07-19",
          "next": "Keep warm"
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the map's key gap or move.",
      "type": "string",
      "example": "The CIO can veto — and hasn't been touched in 2 weeks"
    },
    "calloutDescription": {
      "description": "Synthesis callout body.",
      "type": "string",
      "example": "Lena (CIO, high power) is the lone detractor and the CEO is neutral and uncovered. Have your exec sponsor the CFO broker a CIO meeting this week; leaving a powerful detractor unaddressed is the top risk to a clean close."
    },
    "ctaPrimaryLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft exec meeting invite"
    },
    "ctaPrimaryMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft an exec-to-exec meeting invite for the Cobalt CIO Lena Brooks, brokered by our champion Dana Kwon (CFO)."
    },
    "salesforceUrl": {
      "description": "Account Lightning URL for the secondary \"View in Salesforce\" button; omit if no Id.",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/r/Account/001XX000000abcXYZ/view"
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
                  "name": "users",
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
            "definition": "tile/heatmap",
            "attributes": {
              "layout": "matrix",
              "caption": "{{heatmapCaption}}",
              "xLabels": "{{xLabels}}",
              "yLabels": "{{yLabels}}",
              "encode": "color",
              "scale": "diverging",
              "midpoint": 0,
              "valueFormat": "number",
              "domain": "{{domain}}",
              "cells": "{{cells}}"
            }
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{datagridCaption}}",
              "appearance": "striped",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "name",
                  "header": "Stakeholder",
                  "type": "avatar"
                },
                {
                  "key": "role",
                  "header": "Role",
                  "type": "text"
                },
                {
                  "key": "stance",
                  "header": "Stance",
                  "type": "badge"
                },
                {
                  "key": "last",
                  "header": "Last touch",
                  "type": "date"
                },
                {
                  "key": "next",
                  "header": "Next move",
                  "type": "text"
                }
              ],
              "rows": "{{rows}}"
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
                              "url": "{{salesforceUrl}}"
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


## 6. Output — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Stakeholder Map: [Opp / Account]

## The map
[classification table from Step 3]

## Coverage verdict
[e.g. "Engaged with 2 of 5 required roles. Economic buyer identified but never met. Single-threaded through [name]."]

## Missing people and how to reach them
1. [Role we're missing] - likely [name/title if known] - path: [warm intro via X / champion ask / direct outreach angle]
2. ...

## Not in SFDC yet
- [Name, title, where they appeared] - offer to create as Contacts: show exactly what will be saved (name, title, email, account), write only after an explicit yes, link the created records. On a read-only connector, list them for manual add.

## This week
- [The single highest-leverage relationship action]
```
