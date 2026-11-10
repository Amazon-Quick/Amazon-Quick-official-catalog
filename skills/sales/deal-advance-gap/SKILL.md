---
name: deal-advance-gap
description: "Map an opportunity's path to advance or close from Salesforce stage, stakeholder, activity, qualification, and risk data plus email, documents, and Slack. Use to diagnose a stuck deal, identify blockers and owners, or test whether its close date is credible."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:c7adb572b50cc6d1793a1f3ba161fdab159ccc2e4f4798550bd2fd7d4e45448e"
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

- Apply the human-label rule to Opportunity child records too. State a risk as "Blocking: yes · Severity: High · Status: Mitigating", never `Is_Blocking__c = true`.

# Deal Advance Gap

Forward-looking: against the org's stage exit criteria, what has to happen for this deal to advance — and the shortest path to it. Ground → resolve to one Id (+ evidence, ONE turn) → detail read → map gaps → sequence → output.

## 1. Ground (hardcoded — Opportunity only)

Ground **only Opportunity** — it always exists (naming a missing object fails the whole call). Its fields + childRelationships reveal this org's stage/qualification/next-step schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label relationshipName } childRelationships { childObjectApiName relationshipName } } stages: objectInfos(objectInfoInputs: [{ apiName: \\\"Opportunity\\\", recordTypeIDs: [\\\"012000000000000AAA\\\"], fieldNames: [\\\"StageName\\\"] }]) { fields { ApiName ... on PicklistField { picklistValuesByRecordTypeIDs { recordTypeID picklistValues { label value } } } } } } }\"}" })
```

Step 1 is the authority on names. Note: (a) scalar `__c` fields carrying stage-exit / next-step / blocker / qualification signal — take `{ value }` **and keep each field's `label`**; (b) each lookup's exact `relationshipName` for spanning a related name; (c) each child `relationshipName`. **Build an ApiName→label map now and use the `label` in ALL output** (e.g. "Executive Sponsor", not `Executive_Sponsor__c`; "Target Resolution Date", not `Target_Resolution_Date__c`) — never print a `__c` API name to the user.

`stages` lists the Stage picklist in the org's order, read from the primary record type (`012000000000000AAA`). It is the authority on stage order; never infer the next stage from general sales knowledge.

## 2a. Resolve to ONE opportunity Id (before the detail read)

Given an SFDC **Id** already → skip to 2b with `Id: { eq: "<Id>" }`. Given a **name**, resolve it first — `first: 1` on a `Name like` only caps the response; it does **not** pick the right deal, so on a multi-match it returns an arbitrary one. Run a bounded, ordered candidate query over open deals, since only an open deal can advance (`%DEALNAME%` = 1–2 distinctive words; when the request also names the account, use `%<account word>%<deal words>%`):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%DEALNAME%\\\" }, IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { totalCount edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Account { Name { value } } } } } } } }\"}" })
```

- **`totalCount` above the rows returned** → the list is cut off and may not include the requested deal. Narrow `%DEALNAME%` (add the account or another distinctive word) and retry once; if it is still cut off, say how many open deals match and ask for the account. Never ask the user to choose from a cut-off list.
- **Exactly one** candidate → take its `Id`, go to 2b.
- **Several** → list them (Account · Name · Stage · $ · close) and **ask which**; don't guess.
- **None** → broaden `%…%` and retry once.

## 2b. Read the resolved opp by Id (fill from step 1)

Filter by the **exact Id** from 2a (`first: 1` is correct here — the filter is a unique record Id). **Reference-field rules (avoids the retry loop):**
- Scalar/`__c` → `Field__c { value }`. `displayValue` is null for Id fields — don't rely on it.
- Related record's name → span the exact `relationshipName` from Step 1: `<relationshipName> { Name { value } }`. Do NOT append `{ … }` to a raw `Id`/`__c` field.
- No usable relationshipName → take the `__c { value }` (Id) and move on — **do not retry**.

Insert `<OPP_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed relationship (`<relationshipName> { Name { value } … }` for a lookup; `<childRelationshipName> { edges { node { … } } }` for a child). Standard fields + `OpportunityContactRoles` always work.

**Before dispatching, double-check the query's braces balance** (count `{` vs `}` — they must be equal). Splicing `<OPP_CUSTOM>`/`<REL_BLOCKS>` is where a `}` gets dropped; keep the read flat (no unnecessary nesting).

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } ForecastCategoryName { value } LastActivityDate { value } <OPP_CUSTOM> Account { Name { value } } Owner { Name { value } } <REL_BLOCKS> OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } Tasks(first: 15, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Status { value } Description { value } TaskSubtype { value } } } } Events(first: 10, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } } } }\"}" })
```

**Forecast category — local correction:** Both reads return `ForecastCategoryName` (Pipeline, Best Case, Commit, Closed, Omitted), the category reps see. `ForecastCategory` returns internal values, such as `Forecast` for Commit, that are not labels.

Target = the stage that follows the deal's current stage in step 1's `stages` order (default; when that is Closed Won, the target is to close), or "to close" if asked.

**Retry contract on `InvalidSyntax` / "offending token `<EOF>`" (the dynamic splice dropped a brace):** construct **one** corrected query and dispatch it **only if its text differs** from the failed one (add the missing `}` — never re-send byte-identical text; an identical retry just burns a round-trip for the same error). If that corrected retry still fails, **stop retrying the spliced shape** — fall back to the fixed, guaranteed-field query below (standard fields + contact roles only, no `<OPP_CUSTOM>`/`<REL_BLOCKS>`), then continue the analysis and note that optional custom risk signals were unavailable:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Probability { value } NextStep { value } ForecastCategoryName { value } LastActivityDate { value } Account { Name { value } } Owner { Name { value } } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } } } } } } }\"}" })
```

## 2c. Evidence (run IN PARALLEL with 2a — same turn, issue all at once)

**Issue 2a and all of 2c in a single turn** — these searches key on the deal/account name from the *request* (not the SF read), so batch them with candidate resolution; only 2b's detail read waits on the resolved Id. Keyed on the deal/account:
- **email**: last exchange per contact, open commitments in both directions, silence/OOO/departure
- **docs**: latest transcript/notes → decisions, objections, open commitments, competitor mentions
- **slack**: internal blockers — deal desk, legal, security review, pricing approval

Use whatever email/doc/Slack tools are present; if none, skip silently (SF-only is fine). Cite source + date for anything used.

**No extra Salesforce reads.** 2b already returned the CRM state (stage, close, next step, probability, forecast, last-activity, contact roles, recent Tasks/Events, `__c` signals). Do NOT dispatch a **separate** per-opp SF follow-up (a standalone `ActivityHistory` / `OpportunityFieldHistory` / Task query) — recent activity already rides along as the `Tasks`/`Events` child edges in the 2b query (same round-trip, no extra call). Read those children as distinct states: a completed Task (Status Completed / past-dated Event) is a done touch; an open Task or a future-dated Task/Event is **🔶 In motion / scheduled**, not done — that's the signal behind "Already in motion". Deeper detail comes from the external evidence above.

## 3. Map gaps against exit criteria (cite every claim; invent nothing)

Exit criteria, qualification framework, and required-stakeholders-for-close are **external knowledge** — infer from the org's own data (StageName picklist, closed-won patterns) or ask the user once. Never invent. For the current stage's exit criteria (and every later stage if target is "to close"), mark each: **✅ Done / 🔶 In motion / ❌ Not started**, with the source and the specific gap. Then check the qualification framework the same way — flag only elements that **block advancement**, not every unknown.

**Row states — Quick/Kiro adaptation:** Take every Done, In motion, or Scheduled state from 2b's Tasks and Events. Done needs a completed Task or a past-dated Event; In motion or Scheduled needs an open Task or a future-dated Task or Event for that step. A step that exists only as Next Step text, or a completed touch still awaiting a reply, is Not started.

**Suggested steps — Quick/Kiro adaptation:** The documented reads do not return the org's exit criteria. Unless the user names them, present the checklist as suggested steps instead of asking. Base each step on this deal's returned data and cite it. Say "suggested steps" wherever the output would say exit criteria, including `headerSubtitle` and `meterValueLabel` (for example, "1 of 5 suggested steps complete"), and say in the callout that these are not the org's defined criteria.

## 4. Sequence the path

Order gaps into the shortest credible path: whose gap (Us / Customer / internal team), parallel vs. strictly sequential, and the single next action that unblocks the most downstream items. Critical-path length → earliest credible close; flag if that lands after the current CloseDate.

## 5. Output — widget FIRST (the rendered UI is the default)

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] Row states (Quick/Kiro adaptation): every row marked In motion or Scheduled names the open or future-dated task or event behind it in its `item` text. If it cannot, set that row to Not started; a completed touch awaiting a reply is never In motion.

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules).

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): `headerTitle headerStatus headerSubtitle` (strings) · `meterValue meterMax meterTarget` (numbers — meter `value`/`max`/`target`) · `meterValueLabel meterTargetLabel meterStatus` (strings) · `meterBands` (array: `[{ from, to, variant, label }]` — variants error/warning/success, covering 0→max) · `gridCaption` (string) · `gridRows` (array, one per gap, blockers first: `[{item, owner (plain string — format as the person's display name (e.g. \"You\", \"R. Chen\"); names must be plain strings, not objects: use `User.Name.value` or `Owner.Name.value` from the SF response), due (YYYY-MM-DD), state: {value, badgeVariant}, status:{value,badgeVariant}}]` — `status.value` \"Blocker\"/\"At risk\"/\"On track\"/\"Done\", `status.badgeVariant` error/warning/info/success; every row cites its source) · `calloutTitle calloutDescription` (strings) · `ctaPrimaryLabel ctaPrimaryMsg` (strings — `ctaPrimaryMsg` is the first-person prompt for action/sendMessage) · `oppUrl` (string — Lightning URL `https://<myDomain>/lightning/r/Opportunity/<Id>/view`).",
  "props": {
    "headerTitle": {
      "description": "Header title for the stage-advance gap view.",
      "type": "string",
      "example": "What's needed to advance — Cobalt Robotics"
    },
    "headerStatus": {
      "description": "Header status badge.",
      "type": "string",
      "example": "4 OPEN"
    },
    "headerSubtitle": {
      "description": "Subtitle summarizing the gap to the next stage.",
      "type": "string",
      "example": "Negotiation → Closed Won · 4 exit criteria open · 6 days to close"
    },
    "meterValue": {
      "description": "Readiness/progress toward the next stage — the meter's current value.",
      "type": "number",
      "example": 3
    },
    "meterMax": {
      "description": "The meter's max.",
      "type": "number",
      "example": 7
    },
    "meterTarget": {
      "description": "Target marker on the meter.",
      "type": "number",
      "example": 7
    },
    "meterValueLabel": {
      "description": "Display string for the current value.",
      "type": "string",
      "example": "3 of 7 exit criteria complete"
    },
    "meterTargetLabel": {
      "description": "Display string for the target.",
      "type": "string",
      "example": "7 to advance"
    },
    "meterStatus": {
      "description": "Short readiness read shown on the meter.",
      "type": "string",
      "example": "4 open"
    },
    "meterBands": {
      "description": "Color bands for the meter, in order covering 0→max.",
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
          "to": 4,
          "variant": "error",
          "label": "Blocked"
        },
        {
          "from": 4,
          "to": 7,
          "variant": "warning",
          "label": "Nearly"
        },
        {
          "from": 7,
          "to": 7,
          "variant": "success",
          "label": "Ready"
        }
      ]
    },
    "gridCaption": {
      "description": "Caption for the gaps datagrid.",
      "type": "string",
      "example": "Gap-to-close checklist, blockers first"
    },
    "gridRows": {
      "description": "Stage-exit gaps — one row per gap, blockers first. Empty array → the datagrid is omitted.",
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
          "item": {
            "description": "The gap / required item; cite its source.",
            "type": "string"
          },
          "owner": {
            "description": "Gap owner's display name, a plain string (use User.Name.value or Owner.Name.value — never a nested object).",
            "type": "string"
          },
          "due": {
            "description": "Target date to close the gap, ISO YYYY-MM-DD.",
            "type": "string"
          },
          "state": {
            "description": "Status badge cell for the gap.",
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
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Blocker",
            "badgeVariant": "error"
          },
          "item": "Redlines returned to legal",
          "owner": "You",
          "due": "2026-07-24",
          "state": {
            "value": "Not started",
            "badgeVariant": "error"
          }
        },
        {
          "status": {
            "value": "At risk",
            "badgeVariant": "warning"
          },
          "item": "Security review signed off",
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
          "item": "Final pricing approved (CFO)",
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
          "item": "Procurement PO issued",
          "owner": "Buyer",
          "due": "2026-07-29",
          "state": {
            "value": "Waiting",
            "badgeVariant": "warning"
          }
        },
        {
          "status": {
            "value": "Done",
            "badgeVariant": "success"
          },
          "item": "Metrics agreed",
          "owner": "You",
          "due": "2026-07-18",
          "state": {
            "value": "Done",
            "badgeVariant": "success"
          }
        },
        {
          "status": {
            "value": "Done",
            "badgeVariant": "success"
          },
          "item": "Economic buyer confirmed",
          "owner": "You",
          "due": "2026-07-16",
          "state": {
            "value": "Done",
            "badgeVariant": "success"
          }
        },
        {
          "status": {
            "value": "Done",
            "badgeVariant": "success"
          },
          "item": "Mutual close plan signed",
          "owner": "You",
          "due": "2026-07-17",
          "state": {
            "value": "Done",
            "badgeVariant": "success"
          }
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the top blocker to advancing the stage.",
      "type": "string",
      "example": "Two of the four opens are yours to unblock"
    },
    "calloutDescription": {
      "description": "Synthesis callout body — the blocker and the move.",
      "type": "string",
      "example": "Redlines and the CFO pricing sign-off sit with your side. Send the contract to legal today and confirm Marcus's Friday CFO slot — that clears the critical path and leaves only procurement's PO on the buyer."
    },
    "ctaPrimaryLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft action plan"
    },
    "ctaPrimaryMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft an action plan to clear the legal blocker and confirm the CFO pricing slot for the Cobalt Robotics deal."
    },
    "oppUrl": {
      "description": "Opportunity Lightning URL for the \"View in Salesforce\" button; omit if no Id.",
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
                      "name": "trending-up",
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
              "text": "{{headerSubtitle}}",
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
              "label": "Exit criteria met",
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
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{gridCaption}}",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "item",
                  "header": "Exit criterion",
                  "type": "text"
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
              "rows": "{{gridRows}}"
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
# Advance Gap: <Name> — <current stage> → <target>
**Short answer:** <1–2 lines: advances when X and Y; critical path runs through Z>

## Gaps blocking advancement
| # | Gap | Owner (Us/Customer/team) | Blocking (gate/close req) | Evidence (source+date) |

## Already in motion
- <underway items + expected landing — don't re-ask>

## The path
1. <action — who — by when> (unblocks #n)
   Critical path ~<N> weeks → earliest credible close <date> (flag if after CloseDate)

## Suggested SFDC updates
- NextStep → "<the #1 action>" · CloseDate → <if path math says current date isn't credible>
[Apply with `update-opportunity`, or manually if read-only.]
```
