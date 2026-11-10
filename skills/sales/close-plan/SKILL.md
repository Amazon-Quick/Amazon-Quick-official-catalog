---
name: close-plan
display_name: Close Plan
description: "Build a customer-facing business case and dated mutual action plan from Salesforce opportunity data plus transcripts, email, documents, and Slack. Use to frame why buy and why now, quantify return, map the path to signature, or test the close date."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:93262702caf8ad1658e57b5da37a3af2524256359ecfaf49f3164188348b84db"
id: "ski-4197dd884d80485183232be87085cd92"
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


# Close Plan

Ground + find the deal (one turn) → read the selected opp + gather evidence (one turn) → draft business case + MAP.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists. Its fields reveal this org's real custom and lookup schema; don't assume object names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

From the result: (a) scalar `__c` fields (business-case data, why-now, ROI, etc.) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's Name. The standard contact-role child is hardcoded below.

## 2. Find the deal, then read opp + evidence

**Find the deal (same turn as step 1).** If the user gave an Opportunity Id (prefix `006`), skip this lookup and use it as `<OPP_ID>`. Otherwise run one of the two candidate reads below; both list the newest close dates first. Replace `%DEALNAME%` with the deal name as the user gave it, keeping a `%` wildcard on each side. When the request names the deal's account, including as the first part of the deal name, use the rest of the deal name for `%DEALNAME%`, replace `%ACCOUNTNAME%` with the account name as the user gave it, and run the second read. Otherwise run the first:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Account { Name { value } } } } totalCount } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" }, Account: { Name: { like: \\\"%ACCOUNTNAME%\\\" } } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Account { Name { value } } } } totalCount } } } }\"}" })
```

- **Exactly one returned row and `totalCount = 1`** → take its Id as `<OPP_ID>` and continue.
- **Several rows or `totalCount > 1`** → list only Account · Opportunity · Stage · Amount · Close date and ask which deal the user means. If the total exceeds the returned rows, say the list is partial and ask for a more distinctive name, the account, or the exact Id. Do not guess and do not run the opp read yet.
- **No rows** → ask for a more distinctive name, the account, or the exact Opportunity Id. Do not substitute another deal.

**Read the selected opp + evidence (issue ALL in one turn).** Reference-field rules: scalar → `Field__c { value }`; related name → span via the exact `relationshipName`: `<relationshipName> { Name { value } }`. Only span relationships Step 1 returned. If no usable relationshipName, take the `__c { value }` (the Id) and move on.

Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed custom lookup relationship. Standard fields + `OpportunityContactRoles` always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } Description { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } <REL_BLOCKS> OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } } } } } } }\"}" })
```

No row → say the deal could not be read and ask the user to confirm the Id or access; never fall back to another candidate.

**Evidence (in PARALLEL with the opp read — same turn):** Fire email/doc/Slack searches keyed on the selected deal and account names; these don't depend on the opp read's result. Use whatever tools are present; if none, skip silently.

- **Call transcripts / proposals:** customer's stated problems, success metrics, quantified pain, who said what.
- **Email:** commitments already made in writing, procurement/legal/security threads.
- **Slack:** internal deal-desk/exec mentions, concerns.
- **deal-advance-gap output** (if run this session): its known gaps feed the mutual action plan directly — don't re-derive them.

## 3. Draft business case

**Value prop, differentiators, required stakeholders for close, and internal approval chain are external knowledge — infer from the org's own data or ask the user once. Never invent it.**

In the customer's language, grounded in their own words (cite the call/email each point comes from):

1. **Current state and cost of it** - the problem as they described it, quantified where they gave numbers
2. **Desired outcome** - their success metrics, their timeline drivers (the why-now)
3. **Proposed solution** - what they're buying, mapped to each outcome
4. **Investment and return** - price vs. the quantified value; keep the math simple and attributable
5. **Risk of waiting** - what the delay costs in their terms
6. **Why us** - only differentiators they have actually reacted to

Flag every claim that has no customer evidence behind it — those are the points to validate on the next call, not assert in the doc.

## 4. Draft mutual action plan

Work backward from the target signature date (default: opportunity CloseDate) through both sides' steps: remaining validation, security review, legal redlines, procurement, signatures, plus any internal approvals the user mentions. Each row: step, owner (us / customer / named person), target date, status. Flag the steps whose dates make the CloseDate impossible.

## 5. Widget (default output when `display_widget` is present: Cowork/desktop/web)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left), then call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once. A value that is *only* a `{{token}}` (meter arrays, datagrid rows) becomes the typed literal — arrays stay arrays, numbers stay numbers; a `{{token}}` inside a larger string is interpolated as text. No fabricated content: blank fields stay blank, drop steps with no data.

Layout (editorial restraint, one chart): header (check-circle icon + serif title + status badge) → subhead caption → one meter (close-plan progress) → path-to-signature datagrid → one `variant:"error"` synthesis callout with two buttons.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `planTitle` (header title, \"Mutual close plan — [Account]\") + `headerStatus` (header badge, e.g. \"6 DAYS OUT\") · `subtitle` (one line: amount, target close, days out, steps done) · meter — `progressValue`/`progressMax`/`progressTarget` (numbers), `progressValueLabel`/`progressTargetLabel`/`progressStatus` (strings), `progressBands` (array of `{ from, to, variant, label }`, variants warning/success, covering 0→max in order) · `pathRows` (datagrid array, one row per action-plan step, each `{ step, side:{value,badgeVariant}, owner (plain string — format as the person's display name (e.g. \"R. Chen\"); names must be plain strings, not objects: use `Contact.Name.value` or `User.Name.value` from the SF response), due (ISO YYYY-MM-DD), state:{value,badgeVariant}, status:{value,badgeVariant} (value Critical/At risk/On track/Target, badgeVariant error/warning/info/default) }`; the leading Status column reads each row's `status`; Side badgeVariant primary=Us / secondary=Them / info=Both; State badgeVariant error=Due today/Critical, warning=In review/Waiting/At risk, info=Scheduled, secondary=Target/On track) · callout — `calloutTitle` (headline blocker), `calloutDesc` (cost if it slips), primary button `ctaLabel`/`ctaMsg` (`action/sendMessage`, first-person prompt), secondary `oppUrl` (`action/openLink`, `https://<myDomain>/lightning/r/Opportunity/<Id>/view` — omit if no Id). Before calling: no `{{…}}`/`{!…}` remain, meter is the only chart, every button is `action/sendMessage` or `action/openLink` with real content.",
  "props": {
    "planTitle": {
      "description": "Header title — \"Mutual close plan — [Account]\".",
      "type": "string",
      "example": "Mutual close plan — Cobalt Robotics"
    },
    "headerStatus": {
      "description": "Header urgency badge (e.g. \"6 DAYS OUT\").",
      "type": "string",
      "example": "6 DAYS OUT"
    },
    "subtitle": {
      "description": "One-line summary: amount, target close date, days out, steps done.",
      "type": "string",
      "example": "$1.8M · target close Jul 30 · 6 days out · 4 of 9 steps done"
    },
    "progressValue": {
      "description": "Steps completed (weighted progress) — the meter's current value.",
      "type": "number",
      "example": 4
    },
    "progressMax": {
      "description": "Total steps — the meter's max.",
      "type": "number",
      "example": 9
    },
    "progressTarget": {
      "description": "Target progress marker on the meter.",
      "type": "number",
      "example": 9
    },
    "progressValueLabel": {
      "description": "Display string for current progress (e.g. \"4 of 7 steps\").",
      "type": "string",
      "example": "4 of 9 steps complete"
    },
    "progressTargetLabel": {
      "description": "Display string for the target.",
      "type": "string",
      "example": "9 to sign"
    },
    "progressStatus": {
      "description": "Short progress read shown on the meter.",
      "type": "string",
      "example": "on the critical path"
    },
    "progressBands": {
      "description": "Color bands for the progress meter, in order covering 0→max.",
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
          "to": 5,
          "variant": "warning",
          "label": "In progress"
        },
        {
          "from": 5,
          "to": 9,
          "variant": "success",
          "label": "Closing"
        }
      ]
    },
    "pathRows": {
      "description": "Mutual action-plan steps — one row per step. Empty array → the datagrid is omitted.",
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
          "step": {
            "description": "The action-plan step / task.",
            "type": "string"
          },
          "side": {
            "description": "Which side owns the step (badge cell).",
            "type": "object",
            "properties": {
              "value": {
                "description": "Side label — Us / Them / Both.",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Side badge color: primary=Us, secondary=Them, info=Both.",
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
          "owner": {
            "description": "Step owner's display name, a plain string (use Contact.Name.value or User.Name.value — never a nested object).",
            "type": "string"
          },
          "due": {
            "description": "Step due date, ISO YYYY-MM-DD.",
            "type": "string"
          },
          "state": {
            "description": "Step status badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Status label (e.g. \"Due today\", \"Scheduled\", \"On track\").",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Status badge color: error=Due today/Critical, warning=In review/Waiting/At risk, info=Scheduled, secondary=Target/On track.",
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
            "value": "Critical",
            "badgeVariant": "error"
          },
          "step": "Send redlined MSA",
          "side": {
            "value": "Us",
            "badgeVariant": "neutral"
          },
          "owner": "You",
          "due": "2026-07-24",
          "state": {
            "value": "Due today",
            "badgeVariant": "error"
          }
        },
        {
          "status": {
            "value": "At risk",
            "badgeVariant": "warning"
          },
          "step": "Security review sign-off",
          "side": {
            "value": "Them",
            "badgeVariant": "neutral"
          },
          "owner": "R. Chen",
          "due": "2026-07-25",
          "state": {
            "value": "In review",
            "badgeVariant": "warning"
          }
        },
        {
          "status": {
            "value": "On track",
            "badgeVariant": "info"
          },
          "step": "CFO final price approval",
          "side": {
            "value": "Us",
            "badgeVariant": "neutral"
          },
          "owner": "M. Lee",
          "due": "2026-07-26",
          "state": {
            "value": "Scheduled",
            "badgeVariant": "info"
          }
        },
        {
          "status": {
            "value": "At risk",
            "badgeVariant": "warning"
          },
          "step": "Legal redlines returned",
          "side": {
            "value": "Them",
            "badgeVariant": "neutral"
          },
          "owner": "Buyer legal",
          "due": "2026-07-28",
          "state": {
            "value": "Waiting",
            "badgeVariant": "warning"
          }
        },
        {
          "status": {
            "value": "At risk",
            "badgeVariant": "warning"
          },
          "step": "Procurement PO",
          "side": {
            "value": "Them",
            "badgeVariant": "neutral"
          },
          "owner": "Buyer",
          "due": "2026-07-29",
          "state": {
            "value": "Waiting",
            "badgeVariant": "warning"
          }
        },
        {
          "step": "Signature",
          "side": {
            "value": "Both",
            "badgeVariant": "info"
          },
          "owner": "Dana Kwon",
          "due": "2026-07-30",
          "state": {
            "value": "Target",
            "badgeVariant": "neutral"
          }
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the headline blocker.",
      "type": "string",
      "example": "Redlines are due today and gate everything after"
    },
    "calloutDesc": {
      "description": "Synthesis callout body — the cost if the deal slips.",
      "type": "string",
      "example": "The MSA hasn't gone out and four downstream steps wait on it. Send it this morning; if it slips a day, the Jul 30 signature date is no longer realistic and the deal moves to next quarter."
    },
    "ctaLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft MSA send"
    },
    "ctaMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft a note to legal and the Cobalt legal counterpart attaching the redlined MSA, flagging that security review and procurement both wait on this, with Jul 30 close date."
    },
    "oppUrl": {
      "description": "Opportunity Lightning URL for the secondary \"View in Salesforce\" button (action/openLink); omit if no Id.",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/r/Opportunity/006AX00000M8k2pYAD/view"
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
                      "name": "check-circle",
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
              "label": "Close plan progress",
              "value": "{{progressValue}}",
              "min": 0,
              "max": "{{progressMax}}",
              "target": "{{progressTarget}}",
              "valueFormat": "number",
              "valueLabel": "{{progressValueLabel}}",
              "targetLabel": "{{progressTargetLabel}}",
              "status": "{{progressStatus}}",
              "size": "lg",
              "bands": "{{progressBands}}"
            }
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "Path to signature, by date",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "step",
                  "header": "Step",
                  "type": "text"
                },
                {
                  "key": "side",
                  "header": "Side",
                  "type": "badge"
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
              "rows": "{{pathRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "error",
              "title": "{{calloutTitle}}",
              "description": "{{calloutDesc}}"
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
                              "url": "{{oppUrl}}"
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
# Close Plan: [Opp Name] - [Account]

## Business Case (customer-facing doc)

### Current State
[Problem as they described it, quantified where they gave numbers]

### Desired Outcome
[Their success metrics, their timeline drivers]

### Proposed Solution
[What they're buying, mapped to each outcome]

### Investment and Return
[Price vs. quantified value — simple math, attributable]

### Risk of Waiting
[What the delay costs in their terms]

### Why Us
[Only differentiators they reacted to]

**Claims to validate:** [Every claim with no customer evidence]

## Mutual Action Plan (shared table)

| Step | Owner | Target Date | Status |
|------|-------|-------------|--------|
| [Remaining validation] | [us/customer/name] | [date] | [status] |
| [Security review] | | | |
| [Legal redlines] | | | |
| [Procurement] | | | |
| [Signatures] | | | |
| [Internal approvals] | | | |

**Date conflicts:** [Steps whose dates make CloseDate impossible]

## Suggested SFDC updates
- NextStep → "[next dated step from the plan]"
- CloseDate → [if backward plan says current date not credible]
[Apply with `update-opportunity`, or manually if read-only.]

## Draft email to champion
[Sharing the action plan and asking them to confirm owners on their side]
```

**Offer to create the artifacts as shareable documents** if a docs connector is present (capability call, not an SF read — skip silently if absent): the business case as a customer-facing doc, and the mutual action plan as a co-ownable table. Degrade to the inline markdown above when no docs tool is available.
