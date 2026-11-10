---
name: call-prep
display_name: Call Prep
description: "Build a call brief from Salesforce meeting, account, opportunity, contact, and activity data plus email, documents, and Slack. Use before a customer meeting to understand attendees, deal history, open threads, and discovery needs; rep one-on-one: rep-context."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:89ae4606664781c6ad49a1e63272ea1a5b4ce47e39c589411bf7c5f5f1ffc70c"
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

# Call Prep

Resolve meeting → ground → read account → (calendar + email + docs + slack searches, all in ONE turn with the SF read) → assemble brief. Qualification framework (BANT/MEDDIC/etc.), value prop, and competitors are external knowledge — infer from org data or ask once. Never invent.

## 1. Resolve meeting

**Inputs:** a calendar event (by time, title, or "my next call"), OR an account name + time. If neither given, list today's external meetings and ask which one.

**1a. Find the owner (if named rep)**

- **"my next call"** (default) → skip to 1b with `scope: MINE`
- **"[Rep]'s next call"** → resolve one User. Shared/demo orgs collide (one name → base user + regional variants like `(AM)`/`(BK)`). Pull enough to disambiguate:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
    queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { User(where: { Name: { like: \\\"%REP%\\\" } }, first: 10) { edges { node { Id Name { value } Email { value } IsActive { value } } } } } } }\"}" })
  ```
  **One match** → take its Id. **Several** → list them (Name · Email · active? · Id) and ask user to pick. Then filter Events by `OwnerId: { eq: \"<UserId>\" }` in 1b.

**1b. Find the meeting**

Build the Event query based on input pattern. All patterns share the node shape (`Id Subject StartDateTime EndDateTime Location WhatId WhoId Description Who { ... on Contact { Id Name AccountId Account } } What { ... on Account { Id Name } ... on Opportunity { Id Name AccountId Account } }`). Combine filters with `and: [...]` when needed.

**Pattern: "my next call"** (scope: MINE, StartDateTime >= now, first: 1):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { StartDateTime: { gte: { value: \\\"<NOW>\\\" } } }, first: 1, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Pattern: "[Rep]'s next call"** (OwnerId from 1a, StartDateTime >= now, first: 1):
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(where: { OwnerId: { eq: \\\"<UserId>\\\" }, StartDateTime: { gte: { value: \\\"<NOW>\\\" } } }, first: 1, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Next-call start — local correction:** `<NOW>` is the current date and time as a UTC ISO-8601 instant, for example `2026-11-05T22:15:00Z`. Both next-call reads start there, because `literal: TODAY` starts at local midnight and returns a meeting that already ended earlier today. A meeting that has already started is not the next call.

**Pattern: specific event name** (e.g. "City of Hope call") — match Subject with LIKE, widen window to catch it (next 30 days), list if multiple:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { Subject: { like: \\\"%EVENTNAME%\\\" }, StartDateTime: { gte: { literal: TODAY }, lte: { range: { next_n_days: 30 } } } }, first: 10, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```
**One match** → use it. **Several** → list them (Subject · StartDateTime · Id) and ask user to pick. **Zero** → broaden `%EVENTNAME%` or ask user for account name directly.

**Pattern: time-based** (e.g. "call next thursday", "meeting tomorrow") — parse to date range. Use relative date filters:
- **"tomorrow"**: `StartDateTime: { gte: { range: { next_n_days: 1 } }, lte: { range: { next_n_days: 1 } } }`
- **"next thursday"**: compute day offset (if today = Monday, thursday = 3 days out) → `gte: { range: { next_n_days: 3 } }, lte: { range: { next_n_days: 3 } }`
- **"next week"**: `gte: { range: { next_n_days: 7 } }, lte: { range: { next_n_days: 14 } }`

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { StartDateTime: { gte: { range: { next_n_days: <OFFSET_START> } }, lte: { range: { next_n_days: <OFFSET_END> } } } }, first: 10, orderBy: { StartDateTime: { order: ASC } }) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```
**One match** → use it. **Several** → list them and ask user to pick.

**Pattern: account name directly** (e.g. "prep for City of Hope", "call with Acme") — no meeting specified. Skip Event query entirely, treat input as customer company name, jump to Step 2.

**Pattern: Event ID** (if user pastes SFDC Id `00U...`) — direct lookup:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(where: { Id: { eq: \\\"<EventId>\\\" } }, first: 1) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Location { value } WhatId { value } WhoId { value } Description { value } Who { ... on Contact { Id Name { value } AccountId { value } Account { Id Name { value } } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Extract:** title (Subject), time (StartDateTime/EndDateTime), WhatId (if `001…` → Account, `006…` → Opportunity), WhoId (Contact), description/agenda, meeting link (Location). From Description text or WhoId email domain, identify customer company.

## 2. Ground (hardcoded — Account only; fire with step 3 if independent)

Ground **only Account** — it always exists. Its field names, labels, and relationship names reveal this org's custom scalar and lookup signals; the standard relationships used below are hardcoded.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label relationshipName } } } }\"}" })
```

From the result, select relevant scalar Account `__c` fields by API name and label (industry, size, qualification, etc.) and take their `{ value }`. For a relevant custom lookup, retain its exact `relationshipName` for step 3. The standard `Owner`, `Opportunities`, and `Contacts` relationships below need no metadata.

Complete this grounding call before step 3 because `<ACCOUNT_CUSTOM>` depends on its result. Then batch the independent reads as described in steps 3a–3b.

## 3. Read account (template — fill from step 2)

Insert `<ACCOUNT_CUSTOM>` = confirmed scalar `__c { value }` fields (industry, size, qualification signals, etc.); `<REL_BLOCKS>` = relevant confirmed custom lookups using their exact grounded relationship names.

- **Children:** `Opportunities(where: { IsClosed: { eq: false } }, orderBy: { LastModifiedDate: { order: DESC } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } } } }`
- **Children:** `Contacts(where: { Email: { in: [<ATTENDEE_EMAILS>] } }) { edges { node { Name { value } Title { value } Email { value } } } }`
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { <DOMAIN_FILTER> }, first: 1) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } Type { value } Description { value } <ACCOUNT_CUSTOM> <REL_BLOCKS> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { LastModifiedDate: { order: DESC } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } NextStep { value } LastActivityDate { value } } } } Contacts(where: { Email: { in: [<ATTENDEE_EMAILS>] } }) { edges { node { Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```

Set `<ACTIVITY_ACCOUNT_FILTER>` from the resolved account identity:
- When Step 1 provides the account Id, use `AccountId: { eq: "<AccountId>" }`.
- For direct account-name input, use `Account: { Name: { eq: "<ACCOUNT_NAME>" } }`.
- If the account is ambiguous, resolve it before running the activity read.

Run this activity query and the Account query above as two `dispatch_readonly` calls in the **same tool turn**. They are independent once the account identity is known, so issue them in parallel. Keep Task and Event as root queries rather than nesting `ActivityHistories` under Account.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { recentTasks: Task(where: { <ACTIVITY_ACCOUNT_FILTER> }, orderBy: { ActivityDate: { order: DESC } }, first: 5) { edges { node { Id Subject { value } ActivityDate { value } Description { value } Status { value displayValue } Who { ... on Contact { Id Name { value } Title { value } Email { value } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } recentEvents: Event(where: { <ACTIVITY_ACCOUNT_FILTER> }, orderBy: { StartDateTime: { order: DESC } }, first: 5) { edges { node { Id Subject { value } StartDateTime { value } EndDateTime { value } Description { value } Who { ... on Contact { Id Name { value } Title { value } Email { value } } } What { ... on Account { Id Name { value } } ... on Opportunity { Id Name { value } AccountId { value } Account { Id Name { value } } } } } } } } } }\"}" })
```

**Reference-field rule:** Add scalar custom fields as `Field__c { value }`. Span a relevant custom lookup only through the exact `relationshipName` from step 2: `<relationshipName> { Name { value } }`. If it has no usable relationship name, take the raw Id and move on; do not retry or invent a relationship block.

**If `<DOMAIN_FILTER>` matches more than one Account** (shared/demo orgs collide — duplicate seed data, regional subsidiaries on the same domain), don't silently take `first: 1`. Drop to `first: 10`, Account-level fields only (Name, Website, Owner — no Opportunities/Contacts probe), list the candidates, and ask the user to pick before reading further.

## 3b. Evidence (run IN PARALLEL with step 3 — same turn)

**Issue step 3 and all of step 3b as tool calls in a single turn.** They're independent (searches key on account name/attendee emails, not the SF result):
- **email**: threads with the attendee emails in last 90d → last 2–3 exchanges (date, who, what discussed/committed)
- **docs**: docs mentioning the account name → prioritize files with "transcript", "notes", or "plan" in title, most recent first. Read top 1–2 and extract: key topics, open questions, commitments made.
- **slack**: account name in last 30d → internal context (deal desk threads, exec mentions, support escalations)

Use whatever email/doc/Slack search tools are available. If none present, skip silently (SF-only is fine). Cite source + date for anything you use.

**Perf guardrail:** Do NOT fire additional SF dispatches for `Task` or `EmailMessage` — the two step 3 reads + external evidence have the data.

## 4. Attendee profiles

For each external attendee: their SFDC Contact title, plus a 1–2 line summary of what they likely care about (from title + prior interactions from evidence). Flag anyone who's new (not in SFDC Contacts, no prior email thread).

## 5. Call plan

Based on opportunity stage and the qualification framework (inferred from org data or provided by the user):

- **Objective for this call:** [what should be true after the call that isn't before — e.g. "confirm budget owner and timeline" or "get technical validation scheduled"]
- **3–5 discovery questions:** tailored to the stage and any gaps in the qualification framework. Pull from prior notes if there were unanswered questions.
- **Likely objections:** infer from prior conversations or skip.
- **What to bring:** any doc/proposal/demo that was committed in prior threads.


## 6. Dashboard widget (editorial layout)

When the `display_widget` tool is available (Claude Cowork, the desktop app, the web app), render the call-prep brief as a visual widget instead of the Step 7 text. The layout follows editorial restraint: header with icon, one-line subhead, two datagrids (attendees and talk-track topics), and one synthesis callout with two buttons. When `display_widget` is unavailable (e.g. a terminal) the Step 7 markdown is the whole output, so produce it only then.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] `{{attendeeRows}}` and `{{topicRows}}` are typed arrays — each row object has the required keys and a leading `status` object.
- [ ] Every button's `onClick` is `action/sendMessage` or `action/openLink` with real content.
- [ ] No charts (meter/piechart/chart/heatmap/waterfall) — only datagrids.
- [ ] The callout is `variant: "info"` and closes the widget.

The widget template is embedded below — resolve its tokens and call `display_widget({ resourceType: "dynamic", widgetDefinition: <hydrated> })` once (see the `widgetDefinition` param for token-resolution rules). See `sample-data.json` in this dir for a fully-worked example.

Two blocks below: first the **variable contract** (`renderer.props.schema.json`) — every `{{token}}`'s type + a worked example, use it to compute each value; then the **widget template** to hydrate. Substitute your computed values into the template's `{{token}}`s (see the token-typing rules above), leaving no `{{…}}`/`{!…}`.
```json
{
  "$comment": "Variable contract for the native-mosaic dynamic-mode template (renderer.json, sibling). This is NOT a separate display_widget call — it names every {{token}} in the template with its type and a worked example so you compute the right value for each. Workflow: build a props object with these keys, substitute each into the matching {{token}} in renderer.json (a slot that is only a {{token}} becomes the typed value — arrays stay arrays, numbers stay numbers; a {{token}} inside a larger string interpolates as text; a key you have no data for is omitted so that leaf drops), then call display_widget({ resourceType: 'dynamic', widgetDefinition: <the hydrated template> }) once with no {{…}}/{!…} left. Realistic values: sample-data.json (sibling). Authoring guidance (from the skill): - [ ] Every `{{token}}` replaced with a resolved literal — no `{{…}}`, no `{!…}`.\n- [ ] `{{attendeeRows}}` and `{{topicRows}}` are typed arrays — each row object has the required keys and a leading `status` object.\nThe widget template is embedded below. It is a skeleton: replace every `{{token}}` with a fully-resolved literal computed from the brief you built in Steps 1–5 — this echo path does no expression compilation, so no `{!…}` bindings. See `sample-data.json` in this dir for a fully-worked example.\n- **Header** — phone icon + serif `page-title` (`{{title}}`, \"Call prep — [Meeting title]\").\n- **Subhead caption** — `{{subtitle}}` (one line: time, attendees, deal size, stage).\n- **Attendee datagrid** (`{{attendeeRows}}`) — one row per attendee. Columns: Attendee (avatar), Role (text), Stance (badge), Watch for (text). Each row carries a leading `status` object (`{value,badgeVariant}` — value Ally/Neutral/Blocker, badgeVariant success/warning/error/default); the leading Status column reads each row's `status`.\n- **Talk track datagrid** (`{{topicRows}}`) — one row per open item. Columns: Topic (text), State (badge), Your ask (text). Each row carries a leading `status` object (`{value,badgeVariant}` — value Must land/Push/Defuse/Confirm).\n- **One synthesis callout** (`variant: \"info\"`) — `{{calloutTitle}}` and `{{calloutDesc}}` (the call's goal and what success looks like). Two buttons: a primary \"Draft call agenda\" (`{{ctaLabel}}` / `{{ctaMsg}}`, `action/sendMessage`) and a secondary \"View in Salesforce\" (`{{oppUrl}}`, `action/openLink`).\n1. Start from the embedded template above — a valid-JSON widget-definition envelope whose leaf values carry `{{token}}` placeholders.\n2. Resolve every `{{token}}`. A value that is **only** a `{{token}}` (datagrid `rows`) becomes the resolved **typed** literal — arrays stay arrays. A `{{token}}` **inside** a larger string is interpolated as text.\n3. `{{attendeeRows}}` is an array of attendee objects — each with `name` (plain string — format as the person's display name (e.g. \"Dana Kwon\"); names must be plain strings, not objects: use `Contact.Name.value` from the SF response), `role`, `stance` (`{ value, badgeVariant }`), `watch`, and `status` (`{ value, badgeVariant }`). `{{topicRows}}` is an array of topic objects — each with `topic`, `state` (`{ value, badgeVariant }`), `ask`, and `status` (`{ value, badgeVariant }`).\n4. The result is hydrated widget definition (no `{{…}}` placeholders remain). Then:\n- Resolve every `{{token}}` to a literal before calling — arrays stay arrays (`{{attendeeRows}}`, `{{topicRows}}`), strings stay strings.\n- Callout buttons: the primary is `action/sendMessage` with a first-person `content` prompt (`{{ctaMsg}}`, e.g. \"Draft an agenda for the Cobalt contract walkthrough…\"); the secondary is `action/openLink` with `{{oppUrl}}` — the opportunity's Lightning URL (`https://<myDomain>/lightning/r/Opportunity/<Id>/view`), opening a new tab. Omit the openLink button if you lack the Id.",
  "props": {
    "title": {
      "description": "Page title — \"Call prep — [Meeting title]\".",
      "type": "string",
      "example": "Call prep — Cobalt contract walkthrough"
    },
    "subtitle": {
      "description": "Subhead: time, attendees, deal size, stage.",
      "type": "string",
      "example": "Today 9:00 · Dana Kwon (CFO) + Raj Patel (VP Eng) · $1.8M · Negotiation"
    },
    "attendeeRows": {
      "description": "Meeting attendees — one row per person. Empty array → the datagrid is omitted.",
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
          "name": {
            "description": "Attendee display name, a plain string (use Contact.Name.value — never a nested object).",
            "type": "string"
          },
          "role": {
            "description": "Attendee role (text).",
            "type": "string"
          },
          "stance": {
            "description": "Stance badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "Stance label shown on the badge.",
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
          "watch": {
            "description": "What to watch for with this attendee (text).",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Ally",
            "badgeVariant": "success"
          },
          "name": "Dana Kwon",
          "role": "CFO — econ. buyer",
          "stance": {
            "value": "Champion",
            "badgeVariant": "success"
          },
          "watch": "Will want term flexibility on the 3-yr"
        },
        {
          "status": {
            "value": "Ally",
            "badgeVariant": "success"
          },
          "name": "Raj Patel",
          "role": "VP Engineering",
          "stance": {
            "value": "Champion",
            "badgeVariant": "success"
          },
          "watch": "Technical proof already done — keep him vocal"
        }
      ]
    },
    "topicRows": {
      "description": "Talk-track items — one row per open item. Empty array → the datagrid is omitted.",
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
          "topic": {
            "description": "The topic to cover.",
            "type": "string"
          },
          "state": {
            "description": "Topic-state badge cell.",
            "type": "object",
            "properties": {
              "value": {
                "description": "State label shown on the badge.",
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
          "ask": {
            "description": "Your ask on this topic (text).",
            "type": "string"
          }
        }
      },
      "example": [
        {
          "status": {
            "value": "Must land",
            "badgeVariant": "error"
          },
          "topic": "MSA redlines",
          "state": {
            "value": "Open",
            "badgeVariant": "error"
          },
          "ask": "Agree terms in principle, send today"
        },
        {
          "status": {
            "value": "Push",
            "badgeVariant": "warning"
          },
          "topic": "Pricing sign-off",
          "state": {
            "value": "Pending",
            "badgeVariant": "warning"
          },
          "ask": "Confirm CFO approves Friday"
        },
        {
          "status": {
            "value": "Defuse",
            "badgeVariant": "warning"
          },
          "topic": "CIO in-house concern",
          "state": {
            "value": "Risk",
            "badgeVariant": "warning"
          },
          "ask": "Offer exec-to-exec with our CTO"
        },
        {
          "status": {
            "value": "Confirm",
            "badgeVariant": "success"
          },
          "topic": "Expansion scope",
          "state": {
            "value": "Agreed",
            "badgeVariant": "success"
          },
          "ask": "Reconfirm modules and go-live"
        }
      ]
    },
    "calloutTitle": {
      "description": "Synthesis callout heading — the call's goal.",
      "type": "string",
      "example": "Get the redlined MSA agreed in principle and lock the CFO's Friday price sign-off"
    },
    "calloutDesc": {
      "description": "Synthesis callout body — what success looks like.",
      "type": "string",
      "example": "Success = a dated path to signature by Jul 30. If the CIO concern surfaces, offer the CTO meeting rather than debating build-vs-buy live."
    },
    "ctaLabel": {
      "description": "Primary button label (action/sendMessage).",
      "type": "string",
      "example": "Draft call agenda"
    },
    "ctaMsg": {
      "description": "First-person prompt the primary button sends (action/sendMessage).",
      "type": "string",
      "example": "Draft an agenda for the Cobalt contract walkthrough focused on getting the redlined MSA agreed in principle and the Friday CFO sign-off locked."
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
            "attributes": {
              "gap": "sm",
              "align": "center",
              "isWrapped": false
            },
            "children": [
              {
                "definition": "tile/icon",
                "attributes": {
                  "name": "phone",
                  "size": "xl",
                  "alt": ""
                }
              },
              {
                "definition": "tile/text",
                "attributes": {
                  "text": "{{title}}",
                  "variant": "h1"
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
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "Who's on the call",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "name",
                  "header": "Attendee",
                  "type": "avatar"
                },
                {
                  "key": "role",
                  "header": "Role",
                  "type": "text"
                },
                {
                  "key": "stance",
                  "header": "Stance",
                  "type": "badge"
                },
                {
                  "key": "watch",
                  "header": "Watch for",
                  "type": "text"
                }
              ],
              "rows": "{{attendeeRows}}"
            }
          },
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "Talk track — open items to resolve",
              "appearance": "striped",
              "size": "sm",
              "columns": [
                {
                  "key": "status",
                  "header": "Status",
                  "type": "badge"
                },
                {
                  "key": "topic",
                  "header": "Topic",
                  "type": "text"
                },
                {
                  "key": "state",
                  "header": "State",
                  "type": "badge"
                },
                {
                  "key": "ask",
                  "header": "Your ask",
                  "type": "text"
                }
              ],
              "rows": "{{topicRows}}"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {
              "variant": "info",
              "title": "{{calloutTitle}}",
              "description": "{{calloutDesc}}"
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
                      "label": "{{ctaLabel}}",
                      "variant": "primary",
                      "actions": {
                        "click": [
                          {
                            "definition": "action/sendMessage",
                            "attributes": {
                              "content": "{{ctaMsg}}"
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

What each block shows, from data you already have:

- **Header** — phone icon + serif `page-title` (`{{title}}`, "Call prep — [Meeting title]").
- **Subhead caption** — `{{subtitle}}` (one line: time, attendees, deal size, stage).
- **Attendee datagrid** (`{{attendeeRows}}`) — one row per attendee. Columns: Attendee (avatar), Role (text), Stance (badge), Watch for (text). Each row carries a leading `status` object (`{value,badgeVariant}` — value Ally/Neutral/Blocker, badgeVariant success/warning/error/default); the leading Status column reads each row's `status`.
- **Talk track datagrid** (`{{topicRows}}`) — one row per open item. Columns: Topic (text), State (badge), Your ask (text). Each row carries a leading `status` object (`{value,badgeVariant}` — value Must land/Push/Defuse/Confirm).
- **One synthesis callout** (`variant: "info"`) — `{{calloutTitle}}` and `{{calloutDesc}}` (the call's goal and what success looks like). Two buttons: a primary "Draft call agenda" (`{{ctaLabel}}` / `{{ctaMsg}}`, `action/sendMessage`) and a secondary "View in Salesforce" (`{{oppUrl}}`, `action/openLink`).

**Row shapes:** `{{attendeeRows}}` is an array of attendee objects — each with `name` (plain string — format as the person's display name (e.g. "Dana Kwon"); names must be plain strings, not objects: use `Contact.Name.value` from the SF response), `role`, `stance` (`{ value, badgeVariant }`), `watch`, and `status` (`{ value, badgeVariant }`). `{{topicRows}}` is an array of topic objects — each with `topic`, `state` (`{ value, badgeVariant }`), `ask`, and `status` (`{ value, badgeVariant }`).

**Binding rules:**
- `datagrid` rows: one per attendee (name as avatar, role, stance badge, watch text), one per topic (name, state badge, ask text). Stance badge (`stance.badgeVariant`) reflects alignment — `"success"` (Champion/Ally), `"warning"` (Neutral), `"error"` (Blocker). State badge (`state.badgeVariant`) reflects urgency — `"error"` (Open/Critical), `"warning"` (Pending/Risk), `"success"` (Agreed/Resolved). `status` fills the leading Status column.
- Callout buttons: the primary is `action/sendMessage` with a first-person `content` prompt (`{{ctaMsg}}`, e.g. "Draft an agenda for the Cobalt contract walkthrough…"); the secondary is `action/openLink` with `{{oppUrl}}` — the opportunity's Lightning URL (`https://<myDomain>/lightning/r/Opportunity/<Id>/view`), opening a new tab. Omit the openLink button if you lack the Id.
- No fabricated content — quote blank fields as blank rather than inventing them; drop attendees or topics you have no data for.



## 7. Output

```
# Call Prep: [Account] - [Meeting Title]
[Date Time] | [Attendees]

## Account Snapshot
- [Industry, size, type] | Owner: [Name]
- Open opp: **[Name]** - [Stage] $[Amount] closing [Date]
  Next step (SFDC): [NextStep or "blank"]

## Who's in the room
- **[Name]**, [Title] - [1–2 line context, prior interactions]
- **[Name]**, [Title] - ⚠ NEW (no prior contact)
...

## What's happened so far
- [Date] - [Last call summary from transcript]
- [Date] - [Email thread summary]
- [Date] - [Slack/internal context if any]

## Open threads
- [Unanswered question or commitment from prior notes]
...

## This call
**Objective:** [one sentence]

**Questions to ask:**
1. [Stage-appropriate discovery Q]
...

**Likely objections:** [list]

**Bring:** [any committed deliverables]
```
