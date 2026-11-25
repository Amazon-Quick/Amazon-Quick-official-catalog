---
name: event-invite-list
display_name: Event Invite List (Preview)
description: "Build a prioritized customer invite list for an event from Salesforce Contact, Account and Opportunity data, ranked by location and ideal-customer-profile fit. Use to plan an event guest list, choose which customers to invite near a city or region, or prioritize contacts by title, segment, revenue or open-opportunity signal."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:2b58d73a70777784e6a25b31fc765cb0c29bc471ddad6517c6304c7a449eeef6"
id: "864b5435-51be-4aca-b3c9-12558b9dfac1"
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

- **Scope reading and output to the prompt, never a default full list.** If the user asks for a specific count or ICP dimension, honor it exactly; if they give a broad event invite request, build the full ranked list. Think in lego blocks: show what the prompt asks for, not everything you could fetch.
- Resolve inputs BEFORE the read. Event location and the ideal customer profile (ICP) drive both the query filter and the ranking — if either is missing from the prompt, ask once (Step 1) before querying. Don't guess a city or invent an ICP.

# Event Invite List

Inputs (ask if missing) → ground Contact + Account → read Contacts near the location, then Opportunities for those accounts (TWO sequential queries) → score ICP fit → rank → render. Default list size: **10 contacts** unless the prompt specifies a number.

## 1. Inputs (ask once if not in the prompt)

Two inputs drive everything. If either is absent from the prompt, ask for both in a single message, then proceed — don't ask again:

- **Event location** (required) — a city, metro, state, or region. Becomes the mailing-address filter in Step 3.
- **Ideal customer profile** (required) — any mix of: title / role, job function, job level, customer segment, account industry, account size, account revenue, open-opportunity status, opportunity amount or close date, recent activity. Whatever the user gives is the ranking rubric in Step 4.

Also honor an explicit **list size** if given (e.g. "give me 25"); otherwise default to **10**. The ICP itself is the user's to define — infer unstated dimensions from the org's own data only when reasonable, never invent a disqualifier the user didn't state.

## 2. Ground (hardcoded — Contact and Account)

Ground **Contact** and **Account** — both always exist (naming a missing object fails the whole call), and their `__c` fields reveal this org's real segment/industry/revenue/job-level schema, which Step 4 ranks against. Issue these independent requests in the **same tool turn** so they run in **parallel**:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Account\\\"]) { ApiName fields { ApiName label } } } }\"}" })
```

**If either overflows** or comes back truncated, skip custom-field grounding and proceed with standard fields only; don't keep retrying.

From each response, select by API name and label the scalar `__c` fields carrying ICP signal (job level, job function, persona, segment, industry, employee band, annual revenue, tier, etc.). Add Contact `__c` fields as `<CONTACT_CUSTOM>` and Account `__c` fields as `<ACCOUNT_CUSTOM>` in the read below. The `Account` and `Owner` spans are standard and hardcoded.

## 3. Read contacts near the location (fill from step 2, TWO sequential dispatches)

**GraphQL doesn't allow Opportunities nested under Account under Contact.** Read in two steps — contacts + accounts first, then opportunities for those account IDs.

### 3a. Read contacts with accounts

`%LOCATION%` filters on the contact's mailing address; use the field the location implies — city → `MailingCity`, state/region → `MailingState`. Insert `<CONTACT_CUSTOM>` and `<ACCOUNT_CUSTOM>` from Step 2. Pull a generous pool (`first: 200`) so Step 4 has room to rank down to the target count.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { <LOCATION_FILTER> }, first: 200) { edges { node { Id Name { value } Title { value } Email { value } Phone { value } MailingCity { value } MailingState { value } LastActivityDate { value } <CONTACT_CUSTOM> Account { Id Name { value } Industry { value displayValue } NumberOfEmployees { value } AnnualRevenue { value displayValue } Type { value } <ACCOUNT_CUSTOM> Owner { Name { value } } } } } } } } }\"}" })
```

`<LOCATION_FILTER>` — build from the Step 1 location:
- City: `MailingCity: { like: \\\"%<CITY>%\\\" }`
- State / region: `MailingState: { like: \\\"%<STATE>%\\\" }`
- Multiple cities in a metro: `or: [{ MailingCity: { like: \\\"%<CITY_A>%\\\" } }, { MailingCity: { like: \\\"%<CITY_B>%\\\" } }]`

Empty `edges` → say "No contacts found near [location]"; broaden the location once (city → surrounding state) only if the user's intent clearly allows it, else ask. Never widen to the whole org unasked. `first: 200` caps the pool — if the location is very broad, say so and ask the user to narrow it rather than silently truncating.

### 3b. Read open opportunities for those accounts

**Skip this step if 3a returned no contacts.** Collect unique Account IDs from 3a, then query their open opportunities. If there are many accounts (50+), batch the query into groups of 50 using `or: [{ AccountId: { eq: \"<ID1>\" } }, ...]`.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Opportunity(where: { and: [{ IsClosed: { eq: false } }, { or: [<ACCOUNT_ID_FILTERS>] }] }, orderBy: { CloseDate: { order: ASC } }, first: 200) { edges { node { Id Name { value } AccountId { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } } } }\"}" })
```

`<ACCOUNT_ID_FILTERS>` is a comma-separated list: `{ AccountId: { eq: \"<ID1>\" } }, { AccountId: { eq: \"<ID2>\" } }, ...` for all unique Account IDs from 3a.

After both queries return, **enrich each contact** with its account's open opportunities (match by `AccountId`). A contact whose account has no open opportunities gets `opportunities: []`. The invite table shows ONE opportunity per contact, so pick the single most relevant open one: the largest `Amount`, ties broken by the nearest `CloseDate` (or the one the ICP names, e.g. a renewal closing this quarter). Never list several.

## 4. Score ICP fit and rank

Score each contact 0–10 against the ICP from Step 1, then rank and take the top N (default 10). Weight only the dimensions the user named; if they gave a loose ICP, use the default weighting below. Score from queried values only — a blank field scores 0 for that dimension, never a guess.

| Signal | Weight | Scoring |
|---|---|---|
| Title / role / job level match | 3 | target persona=3, adjacent=1, off=0 |
| Account segment / industry match | 2 | in ICP=2, adjacent=1, off=0 |
| Account size / revenue in range | 2 | in range=2, ±50%=1, outside=0 |
| Open opportunity on the account | 2 | open opp=2, none=0 |
| Recent activity (`LastActivityDate`) | 1 | <90d=1, else 0 |

Rank by total score descending; break ties by open-opportunity amount, then recency. Take the top N. Note anyone excluded only for a missing field (e.g. no Title) so the user can fix it in Salesforce.

**Record links (built here, used in Step 5/6).** For every contact, account, and open opportunity that lands on the list, build its Lightning URL from the Id and `instanceUrl` — `https://[instanceUrl]/lightning/r/Contact/[Id]/view`, `.../Account/[Id]/view`, `.../Opportunity/[Id]/view`. These become the `href` on the Name, Account, and Open-opportunity cells. A contact with no open opportunity gets a plain-text "No open opp" cell (no link).

## 5. Render — widget first

Call `display_widget` immediately after assembling the ranked list. Do not write markdown first — only fall back to the Step 6 markdown when the tool is unavailable.

When the data is assembled, call:

```
display_widget({
  resourceType: "salesforce_widget",
  widget_resource_uri: "ui://widget/standard/event-invite-list",
  props: {
    title: "...",
    answer: "...",
    inviteList: [...],
    callout: {...},
    sources: [...]
  }
})
```

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`).

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write every free-text field (`title`, `answer`, `whyInvite`, ...) in that language. Never join translated text with English fragments: each phrase is written whole, because word order differs.
- **Send data only; never author presentation** (colours, pills, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.

### The response is lego blocks, in this fixed order

1. **`title`** (required) — one bold sentence that already answers the question: the count, event context, and the ICP criteria. Never the skill name.
2. **`answer`** (required) — 2–4 short `- ` markdown bullets, **bold** on key facts (counts, location, ICP highlights), answering ONLY what the user asked.
3. **`inviteList`** (optional) — the invite list card with ranked contacts in a table.
4. **Tail** (optional, at most one): `callout` = time-sensitive and actionable, ONE primary button; `nextStep` = plain suggestion line, no button. Never both.
5. **`sources`** (required) — records actually read that have a record or list URL (leave out any source without one), collapsed as "Sources (N)".

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

| The prompt is… | Send |
|---|---|
| Event invite list request ("who should I invite to [event]", "give me a list for [event]", "build an invite list") | `title` + `answer` (the summary) + `inviteList` (the ranked contacts) + tail (`callout` or `nextStep`) if it applies + `sources` |
| Direct question with a direct answer ("how many contacts in SF match this ICP?") | `title` + `answer` + `sources`; omit `inviteList` unless the list itself is what makes the answer clear |

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a string.
- [ ] `props` contains exactly the fields matching `renderer.props.schema.json` below — `title`, `answer` (required); `labels`, `inviteList`, `callout`, `nextStep` (optional); `sources` (required).
- [ ] `emailLink` shows at most 12 characters of the address then `…`, with the full address as the link title; `opportunityLink` is one opportunity, name only, on one line.
- [ ] `inviteList` (when included) is an array of contact objects ranked by ICP fit descending (highest priority first); each contact has markdown-formatted link fields: `contactNameLink`, `emailLink`, `accountLink`, `opportunityLink`, plus `contactTitle` and `whyInvite`.
- [ ] All links are markdown-formatted: `[Display Text](url)`. Lightning URLs built from `instanceUrl`: `https://[instanceUrl]/lightning/r/Contact/[Id]/view`.
- [ ] `callout` or `nextStep` (at most one): the highest-priority recommendation with a button or plain suggestion.
- [ ] `sources` lists the Salesforce records/queries actually read (Campaign, Contacts, Accounts, Opportunities).
- [ ] No fabricated content — blank fields left blank (no link), not invented.
- [ ] `widget_resource_uri` is exactly `"ui://widget/standard/event-invite-list"`.

### `props` schema (JSON Schema)

Send data only — the widget's HXL template (in `renderer.json`, compiled client-side) renders it. Every value you send must be a ready-to-display string (currency formatted, dates formatted, amounts formatted); names are plain strings. Links are markdown-formatted: `[text](url)`.

{
  "type": "object",
  "additionalProperties": false,
  "description": "Block order: title, answer, then the optional inviteList card, then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A'. Format every value as a ready-to-display string (currency, dates, amounts); names are plain strings, never objects.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold sentence that already answers the question: the count, event context, and the ICP criteria (e.g. 'Here are 14 strong fits to invite to the Dec 3 Executive Dinner – each tied to an open opportunity or renewal in your book.'). Never the skill name."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown with **bold** on the key facts (counts, location, ICP highlights): 2-4 short '- ' bullets, each ONE sentence. Answer ONLY what the user asked; do not restate the table below it."
    },
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed label of the widget (table column headers, the sources toggle); each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "inviteList": {
          "type": "string",
          "default": "INVITE LIST",
          "description": "Heading of the invite list card. English: 'INVITE LIST'."
        },
        "contact": {
          "type": "string",
          "default": "CONTACT",
          "description": "Column header for contact name. English: 'CONTACT'."
        },
        "email": {
          "type": "string",
          "default": "EMAIL",
          "description": "Column header for email. English: 'EMAIL'."
        },
        "account": {
          "type": "string",
          "default": "ACCOUNT",
          "description": "Column header for account name. English: 'ACCOUNT'."
        },
        "opportunity": {
          "type": "string",
          "default": "OPPORTUNITY",
          "description": "Column header for opportunity. English: 'OPPORTUNITY'."
        },
        "whyInvite": {
          "type": "string",
          "default": "WHY INVITE",
          "description": "Column header for invite reasoning. English: 'WHY INVITE'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "inviteList": {
      "type": "array",
      "maxItems": 50,
      "description": "OPTIONAL card 'INVITE LIST'. Include for all event-invite-list queries. One row per contact to invite, ranked by ICP fit descending (highest priority first). Omit the key if no contacts matched; never an empty array.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "contactNameLink",
          "accountLink",
          "whyInvite"
        ],
        "properties": {
          "contactNameLink": {
            "type": "string",
            "description": "Contact name as markdown link (e.g. '[Priya Anand](https://<myDomain>/lightning/r/Contact/<Id>/view)'). Rendered bold and clickable."
          },
          "contactTitle": {
            "type": "string",
            "description": "Contact title / role (e.g. 'VP Finance · economic buyer'). Rendered on a second line under the name, muted."
          },
          "emailLink": {
            "type": "string",
            "description": "Contact email as a markdown link whose href is the full address, with the visible text cut to its first 12 characters followed by '…' when longer, and the full address as the link title so it shows on hover (e.g. '[priya.anand@…](mailto:priya.anand@cedarline.com \"priya.anand@cedarline.com\")'; an address of 12 characters or fewer is shown whole, with no title). Clicking opens the email client with the full address. Quote blank as '—' (plain text, no link) if absent."
          },
          "accountLink": {
            "type": "string",
            "description": "Account name as markdown link (e.g. '[Cedarline Financial](https://<myDomain>/lightning/r/Account/<Id>/view)'). Rendered clickable."
          },
          "opportunityLink": {
            "type": "string",
            "description": "The ONE most relevant open opportunity (largest amount, ties broken by nearest close date), as a markdown link with the opportunity NAME only, no amount, stage or date, so the cell stays on one line (e.g. '[Cedarline Renewal](https://<myDomain>/lightning/r/Opportunity/<Id>/view)'). Names over 24 characters are cut to 24 followed by '…' with the full name as the link title. Quote as 'No open opp' (plain text, no link) if none exists."
          },
          "whyInvite": {
            "type": "string",
            "description": "One or two sentences explaining why this contact is a strong fit (ICP match, deal context, timing, relationship strength). Answer-first, specific to this contact."
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL tail, time-sensitive. A bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if one or more contacts are high-priority AND the user can act on it now. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (who to prioritize, in one sentence, ending with a period)."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences: why these contacts are highest priority and the recommended move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Draft event invite outreach')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked (e.g. 'Draft event invitation emails for the top contacts on this invite list')."
        },
        "level": {
          "type": "string",
          "enum": [
            "tip",
            "note",
            "blocker"
          ],
          "default": "note",
          "description": "OPTIONAL. Emphasis of the callout: 'tip' (quiet), 'note' (standard, the default), 'blocker' (urgent). Include only when it is not 'note'."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button. Use INSTEAD of callout, never both.",
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead (the suggested move, e.g. 'Start with personal invites to the two executive-level contacts')."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning: why this sequencing matters or what to do next."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: the Salesforce records/queries you actually read (Campaign, Contacts, Accounts, Opportunities), linked. Shown as a compact 'Salesforce · Sources (N)' toggle (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "label",
          "url"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "Source name (e.g. 'Campaign: Q4 Executive Dinner – San Francisco', 'Contacts · senior buyers, Bay Area accounts', 'Opportunities · 11 open (this quarter)')."
          },
          "url": {
            "type": "string",
            "description": "Record or list-view URL (https://<myDomain>/lightning/r/<SObject>/<Id>/view). Required: a source with no URL is left out of `sources`, so aggregate queries are not listed."
          }
        }
      }
    }
  }
}

#### Worked examples (the `props` object only)

**Event invite list — "Who should I invite to our SF exec dinner next month?"**

```json
{
  "title": "Here are 14 strong fits to invite to the Dec 3 Executive Dinner – each tied to an open opportunity or renewal in your book.",
  "answer": "- **14 contacts** matched your criteria in the **San Francisco** metro area.\n- All hold **VP+ or economic buyer** roles at accounts with **$500M+ revenue** in Healthcare and Financial Services.\n- **10 contacts** have open opportunities or renewals closing this quarter, ranging from **$450K to $1.2M**.",
  "inviteList": [
    {
      "contactNameLink": "[Priya Anand](https://example.my.salesforce.com/lightning/r/Contact/003XX000001AbC1YAK/view)",
      "contactTitle": "VP Finance · economic buyer",
      "emailLink": "[priya.anand@…](mailto:priya.anand@cedarline.com \"priya.anand@cedarline.com\")",
      "accountLink": "[Cedarline Financial](https://example.my.salesforce.com/lightning/r/Account/001XX000002MnQ8YAK/view)",
      "opportunityLink": "[Cedarline Renewal](https://example.my.salesforce.com/lightning/r/Opportunity/006XX000003kLm2YAE/view)",
      "whyInvite": "Your top open deal; renewal closes Oct 27. A dinner seat keeps the economic buyer close as it lands."
    }
  ],
  "callout": {
    "lead": "Priya Anand is your highest-value invite – VP Finance on the $640K Cedarline renewal closing Oct 27.",
    "text": "Want me to draft an invitation email to her for the Dec 3 dinner? I can do the same for Dana Whitfield and Robert Lang next.",
    "buttonLabel": "Draft event invite outreach",
    "actionMsg": "Draft event invitation emails for the contacts on this San Francisco invite list, leading with Priya Anand (Cedarline), Dana Whitfield (Vantage Retail), and Robert Lang (Summit Health)."
  },
  "sources": [
    {
      "label": "Campaign: Q4 Executive Dinner – San Francisco",
      "url": "https://example.my.salesforce.com/lightning/r/Campaign/701XX000000AbC1YAK/view"
    },
    {
      "label": "Opportunities · 11 open (this quarter)",
      "url": "https://example.my.salesforce.com/lightning/o/Opportunity/list?filterName=Recent"
    }
  ]
}
```

**No results — "How many SF contacts match VP-level tech at 500+ employee companies?"**

```json
{
  "title": "No verified matches for San Francisco VP-level technology leaders at companies with 500+ employees.",
  "answer": "- **1 contact** was returned for **San Francisco**, but did not meet the verified criteria.\n- The contact's **Title** field is not VP-level technology, and the **Employees** field is blank on the account.",
  "nextStep": {
    "lead": "Confirm company size and contact roles in Salesforce.",
    "text": "The available record cannot establish a match for your requested audience."
  },
  "sources": [
    {
      "label": "Contacts · San Francisco, all technology roles",
      "url": "https://example.my.salesforce.com/lightning/o/Contact/list?filterName=__Recent"
    }
  ]
}
```

Note: `inviteList` is omitted (per schema: "Omit the key if no contacts matched") — the renderer shows only title, answer, nextStep, and sources. No empty table.
