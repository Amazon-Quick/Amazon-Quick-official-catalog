---
name: inbox-sweep
display_name: Inbox Sweep
description: "Create a prioritized response queue and email drafts from unread threads, sent-mail voice patterns and Salesforce account and opportunity context. Use when sweeping or triaging an inbox, finding messages needing replies or drafting several customer responses."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:25e6b299de547f3f6df3eeb9ec0d77175d760971b0e343e88dd5d01cd6e3e1ac"
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


# Inbox Sweep

Unread customer emails → classify, prioritize, draft replies (into email). Cap 25 emails / 10 drafts per sweep. Lookback: 72h default.

## 1. Voice + candidate emails (one turn)

Read ~30–40 recent **external** sent emails to build an implicit style profile (greeting, length, sign-off, formality) — don't show it, just match it. In the same turn, search inbox: **unread, last <lookback>, not from your internal domain**.

**Exact lookback cutoff — Quick/Kiro adaptation (candidate-style experiment):**

1. **Prepare:** Before the first inbox search, obtain a timezone-aware current instant from an available current-time capability and compute `window_start = now - <lookback hours>` as an exact instant. Use the returned timestamp and offset as data; do not substitute a hand-authored current time. Preserve the existing independently grounded internal-domain exclusion; this rule does not derive an organization domain from a mailbox-provider domain.
2. **Validate:** Require the first inbox search to express that exact instant, unread state, internal-domain exclusion, and the 25-message cap. Use the connector's precise timestamp form; for Gmail search syntax use `after:<Unix epoch seconds>`, not `after:YYYY/MM/DD`, another calendar date, or local midnight. Require `window_start + <lookback hours> = now` to the returned second. Call mailbox profile, sent-mail sample, inbox search, and thread reads directly; never route connector calls or email/thread/CRM data through code, and never create/read a scratch, response, or data file. If timestamp arithmetic needs a deterministic calculation capability, its only inputs may be the returned timestamp/offset and lookback, and it must persist nothing.
3. **If validation fails:** Do not issue a broader or date-only inbox search. Report that the connector path could not express the exact requested lookback and stop without opening threads, reading Salesforce, requesting approval, or invoking a mailbox action.

**Candidate-set gate — Quick/Kiro adaptation (candidate-style experiment):**

1. **Prepare:** Freeze the messages returned by that one inbox search as this sweep's complete candidate set. The sent-mail sample supplies voice evidence only and never supplies candidates.
2. **Validate:** Every message opened, matched, classified, or drafted must be unread, external, inside the requested lookback and 25-message cap, and identified in the frozen set. Do not run a broader, undated, read-mail, topical, or repeated search to add candidates.
3. **If validation fails:** Exclude the item. If the frozen set is empty, skip Steps 2–5, render the Step 6 widget with zero rows or use Step 7 only when rendering is unavailable or errors, then stop. Do not offer or invoke a mailbox action.

## 2. Match senders to Accounts

Collect the candidate sender domains, then ONE Account read matching them (drop `scope: MINE` for a broader sweep).

**Note:** When using `scope: MINE`, do not query `currentUser` for scoping; the scope already identifies the running user's records. Follow the global connectivity rule before reporting the connector unavailable.

**Note:** Salesforce record `Id` is a scalar. When an ID is needed, select it as bare `Id`; never use the invalid `Id { value }` form.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(scope: MINE, first: 200) { edges { node { Name { value } Website { value } Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, first: 5, orderBy: { CloseDate: { order: ASC } }) { edges { node { Name { value } Amount { value displayValue } StageName { value displayValue } CloseDate { value } NextStep { value } } } } } } } } }}\"}" })
```

Match only by normalized sender domain and a returned Account's `Website`. Do not infer a match from Account or Opportunity names; when no exact domain match is returned, do not attach an Account, Opportunity, amount, or stage to that email. The open `Opportunities` child (same read) grounds Step 4 prioritization (Amount, soonest CloseDate) and fills the output **Opp** column (`$<Amount> · <StageName label>`) — no per-account follow-up read.

## 3. Classify each (read the full thread, not just the latest)

- **Needs reply — deal**: question/request/decision on an active opp → draft
- **Needs reply — scheduling**: proposing/confirming a time → draft availability
- **Needs reply — support**: product/technical → draft ack + flag support handoff
- **FYI only**: CC/newsletter/auto → archive
- **Intro / new inbound**: first contact → route to `lead-triage`
- **Couldn't draft**: needs info only the user has → surface the blocking question
- **Sensitive — skip**: personnel/legal/exec → flag, don't draft

## 4. Prioritize (within needs-reply)

Open opp closing ≤30d > explicit deadline/urgency > larger Amount > older unread.

## 5. Draft replies (priority order, cap 10)

Full thread context; match voice; answer the ask directly + confirm next step; <120 words; **draft in-thread (reply), never send**. Scheduling → propose 2–3 calendar slots. Support → brief ack + "looping in <support>". SFDC logging stays a `log-activity` handoff (never write inline).

**Draft-action gate — Quick/Kiro adaptation (candidate-style experiment):**

1. **Prepare:** From the complete original thread, form one final manifest item containing the external recipient copied from that thread, a greeting identity consistent with the recipient, the original thread identifier, a nonblank in-thread reply subject, and one final body under 120 words.
2. **Validate:** The body has no placeholder, bracketed instruction, or unresolved alternative, and every claim is grounded in the full thread, returned calendar availability, or this run's Salesforce read. Request approval only for a complete create-draft payload containing that exact recipient, subject, thread, and body.
3. **If validation fails:** Do not request approval or call a write action for that item. Put it under **Couldn't draft** with one blocking question. The only permitted mailbox mutation is the exact create-draft payload the user approves. Never offer or invoke send, reply-send, forward, archive, move, label, mark-read, or delete. Denial authorizes nothing and must leave zero mailbox mutations before the Step 6 widget or Step 7 fallback completes the run.

## 6. Widget (default output when `display_widget` is present: Cowork/desktop/web)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left), then call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once. A value that is *only* a `{{token}}` (`{{queueRows}}`, `{{totalRows}}`) becomes the typed literal — arrays stay arrays, numbers stay numbers; a `{{token}}` inside a larger string is interpolated as text. Synthesis-forward, not a dashboard: header + one datagrid + one recommendation. Blocks: header icon + `{{headerTitle}}` page-title + `{{headerSubtitle}}` one-line caption summarizing the queue (prioritized by deal value/urgency, count tied to closing deals); reply-queue datagrid (`{{queueRows}}`, one row per email — From/Subject/Deal/Deal value (currency, sortable)/Waiting (badge)/Suggested reply — with `{{totalRows}}` the full count); one warning callout (`{{calloutTitle}}` = the single most important read + `{{calloutDescription}}`) carrying two real buttons. No fabricated content — blank fields stay blank, drop emails with no data. Self-check before calling: no `{{…}}`/`{!…}` remain, numbers/arrays are typed literals, one `display_widget` call.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `{{headerTitle}}` page title; `{{headerSubtitle}}` queue-summary caption; `{{queueRows}}` datagrid array — one object per email with `from` (name → avatar chip), `subject`, `deal`, `value` (raw currency number), `wait` (`{ value, badgeVariant }` — `error` 2+ days / `warning` 1 day / `info` today / `success` hours), `action` (suggested reply text), `status` (`{value,badgeVariant}` — value Urgent/Today/Fresh/Quick win, badgeVariant success/warning/error/info/default); `{{totalRows}}` full email count (number); `{{calloutTitle}}`/`{{calloutDescription}}` callout copy; `{{ctaPrimaryLabel}}`/`{{ctaPrimaryMsg}}` primary button label + first-person `action/sendMessage` prompt (e.g. \"Draft replies to both Dana Kwon…\"); `{{salesforceUrl}}` secondary `action/openLink` target — the Opportunities list-view Lightning URL (`https://<myDomain>/lightning/o/Opportunity/list`).",
  "props": {
    "headerTitle": {
      "description": "Page title for the inbox sweep.",
      "type": "string",
      "example": "Inbox sweep — 14 items need a reply"
    },
    "headerSubtitle": {
      "description": "Queue-summary caption.",
      "type": "string",
      "example": "Prioritized by deal value and urgency · 3 tied to deals closing this week"
    },
    "totalRows": {
      "description": "Full email count (number).",
      "type": "number",
      "example": 14
    },
    "queueRows": {
      "description": "Emails needing a reply — one row per email, most urgent first. Empty array → the datagrid is omitted.",
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
          "from": {
            "description": "Sender name (shown as an avatar chip).",
            "type": "string"
          },
          "subject": {
            "description": "Email subject.",
            "type": "string"
          },
          "deal": {
            "description": "Linked deal name.",
            "type": "string"
          },
          "value": {
            "description": "Deal amount — a raw currency number.",
            "type": "number"
          },
          "wait": {
            "description": "Wait-time badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Wait label shown on the badge.",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Badge color: error=2+ days, warning=1 day, info=today, success=hours.",
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
          "action": {
            "description": "Suggested reply / next action (text).",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Urgent",
            "badgeVariant": "error"
          },
          "from": "Dana Kwon (CFO)",
          "subject": "Re: contract terms",
          "deal": "Cobalt renewal",
          "value": 1800000,
          "wait": {
            "value": "2 days",
            "badgeVariant": "error"
          },
          "action": "Send redlined MSA + Friday slot"
        },
        {
          "status": {
            "value": "Today",
            "badgeVariant": "warning"
          },
          "from": "R. Chen",
          "subject": "Security questionnaire",
          "deal": "Cobalt renewal",
          "value": 1800000,
          "wait": {
            "value": "1 day",
            "badgeVariant": "warning"
          },
          "action": "Route to SecOps, cc buyer"
        },
        {
          "status": {
            "value": "Urgent",
            "badgeVariant": "error"
          },
          "from": "M. Alvarez",
          "subject": "Pricing for expansion",
          "deal": "Meridian expansion",
          "value": 1000000,
          "wait": {
            "value": "3 days",
            "badgeVariant": "error"
          },
          "action": "Send tiered quote"
        },
        {
          "status": {
            "value": "Fresh",
            "badgeVariant": "info"
          },
          "from": "L. Osei",
          "subject": "Demo follow-up",
          "deal": "Delta Systems",
          "value": 600000,
          "wait": {
            "value": "today",
            "badgeVariant": "info"
          },
          "action": "Book technical deep-dive"
        },
        {
          "status": {
            "value": "Quick win",
            "badgeVariant": "success"
          },
          "from": "Procurement",
          "subject": "PO number request",
          "deal": "Pier 9 Retail",
          "value": 500000,
          "wait": {
            "value": "4 hours",
            "badgeVariant": "success"
          },
          "action": "Confirm PO, forward to finance"
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the queue's single most important read.",
      "type": "string",
      "example": "Clear the two Cobalt threads first"
    },
    "calloutDescription": {
      "description": "Synthesis callout body.",
      "type": "string",
      "example": "Both top items are the $1.8M renewal closing in 6 days — the CFO's contract reply and the security questionnaire. Answer those two before anything else; the rest can batch this afternoon."
    },
    "ctaPrimaryLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft both replies"
    },
    "ctaPrimaryMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft replies to both Dana Kwon (contract terms) and R. Chen (security questionnaire) for the Cobalt renewal closing in 6 days."
    },
    "salesforceUrl": {
      "description": "Opportunities list-view Lightning URL for the secondary button (action/openLink).",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/o/Opportunity/list"
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
                  "name": "inbox",
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
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "Reply queue, highest-leverage first",
              "appearance": "striped",
              "defaultSort": {
                "key": "value",
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
                  "key": "from",
                  "header": "From",
                  "type": "avatar"
                },
                {
                  "key": "subject",
                  "header": "Subject",
                  "type": "text"
                },
                {
                  "key": "deal",
                  "header": "Deal",
                  "type": "text"
                },
                {
                  "key": "value",
                  "header": "Deal value",
                  "type": "currency",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "wait",
                  "header": "Waiting",
                  "type": "badge"
                },
                {
                  "key": "action",
                  "header": "Suggested reply",
                  "type": "text"
                }
              ],
              "rows": "{{queueRows}}"
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


## 7. Output — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Inbox Sweep — <N> customer emails (<lookback>)
## Drafted Replies (<N>)
| Pri | From | Account | Subject | Opp | Draft |
## FYI Only (<N>) — safe to archive
## New Inbound (<N>) — run lead-triage
## Couldn't Draft — need your input (<N>)  · <blocking question>
## Sensitive — skipped (<N>)  · <why>
## Flagged for Support (<N>)
## Suggested SFDC logging (via `log-activity`, or manually)
- <Account>: Log Activity "Inbound email — <subject>"
```

All replies are drafts — review and send from email.
