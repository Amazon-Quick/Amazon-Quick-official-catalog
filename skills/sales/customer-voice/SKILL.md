---
name: customer-voice
display_name: Customer Voice (Preview)
description: "Compile attributable customer quotes and themes from call transcripts and email threads across Salesforce-scoped accounts. Use to understand feedback on a feature, objection, competitor, or emerging issue, compare accounts, or surface recurring themes."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:8c9773b871418b18a6735541412312e6919aa752068cf0973abe35e18d6500aa"
id: "ba0b24ac-d85f-447e-ada8-a73639729931"
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
# Customer Voice

Direct customer quotes on a topic, from transcripts + email threads across your accounts — verbatim with attribution, not summaries. Salesforce only *scopes* the search: which accounts, and who's internal vs. customer. Context (all in ONE turn) → search docs/email/Slack → extract quotes → group by theme.

Inputs: **topic** (theme/objection/feature/competitor, or open-ended "what's coming up"); **scope** (my accounts default / team / named list); **period** (30d default).

- **Scope reading and output to the prompt, never a default full digest.** A topic or open-ended ask searches every source and shows themes with quotes; a lookup or count ("has anyone mentioned Freightly?", "how many accounts raised pricing?") searches only for that term, stops reading once the answer is clear, and shows just the answer — no theme grouping, and quotes only if seeing the words makes the answer faster to grasp. Don't show something just because you found it.

## 1. Context — 3 independent SF reads + the searches, all in ONE turn

Resolve the API version first (once per session; reuse it if already resolved) and substitute it for `<apiVersion>` in every REST URL below:

```
dispatch_readonly(method: "GET", url: "/services/data/")
```

The response lists the org's supported versions - pick the highest. UI-API GraphQL stays pinned at `/services/data/v65.0/graphql`.

The three reads don't depend on each other, so fire them together (with the doc/email/Slack searches below). No schema grounding — fields are fixed.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(scope: MINE, first: 200) { edges { node { Name { value } Website { value } Owner { Name { value } } } } } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { currentUser { Email { value } } } }\"}" })

dispatch_readonly(method: "GET", url: "/services/data/<apiVersion>/query",
  queryParams: { "q": "SELECT Name FROM Organization LIMIT 1" })
```

- **Accounts** = the domains/names to scope the search to (team/named-list scope: drop `scope: MINE`, filter on owner/list).
- **Internal domain** = the part after `@` in `currentUser.Email`; **org name** = `Organization.Name`. Anyone speaking from that domain/company is **internal** — everyone else is the customer.

## 2. Search sources (same turn — skip a source whose connector is absent, and note it)

- **calls**: Salesforce voice and video call transcripts (Einstein Conversation Insights) tied to the scoped accounts, see "Call transcripts" below.
- **docs**: transcripts / notes / meeting docs in the period, in account-named folders (team scope → team-shared too).
- **email**: threads in the period to/from the scoped account domains.
- **Slack**: Slack Connect / external shared channels with the scoped accounts, messages in the period.

**Sources:** Quotes come only from the call transcripts, docs, email, and Slack searches above. Salesforce otherwise only scopes this skill: make no Salesforce reads beyond the three in step 1 and the VoiceCall / VideoCall reads below, never search Tasks, Events, Cases, or other records as a substitute source, and report no counts from such a search.

Narrow each search to the period and the scoped account names/domains (e.g. title contains "transcript" or an account name) instead of paging through every result. Skip shortcuts (`application/vnd.google-apps.shortcut`) and notes where every attendee is internal, and keep only files you can tie to a scoped account by title or folder. A search snippet can be cut off — read the full file before quoting from it.

### Call transcripts

Query `VoiceCall` and `VideoCall` as two separate reads in the same turn (`VideoCall` has no `CallStartDateTime`), limited to the period:

```
dispatch_readonly(method: "GET", url: "/services/data/<apiVersion>/query",
  queryParams: { "q": "SELECT Id, CallStartDateTime, RelatedRecordId, RelatedRecord.Name FROM VoiceCall WHERE CallStartDateTime = LAST_N_DAYS:<period> ORDER BY CallStartDateTime DESC LIMIT 50" })

dispatch_readonly(method: "GET", url: "/services/data/<apiVersion>/query",
  queryParams: { "q": "SELECT Id, StartDateTime, RelatedRecordId, RelatedRecord.Name FROM VideoCall WHERE StartDateTime = LAST_N_DAYS:<period> ORDER BY StartDateTime DESC LIMIT 50" })
```

If a read errors (object not available in the org), count calls under "couldn't search" and carry on. Keep only calls tied to a scoped Account (`RelatedRecordId` starting `001`). For up to the 10 most recent, fetch the transcript:

```
dispatch(method: "POST", url: "/services/data/<apiVersion>/actions/standard/getConversationTranscript",
         body: { "inputs": [{ "recordId": "[call-id]", "transcriptType": "processed" }] })
```

Take the first array element with `isSuccess: true`: `outputValues.unformattedTextTranscript` is the transcript and `outputValues.structuredTranscript.entries` has the per-speaker turns. This action only reads; it is a POST because the action API requires it. A call whose transcript fails or is empty is skipped quietly (count it under "searched, nothing relevant"). Link quotes to the call record.

**A file that won't open is not an error.** Never fetch file content with `dispatch_readonly` (`ContentVersion` / `ContentDocument` `VersionData`): it returns binary that the server can't read and fails with a server error. Read files through the docs connector. If a file still can't be opened, skip it, count it under "searched, nothing relevant", carry on with the rest, and never show the user the error, a status code or a stack trace. If no transcript could be read from any source, say plainly that no voice or video calls or other relevant transcripts were found for these accounts in this period.

Keep track of three buckets per source: **contributed** (yielded at least one quote), **searched, nothing relevant**, and **couldn't search** (connector not installed, connection failed, or a search that isn't enabled). The answer says which sources the quotes came from and which were empty or excluded, so the user knows what isn't reflected.

## 3. Extract quotes (strict — customer-only, on-topic, verbatim)

Per transcript/thread, pull passages where the **customer** (not your domain/org) speaks on the topic: verbatim quote (1–3 sentences) · speaker name + title + account · date + source · one-line context. Paraphrase is NOT voice-of-customer. Open-ended topic → cluster by theme, return top 3–5 by frequency.

- **Speaker side**: transcript labels read `Name (Title, Company)` — a Company equal to the org name is internal. Email: sender domain vs the internal domain.
- **Date** = when the customer said it (email sent date, the transcript's `Date:` line or title prefix) — never a file's created/modified time.
- **Source** = `Gmail`, `Slack Connect`, `Salesforce call`, or `Call transcript`, with its link (thread, permalink, call record, or the doc's `viewUrl`).

## 4. Widget (default output when `display_widget` is present: AWS Quick)

When the quotes are assembled, call `display_widget`; a single one-line "Displaying the visualization now (this may take a minute)." notice may precede it.

### Self-verification (before calling display_widget)

- [ ] `props` is passed as a native JSON object — not a quoted string, not a code block pasted as text. If the value starts with `"{"`, it is wrong.
- [ ] Every quote is a **customer's** words, verbatim, with its account, source and date — no internal speakers, no paraphrase.

The layout is built into the renderer and registered by name — you send **only the widget name and its data**. Call `display_widget` once:

```
display_widget({ resourceType: "salesforce_widget", widget_resource_uri: "ui://widget/standard/customer-voice", props: <object matching the schema below> })
```

- **CRITICAL — `props` must be a nested JSON object, NOT a string.** ❌ WRONG: `props: "{\"title\":...}"`. ✅ RIGHT: `props: {"title": ...}`. If you hold a JSON string, `JSON.parse` it first.
- When `display_widget` is available the widget is the output; produce the section 5 text only as the fallback when the tool is unavailable (e.g. a terminal).

### What to send

Follow the block order and the per-block inclusion rules in the `props` schema below (the root description and each property's `description`): **title → answer → quotes card (optional) → callout OR nextStep (optional) → sources**.

Rules:
- **Language:** when the user writes in English, omit `labels`. When they write in another language, send `labels` with EVERY key translated (headings in upper case) and write `title`, `answer`, `theme` and the tail in that language. Quotes stay verbatim in the customer's own language.
- **Send data only; never author presentation** (colours, icons, HTML, emoji, layout keys, `{!…}`/`{{…}}`): the renderer owns the look and shows or hides each block from the keys you send. Keys outside the schema are rejected, and every optional key you include must be justified by the prompt.
- **Sources:** one entry per source system or list you searched, labelled `<System> · <what was searched>` (e.g. `Gmail · implementation & onboarding mentions (90 days)`, `Accounts · 6 with implementation feedback`) and **linked** with a `url` (Salesforce list view, Gmail search, Drive folder or search, Slack channel — formats in the schema). Sources are only what the answer came from: list a source **only if it contributed at least one quote**. A source you searched that returned nothing relevant, or one you couldn't search (no connector, connection failed, search not enabled), is **not** listed — the last `answer` bullet names it instead (e.g. "Gmail searched, no relevant customer threads; Slack not connected"). Exception: when nothing was found anywhere, `sources` lists what you searched, so the "none found" answer is checkable. Not one entry per quote; each quote already links its own source.
- **Tail:** a time-sensitive, actionable item (a renewal or close date at risk because of what customers said) → `callout` with ONE button; otherwise a genuinely useful move → `nextStep`, no button. Never both. A pure lookup or count question usually gets no tail.

### Scope the blocks to the prompt

The schema marks only `title`, `answer` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.**

| The prompt is… | Send |
|---|---|
| A topic ("what are customers saying about onboarding?", "pull quotes on pricing") | `title` + `answer` (the themes, with counts) + `quotes` + tail only if it applies + `sources` |
| Open-ended ("what's coming up in calls?", "what feedback are we getting?") | `title` + `answer` (top 3–5 themes) + `quotes` with a `theme` on every item + tail only if it applies + `sources` |
| A lookup or count ("has anyone mentioned Freightly?", "how many accounts raised pricing?") | `title` + `answer` + `sources`; add `quotes` only if seeing the words makes the answer faster to grasp |
| Nothing found | `title` + `answer` saying so and what you searched + `sources` (what you searched — the one case where empty searches are listed) |

#### Worked examples (the `props` object only)

**Topic — "What are customers saying about onboarding?"** (themes on top, the quotes card, a plain next step):

```json
{
  "title": "Data migration is the onboarding pain point – both accounts that raised it lost a week or more.",
  "answer": "- **2 accounts** gave onboarding feedback in the last 30 days, and sentiment is **mixed** – both found the product easy to adopt.\n- The friction is **data migration**: it cost **Northpeak Logistics** a week and **Helios Health** three weeks of compliance review.\n- Quotes came from **Slack Connect and Salesforce call transcripts**; Google Drive was searched with no relevant customer notes, and Gmail is excluded (no connector), so email feedback isn't reflected.",
  "quotes": {
    "items": [
      {
        "account": "Northpeak Logistics",
        "source": "Slack Connect",
        "speaker": "Dana Whitfield",
        "date": "Aug 14",
        "sourceUrl": "https://acme.slack.com/archives/C05NPKLOG01/p1755187200000100",
        "quote": "Admins picked up the platform fast. But the migration tooling assumes clean source data – ours wasn't, so we lost a week reconciling records by hand."
      },
      {
        "account": "Helios Health",
        "source": "Salesforce call",
        "date": "Aug 8",
        "sourceUrl": "https://acme.my.salesforce.com/lightning/r/VoiceCall/0LQHs000001VxF3OAK/view",
        "quote": "Implementation stalled on data migration – the compliance review of migrated PHI added three weeks nobody scoped. The product's fine; the migration path needs work."
      }
    ]
  },
  "nextStep": {
    "lead": "Scope data migration at kickoff.",
    "text": "Both lost a week or more to migration work nobody planned for. Want me to draft a migration-readiness checklist for upcoming kickoffs?"
  },
  "sources": [
    {
      "label": "Slack Connect · external shared channels (1)",
      "url": "https://acme.slack.com/archives/C05NPKLOG01"
    },
    {
      "label": "Salesforce · Einstein Conversation Insights transcripts",
      "url": "https://acme.my.salesforce.com/lightning/o/VoiceCall/list?filterName=Recent"
    },
    {
      "label": "Accounts · 2 with onboarding feedback",
      "url": "https://acme.my.salesforce.com/lightning/o/Account/list?filterName=MyAccounts"
    }
  ]
}
```

**Lookup — "Has anyone mentioned Freightly?"** (nothing found: no card, no tail):

```json
{
  "title": "No customer has mentioned Freightly in the last 30 days.",
  "answer": "- I searched **14 call transcripts** and **22 email threads** across your **9 accounts** — none mention Freightly.",
  "sources": [
    {
      "label": "Salesforce · Einstein Conversation Insights transcripts (14, 30 days)",
      "url": "https://acme.my.salesforce.com/lightning/o/VoiceCall/list?filterName=Recent"
    },
    {
      "label": "Gmail · Freightly mentions with your account domains (22 threads, 30 days)",
      "url": "https://mail.google.com/mail/u/0/#search/Freightly+newer_than%3A30d"
    }
  ]
}
```

`props` schema (JSON Schema). Only `title`, `answer` and `sources` are required; follow the root description and each property's `description`:

```json
{
  "type": "object",
  "description": "Block order: title, answer, then the optional quotes card, then at most one tail (callout OR nextStep), then sources. Only title, answer and sources are required. Whether to include the quotes card: see the scope table in the skill instructions. Omit a key and its block is not shown: never send empty arrays, empty strings, placeholders or 'N/A'. A pure lookup or count question usually gets no tail. Every quote is a customer's words verbatim — never paraphrased, never an internal speaker.",
  "required": [
    "title",
    "answer",
    "sources"
  ],
  "properties": {
    "title": {
      "type": "string",
      "description": "REQUIRED. One bold line: the takeaway in the user's context that already answers the question (e.g. 'Data migration is the onboarding pain point – 3 of 6 accounts lost one to three weeks to it.'). Plain text, no markdown. Never the skill name or 'Customer Voice: X'."
    },
    "answer": {
      "type": "string",
      "description": "REQUIRED. Answer-first markdown bullets, rendered under the title: 2-4 short '- ' bullets, each ONE sentence, that answer ONLY what the user asked. Lead with how many accounts and the overall sentiment (e.g. 'net positive'), then the consistent friction or praise and which accounts raised it — the themes, not a re-listing of the quotes. When any source was searched with nothing relevant, or could not be searched (connector missing, connection failed, search not enabled), the last bullet says which sources the quotes came from and names those empty or excluded sources (e.g. 'Gmail searched, no relevant customer threads; Slack not connected'), so the user knows what isn't reflected. Put **bold** inline on the key values (counts, sentiment, theme, account names), never on a whole bullet. When nothing was found, say so and what was searched."
    },
    "labels": {
      "type": "object",
      "description": "OPTIONAL. Every fixed label of the widget; each key's `default` is its English text, and a missing or blank key falls back to it. Omit when the user writes in English; for another language follow the Language rule in SKILL.md.",
      "properties": {
        "customerFeedback": {
          "type": "string",
          "default": "CUSTOMER FEEDBACK",
          "description": "Heading of the quotes card. English: 'CUSTOMER FEEDBACK'."
        },
        "accountColumn": {
          "type": "string",
          "default": "ACCOUNT",
          "description": "Header of the account column (on narrow screens it labels each stacked row). English: 'ACCOUNT'."
        },
        "quoteColumn": {
          "type": "string",
          "default": "QUOTE",
          "description": "Header of the quote column (on narrow screens it labels each stacked row). English: 'QUOTE'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Word shown on the sources toggle; the renderer appends the count, e.g. 'Sources (3)'. Send the word only, no number. English: 'Sources'."
        }
      }
    },
    "quotes": {
      "type": "object",
      "description": "OPTIONAL card 'CUSTOMER FEEDBACK'. Include when the user asked what customers say about a topic, or for an open-ended 'what's coming up' request, and you found customer quotes. Omit the key when no quote was found. Each row links to its source; put the full list of what you read in `sources`.",
      "required": [
        "items"
      ],
      "properties": {
        "items": {
          "type": "array",
          "minItems": 1,
          "description": "The quotes in display order: newest first; open-ended requests group by theme (most-mentioned first, newest first within it) and set `theme` on every item. At most 2 per account per theme.",
          "items": {
            "type": "object",
            "required": [
              "account",
              "source",
              "date",
              "quote"
            ],
            "properties": {
              "account": {
                "type": "string",
                "description": "Account Name, a plain string from the step 1 Account read."
              },
              "source": {
                "type": "string",
                "enum": [
                  "Gmail",
                  "Slack Connect",
                  "Salesforce call",
                  "Call transcript"
                ],
                "description": "Where the quote came from."
              },
              "speaker": {
                "type": "string",
                "description": "The customer's name (e.g. 'Elena Cortez'). Omit when unknown."
              },
              "date": {
                "type": "string",
                "description": "When the customer said it, as 'Mon D' (e.g. 'Aug 19'): the email's sent date or the transcript's Date line — never a file's created/modified time."
              },
              "sourceUrl": {
                "type": "string",
                "description": "Link to the email thread, Slack permalink, VoiceCall/VideoCall record, or the document's viewUrl. Omit if none."
              },
              "theme": {
                "type": "string",
                "description": "Open-ended requests only: the theme this quote belongs to (e.g. 'Pricing'). Appended to the source line."
              },
              "quote": {
                "type": "string",
                "description": "The customer's words verbatim, 1-3 sentences, without surrounding quotation marks (the widget adds them)."
              }
            }
          }
        }
      }
    },
    "callout": {
      "type": "object",
      "description": "OPTIONAL tail, time-sensitive. Warning icon, a bold first sentence followed by normal text, then ONE blue primary button. Use INSTEAD of nextStep, never both (if both are sent only the callout renders). Include only if something is time-sensitive AND the user can act on it. Requires BOTH a visible one-sentence lead and visible explanatory text (non-whitespace); if either is unavailable, omit the ENTIRE callout object (never send blank or whitespace-only lead/text).",
      "required": [
        "lead",
        "text",
        "buttonLabel",
        "actionMsg"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). The bold first sentence of the callout (the caution in one sentence, ending with a period)."
        },
        "text": {
          "type": "string",
          "description": "REQUIRED, visible (non-whitespace). One to three sentences of normal-weight text that follow the bold lead on the same line: what, why now, and the move."
        },
        "buttonLabel": {
          "type": "string",
          "description": "Label of the single primary button (e.g. 'Send re-engagement via Katie')."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when the button is clicked."
        }
      }
    },
    "nextStep": {
      "type": "object",
      "description": "OPTIONAL tail, not time-sensitive: a plain suggestion line with NO button, only when there is a genuinely useful next move. Use INSTEAD of callout, never both.",
      "required": [
        "lead",
        "text"
      ],
      "properties": {
        "lead": {
          "type": "string",
          "description": "Bold lead (the suggested move)."
        },
        "text": {
          "type": "string",
          "description": "One or two sentences of reasoning, ending with an offer to help if natural."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "REQUIRED. Where the answer came from: one entry per source system or list that contributed at least one quote, labelled '<System> · <what was searched>' — e.g. 'Gmail · implementation & onboarding mentions (90 days)', 'Salesforce · Einstein Conversation Insights transcripts', 'Slack Connect · external shared channels (2)', 'Accounts · 6 with implementation feedback' — each linked (see `url`). Never list a source that returned nothing relevant, or one you could not search (connector missing, connection failed, search not enabled): name it in the last `answer` bullet instead. Exception: when nothing was found anywhere, list what you searched so the 'none found' answer is checkable. Not one entry per quote: each quote already links its own source. Shown as a compact 'Salesforce · Sources (N)' toggle that expands to a numbered list (the word comes from labels.sources). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "required": [
          "label",
          "url"
        ],
        "properties": {
          "label": {
            "type": "string",
            "description": "'<System> · <what was searched>' (e.g. 'Gmail · implementation & onboarding mentions (90 days)', 'Accounts · 6 with implementation feedback')."
          },
          "url": {
            "type": "string",
            "description": "REQUIRED: every listed source was searched, so link to it (the search or list that produced the quotes): Salesforce list view 'https://<instanceUrl>/lightning/o/<Object>/list?filterName=<view>' (e.g. Account / MyAccounts, VoiceCall), a Gmail search 'https://mail.google.com/mail/u/0/#search/<url-encoded query>', a Google Drive folder viewUrl (or 'https://drive.google.com/drive/search?q=<query>' when the files span folders), or a Slack channel permalink."
          }
        }
      }
    }
  }
}
```

## 5. Text fallback — only when `display_widget` is unavailable or returned an error

Skip this section entirely if the widget rendered.

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

**No quotes found:** If no transcript, thread, or Slack message has an on-topic customer quote, still return this template with 0 quotes, keeping the topic and period in the header. Write `None` under Accounts represented and fill Gaps as shown. Close with at most one line offering a wider period or scope, or asking for a transcript, notes doc, email thread, or Slack thread to search; offer no other source.
