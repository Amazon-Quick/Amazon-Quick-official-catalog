---
name: deal-signals
description: "Build a deal-risk digest from Salesforce close dates, activity, next steps and forecast fields plus email, documents and Slack. Use to find quiet or overdue deals, close-date danger, renewal windows, competitor mentions or other risks needing attention."
icon: assets/salesforce.svg
checksum: "sha256:67c88be96ed16234650c331838631159160660761f2ce451b9dfcfed768020cf"
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

# Deal Signals

Ground → (read + evidence, one turn) → check thresholds → digest. Scope: my book (default), or a tier/team if asked. Requested CloseDate window: an exact half-open date interval or a relative N-day interval resolved from one frozen as-of instant and timezone; without a requested window, use the open book. Scheduled-change context: since last run, else 7 days.

## 1. Ground (hardcoded — Opportunity only) + running user's Id

Opportunity always exists; naming a missing object fails the whole call. Its fields reveal this org's custom signal fields — don't assume names. Fetch `currentUser.Id` in the SAME call (used to account-scope the book in step 2), so this stays one round-trip:

```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```

Record `currentUser.Id` as `<UID>`. Note scalar `__c` fields relevant to signals (renewal date, competitor, champion, deal-desk/legal-hold). **Resolve the next-step field `<NEXTSTEP>` — prefer a custom field over standard `NextStep`:** first a `__c` field whose `label` or ApiName reads like a next step (e.g. `Next_Step__c` labeled "Next Step"); else the standard `NextStep`. A custom next-step field implies the org built its own next-step logic and reps actually fill it in, whereas the standard `NextStep` is frequently left empty — preferring the custom one is why the "stale commitment" signal fires on the field reps actually use, not a permanently-blank standard one. Use exact names from this result.

## 2. Read the open book (one call, scope: MINE)

`scope: MINE` = the running user's book (no user lookup needed). Add confirmed `__c { value }` fields into `<OPP_CUSTOM>`, and select the resolved next-step field as `<NEXTSTEP> { value }` (default `NextStep { value }`). **Also account-scope the book:** add `Account: { OwnerId: { eq: \"<UID>\" } }` to the `where` so the sweep only covers opps on accounts the rep currently owns. When an account is reassigned, Salesforce moves `Account.OwnerId` but not the open opps' `OwnerId`, so `scope: MINE` alone keeps surfacing stale "zombie" deals on accounts the rep no longer manages. For a tier/team scope (asked for explicitly), drop `scope: MINE` AND this account-owner clause and filter on the requested owner/team instead — a manager reviewing a team wants every deal regardless of account owner.

**Requested CloseDate window — EXP-05 active correction:** Treat `CloseDate` as a Salesforce Date and use one frozen as-of instant plus one IANA timezone for every threshold and relative-window calculation. Replace `<CLOSE_DATE_FILTER>` in the literal query with exactly one of these values:

- Exact half-open interval `[<START_INCLUSIVE>, <END_EXCLUSIVE>)` → `CloseDate: { gte: { value: "<START_INCLUSIVE>" }, lt: { value: "<END_EXCLUSIVE>" } }, `.
- `next N days`, where `N` is a positive integer → convert the frozen instant to its local Date in the supplied timezone, add `N` calendar days for the exclusive end, and use the same exact `gte`/`lt` clause. For `as_of=2026-10-21T16:00:00Z`, `America/New_York`, and `N=30`, use `[2026-10-21, 2026-11-20)`.
- No requested CloseDate window → omit the whole placeholder.

If a relative window lacks an explicit or trusted as-of instant or timezone, ask for them and stop before the open-book read. Do not use Salesforce `TODAY`, a range literal, host-current dates, or output-only post-filtering as a substitute. Record the effective inclusive start and exclusive end and use the same local as-of Date in Step 3.

If `pageInfo.hasNextPage` is true, say that the returned first 100 by CloseDate are incomplete and ask for a narrower window or scope. Do not claim a complete sweep or produce the final digest from a truncated result.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(scope: MINE, where: { IsClosed: { eq: false }, <CLOSE_DATE_FILTER>Account: { OwnerId: { eq: \\\"<UID>\\\" } } }, orderBy: { CloseDate: { order: ASC } }, first: 100) { pageInfo { hasNextPage } totalCount edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } <NEXTSTEP> { value } LastActivityDate { value } LastModifiedDate { value } ForecastCategory { value } <OPP_CUSTOM> Account { Name { value } } } } } } } }\"}" })
```

## 2b. Evidence (same turn, only for CRM-flagged accounts — keeps the sweep fast)

After threshold checks flag accounts, in ONE turn fire (parallel, if tools present): **email** (last reply from us / **inbound from them with no reply from us in 3+ business days** / bounce / OOO / departure), **docs/transcripts** (competitor mention), **slack** (deal-desk/exec concerns). Keyed on the flagged account names. No tools present → skip silently.

**Email evidence — Quick/Kiro adaptation:** When an email tool is available, run the 2b email search for the flagged accounts; it is part of the sweep, not optional. If no email tool is available or the search fails, add one line saying email was not checked (under the ✅ line in the digest, or in the widget callout), so inbound-waiting, champion-risk, and competitor signals are not implied clear.

**No extra Salesforce reads.** Step 2 already returned every CRM field the thresholds need (LastActivityDate, CloseDate, LastModifiedDate, NextStep, ForecastCategory, `__c` signals). Do NOT dispatch per-opp SF follow-ups (EmailMessage / Task / OpportunityFieldHistory / activity queries) — each is a serial round-trip. Evidence here is ONLY the external email/doc/slack connectors above; if those aren't present, skip.

## 3. Check thresholds (compute explicit dates from the one frozen as-of instant and timezone — never quarter-relative or host-current)

Per open opp, fire a signal only when the record shows the trigger:
- **Gone quiet** — LastActivityDate >14d ago (or null) AND CloseDate within 90d
- **Inbound waiting** — customer emailed us and we haven't replied in 3+ business days (email evidence; the ball is on our side)
- **Danger zone** — CloseDate ≤21d out and stage still early
- **Overdue** — CloseDate < today
- **Slipped** — CloseDate moved out / recent LastModifiedDate date change
- **Stale commitment** — NextStep unchanged 21d+
- **Champion risk** — primary contact left/quiet (email/OOO evidence)
- **Renewal opening** — renewal entering lead-time window
- **Competitor mention** — named in recent email/transcript

**Stale commitment — Quick/Kiro adaptation:** A next step has been unchanged for 21+ days when `<NEXTSTEP>` is set and `LastModifiedDate` is 21 or more days before the frozen local as-of date, because no field on the deal has changed since then. Fire Stale commitment for each such deal. When `LastModifiedDate` is more recent, the record does not show the trigger, so do not fire it.

## 4. Widget (default output when `display_widget` is present: Cowork/desktop/web)

**Output choice — local correction:** This widget shows one opportunity's buying signals, and no step computes its composite score or six-week score trend. For a book or team sweep, do not call `display_widget`; the step 5 digest is the final output, overriding the widget-first rule. When the request names one deal that is in the step 2 results, call `display_widget` for that deal alone and remove the `tile/column` that holds the chart and meter, because the widget schema requires data the skill does not have. Give signal counts only in `subtitle`, use Watch for each risk row's `status` and `dir`, and skip the "two graphs present" check. Never invent a score or a trend.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.

The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left), then call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once. A value that is *only* a `{{token}}` (chart/meter/datagrid arrays) becomes the typed literal — arrays stay arrays, numbers stay numbers; a `{{token}}` inside a larger string is interpolated as text. Compute every leaf from data already fetched; no `{!…}` bindings, no fabrication (blank fields stay blank; drop signals with no data).

Synthesis-forward layout — header, two graphs, one datagrid, one callout:
- **Header** — activity icon, title (`{{title}}`), status badge (`{{headerStatus}}`), one-line caption (`{{subtitle}}`) summarizing score/trend/signal counts, and a second muted caption (`{{dealContext}}`) carrying this opp's shared deal facts — StageName label · Amount · CloseDate · next step · last activity — joined by ` · ` (constant across the signals below, so it sits once in the header, not per row).
- **Two graphs** — line chart of the 6-week signal-score trend (`{{chartCaption}}`, `{{chartCategories}}` = week labels, `{{chartSeries}}` = one `[{ name, data: [numbers] }]`); and a meter for the composite score (`{{meterLabel}}`, `{{meterValue}}` vs target `{{meterTarget}}` max `{{meterMax}}`, `valueFormat:"number"`, `{{meterValueLabel}}`, `{{meterTargetLabel}}`, `{{meterStatus}}`, and `{{meterBands}}` = ordered `[{ from, to, variant, label }]` covering 0→max for Cold/Warm/Hot, variants error/warning/success).
- **Signals datagrid** (`{{datagridCaption}}`, `{{datagridRows}}`) — one row per signal, strongest first: `signal` (name), `dir` (badge `{ value, badgeVariant }` — success Positive / warning Watch), `when` (ISO `YYYY-MM-DD`), `note` (detail), plus a leading `status` object (`{value,badgeVariant}` — value Buy/Watch, badgeVariant success/warning); the leading Status column reads each row's `status`.
- **One synthesis callout** (`variant:"success"`) closes the widget — `{{calloutTitle}}` (the single most important read) and `{{calloutDescription}}`, with two real buttons: primary `action/sendMessage` (`{{primaryButtonLabel}}` / first-person `{{primaryButtonContent}}`) and secondary "View in Salesforce" `action/openLink` to `{{oppUrl}}` (`https://<myDomain>/lightning/r/Opportunity/<Id>/view`; omit if you lack the Id). No decorative buttons.

Before calling, verify: no `{{…}}`/`{!…}` remain; `{{chartCategories}}`/`{{chartSeries}}`/`{{meterBands}}`/`{{datagridRows}}` are arrays and `{{meterValue}}`/`{{meterMax}}`/`{{meterTarget}}` numbers; both buttons wired (real sendMessage `content`, openLink `url`); two graphs present; the callout closes it.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): The widget template is embedded below — a widget-definition envelope whose leaf values carry `{{token}}` placeholders. Resolve every `{{token}}` to a literal (no `{{…}}`/`{!…}` left), then call `display_widget({ resourceType: \"dynamic\", widgetDefinition: <hydrated> })` once. A value that is *only* a `{{token}}` (chart/meter/datagrid arrays) becomes the typed literal — arrays stay arrays, numbers stay numbers; a `{{token}}` inside a larger string is interpolated as text. Compute every leaf from data already fetched; no `{!…}` bindings, no fabrication (blank fields stay blank; drop signals with no data).\n- **Header** — activity icon, title (`{{title}}`), status badge (`{{headerStatus}}`), one-line caption (`{{subtitle}}`) summarizing score/trend/signal counts, and a second muted caption (`{{dealContext}}`) carrying this opp's shared deal facts — StageName label · Amount · CloseDate · next step · last activity — joined by ` · ` (constant across the signals below, so it sits once in the header, not per row).\n- **Two graphs** — line chart of the 6-week signal-score trend (`{{chartCaption}}`, `{{chartCategories}}` = week labels, `{{chartSeries}}` = one `[{ name, data: [numbers] }]`); and a meter for the composite score (`{{meterLabel}}`, `{{meterValue}}` vs target `{{meterTarget}}` max `{{meterMax}}`, `valueFormat:\"number\"`, `{{meterValueLabel}}`, `{{meterTargetLabel}}`, `{{meterStatus}}`, and `{{meterBands}}` = ordered `[{ from, to, variant, label }]` covering 0→max for Cold/Warm/Hot, variants error/warning/success).\n- **Signals datagrid** (`{{datagridCaption}}`, `{{datagridRows}}`) — one row per signal, strongest first: `signal` (name), `dir` (badge `{ value, badgeVariant }` — success Positive / warning Watch), `when` (ISO `YYYY-MM-DD`), `note` (detail), plus a leading `status` object (`{value,badgeVariant}` — value Buy/Watch, badgeVariant success/warning); the leading Status column reads each row's `status`.\n- **One synthesis callout** (`variant:\"success\"`) closes the widget — `{{calloutTitle}}` (the single most important read) and `{{calloutDescription}}`, with two real buttons: primary `action/sendMessage` (`{{primaryButtonLabel}}` / first-person `{{primaryButtonContent}}`) and secondary \"View in Salesforce\" `action/openLink` to `{{oppUrl}}` (`https://<myDomain>/lightning/r/Opportunity/<Id>/view`; omit if you lack the Id). No decorative buttons.\nBefore calling, verify: no `{{…}}`/`{!…}` remain; `{{chartCategories}}`/`{{chartSeries}}`/`{{meterBands}}`/`{{datagridRows}}` are arrays and `{{meterValue}}`/`{{meterMax}}`/`{{meterTarget}}` numbers; both buttons wired (real sendMessage `content`, openLink `url`); two graphs present; the callout closes it. Tokens: title subtitle dealContext headerStatus meterLabel/Value/Max/Target/ValueLabel/TargetLabel/Status/Bands chartCaption/chartCategories/chartSeries datagridCaption/datagridRows calloutTitle/calloutDescription primaryButtonLabel/primaryButtonContent oppUrl.",
  "props": {
    "title": {
      "description": "Header title for the buying-signals view.",
      "type": "string",
      "example": "Buying signals — Cobalt Robotics"
    },
    "headerStatus": {
      "description": "Header status badge (overall signal strength).",
      "type": "string",
      "example": "STRONG BUY"
    },
    "subtitle": {
      "description": "Caption: composite score, trend, and signal counts.",
      "type": "string",
      "example": "Signal score 74 / 100 · trending up · 3 strong buys, 1 warning"
    },
    "dealContext": {
      "description": "Muted second caption with the opp's shared deal facts — stage · amount · close date · next step · last activity, joined by ' · '.",
      "type": "string",
      "example": "Negotiation · $1.8M · close Sep 30 · next: exec review Jul 28 · last activity Jul 20"
    },
    "chartCaption": {
      "description": "Caption for the 6-week signal-score trend line chart.",
      "type": "string",
      "example": "Signal score, last 6 weeks"
    },
    "chartCategories": {
      "description": "Week labels for the trend chart's x-axis, as strings.",
      "type": "array",
      "items": {
        "type": "string"
      },
      "example": [
        "Wk 1",
        "Wk 2",
        "Wk 3",
        "Wk 4",
        "Wk 5",
        "Wk 6"
      ]
    },
    "chartSeries": {
      "description": "Trend series — one object {name, data}.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "description": "Series name.",
            "type": "string"
          },
          "data": {
            "description": "Weekly signal scores — a number array matching chartCategories.",
            "type": "array",
            "items": {
              "type": "number"
            }
          }
        }
      },
      "example": [
        {
          "name": "Score",
          "data": [
            48,
            52,
            60,
            63,
            70,
            74
          ]
        }
      ]
    },
    "meterLabel": {
      "description": "Label for the composite-score meter.",
      "type": "string",
      "example": "Composite signal score"
    },
    "meterValue": {
      "description": "Composite signal score — the meter's current value.",
      "type": "number",
      "example": 74
    },
    "meterMax": {
      "description": "The meter's max.",
      "type": "number",
      "example": 100
    },
    "meterTarget": {
      "description": "Target marker on the meter.",
      "type": "number",
      "example": 70
    },
    "meterValueLabel": {
      "description": "Display string for the score.",
      "type": "string",
      "example": "74 / 100"
    },
    "meterTargetLabel": {
      "description": "Display string for the target.",
      "type": "string",
      "example": "70 = strong"
    },
    "meterStatus": {
      "description": "Short read shown on the meter (Cold / Warm / Hot).",
      "type": "string",
      "example": "strong buy"
    },
    "meterBands": {
      "description": "Color bands for the meter, in order covering 0→max (Cold / Warm / Hot).",
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
          "to": 40,
          "variant": "error",
          "label": "Cold"
        },
        {
          "from": 40,
          "to": 70,
          "variant": "warning",
          "label": "Warm"
        },
        {
          "from": 70,
          "to": 100,
          "variant": "success",
          "label": "Hot"
        }
      ]
    },
    "datagridCaption": {
      "description": "Caption for the signals datagrid.",
      "type": "string",
      "example": "Signals detected, strongest first"
    },
    "datagridRows": {
      "description": "Buying signals — one row per signal, strongest first. Empty array → the datagrid is omitted.",
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
          "signal": {
            "description": "Signal name.",
            "type": "string"
          },
          "dir": {
            "description": "Direction badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Direction label (Positive / Watch).",
                "type": "string"
              },
              "badgeVariant": {
                "description": "Badge color: success=Positive, warning=Watch.",
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
          "when": {
            "description": "Signal date, ISO YYYY-MM-DD.",
            "type": "string"
          },
          "note": {
            "description": "Short detail for the signal.",
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
          "signal": "Budget approved",
          "dir": {
            "value": "Positive",
            "badgeVariant": "success"
          },
          "when": "2026-07-06",
          "note": "CFO confirmed renewal + expansion budget"
        },
        {
          "status": {
            "value": "Buy",
            "badgeVariant": "success"
          },
          "signal": "Multi-thread widening",
          "dir": {
            "value": "Positive",
            "badgeVariant": "success"
          },
          "when": "2026-07-13",
          "note": "5 contacts engaged, up from 2"
        },
        {
          "status": {
            "value": "Buy",
            "badgeVariant": "success"
          },
          "signal": "Usage climbing",
          "dir": {
            "value": "Positive",
            "badgeVariant": "success"
          },
          "when": "2026-07-18",
          "note": "Platform seats +12% this month"
        },
        {
          "status": {
            "value": "Watch",
            "badgeVariant": "warning"
          },
          "signal": "Competitor mentioned",
          "dir": {
            "value": "Watch",
            "badgeVariant": "warning"
          },
          "when": "2026-07-20",
          "note": "CIO referenced in-house build option"
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the single most important read.",
      "type": "string",
      "example": "Signals say press now"
    },
    "calloutDescription": {
      "description": "Synthesis callout body — the read and the move.",
      "type": "string",
      "example": "Score climbed 48→74 in six weeks on budget approval, wider threading, and rising usage. The one caution is the CIO's in-house-build comment — get ahead of it in the exec meeting and this closes on time."
    },
    "primaryButtonLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft exec ask"
    },
    "primaryButtonContent": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft an exec ask for the Cobalt meeting focused on addressing the in-house-build option the CIO mentioned."
    },
    "oppUrl": {
      "description": "Opportunity Lightning URL for the secondary \"View in Salesforce\" button; omit if no Id.",
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
            "attributes": { "gap": "sm", "align": "center", "justify": "between", "isWrapped": true },
            "children": [
              {
                "definition": "tile/row",
                "attributes": { "gap": "sm", "align": "center" },
                "children": [
                  { "definition": "tile/icon", "attributes": { "name": "activity", "size": "xl", "alt": "" } },
                  { "definition": "tile/text", "attributes": { "text": "{{title}}", "variant": "h1" } }
                ]
              },
              { "definition": "tile/badge", "attributes": { "label": "{{headerStatus}}", "variant": "success" } }
            ]
          },
          { "definition": "tile/text", "attributes": { "text": "{{subtitle}}", "variant": "caption", "color": "muted" } },
          { "definition": "tile/text", "attributes": { "text": "{{dealContext}}", "variant": "caption", "color": "muted" } },

          { "definition": "tile/separator" },

          {
            "definition": "tile/column",
            "attributes": { "gap": "md" },
            "children": [
              {
                "definition": "tile/chart",
                "attributes": {
                  "chartType": "line",
                  "caption": "{{chartCaption}}",
                  "categories": "{{chartCategories}}",
                  "series": "{{chartSeries}}",
                  "valueFormat": "number",
                  "showValues": false,
                  "showLegend": false
                }
              },
              {
                "definition": "tile/meter",
                "attributes": {
                  "label": "{{meterLabel}}",
                  "value": "{{meterValue}}",
                  "min": 0,
                  "max": "{{meterMax}}",
                  "target": "{{meterTarget}}",
                  "valueFormat": "number",
                  "valueLabel": "{{meterValueLabel}}",
                  "targetLabel": "{{meterTargetLabel}}",
                  "status": "{{meterStatus}}",
                  "size": "lg",
                  "bands": "{{meterBands}}"
                }
              }
            ]
          },

          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{datagridCaption}}",
              "appearance": "striped",
              "columns": [
                { "key": "status", "header": "Status", "type": "badge" },
                { "key": "signal", "header": "Signal", "type": "text" },
                { "key": "dir", "header": "Direction", "type": "badge" },
                { "key": "when", "header": "Detected", "type": "date" },
                { "key": "note", "header": "Detail", "type": "text" }
              ],
              "rows": "{{datagridRows}}"
            }
          },

          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "success",
              "title": "{{calloutTitle}}",
              "description": "{{calloutDescription}}"
            },
            "children": [
              {
                "definition": "tile/row",
                "attributes": { "gap": "sm", "align": "center", "isWrapped": true },
                "children": [
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{primaryButtonLabel}}",
                      "variant": "primary",
                      "actions": { "click": [ { "definition": "action/sendMessage", "attributes": { "content": "{{primaryButtonContent}}" } } ] }
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "View in Salesforce",
                      "iconName": "open-in-new",
                      "variant": "secondary",
                      "actions": { "click": [ { "definition": "action/openLink", "attributes": { "url": "{{oppUrl}}" } } ] }
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

Per fired signal, surface the trigger value **plus one or two supporting facts** from the Step 2 record (all already fetched — no new read), separated by ` • ` so the evidence is scannable, not a single condensed fact. Blank line between the 🔴 and 🟡 groups.

```
# Deal Signals — <as-of local date> — <scope> — <effective CloseDate window or all open dates>

🔴 Act today
- **<Account / Opp>** — <signal> — <StageName label> • $<Amount> • close <CloseDate> • last activity <LastActivityDate> • next step <NextStep> → <action>

🟡 This week
- **<Account / Opp>** — <signal> — <trigger value> • <supporting fact> • <supporting fact> → <action>

✅ Nothing else crossed a threshold (<N> opps swept)
```
Link each record. CRM fix → offer `update-opportunity`; a touch → `draft-outreach`/`schedule-meeting`. Scheduled run: lead with count of new items since last run; a quiet digest is success.

**Complete digest — Quick/Kiro adaptation:** List every deal that fired a signal, under its strongest signal; lower-priority deals in the same group may share one line, but never drop a flagged deal to shorten the digest. Always end with the ✅ line. Before sending, check that the number of deals listed equals the number that fired a signal.
