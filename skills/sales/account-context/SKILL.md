---
name: account-context
description: "Build a 360-degree brief on a company already in Salesforce: CRM state, key contacts, recent email, documents and internal Slack. Use when asked to tell about, catch up on, or give the full picture on an existing account. Not in CRM: research-prospect."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:16e923d8310775f5d51a828cd69da555ee03e5ff20293c676f43c1051b72ada6"
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
Assemble a 360° brief on an account — the Salesforce record, open pipeline, key contacts, recent activity, and (when connected) email, documents, and internal Slack — in one pass.

# Audience:
This skill is used by workers in a sales organization. They want results as fast as possible. Minimize thinking when it's not necessary, hyper focus on getting them the results for the described goal.

# Rules:

- Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.

# Account Context

Resolve to one account, ground its customs, one read by Id, enrich in parallel, synthesize.

## 1. Resolve the account (disambiguate — do NOT probe)

Shared/demo orgs collide on name (duplicate seed data, empty test records like `MBourlon Acme Lab`). Land on a single Id first. One small query, **Account-level fields only** — never pull each candidate's Opportunities/Contacts to see "which is real"; that's a probe, skip it unless the user asks. If the user gave a Salesforce Id, skip this step.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 10) { edges { node { Id Name { value } Website { value } Type { value } Industry { value } LastActivityDate { value } Owner { Name { value } } } } } } } }\"}" })
```

(domain → filter `Website` instead of `Name`.)

- **One clear match** → take its Id, continue.
- **Several plausible matches** → list them (Name · Website · Owner · LastActivityDate · Id link) and ask the user to pick. `LastActivityDate` is your one free liveness tell — a blank/stale row beside a recent one usually flags the dead test record — but let the user decide; don't pick for them.
- **10 rows hit (likely more)** or **empty** → ask the user to narrow or correct the name.

## 2. Ground customs (fire in parallel with step 1)

Get the `__c` fields on every object this read touches — Account (health, tier, segment, ARR, renewal, status, score, region), Opportunity (forecast, competitor, close-plan, deal-health), Contact (buyer role/persona), Task (activity customs) — so the read can fetch them. Standard fields and the standard children (`Opportunities`, `Contacts`, `Tasks`) are reliable across orgs; you're grounding **only** for customs worth showing.

Issue these four individual `dispatch_readonly` requests in the same tool turn, in parallel with step 1. Keep one object per `objectInfos` request; combining catalogs can overflow the tool result.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Task\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

**An individual response can still be huge** — person-account orgs add hundreds of `__pc` fields, managed packages add `namespace__` fields (60KB+). If a tool result **truncates and auto-persists to a temp file**, that file is **outside the bash mount** — don't shell to it (`cat`/`jq`/`python3`/`ls` will fail, it's not on that mount). Read it back with the **Read tool only**, and go straight there — don't retry bash first — then scan for `__c` fields whose `label` matches your signal keywords, ignoring `__pc` and `namespace__` noise. Grounding is best-effort: if the Read tool can't load it either, or it's still unwieldy, take the standard fields and move on — customs are additive, not required.

## 3. Read the resolved account (by Id — fill from steps 1–2)

Filter by the resolved `Id` (disambiguation is done — no `like`, no `first:1` roulette). Insert the per-object custom tokens from step 2's grounding — `<ACCT_CUSTOM>` on Account, `<OPP_CUSTOM>` on each Opportunity node, `<CONTACT_CUSTOM>` on each Contact node, `<TASK_CUSTOM>` on each Task node — each = that object's confirmed `__c { value }` fields (`{ value displayValue }` for currency/picklist). Omit a token if grounding surfaced no relevant customs for that object.

Preserve the supplied GraphQL documents; replace only `<ID>` and the grounded custom-field placeholders.

**Canonical query execution — Quick/Kiro adaptation:** The deep read below is a complete
canonical request, not a query outline. Start from its literal `queryInput` and substitute only
`<ID>`, `<ACCT_CUSTOM>`, `<OPP_CUSTOM>`, `<CONTACT_CUSTOM>`, and `<TASK_CUSTOM>`.

- Each `*_CUSTOM` value is zero or more complete, confirmed field selections, for example
  `Health_Score__c { value }`; omit the whole slot when no confirmed custom field applies.
- Do **not** retype or reformat the document, add or remove braces, move a selection set, or
  merge/split this request. `aggregate` is a sibling of `query` under `uiapi`, never a child of
  `uiapi.query`.
- Before dispatch, verify that all placeholders are resolved or omitted and that the query retains
  `uiapi { query { Account(...) { ... } Task(...) { ... } } aggregate { Opportunity(...) { ... } } }`.
- On a JSON or GraphQL syntax error, discard the generated request. Rebuild once from this exact
  template using the resolved `<ID>` and with all four custom slots omitted. Do not hand-repair
  braces or relocate `aggregate`. If that standard-fields request still fails, report the error
  and stop rather than retrying a mutated query.

**Rules that avoid the retry loop:**
- Related record's name → span the lookup: `Owner { Name { value } }`. `Account.Owner` and `Opportunity.Owner` are single-target (→ `User`) and span cleanly. Never append `{ … }` to a raw `Id`/`__c` field.
- **Activity owners are polymorphic — don't span them.** `Task.Owner`/`Event.Owner` (and `Who`/`What`) are `User | Group` unions, so `Owner { Name { value } }` fails with `Field 'Name' in type 'Task_Owner' is undefined`. The default query below omits the owner span on Tasks; if you truly need it, use a fragment — `Owner { ... on User { Name { value } } }`. Don't assume symmetry with Opportunity.
- **Any `FieldUndefined` / `undefined in type X`** means that name or shape is wrong for THIS org — don't re-fire it. Re-ground that one object via `objectInfos(apiNames:["<Obj>"]) { fields { ApiName relationshipName referenceToInfos { ApiName } } }` (a `referenceToInfos` listing 2+ targets = polymorphic union → use a fragment), then retry from confirmed names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ID>\\\" } }, first: 1) { edges { node { Id Name { value } Website { value } Industry { value } NumberOfEmployees { value } AnnualRevenue { value displayValue } Type { value } BillingCity { value } BillingCountry { value } Description { value } CreatedDate { value } LastActivityDate { value } Owner { Name { value } Email { value } } <ACCT_CUSTOM> Opportunities(first: 10, where: { IsClosed: { eq: false } }, orderBy: { LastModifiedDate: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } Type { value } LastActivityDate { value } <OPP_CUSTOM> Owner { Name { value } } } } } Contacts(first: 15, orderBy: { LastActivityDate: { order: DESC } }) { edges { node { Id Name { value } Title { value } Email { value } Phone { value } LastActivityDate { value } <CONTACT_CUSTOM> } } } } } } Task(where: { AccountId: { eq: \\\"<ID>\\\" }, ActivityDate: { gte: { literal: LAST_90_DAYS } } }, first: 10, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } Status { value } IsClosed { value } Description { value } <TASK_CUSTOM> } } } } aggregate { Opportunity(where: { AccountId: { eq: \\\"<ID>\\\" }, IsClosed: { eq: false } }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```

`Opportunities` is bounded open supporting detail; the `aggregate` block rides in the same query (one dispatch) and is authoritative — use `totalCount` and `Amount.sum.value` for the complete open pipeline, not the ten supporting-detail records. `Task` carries **no** `Owner` span (polymorphic — see rule above). If a child or the `Task` root errors, drop that block and read recency from `LastActivityDate` — don't retry.

**Account tasks — local correction:** The `Task` root filters on `AccountId`, so it returns the account's tasks logged on its opportunities and contacts as well as on the account. The Account `Tasks` child returns only tasks logged directly on the account, so it missed most activity.

**Task status — local correction:** The `Task` rows include open tasks. A task's `ActivityDate` is its due date, so the window also returns open tasks due later. Count only rows with `IsClosed` true as logged activity. Show an open task as a follow-up with its due date, and call it overdue when that date is before today. If no returned row is closed, take the last-activity date from the account's `LastActivityDate`.

## 4. Enrich (parallel — skip any source not connected; never fabricate)

Fire these together in one turn; skip any whose tool isn't available and note it once at the end.
- **Email** — threads to/from the account's domain, last 90d. 5 most recent: date, participants, subject, one-line landing.
- **Documents** — docs mentioning the account: most recent transcript/notes + any account plan / proposal / MSA (title + date + one-line).
- **Slack** — account name, last 60d: relevant threads (deal desk, escalations, exec mentions, win/loss) with links.

## 5. Widget (default output when `display_widget` is present: Cowork/desktop/web)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left), then call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once.

**CRITICAL — widgetDefinition must be passed as a nested JSON object, NOT a string:**
- ❌ WRONG: `widgetDefinition: "{\"renderer\":{...}}"` (stringified with escaped quotes)
- ✅ RIGHT: `widgetDefinition: {"renderer":{...}}` (native object, no quotes around opening brace)

**Self-check before calling display_widget:**
1. After hydrating all `{{tokens}}`, verify the result is a JavaScript object (not a string)
2. If you have a string variable containing JSON, parse it first: `JSON.parse(stringVar)`
3. Pass the parsed object directly to `widgetDefinition` — do NOT stringify it again
4. The tool call must look like: `display_widget({resourceType: "dynamic", widgetDefinition: {renderer: {...}}})`
   - NOT: `display_widget({resourceType: "dynamic", widgetDefinition: "{\"renderer\":..."})`

When `display_widget` is available the widget is the output; produce the section 6 text only as the fallback when the tool is unavailable (e.g. a terminal). Every token here is text (no typed arrays); a `{{token}}` inside a larger string is interpolated. No fabricated content: drop any block whose data you don't have, never send empty rows or leave stray `{{tokens}}`.

**CRITICAL — contact card limit:** The template has exactly 2 contact cards (c1, c2). If you find more than 2 contacts in the data, select the 2 most relevant (by role importance, recent touch, or deal involvement). Do NOT add additional contact cards beyond the template structure.

Layout — a chartless editorial account brief, not a chart dashboard: it reads like a one-page memo. Lead with the one move worth making now, then support it. Header (file icon + serif `page-title` account name + status badge) → one `recommended` "recommended move" callout → a column of severity-ranked flag callouts → open-opportunity section (opp card with stage/timing badges + "View in Salesforce" link, a `warning` stalled-next-step callout, a 3-up row of document cards, an inline `recommended` draft-email callout) → recent closed/lost card + sync caption → key contacts (multi-threading `warning` callout + 3-up contact cards) → an expanded Account Details accordion (firmographic chip row, recent-correspondence callout + 3 mail rows, internal-chatter 2 chat rows). No pie/bar/meter/heatmap/waterfall tiles — synthesis and flags carry it.

Tokens: `accountName` (serif header title) + `headerStatus` (header badge, tone by urgency, e.g. "CLOSING TODAY") · `recMove`/`recMoveMsg` (recommended-move callout description + its `action/sendMessage` first-person prompt) — compute from the most time-sensitive gap · flags `flag1Title`/`flag1Detail` … `flag3Title`/`flag3Detail` (rank by threat to the open deal; add/drop to match the data; tone error/warning) · `totalPipeline` (open-opps caption) · opp card `oppName`/`oppStage`/`oppTiming`/`oppAmount` + `oppUrl` (`action/openLink`, `https://<myDomain>/lightning/r/Opportunity/<Id>/view` — omit the button if no Id) · `blockedTitle`/`blockedDesc` (stalled next-step `warning` callout) · docs `doc1Title`/`doc1Meta` … `doc3Title`/`doc3Meta` (icon red=awaiting signature, green=signed) · `inlineCtaQuote`/`inlineCtaMsg` (inline draft-email `recommended` callout + its `action/sendMessage` prompt) · closed/lost `lostTitle`/`lostAmount`/`lostMeta`/`lostStatus` + `syncLine` (sync caption) · `mtRiskTitle`/`mtRiskDesc` (multi-threading `warning` callout) · contacts `c1Name`/`c1Role`/`c1RolePill`/`c1Signal`/`c1Touch`/`c1Note` … c2/c3 (RolePill success=Champion, warning=Economic Buyer, error=Blocker risk; Signal word Warm/Cooling sits next to its dot — never color alone) · chips `chipRevenue`/`chipIndustry`/`chipEmployees`/`chipLocation`/`chipOwner` (plain strings — `chipOwner` must be formatted as `"Owner: <name>"` (e.g. "Owner: Sona Allen"); names must be plain strings, not objects: use `Account.Owner.Name.value` from the GraphQL response) · `corrPrompt` (correspondence `recommended` callout, e.g. "Last inbound was 38 days ago") · mail rows `mail1Subject`/`mail1Date` … `mail3*` · chat rows `chat1Channel`/`chat1Msg`/`chat1Time`, `chat2*`. Before calling: no `{{…}}`/`{!…}` remain, no charts, every button is `action/sendMessage` (first-person `content`) or `action/openLink` (record `url`) — none decorative; the accordion is `isExpanded: true`; badge/label text carries role and signal meaning, not color.

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
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{accountName}}",
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
            "definition": "tile/callout",
            "attributes": {
              "variant": "recommended",
              "eyebrow": "RECOMMENDED MOVE",
              "title": "Next Best Action",
              "description": "{{recMove}}"
            },
            "children": [
              {
                "definition": "tile/button",
                "attributes": {
                  "label": "Draft the note",
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
              }
            ]
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "Flags & Risks",
              "variant": "section-title"
            }
          },
          {
            "definition": "tile/column",
            "attributes": {
              "gap": "sm"
            },
            "children": [
              {
                "definition": "tile/callout",
                "attributes": {
                  "variant": "error",
                  "title": "{{flag1Title}}",
                  "description": "{{flag1Detail}}"
                }
              },
              {
                "definition": "tile/callout",
                "attributes": {
                  "variant": "warning",
                  "title": "{{flag2Title}}",
                  "description": "{{flag2Detail}}"
                }
              },
              {
                "definition": "tile/callout",
                "attributes": {
                  "variant": "error",
                  "title": "{{flag3Title}}",
                  "description": "{{flag3Detail}}"
                }
              }
            ]
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
                  "text": "Open Opportunities",
                  "variant": "section-title"
                }
              },
              {
                "definition": "tile/text",
                "attributes": {
                  "text": "{{totalPipeline}}",
                  "variant": "caption",
                  "color": "primary",
                  "weight": "semibold"
                }
              }
            ]
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
                              "text": "{{oppName}}",
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
                                  "label": "{{oppStage}}",
                                  "variant": "secondary"
                                }
                              },
                              {
                                "definition": "tile/badge",
                                "attributes": {
                                  "label": "{{oppTiming}}",
                                  "variant": "warning"
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
                              "text": "{{oppAmount}}",
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
                  },
                  {
                    "definition": "tile/callout",
                    "attributes": {
                      "variant": "warning",
                      "title": "{{blockedTitle}}",
                      "description": "{{blockedDesc}}"
                    }
                  },
                  {
                    "definition": "tile/callout",
                    "attributes": {
                      "variant": "recommended",
                      "title": "Suggested Outreach",
                      "description": "{{inlineCtaQuote}}"
                    },
                    "children": [
                      {
                        "definition": "tile/button",
                        "attributes": {
                          "label": "Draft Email",
                          "variant": "primary",
                          "actions": {
                            "click": [
                              {
                                "definition": "action/sendMessage",
                                "attributes": {
                                  "content": "{{inlineCtaMsg}}"
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
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "Key Contacts",
              "variant": "section-title"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "warning",
              "title": "{{mtRiskTitle}}",
              "description": "{{mtRiskDesc}}"
            }
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
                  "width": "stretch"
                },
                "children": [
                  {
                    "definition": "tile/container",
                    "attributes": {},
                    "children": [
                      {
                        "definition": "tile/column",
                        "attributes": {
                          "gap": "sm"
                        },
                        "children": [
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "center",
                              "justify": "between"
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{c1Name}}",
                                  "variant": "body",
                                  "weight": "bold"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{c1Role}}",
                              "variant": "caption",
                              "color": "muted"
                            }
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "sm",
                              "align": "center",
                              "justify": "between"
                            },
                            "children": [
                              {
                                "definition": "tile/badge",
                                "attributes": {
                                  "label": "{{c1RolePill}}",
                                  "variant": "success"
                                }
                              },
                              {
                                "definition": "tile/row",
                                "attributes": {
                                  "gap": "xs",
                                  "align": "center"
                                },
                                "children": [
                                  {
                                    "definition": "tile/text",
                                    "attributes": {
                                      "text": "{{c1Signal}}",
                                      "variant": "caption",
                                      "color": "muted"
                                    }
                                  }
                                ]
                              }
                            ]
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "center"
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{c1Touch}}",
                                  "variant": "caption",
                                  "color": "muted"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{c1Note}}",
                              "variant": "caption"
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
                  "width": "stretch"
                },
                "children": [
                  {
                    "definition": "tile/container",
                    "attributes": {},
                    "children": [
                      {
                        "definition": "tile/column",
                        "attributes": {
                          "gap": "sm"
                        },
                        "children": [
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "center",
                              "justify": "between"
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{c2Name}}",
                                  "variant": "body",
                                  "weight": "bold"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{c2Role}}",
                              "variant": "caption",
                              "color": "muted"
                            }
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "sm",
                              "align": "center",
                              "justify": "between"
                            },
                            "children": [
                              {
                                "definition": "tile/badge",
                                "attributes": {
                                  "label": "{{c2RolePill}}",
                                  "variant": "warning"
                                }
                              },
                              {
                                "definition": "tile/row",
                                "attributes": {
                                  "gap": "xs",
                                  "align": "center"
                                },
                                "children": [
                                  {
                                    "definition": "tile/text",
                                    "attributes": {
                                      "text": "{{c2Signal}}",
                                      "variant": "caption",
                                      "color": "muted"
                                    }
                                  }
                                ]
                              }
                            ]
                          },
                          {
                            "definition": "tile/row",
                            "attributes": {
                              "gap": "xs",
                              "align": "center"
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{c2Touch}}",
                                  "variant": "caption",
                                  "color": "muted"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{c2Note}}",
                              "variant": "caption"
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
            "definition": "tile/text",
            "attributes": {
              "text": "Account Details",
              "variant": "section-title"
            }
          },
          {
            "definition": "tile/column",
            "attributes": {
              "gap": "md"
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
                    "definition": "tile/badge",
                    "attributes": {
                      "label": "$ {{chipRevenue}}",
                      "variant": "outline"
                    }
                  },
                  {
                    "definition": "tile/badge",
                    "attributes": {
                      "label": "🏢 {{chipIndustry}}",
                      "variant": "outline"
                    }
                  },
                  {
                    "definition": "tile/badge",
                    "attributes": {
                      "label": "👥 {{chipEmployees}}",
                      "variant": "outline"
                    }
                  },
                  {
                    "definition": "tile/badge",
                    "attributes": {
                      "label": "📍 {{chipLocation}}",
                      "variant": "outline"
                    }
                  },
                  {
                    "definition": "tile/badge",
                    "attributes": {
                      "label": "👤 {{chipOwner}}",
                      "variant": "outline"
                    }
                  }
                ]
              },
              {
                "definition": "tile/column",
                "attributes": {
                  "gap": "xs"
                },
                "children": [
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "Recent correspondence",
                      "weight": "semibold",
                      "color": "muted",
                      "variant": "caption"
                    }
                  },
                  {
                    "definition": "tile/callout",
                    "attributes": {
                      "variant": "recommended",
                      "title": "Activity Summary",
                      "description": "{{corrPrompt}}"
                    }
                  },
                  {
                    "definition": "tile/container",
                    "attributes": {},
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
                              "gap": "xs",
                              "align": "center",
                              "width": "stretch"
                            },
                            "children": [
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{mail1Subject}}",
                                  "variant": "body"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{mail1Date}}",
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
                  "gap": "xs"
                },
                "children": [
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "Internal chatter",
                      "weight": "semibold",
                      "color": "muted",
                      "variant": "caption"
                    }
                  },
                  {
                    "definition": "tile/container",
                    "attributes": {},
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
                              "gap": "xs",
                              "align": "center",
                              "width": "stretch"
                            },
                            "children": [
                              {
                                "definition": "tile/badge",
                                "attributes": {
                                  "label": "{{chat1Channel}}",
                                  "variant": "outline"
                                }
                              },
                              {
                                "definition": "tile/text",
                                "attributes": {
                                  "text": "{{chat1Msg}}",
                                  "variant": "body"
                                }
                              }
                            ]
                          },
                          {
                            "definition": "tile/text",
                            "attributes": {
                              "text": "{{chat1Time}}",
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
          }
        ]
      }
    }
  }
}
```


## 6. Synthesize — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Lead with current state, not raw data. Omit any section whose source wasn't available. When email/docs/Slack connectors are absent, those sections are empty *by necessity* — note it once at the end (`Note: email/docs/Slack not connected`), don't imply the account is quiet everywhere.

```
# Account Context: [Account Name]

## Current State
[2-3 sentences: where this account is, what's active, the headline]

## Salesforce
- **Owner:** [Name] · **Profile:** [Industry] | [Employees] | [Type][ | custom health/tier if present]
- **Open opps:** [N], $[total]
  - **[Opp Name]** — [Stage] $[Amount] closes [Date] | Next: [NextStep]
- **Recent closed:** [Won/Lost] [Name] $[Amount] ([Date])
- **Last activity:** [Date] — [Subject]

## Key Contacts
| Name | Title | Last Touch | Notes |
|---|---|---|---|

## Recent Correspondence (email)
- [Date] — [Subject] with [Names] — [one-line]

## Documents
- [Title] ([type], modified [Date])

## Internal Chatter (Slack)
- [#channel] [Date] — [one-line] [link]

## Gaps / Flags
- [e.g. "No activity in 30d on $XXk opp" · "NextStep blank" · "single-threaded — 1 contact"]

## Ask the Owner
[If the requester is NOT the owner — draft a Slack DM to the owner. Conversational, lowercase opener, references the specific opp $ and one detail above, offers help. Offer to send it as a Slack draft.]

> hey — was looking at [Account], saw the $[X] opp at [stage]. [one specific detail]. anything you need from me on it?
```
