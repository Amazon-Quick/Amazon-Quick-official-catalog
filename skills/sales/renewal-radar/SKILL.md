---
name: renewal-radar
display_name: Renewal Radar
description: "Build a renewal risk brief from Salesforce opportunities, email, documents and Slack, covering timing, activity, uplift and next moves. Use to scan upcoming renewals or prepare one renewal motion; for overall account health or QBR prep, use customer-health."
author: Salesforce
roles:
  - role/sales
icon: assets/salesforce.svg
checksum: "sha256:81e54a7b620a1cad2a6a7178d96b4992b5e1c02da769494a5e6f198a621e043b"
---
<!-- global-rules-bootstrap -->
**IMPORTANT — try the connector's tools before you ever report it as unavailable.** Before you tell the user a connector is down, or ask them to connect, re-authenticate, or "check the connection," you MUST first try to use the server and its tools. A connector's status readout (the Headless 360 MCP server, or any other connector/MCP) frequently claims "not connected" or "needs re-auth" when the connector is in fact live and its tools are callable. Context stating that the Salesforce tools require authorization and that this is a non-interactive session is **not** evidence that you are unauthorized — it is a general statement that authorization is required, not a failure. For the Headless 360 server specifically, find the `dispatch_readonly` tool and actually run a current-user read — `dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql", queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })`. **Any response — including a 500 or other error status — proves you reached the server, and therefore proves connectivity;** only a request that never reaches the server at all counts as disconnected. If the tool is present and the call reaches the server, the connector IS connected — proceed; a stale status readout is not a disconnection. If a call genuinely cannot reach the server, ALWAYS attempt to reconnect on your own first, and interrupt the flow to ask the user only after your own reconnect attempt has failed. Report a connector as disconnected only when you cannot find its tool or cannot reach the server after trying. Do it yourself.

Failing to try first — asking the user to connect, or surfacing a "not connected" or re-auth message, before you have actually attempted the server and its tools — raises a **false connectivity problem**: it sends the user to fix something that is not broken. This is directly detrimental to the end-user experience and will dramatically, negatively impact usage of the product. Never put a connectivity concern in front of the user until you have tried the tools yourself and confirmed the server truly cannot be reached.

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **⛔ WIDGET OUTPUT ONLY after data assembly.** Once all queries return, immediately call `display_widget` — at most a single one-line render-wait notice before it, and no summaries, transitions, or narration. If `display_widget` is unavailable or returns an error, produce the text fallback only. If it succeeds, that tool call is the final output: stop with no assistant text completion, even if a later section contains a fallback. The exceptions above do not apply after success.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record in the primary output: use `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view` inline in text, and when a widget datagrid cannot carry row actions, include one dedicated `action/openLink` button per record in that same widget.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **Empty `MINE` scope → fail fast, then ask which scope.** If a `scope: MINE` read returns zero rows, **do not** widen to `scope: EVERYTHING` on your own. Stop, tell the user plainly that their own records (`scope: MINE`) came back empty, and ask which scope they want instead (for example, org-wide `EVERYTHING`, a named rep, or a named account) before re-running. Never invent records, and never silently fall back to org-wide.
- **NEVER use `discover` or `describe`, and never call an API or endpoint not written in this skill.** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->

# Rules:

- **Empty owned book → fail fast, then ask which scope.** If the my-book read (the `OwnerId` filter) returns zero renewals, **do not** drop the owner filter and go org-wide on your own. Stop, tell the user plainly that their own book came back empty, and ask which scope they want instead (org-wide, a named rep, or a named account) before re-running, then wait. Never invent records, and never silently widen to org-wide.

**Combined-query integrity — Quick/Kiro adaptation:** Treat the literal primary request below as the canonical template. Replace only `<currentUserId>`, `<OPP_CUSTOM>`, the documented scope clause, and both occurrences of `CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 120 } } }`; keep `query` and `aggregate` as siblings and their `where` filters identical, then serialize the decoded GraphQL once into `queryInput` and verify JSON plus bracket balance before dispatch. If the server reports `InvalidSyntax` or unexpected `<EOF>`, rebuild once from the literal template with the same grounded substitutions—never hand-retype, patch braces, or route the request through generated code.

**Usage-series grounding — Quick/Kiro adaptation:** Populate a row's `usage` only from returned numeric time-series values explicitly tied to that renewal; `LastActivityDate`, `StageName`, qualitative evidence, or metadata field presence cannot be expanded into a series. If no such series was returned, omit `usage` from that row while preserving the complete active widget and its Usage trend column; leave the cell empty—never synthesize points, arrows, zeroes, or direction.

# Renewal Radar

The renewal you start 90 days out is a process; the one you notice 2 weeks out is a discount. Keep the renewal calendar visible, flag the risky ones early, prep each renewal motion.

**Inputs:** my book (default), named rep, named account, or the team. Window: next N days (default 120), an exact half-open Date interval, or a named fiscal quarter with grounded start-inclusive/end-exclusive dates.

## 1. Resolve scope

- **"my renewals"** (default) → resolve `currentUser.Id` once through this exact query, then use that ID for the OwnerId filter:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })
  ```
- **"[Rep]'s renewals"** → resolve one User. Shared/demo orgs collide (one name → base user + regional variants like `(AM)`/`(BK)`). Pull enough to disambiguate:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Email { value } IsActive { value } } } } } } }\"}" })
  ```
  **One match** → take its Id for OwnerId filter in step 3. **Several** → list them (Name · Email · active? · Id) and ask user to pick. **Zero** → ask user to clarify.
- **Named account** → resolve through this exact bounded query, replacing `<ACCOUNT_NAME>` only with the user-supplied account name or distinctive words from it:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%<ACCOUNT_NAME>%\\\" } }, first: 10) { edges { node { Id Name { value } Website { value } } } totalCount } } } }\"}" })
  ```
  **One exact Name match** → use its Id for the AccountId filter in step 3. **Several plausible or exact matches** → list Name and Website and ask the user to pick. **Zero** → ask the user to clarify. If `totalCount` exceeds the returned rows and none is an exact Name match, ask for the exact account name or website rather than presenting the truncated list as complete.
- **Team** → no owner filter

## 2. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists. Its fields reveal this org's renewal-specific custom signals.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

From the result, select only relevant `__c` fields (ARR, renewal type, usage signals, auto-renew flags) and take their `{ value }`. A custom ARR field is a per-record signal only in this request; the book-wide aggregate below is standard Opportunity Amount and must not be relabeled ARR.

## 3. Pull renewal calendar (GraphQL — fill from step 2)

Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields from Step 2. **Nest Account and Owner in this one query.**

**Date filter:** resolve one frozen as-of instant and IANA timezone before materializing any relative window. Replace both `CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 120 } } }` occurrences with the same Date predicate:
- **Exact half-open window** `[<START_INCLUSIVE>, <END_EXCLUSIVE>)` → `CloseDate: { gte: { value: "<START_INCLUSIVE>" }, lt: { value: "<END_EXCLUSIVE>" } }`.
- **"next N days"** (default 120) → convert the frozen instant to its local Date, add positive integer `N` calendar days for the exclusive end, and use the same exact `gte`/`lt` predicate. For `as_of=2026-10-21T16:00:00Z`, `America/New_York`, and `N=120`, use `[2026-10-21, 2027-02-18)`.
- **Named fiscal quarter** → use only explicit start-inclusive/end-exclusive ISO dates supplied by the user or trusted org context and use the same exact `gte`/`lt` predicate.

If a relative window lacks its as-of instant or timezone, or a named fiscal quarter lacks exact boundaries, ask for the missing values and wait. Never assume a calendar or February fiscal start, pass an exclusive end through `lte`, use Salesforce `TODAY`/`next_n_days` as a substitute for the frozen context, or post-filter an unbounded result.

**Primary query (`like`/`or` catches both Type picklist values and Name patterns) — ONE combined dispatch: a bounded `query` for the detail rows plus an `aggregate` sibling on the IDENTICAL `where` for the authoritative total Opportunity Amount + count.** Do not sum the capped `query` rows for the headline total — read it from the `aggregate` block's `Amount.sum.value` / `Id.count.value` (or `totalCount`). Label this monetary value **Amount** or **renewal value**, never ARR, unless a separate returned ARR field and matching ARR aggregate explicitly establish that semantic.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { OwnerId: { eq: \\\"<currentUserId>\\\" }, IsClosed: { eq: false }, CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 120 } } }, or: [{ Type: { like: \\\"%renew%\\\" } }, { Name: { like: \\\"%renew%\\\" } }] }, orderBy: { CloseDate: { order: ASC } }, first: 50) { edges { node { Id Name { value } Type { value displayValue } Amount { value displayValue } CloseDate { value } StageName { value displayValue } NextStep { value } LastActivityDate { value } Account { Name { value } Industry { value displayValue } Type { value displayValue } } Owner { Name { value } } <OPP_CUSTOM> } } } } aggregate { Opportunity(where: { OwnerId: { eq: \\\"<currentUserId>\\\" }, IsClosed: { eq: false }, CloseDate: { gte: { literal: TODAY }, lte: { range: { next_n_days: 120 } } }, or: [{ Type: { like: \\\"%renew%\\\" } }, { Name: { like: \\\"%renew%\\\" } }] }) { edges { node { aggregate { Id { count { value } } Amount { sum { value } } } } } totalCount } } } }\"}" })
```

Replace the `CloseDate` clause in **both** the `query` and `aggregate` blocks with the grounded date filter — keep the two `where` clauses identical. Insert `<OPP_CUSTOM>` as `ARR__c { value } AutoRenew__c { value }` if those fields exist, or omit if none (on the `query` block only — the `aggregate` block doesn't select record fields). If `aggregate.Opportunity.totalCount` exceeds the 50 detail rows returned, label the calendar "Top 50 of `<totalCount>`" — never present the 50-row slice as the complete renewal book.

**Scope filters (apply identically to BOTH the `query` and `aggregate` `where`):**
- **My book** (default): keep `OwnerId: { eq: "<currentUserId>" }` using the `currentUser.Id` resolved in step 1
- **Named rep**: replace it with `OwnerId: { eq: "<resolvedUserId>" }`
- **Named account**: replace it with `AccountId: { eq: "<accountId>" }`
- **Team**: omit the owner clause

## 3b. Evidence (after step 3; parallelize the evidence searches)

Wait for step 3, collect the distinct returned `Account.Name.value` values, and then issue all available email, document, and Slack searches together in the next turn. The searches depend on those returned names for my-book, named-rep, named-account, and team scopes; never guess names or take them from memory.
- **email**: threads mentioning each returned account name in last 90d → escalations, sentiment, exec engagement
- **docs**: docs mentioning each returned account name → prioritize files with "escalation", "churn", "expansion" in title, most recent first. Read top 1–2 per account and extract: risk signals, expansion discussions.
- **slack**: each returned account name in last 30d → internal context (support escalations, CSM warnings, expansion threads)

Use whatever email/doc/Slack search tools are available. If none present, skip silently (SF-only is fine). Cite source + date for anything you use.

**Perf guardrail:** Do NOT fire additional SF dispatches for `Task` or `Contract` — the step 3 read has the data.

## 4. Score each renewal

| Signal | Effect |
|---|---|
| No activity on the account in 30+ days (LastActivityDate < 30 days ago) | risk ↑ |
| Open support escalation mentioned in email/Slack | risk ↑ |
| Usage/adoption signals trending down (if `__c` field present) | risk ↑ |
| Active expansion conversation in email/Slack | risk ↓ / uplift ↑ |
| Multi-year or auto-renew term (if `__c` flag present) | risk ↓ |
| NextStep blank or stale | risk ↑ |
| Champion or economic buyer has changed/left (email/Slack evidence from 3b) | risk ↑ |

**Stage snapshot grounding — Quick/Kiro adaptation:** `StageName` is only the current stage value; it does not establish time in stage or that a renewal is "still," "stuck," or "sitting" there. Say `currently at <Stage>` when useful, never use Stage alone as a risk signal, and base each verdict only on a signal in the table above or dated external evidence.

Verdict per renewal: 🟢 on track / 🟡 needs attention / 🔴 at risk - with the evidence.

## 5. Widget (default output when `display_widget` is present: Cowork/desktop/web)

Default output on Cowork/desktop/web; in a terminal `display_widget` is unavailable, so section 6 is the whole output there.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left — this echo path does no expression compilation), then call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once. A value that is *only* a `{{token}}` (meter `value`/`bands`, piechart `slices`, datagrid `rows`) becomes the typed literal — arrays stay arrays, numbers stay numbers; a `{{token}}` inside a larger string is interpolated as text.

Blocks, all from data already fetched: header icon + `{{pageTitle}}` title + `{{headerStatus}}` warning badge, then `{{subtitle}}` caption; a meter ("At-risk renewal value share": `{{riskValue}}` vs `{{riskTarget}}` over a fixed 0–100 range, with `{{riskValueLabel}}`/`{{riskTargetLabel}}`/`{{riskStatus}}`/`{{riskBands}}`) and a donut piechart ("Renewal value by risk verdict": `{{pieCenter}}` center, `{{pieSlices}}`) in a wrapped row; a renewals datagrid (`{{gridCaption}}`, `{{gridRows}}`, count `{{totalRenewals}}`) with columns Account, Amount (currency), Renews (date), Usage trend (sparkline), Verdict (badge), Play; a wrapped row of per-Opportunity openLink buttons (`{{recordLinkButtons}}`); one error callout (`{{synthTitle}}`/`{{synthDescription}}`) with a primary sendMessage button (`{{primaryLabel}}`/`{{primaryPrompt}}`) and a secondary openLink button ("View in Salesforce", `{{criticalRenewalsUrl}}`).

Binding:
- Numbers stay numbers (`{{riskValue}}`, `{{riskTarget}}`, each row's `amount`, `usage` arrays); arrays stay arrays (`{{riskBands}}`, `{{pieSlices}}`, `{{gridRows}}`, `{{recordLinkButtons}}`).
- `{{riskBands}}`: array of `{ from, to, variant, label }` covering 0→100 in order — success (0–15 Healthy), warning (15–30 Elevated), error (30–100 High).
- `{{pieSlices}}`: array of `{ label, value, role? }`, one per verdict; mark the at-risk segment `"role": "highlight"`. `{{pieCenter}}` is the summed Opportunity Amount of `{{pieSlices}}` — the scored sample, so the donut stays internally consistent — as a formatted currency string (e.g. "$4.7M"), not a raw number; the authoritative full-book Opportunity Amount (aggregate `Amount.sum`) is the headline/subtitle figure, not the donut center.
- `{{gridCaption}}`: state the effective grounded window and ordering, e.g. `Renewals in the next 120 days, Critical first then close date` or `Renewals in Q1 FY27, Critical first then close date`. It must describe the same date clause used in both query blocks.
- `{{gridRows}}`: array of `{ account (plain string — use `Account.Name.value`), amount (number from `Opportunity.Amount.value`), close (ISO YYYY-MM-DD), usage (number[]), verdict ({ value, badgeVariant }), action, status:{value,badgeVariant} (value Critical|At risk, badgeVariant error|warning) }`. Verdict badge: error=Critical, warning=At risk, success=On track. Risky rows carry a leading `status` object; healthy rows omit both. Pre-sort the array Critical first, then At risk, then On track, using close date ascending only within each verdict; the renderer deliberately applies no independent default sort.
- `{{recordLinkButtons}}`: one complete `tile/button` block per scored Opportunity, in the same order as `{{gridRows}}`. Label each `Open <Account> renewal`, use `variant: "secondary"` and `iconName: "open-in-new"`, and give it one `action/openLink` whose URL is `https://<myDomain>/lightning/r/Opportunity/<Id>/view` from that row's returned Opportunity Id. Never use an Account Id, list URL, or guessed Id for these buttons.
- `{{totalRenewals}}` = the scored row count (sample size), not the book-wide renewal count — label it "N of `<total>`" when the aggregate count exceeds it.
- **Sample vs. book scope — risk metrics are sampled.** The verdicts, the meter's at-risk share (`{{riskValue}}`), `{{pieSlices}}`, and `{{gridRows}}` are computed from the scored detail rows only (≤200 Tableau / ≤50 hardcoded); only the Opportunity Amount/count totals come from the aggregate and are full-book. When the book exceeds the returned rows, set `{{headerStatus}}`/`{{subtitle}}` to say so (e.g. "Risk shown for top 50 of 180 renewals") and carry the authoritative full-book Amount/count in `{{subtitle}}` — never present the meter, pie, or verdicts as covering the whole book.
- Callout: `{{primaryPrompt}}` is first-person (e.g. "Draft an executive save plan for…"); `{{criticalRenewalsUrl}}` = `https://<myDomain>/lightning/o/Opportunity/list?filterName=Critical_Renewals`, or the account record URL for a single renewal.

Verify before calling: no `{{…}}`/`{!…}` remain; exactly 2 graphs (meter + piechart); datagrid `amount`/`usage` are numbers/arrays, `close` is ISO, risky rows carry a leading `status` object and healthy rows omit both; the datagrid caption matches the effective date filter; rows are Critical-first with no renderer `defaultSort`; there is exactly one Opportunity openLink button per grid row plus the callout's 2 real buttons (sendMessage, openLink); section 6 text is produced only when `display_widget` is unavailable.


Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `{{pageTitle}}` (e.g. \"Renewal radar — next 120 days\"), `{{headerStatus}}` (e.g. \"$1.4M AT RISK\"), `{{subtitle}}` (window summary); meter `{{riskValue}}`/`{{riskTarget}}`/`{{riskValueLabel}}`/`{{riskTargetLabel}}`/`{{riskStatus}}`/`{{riskBands}}`; piechart `{{pieCenter}}` (formatted currency string e.g. \"$4.7M\")/`{{pieSlices}}`; datagrid `{{gridCaption}}`/`{{gridRows}}`/`{{totalRenewals}}`; per-record links `{{recordLinkButtons}}`; callout `{{synthTitle}}`/`{{synthDescription}}`/`{{primaryLabel}}`/`{{primaryPrompt}}`/`{{criticalRenewalsUrl}}`.",
  "props": {
    "pageTitle": {
      "description": "Page title (e.g. \"Renewal radar — next 120 days\").",
      "type": "string",
      "example": "Renewal radar — next 120 days"
    },
    "headerStatus": {
      "description": "Header at-risk badge (e.g. \"$1.4M AT RISK\").",
      "type": "string",
      "example": "$1.4M AT RISK"
    },
    "subtitle": {
      "description": "Window summary.",
      "type": "string",
      "example": "$4.7M renewal value across 11 renewals · $1.4M at risk · 3 need attention now"
    },
    "riskValue": {
      "description": "At-risk renewal-value share percentage.",
      "type": "number",
      "example": 30
    },
    "riskTarget": {
      "description": "Target/threshold marker on the meter.",
      "type": "number",
      "example": 15
    },
    "riskValueLabel": {
      "description": "Display string for the at-risk value.",
      "type": "string",
      "example": "$1.4M of $4.7M renewal value at risk (30%)"
    },
    "riskTargetLabel": {
      "description": "Display string for the target.",
      "type": "string",
      "example": "15% ceiling"
    },
    "riskStatus": {
      "description": "Short risk read shown on the meter.",
      "type": "string",
      "example": "over ceiling"
    },
    "riskBands": {
      "description": "Color bands for the risk meter, in order covering 0→max.",
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
          "to": 15,
          "variant": "success",
          "label": "Healthy"
        },
        {
          "from": 15,
          "to": 30,
          "variant": "warning",
          "label": "Elevated"
        },
        {
          "from": 30,
          "to": 100,
          "variant": "error",
          "label": "High"
        }
      ]
    },
    "pieCenter": {
      "description": "Pie center value — total scored Opportunity Amount, a formatted currency string (e.g. \"$4.7M\").",
      "type": "string",
      "example": "$4.7M"
    },
    "pieSlices": {
      "description": "Opportunity Amount by risk verdict — one slice per verdict. Empty array → the pie is omitted.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "label": {
            "description": "Slice label.",
            "type": "string"
          },
          "value": {
            "description": "Slice value (Opportunity Amount).",
            "type": "number"
          },
          "role": {
            "description": "Optional emphasis; set \"highlight\" on the key slice.",
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
          "label": "On track",
          "value": 3300000
        },
        {
          "label": "At risk",
          "value": 900000,
          "role": "highlight"
        },
        {
          "label": "Critical",
          "value": 500000
        }
      ]
    },
    "gridCaption": {
      "description": "Datagrid caption containing the effective grounded date window and Critical-first ordering.",
      "type": "string",
      "example": "Renewals in the next 120 days, Critical first then close date"
    },
    "gridRows": {
      "description": "Upcoming renewals — one row per account. Empty array → the datagrid is omitted.",
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
          "account": {
            "description": "Account name.",
            "type": "string"
          },
          "amount": {
            "description": "Opportunity Amount, in dollars (number).",
            "type": "number"
          },
          "close": {
            "description": "Renewal/close date, ISO YYYY-MM-DD.",
            "type": "string"
          },
          "usage": {
            "description": "Recent usage trend — a number array (sparkline).",
            "type": "array",
            "items": {
              "type": "number"
            }
          },
          "verdict": {
            "description": "Renewal-verdict badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Verdict label.",
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
          "action": {
            "description": "Recommended action (text).",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Critical",
            "badgeVariant": "error"
          },
          "account": "Cobalt Robotics",
          "amount": 500000,
          "close": "2026-08-12",
          "usage": [
            82,
            78,
            71,
            60,
            44,
            38
          ],
          "verdict": {
            "value": "Critical",
            "badgeVariant": "error"
          },
          "action": "⚠ exec save plan — usage down 54%"
        },
        {
          "status": {
            "value": "At risk",
            "badgeVariant": "warning"
          },
          "account": "Alto Financial",
          "amount": 400000,
          "close": "2026-08-20",
          "usage": [
            50,
            52,
            49,
            55,
            58,
            61
          ],
          "verdict": {
            "value": "At risk",
            "badgeVariant": "warning"
          },
          "action": "Multi-year + expansion pitch"
        },
        {
          "account": "Pier 9 Retail",
          "amount": 700000,
          "close": "2026-08-28",
          "usage": [
            60,
            64,
            66,
            70,
            72,
            75
          ],
          "verdict": {
            "value": "On track",
            "badgeVariant": "success"
          },
          "action": "Uplift candidate: +12% list"
        },
        {
          "account": "Meridian Health",
          "amount": 1200000,
          "close": "2026-09-18",
          "usage": [
            88,
            90,
            91,
            93,
            95,
            96
          ],
          "verdict": {
            "value": "On track",
            "badgeVariant": "success"
          },
          "action": "Anchor reference; propose 3-yr"
        }
      ]
    },
    "totalRenewals": {
      "description": "Total renewal count in the window (number).",
      "type": "number",
      "example": 11
    },
    "recordLinkButtons": {
      "description": "One complete tile/button block per scored Opportunity, in grid order. Each button opens that Opportunity's returned Id with action/openLink.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "definition": {
            "type": "string",
            "enum": [
              "tile/button"
            ]
          },
          "attributes": {
            "type": "object"
          }
        }
      },
      "example": [
        {
          "definition": "tile/button",
          "attributes": {
            "label": "Open Cobalt Robotics renewal",
            "iconName": "open-in-new",
            "variant": "secondary",
            "actions": {
              "click": [
                {
                  "definition": "action/openLink",
                  "attributes": {
                    "url": "https://org.lightning.force.com/lightning/r/Opportunity/006000000000000AAA/view"
                  }
                }
              ]
            }
          }
        }
      ]
    },
    "synthTitle": {
      "description": "Synthesis callout heading — the biggest renewal risk.",
      "type": "string",
      "example": "Cobalt Robotics is the critical renewal this month"
    },
    "synthDescription": {
      "description": "Synthesis callout body — the risk and the move.",
      "type": "string",
      "example": "Cobalt ($500K, renews Aug 12) has seen usage drop 54% in 6 weeks and needs an exec save plan now. Alto Financial ($400K, Aug 20) is at risk and could be secured with a multi-year + expansion pitch. These two renewals carry $900K of the $1.4M at-risk renewal value."
    },
    "primaryLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft exec save plan"
    },
    "primaryPrompt": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft an executive save plan for Cobalt Robotics to address the 54% usage decline before their August 12 renewal."
    },
    "criticalRenewalsUrl": {
      "description": "Lightning URL for the \"View in Salesforce\" button (critical renewals).",
      "type": "string",
      "example": "https://org.lightning.force.com/lightning/o/Opportunity/list?filterName=Critical_Renewals"
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
                      "name": "refresh",
                      "size": "xl",
                      "alt": ""
                    }
                  },
                  {
                    "definition": "tile/text",
                    "attributes": {
                      "text": "{{pageTitle}}",
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
            "definition": "tile/row",
            "attributes": {
              "gap": "lg",
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
                    "definition": "tile/meter",
                    "attributes": {
                      "label": "At-risk renewal value share",
                      "value": "{{riskValue}}",
                      "min": 0,
                      "max": 100,
                      "target": "{{riskTarget}}",
                      "valueFormat": "percent",
                      "valueLabel": "{{riskValueLabel}}",
                      "targetLabel": "{{riskTargetLabel}}",
                      "status": "{{riskStatus}}",
                      "bands": "{{riskBands}}",
                      "size": "lg"
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
                      "caption": "Renewal value by risk verdict",
                      "variant": "donut",
                      "valueFormat": "currency",
                      "centerLabel": "Amount",
                      "centerValue": "{{pieCenter}}",
                      "slices": "{{pieSlices}}"
                    }
                  }
                ]
              }
            ]
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{gridCaption}}",
              "appearance": "striped",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "account",
                  "header": "Account",
                  "type": "text"
                },
                {
                  "key": "amount",
                  "header": "Amount",
                  "type": "currency",
                  "align": "right",
                  "sortable": true
                },
                {
                  "key": "close",
                  "header": "Renews",
                  "type": "date",
                  "sortable": true
                },
                {
                  "key": "usage",
                  "header": "Usage trend",
                  "type": "sparkline"
                },
                {
                  "key": "verdict",
                  "header": "Verdict",
                  "type": "badge"
                },
                {
                  "key": "action",
                  "header": "Play",
                  "type": "text"
                }
              ],
              "rows": "{{gridRows}}",
              "totalRows": "{{totalRenewals}}"
            }
          },
          {
            "definition": "tile/column",
            "attributes": {
              "gap": "sm"
            },
            "children": [
              {
                "definition": "tile/text",
                "attributes": {
                  "text": "Renewal records",
                  "variant": "section-title"
                }
              },
              {
                "definition": "tile/row",
                "attributes": {
                  "gap": "sm",
                  "isWrapped": true
                },
                "children": "{{recordLinkButtons}}"
              }
            ]
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "error",
              "title": "{{synthTitle}}",
              "description": "{{synthDescription}}"
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
                      "label": "{{primaryLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{primaryPrompt}}"
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
                              "url": "{{criticalRenewalsUrl}}"
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

**Formatting rules:**
- **Link every opportunity:** `[Account] [↗](https://[instanceUrl]/lightning/r/Opportunity/[Id]/view)` inline in table + full URLs in Hygiene section
- **Extract instance URL:** from query result's `url` field or construct from org subdomain (e.g. `org62.my.salesforce.com`)
- **Specify date window:** e.g. "Aug 4 – Dec 1, 2026" (not just "next 120 days")
- **Status column:** extract from NextStep/Description/custom fields if present (e.g. "Ali resell", "Out of ext."), else fall back to StageName
- **Timeline specifics in At-risk section:** days until close, months since last activity, field API names for data discrepancies

```
# Renewal Radar - [scope] - [date range] ([instanceUrl])

| Account | Opp | Renewal date | Amount | Status | Risk driver | Next step |
|---|---|---|---|---|---|---|
| [Account] | [↗](https://[instanceUrl]/lightning/r/Opportunity/[Id]/view) | [date] | $[X] | [extracted status] | [flag] | [action] |

## At risk (act this week)
- **[Account] [↗](url)** - [date] ([N days away]) - [specific risk with timeline context: "no activity in 2.5 months", "6 days away"] → [the play]

## Uplift candidates
- **[Account] [↗](url)** - [the expansion signal and the proposed uplift motion]

## Hygiene

For each renewal with missing/incorrect data, propose the EXACT field change needed with **full Lightning URL**:

**Missing NextStep:**
```
🔧 Update [Opp Name]

Current NextStep: [blank]
→ Should be: [specific action based on stage and date proximity]

Apply this change via update-opportunity?
```

**Incorrect CloseDate:**
```
🔧 Update [Opp Name]

Current Close Date: [wrong date]
→ Should be: [corrected date based on contract/renewal timing]

Apply this change via update-opportunity?
```

**Missing renewal opportunity** (an account whose term is ending with no renewal opp on the books):
```
📋 Create Renewal Opportunity

Account: [Account]  ·  Name: "[Account] – [Year] Renewal"
Type: Renewal  ·  Amount: [prior renewal Amount or grounded ARR]  ·  Close Date: [term end]  ·  Stage: [initial renewal stage]

Create this record?
```

Present each proposed change with confirmation before attempting any write. On a read-only connector, output these as a checklist for manual entry.
```

For a single named account, expand into a renewal prep brief: history, current sentiment, pricing/uplift recommendation, paperwork timeline worked back from the end date.
