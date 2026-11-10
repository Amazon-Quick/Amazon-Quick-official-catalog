---
name: schedule-meeting
display_name: Schedule Meeting
description: "Book a customer meeting from calendar availability and Salesforce account, contact and opportunity data, then log the confirmed event in Salesforce. Use to find times, draft an invitation, schedule a follow-up, demo or review, or place a call on the calendar."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:0459e3595519a496e2bad5ad8a5c019feb95c2027314d887b3ab0cc1e1541278"
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
Find a time, draft or book the invite, and log the meeting to Salesforce as an `Event` on the right account/opportunity — so activity history stays honest.

# Audience:
Sales reps booking a meeting. This skill **BOOKS via calendar** and **WRITES an Event** to Salesforce; the confirmation gates and correctness matter more than speed.

# Rules:

- The proposed slots, the invite preview, and the final confirmation block are the only required output.
- **Two confirmation gates, both explicit-yes:** (1) before creating any calendar invite / sending any email, show the full invite (title, time, attendees, agenda); (2) before writing the SFDC Event. Never book or write without showing it first.
- Source attendee emails from SFDC first; if a contact has no address on record, recover it from the email connector, and only if neither has it, say so.
- **Calendar and email are capabilities, not Salesforce APIs** — use the calendar/email connector or MCP tools already available to you for availability, invites, drafts, and recovering an attendee address SFDC lacks. Only the `Event` log and the record reads go through `dispatch`/`dispatch_readonly`.

**Effect allowlist — Quick/Kiro adaptation (candidate-derived):** The only effects this skill may
offer are one complete-preview-plus-later-yes slot-proposal email draft or calendar invite and,
after an invite exists, one separately previewed and approved Salesforce Event. Never create or
offer to create an Account, Contact, Opportunity, or any other record. “Prepare,” “preview,” or “do
not book/create” means return the complete invitation preview and confirmation question with zero
effects; it does not authorize a draft, invite, Salesforce write, or other mutation.

# Schedule Meeting

**Inputs:** who (contact name(s) or "the [account] team") · what (demo, follow-up, QBR, security review…) · when (a window like "next week" or specific constraints) · duration (default 30 min; 60 for demos/QBRs).

## 1. Ground Event fields + resolve people and records

Run Event grounding and exactly one resolver path in the **same tool turn** (in **parallel**).

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Event\\\"]) { fields { ApiName label dataType } } } }\"}" })
```

**Account supplied:** `<ACCOUNT_FILTER>` = `Id: { eq: "<ACCOUNT_ID>" }`, or `Name: { like: "%[account]%" }` if no Id.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { <ACCOUNT_FILTER> }, first: 10) { edges { node { Id Name { value } BillingCity { value } BillingState { value } Industry { value } } } } } } }\"}" })
```

**Only contact name(s) supplied:** run once per attendee in parallel; use its Account Id below.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { Name: { like: \\\"%[name]%\\\" } }, first: 10) { edges { node { Id Name { value } Title { value } Account { Id Name { value } } } } } } } }\"}" })
```

Resolve one Account; ask on zero/multiple Account or Contact matches. Contact-only matches must share it; never guess.

## 1b. Read people and open opportunities

In the **same tool turn** (in **parallel**), run Opportunity and one Contact request per attendee with the same exact `<ACCOUNT_ID>`. Set `<CONTACT_SELECTOR>` to: resolved contact → `, Id: { eq: "<CONTACT_ID>" }`; account supplied → `, Name: { like: "%[name]%" }`; "the account team" → omit.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { AccountId: { eq: \\\"<ACCOUNT_ID>\\\" } <CONTACT_SELECTOR> }, first: 10) { edges { node { Id Name { value } Email { value } Title { value } } } } } } }\"}" })
```

Resolve each named attendee to one Contact; ask on zero/multiple matches.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { AccountId: { eq: \\\"<ACCOUNT_ID>\\\" }, IsClosed: { eq: false } }, first: 50) { edges { node { Id Name { value } StageName { value displayValue } } } } } } }\"}" })
```

Get attendee emails from SFDC; if a contact record has no address, recover it from the email connector. If neither has it, say so — never invent one. If multiple open opps, ask which one this meeting belongs to.

## 2. Find the time

Pull your calendar availability in the requested window (calendar tool). Propose 2–3 specific slots, avoiding existing meeting blocks and respecting working hours. Honor any stated customer preferences (timezone, no Fridays).

## 3. Draft or book — confirm which first

- **Propose-by-email:** draft an email offering the slots (use `voice-profile` tone if configured). Lands as a draft, never sent automatically.
- **Direct invite:** create the calendar event (attendees, agenda in the description, video link if the calendar adds one). Show the full invite and get an explicit yes **before** creating it.

## 4. Log it in Salesforce

After the invite exists, create the matching SFDC `Event` — confirm before writing:

```
dispatch(method: "POST", url: "/services/data/v63.0/sobjects/Event",
         body: { "Subject": "[title]", "StartDateTime": "[ISO8601]", "EndDateTime": "[ISO8601]", "WhoId": "[primary contact Id]", "WhatId": "[opportunity or account Id]" })
```

On a read-only connector, output the Event details as a paste-ready block instead of writing. Then confirm:

```
✅ Booked: [Title] - [date/time]
Calendar: [event created / draft email in email]
Salesforce: Event logged on [Account] / [Opportunity] - [link]
```
