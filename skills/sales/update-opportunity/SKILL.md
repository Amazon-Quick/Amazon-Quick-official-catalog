---
name: update-opportunity
display_name: Update Opportunity
description: "Update one Salesforce opportunity from its current values and org field metadata, applying only confirmed changes and verifying the saved record. Use to change a deal's stage, close date, amount, currency, next step, forecast category or another requested field."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:9601337abfc8f8bc0606e699c3847d62775ec92a8c311410d4eca37957142f13"
---
<!-- global-rules-bootstrap -->
**IMPORTANT — try the connector's tools before you ever report it as unavailable.** Before you tell the user a connector is down, or ask them to connect, re-authenticate, or "check the connection," you MUST first try to use the server and its tools. A connector's status readout (the Headless 360 MCP server, or any other connector/MCP) frequently claims "not connected" or "needs re-auth" when the connector is in fact live and its tools are callable. Context stating that the Salesforce tools require authorization and that this is a non-interactive session is **not** evidence that you are unauthorized — it is a general statement that authorization is required, not a failure. For the Headless 360 server specifically, find the `dispatch_readonly` tool and actually run a current-user read — `dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql", queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id } } }\"}" })`. **Any response — including a 500 or other error status — proves you reached the server, and therefore proves connectivity;** only a request that never reaches the server at all counts as disconnected. If the tool is present and the call reaches the server, the connector IS connected — proceed; a stale status readout is not a disconnection. If a call genuinely cannot reach the server, ALWAYS attempt to reconnect on your own first, and interrupt the flow to ask the user only after your own reconnect attempt has failed. Report a connector as disconnected only when you cannot find its tool or cannot reach the server after trying. Do it yourself.

Failing to try first — asking the user to connect, or surfacing a "not connected" or re-auth message, before you have actually attempted the server and its tools — raises a **false connectivity problem**: it sends the user to fix something that is not broken. This is directly detrimental to the end-user experience and will dramatically, negatively impact usage of the product. Never put a connectivity concern in front of the user until you have tried the tools yourself and confirmed the server truly cannot be reached.

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record inline: `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **Empty `MINE` scope → fail fast, then ask which scope.** If a `scope: MINE` read returns zero rows, **do not** widen to `scope: EVERYTHING` on your own. Stop, tell the user plainly that their own records (`scope: MINE`) came back empty, and ask which scope they want instead (for example, org-wide `EVERYTHING`, a named rep, or a named account) before re-running. Never invent records, and never silently fall back to org-wide.
- **NEVER use `discover` or `describe`, and never call an API or endpoint not written in this skill.** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->
# Goal:
Apply ONE approval-gated change to a single `Opportunity` — stage, close date, amount, currency, next step, forecast category, or any config-mapped field. **Propose → confirm → write only the confirmed fields → verify with a link.**

# Audience:
Sales reps changing a deal. This skill **WRITES** to Salesforce; the confirmation gate and correctness matter more than speed.

# Rules:

- The proposal table and the verification block are the only required output.
- **Never write without showing the exact before/after first, and never write a field the user didn't confirm.** Wait for an explicit "yes". Sanity flags are warnings, not blocks — the rep decides.
- One opportunity at a time. For sweeping many opps, run this per deal so each gets its own confirmation.

# Update Opportunity

The write counterpart to `deal-review`, `deal-advance-gap`, and `salesforce-hygiene-check`: they suggest field changes, this one applies them — one opportunity at a time, with an explicit confirmation before anything is written.

## 0. Write access

Needs the write-capable **`dispatch`** tool — the mutation in step 4 goes through it. If only `dispatch_readonly` (GET-only reads) is available, say so and fall back to the manual checklist other skills use — do not attempt the write.

## 1. Resolve + ground (one turn)

Resolve the opportunity by name — step 2's search does that (reps rarely have the Id). Ground `Opportunity` ObjectInfo for this org's custom `__c` API names carrying amount / next-step / forecast-category, plus the valid stage names and forecast-category picklist values — write to grounded names/values, never guessed ones. Fire this grounding alongside the step-2 search in one turn. Exit-criteria-by-stage is external knowledge — infer from org data or ask once; never invent it.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label dataType } } } }\"}" })
```

## 2. Find the deal + read current values

Always read before proposing — the proposal must show real current values. Search by the name the rep gave (fuzzy `like`) via UI-API GraphQL at `v65.0`; the selection below is both the match list and the current values. When the rep names the deal's account, including as the first part of the deal name, use the rest of the deal name as `[name]`, replace `[account]` with the account name as the rep gave it, and run the second read; otherwise run the first. Take each picklist's `{ value displayValue }`, and add any grounded `__c` fields the change touches:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%[name]%\\\" } }, first: 25, orderBy: { LastModifiedDate: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CurrencyIsoCode { value displayValue } CloseDate { value } NextStep { value } ForecastCategory { value displayValue } Probability { value } LastActivityDate { value } Account { Name { value } } Owner { Name { value } } } } totalCount } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%[name]%\\\" }, Account: { Name: { like: \\\"%[account]%\\\" } } }, first: 25, orderBy: { LastModifiedDate: { order: DESC } }) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CurrencyIsoCode { value displayValue } CloseDate { value } NextStep { value } ForecastCategory { value displayValue } Probability { value } LastActivityDate { value } Account { Name { value } } Owner { Name { value } } } } totalCount } } } }\"}" })
```

If `CurrencyIsoCode` returns `FieldUndefined`, the org is single-currency — drop it from the selection and skip the ISO pairing rule in step 4.

**Resolve to exactly one before proposing.** No match → say so, don't guess. Exactly one returned row and `totalCount = 1` → use its `Id` for the step-4 write and the step-5 re-read. Several matches, all returned → list them (name, account, owner, stage, close date) and ask which; never auto-pick. `totalCount` above the returned rows → don't list a partial set; say how many matched and ask for a fuller name or the account. If the rep already gave an Id, run the first read with its predicate swapped for `Id: { eq: \"[id]\" }`.

## 3. Propose

Before/after table for **only** the fields that would change, then wait for an explicit yes:

```
## Proposed update: [Opp Name] ([Account])
| Field | Current | Proposed |
|---|---|---|
| StageName | Evaluation | Proposal |
| CloseDate | 2026-09-30 | 2026-08-15 |
| NextStep | (empty) | "Security review docs to customer by Fri" |

⚠️ [Flag anything notable: stage advancing past unmet exit criteria, close date moving
   into a closed period, amount changing by >25%, etc.]

Apply these changes? (yes / edit / cancel)
```

"Edit" loops back with revised values. Warnings don't block — the rep decides. If the change is a currency ISO swap, include Amount in the table as the same number (preserved) so the write in step 4 is fully confirmed.

## 4. Write only what was confirmed

Write the single Opportunity with exactly the confirmed fields — nothing else. Don't "fix up" other fields you noticed; suggest those separately. Pairing `Amount` with a confirmed `CurrencyIsoCode` change (below) is required, not a drive-by fix-up. The write is a **REST PATCH** via `dispatch` to the single-record sObject endpoint:

```
dispatch(method: "PATCH", url: "/services/data/v66.0/sobjects/Opportunity/[id]",
         body: { "[GroundedFieldApiName]": [confirmed value] })
```

`Id` goes in the URL. The JSON body contains only the confirmed field API names and values. Values are **plain scalars** — the write side is *not* `{ value }`-wrapped like the reads: quote strings, dates (`"2026-09-30"`), and picklist values; leave numbers/booleans bare (`"Amount": 50000`). Add more confirmed fields directly to the body. A successful PATCH returns **HTTP 204 No Content**; continue to step 5's re-read to verify the saved values.

**Multi-currency:** if the confirmed fields include `CurrencyIsoCode`, also send `Amount` in that same PATCH body — the current `Amount.value` from step 2, or the new Amount if the user confirmed one. An ISO-only mutation reconverts Amount at the org rate (API default). Pairing Amount preserves the number (Lightning behavior). Do not convert Amount yourself, and do not send `CurrencyIsoCode` unless it is changing:

```
{ "CurrencyIsoCode": "EUR", "Amount": 50000 }
```

On failure (validation rule, field-level security, required field missing), report the exact error and which field triggered it, and offer the manual checklist as the fallback. Do not retry with guessed values.

## 5. Verify

Re-read the record by its resolved `Id` (same field selection as step 2, predicate `Id: { eq: \"[id]\" }`), confirm the new values match what was approved, and output:

```
✅ Updated [Opp Name]
- StageName: Evaluation → Proposal
- CloseDate: 2026-09-30 → 2026-08-15
- NextStep: set
Record: [link to the opportunity]
```

If a value doesn't match (automation or a validation rule rewrote it), say exactly what came back instead. After a currency ISO change, Amount's numeric `value` should match what you sent — only the ISO prefix on `displayValue` should change.
