---
name: assign-target-to-sdr
display_name: Assign Target to SDR (Preview)
description: "Assign a Salesforce Lead or Contact to an active Agentforce Engagement Agent using target records and Agentforce agent definitions, after confirming both. Use to hand a prospect to Agentforce for automated qualification and email outreach."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:eebe5444312b6406ab17f467f5a34524c8de06c68bcecc524ed7945d053e1ee8"
id: "70da2230-ac60-4b95-9b67-37779d10e722"
---
<!-- global-rules-bootstrap -->

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record inline: `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **One idea per sentence.** In all generated content, if a sentence needs re-reading, it is carrying too much: split it.
- **Don't repeat the visual.** When a visualization or widget renders, the text around it tells the user what to conclude from the data. Do not restate numbers they can already see.
- **Use plain language.** Choose terms any reader understands on first read, with no domain knowledge or cultural context required. Avoid jargon and colloquialisms, and make labels signal what follows. Test: would a reader unfamiliar with the idiom understand the term and know what content to expect? Use "No engagement", not "went dark" or "ghosted".
- **Reproduce Salesforce terminology exactly.** Use the field labels, object names, and stage values the data returns; do not paraphrase them. Spell out acronyms on first use unless the term is an industry framework (for example, MEDDIC).
- **Empty `MINE` scope → fail fast, then ask which scope.** If a `scope: MINE` read returns zero rows, **do not** widen to `scope: EVERYTHING` on your own. Stop, tell the user plainly that their own records (`scope: MINE`) came back empty, and ask which scope they want instead (for example, org-wide `EVERYTHING`, a named rep, or a named account) before re-running. Never invent records, and never silently fall back to org-wide.
- **While following this skill, don't call `discover` or `describe`, and don't call any API or endpoint not written here. This file already has every query and widget reference you need. (Outside this skill, they're available as normal.)** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->
# Assign Target to SDR

Resolve target + list agents (ONE turn, batched) → confirm → invoke → report.

**The contract:** never invoke without showing the user which target and which agent first. The user picks the agent; never guess `botDefinitionId`.

## 0. Write access

This invokes a write action - needs a Salesforce connector with create/update access. Read-only connector → say so and stop, there is no read-only fallback.

## 1. Resolve target + list agents (batch — fire both in the SAME turn)

These are independent (target lookup doesn't depend on the agent list, or vice versa) — issue both dispatches in one turn, not sequentially.

**Target — Contact + Lead in one GraphQL call.** This read uses only standard fields (`Name`, `Email`, `Title`, `Company`, `Status`, `Account.Name`), so it needs no ObjectInfo grounding — grounding is for custom/org-specific fields, and there are none here. Both objects are UI-API-serviceable, so query them as two roots of the same GraphQL request rather than splitting one to SOQL:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { or: [{ Name: { like: \\\"%MATCH%\\\" } }, { Email: { eq: \\\"%MATCH%\\\" } }] }, first: 5) { edges { node { Id Name { value } Email { value } Title { value } Account { Name { value } } } } } Lead(where: { and: [{ or: [{ Name: { like: \\\"%MATCH%\\\" } }, { Email: { eq: \\\"%MATCH%\\\" } }] }, { IsConverted: { eq: false } }] }, first: 5) { edges { node { Id Name { value } Email { value } Company { value } Status { value } } } } } } }\"}" })
```

`%MATCH%` = the name/email the user gave. If they gave a `003…`/`00Q…` Id directly, skip this read and use it as `targetId`. If a field this read names is missing on the org (a `FieldUndefined`), re-ground Contact/Lead via `objectInfos` and drop it — don't fall back to discovery.

**Agents (BotVersion — the one read that must be SOQL: UI-API GraphQL doesn't serve `BotVersion`):**

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT BotDefinitionId, BotDefinition.MasterLabel, BotDefinition.Description FROM BotVersion WHERE Status = 'Active' AND BotDefinition.AgentType = 'EinsteinSDR'" })
```

(Swap `EinsteinSDR` for the org's custom agent type if asked.)

**Resolve:**
- Target: exactly one match → `targetId`. Multiple → show candidates (Name, Contact/Lead, Email, Account/Company), ask which. None → say so, ask for the Id, don't invent a record.
- Agents: one or more → present MasterLabel + Description, ask which (or match a name the user already gave). None active → tell the user, stop — nothing to assign to.

## 2. Confirm

```
## Assign to Agentforce Engagement Agent
| | |
|---|---|
| Target | [Name] ([Contact/Lead], [Account/Company]) - [link] |
| Agent | [MasterLabel] |

The agent will begin qualifying this prospect and reaching out by email. Proceed? (yes / pick another agent / cancel)
```

Wait for explicit yes. "Pick another agent" loops back to the Step 1 agent list (already fetched — don't re-query).

## 3. Invoke

The `assignTargetToSdr` standard action only exists on newer API versions, so a hardcoded version can 404. Resolve the version first (once per session; reuse it if already resolved) and substitute it for `<apiVersion>` below:

```
dispatch_readonly(method: "GET", url: "/services/data/")
```

The response lists the org's supported versions - pick the highest.

```
dispatch(method: "POST", url: "/services/data/<apiVersion>/actions/standard/assignTargetToSdr",
         body: { "inputs": [{ "targetId": "[resolved Id]", "botDefinitionId": "[chosen BotDefinitionId]" }] })
```

## 4. Report

Success = the assignment record was created — ignore downstream email-delivery errors in the response, still report success.

```
✅ Assigned [Target Name] to [Agent MasterLabel]
The Engagement Agent will qualify and reach out by email.
Record: [link to the Contact/Lead]
```

Genuine failure (assignment not created — invalid target, inactive agent, permission error) → report the exact error and which input triggered it. Don't retry with guessed values.
