---
name: log-activity
display_name: Log Activity
description: "Draft and, after confirmation, log a completed Salesforce Task from a user's summary or transcript and the matched account, opportunity and contact. Use when recording a past call, meeting or email exchange. For existing timelines, use query-activity-history."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:30ae63cade8ae76888cf7433a4fdecc87de48e0f95955f1fd49bf3df3286cf4e"
id: "d8784ded-6816-42b5-a4d2-897f657e44cf"
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
# Rules:

- Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.

# Log Activity

Ground + resolve (batched) → draft → confirm → write → read back → verify → report. Also answers the read side: "what's logged on [account]."

## 1. Write access (no call)

Needs a create-access connector. Read-only only → skip straight to drafting and hand the user paste-ready text instead of writing.

## 2. Ground Task + resolve records (batch — fire both in the SAME turn)

Independent — issue both in one turn, not sequentially.

**Ground Task** (root object, always exists). Picklist values depend on the record type, and a new Task is saved under the user's default one, so look that up first, in the same turn as the resolve:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Task\\\"]) { defaultRecordTypeId fields { ApiName dataType } } } }\"}" })
```

Then ground against it, with `<RECORD_TYPE_ID>` = the returned `defaultRecordTypeId`. This reveals TaskSubtype's real picklist values and any custom required fields. Substitute only the value returned by the preceding read. Never hardcode the primary record type `012000000000000AAA` when the returned default differs; if Salesforce itself returns that value, use it as the user's actual default.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(objectInfoInputs: [{apiName: \\\"Task\\\", recordTypeIDs: [\\\"<RECORD_TYPE_ID>\\\"]}]) { fields { ApiName label dataType required ... on PicklistField { picklistValuesByRecordTypeIDs { picklistValues { value label } } } } } } }\"}" })
```

**Resolve the account** (standard fields only, no grounding needed) — nest its open Opportunities and Contacts as children in the same call, not a separate round-trip:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 3) { edges { node { Id Name { value } Opportunities(where: { IsClosed: { eq: false } }, first: 10, orderBy: { CloseDate: { order: ASC } }) { edges { node { Id Name { value } StageName { value displayValue } CloseDate { value } } } } Contacts(first: 20) { edges { node { Id Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```

Skip the resolve call if the user already gave an unambiguous account/opp/contact Id. Multiple account matches, or an ambiguous opp/contact within one → ask, never guess which one a call belongs to. From Step 1's result, note TaskSubtype's valid values and any `required` custom field on Task — those go in the write.

## 3. Draft (prompt only)

- **Subject:** "[Type]: [topic]" (e.g. "Call: pricing and security review timeline")
- **Type:** Call, Email, or Task (a meeting is `Task`) — written to `TaskSubtype`, a restricted picklist; must match a value Step 2 confirmed
- **Date:** when it happened (default today)

**Relative-date grounding — Quick/Kiro adaptation:** Keep commitment timing exactly as the user stated unless an explicit host as-of date and timezone make one calendar date unambiguous. If `Friday`, `next week`, or similar wording permits more than one date, preserve the literal phrase in Description or ask before preview; never insert a specific date by assumption. The Task ActivityDate still records when the completed activity occurred.
- **Description:** 3-6 bullets — discussed, agreed, their commitments, ours. From the transcript if given, else the user's words.
- **Related to:** WhatId = the resolved Opportunity (or Account if no deal), WhoId = the resolved Contact
- **Follow-up:** if a clear next step came out of it, after the Task is separately confirmed and logged, offer to hand the change to `update-opportunity` for its own current-to-proposed preview and fresh approval; never combine an Opportunity update with the Task approval.

## 4. Confirm, then write

Show before writing, always:

```
📋 Draft Activity Log

Subject: [subject]
Status: Completed
Type: [Call/Email/Task]
Date: [date]
Related Account: [account name]
Related Opportunity: [opp name + stage + close date, or —]
Related Contact: [contact name]
[Required custom field label]: [value] (repeat for every required custom field; omit when none)

Description:
• [bullet]…

Ready to log this to Salesforce?
```

**Confirmation scope — Quick/Kiro structural adaptation:** This complete preview and its yes authorize exactly one Task POST containing only the displayed values. The displayed related record names map to the resolved `WhatId` and `WhoId`, and every required custom field appears by its grounded human label. Freeze the corresponding POST body as the exact approved payload. Present only choices to approve that Task, change it, cancel, or preview a separate follow-up; do not offer a combined Task-plus-Opportunity, email, calendar, or other mutation. An Opportunity NextStep change must run separately through `update-opportunity`, show the exact current and proposed values, and obtain a fresh explicit yes. If any Task field or resolved relationship changes after preview, show the complete revised draft and ask again.

Only after explicit yes:

```
dispatch(method: "POST", url: "/services/data/v63.0/sobjects/Task",
  body: { "Subject": "[subject]", "Status": "Completed", "ActivityDate": "[YYYY-MM-DD]", "TaskSubtype": "[value]", "Description": "[bullets]", "WhatId": "[Opportunity or Account Id]", "WhoId": "[Contact Id]" <TASK_CUSTOM> })
```

`<TASK_CUSTOM>` = every Step 2 `required` custom field on Task, filled from the draft/user and shown in the preview. Creation fails or does not return a usable Task Id → report the exact create error or result and output the entry as paste-ready text instead, then stop. Don't retry blind.

## 5. Read back, verify, then report

After the one successful Task POST returns a Task Id, substitute only that exact returned value for `<CREATED_TASK_ID>` and issue exactly this one post-create read:

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/sobjects/Task/<CREATED_TASK_ID>",
  queryParams: {})
```

Treat the Task POST body frozen at approval as the exact approved payload. Before claiming success, compare the returned `Subject`, `Status`, `ActivityDate`, `TaskSubtype`, `Description`, `WhatId`, `WhoId`, and every required custom field represented by `<TASK_CUSTOM>` exactly against that payload. A missing field, null/value difference, type or value mismatch, missing record, malformed response, or read error means persistence was not verified.

If the read-back errors or any comparison fails, report `Creation returned a Task ID, but persistence could not be verified.` Include only the minimal read error or human-labeled mismatches and the Task record link, then stop. Do not claim `Logged`, retry the GET or POST, make any mutation (including an Opportunity update or Task repair/delete), or clean up.

Only after the read-back succeeds and every required comparison matches exactly:

```
✅ Logged: "[Subject]" — [Date]
Related to: [Account] / [Opportunity] / [Contact]
Record: https://[instanceUrl]/lightning/r/Task/[returned Id]/view
```

## Read mode — "what's logged on [account/opp]"

Standard fields only, no grounding. For an account-scoped ask, resolve the account by name, nesting its Tasks as children — `Account.Tasks` is a standard child relationship, so this is one call, not a resolve-then-query chain:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 1) { edges { node { Id Name { value } Tasks(first: 20, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } Status { value } Description { value } Owner { ... on User { Name { value } } } } } } } } } } } }\"}" })
```

**Account scope — local correction:** The Account `Tasks` child returns only tasks logged directly on the account record. Tasks logged on the account's opportunities or contacts aren't in it, and this skill logs a call on the open opportunity when there is one. Say that the list holds the tasks logged on the account record, and never report the account as having no activity because the list is empty. For a deal's tasks, offer the opp-scoped ask below; for the account's full timeline, point to query-activity-history.

For an opp-scoped ask, select one Opportunity first. If the user gave an Opportunity Id (prefix `006`), use it as `<OPP_ID>`. Otherwise run one of the two candidate reads below; both list the newest close dates first. Replace `%OPP%` with the deal name as the user gave it, keeping a `%` wildcard on each side. When the request names the deal's account, including as the first part of the deal name, use the rest of the deal name for `%OPP%`, replace `%ACCOUNT%` with the account name as the user gave it, and run the second read. Otherwise run the first:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%OPP%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } CloseDate { value } Account { Name { value } } } } totalCount } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%OPP%\\\" }, Account: { Name: { like: \\\"%ACCOUNT%\\\" } } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } CloseDate { value } Account { Name { value } } } } totalCount } } } }\"}" })
```

- **Exactly one returned row and `totalCount = 1`** → take its Id as `<OPP_ID>`.
- **Several rows or `totalCount > 1`** → list Account · Opportunity · Stage · Close date and ask which deal the user means. If the total exceeds the returned rows, say the list is partial and ask for a more distinctive name, the account, or the exact Id. Do not guess.
- **No rows** → ask for a more distinctive name, the account, or the exact Opportunity Id. Do not substitute another deal.

Then read that Opportunity's Tasks by exact Id — `Opportunity.Tasks` is a standard child relationship; same nested block:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } Tasks(first: 20, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } TaskSubtype { value } Status { value } Description { value } Owner { ... on User { Name { value } } } } } } } } } } } }\"}" })
```

Output as a dated list, newest first, one line each; note the last-touch gap if it's longer than 14 days.

## [CUSTOMIZE]

- **Required fields:** Step 2's grounding surfaces org-specific required custom fields on Task automatically — no hardcoded list needed.
- **Event vs Task:** this skill logs completed Tasks. If your org logs meetings as Events instead, switch Step 4's write to create an Event with start/end times from Calendar.
- **Description depth:** default is 3-6 bullets; adjust the target length in Step 3 if your team wants fuller notes.
