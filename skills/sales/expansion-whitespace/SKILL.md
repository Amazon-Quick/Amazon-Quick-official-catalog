---
name: expansion-whitespace
description: "Identify ranked expansion plays for one customer from Salesforce contacts, owned products and opportunities plus recent email, documents and Slack. Use to find evidence-backed whitespace, upsell paths or adjacent teams and products ready for outreach."
icon: assets/salesforce.svg
checksum: "sha256:ad0d881cd2c56138113c995f751ccd44b428309e319306a79250dffbaf96e649"
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

- **Expansion Whitespace text contract.** Aside from the exact required pre-widget notice, the text fallback is the only permitted prose, and it must start with `# Expansion Whitespace`.

# Expansion Whitespace

Resolve account → ground → read → map whitespace → output. Product catalog is external knowledge — ask once.

## 1. Resolve the account

Shared/demo orgs collide on name. If user gave Salesforce Id, skip to Step 2. Otherwise:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%ACCOUNT%\\\" } }, first: 10) { edges { node { Id Name { value } Website { value } Type { value } Industry { value } Owner { Name { value } } } } } } } }\"}" })
```

**One match** → take its Id, continue to Step 2.

**Several** → STOP. Before Step 2, determine which account:
- **If user provided $amount or seat count:** Search Opportunities across ALL candidate account Ids to find which has matching renewal/deal:
  ```
  dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
    queryParams: { "q": "SELECT Id, AccountId, Account.Name, Name, Amount, CloseDate, StageName FROM Opportunity WHERE AccountId IN ('<ID1>','<ID2>',...) AND (Amount = <USER_AMOUNT> OR Name LIKE '%<USER_PRODUCT>%' OR CloseDate >= TODAY) ORDER BY CloseDate DESC LIMIT 50" })
  ```
  Match by Amount or product name. Take that AccountId, continue to Step 2.

- **Else:** List candidates (Name · Website/Industry · Owner · Id) and ask user to pick.

**None** → broaden name or ask for correct account. Don't guess.

## 2. Ground (hardcoded — Account + Contact)

Ground **Account + Contact** (both always exist). Lean projection discovers this org's custom fields without the full schema payload. **Fire as two separate calls** (combined ObjectInfo often overflows):

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { fields { ApiName label } } } }\"}" })
```

From the results: note scalar `__c` fields (Success_Segment, License_Utilization, Job_Function, Job_Level, etc.) — take their `{ value }` in the read queries. Without `dataType`/`relationshipName`, you can't perfectly distinguish scalar vs reference fields, but most customs are scalar; reference fields that slip through will show Ids (cryptic but not broken). Standard relationships (`Account`, `Owner`, `Contacts`, `ChildAccounts`) are hardcoded in queries below.

## 3. Read (fill from steps 1–2)

Insert `<ACCOUNT_CUSTOM>` = confirmed scalar `__c { value }` fields on Account; `<CONTACT_CUSTOM>` = confirmed scalar `__c { value }` fields on Contact (role, department, etc.).

**Fire TWO separate dispatches in ONE turn** (parallel, no dependency). Triple-nesting (Account > Opportunities > OpportunityLineItems) commonly fails; split avoids errors.

**Dispatch A — Account + Contacts + ChildAccounts:**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } NumberOfEmployees { value } AnnualRevenue { value displayValue } <ACCOUNT_CUSTOM> Contacts(first: 30) { edges { node { Name { value } Title { value } <CONTACT_CUSTOM> } } } ChildAccounts { edges { node { Name { value } Industry { value } Owner { Name { value } } } } } } } } } } }\"}" })
```

**Dispatch B — Won Opportunities + line items (the actual products/SKUs owned):**
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { Account: { Id: { eq: \\\"<ACCOUNT_ID>\\\" } }, IsWon: { eq: true } }, first: 30, orderBy: { CloseDate: { order: DESC } }) { edges { node { Name { value } Amount { value } CloseDate { value } StageName { value } Description { value } OpportunityLineItems(first: 50) { edges { node { Quantity { value } TotalPrice { value displayValue } Product2 { Name { value } } } } } } } } } } }\"}" })
```

The `OpportunityLineItems` child (span `Product2` for the SKU name, with `Quantity`/`TotalPrice`) is the real "Owned today" input for the Step 4 grid — one read, no extra round-trip (this is a single child level, not the triple-nesting that overflows). Fall back to `Opportunity.Name` only if the org doesn't use line items (empty `edges`).

For book-level sweep: replace Dispatch A `where: { Id: { eq: ... } }` with `scope: MINE` or team filter, limit 20.

## 3b. Evidence (run IN PARALLEL with step 3 — same turn)

**Issue step 3 and all of step 3b as tool calls in a single turn.** They're independent (searches key on account name, not the SF result):
- **email**: threads mentioning teams/use-cases/products not yet sold, **plus recent events/invites/webinars as timing hooks**
- **docs**: recent transcripts/notes → teams/departments mentioned, **job changes, new projects**
- **slack**: internal mentions → expansion plays discussed

Use whatever email/doc/Slack search tools are available. If none present, skip silently (SF-only is fine). Cite source + date for anything you use. **Prioritize evidence from last 90 days for recency/relevance.**

## 4. Map whitespace

**Product catalog (external):** ask user for the product/SKU list once — never invent. Build owned-vs-possible grid:

| Dimension | Owned today | Whitespace | Evidence |
|---|---|---|---|
| Products / SKUs | [SKUs owned, from Dispatch B's OpportunityLineItems (Product2 name · Quantity · TotalPrice); fall back to Opportunity.Name only if no line items] | [catalog items they haven't] | [need signal: mentioned in calls/emails? industry-typical?] |
| Teams / departments | [all contacts from Contacts child: name + title, not just technical subset] | [adjacent teams named in transcripts] | |
| Geography / subsidiaries | [entities under contract, plus reseller contacts if Account Type = reseller] | [child accounts with no spend] | |
| Volume / tier | [seats or usage from `__c`, penetration as exact % = seats/NumberOfEmployees] | [headroom vs employee count or benchmark, Success_Segment__c gap if present] | |

**Only call something whitespace if there is at least one piece of evidence** (stakeholder mentioned the team, transcript named the use case, org structure shows the entity). "They could theoretically buy everything" is not a finding.

## 4b. Cross-dimensional analysis (no extra dispatches — use data already fetched)

**Contact-to-product gap:** Cross-match contact titles/roles against owned products. Flag senior/exec/C-suite titles NOT reflected in product ownership (e.g., CIO with no BI tool seat, VP Sales with no CRM license = upsell hook).

**Child account routing:** For ChildAccounts with different Owner than parent, note AE-to-AE warm intro path (e.g., "Parent CIO → intro to Child Account Owner [Name]").

**Quick/Kiro evidence gate:** Render or rank a play only when one evidence record contains a
user-supplied catalog item or a product/use case directly named by a dated source, the exact target
team/subsidiary/use case named by that source, and `source · date — exact supporting fact`. A
contact title, industry, employee count, account health, Opportunity/line-item name or value, or
ChildAccount alone does not establish a product-to-target relationship. Treat
`Opportunity.Amount` and `OpportunityLineItems.TotalPrice` only as account/product history: never
allocate them to a person, team, department, or child account, call them ARR, or derive a value or
range without a dated cited source that supplies the explicit mapping and annual-recurring or
expansion basis. No qualifying record means no evidence-backed play.

**Quick/Kiro motion gate:** `Warm intro` requires dated evidence that an existing contact can
introduce a distinct target person or team. If the contact is the target or belongs to the target
team, use `Research / re-engage`. `Renewal add-on` requires a returned or dated cited active
renewal.

## 5. Rank plays

**Prioritize by sales motion complexity, not just $ size:**
1. **Renewal add-ons** (bundle into active renewal — lowest friction)
2. **Warm intro expansions** (existing contact opens door — medium friction)
3. **Cold new products** (no prior relationship — highest friction)

When evidence strength equal, prefer lower friction. Score on evidence strength, deal size potential, and access. **For reseller/partner accounts in "Owned today", name individual contacts, not just entity.** Top plays get a one-line motion: who to approach, with what message, anchored on which existing success.


## 6. Output — widget FIRST

When the data is assembled, call `display_widget` once; a single one-line "Displaying the
visualization now (this may take a minute)." notice may precede it.

**Quick/Kiro widget gate:** Every row must satisfy the evidence gate and visibly include its
source/date. A direct target uses `Research / re-engage`, not `Warm intro`. With no qualifying
record, use `datagridRows: []`, the exact callout `No evidence-backed expansion play identified`,
and one request for the missing catalog or dated source. Never add a heatmap, pie, allocation, ARR,
fit score, monetary estimate, draft-expansion action, or Opportunity proposal.

### Self-verification (before calling display_widget)

- [ ] `widgetDefinition` is a native JSON object with no unresolved tokens.
- [ ] Every populated row contains Play, Target, Evidence (`source · date — fact`), and Next step.
- [ ] The no-evidence state has an empty row array and the exact no-play callout.

The two JSON blocks below are the only executable widget contract for this skill.

```json
{
  "$comment": "Variable contract for the evidence-first Quick/Kiro expansion widget. This is the only executable expansion widget contract in the active skill. It never renders product-to-business-unit allocation, ARR, estimated values, fit scores, or an opportunity-creation action.",
  "props": {
    "title": {"description": "Account title.", "type": "string", "example": "Expansion whitespace — Meridian Health"},
    "subtitle": {"description": "Evidence state, never a monetary summary.", "type": "string", "example": "No evidence-backed plays · catalog or dated customer source needed"},
    "datagridCaption": {"description": "Caption for evidence-backed plays.", "type": "string", "example": "Evidence-backed plays"},
    "datagridRows": {
      "description": "One row per complete evidence record; empty when no play qualifies.",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "status": {"type": "object", "properties": {"value": {"type": "string"}, "badgeVariant": {"type": "string"}}},
          "play": {"type": "string"},
          "target": {"type": "string"},
          "evidence": {"type": "string", "description": "source · date — exact supporting fact"},
          "motion": {"type": "object", "properties": {"value": {"type": "string"}, "badgeVariant": {"type": "string"}}}
        }
      },
      "example": [{"status": {"value": "Evidence", "badgeVariant": "info"}, "play": "Analytics discovery", "target": "Yard Operations", "evidence": "Call note · 2026-07-24 — team requested analytics coverage", "motion": {"value": "Research", "badgeVariant": "info"}}]
    },
    "calloutTitle": {"description": "Evidence-state heading.", "type": "string", "example": "No evidence-backed expansion play identified"},
    "calloutDescription": {"description": "Missing evidence and one safe next step.", "type": "string", "example": "Share a product catalog or a dated customer source naming a target and use case."},
    "primaryButtonLabel": {"description": "Safe request-for-evidence action label.", "type": "string", "example": "Request evidence"},
    "primaryButtonContent": {"description": "First-person request for the missing evidence.", "type": "string", "example": "Ask me to share a product/SKU catalog or a dated customer source that names a target team and use case."},
    "accountUrl": {"description": "Account Lightning URL.", "type": "string", "example": "https://example.invalid/lightning/r/Account/001000000000000AAA/view"}
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
            "attributes": {"gap": "sm", "align": "center", "isWrapped": false},
            "children": [
              {"definition": "tile/icon", "attributes": {"name": "users", "size": "xl", "alt": ""}},
              {"definition": "tile/text", "attributes": {"text": "{{title}}", "variant": "h1"}}
            ]
          },
          {"definition": "tile/text", "attributes": {"text": "{{subtitle}}", "variant": "caption", "color": "muted"}},
          {"definition": "tile/separator"},
          {
            "definition": "tile/datagrid",
            "attributes": {
              "caption": "{{datagridCaption}}",
              "appearance": "striped",
              "columns": [
                {"key": "status", "header": "Status", "type": "badge"},
                {"key": "play", "header": "Play", "type": "text"},
                {"key": "target", "header": "Target", "type": "text"},
                {"key": "evidence", "header": "Evidence (source · date)", "type": "text"},
                {"key": "motion", "header": "Next step", "type": "badge"}
              ],
              "rows": "{{datagridRows}}",
              "size": "sm"
            }
          },
          {
            "definition": "tile/callout",
            "attributes": {"variant": "info", "title": "{{calloutTitle}}", "description": "{{calloutDescription}}"},
            "children": [
              {
                "definition": "tile/row",
                "attributes": {"gap": "sm", "align": "center", "isWrapped": true},
                "children": [
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "{{primaryButtonLabel}}",
                      "variant": "primary",
                      "actions": {"click": [{"definition": "action/sendMessage", "attributes": {"content": "{{primaryButtonContent}}"}}]}
                    }
                  },
                  {
                    "definition": "tile/button",
                    "attributes": {
                      "label": "View in Salesforce",
                      "iconName": "open-in-new",
                      "variant": "secondary",
                      "actions": {"click": [{"definition": "action/openLink", "attributes": {"url": "{{accountUrl}}"}}]}
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

## 7. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

Use only when the evidence-first widget is unavailable or errors.

```
# Expansion Whitespace: [Account / scope] — [Account Lightning link]

## Evidence-backed plays
1. **[Play]** — target: [team / subsidiary / use case]
   - Evidence: [source · date — exact supporting fact]
   - Motion: [Renewal add-on / Warm intro / Research / re-engage] — [cited reason]

If no evidence record qualifies, write exactly: `No evidence-backed expansion play identified.`

## Missing evidence
- [Catalog item, product-to-target mapping, dated customer source, or value basis]

## Next safe step
[Ask once for the missing catalog or a dated customer source naming the target and use case.]
```

Never show an unsupported allocation, ARR, monetary estimate, contact-spend relationship, or
Opportunity proposal.
