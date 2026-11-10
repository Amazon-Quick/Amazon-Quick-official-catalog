---
name: lead-triage
display_name: Lead Triage
description: "Produce an inbound-lead priority and routing recommendation from Salesforce Lead and Account data, research and email engagement. Use when qualifying a new lead, assessing ICP fit and intent, choosing an owner or deciding the response speed and next step."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:71b6d46c29ce35fca20a09e809c37779038f5539159c74c6cc61f3cd0de667d4"
id: "ski-773aabeac93644ca84f80c80161e8e5d"
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


# Lead Triage

Ground → read Lead + Account → enrich → score → route. **No per-lead follow-ups** — the reads have the data.

## 1. Ground (hardcoded — Lead and Account)

Ground **Lead** and **Account** (for ICP fields). Both always exist. Issue these independent requests in the **same tool turn** so they run in **parallel**:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Lead\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

**If either overflows**, the result auto-persists to a temp file **outside the bash mount** — don't shell to it (`cat`/`python3`/`ls` will fail, it's not on that mount). Read it back with the Read tool only, and go straight to that — don't retry bash first. If the Read tool can't load it either, skip custom-field grounding and proceed with standard fields only; don't keep retrying.

From each response, select relevant `__c` fields by API name and label (segment, industry, employee count, lead score, MQL status, etc.) and take their `{ value }`. The `Owner` spans below are standard and hardcoded.

## 2. Read lead + matching account (templated, one turn)

Fire these as tool calls in **one turn** (independent). Insert `<LEAD_CUSTOM>` = confirmed scalar `__c` fields on Lead, `<ACCOUNT_CUSTOM>` = confirmed scalar `__c` fields on Account.

**Lead (by identifier user provided — Id, email, or name+company):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Lead(where: { <LEAD_FILTER> }, first: 1) { edges { node { Id Name { value } Company { value } Title { value } Email { value } LeadSource { value } Status { value } CreatedDate { value } <LEAD_CUSTOM> Owner { ... on User { Name { value } } ... on Group { Name { value } } } } } } } } }\"}" })
```

**Account (by company name or domain):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { or: [{ Name: { like: \\\"%<COMPANY>%\\\" } }, { Website: { like: \\\"%<DOMAIN>%\\\" } }] }, first: 5) { edges { node { Id Name { value } Type { value } <ACCOUNT_CUSTOM> Owner { Name { value } } } } } } } }\"}" })
```

`<LEAD_FILTER>` = build from user input: `Id: { eq: "<id>" }` OR `Email: { eq: "<email>" }` OR `and: [{ Name: { like: "%<name>%" } }, { Company: { like: "%<company>%" } }]`

If Account exists with Owner → existing relationship, routing = coordinate with that owner.

**Web research (parallel with SF reads):** Use web search/fetch if available to find company size, industry, funding, recent news. Fire in SAME turn as SF reads. If tools absent, skip silently.

**Email search (parallel):** Use email search if available to find prior threads from this domain. Fire in SAME turn. If tool absent, skip silently.

## 3. Score ICP fit

Against ICP (ask user once if not inferrable from org data):

| Dimension | Fit | Evidence |
|---|---|---|
| Industry | ✅ / ⚠️ / ❌ | [from Account/web] |
| Size | ✅ / ⚠️ / ❌ | [from Account custom/web] |
| Persona (title) | ✅ / ⚠️ / ❌ | [from Lead.Title] |
| Disqualifiers | ✅ none / ❌ [which] | [check against ICP] |

## 4. Score intent

| Signal | Strength |
|---|---|
| Source quality | High (demo request, referral) / Med (content, event) / Low (list, cold) |
| Message specificity | Specific use case / Generic interest / None |
| Prior engagement | Email thread / SFDC history / None |
| Timing trigger | Recent funding, hiring, exec change / None |

## 5. Assign priority

Calibration: P0 ≈ top 20%, P1 ≈ next 25%, P2 ≈ remaining.

- **P0:** Strong ICP fit AND high intent (specific ask, demo request, or hot trigger)
- **P1:** Strong fit with medium intent, OR moderate fit with high intent
- **P2:** Moderate fit with low intent, or fit unclear
- **DQ:** Hard disqualifier hit

Override: if Account exists with owner → routing = "coordinate with [owner]"


## 6. Render

Call `display_widget` now with the data you collected. Do not write markdown first — call immediately. Only fall back to markdown if the tool is unavailable.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below. Call `display_widget` in **dynamic** mode with it. It is a skeleton: replace every `{{token}}` placeholder with a fully-resolved literal computed from the leads you scored — this echo path does no expression compilation, so no `{!…}` bindings.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): The widget template is embedded below. Call `display_widget` in **dynamic** mode with it. It is a skeleton: replace every `{{token}}` placeholder with a fully-resolved literal computed from the leads you scored — this echo path does no expression compilation, so no `{!…}` bindings.\n- **Header** — an icon, page-title text (`{{headerTitle}}`), with a one-line caption subhead (`{{headerSubtitle}}`) summarizing the leads (scored by fit and intent · tier counts) and a separator.\n- **Tier donut + its written breakdown** — a piechart (donut, \"Leads by tier\", `{{slices}}` with Hot/Warm/Nurture counts, center shows `{{centerValue}}` \"New leads\") paired in a row with a text column to its right (`{{donutAsideTitle}}` section-title + `{{donutAside}}` body). The donut runs with `showLegend:false`, so `{{donutAside}}` must name every slice with its count (and %) in prose — it replaces the legend, and a colorblind reader relies on it. Keep it to one sentence (~18–32 words) that leads with the insight, not a bare list.\n- **Source column chart, full-width** — preceded by a caption pair (`{{chartAsideTitle}}` section-title + `{{chartAside}}` body, one-sentence takeaway), then the column chart itself full-width (\"Leads by source\", `{{categories}}` on x-axis, `{{series}}` data, `valueFormat:\"number\"`, `showValues:true`, `showLegend:false`). A column chart must be full-width to keep its axis, value labels, and bar height legible — never put it in a shared row.\n- **Hot leads datagrid** (`{{hotRows}}`) — one row per hot lead. Columns: Lead (text), Company (text), Fit score (databar, target 100, sortable), Source (badge), Next step (text). Every row carries a leading `status` object (`{value,badgeVariant}` — value Hot, badgeVariant success); the leading Status column reads each row's `status`. `totalRows` shows the full lead count.\n- **One synthesis callout** (`variant:\"info\"`) — `{{calloutTitle}}` (the queue's single most important read) and `{{calloutDescription}}`. It carries two real buttons: a primary \"Draft outreach to both\" (`{{ctaPrimaryLabel}}` / `{{ctaPrimaryMsg}}`, `action/sendMessage`) and a secondary \"View in Salesforce\" (`{{salesforceUrl}}`, `action/openLink`).\n1. Start from the embedded template above — a valid-JSON widget-definition envelope whose leaf values carry `{{token}}` placeholders.\n2. Resolve every `{{token}}`. A value that is **only** a `{{token}}` (piechart `slices`, chart `categories` and `series`, datagrid `rows`, `totalRows`, `centerValue`) becomes the resolved **typed** literal — numbers stay numbers, arrays stay arrays. A `{{token}}` **inside** a larger string is interpolated as text.\n3. `{{slices}}` is an array of slice objects — each with `label`, `value`, and optionally `role:\"highlight\"` (for Hot). `{{categories}}` is an array of source names. `{{series}}` is an array with one series object carrying `name` and `data` (array of numbers).\n4. `{{hotRows}}` is an array of lead objects — each with `lead` (name), `co` (company), `score` (number 0-100), `src` (`{ value, badgeVariant }`), `next` (next step text), and `status` (`{value,badgeVariant}` — value Hot, badgeVariant success).\n5. The result is hydrated widget definition (no `{{…}}` placeholders remain). Then call:\n- Resolve every `{{token}}` to a literal before calling — numbers stay numbers (`{{totalRows}}`, `{{centerValue}}`, each row's `score`, each slice's `value`, chart `data` numbers), arrays stay arrays (`{{slices}}`, `{{categories}}`, `{{series}}`, `{{hotRows}}`), strings stay strings.\n- Aside text: `{{donutAsideTitle}}` / `{{donutAside}}` describe the tier donut (donutAside states each slice's count and % in words, since the legend is off); `{{chartAsideTitle}}` / `{{chartAside}}` sit above the source chart (chartAside interprets the shape — which sources dominate — rather than re-listing every bar). All four are plain strings computed from the same counts you charted. Do not repeat the callout's specific claims.\n- Callout buttons: the primary is `action/sendMessage` with a first-person `content` prompt (`{{ctaPrimaryMsg}}`, e.g. \"Draft outreach to Beacon Health...\"); the secondary is `action/openLink` with `{{salesforceUrl}}` — the Leads list view Lightning URL (`https://<myDomain>/lightning/o/Lead/list`), opening a new tab.",
  "props": {
    "headerTitle": {
      "description": "Page title for lead triage.",
      "type": "string",
      "example": "Lead triage — 23 new leads this week"
    },
    "headerSubtitle": {
      "description": "Caption: leads scored by fit and intent, with tier counts.",
      "type": "string",
      "example": "Scored by fit and intent · 5 hot, 9 warm, 9 nurture"
    },
    "centerValue": {
      "description": "Donut center value — the new-lead total.",
      "type": "string",
      "example": "23"
    },
    "slices": {
      "description": "Leads by tier — one slice per tier (Hot / Warm / Nurture). Empty array → the donut is omitted.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "label": {
            "description": "Tier label.",
            "type": "string"
          },
          "value": {
            "description": "Lead count in this tier.",
            "type": "number"
          },
          "role": {
            "description": "Optional emphasis; set \"highlight\" on Hot.",
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
          "label": "Hot",
          "value": 5,
          "role": "highlight"
        },
        {
          "label": "Warm",
          "value": 9
        },
        {
          "label": "Nurture",
          "value": 9
        }
      ]
    },
    "donutAsideTitle": {
      "description": "Section title beside the tier donut.",
      "type": "string",
      "example": "Tier breakdown"
    },
    "donutAside": {
      "description": "One-sentence written breakdown of the donut — names each slice's count and % (replaces the off legend).",
      "type": "string",
      "example": "Only 5 of the 23 leads are hot (22%). Warm and nurture each hold 9 leads (39%), so 18 sit below sales-ready and need working before they convert."
    },
    "chartAsideTitle": {
      "description": "Section title above the source chart.",
      "type": "string",
      "example": "Where leads originate"
    },
    "chartAside": {
      "description": "One-sentence takeaway interpreting which sources dominate.",
      "type": "string",
      "example": "Webinar and inbound demo produce 13 of 23 leads, over half; the other three sources trail to referral's 2, so most new leads trace to those top two channels."
    },
    "categories": {
      "description": "Lead-source names for the chart's x-axis.",
      "type": "array",
      "items": {
        "type": "string"
      },
      "example": [
        "Webinar",
        "Inbound demo",
        "Content",
        "Event",
        "Referral"
      ]
    },
    "series": {
      "description": "Source-chart series — one object {name, data}.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "description": "Series name.",
            "type": "string"
          },
          "data": {
            "description": "Lead counts per source — a number array matching categories.",
            "type": "array",
            "items": {
              "type": "number"
            }
          }
        }
      },
      "example": [
        {
          "name": "Leads",
          "data": [
            7,
            6,
            5,
            3,
            2
          ]
        }
      ]
    },
    "totalRows": {
      "description": "Full lead count (number).",
      "type": "number",
      "example": 23
    },
    "hotRows": {
      "description": "Hot leads — one row per lead. Empty array → the datagrid is omitted.",
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
          "lead": {
            "description": "Lead name.",
            "type": "string"
          },
          "co": {
            "description": "Company.",
            "type": "string"
          },
          "score": {
            "description": "Fit score, 0–100 (feeds the databar).",
            "type": "number"
          },
          "src": {
            "description": "Source badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Source label.",
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
          "next": {
            "description": "Next step (text).",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Hot",
            "badgeVariant": "success"
          },
          "lead": "J. Okafor",
          "co": "Beacon Health",
          "score": 92,
          "src": {
            "value": "Inbound demo",
            "badgeVariant": "success"
          },
          "next": "Call today — requested pricing"
        },
        {
          "status": {
            "value": "Hot",
            "badgeVariant": "success"
          },
          "lead": "P. Nardi",
          "co": "Orbit Logistics",
          "score": 85,
          "src": {
            "value": "Referral",
            "badgeVariant": "info"
          },
          "next": "Warm intro from Cobalt"
        },
        {
          "status": {
            "value": "Hot",
            "badgeVariant": "success"
          },
          "lead": "S. Realm",
          "co": "Vantage Retail",
          "score": 78,
          "src": {
            "value": "Webinar",
            "badgeVariant": "neutral"
          },
          "next": "Book discovery"
        },
        {
          "status": {
            "value": "Hot",
            "badgeVariant": "success"
          },
          "lead": "M. Cho",
          "co": "Delta Freight",
          "score": 71,
          "src": {
            "value": "Event",
            "badgeVariant": "neutral"
          },
          "next": "Send case study"
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the queue's single most important read.",
      "type": "string",
      "example": "Two hot leads can't wait"
    },
    "calloutDescription": {
      "description": "Synthesis callout body.",
      "type": "string",
      "example": "Beacon Health asked for pricing (score 92) and Orbit is a warm referral from your Cobalt champion. Call both today; the other three hot leads can take a same-week discovery booking."
    },
    "ctaPrimaryLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft outreach to both"
    },
    "ctaPrimaryMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft outreach to Beacon Health (J. Okafor) requesting pricing and Orbit Logistics (P. Nardi) following up on the warm referral from Cobalt."
    },
    "salesforceUrl": {
      "description": "Leads list-view Lightning URL for the secondary button (action/openLink).",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/o/Lead/list"
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
                  "name": "user",
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
                      "caption": "Leads by tier",
                      "variant": "donut",
                      "valueFormat": "number",
                      "showLegend": false,
                      "centerLabel": "New leads",
                      "centerValue": "{{centerValue}}",
                      "slices": "{{slices}}"
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
              "caption": "Leads by source",
              "categories": "{{categories}}",
              "series": "{{series}}",
              "valueFormat": "number",
              "showValues": true,
              "showLegend": false
            }
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "Work these first — hot leads by score",
              "appearance": "striped",
              "defaultSort": {
                "key": "score",
                "direction": "desc"
              },
              "totalRows": "{{totalRows}}",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "lead",
                  "header": "Lead",
                  "type": "text"
                },
                {
                  "key": "co",
                  "header": "Company",
                  "type": "text"
                },
                {
                  "key": "score",
                  "header": "Fit score",
                  "type": "databar",
                  "target": 100,
                  "sortable": true
                },
                {
                  "key": "src",
                  "header": "Source",
                  "type": "badge"
                },
                {
                  "key": "next",
                  "header": "Next step",
                  "type": "text"
                }
              ],
              "rows": "{{hotRows}}"
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

What each block shows, from data you already have — a synthesis-forward layout: a header, two charts, one datagrid, and one recommendation. Not a dashboard.

- **Header** — an icon, page-title text (`{{headerTitle}}`), with a one-line caption subhead (`{{headerSubtitle}}`) summarizing the leads (scored by fit and intent · tier counts) and a separator.
- **Tier donut + its written breakdown** — a piechart (donut, "Leads by tier", `{{slices}}` with Hot/Warm/Nurture counts, center shows `{{centerValue}}` "New leads") paired in a row with a text column to its right (`{{donutAsideTitle}}` section-title + `{{donutAside}}` body). The donut runs with `showLegend:false`, so `{{donutAside}}` must name every slice with its count (and %) in prose — it replaces the legend, and a colorblind reader relies on it. Keep it to one sentence (~18–32 words) that leads with the insight, not a bare list.
- **Source column chart, full-width** — preceded by a caption pair (`{{chartAsideTitle}}` section-title + `{{chartAside}}` body, one-sentence takeaway), then the column chart itself full-width ("Leads by source", `{{categories}}` on x-axis, `{{series}}` data, `valueFormat:"number"`, `showValues:true`, `showLegend:false`). A column chart must be full-width to keep its axis, value labels, and bar height legible — never put it in a shared row.
- **Hot leads datagrid** (`{{hotRows}}`) — one row per hot lead. Columns: Lead (text), Company (text), Fit score (databar, target 100, sortable), Source (badge), Next step (text). Every row carries a leading `status` object (`{value,badgeVariant}` — value Hot, badgeVariant success); the leading Status column reads each row's `status`. `totalRows` shows the full lead count.
- **One synthesis callout** (`variant:"info"`) — `{{calloutTitle}}` (the queue's single most important read) and `{{calloutDescription}}`. It carries two real buttons: a primary "Draft outreach to both" (`{{ctaPrimaryLabel}}` / `{{ctaPrimaryMsg}}`, `action/sendMessage`) and a secondary "View in Salesforce" (`{{salesforceUrl}}`, `action/openLink`).

**Hydration rules:**
1. Start from the embedded template above — a valid-JSON widget-definition envelope whose leaf values carry `{{token}}` placeholders.
2. Resolve every `{{token}}`. A value that is **only** a `{{token}}` (piechart `slices`, chart `categories` and `series`, datagrid `rows`, `totalRows`, `centerValue`) becomes the resolved **typed** literal — numbers stay numbers, arrays stay arrays. A `{{token}}` **inside** a larger string is interpolated as text.
3. `{{slices}}` is an array of slice objects — each with `label`, `value`, and optionally `role:"highlight"` (for Hot). `{{categories}}` is an array of source names. `{{series}}` is an array with one series object carrying `name` and `data` (array of numbers).
4. `{{hotRows}}` is an array of lead objects — each with `lead` (name), `co` (company), `score` (number 0-100), `src` (`{ value, badgeVariant }`), `next` (next step text), and `status` (`{value,badgeVariant}` — value Hot, badgeVariant success).
5. The result is hydrated widget definition (no `{{…}}` placeholders remain). Then call:

```
display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated renderer.json> })
```

**Binding rules:**
- Resolve every `{{token}}` to a literal before calling — numbers stay numbers (`{{totalRows}}`, `{{centerValue}}`, each row's `score`, each slice's `value`, chart `data` numbers), arrays stay arrays (`{{slices}}`, `{{categories}}`, `{{series}}`, `{{hotRows}}`), strings stay strings.
- Piechart `slices`: each slice has `label`, `value` (number), and optionally `role:"highlight"` for the Hot tier.
- Chart `series`: array with one object `{ name: "Leads", data: [array of numbers] }` matching the `categories` count.
- Aside text: `{{donutAsideTitle}}` / `{{donutAside}}` describe the tier donut (donutAside states each slice's count and % in words, since the legend is off); `{{chartAsideTitle}}` / `{{chartAside}}` sit above the source chart (chartAside interprets the shape — which sources dominate — rather than re-listing every bar). All four are plain strings computed from the same counts you charted. Do not repeat the callout's specific claims.
- `datagrid` rows: one per hot lead. `score` is a raw number (0-100) — the databar fills against `target:100`. The Source badge (`src.badgeVariant`) reflects source quality — `"success"` (Inbound demo, Referral), `"info"`, or `"secondary"` (Webinar, Event, Content). `status` fills the leading Status column.
- Callout buttons: the primary is `action/sendMessage` with a first-person `content` prompt (`{{ctaPrimaryMsg}}`, e.g. "Draft outreach to Beacon Health..."); the secondary is `action/openLink` with `{{salesforceUrl}}` — the Leads list view Lightning URL (`https://<myDomain>/lightning/o/Lead/list`), opening a new tab.

**Numeric score — Quick/Kiro adaptation:** Treat each row's `score` as optional. Populate it only from a queried numeric field whose grounded label explicitly means Lead Score or Fit Score, or from a deterministic formula supplied by the user with its inputs and arithmetic shown. CRM Rating, P-level, qualitative ICP fit, and model judgment do not become a numeric score. If neither source exists, omit `score` from every row, remove the Fit score column and its `defaultSort`, and change the datagrid caption to `Prioritized leads`; never estimate, normalize, or display a percentage of target.

**Tier mapping — Quick/Kiro adaptation:** Do not translate P0/P1/P2/DQ, CRM Rating, or qualitative ICP fit into Hot/Warm/Nurture without an explicit user- or team-supplied mapping. When no mapping exists, remove the top-level tier-donut row containing `tile/piechart` and remove the Hot-leads datagrid before calling `display_widget`; keep the source chart, and state the exact P-level and qualitative ICP fit in `headerSubtitle` and the callout. Removing those blocks is not an error or fallback condition: call `display_widget` with the remaining blocks and emit no markdown result. Do not claim Hot, Warm, or Nurture as a derived tier. A queried CRM Rating may appear only when explicitly labeled `CRM Rating`; it must not determine priority, qualitative fit, numeric score, tier, SLA, or action.

- No fabricated content — quote blank fields as blank rather than inventing them; drop leads you have no data for.




## 7. Output

```
# Lead Triage: [Name] @ [Company]

**Priority: P[0/1/2/DQ]**
[One-sentence rationale]

## CRM Status
[Net new | OR | Account exists - owned by [Name], coordinate first]

## ICP Fit: [Strong / Moderate / Poor]
[fit table]

## Intent: [High / Medium / Low]
[intent table]

## Recommended Action
- **Route to:** [self / named owner / DQ queue]
- **Response SLA:** [P0: same day / P1: 48h / P2: this week]
- **First touch:** [e.g. "draft-outreach with [hook]" or "send qualification questions" or "DQ - reply with polite no"]

## Suggested SFDC updates
[Apply with write skills, or manually if read-only.]
- Lead Status → [value]
- Lead Owner → [name]
- [Notes field] → "[triage summary]"
```

If routing to teammate, offer to draft Slack message to lead-handoff channel (ask user for channel if not known).
