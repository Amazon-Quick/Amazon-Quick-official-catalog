---
name: configure
description: Set up the Sales Cloud plugin — show the "How I can help you sell" overview, offer a "Where do you want to start?" chooser, and (on request) build Your Sales Intelligence, a live view of the user's book of business, then offer to schedule the daily refresh. Use when the user says "configure", "configure salesforce", "set me up", "onboard me", "get me started", or on first run of the plugin.
author: Salesforce
icon: assets/salesforce.svg
# Explicit-invocation only: the user runs this deliberately (/configure or by name).
# Claude must not auto-trigger onboarding from ambient conversation.
disable-model-invocation: true
checksum: "sha256:5a90fc96b925fdfe308d263bffca08fb975093d23d6dc9e97a3a7cb7dd9f99ee"
---
<!-- global-rules-bootstrap -->

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **Ground dynamic or custom relationship and field names before relying on them.** Fixed standard fields that this skill explicitly marks as requiring no grounding need no extra grounding call. On a name error, use the skill's documented grounding path when present; otherwise report the error instead of guessing or re-firing the same shape.
- **Cite every value exactly as queried**; never fabricate; distinguish a blank value from a value that was not queried. Link each Salesforce record inline: `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`.
- **Show human labels, never API/field literals.** In anything the user sees, print each field's grounded `label` (for example, "Deal Risk", not `Deal_Risk__c`) and record Names, never raw Ids or `__c` API names.
- **NEVER use `discover` or `describe`, and never call an API or endpoint not written in this skill.** Every Salesforce URL you need is in the skill. Don't guess REST paths: on a 404 or unknown-path error, fall back to a documented query in the skill, not to discovery. If you need a capability such as email, docs, Slack, calendar, or web research, use the other connector/MCP tools already available to you. Endpoint guessing and discovery add needless round-trips. Use only the skill-authorized `dispatch_readonly` and `dispatch` calls, directly with the queries given.
<!-- /global-rules-bootstrap -->

# Rules:

- **Empty `MINE` scope is not a failure.** A brand-new user legitimately has no activity — record "none yet", never invent records.
- **Artifacts can only call MCP tools you declare in their `mcp_tools`, and the host blocks any tool you did not actually call this session.** So (1) resolve the EXACT fully-qualified tool name in-session before creating an artifact — do not guess or list candidate variants; (2) declare only tools you verified this session in `mcp_tools`; (3) never make an artifact depend on a server that may not be connected. Your Sales Intelligence view calls exactly one tool (the read-only dispatch tool).

# Configure Salesforce

Gate on Salesforce (and note whether Slack is connected), then show the welcome and the "How I can help you sell" widget, gather the user's book of business, and present a "Where do you want to start?" chooser. The chooser's first option builds **Your Sales Intelligence** (a live view of their book); its other options are personalized starter actions. Build Your Sales Intelligence only when the user picks that option. Finish by offering to schedule the daily refresh.
**Load every tool you'll need in ONE ToolSearch first.** If any tools are deferred in this session, resolve them up front in a single `select:` query rather than discovering them one step at a time (mid-run ToolSearch round-trips were a measured slowdown). Across the whole flow you will need: the Salesforce dispatch tool (`dispatch_readonly`), the `display_widget` capability (step 1), `create_artifact` (step 6), and the scheduling tool (step 7); and — if present — Slack read tools (they only change the welcome wording in step 1). Load them once, then proceed. Skip any that aren't offered in this session.

## 0. Salesforce connected? (hard gate)

Probe the running user:
```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id Name { value } } } }\"}" })
```
If `dispatch_readonly`/`salesforce-h360` is absent, or the probe errors, exit gracefully, exactly:

```
I can't reach Salesforce yet. Please connect the Sales Cloud server (`salesforce-h360`) via /mcp, then re-run configure.
```

Do NOT attempt workarounds, ask clarifying questions, or invent a profile. Just stop. Salesforce is the **only** hard requirement.

**Record from this step:**
- `<UID>` — `currentUser.Id`.
- `<FIRST_NAME>` — the first word of `currentUser.Name` (for the step-1 welcome).
- `<DISPATCH_TOOL>` — the exact fully-qualified name of the tool you just called: `mcp__<server>__dispatch_readonly` (typically `mcp__salesforce-h360__dispatch_readonly`, though the server segment can differ by install). Your Sales Intelligence artifact (step 6) needs it verbatim, both inlined in its script and as its sole `mcp_tools` entry.
**Slack (optional, non-gating).** Note whether Slack read tools are connected this session (e.g. `slack_search_users`). Slack is never required; its presence only decides whether the step-1 welcome says "Salesforce & Slack" or just "Salesforce". Never block on Slack.

## 1. Show the opening and the "How I can help you sell" widget

This is the first thing the user sees. Do it in ONE turn: a welcome line as normal chat, then the widget. Then go straight to step 2 — the reads run while the welcome is already on screen.

**Welcome line.** Substitute `<FIRST_NAME>` from step 0. Include "& Slack" **only if** Slack was connected (step 0); otherwise drop it:

```
Welcome <FIRST_NAME>! Now that I'm connected to your Salesforce & Slack, I can help across your whole selling day—not just answer CRM questions.
```

(No Slack this session → "…connected to your Salesforce, I can help across your whole selling day—not just answer CRM questions.")

**Widget.** Then make **one** `display_widget` call. The **"How I can help you sell" capability grid is static** — does not vary by user — so paste it verbatim. The grid is display-only; the "Where do you want to start?" chooser (step 3) is a separate native question, **not** buttons inside the widget. If `display_widget` isn't available (e.g. a terminal that mounts no widget host), skip it silently and instead list the four capabilities as plain text, one line each.

```jsonc
display_widget({
  "resourceType": "dynamic",
  "widgetDefinition": { "renderer": { "componentOverrides": { "$": {
    "type": "mosaic", "definition": "tile/widget", "children": [

      // ---- STATIC: capability grid (copy verbatim) ----
      { "definition": "tile/container", "attributes": {}, "children": [
       { "definition": "tile/column", "attributes": { "gap": "lg" }, "children": [

        { "definition": "tile/row", "attributes": { "gap": "sm", "align": "center" }, "children": [
          { "definition": "tile/icon", "attributes": { "name": "star", "size": "md", "alt": "" } },
          { "definition": "tile/text", "attributes": { "text": "How I can help you sell", "variant": "section-title" } } ] },

        { "definition": "tile/row", "attributes": { "gap": "md", "align": "stretch", "isWrapped": true }, "children": [

          { "definition": "tile/column", "attributes": { "width": "md" }, "children": [
           { "definition": "tile/container", "attributes": {}, "children": [
            { "definition": "tile/row", "attributes": { "gap": "sm", "align": "center" }, "children": [
              { "definition": "tile/icon", "attributes": { "name": "dashboard", "size": "md", "alt": "" } },
              { "definition": "tile/text", "attributes": { "text": "Start informed", "variant": "h5", "weight": "semibold" } } ] },
            { "definition": "tile/text", "attributes": { "text": "Get a morning briefing that combines your calendar, inbox, pipeline movement, and urgent follow-ups.", "variant": "body", "color": "muted" } },
            { "definition": "tile/text", "attributes": { "text": "DAILY BRIEFING · CALENDAR · INBOX SWEEP", "variant": "caption", "color": "primary" } } ] } ] },

          { "definition": "tile/column", "attributes": { "width": "md" }, "children": [
           { "definition": "tile/container", "attributes": {}, "children": [
            { "definition": "tile/row", "attributes": { "gap": "sm", "align": "center" }, "children": [
              { "definition": "tile/icon", "attributes": { "name": "trending-up", "size": "md", "alt": "" } },
              { "definition": "tile/text", "attributes": { "text": "Move deals forward", "variant": "h5", "weight": "semibold" } } ] },
            { "definition": "tile/text", "attributes": { "text": "Catch stalled deals, prep for calls, map stakeholders, and leave every conversation with a clear next step.", "variant": "body", "color": "muted" } },
            { "definition": "tile/text", "attributes": { "text": "DEAL SIGNALS · CALL PREP · FOLLOW-UP", "variant": "caption", "color": "primary" } } ] } ] },

          { "definition": "tile/column", "attributes": { "width": "md" }, "children": [
           { "definition": "tile/container", "attributes": {}, "children": [
            { "definition": "tile/row", "attributes": { "gap": "sm", "align": "center" }, "children": [
              { "definition": "tile/icon", "attributes": { "name": "message", "size": "md", "alt": "" } },
              { "definition": "tile/text", "attributes": { "text": "Communicate like you", "variant": "h5", "weight": "semibold" } } ] },
            { "definition": "tile/text", "attributes": { "text": "Draft outreach, objection responses, and follow-ups using the voice and patterns captured in your Context.", "variant": "body", "color": "muted" } },
            { "definition": "tile/text", "attributes": { "text": "VOICE PROFILE · DRAFT OUTREACH · OBJECTIONS", "variant": "caption", "color": "primary" } } ] } ] },

          { "definition": "tile/column", "attributes": { "width": "md" }, "children": [
           { "definition": "tile/container", "attributes": {}, "children": [
            { "definition": "tile/row", "attributes": { "gap": "sm", "align": "center" }, "children": [
              { "definition": "tile/icon", "attributes": { "name": "search", "size": "md", "alt": "" } },
              { "definition": "tile/text", "attributes": { "text": "Find the next opportunity", "variant": "h5", "weight": "semibold" } } ] },
            { "definition": "tile/text", "attributes": { "text": "Prioritize leads, research prospects, uncover account whitespace, and spot renewals that need attention.", "variant": "body", "color": "muted" } },
            { "definition": "tile/text", "attributes": { "text": "LEAD TRIAGE · RESEARCH · EXPANSION · RENEWALS", "variant": "caption", "color": "primary" } } ] } ] }

        ] }
       ] }
      ] }

    ] } } } }
})
```

## 2. Gather the book of business (issue ALL reads in ONE parallel batch)

This runs right after the opening: step 3's "Where do you want to start?" chooser is personalized from what you find here, and — if the user chooses to build Your Sales Intelligence — steps 4–6 reuse the same reads. Keep `currentUser.Id` from step 0 as `<UID>`. Reads **1a, 1b, 1d, 1e, and 1j are independent** — issue them as a **single batch of parallel `dispatch_readonly` calls in one turn**, don't await each before sending the next. This tier gathers what the chooser needs to personalize its options — dominant objects (1d), recent activity (1e), and a standout open opp/renewal/lead (1j) — plus the identity Your Sales Intelligence inlines (1a/1b). The deeper profiling reads (permission sets, Slack/mail signal, sales-performance history) are skipped. (1i needs no query.)
**1a. Identity** — already have Id/Name/Email/TimeZone if you widened step 0; else:
```
dispatch_readonly(method: "GET", url: "/services/data/v66.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Id Name { value } Email { value } TimeZoneSidKey { value } } } }\"}" })
```

**1b. Role / title / manager / profile** — not served by UI-API GraphQL; SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Id, Name, Title, Department, ManagerId, Manager.Name, UserRole.Name, Profile.Name FROM User WHERE Id = '<UID>'" })
```
`UserRole.Name` is edition-gated — the role hierarchy is absent in some editions (Group/Essentials/Contact Manager), where this query throws `INVALID_FIELD` on that column. If it does, **drop `UserRole.Name` and re-run** the same query with the rest of the fields (all of which are guaranteed standard) — record role as "not set" rather than failing the step.


**1d. What they work on** (dominant objects) — SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Id, Name, Type, LastReferencedDate FROM RecentlyViewed WHERE LastReferencedDate != null ORDER BY LastReferencedDate DESC LIMIT 100" })
```
Group by `Type` → the objects they touch most (Opportunity, Account, Lead, …).

**1e. Recent activity** (cadence signal) — GraphQL, `scope: MINE`:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Task(scope: MINE, where: { ActivityDate: { gte: { literal: LAST_90_DAYS } } }, first: 100, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Id Subject { value } Status { value displayValue } ActivityDate { value } } } } } } }\"}" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Event(scope: MINE, where: { ActivityDate: { gte: { literal: LAST_90_DAYS } } }, first: 100, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Id Subject { value } ActivityDate { value } } } } } } }\"}" })
```


**1i. Quota (only if you can source it).** There is no reliable standard SOQL field for a rep's quota. If the user states it, use it; otherwise leave quota `null` — Your Sales Intelligence's Attainment donut degrades to a closed-won summary. Do **not** query `ForecastingQuota` speculatively or fabricate a number.

**1j. Open pipeline** — the open-work signal for the chooser's personalized options: # open, open value, and a standout open opp/renewal with its amount. SOQL:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Id, Name, Amount, StageName, CloseDate FROM Opportunity WHERE OwnerId = '<UID>' AND Account.OwnerId = '<UID>' AND IsClosed = false ORDER BY CloseDate ASC LIMIT 200" })
```
Compute # open, total open value, and the subset closing this quarter, and pick the standout open opp/renewal/lead that will anchor a chooser option. (Your Sales Intelligence re-derives all of the numbers client-side at render; here you use it to personalize the step-3 chooser.)

**`AND Account.OwnerId = '<UID>'` scopes the open book to accounts the rep currently owns.** When an account is reassigned to another rep, Salesforce updates `Account.OwnerId` but does NOT cascade to the open opportunities' `OwnerId` — so an owner-only filter kept surfacing "zombie" opps on accounts the rep no longer manages. This clause drops them so the pipeline reflects the book they actually work. It also excludes open opps with no Account (the intended "on my accounts" read). This must match Your Sales Intelligence's open-book query, which is account-scoped the same way — keep the two in sync. (Closed-won reads in 1h stay owner-only: realized wins count even on accounts that later moved.)


## 3. Ask where to start

**Present "Where do you want to start?" using Claude's NATIVE option-selection UI — NOT buttons inside the widget.** Ask the question with the built-in multiple-choice tool (`AskUserQuestion` — question `"Where do you want to start?"`, a short header like `"Start"`), so the user gets native selectable option buttons (the host also appends its own "Other" free-text choice). This question tool ends the turn and waits for the pick, so don't add a separate "pick one below" line or any recap. Give the question exactly these options:

- **Option 1 — fixed, verbatim label `Build a smart view of my book`.** Description e.g. "A live view of your pipeline, attainment, and what needs attention." Picking it runs steps 4–6 (build Your Sales Intelligence).
- **Options 2–4 — personalized from step 2.** Each is the highest-value next thing *this* user can do and maps to a real plugin skill (e.g. `daily-briefing`, `deal-signals`, `call-prep`, `renewal-radar`, `lead-triage`, `draft-outreach`, `inbox-sweep`, `expansion-whitespace`). Keep each label short (2–4 words); each description must name a real account/opp/renewal/lead/amount from step 2 — none may be a generic verb-only option. E.g. an AE with a big open renewal → label "Review a renewal" / desc "Check your Acme Corp renewal and what's at risk"; an SDR heavy in Leads → label "Triage my leads" / desc "Sort your new leads and who to call first." Resolve every value to a literal (no `<...>`/`{{token}}` left).

**Chooser grounding — Quick/Kiro adaptation:** Treat each named example inside a personalized option as one returned record keyed by its Id. Copy its Name, Amount, CloseDate, and any overdue/closing claim from that same row; never merge records that share a name, and recompute each date predicate against that row before display. Compute aggregate counts separately, then verify every displayed name/amount/date tuple against the returned rows. Ask only the native `Where do you want to start?` question and its options—do not add a second welcome, book summary, or recap immediately before it.

If the native question tool isn't available this session, fall back to a short numbered plain-text list of the same options and wait for the user's reply. Either way, then go to step 4.

## 4. On the user's pick

**Only build Your Sales Intelligence when the user picks `Build a smart view of my book`.** Then run steps 4–6 (author → build → create + close).

**The deliverable is a Cowork artifact — not an HTML file.** "Build Your Sales Intelligence" is done only when the view is registered with the host by calling **`create_artifact`** (step 6); on a rebuild/refresh you call **`update_artifact`** instead. The `.artifact.html` file step 5 writes is a scratch **input** to that call and nothing more — writing it, reading it back, or opening/previewing it (in a browser, a `file://` link, or by pasting its HTML into chat) is **not** the deliverable and the user never sees it. Do not stop after step 5. If `create_artifact`/`update_artifact` aren't available this session, you cannot build the view — **do not substitute anything else** (no raw HTML file, no `file://` link, no inline/pasted render). Stop and tell the user to enable AI-powered artifacts so you can build a reusable, persistent dashboard, then re-run configure. For example: "I can't build Your Sales Intelligence without artifacts — please ensure AI-powered artifacts are enabled in Cowork under Settings > Capabilities > Visuals so I can create a reusable, persistent dashboard, then run configure again."

- **Picked a personalized option instead** → run the skill you mapped that option to in step 3 (using the account/opp/lead you named in its description); that skill takes over. Don't build anything; once that skill's work is done, go to step 7.
- **Picked "Other" / typed something else / picked nothing** → answer normally; build Your Sales Intelligence only if they ask for it. Once that is handled, go to step 7.

When you do build, author the data first.

**First, resolve Your Sales Intelligence's Opportunity fields from the layout (one read).** The view grounds *every* Opportunity field it selects against the running user's FLS at run time — a hidden or absent field just drops its column instead of failing the board, so you never have to assert a field is present here. What you resolve at build time is *which field backs each concept the view needs* — `name`, `stage`, `amount`, `probability`, `closeDate`, `lastActivity`, `nextStep` — because orgs vary. Most use the standard fields; some rename a concept to a custom field (next step is the classic case: a custom `Next_Step__c` with standard `NextStep` left empty). The field shape is org-wide, not per-owner, so resolve it from any Opportunity's Full layout — the user's own book first, any accessible opp as a fallback:

1. Get an Opportunity Id to read the layout from. Prefer an open opp from 1j (the user's own book). **If 1j returned none, don't skip — query any Opportunity the user can see** (the layout/field shape is the same regardless of owner):
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Id FROM Opportunity ORDER BY LastModifiedDate DESC LIMIT 1" })
```
Use that `Id` for the layout read below. Only if this *also* returns nothing (the org has no Opportunity at all) fall through to item 5.
2. **IMPORTANT — read the layout, not ObjectInfo.** Read that record shaped by its Full/View layout; the response's `fields` object holds exactly the fields on that layout, honoring the user's FLS:
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/ui-api/records/<OPP_ID>",
  queryParams: { "layoutTypes": "Full", "modes": "View" })
```
   **The layout is the gold standard for what's relevant to this user's persona — always resolve every field from it first, and reach for ObjectInfo only for a concept the layout can't satisfy.** The layout surfaces exactly the fields the org put in front of this user; ObjectInfo returns the object's *entire* field catalog — a huge payload, most of it irrelevant to the current persona (and heavier to fetch). So the layout, not ObjectInfo, is the default source for all field resolution below.
3. Collect the laid-out field API names — the **keys** of the response's `fields` object (e.g. `Name`, `StageName`, `Amount`, `NextStep`, `Next_Step__c`, …).
4. Build `<FIELD_MAP>` — resolve each concept to the field this org uses, matched **against the laid-out keys** (never a hardcoded assumption). Per concept, with its standard field and a fuzzy pattern:
   | concept | standard field | fuzzy pattern (on API name) |
   |---|---|---|
   | `name` | `Name` | `/name/i` |
   | `stage` | `StageName` | `/stage/i` |
   | `amount` | `Amount` | `/amount|value/i` |
   | `probability` | `Probability` | `/prob/i` |
   | `closeDate` | `CloseDate` | `/close.?date/i` |
   | `lastActivity` | `LastActivityDate` | `/last.?activity|activity.?date/i` |
   | `nextStep` | `NextStep` | `/next.?step/i` |

   Resolution rule per concept:
   - **`nextStep` prefers a custom field** — a custom logic field implies the org actually tracks the concept there while the standard one sits blank. Pick the first laid-out key matching `/next.?step/i` that is **not** exactly `NextStep`; else the standard `NextStep` if it's on the layout; else leave `nextStep` unresolved.
   - **Every other concept prefers its standard field** (protects the view's typed math — `amount` must be a currency, `probability` a percent, etc.): if the standard field is a laid-out key, use it; else the first laid-out key matching the fuzzy pattern (the org backs the concept with a custom field); else leave the concept unresolved.
   - **A concept you can't resolve from the layout:** if the view genuinely needs it and it's plausibly hidden from the layout, you *may* consult ObjectInfo (item 5's query) for just that concept; otherwise leave it out of `<FIELD_MAP>` — the view falls back to the concept's standard API name at run time and drops it degrade-safe if it's truly inaccessible.

   `<FIELD_MAP>` is a JSON object of the concepts you resolved, e.g. `{"name":"Name","stage":"StageName","amount":"Amount","probability":"Probability","closeDate":"CloseDate","lastActivity":"LastActivityDate","nextStep":"Next_Step__c"}`. Omit a concept to let the view use its standard default; set `nextStep` to `""` to disable the "needs a next step" signal.
5. **Only if step 1 found no Opportunity at all** (empty org, so there's no record to lay out — this is the sole case where a layout read is impossible) → resolve from ObjectInfo directly, no record needed:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Opportunity\\\"]) { fields { ApiName label } } } }\"}" })
```
Apply the same per-concept rule to `fields[].ApiName` (with `label` as an extra fuzzy signal): standard field first for every concept except `nextStep`, which prefers a custom next-step-looking name/label over standard `NextStep`. This honors FLS (ObjectInfo only returns fields the user can access) and never needs a record.

This is a single read on the build path only — skip it entirely if you already resolved `<FIELD_MAP>` this session. `<FIELD_MAP>` is inlined into Your Sales Intelligence in step 5; the view selects each resolved field degrade-safe, so a wrong or FLS-hidden name costs only that one column/signal, never the board.

Your Sales Intelligence needs only a tiny identity record — no full profile, no memories. From your step-2 reads, note just:
- **`USER_NAME`** — the rep's first name (1a).
- **`ROLE`** — their role/title (1b); use `"not set"` if none.
- **`QUOTA`** — only if the user stated one (1i); otherwise leave it null (the Attainment donut degrades to a closed-won summary).

That's all step 5 inlines into Your Sales Intelligence — everything else (open pipeline, attainment, signals) the artifact re-derives client-side at render.

## 5. Build Your Sales Intelligence file with ONE shell command

`create_artifact` takes an **`html_path`** (a scratch file), not inline HTML — so a single `python3` block substitutes the data you authored in step 4 into the Your-Sales-Intelligence template. The file this writes is scratch **input** for step 6's `create_artifact` call — do not open, preview, or show it to the user; step 6 is where the artifact actually gets created. **Never Read the template into your reply and retype it** (hundreds of lines) — the only content you type is the small step-4 data. Use Python `.replace`, not `sed` — the JSON contains `/`, `&`, and quotes that break `sed s///`.

The block **self-resolves the template dir** (`$CLAUDE_PLUGIN_ROOT` is often unset in the shell — don't waste a turn running `find`; the fallback globs the installed-plugin locations).

```bash
python3 - <<'PY'
import os, json, glob, pathlib, datetime

# --- resolve the plugin template dir: env var first, then installed-plugin globs ---
def plugin_root():
    home = str(pathlib.Path.home())
    cands = [os.environ.get("CLAUDE_PLUGIN_ROOT")] if os.environ.get("CLAUDE_PLUGIN_ROOT") else []
    cands += glob.glob(home + "/.claude/plugins/marketplaces/*/plugins/headless-360-for-sales")
    cands += glob.glob(home + "/.claude/plugins/repos/*/*/headless-360-for-sales")
    for c in cands:
        if c and pathlib.Path(c, "skills/configure/your-sales-intelligence.html").exists():
            return pathlib.Path(c)
    raise SystemExit("templates not found; set CLAUDE_PLUGIN_ROOT")
ROOT = plugin_root()

# --- build-injected: the plugin version this run was generated with. SKILL.md is a
# template, so `1.0.0-beta.3.1` is replaced at plugin build time with the shipped
# version — leave this line EXACTLY as rendered; do not edit, retype, or author it.
# It is stamped into the artifact it builds (and the step-7 schedule) so a later plugin
# update can detect what version built it and refresh anything stale. ---
PLUGIN_VERSION = "1.0.0-beta.3.1"

# --- the ONLY things you type out (from step 4 / step 0) ---
USER_NAME = "<rep first name>"                             # from 1a
ROLE      = "<rep role/title>"                             # from 1b, or "not set"
DISPATCH_TOOL = "mcp__salesforce-h360__dispatch_readonly"   # EXACT name verified in step 0
OWNER_ID      = "<UID>"                                     # running user's Id
FIELD_MAP = {"nextStep": "NextStep"}                       # from step 4: concept -> resolved Opportunity field API name (omit a concept to use its standard default; e.g. {"amount":"Amount","nextStep":"Next_Step__c"})
QUOTA, FY_START_MONTH = None, 1                             # QUOTA only if sourced in 1i; else None

ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

# --- Your Sales Intelligence artifact ---
IDENTITY = {"userName": USER_NAME, "role": ROLE, "quota": QUOTA, "fyStartMonth": FY_START_MONTH}
c = pathlib.Path(ROOT, "skills/configure/your-sales-intelligence.html").read_text()
c = (c.replace('var DISPATCH_TOOL = "__DISPATCH_TOOL__";', 'var DISPATCH_TOOL = ' + json.dumps(DISPATCH_TOOL) + ';')
      .replace('var OWNER_ID = "__OWNER_ID__";',           'var OWNER_ID = ' + json.dumps(OWNER_ID) + ';')
      .replace('var IDENTITY = __IDENTITY__;',             'var IDENTITY = ' + json.dumps(IDENTITY) + ';')
      .replace('var FIELD_MAP = __FIELD_MAP__;',            'var FIELD_MAP = ' + json.dumps(FIELD_MAP) + ';')
      .replace('var PLUGIN_VERSION = "__PLUGIN_VERSION__";', 'var PLUGIN_VERSION = ' + json.dumps(PLUGIN_VERSION) + ';'))
assert "__DISPATCH_TOOL__" not in c and "__OWNER_ID__" not in c and "__IDENTITY__" not in c and "__FIELD_MAP__" not in c and "__PLUGIN_VERSION__" not in c, "a placeholder was not replaced"
pathlib.Path("your-sales-intelligence.artifact.html").write_text(c)

print("wrote your-sales-intelligence.artifact.html")
PY
```

`IDENTITY.quota` is `null` unless you sourced a quota in 1i (the Attainment donut degrades to a closed-won summary); `fyStartMonth` defaults to `1` if you don't know the org's fiscal year start. On a re-run the file is overwritten with fresh data and a fresh timestamp — that's the intent, don't create a second copy.

**If your session has no shell** (the command can't run): copy the Your-Sales-Intelligence template into scratch and use the **Edit** tool to replace the placeholders in place — the five `__…__` tokens. Never Read-then-Write a whole template — that re-emits it.

## 6. Create Your Sales Intelligence artifact, then confirm

**This is the step that actually builds the artifact — it is required, not optional, and is the only thing that makes the view appear in Cowork.** The file exists from step 5. Issue the single `create_artifact` call below. (If the artifact already exists — a rebuild or refresh — call `update_artifact` with the same `id` and `html_path` instead.) The template carries a matching machine-managed `@h360-artifact-id: your-sales-intelligence` HTML comment (its stable identity, so it stays identifiable even if the user renames it in Claude), so the `id` you pass **must equal that stamp** — never invent a different one:

```
create_artifact({ "id": "your-sales-intelligence", "html_path": "your-sales-intelligence.artifact.html", "description": "Your live sales intelligence view", "mcp_tools": ["<DISPATCH_TOOL>"] })
```

- **Your Sales Intelligence** — the `your-sales-intelligence` artifact, with **exactly one `mcp_tools` entry: `<DISPATCH_TOOL>`** (verbatim the value from step 0; the host blocks any tool not declared and not called this session). It pulls live data by calling only `<DISPATCH_TOOL>` via `window.cowork.callMcpTool`, running owner-scoped **SOQL** over `/services/data/v63.0/query` (flat records — no GraphQL envelopes, no memory dependency), and computes everything client-side: the **KPI strip** (open pipeline, weighted, closed-won this year, win rate), the **"What needs attention"** signals (quiet deals >30d, closing this week, new leads), the **Attainment** donut, and **pipeline-by-stage** + **amount-by-close-month** charts; caches via `window.storage`.

Then send this line verbatim, followed by step 7's question in the same message:

```
Your Sales Intelligence is ready — take a minute to review it. This is just a starting point, though: swap in different data, rework the layout or restyle it completely. Let me know what you'd like to change.
```

## 7. Offer the daily refresh schedule

Do this once the work above is done: after Your Sales Intelligence is created in step 6, or — if the user handed off to a personalized skill or answered "Other" in step 4 — after that work is done. List the current scheduled tasks **before** asking anything, and look for an existing refresh task as described below. The user is asked only when none exists, and a task is created only on yes.

The job defers to the **`update`** skill — the stable, version-aware maintenance entrypoint that keeps the plugin current; this skill (`configure`) doesn't describe what `update` does — `update` owns that.
**Name the task `Salesforce Updates`.** If the scheduling tool has a name/title field, set it to exactly `Salesforce Updates`. Regardless, the prompt's **first line must be `Salesforce Updates`** — some schedulers (e.g. `CronCreate`) have no title field, so the first line is the only durable identity, and `update` reads the baseline off this same task. **Create a scheduled task** to run daily (at an off-:00/:30 minute so it doesn't pile up with other jobs) with the prompt below **verbatim** — the `Created with plugin version 1.0.0-beta.3.1` line is build-injected (SKILL.md is a template) and records which plugin version set the job up, so a later run can detect a job created by an older version and re-create it; leave it exactly as rendered.

> Salesforce Updates. Created with plugin version 1.0.0-beta.3.1. Run `/update` for the current user to keep the Sales Cloud plugin current. Invoke the `update` skill explicitly by that name (it is not model-auto-invoked). Emit no chat narration unless something fails. (Follow the `update` skill body — don't reproduce its steps or any HTML here.)

Use whatever scheduling capability is available in the session to create a recurring, durable daily task with that instruction as its prompt. **First check for an existing scheduled task that already does this refresh** — list the current scheduled tasks and look for one named `Salesforce Updates` or whose prompt starts with `Salesforce Updates` (match on that stable identity line, NOT the whole prompt — the `Created with plugin version …` line differs between versions). Also match a legacy job — one starting with `Daily Headless 360 update` or `Daily configure refresh` (earlier wordings) — as the same task. Then:
- **No existing refresh task** → ask whether they'd like a daily `Salesforce Updates` schedule, using the native question tool (`AskUserQuestion` — e.g. "Want me to keep the plugin current for you every day?", options `Yes, schedule it` / `No thanks`); if it isn't available, ask in plain text. **Only on yes, create it** now with the prompt above. On no, create nothing and don't ask again.
- **An existing refresh task whose version line matches `1.0.0-beta.3.1`** → skip the question and leave it; do NOT create a second (re-running configure at the same version won't duplicate it).
- **An existing refresh task created with a DIFFERENT (older) plugin version, or a legacy `Daily Headless 360 update` / `Daily configure refresh` job** → it's stale and the user already opted in, so without asking: silently delete it and create a fresh one with the prompt above, so the job is named `Salesforce Updates`, carries the current version, and defers to `update`. This is exactly the update-on-new-version path.

When creating or replacing, do it silently and ensure exactly one refresh task exists and it carries the current version. If some scheduled tasks auto-expire (e.g. after a fixed number of days), you may note once that they can re-run configure to renew.

Close with one short line and stop (e.g. "You're all set — the daily refresh is scheduled and I'm here whenever you want to dig in." — or, if they declined, "You're all set — I'm here whenever you want to dig in."). Do not add a summary or recap, and do not end on a bare tool call — a tool-call-only turn makes the harness re-prompt you, costing a full extra round.

## Appendix — artifact HTML source

Your Sales Intelligence renders from a sibling template file: `skills/configure/your-sales-intelligence.html` under the plugin root (step 5's shell command self-resolves that root — `$CLAUDE_PLUGIN_ROOT` if set, else the installed-plugin globs). `create_artifact`/`update_artifact` take an **`html_path`**, not inline HTML — so the substitution is a file operation (a `python3` `.replace` writing to your scratch dir), and you pass that path. **Never Read a template into your reply and retype it** — reproducing hundreds of lines of HTML as output tokens was the dominant cost of this skill; the only content you should ever type out is the small authored dataset (`USER_NAME`, `ROLE`, and the `OWNER_ID`/`DISPATCH_TOOL`/quota values).