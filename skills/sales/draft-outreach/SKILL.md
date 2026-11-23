---
name: draft-outreach
display_name: Draft Outreach
description: "Write, draft or help with personalized outreach emails, cold emails, follow-ups, or reaching out to a specific prospect or customer by name. Creates email drafts from Salesforce contact, account, opportunity and activity data plus prior email, documents and Slack. Use when the user specifies who to email (person name, email address, or company name). For batch inbox replies, use inbox-sweep."
author: Salesforce
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:e6d32824c98e9a4d4ea7bf273c7efc1e0a94794ca88b6cd5fe82f418054a2f07"
id: "1518588d-f489-403f-bf1b-dabd08e12526"
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
# Rules:


# Draft Outreach

Ground → (read + evidence searches, all in ONE turn) → draft → create draft.

Value prop, proof points, voice/tone, signature block, and competitors (to avoid naming unprompted) are external knowledge — infer from the org's own closed-won data and product catalog, or ask the user once. Never invent them.

- **Scope reading and output to the prompt.** A broad ask ("draft outreach to Priya Anand") gets the full draft with context; a specific follow-up ("make it shorter" / "what's her role?") answers only that. Don't show the full output when the user asked a narrow question.

## 1. Ground (hardcoded — Contact only)

Ground **only Contact** — it always exists (naming a missing custom object fails the whole call). Its fields + childRelationships reveal this org's persona/segment schema; don't assume names.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { objectInfos(apiNames: [\\\"Contact\\\"]) { fields { ApiName label relationshipName } childRelationships { childObjectApiName relationshipName } } } }\"}" })
```

Step 1 is the authority on names — use exact strings from it, never guess. From the result, note: (a) scalar `__c` fields (persona, segment, relationship-context, etc.) — take their `{ value }`; (b) each lookup field's exact `relationshipName` to span for a related record's name; (c) each child `relationshipName` beyond the two standard ones below.

## 2. Read (fill from step 1)

`%NAME%` = recipient's name and `%COMPANY%` = the company/account named in the request (swap `Name: { like: ... }` for `Email: { eq: \"%EMAIL%\" }` when given an email instead). **Reference-field rules (avoids the retry loop):**
- A scalar/`__c` field → `Field__c { value }`. `displayValue` is null for Id fields here — don't rely on it.
- To get a **related record's name**, span via the exact `relationshipName` from Step 1. Do NOT append `{ ... }` to a raw `Id`/`__c` field.
- Only span relationships Step 1 actually returned. No usable relationshipName → take the `__c { value }` (the Id) and move on — **do not retry**.

Insert `<CONTACT_CUSTOM>` = confirmed scalar `__c { value }` fields; `<REL_BLOCKS>` = one block per confirmed org-specific relationship. `Account` (parent) and `OpportunityContactRoles` (child) always work.

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Contact(where: { Name: { like: \\\"%NAME%\\\" } }, first: 1) { edges { node { Id Name { value } Title { value } Email { value } LastActivityDate { value } <CONTACT_CUSTOM> Account { Name { value } Industry { value } } <REL_BLOCKS> OpportunityContactRoles { edges { node { Role { value } IsPrimary { value } Opportunity { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsClosed { value } } } } } Tasks(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } TaskSubtype { value } } } } Events(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } Opportunities(where: { IsClosed: { eq: false } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } } } } } } } } } }\"}" })
```

Empty `edges` → broaden `%NAME%`. **Prior-contact detection reads BOTH children plus the email search** — the `Tasks` child carries logged emails, the `Events` child carries calls/meetings; take the most-recent touch across Tasks, Events, AND the 2b email threads (a prior touch logged as an Event is invisible if you look only at Tasks). `Task.TaskSubtype` labels the last touch email-vs-call for the warm/cold call. `Tasks`/`Events` are standard activity children — but if a read errors on `Events` (`FieldUndefined`/`InvalidSyntax`), re-issue it **without** the `Events` block (Tasks-only) rather than failing the whole read; don't retry byte-identical. The sibling Account root's `Opportunities` (open) surface a deal-in-flight hook even when the contact has no contact-role of their own. Given a **company only** (no person named): skip Step 1 grounding and dispatch this instead — standard fields only, no custom-field grounding needed; its `Tasks`/`Events` children fill the "Prior contact" line for company-level asks:

```
dispatch_readonly(method: "GET", url: "/services/data/v65.0/graphql",
  queryParams: { "queryInput": "{\"query\":\"query { uiapi { query { Account(where: { Name: { like: \\\"%COMPANY%\\\" } }, first: 1) { edges { node { Id Name { value } Industry { value } Owner { Name { value } } Opportunities(where: { IsClosed: { eq: false } }, first: 5) { edges { node { Name { value } StageName { value displayValue } Amount { value displayValue } CloseDate { value } IsClosed { value } } } } Tasks(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } TaskSubtype { value } } } } Events(first: 3, orderBy: { ActivityDate: { order: DESC } }) { edges { node { Subject { value } ActivityDate { value } Description { value } } } } } } } } } }\"}" })
```

## 2b. Evidence (run IN PARALLEL with step 2 — same turn, issue all at once)

**Issue step 2 and all of step 2b as tool calls in a single turn.** They key on the recipient/company name from the request, not on the SF result, so batch them together:
- **email**: prior threads with this recipient — last exchange date + topic (warm follow-up vs. cold)
- **docs**: recent notes/transcripts mentioning the account — hooks, decisions, objections
- **slack**: internal mentions of the account/contact — context worth referencing

Use whatever email/doc/Slack tools are available; skip silently if none are present (SFDC-only is fine). Cite source + date for anything you use.

## 3. Draft the email (cite every claim; invent nothing)

If step 2 AND 2b both come back empty (no SFDC record, no prior threads): run a lightweight pass — company basics + one recent signal — before drafting; never draft on invented context.

Structure (body under 120 words):
1. **Relevance line** — one sentence proving you did homework, sourced from step 2/2b. Never "I came across your company."
2. **Value bridge** — connect their situation to the value prop; use a proof point if it fits naturally.
3. **Soft ask** — one low-friction CTA. Default: "Worth a 20-min call to see if this maps to what you're working on?"
4. **Signature** — the block the user provided, or sampled from sent mail.

Tone: match the team voice (sampled from sent mail, or as directed); concise and direct — no "hope this finds you well," no paragraph intros.

Subject: 4-7 words, specific not salesy — references the hook, not the product.

## 4. Create email draft

Use email to create a draft (do not send): To = recipient email, Subject = [generated], Body = [generated]. Return the draft ID/link.

## 5. Widget output

When `display_widget` is present, produce widget output first. If unavailable or it errors, fall back to text (§6).

### HXL data contract

Build a `props` object per `renderer.props.schema.json` (embedded below) — every key's type + description. Required keys (`title`, `sources`) must be present; optional keys (`draft`) are included ONLY when data exists. Omit keys without data (their blocks are not shown). All values are display-ready — no formatting functions in the template.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "description": "Data contract for the draft-outreach HXL widget. Block order: title, email (optional), sources. Required keys: title, sources. Optional: email. Omit a key and its block is not shown. All values are display-ready — no formatting functions in the template.",
  "properties": {
    "title": {
      "type": "string",
      "description": "Takeaway sentence describing the drafted outreach (e.g., 'Here's a re-engagement email to Priya Anand...')."
    },
    "labels": {
      "type": "object",
      "additionalProperties": false,
      "description": "OPTIONAL. Every fixed label in the email draft card. Each key's `default` is its English text; a missing or blank key falls back to it. Omit when the user writes in English.",
      "properties": {
        "email": {
          "type": "string",
          "default": "EMAIL DRAFT",
          "description": "Card heading. English: 'EMAIL DRAFT'."
        },
        "draft": {
          "type": "string",
          "default": "DRAFT",
          "description": "Draft status badge. English: 'DRAFT'."
        },
        "to": {
          "type": "string",
          "default": "TO",
          "description": "Recipient field label. English: 'TO'."
        },
        "subject": {
          "type": "string",
          "default": "SUBJECT",
          "description": "Subject field label. English: 'SUBJECT'."
        },
        "send": {
          "type": "string",
          "default": "Send",
          "description": "Send button label. English: 'Send'."
        },
        "sources": {
          "type": "string",
          "default": "Sources",
          "description": "Sources accordion toggle. English: 'Sources'."
        }
      }
    },
    "email": {
      "type": "object",
      "description": "OPTIONAL. Email draft card. Include ONLY when a draft was created.",
      "required": ["toName", "subject", "body", "actionMsg"],
      "properties": {
        "toName": {
          "type": "string",
          "description": "Recipient name as plain text (e.g. 'Priya Anand')."
        },
        "toEmail": {
          "type": "string",
          "description": "Recipient email address, shown after the name. Only when known; never guess. Omit otherwise."
        },
        "subject": {
          "type": "string",
          "description": "Email subject line. Plain text."
        },
        "body": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "string"
          },
          "description": "Email body, one array item per paragraph. Each item is markdown: **bold** the key facts (amounts, dates, deliverables)."
        },
        "actionMsg": {
          "type": "string",
          "description": "First-person request sent to chat when Send is clicked (e.g. 'Send this email to Priya Anand – show it to me to confirm first.')."
        }
      }
    },
    "sources": {
      "type": "array",
      "description": "Citation sources array. Each item has label (text) and optional url (link). Every source needs its record `url`. If a source has no URL of its own, label it specifically (object and record, e.g. 'Activities: Northpeak Logistics (Aug 11\u201324)'), never vaguely ('contacts and activity history'); leave out any source you cannot name specifically. Never add a timestamp.",
      "items": {
        "type": "object",
        "properties": {
          "label": {
            "type": "string"
          },
          "url": {
            "type": "string"
          }
        },
        "required": ["label"]
      }
    }
  },
  "required": ["title", "sources"],
  "additionalProperties": false
}
```

### Scope the blocks to the prompt

The schema marks only `title` and `sources` as required. **Every other key is a choice, and the choice follows the question — not what you happened to retrieve.** Data you fetched but did not use stays out of the widget.

### What to send

Omit a key and its block is not shown.

#### Worked examples

**Full draft** — recipient known, draft created:

```json
{
  "title": "Here's a re-engagement email to Priya Anand — leads with Robert's introduction and a phased-pricing path, not a discount.",
  "email": {
    "toName": "Priya Anand",
    "toEmail": "priya.anand@cedarlinefinancial.com",
    "subject": "Flexible pricing paths for the Sales Cloud rollout",
    "body": ["Hi Priya,", "Robert Nkemelu suggested I reach out directly as you've taken over sponsorship of the Sales Cloud initiative. Congratulations on the expanded role. I understand the enterprise package pricing raised concerns — fair, and worth addressing head-on.", "I've put together a couple of options that align with the ROI math behind the rollout and two alternative packaging paths, including a phased structure that shifts spend to align with your realized value. Worth 20 minutes this week to walk the numbers and confirm this still fits your budget priorities? I'll bring the options; you pick the shape.", "Best,\nBryan Corcoran\nSalesforce"],
    "actionMsg": "Send this email to Priya Anand – show it to me to confirm first."
  },
  "sources": [
    { "label": "Priya Anand (Contact)", "url": "https://cedarline.lightning.force.com/lightning/r/Contact/003xx000004SomfAAC/view" },
    { "label": "Cedarline Financial (Account)", "url": "https://cedarline.lightning.force.com/lightning/r/Account/001xx000003DKFYAA4/view" },
    { "label": "Sales Cloud rollout (Opportunity)", "url": "https://cedarline.lightning.force.com/lightning/r/Opportunity/006xx000008tRCLAA2/view" },
    { "label": "Prior email thread (Task)" }
  ]
}
```

**Guidance only** — no draft created (research/strategy answer without an email):

```json
{
  "title": "Approach for re-engaging Darrel Schneider at Pacific Fleet: New CFO, recent industry signal about fleet modernization spend; prior buyer still in seat. Next move: Cold call or LinkedIn InMail — prior thread is stale, email may not land.",
  "sources": [
    { "label": "Darrel Schneider (Contact)", "url": "https://pacific.lightning.force.com/lightning/r/Contact/003xx000004SomfAAC/view" },
    { "label": "Pacific Fleet (Account)", "url": "https://pacific.lightning.force.com/lightning/r/Account/001xx000003DKFYAA4/view" }
  ]
}
```

`props` schema (JSON Schema) is embedded in the HXL data contract section above.

### Rendering

Once data is assembled, call:
```
display_widget({
  resourceType: "salesforce_widget",
  widget_resource_uri: "ui://widget/standard/draft-outreach",
  props: <your data object>
})
```

A single one-line "Displaying now." notice may precede the call. After success, stop — no assistant text completion.

## 6. Text — FALLBACK ONLY — DO NOT USE IF `display_widget` SUCCEEDED

```
# Outreach Draft → [Recipient Name], [Title] @ [Company]

**Context used:**
- CRM: [summary of SFDC findings or "net new"]
- Prior contact: [last thread date + topic, or "none - cold"]
- Hook: [the relevance angle used]

---
**Subject:** [subject line]

[email body]
---

✉️ Created as email draft: [link/ID]
Review, edit, and send from your drafts folder.

**Suggested SFDC logging** (via `log-activity`, or manually on a read-only connector)**:**
- Log Activity on [Account/Contact]: "Outbound email - [subject]"
```
