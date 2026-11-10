---
name: customer-voice
display_name: Customer Voice
description: "Compile attributable customer quotes and themes from call transcripts and email threads across Salesforce-scoped accounts. Use to understand feedback on a feature, objection, competitor or emerging issue, compare accounts, or surface recurring themes. Also load as conditional support for handle-objection prompts such as a buyer saying we're too expensive; do not search or use quotes until handle-objection's evidence gate permits them."
author: Salesforce
roles:
  - role/sales
icon: assets/salesforce.svg
checksum: "sha256:64325e7b5e89cf2a7f759e977f1fda647970d02e2232a74bb73839c606cd1564"
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
# Customer Voice

Direct customer quotes on a topic, from transcripts + email threads across your accounts — verbatim with attribution, not summaries. Salesforce only *scopes* the search: which accounts, and who's internal vs. customer. Context (all in ONE turn) → search docs/email → extract quotes → group by theme.

Inputs: **topic** (theme/objection/feature/competitor, or open-ended "what's coming up"); **scope** (my accounts default / team / named list); **period** (30d default).

## 1. Context — 3 independent SF reads + the searches, all in ONE turn

These don't depend on each other, so fire them together (with the doc/email searches below). No schema grounding — fields are fixed.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(scope: MINE, first: 200) { edges { node { Name { value } Website { value } Owner { Name { value } } } } } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Email { value } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Name FROM Organization LIMIT 1" })
```

- **Accounts** = the domains/names to scope the search to (team/named-list scope: drop `scope: MINE`, filter on owner/list).
- **Internal domain** = the part after `@` in `currentUser.Email`; **org name** = `Organization.Name`. Anyone speaking from that domain/company is **internal** — everyone else is the customer.

## 2. Search sources (same turn — skip silently if a connector is absent)

- **docs**: transcripts / notes / meeting docs in the period, in account-named folders (team scope → team-shared too).
- **email**: threads in the period to/from the scoped account domains.

**Sources — Quick/Kiro adaptation:** Quotes come only from these docs and email searches. Salesforce only scopes this skill: make no Salesforce reads beyond the three in step 1, never search Tasks, Events, Cases, or other records as a substitute source, and report no counts from such a search.

## 3. Extract quotes (strict — customer-only, on-topic, verbatim)

Per transcript/thread, pull passages where the **customer** (not your domain/org) speaks on the topic: verbatim quote (1–3 sentences) · speaker name + title + account · date + source · one-line context. Paraphrase is NOT voice-of-customer. Open-ended topic → cluster by theme, return top 3–5 by frequency.

## 4. Output

```
# Customer Voice: "<Topic>" — <N> quotes from <M> accounts (<period>)

## <Theme>
> "<Verbatim quote>"
> — <Name>, <Title> @ <Account> — <Date> (<source link>)

## Accounts represented
<Account> (<N>), …

## Gaps
- <N> accounts in scope had no transcript/thread in period
- Topic not mentioned in: <accounts>
```

**No quotes found — Quick/Kiro adaptation:** If no transcript or thread has an on-topic customer quote, still return this template with 0 quotes, keeping the topic and period in the header. Write `None` under Accounts represented and fill Gaps as shown. Close with at most one line offering a wider period or scope, or asking for a transcript, notes doc, or email thread to search; offer no other source.
