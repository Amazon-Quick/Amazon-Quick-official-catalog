---
name: handle-objection
description: "Build a grounded response to a customer objection from the current deal, win-loss history, customer evidence and approved internal documents. Use when interpreting pricing, timing, trust or competitive pushback and preparing a talk track or written reply. For every buyer-objection response, load win-loss-review and customer-voice as conditional support, but do not invoke or use them until this skill's selected-deal and direct-evidence gates pass."
icon: assets/salesforce.svg
checksum: "sha256:8e38c573ef75395b09273c5b52f1161f7cccef9d01e0a68ca14569bc63c9fc14"
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


# Handle Objection

A grounded response, not a script: what the objection means, how deals like it went, and your own customers' evidence that answers it. Inputs: **the objection** (their words / email / transcript) and **the deal** (opp for context). Common objections/competitors/differentiators are external — infer from org data or ask once; never invent. **Read-only:** this skill never writes to Salesforce; drafting remains delegated to `draft-outreach`.

## 1. Classify what's really being said

Map to type: price/value · timing/priority · competitive · risk/trust · authority ("check with…") · status quo. Distinguish an **objection** (reason not to buy) from a **negotiation move** (reason to buy cheaper) — the response differs.

## 2. Resolve the deal to one Opportunity (approved #19 correction)

Use only a selected Opportunity as the deal. If the current user turn or attached record context supplies an Opportunity Id with prefix `006`, skip the candidate lookup and use it as `<OPP_ID>` in step 3. Otherwise run one of the two candidate reads below; both list the newest close dates first. Replace `<DEAL_NAME>` with the deal name as the user gave it, preserving the surrounding `%` wildcards. When the request names the deal's account, including as the first part of the deal name, use the rest of the deal name as `<DEAL_NAME>`, replace `<ACCOUNT_NAME>` with the account name as the user gave it, and run the second read. Otherwise run the first:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%<DEAL_NAME>%\\\" } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Account { Name { value } } } } totalCount } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Name: { like: \\\"%<DEAL_NAME>%\\\" }, Account: { Name: { like: \\\"%<ACCOUNT_NAME>%\\\" } } }, orderBy: { CloseDate: { order: DESC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Account { Name { value } } } } totalCount } } } }\"}" })
```

- **Exactly one returned row and `totalCount = 1`** → take its Id as `<OPP_ID>` and continue.
- **Several rows or `totalCount > 1`** → list only Account · Opportunity · Stage · Amount · Close date and ask which deal the user means. If the total exceeds the returned rows, say the list is partial and ask for a more distinctive name, account, or exact Id. Do not guess and do not run the detail read yet.
- **No rows** → ask for a more distinctive name or exact Opportunity Id. Do not substitute another deal or claim deal grounding.

Candidate fields are identification context only; they are not objection evidence.

## 3. Read the selected deal by exact Id

Only after a current-turn Id or one unambiguous candidate is selected, replace `<OPP_ID>` with that exact Id and run:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Id: { eq: \\\"<OPP_ID>\\\" } }, first: 1) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } Type { value } NextStep { value } Description { value } Account { Name { value } Industry { value } } Owner { Name { value } } OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Contact { Name { value } Title { value } } } } } } } } } } }\"}" })
```

No detail row → say the deal could not be read and ask the user to confirm the Id or access; never fall back to another candidate. The exact-Id read authorizes literal deal context only. Its Id, stage, amount, dates, Next Step, owner, account, and contact roles do not establish objection evidence, speaker, cause, authority, or recipient. `Description` qualifies only when its returned text directly and attributably records this customer's objection, reason, goal, or metric for this deal.

## 4. Pull direct evidence first — Quick/Kiro safe branch

**Safe evidence gate — Quick/Kiro adaptation:** This replaces the source's fire-in-parallel order. After the exact-Id detail read succeeds, search only for direct, customer-specific evidence of this objection: the user's supplied source, an attributable customer email/transcript/note, or returned `Description` text or a document that explicitly records the customer's words, reason, goal, or metric for this deal. The candidate list and literal deal context are identification/context only. A user paraphrase such as “the customer says it is too expensive” establishes the objection text but is not direct evidence of the reason, speaker, channel, approver, or intended recipient. Stage, Amount, Probability, Close Date, Next Step, Closed Won/Lost, owner, Contact title/role, account association, activity subject, and amount/outcome correlation never qualify as direct evidence.

### No direct evidence found

Stop evidence collection. Do not invoke or use `win-loss-review`, do not gather account-wide opportunities, contacts, or activities to fill the gap, and ignore any such data already returned. Do not infer history, causation, thresholds, stakeholders, buying authority, implementation, or recommendations from CRM context. Go directly to the mandatory no-direct-evidence response in step 5.

### Direct evidence found

Only after at least one qualifying source is found, gather the source evidence in parallel and use only claims that the returned source states directly:

- **Win/loss** (`win-loss-review`): only dated, attributable evidence that explicitly documents this objection, why the deal ended, or what action changed the outcome; amount/outcome patterns alone are unusable.
- **Customer voice** (`customer-voice`): verbatim quotes speaking to this exact concern.
- **Docs**: case studies, ROI, security/compliance already cleared for external use.
- **The deal itself**: explicit customer-stated pain, goals, or metrics for this deal.

Every dynamic claim must carry its inline source or Salesforce record link and exact supporting field/date. Closed Won/Lost, Next Step, amounts, stages, contact titles, and correlations retain only their literal meanings and cannot support causal or prescriptive language. If a required claim has no direct source, omit it.

## 5. Build the response

**Selected-deal output gate — Quick/Kiro structural adaptation:** Neither response template below is available until step 3 has returned exactly one Opportunity detail row for a current-turn `006` Id or a candidate explicitly selected by the user after disambiguation. If step 2 returned zero, multiple, or truncated candidates, or step 3 did not run or return that one row, output only the step-2 clarification or partial-list question and stop. Do not classify the objection, search for objection evidence, or emit even the generic no-direct-evidence response from the user's paraphrase alone. This gate is terminal for every unresolved-deal state.

### No-direct-evidence response — mandatory

When the safe evidence gate finds no qualifying source, use exactly this section structure and meaning, substituting only the user's objection wording. Do not add CRM facts, people, history, proof, recommendations, closing offers, or suggested actions.

```
# Objection: "<user-provided wording>" (user-provided paraphrase)
## What's underneath it
This is a price/value objection. The underlying reason and whether it is an objection or a negotiation move are not established.
## The response
"I hear you. When you say the price is too high, is the concern the available budget or whether the expected value supports the investment? What would you need to see or change to decide?"
## Proof points to have ready
No directly documented customer proof point for this objection was found.
## What history says
No directly documented win/loss history explains this objection; amount/outcome patterns were not used.
## Don't
- Don't infer a reason, threshold, approver, recipient, loss cause, or recommended concession from CRM amounts, outcomes, stages, contacts, activities, or Next Step text.
```

End immediately after `Don't`. Do not add a next-step menu, follow-up offer, question, button, CTA, or action.

### Direct-evidence response — only after the evidence gate passes

Use the source response shape below. Cite each claim beside the sentence or bullet it supports; a general caveat does not cure an unsupported claim.

```
# Objection: "<their words>"
## What's underneath it
<1–2 sentences: the real concern; objection vs negotiation>
## The response
<talk track in your voice, 3–5 sentences: acknowledge → answer with their own stated goals + one proof point → question that moves it forward>
## Proof points to have ready
- <customer quote / case study / metric — with source>
## If it's <competitor>
- Where they're strong (be honest) + where this customer's needs don't match it; the trap question that surfaces the difference
## What history says
<from win/loss: how often this objection appears in wins vs losses, and what winning reps did next>
## Don't
- <the response that historically loses this — overdiscounting, feature-dumping, arguing>
```

For the direct-evidence response only, link the selected Opportunity inline using its returned Id. The no-direct-evidence response remains intentionally free of CRM facts and links.

Objection arrived in writing? Offer to draft the reply via `draft-outreach`.

**Written-objection gate — Quick/Kiro adaptation:** Treat the objection as written only when explicit user input or a retrieved written source establishes both the written channel and an attributable speaker or intended recipient. A paraphrased objection in the request establishes only its content; a Contact name, title, or Opportunity role does not establish who raised it or should receive a reply. Without both the channel and participant evidence, return an unaddressed talk track and omit every draft CTA or action, including a conditional request to tell you that it came in writing; do not name a speaker, addressee, or recipient.
