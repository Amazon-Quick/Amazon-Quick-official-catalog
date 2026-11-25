---
name: research-prospect
display_name: Research Prospect (Preview)
description: "Research a specific company or prospect before outreach, tell me about them, who they are, what I should know, or build a prospect brief with ICP fit analysis. Requires company name or domain. Combines web research and Salesforce data, covering company facts, recent signals, likely priorities, contacts and ICP fit. Use for net-new companies or people before first outreach. Existing accounts: account-context."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:31f4244781d0cd69c83a1a805aaa53f3d401f79a0af9fd810a6eb19f25fabd20"
id: "64b8346c-09b3-4573-8247-ba4202ac1bb9"
---
<!-- global-rules-bootstrap -->

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
- **⛔ WIDGET OUTPUT ONLY after data assembly.** Once all queries return, immediately call `display_widget` — at most a single one-line render-wait notice before it, and no summaries, transitions, or narration. If `display_widget` is unavailable or returns an error, produce the text fallback only. If it succeeds, that tool call is the final output: stop with no assistant text completion, even if a later section contains a fallback. The exceptions above do not apply after success.
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
<!-- response-formatting -->
## Response formatting

- **Number formatting:** Format numbers for readability across the entire response, including values retrieved directly from Salesforce fields. Abbreviate large numbers with a suffix for their scale: K (thousand), M (million), B (billion), T (trillion), and the next suffix up for anything larger, never leaving a big number unabbreviated or spelling it out in full (e.g., $120K, $1.25M, $2.4B, $1.3T), and round percentages to whole numbers unless decimals are required for meaningful comparison.
- **Empty table cells (structured data tables only):** keep empty states terse and never explain them inside a table cell.
  - AI-generated cells: write "Not enough data" when the returned data cannot support a grounded answer (for example, a Suggested Action cell when no recommendation can be supported).
  - Cells filled directly from CRM fields: leave the cell blank when the source field was queried and confirmed empty or null. Keep valid values such as 0.
# Rules:


# Research Prospect

See [references/research-workflow.md](references/research-workflow.md) for workflow overview.

Ground Account → CRM read + web research (ONE turn) → score fit → output. Grounding surfaces this org's custom ICP fields (tier/segment/territory) — fit scoring reads them, so don't skip it.

## 1. Inputs

- **Company name or domain** (required)
- **Contact name or title** (optional)

ICP (industries, size, titles, disqualifiers), value prop, competitors, differentiators are external knowledge — infer from org data or confirm with the user once. Never invent.

## 2. Ground Account (this turn), then CRM read + web research (ONE turn)

**Ground Account first** — its `__c` fields are this org's ICP schema (tier, segment, territory, employee band, etc.), and Step 3 scores fit against them. Account always exists, so this one call never fails on a missing object:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { fields { ApiName label } } } }\"}" })
```
From the result, note the scalar `__c` fields whose label carries ICP/segment/tier/territory/employee-band signal — add each as `Field__c { value }` to `<ACCOUNT_CUSTOM>` in the read below.

**Just scan the result by eye — do not script the extraction**. The Account catalog is large and may not come back inline: if it overflows or comes back truncated, skip custom-field grounding and proceed with standard fields only; don't keep retrying. Do the same if the payload is unwieldy.

**CRM read + web search — fire BOTH as tool calls in ONE turn (independent).**

**Salesforce** — read the matching Account over GraphQL (Account is UI-API-serviceable; no SOQL needed). Insert `<ACCOUNT_CUSTOM>` = the confirmed scalar `__c { value }` fields from grounding.

Match on **`Name` first**. Do **not** combine Name and Website with `or` — a two-clause `or` in a UI-API `where` 500s on this endpoint. Only if the name search returns no rows, run the Website-only fallback below.
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 5) { edges { node { Id Name { value } Website { value } Industry { value displayValue } NumberOfEmployees { value } Type { value displayValue } <ACCOUNT_CUSTOM> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } Contacts(first: 10) { edges { node { Id Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```
- **Found** → note owner, open opps, known contacts. Output must say "already in CRM, owned by [Name]" prominently so the user doesn't step on a colleague.
- **No rows** → run the **Website-only fallback** (a `%DOMAIN%` match), still no `or`:
```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
         queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Website: { like: \\\"%DOMAIN%\\\" } }, first: 5) { edges { node { Id Name { value } Website { value } Industry { value displayValue } NumberOfEmployees { value } Type { value displayValue } <ACCOUNT_CUSTOM> Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, orderBy: { CloseDate: { order: ASC } }, first: 10) { edges { node { Id Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } Contacts(first: 10) { edges { node { Id Name { value } Title { value } Email { value } } } } } } } } } }\"}" })
```
- **Still no match** → "net new - no CRM record". Broaden `%…%` once if a partial name seems likely; don't retry the same shape.

**Web search** (same turn, independent of the SFDC result):
- Company basics: what they do, HQ, size, funding stage, leadership
- Recent signals (last 6 months): funding rounds, exec hires, product launches, layoffs, earnings, expansion
- Tech/operating context relevant to your product category
- Likely priorities, inferred from the signals (e.g. just raised → hiring + scaling; new CRO → pipeline overhaul)
- If a contact was specified: their role, tenure, prior companies, public talks/posts, and what they likely care about

## 3. ICP fit scoring

| Dimension | Fit | Evidence |
|---|---|---|
| Industry | ✅ / ⚠️ / ❌ | [from research] |
| Company size | ✅ / ⚠️ / ❌ | [employee count vs ICP range] |
| Buyer persona present | ✅ / ⚠️ / ❌ | [title found / inferred] |
| Disqualifiers | ✅ none / ❌ [which] | |
| Timing signal | ✅ / ⚠️ / ❌ | [recent trigger event or none] |

Overall: **Strong fit / Moderate fit / Poor fit** with one-sentence rationale.

## 4. Relevance hooks

2-3 specific, sourced hooks for outreach — things from the research that connect to your value prop. Not generic ("they're growing") but specific ("they posted 12 [relevant role] openings last month and their [exec title] spoke about [relevant pain] at [conf]").

## 5. Prospect brief widget (editorial layout)

When the `display_widget` tool is available (a widget-capable client), render the prospect brief as a visual widget instead of the section 6 text. When `display_widget` is unavailable (e.g. a terminal) the section 6 markdown is the whole output, so produce it only then.

When the data is assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] `data` is a nested JSON object, NOT a string.
- [ ] All values in data are literals — no template syntax.
- [ ] Only `title`, `answer`, and `sources` are required; every other optional key is justified by the prompt (see "Scope the blocks to the prompt").
- [ ] The `answer` is scoped to the prompt: if the user asked only about ICP fit, give only the fit facts, not the full firmographics.
- [ ] Tail fork: sent `callout` XOR `nextStep`, never both.
- [ ] Every `contacts` row has `draftLabel`, `draftText` and `draftMsg`.
- [ ] Omitted keys have no data or weren't asked for — never send empty placeholders.
- [ ] The section 6 markdown is produced only when `display_widget` is unavailable (the terminal fallback) — not alongside a rendered widget.

Send only the widget name and its data — no layout, no `{!…}`:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/research-prospect", props: <object matching the schema below> })
```

- Send data only; no layout and no `{!…}`.
- **`props` is a nested JSON object, NOT a string.**
- The widget is the output, even for a narrow ask: a one-fact question sends just `title`, `answer` and `sources`, never prose. Once the call succeeds, add no text after it. Reply in text (§6) only when `display_widget` is unavailable or errors.

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Scope reading and output to the prompt.** Broad asks ("Research [Company]", "Brief me on [Company]") get the full card set (ICP score, signals, contacts); specific asks ("Is [Company] a good fit?", "Who should I reach out to?") get only the matching card. Don't show something just because you fetched it.
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated and write every free-text field in that language.
- **Send data only; never author presentation** (colors, layout, template expressions): the renderer owns the look and shows or hides each block from the keys you send.

### The response is lego blocks, in this fixed order

1. **`title`** (required): The takeaway sentence in the user's context — ICP fit read + hook + ownership status. Never the skill name.
2. **`answer`** (required): 2–4 markdown bullets with **bold** facts. Scope to the prompt: broad → firmographics + CRM status + whitespace + timing; specific → only what was asked.
3. **`icpScore`**: ICP fit score card with numeric score + rating + threshold + flag rows. **ALWAYS include for broad prompts** ("Research [Company]", "Brief me on [Company]"). Also include when specifically asked about ICP fit.
   - `score` (number, required): Numeric ICP fit score out of 100. Example: 72
   - `rating` (string, required): Qualitative rating based on score. Example: "moderate", "strong", "weak"
   - `threshold` (number, required): Threshold score for "strong" rating. Example: 80
   - `flags` (array, required): Fit dimension rows, ranked by impact (blockers first)
4. **`signals`** (optional): External signals table (M&A, funding, earnings). Include ONLY when the prompt is broad or asks about signals/timing.
5. **`contacts`** (optional): Stakeholder rows ranked by fit, with draft-outreach hooks and buttons. Include ONLY when the prompt is broad or asks about who to contact. **Every contact row carries a draft card:** `draftLabel` (`"DRAFT"`), `draftText` (a short first-touch message to that person, 2–3 sentences, built only from facts you gathered) and `draftMsg` (a first-person request to draft the full email, e.g. "Draft an intro email to Edward Stamos at Acme United, leading with the efficiency angle."). Without `draftText` the card does not render.
   Add `Phone { value }` to the Contacts selection of the account query, and send `email` and `phone` on every row whose record has them; the widget renders them as links.
6. **Tail (XOR)**: Either `callout` (time-sensitive/blocked) OR `nextStep` (non-urgent), never both.
7. **`sources`** (required): Provenance footer: CRM records and web sources.

### Scope the blocks to the prompt

| The prompt is… | Send |
|---|---|
| Broad ("Research [Company]", "Brief me on [Company]") | `title` + `answer` + `icpScore` + `signals` + `contacts` + tail + `sources` |
| Specific about ICP ("Is [Company] a good fit?") | `title` + `answer` + `icpScore` + tail + `sources` |
| Specific about contacts ("Who should I reach out to at [Company]?") | `title` + `answer` + `contacts` + tail + `sources` |
| Specific about signals ("What recent events matter at [Company]?") | `title` + `answer` + `signals` + tail + `sources` |
| Direct question ("What's [Company]'s industry?") | `title` + `answer` + `sources`; a card only if it speeds up the answer |

### Rules

- Omit a key and its block is not shown; never send empty or placeholder values.
- Scope the `answer` too: if the user asked only about ICP fit, give only the fit facts in `answer`.
- The tail is XOR in the data: send `callout` when time-sensitive or blocked, `nextStep` otherwise, never both.
- Currency, dates, and counts are display-ready strings (e.g., "$230K", "Jan 2026", "3 open opportunities").
- Names are plain strings, URLs follow Lightning format (`https://<myDomain>/lightning/r/<Type>/<Id>/view`).
- Rank `icpScore.flags` most-severe first (blockers → cautions → context).
- Rank `signals.rows` by relevance to the value prop.
- Rank `contacts` by fit (best entry point first).
- Every `contacts` row includes `draftLabel`, `draftText` and `draftMsg`. Ground `draftText` in the pipeline, signals and role you found; never invent events or relationships. When the account is owned by someone else, keep the draft neutral and let `hook` carry the coordinate-first caveat.
- Before calling: no template expressions, no keys outside the schema.

#### Worked examples (the data object only)

**Broad — "Research Acme United Corp before I reach out."** (all blocks — ICP fit, signals, contacts, next step):

```json
{
  "title": "Acme United is a moderate fit (72/100) — the hook is efficiency, and this account is already owned.",
  "answer": "- **Manufacturing, 680 employees, mid-market, public on NYSE as ACU** — a reasonable Ideal Customer Profile match, but not a clean one.\n- **Already in Salesforce, owned by OrgFarm EPIC with 3 open opportunities ($230K)** on a stale 2024 close date — so this is a coordinate-first motion, not a cold reach.\n- **Whitespace is Sales Cloud and Service Cloud**; the strongest angle is efficiency and cost reduction, not growth.",
  "icpScore": {
    "score": 72,
    "rating": "moderate",
    "threshold": 80,
    "flags": [
      {
        "title": "Fits the profile — Manufacturing, 680 employees, public on NYSE as ACU.",
        "detail": "Industry, size, and public-company profile match the ideal profile.",
        "tone": "success"
      },
      {
        "title": "Ownership conflict — already in Salesforce under a different representative.",
        "detail": "Owned by OrgFarm EPIC with $230K of open pipeline on a stale 2024 close date. Coordinate before any outreach.",
        "tone": "warning"
      }
    ]
  },
  "signals": {
    "rows": [
      {
        "signal": "M&A",
        "headline": "SLED Distribution acquisition · Jan 2026.",
        "context": "Asset acquisition adds integration and scaling needs — a natural expansion conversation once ownership is coordinated. Best entry point."
      }
    ]
  },
  "contacts": [
    {
      "name": "Edward Stamos",
      "title": "President & CEO",
      "email": "estamos@acmeunited.com",
      "phone": "+1 (203) 555-0142",
      "hook": "Lead with the efficiency and cost-reduction story.",
      "draftLabel": "DRAFT",
      "draftText": "Edward — congratulations on the SLED Distribution close...",
      "draftMsg": "Draft an intro email to Edward Stamos at Acme United, leading with the efficiency angle and the SLED acquisition."
    }
  ],
  "nextStep": {
    "text": "This is a coordinate-first account — align with OrgFarm EPIC on the efficiency angle before any outreach.",
    "buttonLabel": "Save to Salesforce",
    "actionMsg": "Save this research to the Acme United account record in Salesforce."
  },
  "sources": [
    {
      "label": "Account: Acme United Corp",
      "url": "https://orgfarm.lightning.force.com/lightning/r/Account/001AX000005mNq8YAE/view"
    }
  ]
}
```

**Specific — "Is Acme United a good fit for our ICP?"** (ICP score only, answer scoped to fit):

```json
{
  "title": "Acme United is a moderate fit (72/100) — Manufacturing profile matches, but ownership conflict requires coordination.",
  "answer": "- **Fits on industry, size, and public-company profile** — Manufacturing, 680 employees, NYSE-listed.\n- **Ownership conflict blocks direct outreach** — already owned by OrgFarm EPIC with $230K stale pipeline.\n- **Mixed financials** — tariff pressure makes efficiency story stronger than growth.",
  "icpScore": {
    "score": 72,
    "rating": "moderate",
    "threshold": 80,
    "flags": [
      {
        "title": "Fits the profile — Manufacturing, 680 employees, public on NYSE as ACU.",
        "detail": "Industry, size, and public-company profile match the ideal profile.",
        "tone": "success"
      },
      {
        "title": "Ownership conflict — already in Salesforce under a different representative.",
        "detail": "Owned by OrgFarm EPIC with $230K of open pipeline on a stale 2024 close date. Coordinate before any outreach.",
        "tone": "warning"
      }
    ]
  },
  "sources": [
    {
      "label": "Account: Acme United Corp",
      "url": "https://orgfarm.lightning.force.com/lightning/r/Account/001AX000005mNq8YAE/view"
    }
  ]
}
```


`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; include any other key only when the prompt asks for it or it clearly speeds up the answer (see "Scope the blocks to the prompt").

The optional `labels` object lets you override fixed eyebrow text for non-English prompts. For English prompts, omit `labels` entirely — the renderer uses defaults. Only include it when the user's prompt is clearly non-English.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "description": "Data contract for research-prospect lego widget. The model sends this shape as props to ui://widget/standard/research-prospect. Only title/answer/sources are required; include any other key only when the prompt asks for it or when it speeds understanding.",
  "properties": {
    "title": {
      "type": "string",
      "description": "The takeaway sentence in the user's context \u2014 ICP fit read + hook + ownership status. Never the skill name."
    },
    "answer": {
      "type": "string",
      "description": "2\u20134 markdown bullets with **bold** facts. Scope to the prompt: broad \u2192 firmographics + CRM status + whitespace + timing; specific \u2192 only what was asked."
    },
    "icpScore": {
      "type": "object",
      "description": "Include ONLY when the prompt is broad or asks about ICP fit. ICP fit score card with flag rows explaining the score dimensions.",
      "additionalProperties": false,
      "required": [
        "flags"
      ],
      "properties": {
        "score": {
          "type": "number",
          "description": "Numeric ICP fit score out of 100. Example: 72"
        },
        "rating": {
          "type": "string",
          "description": "Qualitative rating based on score. Example: 'moderate', 'strong', 'weak'"
        },
        "threshold": {
          "type": "number",
          "description": "Threshold score for 'strong' rating. Example: 80"
        },
        "flags": {
          "type": "array",
          "description": "Fit dimension rows, ranked by impact (blockers first). Each row: title (the dimension + verdict), detail (evidence), tone (error/warning/success).",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "title",
              "tone"
            ],
            "properties": {
              "title": {
                "type": "string",
                "description": "Bold dimension line with verdict. Example: 'Fits the profile \u2014 Manufacturing, 680 employees, public on NYSE as ACU.'"
              },
              "detail": {
                "type": "string",
                "description": "Muted evidence line beneath. Example: 'Industry, size, and public-company profile match the ideal profile; the Jan 2026 SLED Distribution acquisition signals integration and scaling needs.'"
              },
              "tone": {
                "type": "string",
                "enum": [
                  "error",
                  "warning",
                  "success",
                  "muted"
                ],
                "description": "Severity: error (blocker), warning (caution), success (strong fit), muted (context)."
              }
            }
          }
        }
      }
    },
    "signals": {
      "type": "object",
      "description": "Include ONLY when the prompt is broad or asks about signals/timing. External signals (M&A, funding, earnings, etc.).",
      "additionalProperties": false,
      "required": [
        "rows"
      ],
      "properties": {
        "rows": {
          "type": "array",
          "description": "Signal rows, ranked by relevance to the value prop.",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": [
              "signal",
              "headline",
              "context"
            ],
            "properties": {
              "signal": {
                "type": "string",
                "description": "Signal category (bold, short). Example: 'M&A', 'Financing', 'Earnings'"
              },
              "headline": {
                "type": "string",
                "description": "Bold lead for the detail. Example: 'SLED Distribution acquisition \u00b7 Jan 2026.' or 'Q1 2026 results:'"
              },
              "context": {
                "type": "string",
                "description": "Plain text context following the headline. Example: 'Asset acquisition adds integration and scaling needs \u2014 a natural expansion conversation once ownership is coordinated. Best entry point.'"
              }
            }
          }
        }
      }
    },
    "contacts": {
      "type": "array",
      "description": "Include ONLY when the prompt is broad or asks about who to contact. Stakeholder rows ranked by fit, with draft-outreach hooks and buttons.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "name",
          "title",
          "hook"
        ],
        "properties": {
          "name": {
            "type": "string",
            "description": "Full name. Example: 'Edward Stamos'"
          },
          "title": {
            "type": "string",
            "description": "Role and any context. Example: 'President & CEO' or 'VP Customer Support \u00b7 potential champion'"
          },
          "email": {
            "type": "string",
            "description": "Email address if known."
          },
          "phone": {
            "type": "string",
            "description": "Formatted phone if known. Example: '+1 (203) 555-0142'"
          },
          "hook": {
            "type": "string",
            "description": "The reason to reach out, without a \"Why reach out\" prefix (the widget adds the label). Example: 'Lead with the efficiency and cost-reduction story.'"
          },
          "draftLabel": {
            "type": "string",
            "description": "Draft button label. Example: 'Draft' or omit if no draft message."
          },
          "draftText": {
            "type": "string",
            "description": "The actual drafted message body to show in the card. Example: 'Edward \u2013 congratulations on the SLED Distribution close. As you integrate those assets, a few manufacturing peers have used us to consolidate ops and protect margin against tariff pressure. Worth a 20-minute conversation on where the efficiency gains land first?'"
          },
          "draftMsg": {
            "type": "string",
            "description": "First-person prompt for action/sendMessage. Example: 'Draft an intro email to Edward Stamos at Acme United, leading with the efficiency angle and the SLED acquisition.'"
          },
          "source": {
            "type": "string",
            "description": "Context badge for non-CRM contacts. Example: 'Not in Salesforce \u00b7 from LinkedIn'"
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "Include ONLY for time-sensitive or urgent recommendations. Mutually exclusive with nextStep (tail fork). Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "additionalProperties": false,
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). Bold callout heading. Example: 'Coordinate with the owner first'"
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). Callout body \u2014 what to do and why."
        },
        "level": {
          "type": "string",
          "enum": [
            "tip",
            "note",
            "blocker"
          ],
          "description": "Emphasis level per design rules: tip (quiet context), note (standard move), blocker (time-sensitive/blocked). Omit to default to 'note'."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Primary action button label. Omit if no button."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person prompt for action/sendMessage when button is clicked."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "description": "Include ONLY when no callout (tail fork). Non-urgent suggested next action.",
      "additionalProperties": false,
      "required": [
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Optional bold lead-in. Example: 'Save this research to the account record'"
        },
        "text": {
          "type": "string",
          "description": "Suggested next step. Example: 'This is a coordinate-first account \u2014 align with OrgFarm EPIC on the efficiency angle before any outreach. Save this research to the account record so the owner has the signals and draft messages in context.'"
        },
        "buttonLabel": {
          "type": "string",
          "description": "Action button label. Example: 'Save to Salesforce'. Omit if no button."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person prompt for action/sendMessage when button is clicked."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "Always required. Provenance footer: CRM records and web sources. Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "label"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name. Example: 'Account: Acme United Corp' or 'Acme United Q1 2026 Earnings'"
          },
          "url": {
            "type": "string",
            "description": "Link if available. CRM records use Lightning URLs; web sources use their public URL."
          }
        }
      }
    },
    "labels": {
      "type": "object",
      "description": "Optional fixed label text for non-English prompts. Model omits this for English; host fills missing values from defaults.",
      "additionalProperties": false,
      "properties": {
        "icpScoreCaption": {
          "type": "string",
          "default": "ICP Fit Summary",
          "description": "ICP fit card heading"
        },
        "icpFlagsCaption": {
          "type": "string",
          "default": "Fit Dimensions",
          "description": "ICP flags table caption"
        },
        "signalsCaption": {
          "type": "string",
          "default": "Recent Findings",
          "description": "Signals card heading"
        },
        "signalCategoryHeader": {
          "type": "string",
          "default": "Signal Category",
          "description": "Signals table first column header"
        },
        "signalHeader": {
          "type": "string",
          "default": "Signal",
          "description": "Signals table second column header"
        },
        "contactsCaption": {
          "type": "string",
          "default": "Who to Contact",
          "description": "Contacts card heading"
        },
        "hookPrefix": {
          "type": "string",
          "default": "Why Reach Out",
          "description": "Hook prefix label"
        },
        "send": {
          "type": "string",
          "default": "Send",
          "description": "Send button label"
        }
      }
    }
  }
}
```



## 6. Output (FALLBACK ONLY — DO NOT USE IF display_widget SUCCEEDED)

Scope this to the prompt too: if the user asked only about ICP fit, give only the ICP section and the headline. Omit any section whose source wasn't available or that the prompt didn't ask for.

```
# Prospect Research: [Company]

## CRM Status
[Already in Salesforce - owned by [Name], [N] open opps | OR | Net new - no CRM record]

## Company Snapshot
- What they do: [one line]
- Size / stage: [employees, funding]
- HQ: [location]
- Leadership: [key names + titles]

## Recent Signals
- [Date] - [Signal] ([source])
...

## [Contact Name] (if specified)
- Role / tenure / background
- What they likely care about

## ICP Fit: [Strong / Moderate / Poor]
[Scoring table]
[One-sentence rationale]

## Relevance Hooks
1. [Specific hook] - ties to [your value prop angle]
2. ...

## Suggested Next Step
[e.g. "Run draft-outreach targeting [Contact]" or "Low fit - log as disqualified" or "Already owned by [Name] - coordinate before reaching out"]
```
