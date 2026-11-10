---
name: account-tiering
display_name: Account Tiering
description: "Rank an account list or full book into action tiers from Salesforce ICP fit, engagement, activity, contact, and opportunity data. Use to score accounts, prioritize coverage, decide where to focus, or identify accounts to activate, qualify, or deprioritize."
author: Salesforce
roles:
  - role/sales
icon: assets/salesforce.svg
checksum: "sha256:f5687c556f657187ad8e5cf08935922110145c3b2bf5c23d79797228213fca96"
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

# Account Tiering

Probe → ground (its own turn) → read/evidence by scope → score → tier. Scope: "my accounts", a named list, or a report/list view name. Default tier count: 3 (A/B/C).

**Quick/Kiro connector preflight — candidate-derived adaptation:** Before Step 1, issue the global
v66 current-user probe once and wait for its result. Any server response proves the Salesforce
connector is reachable; only then issue Q1. Do not use Q1 as the connectivity probe or send it
before Q0. If Q0 cannot reach the server, follow the global reconnect branch and do not start Q1,
Q2, or optional evidence searches. A successful Q0 authorizes no extra retry later.

## 1. Ground (hardcoded — Account only)

Ground **only Account** — it always exists (naming a missing object fails the whole call). Its fields reveal this org's real ICP/engagement schema (custom fit score, territory, renewal fields, etc.) — don't assume custom field names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

**Field policy.** Step 2's standard fields and child spans are fixed — always read, never grounded. Custom fields are optional and come from THIS result only: use exact strings, never guess. Select relevant scalar `__c` fields carrying ICP-fit/engagement signals as `{ value }`, and each relevant custom lookup's exact `relationshipName` for a related record name. Build Step 2 only once this result is in hand — never fire the two together.

**Standard-field fallback.** If Step 1 errors, returns no `fields`, or was saved to a file you could not read in full (read failed, truncated, or token-capped), select NO custom fields — not from a preview, a partial read, or memory. Leave `<ACCOUNT_CUSTOM>` and the custom lookup blocks empty, fire Step 2 exactly as written, and disclose it (Step 5).

The ICP (industries, size, titles, disqualifiers) is set in Step 3 by a fixed rule — never invent it.

## 2. Read (fill from step 1, one dispatch)

`%SCOPE%` = `scope: MINE` for "my accounts"; `where: { Name: { in: [\\\"Acme\\\", ...] } }` for a named list. (A report/list-view scope needs its own name→Id resolve first — outside the common path; ask for a name list instead if one isn't already resolved.)

**Reference-field rule:** a confirmed scalar `__c` field → `Field__c { value }` (`displayValue` is null for Id fields here — don't rely on it). For a related record's name, span only the exact `relationshipName` from Step 1: `<relationshipName> { Name { value } }`. No usable `relationshipName` → take the `__c { value }` Id and move on; do not retry.

Insert `<ACCOUNT_CUSTOM>` = confirmed scalar `__c { value }` fields relevant to fit/engagement; `<REL_BLOCKS>` = one block per confirmed relevant custom lookup. `Owner`/`Opportunities`/`Contacts` always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(%SCOPE%, first: 200, orderBy: { Id: { order: ASC } }) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } AnnualRevenue { value displayValue } Website { value } Type { value } LastActivityDate { value } <ACCOUNT_CUSTOM> Owner { Name { value } } <REL_BLOCKS> Opportunities(where: { IsClosed: { eq: false } }, first: 1, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } StageName { value } CloseDate { value } } } } Contacts(first: 10) { edges { node { Id Title { value } } } } } } pageInfo { hasNextPage } totalCount } } } }\"}" })
```

`Opportunities` is an existence check: Salesforce applies the open filter, and `first: 1` returns just the open deal with the earliest close date (it may be past due) — show it in the Open Opp column. Step 4's "Open opportunity exists" = a non-empty `Opportunities.edges`. This read supports no opportunity counts or pipeline amounts, so the output shows none — never count these rows or present one deal as the account's pipeline. Empty `Account` `edges` → for `scope: MINE`, follow the empty-`MINE` rule; for a named list, confirm the account names.

**Bounds.** `Account(first: 200)` is the whole book up to 200 accounts. `pageInfo.hasNextPage: true` → the book is larger (`totalCount` accounts): tier the 200 you have and disclose the partial book (Step 5) — never call them the whole book. `Contacts(first: 10)` is a bounded sample per account — enough for the 3+ contacts signal; a full 10 with no target title scores the persona check `maybe`, not `none`.

## 2b. Evidence (scope-dependent ordering)

**Quick/Kiro evidence dependency — candidate-derived adaptation:** Run only searches whose exact
keys already exist; never invent, shorten, or hand-rewrite an Account name or domain.

- **Named list:** Q2 may run in parallel with Slack/document searches keyed by the exact names the
  user supplied. Email may run in that turn only when the user supplied an exact domain; otherwise
  wait for Q2's returned Website.
- **`scope: MINE`:** Q2 MUST finish first. Key a manifest by returned Account Id, preserving exact
  `Name.value` and the domain parsed only from that row's `Website.value`. Then run one optional-
  evidence batch. Slack/doc searches use the exact returned Account name; email uses only that
  Account's returned Website domain. A missing Website means email is not checked for that Account.
- Count an email as inbound account evidence only when its sender matches that exact Account domain
  and is not the user. Self-mail, delivery failures, and bounces are not customer engagement.

Evidence searches:
- **email**: inbound threads from qualifying account domains in the last 90d → which accounts, last date
- **docs/slack**: exact account-name mentions → triggers, concerns

Use whatever tools are available; skip silently if none (SFDC-only is fine). Never block on these;
cite source + date for anything you use.

## 3. Score ICP fit (0-10)

**ICP source** — use the first that applies, and record which (Step 5):
1. **Stated** — the industries, size, titles, or disqualifiers the user gives in the request (or earlier in the conversation).
2. **Derived** — otherwise, from the accounts read in Step 2 that have an open opportunity (Step 4's signal), ignoring nulls: target industries = their 3 most common `Industry` values (ties alphabetical); size range = their min–max `NumberOfEmployees`. Persona = a Contact title containing VP, Director, Head, or Chief, or a C-level acronym (CEO, CFO, CRO, CIO, CTO, COO). Disqualifiers = none, so every account scores clean.
3. **Ask** — the ICP can't be derived: no account has an open opportunity, or none of those accounts has an `Industry` or none has a `NumberOfEmployees` value. Ask the user for the ICP once, and don't score until they answer — never derive with a missing criterion.

A criterion the user didn't state falls back to its derived value; if that value can't be derived, ask (3).

| Signal | Weight | Scoring |
|---|---|---|
| Industry match | 3 | exact=3, adjacent=1, off-ICP=0 |
| Size in range | 3 | in range=3, ±50%=1, outside=0 |
| Target persona present (Contact titles) | 2 | yes=2, maybe=1, none=0 |
| No disqualifiers | 2 | clean=2, soft DQ=1, hard DQ=0 |

## 4. Score engagement (0-10)

| Signal | Weight | Scoring |
|---|---|---|
| Open opportunity exists (Step 2) | 3 | yes=3, no=0 |
| LastActivityDate recency | 3 | <30d=3, 30-90d=2, 90-180d=1, >180d=0 |
| Inbound signal (Step 2b email, last 90d) | 2 | yes=2, no=0 |
| Multiple contacts engaged | 2 | 3+=2, 2=1, ≤1=0 |

## 5. Tier and recommend

Plot on a 2x2 (Fit × Engagement). **High = 6 or more** on that axis; low = 5 or less.
- **Tier A** (high fit, high engagement): active pursuit — progress the open opp, multi-thread.
- **Tier B** (high fit, low engagement): activation — outbound sequence, find a trigger.
- **Tier C** (low fit, high engagement): qualify hard — one discovery call to confirm fit or DQ.
- **Deprioritize** (low fit, low engagement): no active motion, revisit quarterly.

**Quick/Kiro tier-display reconciliation — local adaptation:** For every rendered tiering
widget, compute raw Fit and Engagement scores first and use those same raw 0–10 scores in all
classification surfaces.

- The heatmap MUST be binary, not three-band: `heatmapXLabels` is exactly
  `["Low (0–5)", "High (6–10)"]`; `heatmapYLabels` is exactly
  `["High fit (6–10)", "Low fit (0–5)"]`.
- Assign every account to a heatmap cell from raw scores before any display conversion. The
  High-fit/High-engagement count MUST equal Tier A; High-fit/Low-engagement MUST equal Tier B;
  Low-fit/High-engagement MUST equal Tier C; Low-fit/Low-engagement MUST equal Deprioritize.
  The heatmap-cell total, pie-slice total, and scored-book count MUST all agree.
- `heatmapDomain` is an account-count range, not a score range. Omit empty cells but never create
  a Mid fit or Mid engagement band.
- The Tier A datagrid keeps presentation-only scales: `fit` is raw Fit ÷ 2 (0–5, including .5)
  and `engage` is raw Engagement × 10 (0–100). Those converted values MUST NOT determine a tier
  or heatmap cell.
- `arr` and `white` are optional, evidence-backed currency metrics—not required row defaults.
  Include `arr` only when Step 1 grounded an accessible currency field explicitly meaning ARR or
  Annual Recurring Revenue and Step 2 queried a value from it; standard `AnnualRevenue` is not
  ARR. Include `white` only from a queried currency field explicitly meaning Whitespace or
  Expansion Potential; a picklist such as Upsell Opportunity is not a whitespace amount.
- If an ARR or Whitespace field is absent, inaccessible, null, or unqueried, omit that row key and
  its corresponding datagrid column. Never substitute `0`, `$0`, or `$0.00` for unavailable data.
  If both are unavailable, render only Account, ICP fit, Engagement, and Motion columns.

**Disclosures** — carry each that applies into the output (the widget `subtitle`; in the text fallback, a line under the heading):
- Partial book (`hasNextPage: true`): "first 200 of [totalCount] accounts — narrow the scope to tier the rest". The widget `title` and the text heading also count "200 of [totalCount]", never just 200.
- Standard-field fallback: "custom fit fields unavailable — scored on standard fields".
- Derived ICP: "ICP derived from your [N] accounts with open deals: [industries], [min–max] employees". Omit when the user stated the ICP.

## 6. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `title` (page title with account count), `subtitle` (tier counts summary) · `heatmapCaption`, `heatmapXLabels`, `heatmapYLabels`, `heatmapDomain` (array `[min, max]`), `heatmapCells` (array of `{x, y, value, valueLabel?}`, one per quadrant) · `piechartCaption`, `piechartCenterLabel`, `piechartCenterValue`, `piechartSlices` (array of `{label, value, role?}`, role:\"highlight\" on Tier A) · `datagridCaption`, `datagridRows` (array, one per Tier A account: `{account, fit: 1-5 number, engage: 0-100 number, arr: number, white: number, motion: {value, badgeVariant}}`) · `calloutTitle`, `calloutDescription` (coverage gap), `primaryButtonLabel`, `primaryButtonMsg` (sendMessage action), `salesforceUrl` (Account list view URL).",
  "props": {
    "title": {
      "description": "Page title for the tiering view, with the book size (e.g. account count).",
      "type": "string",
      "example": "Account tiering — book of 40"
    },
    "subtitle": {
      "description": "One-line summary caption — how accounts were scored and the tier counts.",
      "type": "string",
      "example": "Scored on ICP fit × engagement · 6 Tier A, 14 Tier B, 20 Tier C"
    },
    "heatmapCaption": {
      "description": "Caption above the fit×engagement heatmap.",
      "type": "string",
      "example": "Accounts by ICP fit and engagement; count per quadrant"
    },
    "heatmapXLabels": {
      "description": "Heatmap X-axis labels (engagement bands), low→high. Keep each ≤12 chars, one or two short words — column headers sit in narrow equal-width columns and do NOT truncate, so long labels overrun into the neighboring header. Abbreviate (e.g. 'Low engage', 'High engage').",
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 12
      },
      "example": [
        "Low engage",
        "Mid engage",
        "High engage"
      ]
    },
    "heatmapYLabels": {
      "description": "Heatmap Y-axis labels (ICP-fit bands), high→low. Keep each ≤16 chars; long labels widen the row-label gutter and squeeze the grid.",
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 16
      },
      "example": [
        "High fit",
        "Mid fit",
        "Low fit"
      ]
    },
    "heatmapDomain": {
      "description": "Color-scale domain as [min, max] — the value range the heatmap colors span.",
      "type": "array",
      "items": {
        "type": "number"
      },
      "example": [
        0,
        8
      ]
    },
    "heatmapCells": {
      "description": "One entry per occupied fit×engagement quadrant; drives the heatmap coloring. Omit empty quadrants.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "x": {
            "description": "Engagement-band label (matches an entry in heatmapXLabels).",
            "type": "string"
          },
          "y": {
            "description": "ICP-fit-band label (matches an entry in heatmapYLabels).",
            "type": "string"
          },
          "value": {
            "description": "Account count in this quadrant — drives the cell color.",
            "type": "number"
          },
          "valueLabel": {
            "description": "Optional display label for the cell (e.g. \"6 · Tier A\").",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "x": "High engage",
          "y": "High fit",
          "value": 6,
          "valueLabel": "6 · Tier A"
        },
        {
          "x": "Mid engage",
          "y": "High fit",
          "value": 4
        },
        {
          "x": "Low engage",
          "y": "High fit",
          "value": 3
        },
        {
          "x": "High engage",
          "y": "Mid fit",
          "value": 5
        },
        {
          "x": "Mid engage",
          "y": "Mid fit",
          "value": 7
        },
        {
          "x": "Low engage",
          "y": "Mid fit",
          "value": 2
        },
        {
          "x": "Mid engage",
          "y": "Low fit",
          "value": 3
        },
        {
          "x": "Low engage",
          "y": "Low fit",
          "value": 8
        }
      ]
    },
    "piechartCaption": {
      "description": "Caption above the book-by-tier pie chart.",
      "type": "string",
      "example": "Book by tier"
    },
    "piechartCenterLabel": {
      "description": "Pie center label — what the total counts (e.g. \"Accounts\").",
      "type": "string",
      "example": "Accounts"
    },
    "piechartCenterValue": {
      "description": "Pie center value — the total (e.g. \"40\").",
      "type": "string",
      "example": "40"
    },
    "piechartSlices": {
      "description": "One slice per tier — the book split by tier. Empty → the pie is omitted.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "label": {
            "description": "Tier name (e.g. \"Tier A\").",
            "type": "string"
          },
          "value": {
            "description": "Account count in this tier.",
            "type": "number"
          },
          "role": {
            "description": "Optional emphasis; set \"highlight\" on the Tier A slice.",
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
          "label": "Tier A",
          "value": 6,
          "role": "highlight"
        },
        {
          "label": "Tier B",
          "value": 14
        },
        {
          "label": "Tier C",
          "value": 20
        }
      ]
    },
    "datagridCaption": {
      "description": "Caption above the Tier A accounts datagrid.",
      "type": "string",
      "example": "Tier A — invest: named plan, exec alignment, quarterly on-site"
    },
    "datagridRows": {
      "description": "Tier A accounts to invest in — one row per account, highest fit/engagement first. Empty → the datagrid is omitted.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "account": {
            "description": "Account name.",
            "type": "string"
          },
          "fit": {
            "description": "ICP fit score, 1–5.",
            "type": "number"
          },
          "engage": {
            "description": "Engagement score, 0–100.",
            "type": "number"
          },
          "arr": {
            "description": "Current ARR, in dollars.",
            "type": "number"
          },
          "white": {
            "description": "Whitespace / expansion opportunity, in dollars.",
            "type": "number"
          },
          "motion": {
            "description": "Recommended sales motion badge.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Motion label (e.g. \"Expand\" / \"Deepen\").",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Badge color: success / info / warning / error.",
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
          "account": "Meridian Health",
          "fit": 5,
          "engage": 92,
          "arr": 1200000,
          "white": 800000,
          "motion": {
            "value": "Expand",
            "badgeVariant": "success"
          }
        },
        {
          "account": "Pier 9 Retail",
          "fit": 5,
          "engage": 78,
          "arr": 700000,
          "white": 500000,
          "motion": {
            "value": "Expand",
            "badgeVariant": "success"
          }
        },
        {
          "account": "Alto Financial",
          "fit": 4,
          "engage": 61,
          "arr": 400000,
          "white": 900000,
          "motion": {
            "value": "Deepen",
            "badgeVariant": "info"
          }
        },
        {
          "account": "Northwind Log.",
          "fit": 4,
          "engage": 55,
          "arr": 350000,
          "white": 600000,
          "motion": {
            "value": "Deepen",
            "badgeVariant": "info"
          }
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the single biggest coverage gap or opportunity.",
      "type": "string",
      "example": "Coverage gap"
    },
    "calloutDescription": {
      "description": "Synthesis callout body — the gap and the recommended move.",
      "type": "string",
      "example": "3 high-fit accounts sit in the low-engagement column with no active opportunity — the fastest path to Tier A. Book an exec intro on each before quarter end."
    },
    "primaryButtonLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft exec intro plan"
    },
    "primaryButtonMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft an exec intro plan for the 3 high-fit, low-engagement accounts to move them to Tier A. Focus on booking exec intros before quarter end."
    },
    "salesforceUrl": {
      "description": "Account list-view Lightning URL for the \"View in Salesforce\" link.",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/o/Account/list?filterName=Recent"
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
                  "name": "layers",
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
            "definition": "tile/row",
            "attributes": {
              "gap": "lg",
              "align": "stretch",
              "isWrapped": false
            },
            "children": [
              {
                "definition": "tile/column",
                "attributes": {
                  "width": "stretch"
                },
                "children": [
                  {
                    "definition": "tile/heatmap",
                    "attributes": {
                      "layout": "matrix",
                      "caption": "{{heatmapCaption}}",
                      "xLabels": "{{heatmapXLabels}}",
                      "yLabels": "{{heatmapYLabels}}",
                      "encode": "color",
                      "scale": "sequential",
                      "valueFormat": "number",
                      "domain": "{{heatmapDomain}}",
                      "cells": "{{heatmapCells}}"
                    }
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
                    "definition": "tile/piechart",
                    "attributes": {
                      "caption": "{{piechartCaption}}",
                      "variant": "donut",
                      "valueFormat": "number",
                      "centerLabel": "{{piechartCenterLabel}}",
                      "centerValue": "{{piechartCenterValue}}",
                      "slices": "{{piechartSlices}}"
                    }
                  }
                ]
              }
            ]
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{datagridCaption}}",
              "appearance": "striped",
              "size": "sm",
              "defaultSort": {
                "key": "fit",
                "direction": "desc"
              },
              "columns": [
                {
                  "key": "account",
                  "header": "Account",
                  "type": "text"
                },
                {
                  "key": "fit",
                  "header": "ICP fit",
                  "type": "number",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "engage",
                  "header": "Engagement",
                  "type": "databar",
                  "target": 100
                },
                {
                  "key": "arr",
                  "header": "ARR",
                  "type": "currency",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "white",
                  "header": "Whitespace",
                  "type": "currency",
                  "align": "right"
                },
                {
                  "key": "motion",
                  "header": "Motion",
                  "type": "badge"
                }
              ],
              "rows": "{{datagridRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "recommended",
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
                      "label": "{{primaryButtonLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{primaryButtonMsg}}"
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


## 7. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Account Tiering - [N] accounts

## Tier A - Active Pursuit ([N])
| Account | Fit | Eng | Open Opp | Last Touch | Next Action |
|---|---|---|---|---|---|
...

## Tier B - Activate ([N])
...

## Tier C - Qualify or DQ ([N])
...

## Deprioritized ([N])
[Just names, collapsed]

## Coverage Gaps
- [N] Tier A/B accounts with no activity in 30+ days
- [N] accounts missing Industry or NumberOfEmployees (can't score - fix in SFDC)
```
