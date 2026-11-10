---
name: research-prospect
description: "Build a prospect brief from web research and Salesforce, covering company facts, recent signals, likely priorities, contacts and ICP fit. Use to research a net-new company or person before outreach. Existing accounts: account-context."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:64cf9572e5ff299a7f26639ec7717173e7d0ba042a56b22dda286a0b7ef978bb"
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


# Research Prospect

Ground Account → CRM read + web research (ONE turn) → score fit → output. Grounding surfaces this org's custom ICP fields (tier/segment/territory) — fit scoring reads them, so don't skip it.

## 1. Inputs

- **Company name or domain** (required)
- **Contact name or title** (optional)

ICP (industries, size, titles, disqualifiers), value prop, competitors, differentiators are external knowledge — infer from org data or confirm with the user once. Never invent.

## 2. Ground Account (this turn), then CRM read + web research (ONE turn)

**Ground Account first** — its `__c` fields are this org's ICP schema (tier, segment, territory, employee band, etc.), and Step 3 scores fit against them. Account always exists, so this one call never fails on a missing object:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })
```
From the result, note the scalar `__c` fields whose label carries ICP/segment/tier/territory/employee-band signal — add each as `Field__c { value }` to `<ACCOUNT_CUSTOM>` in the read below.

**Just scan the result by eye — do not script the extraction** (no `cat` / `python3` / `jq` / `grep` over the response). The Account catalog is large and may not come back inline: if the host wrote it to a temp file, open that file with the **Read tool only** — its path is outside the shell sandbox, so `cat` / `ls` fail on it. If the Read fails or the payload is unwieldy, skip grounding and use the standard fields below only — don't retry.

**CRM read + web search — fire BOTH as tool calls in ONE turn (independent).**

**Salesforce** — read the matching Account over GraphQL (Account is UI-API-serviceable; no SOQL needed). Insert `<ACCOUNT_CUSTOM>` = the confirmed scalar `__c { value }` fields from grounding.

Match on **`Name` first**. Do **not** combine Name and Website with `or` — a two-clause `or` in a UI-API `where` 500s on this endpoint. Only if the name search returns no rows, run the Website-only fallback below.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 5) { edges { node { Id Name { value } Website { value } Industry { value displayValue } NumberOfEmployees { value } Type { value displayValue } <ACCOUNT_CUSTOM> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } Contacts(first: 10) { edges { node { Id Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```
- **Found** → note owner, open opps, known contacts. Output must say "already in CRM, owned by [Name]" prominently so the user doesn't step on a colleague.
- **No rows** → run the **Website-only fallback** (a `%DOMAIN%` match), still no `or`:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Website: { like: \\\"%DOMAIN%\\\" } }, first: 5) { edges { node { Id Name { value } Website { value } Industry { value displayValue } NumberOfEmployees { value } Type { value displayValue } <ACCOUNT_CUSTOM> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } Contacts(first: 10) { edges { node { Id Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```
- **Still no match** → "net new - no CRM record". Broaden `%…%` once if a partial name seems likely; don't retry the same shape.

**Web search** (same turn, independent of the SFDC result):
- Company basics: what they do, HQ, size, funding stage, leadership
- Recent signals (last 6 months): funding rounds, exec hires, product launches, layoffs, earnings, expansion
- Tech/operating context relevant to your product category
- Likely priorities, inferred from the signals (e.g. just raised → hiring + scaling; new CRO → pipeline overhaul)
- If a contact was specified: their role, tenure, prior companies, public talks/posts, and what they likely care about

## 3. ICP fit scoring

| Dimension | Fit | Evidence |
|---|---|---|
| Industry | ✅ / ⚠️ / ❌ | [from research] |
| Company size | ✅ / ⚠️ / ❌ | [employee count vs ICP range] |
| Buyer persona present | ✅ / ⚠️ / ❌ | [title found / inferred] |
| Disqualifiers | ✅ none / ❌ [which] | |
| Timing signal | ✅ / ⚠️ / ❌ | [recent trigger event or none] |

Overall: **Strong fit / Moderate fit / Poor fit** with one-sentence rationale.

**Fit badge mapping — Quick/Kiro adaptation:** Keep `fitStatus` and `fitVariant` paired: Strong fit → `STRONG FIT` / `success`; Moderate fit → `MODERATE FIT` / `warning`; Poor fit → `POOR FIT` / `error`. Do not show a success-colored badge for a Moderate or Poor verdict.

**Numeric-meter provenance and scoreless branch — Quick/Kiro adaptation:** Include the ICP meter only when current org/user context supplies an explicit deterministic numeric formula with attributable inputs, target, and complete ordered bands. Embedded examples, qualitative dimension marks, and model judgment are not formulas. If that complete numeric contract is unavailable, do not estimate, copy examples, default to zero, or interrupt solely to ask for a score formula. Keep the evidence-backed Strong/Moderate/Poor verdict and its mapped badge, remove exactly the single `tile/meter` child from the widget template before resolving tokens, and do not emit or resolve any `icpValue`, `icpTarget`, `icpValueLabel`, `icpTargetLabel`, `icpStatus`, or `icpBands` value. Preserve the header, subtitle, separator, signals datagrid, synthesis callout, and every otherwise eligible action. This reduced widget remains the required widget path—not the text fallback. When the complete numeric contract is available, retain the meter and bind every numeric token from that same formula.

## 4. Relevance hooks

2-3 specific, sourced hooks for outreach — things from the research that connect to your value prop. Not generic ("they're growing") but specific ("they posted 12 [relevant role] openings last month and their [exec title] spoke about [relevant pain] at [conf]").

## 5. Prospect brief widget (editorial layout)

When the `display_widget` tool is available (Claude Cowork, the desktop app, the web app), render the prospect brief as a visual widget instead of the section 6 text. When `display_widget` is unavailable (e.g. a terminal) the section 6 markdown is the whole output, so produce it only then.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] Every `{{token}}` placeholder replaced with a resolved literal — no `{{…}}` left, no `{!…}` expressions in the widget definition.
- [ ] `fitStatus` and `fitVariant` use the exact Strong/success, Moderate/warning, or Poor/error mapping.
- [ ] With a complete attributable numeric formula, meter `value`/`max`/`target` and band `from`/`to` values are numbers, not strings; the bands cover `[0, 100]`, and every value/label/status comes from that formula.
- [ ] Without that formula, the single `tile/meter` block and all six `icp*` tokens are absent while the header, subtitle, separator, signals, callout, and eligible actions remain.
- [ ] Every `datagrid` signal row carries a leading `status` object; `tag` is a badge object.
- [ ] The `tile/callout` carries a resolved `title`/`description` (the approach + the timing), not empty and not a recap.
- [ ] No fabricated content — blank fields omitted or quoted blank, not invented.
- [ ] The section 6 markdown is produced only when `display_widget` is unavailable (the terminal fallback) — not alongside a rendered widget.

The widget template is embedded below. Call `display_widget` in **dynamic** mode with it. It is a skeleton: replace every `{{token}}` with a fully-resolved literal computed from the data you researched and scored — this echo path does no expression compilation, so no `{!…}` bindings. See `sample-data.json` in this dir for a fully-worked example of every token.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): - [ ] Every `{{token}}` placeholder replaced with a resolved literal — no `{{…}}` left, no `{!…}` expressions in the widget definition.\nThe widget template is embedded below. Call `display_widget` in **dynamic** mode with it. It is a skeleton: replace every `{{token}}` with a fully-resolved literal computed from the data you researched and scored — this echo path does no expression compilation, so no `{!…}` bindings. See `sample-data.json` in this dir for a fully-worked example of every token.\n- **Header** — an icon (search) + page-title text (`{{prospectTitle}}`, the prospect brief title) + a status badge (`{{fitStatus}}`, e.g. \"STRONG FIT\", with `{{fitVariant}}` from the exact verdict mapping), with a one-line caption subhead (`{{prospectSubtitle}}`) summarizing firmographics (industry/employees/revenue/fit), and a separator.\n- **Optional meter** — retain \"ICP fit\" only when an attributable deterministic numeric formula supplies `{{icpValue}}`, `{{icpTarget}}`, `{{icpValueLabel}}`, `{{icpTargetLabel}}`, `{{icpStatus}}`, and complete `{{icpBands}}`; otherwise remove exactly this block before token resolution and keep every independent block.\n- **Signals and openings datagrid** (`{{signalRows}}`) — one row per signal. Columns: Signal (text), Read (badge), Detail (text). Every row carries a leading `status` object (`{value,badgeVariant}` — value Buy/Fit/Watch, badgeVariant success/info/warning); the leading Status column reads each row's `status`.\n- **One synthesis callout** (`variant:\"recommended\"`) — `{{synthTitle}}` (the prospect's single most important read) and `{{synthDetail}}`. It carries two real buttons: a primary prompt button (`{{ctaLabel}}` / `{{ctaMsg}}`, `action/sendMessage`) and a secondary \"View in Salesforce\" (`{{prospectUrl}}`, `action/openLink`).\n1. Determine the meter branch before hydration. A complete attributable numeric formula retains the meter; no complete formula removes exactly the meter block and its six `icp*` tokens.\n2. Start from the embedded template above — a valid-JSON widget-definition envelope whose leaf values carry `{{token}}` placeholders.\n3. Resolve every `{{token}}`. A value that is **only** a `{{token}}` (meter `value`/`bands`, datagrid `rows`) becomes the resolved **typed** literal — numbers stay numbers, arrays stay arrays. A `{{token}}` **inside** a larger string is interpolated as text.\n4. `{{signalRows}}` is an array of signal objects — each with `topic` (signal name), `tag` (`{ value, badgeVariant }`), `note` (detail text), and `status` (`{value,badgeVariant}` — value Buy/Fit/Watch, badgeVariant success/info/warning).\n5. The result is hydrated widget definition (no `{{…}}` placeholders remain). Then call:\n- Resolve every remaining `{{token}}` to a literal before calling — numbers stay numbers (`{{icpValue}}`, `{{icpTarget}}`) only on the formula-backed meter branch, arrays stay arrays (`{{icpBands}}`, `{{signalRows}}`), and strings stay strings. On the scoreless branch, remove the meter first and never synthesize its six numeric tokens. Resolve `{{fitStatus}}` and `{{fitVariant}}` from the exact verdict mapping above.\n- On the formula-backed meter branch, `{{icpBands}}` is an attributable array of `{ from, to, variant, label }` covering 0→100 in order. On the scoreless branch, the meter and this token are absent.\n- Callout buttons: the primary is `action/sendMessage` with a first-person `content` prompt (`{{ctaMsg}}`, e.g. \"Draft a warm intro request…\"); the secondary is `action/openLink` with `{{prospectUrl}}` — the account's Lightning URL (`https://<myDomain>/lightning/r/Account/<Id>/view`), opening a new tab. Omit the openLink button if you lack the Id.",
  "props": {
    "prospectTitle": {
      "description": "Header page title — the prospect brief title.",
      "type": "string",
      "example": "Prospect brief — Beacon Health"
    },
    "fitStatus": {
      "description": "Header status badge — ICP verdict (e.g. \"STRONG FIT\").",
      "type": "string",
      "example": "STRONG FIT"
    },
    "fitVariant": {
      "description": "Header badge color paired to the verdict: success for Strong, warning for Moderate, error for Poor.",
      "type": "string",
      "enum": [
        "success",
        "warning",
        "error"
      ],
      "example": "success"
    },
    "prospectSubtitle": {
      "description": "Caption subhead: firmographics (industry / employees / revenue / fit).",
      "type": "string",
      "example": "Healthcare · 4,200 employees · $890M revenue · strong ICP fit"
    },
    "icpValue": {
      "description": "Formula-backed meter branch only: ICP fit score (0–100) computed from the attributable numeric formula.",
      "type": "number",
      "example": 88
    },
    "icpTarget": {
      "description": "Formula-backed meter branch only: target marker supplied by the same attributable numeric contract.",
      "type": "number",
      "example": 70
    },
    "icpValueLabel": {
      "description": "Formula-backed meter branch only: display string for the computed ICP score.",
      "type": "string",
      "example": "88 / 100"
    },
    "icpTargetLabel": {
      "description": "Formula-backed meter branch only: display string for the attributable target.",
      "type": "string",
      "example": "70 = qualified"
    },
    "icpStatus": {
      "description": "Formula-backed meter branch only: short status derived from the numeric contract.",
      "type": "string",
      "example": "strong fit"
    },
    "icpBands": {
      "description": "Formula-backed meter branch only: attributable ordered color bands covering 0→100.",
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
          "label": "Weak"
        },
        {
          "from": 50,
          "to": 70,
          "variant": "warning",
          "label": "Fair"
        },
        {
          "from": 70,
          "to": 100,
          "variant": "success",
          "label": "Strong"
        }
      ]
    },
    "signalRows": {
      "description": "Signals and openings — one row per signal. Empty array → the datagrid is omitted.",
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
          "topic": {
            "description": "Signal name.",
            "type": "string"
          },
          "tag": {
            "description": "Read badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Read label (Buy / Fit / Watch).",
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
          "note": {
            "description": "Detail for the signal.",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Buy",
            "badgeVariant": "success"
          },
          "topic": "Recent funding",
          "tag": {
            "value": "Opportunity",
            "badgeVariant": "success"
          },
          "note": "$120M Series D in May — budget available"
        },
        {
          "status": {
            "value": "Buy",
            "badgeVariant": "success"
          },
          "topic": "New CIO hired",
          "tag": {
            "value": "Opportunity",
            "badgeVariant": "success"
          },
          "note": "From a customer of ours — warm angle"
        },
        {
          "status": {
            "value": "Fit",
            "badgeVariant": "info"
          },
          "topic": "Hiring data engineers",
          "tag": {
            "value": "Signal",
            "badgeVariant": "info"
          },
          "note": "12 open reqs — scaling analytics"
        },
        {
          "status": {
            "value": "Watch",
            "badgeVariant": "warning"
          },
          "topic": "Uses competitor for CRM",
          "tag": {
            "value": "Obstacle",
            "badgeVariant": "warning"
          },
          "note": "Contract renews Q1 — time the approach"
        }
      ]
    },
    "synthTitle": {
      "description": "Synthesis callout heading — the prospect's single most important read.",
      "type": "string",
      "example": "Lead with the new CIO and the funding"
    },
    "synthDetail": {
      "description": "Synthesis callout body.",
      "type": "string",
      "example": "Beacon just raised $120M and hired a CIO who knows us from a prior account. Open with a warm intro to the CIO framed around scaling their new data-engineering team — and time it ahead of their Q1 CRM renewal."
    },
    "ctaLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft warm intro"
    },
    "ctaMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft a warm intro request to connect me to the Beacon Health CIO, mentioning they know our product from a prior account."
    },
    "prospectUrl": {
      "description": "Account Lightning URL for the secondary \"View in Salesforce\" button; omit if no Id.",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/r/Account/001AX000005mNq8YAE/view"
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
                      "name": "search",
                      "size": "xl",
                      "alt": ""
                    }
                  },
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{prospectTitle}}",
                      "variant": "h1"
                    }
                  }
                ]
              },
              {
                "definition": "tile/badge",
                "attributes": {
                  "label": "{{fitStatus}}",
                  "variant": "{{fitVariant}}"
                }
              }
            ]
          },
          {
            "definition": "tile/text",
            "attributes": {
              "text": "{{prospectSubtitle}}",
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
              "label": "ICP fit",
              "value": "{{icpValue}}",
              "min": 0,
              "max": 100,
              "target": "{{icpTarget}}",
              "valueFormat": "number",
              "valueLabel": "{{icpValueLabel}}",
              "targetLabel": "{{icpTargetLabel}}",
              "status": "{{icpStatus}}",
              "bands": "{{icpBands}}"
            }
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "What we know — signals and openings",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "topic",
                  "header": "Signal",
                  "type": "text"
                },
                {
                  "key": "tag",
                  "header": "Read",
                  "type": "badge"
                },
                {
                  "key": "note",
                  "header": "Detail",
                  "type": "text"
                }
              ],
              "rows": "{{signalRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "recommended",
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
                              "url": "{{prospectUrl}}"
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

What each block shows, from data you already gathered:

- **Header** — an icon (search) + page-title text (`{{prospectTitle}}`, the prospect brief title) + a status badge (`{{fitStatus}}`, e.g. "STRONG FIT", with `{{fitVariant}}` from the exact verdict mapping), with a one-line caption subhead (`{{prospectSubtitle}}`) summarizing firmographics (industry/employees/revenue/fit), and a separator.
- **Optional meter** — include "ICP fit" only when an attributable deterministic numeric formula supplies `{{icpValue}}`, `{{icpTarget}}`, `{{icpValueLabel}}`, `{{icpTargetLabel}}`, `{{icpStatus}}`, and complete `{{icpBands}}`; without it, remove exactly the meter and preserve every independent block.
- **Signals and openings datagrid** (`{{signalRows}}`) — one row per signal. Columns: Signal (text), Read (badge), Detail (text). Every row carries a leading `status` object (`{value,badgeVariant}` — value Buy/Fit/Watch, badgeVariant success/info/warning); the leading Status column reads each row's `status`.
- **One synthesis callout** (`variant:"recommended"`) — `{{synthTitle}}` (the prospect's single most important read) and `{{synthDetail}}`. It carries two real buttons: a primary prompt button (`{{ctaLabel}}` / `{{ctaMsg}}`, `action/sendMessage`) and a secondary "View in Salesforce" (`{{prospectUrl}}`, `action/openLink`).

**Hydration rules:**
1. Determine the meter branch before hydration. A complete attributable numeric formula retains the meter; no complete formula removes exactly the `tile/meter` child and its six `icp*` tokens.
2. Start from the embedded template above — a valid-JSON widget-definition envelope whose leaf values carry `{{token}}` placeholders.
3. Resolve every remaining `{{token}}`. A value that is **only** a `{{token}}` (formula-backed meter `value`/`bands`, datagrid `rows`) becomes the resolved **typed** literal — numbers stay numbers, arrays stay arrays. A `{{token}}` **inside** a larger string is interpolated as text.
4. `{{signalRows}}` is an array of signal objects — each with `topic` (signal name), `tag` (`{ value, badgeVariant }`), `note` (detail text), and `status` (`{value,badgeVariant}` — value Buy/Fit/Watch, badgeVariant success/info/warning).
5. The result is a hydrated widget definition with no unresolved token. Then call:

```
display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated renderer.json> })
```

**Binding rules:**
- Resolve every remaining `{{token}}` to a literal before calling — numbers stay numbers (`{{icpValue}}`, `{{icpTarget}}`) only on the formula-backed meter branch, arrays stay arrays (`{{icpBands}}`, `{{signalRows}}`), and strings stay strings. On the scoreless branch, remove the meter first and never synthesize its six numeric tokens. Resolve `{{fitStatus}}` and `{{fitVariant}}` from the exact verdict mapping above.
- On the formula-backed meter branch, `{{icpBands}}` is an attributable array of `{ from, to, variant, label }` covering 0→100 in order. On the scoreless branch, the meter and this token are absent.
- `datagrid` rows: one per signal. The Read badge (`tag.badgeVariant`) reflects signal type — `"success"` (Opportunity), `"info"` (Signal), `"warning"` (Obstacle). `status` fills the leading Status column.
- Callout buttons: the primary is `action/sendMessage` with a first-person `content` prompt (`{{ctaMsg}}`, e.g. "Draft a warm intro request…"); the secondary is `action/openLink` with `{{prospectUrl}}` — the account's Lightning URL (`https://<myDomain>/lightning/r/Account/<Id>/view`), opening a new tab. Omit the openLink button if you lack the Id.
- No fabricated content — quote blank fields as blank rather than inventing them; drop signals you have no data for.



## 6. Output

```
# Prospect Research: [Company]

## CRM Status
[Already in Salesforce - owned by [Name], [N] open opps | OR | Net new - no CRM record]

## Company Snapshot
- What they do: [one line]
- Size / stage: [employees, funding]
- HQ: [location]
- Leadership: [key names + titles]

## Recent Signals
- [Date] - [Signal] ([source])
...

## [Contact Name] (if specified)
- Role / tenure / background
- What they likely care about

## ICP Fit: [Strong / Moderate / Poor]
[Scoring table]
[One-sentence rationale]

## Relevance Hooks
1. [Specific hook] - ties to [your value prop angle]
2. ...

## Suggested Next Step
[e.g. "Run draft-outreach targeting [Contact]" or "Low fit - log as disqualified" or "Already owned by [Name] - coordinate before reaching out"]
```
