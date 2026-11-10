---
name: update
description: Version-aware maintenance for the Sales Cloud plugin — keeps the daily refresh schedule current at the installed plugin version so new versions, migrations, and features get picked up. This is the skill the daily schedule runs. Also use when the user says "update", "run my plugin update", or after installing a new plugin version.
author: Salesforce
icon: assets/salesforce.svg
# Explicit-invocation only: run by the daily schedule (which invokes it by name /update)
# or by the user deliberately. Claude must not auto-trigger maintenance from conversation.
disable-model-invocation: true
checksum: "sha256:56bc7a0247191b47b172397c578f5dd760bf42fcc8504d78ab9974b7c58b65d2"
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

# Keep the daily schedule current

Keep the daily `Salesforce Updates` schedule, if the user opted in to one, stamped with the current plugin version, so when a future plugin version ships the daily job is already in place to pick it up. That is the whole job.

**Load the scheduling / task-list capability in one ToolSearch.**

List the current scheduled tasks and find the daily job named `Salesforce Updates` (or whose prompt starts with `Salesforce Updates`; also match a legacy `Daily Headless 360 update` or `Daily configure refresh`). Then:
- **It exists and its `Created with plugin version …` line already equals `1.0.0-beta.3.1`** → leave it; nothing to do.
- **It exists at an older version, or under a legacy name** → delete it and re-create it with `configure`'s exact daily-refresh prompt (named `Salesforce Updates`, carrying `Created with plugin version 1.0.0-beta.3.1`), advancing the baseline to the current version.
- **No such job exists** → do not create one; the user declined or never opted in, and `configure` creates it only on their yes.

Follow `configure`'s daily-refresh scheduling step for the exact prompt text and the off-`:00/:30` scheduling detail; don't reproduce it here. This runs unattended — emit no chat narration unless something fails or the user ran `update` interactively (then one line: that the schedule is current at version `1.0.0-beta.3.1`).
