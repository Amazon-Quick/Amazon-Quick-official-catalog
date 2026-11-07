---
name: draft-outreach
description: "Create a personalized email draft from Salesforce contact, account, opportunity and activity data plus prior email, documents and Slack. Use when starting, following up with or re-engaging one prospect or customer. For batch inbox replies, use inbox-sweep."
icon: assets/salesforce.svg
checksum: "sha256:1bd444569f463425a20ab2f0b7b1c153ef9ad1f70d7f3a1441fa44c2941574ea"
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


# Draft Outreach

Ground → (read + evidence searches, all in ONE turn) → draft → create draft.

Value prop, proof points, voice/tone, signature block, and competitors (to avoid naming unprompted) are external knowledge — infer from the org's own closed-won data and product catalog, or ask the user once. Never invent them.

## 1. Ground (hardcoded — Contact only)

Ground **only Contact** — it always exists (naming a missing custom object fails the whole call). Its fields + childRelationships reveal this org's persona/segment schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { fields { ApiName label relationshipName } childRelationships { childObjectApiName relationshipName } } } }\"}" })
```

Step 1 is the authority on names — use exact strings from it, never guess. From the result, note: (a) scalar `__c` fields (persona, segment, relationship-context, etc.) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's name; (c) each child `relationshipName` beyond the two standard ones below.

## 2. Read (fill from step 1)

`%NAME%` = recipient's name and `%COMPANY%` = the company/account named in the request (swap `Name: { like: ... }` for `Email: { eq: \"%EMAIL%\" }` when given an email instead). **Reference-field rules (avoids the retry loop):**
- A scalar/`__c` field → `Field__c { value }`. `displayValue` is null for Id fields here — don't rely on it.
- To get a **related record's name**, span via the exact `relationshipName` from Step 1. Do NOT append `{ ... }` to a raw `Id`/`__c` field.
- Only span relationships Step 1 actually returned. No usable relationshipName → take the `__c { value }` (the Id) and move on — **do not retry**.

Insert `<CONTACT_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed org-specific relationship. `Account` (parent) and `OpportunityContactRoles` (child) always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { Name: { like: \\\"%NAME%\\\" } }, first: 1) { edges { node { Id Name { value } Title { value } Email { value } LastActivityDate { value } <CONTACT_CUSTOM> Account { Name { value } Industry { value } } <REL_BLOCKS> OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Opportunity { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsClosed { value } } } } } Tasks(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } TaskSubtype { value } } } } Events(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } Opportunities(where: { IsClosed: { eq: false } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } } } } } } }\"}" })
```

Empty `edges` → broaden `%NAME%`. **Prior-contact detection reads BOTH children plus the email search** — the `Tasks` child carries logged emails, the `Events` child carries calls/meetings; take the most-recent touch across Tasks, Events, AND the 2b email threads (a prior touch logged as an Event is invisible if you look only at Tasks). `Task.TaskSubtype` labels the last touch email-vs-call for the warm/cold call. `Tasks`/`Events` are standard activity children — but if a read errors on `Events` (`FieldUndefined`/`InvalidSyntax`), re-issue it **without** the `Events` block (Tasks-only) rather than failing the whole read; don't retry byte-identical. The sibling Account root's `Opportunities` (open) surface a deal-in-flight hook even when the contact has no contact-role of their own. Given a **company only** (no person named): skip Step 1 grounding and dispatch this instead — standard fields only, no custom-field grounding needed; its `Tasks`/`Events` children fill the "Prior contact" line for company-level asks:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsClosed { value } } } } Tasks(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } TaskSubtype { value } } } } Events(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } } } }\"}" })
```

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**Issue step 2 and all of step 2b as tool calls in a single turn.** They key on the recipient/company name from the request, not on the SF result, so batch them together:
- **email**: prior threads with this recipient — last exchange date + topic (warm follow-up vs. cold)
- **docs**: recent notes/transcripts mentioning the account — hooks, decisions, objections
- **slack**: internal mentions of the account/contact — context worth referencing

Use whatever email/doc/Slack tools are available; skip silently if none are present (SFDC-only is fine). Cite source + date for anything you use.

**Email evidence directionality — Quick/Kiro adaptation (candidate-style experiment):**

1. **Prepare:** For each mailbox item used for prior-touch or personalization, record its message or thread identifier, state (`draft`, `sent`, `received`, or `unknown`), author, recipient, date, and the exact statement used. Attribute each statement to its own message, not to the thread subject, signature alone, or another message in the thread.
2. **Validate:** An unsent draft is not a prior touch and supports no claim about what the customer knew, said, requested, decided, objected to, committed to, or agreed. A delivered seller-authored message may count only as an outbound touch and seller statement; it does not prove customer agreement. A seller-authored CRM note proves only what the seller recorded unless independently corroborated. Use a customer claim only from customer-authored inbound content whose sender identity matches the selected Contact or was confirmed by the user, or from another returned source that explicitly states it. Unknown or conflicting state, direction, authorship, or identity is not customer evidence.
3. **If validation fails:** Omit the unsupported customer claim and choose another eligible hook. If none remains, follow Step 3's ask path. Do not request draft creation from the unsupported claim.

## 3. Draft the email (cite every claim; invent nothing)

If step 2 AND 2b both come back empty (no SFDC record, no prior threads): run a lightweight pass — company basics + one recent signal — before drafting; never draft on invented context.

Structure (body under 120 words):
1. **Relevance line** — one sentence proving you did homework, sourced from step 2/2b. Never "I came across your company."
2. **Value bridge** — connect their situation to the value prop; use a proof point if it fits naturally.
3. **Soft ask** — one low-friction CTA. Default: "Worth a 20-min call to see if this maps to what you're working on?"
4. **Signature** — the block the user provided, or sampled from sent mail.

Tone: match the team voice (sampled from sent mail, or as directed); concise and direct — no "hope this finds you well," no paragraph intros.

Subject: 4-7 words, specific not salesy — references the hook, not the product.

**Draft manifest — Quick/Kiro adaptation (candidate-style experiment):**

1. **Prepare:** Freeze one new-draft payload: one recipient whose display name, email, and Account come from the same selected Contact row or from the user's explicit address; the exact 4–7 word Subject; the exact under-120-word Body; and, for every customer-attributed sentence, its eligible source or message identifier, author, state, and date. A searched evidence thread does not silently turn this new outreach draft into a reply or replace the selected Contact's email with a conflicting sender address.
2. **Validate:** Reject a blank or conflicting recipient, blank subject, placeholder, unresolved alternative, invented date or identity, added Cc/Bcc, send action, or customer claim that failed the directionality gate. Request connector approval only for a complete create-draft payload containing the exact To, Subject, and Body.
3. **If validation fails:** Do not invoke an email write. Omit or repair the unsupported claim, or ask one blocking question. Approval authorizes only the exact displayed create-draft payload once. Denial, failure, or any payload change authorizes no mutation until a fresh complete preview and approval; do not offer another draft attempt or Salesforce write after denial. Keep Salesforce logging as the existing handoff only, then complete through the Step 5 widget or Step 6 fallback.

## 4. Create email draft

Use email to create a draft (do not send): To = recipient email, Subject = [generated], Body = [generated]. Return the draft ID/link.

## 5. Widget (default output when `display_widget` is present: Cowork/desktop/web)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left — this echo path compiles no expressions), then call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once. A value that is *only* a `{{token}}` (the `{{contextRows}}` datagrid array) becomes the typed literal — arrays stay arrays; a `{{token}}` inside a larger string is interpolated as text. Fabricate nothing — every context row must trace to a real Step 2/2b finding; drop rows you lack data for rather than pad.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `{{draftTitle}}` header page-title (\"Outreach — [Name], [Title] @ [Company]\"); `{{draftSubtitle}}` caption subhead summarizing CRM status, prior-contact recency, and the hook; `{{intentBadge}}` status badge = the outreach intent (COLD INTRO / WARM FOLLOW-UP / RE-ENGAGE / REFERRAL / EVENT FOLLOW-UP); `{{contextRows}}` datagrid array (Source badge, What-it-told-us text), each row `{ source: { value, badgeVariant }, detail }` with badgeVariant `\"info\"` (CRM), `\"secondary\"` (prior email/activity), `\"success\"` (research signal); `{{subject}}` / `{{emailBody}}` the draft callout title/description — the exact subject and body created in Step 4, verbatim, not a paraphrase; `{{reviseLabel}}` / `{{reviseMsg}}` primary button (`action/sendMessage`) label + first-person revision instruction; `{{draftUrl}}` secondary button (`action/openLink`) = the created draft's deep link from Step 4 — omit that button if the draft tool returned no link. Before calling, confirm no `{{…}}` or `{!…}` remain and `{{subject}}`/`{{emailBody}}` match the Step 4 draft verbatim.",
  "props": {
    "draftTitle": {
      "description": "Header page title — \"Outreach — [Name], [Title] @ [Company]\".",
      "type": "string",
      "example": "Outreach — Dana Kwon, CFO @ Cobalt Robotics"
    },
    "intentBadge": {
      "description": "Status badge — the outreach intent.",
      "type": "string",
      "enum": [
        "COLD INTRO",
        "WARM FOLLOW-UP",
        "RE-ENGAGE",
        "REFERRAL",
        "EVENT FOLLOW-UP"
      ],
      "example": "WARM FOLLOW-UP"
    },
    "draftSubtitle": {
      "description": "Caption subhead: CRM status, prior-contact recency, and the hook.",
      "type": "string",
      "example": "Existing account · last thread 12 days ago · hook: Q4 close-cycle automation"
    },
    "contextRows": {
      "description": "Context signals feeding the draft — one row per source. Empty array → the datagrid is omitted.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source": {
            "description": "Source badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Source label shown on the badge.",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Badge color: info=CRM, secondary=prior email/activity, success=research signal.",
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
            "description": "What this source told us (text).",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "source": {
            "value": "CRM",
            "badgeVariant": "info"
          },
          "detail": "$1.8M renewal + expansion in Negotiation, closes Jul 30; owner Priya Nair"
        },
        {
          "source": {
            "value": "Prior email",
            "badgeVariant": "neutral"
          },
          "detail": "Jul 12 thread — Dana asked for the ROI model ahead of budget sign-off"
        },
        {
          "source": {
            "value": "Activity",
            "badgeVariant": "neutral"
          },
          "detail": "Last logged call Jul 6: budget confirmed for renewal + expansion"
        },
        {
          "source": {
            "value": "Signal",
            "badgeVariant": "success"
          },
          "detail": "Cobalt posted 14 finance-ops roles in Q1 — capacity strain on the close cycle"
        }
      ]
    },
    "subject": {
      "description": "Draft callout title — the exact email subject from Step 4, verbatim.",
      "type": "string",
      "example": "ROI model + a Q4 close-cycle idea"
    },
    "emailBody": {
      "description": "Draft callout body — the exact email body from Step 4, verbatim (not a paraphrase).",
      "type": "string",
      "example": "Dana — following up on the ROI model you asked for before budget sign-off; it's attached. One thing it surfaced: your Q1 finance-ops hiring suggests the close cycle is getting heavier. The automation tier in the expansion covers exactly that — Meridian Health cut three days off their close with it. Worth a 20-min call to see if it maps to what you're planning for Q4?"
    },
    "reviseLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Revise the draft"
    },
    "reviseMsg": {
      "description": "First-person revision instruction the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Revise this outreach email to Dana Kwon: keep it under 100 words, lead harder on the Q4 close-cycle time savings, and soften the CTA to a yes/no question."
    },
    "draftUrl": {
      "description": "The created draft's deep link for the secondary \"open\" button (action/openLink); omit if the draft tool returned no link.",
      "type": "string",
      "example": "https://mail.google.com/mail/u/0/#drafts"
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
                      "name": "mail",
                      "size": "xl",
                      "alt": ""
                    }
                  },
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{draftTitle}}",
                      "variant": "h1"
                    }
                  }
                ]
              },
              {
                "definition": "tile/badge",
                "attributes": {
                  "label": "{{intentBadge}}",
                  "variant": "info"
                }
              }
            ]
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "{{draftSubtitle}}",
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
              "caption": "Context used to personalize",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "source",
                  "header": "Source",
                  "type": "badge"
                },
                {
                  "key": "detail",
                  "header": "What it told us",
                  "type": "text"
                }
              ],
              "rows": "{{contextRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "info",
              "eyebrow": "DRAFT EMAIL",
              "title": "{{subject}}",
              "description": "{{emailBody}}"
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
                      "label": "{{reviseLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{reviseMsg}}"
                            }
                          }
                        ]
                      }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "Open draft in email",
                      "variant": "secondary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/openLink",
                            "attributes": {
                              "url": "{{draftUrl}}"
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
# Outreach Draft → [Recipient Name], [Title] @ [Company]

**Context used:**
- CRM: [summary of SFDC findings or "net new"]
- Prior contact: [last thread date + topic, or "none - cold"]
- Hook: [the relevance angle used]

---
**Subject:** [subject line]

[email body]
---

✉️ Created as email draft: [link/ID]
Review, edit, and send from your drafts folder.

**Suggested SFDC logging** (via `log-activity`, or manually on a read-only connector)**:**
- Log Activity on [Account/Contact]: "Outbound email - [subject]"
```
