---
name: deal-review
description: "Build a scored deal-health assessment from Salesforce fields, contacts and activity plus email, documents and Slack, with evidence-backed risks. Use to judge whether one deal will close; for stage-exit gaps and a sequenced path, use deal-advance-gap."
checksum: "sha256:dbac1a9e8782cc847d1cdcb54a17506c8870567833a4cd33e7b464ed8f18f7d1"
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


# Deal Review

Ground → (read + evidence searches, all in ONE turn) → analyze.

## 1. Ground (hardcoded — Opportunity only)

Ground `Opportunity`. Its fields reveal this org's custom deal signals; the fixed standard history query below needs no metadata.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } stages: objectInfos(objectInfoInputs: [{ apiName: \\\"Opportunity\\\", recordTypeIDs: [\\\"012000000000000AAA\\\"], fieldNames: [\\\"StageName\\\"] }]) { fields { ApiName ... on PicklistField { picklistValuesByRecordTypeIDs { recordTypeID picklistValues { label value } } } } } } }\"}" })
```

Step 1 is the authority on names — use exact strings from it, never guess. Select relevant `__c` fields (health, next-step, exec-sponsor, forecast, risk signals, etc.) as `{ value }` and keep each field's `label`. **Build an ApiName→label map now and use the `label` in ALL output** (e.g. render `Executive_Sponsor__c` as "Executive Sponsor", `Health_Score__c` as "Health Score") — never print a `__c` API name to the user.

**Stage order — local correction:** `stages` lists the Stage picklist in the org's order, read from the primary record type (`012000000000000AAA`). Take `kpiStageNum` from the deal's position in it (two digits, for example `04`) and `kpiStageSub` from the stages after it up to and including Closed Won (for example, "5 stages to close"). Never infer either from general sales knowledge.

## 2. Read (fill from step 1)

`%DEALNAME%` = 1–2 words. A confirmed `__c` field → `Field__c { value }`; do not invent or span custom relationships.

Insert `<OPP_CUSTOM>` = relevant confirmed `__c { value }` fields. Standard fields and `OpportunityContactRoles` always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 1) { totalCount edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } CreatedDate { value } Type { value displayValue } Probability { value } ForecastCategory { value } NextStep { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } Tasks(first: 15, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Status { value } Description { value } TaskSubtype { value } } } } Events(first: 10, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } OpportunityHistories(first: 200, orderBy: { CreatedDate: { order: DESC } }) { edges { node { CreatedDate { value } StageName { value } Amount { value displayValue } PrevAmount { value displayValue } CloseDate { value } PrevCloseDate { value } } } } } } } } } }\"}" })
```

**Multiple matches — local correction:** `first: 1` returns one deal even when `totalCount` shows that several matched, and the latest close date can belong to a different deal. When `totalCount` is above 1, run the candidate read below before using the result. If `totalCount` is above 10, its list would be cut off, so first narrow `%DEALNAME%` with the account or other words from the request (for example `%Acme%Renewal%`), never with a name from a returned deal. Then:
- if the list is empty or still cut off (`totalCount` above the rows returned), or narrowing was needed and the request had nothing to narrow with, say how many deals matched and ask for the full deal name or the account instead of listing a partial set;
- if exactly one candidate's `Name` equals the deal name the user gave, take it;
- otherwise, if exactly one candidate is open, take it;
- otherwise list the candidates (Account · Name · Stage · close) and ask which.

Keep the step 2 result when the chosen deal is the one it returned; otherwise rerun the full template with `where: { Id: { eq: "<ID>" } }`.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { totalCount edges { node { Id Name { value } StageName { value displayValue } CloseDate { value } IsClosed { value } Account { Name { value } } } } } } } }\"}" })
```

Empty `edges` → use a broad resolver selecting only `Id Name { value }`, choose the target, then rerun the full template with `where: { Id: { eq: "<ID>" } }`; never run the rich template across multiple matches. The `orderBy: { CloseDate: { order: DESC } }` makes `first: 1` favor the active/current deal on a multi-match name (not an arbitrary stale closed-won). `Task.Description`/`TaskSubtype` carry the "what happened" detail behind each timeline row. The `Tasks`/`Events` children carry the activity timeline — read them as **three separate states** (see next paragraph); a scalar `LastActivityDate` alone can't distinguish an open task or a future meeting from a completed touch.

**Deal history (included in the read above).** The nested `OpportunityHistories` snapshots are already scoped to the selected Opportunity, so they ground whether the CloseDate moved and detect same-day stage jumps without an ID-dependent second dispatch.
A snapshot dated *this* cycle with `CloseDate` different from `PrevCloseDate` = real slippage (penalize); no recent CloseDate change with the current date holding = inherited history, not a current slip (context only). Same-day StageName jumps = signals to surface. Empty/unavailable → don't infer a slip.

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**Issue step 2 and all of step 2b as tool calls in a single turn — do not wait for the SF read to return before firing the searches.** They're independent (searches key on the deal/account name, not the SF result), so batch them together. Keyed on the deal/account name:
- **email**: threads with the account/contacts, last ~60d → last exchange date + topic, objections, commitments
- **docs**: recent transcripts/notes on the account → decisions, objections, competitor mentions
- **slack**: internal mentions → deal-desk/exec/concerns

Use whatever email/doc/Slack search tools are available. If none are present, skip silently (SF-only is fine). Never block on these; cite source + date for anything you use.

## 3. Analyze (cite every value/source; invent nothing)

Signal-adjust from SFDC `Probability`, only on a shown trigger:
`+5` ≥3 contact roles · `+10` economic buyer role · `+10` champion engaged (multiple completed touches, email/Task) · `+10` mutual close plan / exec engaged (email/doc) · `−10` >14d since last **completed** touch · `−15` CloseDate past · `−15` open blocking risk · `−10` open High-sev risk · `−10` single-threaded · `−10` champion quiet 14d+ (email) · `−10` competitor named (doc/email) · `−10` current-cycle CloseDate slip (see guardrail). Floor 5, ceil 95. Show the math.

**Activity — three states, never conflated** (read from the Tasks/Events children, not `LastActivityDate` alone): *completed* = Task `Status` Completed or past-dated Event; *open* = Task not yet Completed; *scheduled* = any Task/Event dated after today. "Days dark", the `−10 >14d`, and `−10 champion quiet` triggers key on the last **completed** touch only — a future QBR or an open task is momentum, not a completed touch, and never resets the clock or counts as one. Surface open tasks and scheduled meetings as positive momentum, not silence.

**Match every adjustment to shown state; current-cycle only.** Apply a trigger only if the data you pulled shows it. Apply the slip penalty only when the deal-history query above shows the *current* CloseDate moved this cycle — a PushCount / stage-cycling count inherited from earlier cycles, with the current date holding, is **not** current slippage; don't penalize it (note it as historical context instead). Distinguish a confirmed blocking risk from one that's merely stale or unknown — don't score both as equally blocking.

Report any grounded `Executive Sponsor` by name.

## 4. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

Two blocks are embedded below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}` in the template with its type and a worked example; then the **widget template** (`renderer.json`). Compute a value for each token per the contract, substitute it into the template, and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate call — it names every {{token}} in the template, with each value's type and a worked example, so you compute the right value for each. Workflow: compute a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — qualRows stays an array; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Layout: header (title + status pill) → healthLine caption → recommended-move callout → 4 KPI stat strip → MEDDIC datagrid → deal card + blocker callout. Realistic values: sample-data.json (sibling).",
  "props": {
    "dealName": {
      "description": "Opportunity name (page title, header row).",
      "type": "string",
      "example": "Cobalt Robotics renewal + expansion"
    },
    "headerStatus": {
      "description": "Status pill beside the title (warning tone). Short urgency read.",
      "type": "string",
      "example": "6 DAYS TO CLOSE"
    },
    "healthLine": {
      "description": "One muted caption under the header — the composite health read: a 🟢/🟡/🔴 marker, 'Health <X>/10', and a one-clause verdict. The emoji + text carry the state, never color alone.",
      "type": "string",
      "example": "🟡 Health 6/10 — strong economics, but an unstarted paper process is the risk to a Jul 30 close"
    },
    "recMove": {
      "description": "Recommended-move callout heading — the #1 next action.",
      "type": "string",
      "example": "Get legal the contract today, reconfirm the champion holds on price"
    },
    "recMoveDetail": {
      "description": "Recommended-move callout body — why, and the specific move.",
      "type": "string",
      "example": "Paper process hasn't started and engagement dipped this week. With 6 days to close, send redlines this morning and confirm the VP Eng will defend the price when procurement pushes back."
    },
    "recMoveMsg": {
      "description": "Draft-action prompt behind the callout's primary button (compose a message/email for the top move).",
      "type": "string",
      "example": "Draft a note to legal requesting contract redlines for the Cobalt Robotics deal by end of day, flagging the Jul 30 close date."
    },
    "recMoveChampMsg": {
      "description": "Draft-action prompt for the champion-reconfirmation secondary action.",
      "type": "string",
      "example": "Draft a reconfirmation message to the VP Eng at Cobalt asking if they'll hold on price when procurement counters."
    },
    "recMoveOpenMsg": {
      "description": "Action prompt for the 'open in Salesforce' secondary action.",
      "type": "string",
      "example": "Open the Cobalt Robotics renewal + expansion opportunity in Salesforce and summarize its current state."
    },
    "kpiAmountNum": {
      "description": "KPI 1 value — deal amount. Format: currency symbol + K/M/B, one decimal max, no trailing .0 (e.g., 20K, 1.3M, 20B).",
      "type": "string",
      "example": "$1.8M"
    },
    "kpiAmountSub": {
      "description": "KPI 1 sublabel (context under the amount, e.g. current stage).",
      "type": "string",
      "example": "Negotiation"
    },
    "kpiStageNum": {
      "description": "KPI 2 value — stage number, display-formatted.",
      "type": "string",
      "example": "06"
    },
    "kpiStageLabel": {
      "description": "KPI 2 label — the grounded stage name (human label, never an API name).",
      "type": "string",
      "example": "Finalizing Closure"
    },
    "kpiStageSub": {
      "description": "KPI 2 sublabel (stages remaining).",
      "type": "string",
      "example": "1 stage to close"
    },
    "kpiCloseNum": {
      "description": "KPI 3 value — count until close (paired with kpiCloseUnit).",
      "type": "string",
      "example": "6"
    },
    "kpiCloseUnit": {
      "description": "KPI 3 unit for kpiCloseNum.",
      "type": "string",
      "example": "days"
    },
    "kpiCloseSub": {
      "description": "KPI 3 sublabel — the close date.",
      "type": "string",
      "example": "Jul 30, 2026"
    },
    "kpiQualNum": {
      "description": "KPI 4 value — MEDDIC criteria met (paired with kpiQualUnit).",
      "type": "string",
      "example": "3"
    },
    "kpiQualUnit": {
      "description": "KPI 4 unit for kpiQualNum.",
      "type": "string",
      "example": "of 6"
    },
    "kpiQualSub": {
      "description": "KPI 4 sublabel.",
      "type": "string",
      "example": "MEDDIC met"
    },
    "qualBadge": {
      "description": "Badge on the MEDDIC datagrid heading (gap count).",
      "type": "string",
      "example": "3 gaps"
    },
    "qualCaption": {
      "description": "Caption above the MEDDIC datagrid.",
      "type": "string",
      "example": "MEDDIC qualification — gaps block the commit"
    },
    "qualRows": {
      "description": "MEDDIC datagrid rows, one object per criterion (whole-token: stays an array). Each row: crit (criterion name), state ({ value, badgeVariant: success|warning|error }), detail (evidence clause), status ({value,badgeVariant} — value Met|Gap, badgeVariant success|warning|error).",
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
          "crit": {
            "description": "MEDDIC criterion name (e.g. Metrics, Economic buyer, Paper process).",
            "type": "string"
          },
          "state": {
            "description": "Criterion status badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Status label shown on the badge (e.g. Confirmed / Missing).",
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
          "detail": {
            "description": "Evidence clause for the criterion.",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Met",
            "badgeVariant": "success"
          },
          "crit": "Metrics",
          "state": {
            "value": "Confirmed",
            "badgeVariant": "success"
          },
          "detail": "18% cost reduction, quantified with buyer"
        },
        {
          "status": {
            "value": "Gap",
            "badgeVariant": "error"
          },
          "crit": "Paper process",
          "state": {
            "value": "Missing",
            "badgeVariant": "error"
          },
          "detail": "Redlines not started with 6 days to close"
        }
      ]
    },
    "dealAccount": {
      "description": "Deal-card account name.",
      "type": "string",
      "example": "Cobalt Robotics"
    },
    "dealStage": {
      "description": "Deal-card stage badge (grounded stage label).",
      "type": "string",
      "example": "Negotiation"
    },
    "dealTiming": {
      "description": "Deal-card timing badge.",
      "type": "string",
      "example": "Closes in 6 days"
    },
    "dealAmount": {
      "description": "Deal-card amount, display-formatted.",
      "type": "string",
      "example": "$1.8M"
    },
    "dealUrl": {
      "description": "Lightning record URL for the deal-card link. Omit if no valid Id.",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/r/Opportunity/006AX00000M8k2pYAD/view"
    },
    "blockerTitle": {
      "description": "Blocker callout heading — the single biggest risk.",
      "type": "string",
      "example": "Paper process is the long pole"
    },
    "blockerDesc": {
      "description": "Blocker callout body — the risk and the move to clear it.",
      "type": "string",
      "example": "Redlines haven't started and engagement dipped this week. With 6 days to close, get legal the contract today and reconfirm the champion will hold on price — otherwise this slips to next quarter."
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
                      "name": "briefcase",
                      "size": "xl",
                      "alt": ""
                    }
                  },
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{dealName}}",
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
              "text": "{{healthLine}}",
              "variant": "caption",
              "color": "muted"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "recommended",
              "eyebrow": "THE PLAY",
              "title": "{{recMove}}",
              "description": "{{recMoveDetail}}"
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
                      "label": "Draft legal push",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{recMoveMsg}}"
                            }
                          }
                        ]
                      }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "Reconfirm champion",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{recMoveChampMsg}}"
                            }
                          }
                        ]
                      }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "Open deal",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{recMoveOpenMsg}}"
                            }
                          }
                        ]
                      }
                    }
                  }
                ]
              }
            ]
          },
          {
            "definition": "tile/separator"
          },
          {
            "definition": "tile/row",
            "attributes": {
              "gap": "sm",
              "align": "stretch",
              "isWrapped": true
            },
            "children": [
              {
                "definition": "tile/column",
                "attributes": {
                  "width": "md"
                },
                "children": [
                  {
                    "definition": "tile/container",
                    "attributes": {},
                    "children": [
                      {
                        "definition": "tile/column",
                        "attributes": {
                          "gap": "xs"
                        },
                        "children": [
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "AMOUNT",
                              "weight": "semibold",
                              "color": "muted",
                              "variant": "caption"
                            }
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "baseline"
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{kpiAmountNum}}",
                                  "variant": "display"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{kpiAmountSub}}",
                              "variant": "caption",
                              "color": "muted"
                            }
                          }
                        ]
                      }
                    ]
                  }
                ]
              },
              {
                "definition": "tile/column",
                "attributes": {
                  "width": "md"
                },
                "children": [
                  {
                    "definition": "tile/container",
                    "attributes": {},
                    "children": [
                      {
                        "definition": "tile/column",
                        "attributes": {
                          "gap": "xs"
                        },
                        "children": [
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "STAGE",
                              "weight": "semibold",
                              "color": "muted",
                              "variant": "caption"
                            }
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "baseline",
                              "isWrapped": true
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{kpiStageNum}}",
                                  "variant": "display"
                                }
                              },
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{kpiStageLabel}}",
                                  "variant": "section-title",
                                  "color": "muted"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{kpiStageSub}}",
                              "variant": "caption",
                              "color": "muted"
                            }
                          }
                        ]
                      }
                    ]
                  }
                ]
              },
              {
                "definition": "tile/column",
                "attributes": {
                  "width": "md"
                },
                "children": [
                  {
                    "definition": "tile/container",
                    "attributes": {},
                    "children": [
                      {
                        "definition": "tile/column",
                        "attributes": {
                          "gap": "xs"
                        },
                        "children": [
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "CLOSE",
                              "weight": "semibold",
                              "color": "muted",
                              "variant": "caption"
                            }
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "baseline"
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{kpiCloseNum}}",
                                  "variant": "display",
                                  "color": "error"
                                }
                              },
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{kpiCloseUnit}}",
                                  "variant": "section-title",
                                  "color": "muted"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{kpiCloseSub}}",
                              "variant": "caption",
                              "color": "muted"
                            }
                          }
                        ]
                      }
                    ]
                  }
                ]
              },
              {
                "definition": "tile/column",
                "attributes": {
                  "width": "md"
                },
                "children": [
                  {
                    "definition": "tile/container",
                    "attributes": {},
                    "children": [
                      {
                        "definition": "tile/column",
                        "attributes": {
                          "gap": "xs"
                        },
                        "children": [
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "QUALIFICATION",
                              "weight": "semibold",
                              "color": "muted",
                              "variant": "caption"
                            }
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "baseline"
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{kpiQualNum}}",
                                  "variant": "display",
                                  "color": "warning"
                                }
                              },
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{kpiQualUnit}}",
                                  "variant": "section-title",
                                  "color": "muted"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{kpiQualSub}}",
                              "variant": "caption",
                              "color": "muted"
                            }
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            ]
          },
          {
            "definition": "tile/separator"
          },
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
                "definition": "tile/text",
                "attributes": {
                  "text": "MEDDIC qualification",
                  "variant": "section-title"
                }
              },
              {
                "definition": "tile/badge",
                "attributes": {
                  "label": "{{qualBadge}}",
                  "variant": "warning"
                }
              }
            ]
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{qualCaption}}",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "crit",
                  "header": "Criterion",
                  "type": "text"
                },
                {
                  "key": "state",
                  "header": "State",
                  "type": "badge"
                },
                {
                  "key": "detail",
                  "header": "Detail",
                  "type": "text"
                }
              ],
              "rows": "{{qualRows}}"
            }
          },
          {
            "definition": "tile/separator"
          },
          {
            "definition": "tile/container",
            "attributes": {},
            "children": [
              {
                "definition": "tile/column",
                "attributes": {
                  "gap": "md"
                },
                "children": [
                  {
                    "definition": "tile/row",
                    "attributes": {
                      "gap": "md",
                      "align": "start",
                      "justify": "between",
                      "isWrapped": true
                    },
                    "children": [
                      {
                        "definition": "tile/column",
                        "attributes": {
                          "gap": "xs",
                          "width": "stretch"
                        },
                        "children": [
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{dealAccount}}",
                              "variant": "h4",
                              "weight": "semibold"
                            }
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "center",
                              "isWrapped": true
                            },
                            "children": [
                              {
                                "definition": "tile/badge",
                                "attributes": {
                                  "label": "{{dealStage}}",
                                  "variant": "secondary"
                                }
                              },
                              {
                                "definition": "tile/badge",
                                "attributes": {
                                  "label": "{{dealTiming}}",
                                  "variant": "error"
                                }
                              }
                            ]
                          }
                        ]
                      },
                      {
                        "definition": "tile/column",
                        "attributes": {
                          "gap": "xs",
                          "align": "end"
                        },
                        "children": [
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{dealAmount}}",
                              "variant": "h3",
                              "weight": "bold"
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
                                      "url": "{{dealUrl}}"
                                    }
                                  }
                                ]
                              }
                            }
                          }
                        ]
                      }
                    ]
                  },
                  {
                    "definition": "tile/separator"
                  },
                  {
                    "definition": "tile/callout",
                    "attributes": {
                      "variant": "error",
                      "title": "{{blockerTitle}}",
                      "description": "{{blockerDesc}}"
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
# Deal Review: <Name> — <Account>
## Health: 🟢/🟡/🔴 <X>/10 — <one-sentence verdict>
<Stage displayValue> · <Amount displayValue> · <Type> · close <CloseDate> · age <days since CreatedDate>d
Prob: SFDC <P>% → adjusted <Y>% (<±adj: evidence>…). If evidence is genuinely two-sided, say so rather than forcing a single precise number.

## Qualification (BANT/MEDDIC)
| Element | Status | Evidence |
|---|---|---|
| Budget | ✅/⚠️/❌ | <$X confirmed <date>, source / gap> |
| Authority | ✅/⚠️/❌ | <EB name, role, source / gap> |
| Need | ✅/⚠️/❌ | <driver, source / gap> |
| Timeline | ✅/⚠️/❌ | <customer close driver, source / gap> |
Cite the source per row; ❌ only when truly not pulled.

## Strengths
- 1–3 evidenced positives (confirmed BANT, prior wins, engaged champion, momentum) — always populate when present; don't drop positives while keeping risks.

## Activity Timeline
- <date> · <source> · <subject / what happened>  (newest first, from the Tasks/Events children)
- Last **completed** touch: <N>d ago · open tasks: <subject, due> · scheduled: <meeting, date>
Keep the three states separate; a scheduled/open item is not a completed touch.

## Risks
- <Primary confirmed gate (Sev, Status, owner)>; then each open risk <Name (Sev, Status, blocking?)>. Mark confirmed-blocking vs stale/unknown distinctly.

## Missing
- Qualification gaps, single-threading, no MAP, unnamed competitor, missing exec sponsor, procurement owner — whatever affects closure.

## Stakeholders
- <Name (Title, Role)>…

## Stage check
- <matches / ahead of evidence — why>

## Evidence
- <key email/doc/Slack signals w/ date+source, or "CRM only — email/docs/Slack not connected">

## Recommended Next Actions
1. 2–4 actions, each tied to a named gap/risk above with an owner or date

## Suggested SFDC updates
- StageName/NextStep/CloseDate if evidence differs from the record (apply with `update-opportunity`, or note if read-only)
```
