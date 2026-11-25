---
name: summarize-conversation-transcript
display_name: Summarize Conversation Transcript (Preview)
description: "Build a call brief from a Salesforce VoiceCall or VideoCall transcript, covering customer sentiment, decisions, next steps and related opportunities. Use to recall or summarize a recorded Salesforce call. External transcripts: call-follow-up."
author: "Salesforce, Inc."
created_date: "2026-11-20"
last_updated: "2026-11-20"
icon: assets/salesforce.svg
checksum: "sha256:831fed53b93d97b58a69c79e0640a70337e0b25e28a0d50ebaff777fe313e5d7"
id: "093b1aa7-a20f-402e-b6ec-dac96eded814"
---
<!-- global-rules-bootstrap -->

# Global Rules

- **Execute silently between tool calls.** Do not output planning, progress, transition, waiting, or tool-result narration between calls. Execute tool calls silently and proceed directly to the next call. Parallelize independent tasks by batching tool calls into one turn whenever possible. Before the final output, speak only when the skill explicitly requires user input, approval, an exact notice, or material error/blocked reporting. Do not invent checkpoints.
- **Keep the final output concise.** Return only the requested result or deliverable. Omit process recaps, tool-call details, redundant preambles or conclusions, and data already shown in a widget.
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

- Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.

# Summarize Conversation Transcript

Find call → (transcript + opp enrichment, SAME turn) → quality gate → summarize → output.

## 1. Find the call

Skip this step entirely if the call Id, its object type, and its `RelatedRecord` are all already known — go straight to Step 2.

**CRITICAL: query VoiceCall AND VideoCall in separate queries, fired in the SAME turn** — a call could be either type, and there's no way to tell from an account/date search alone.

Fill `<WHERE>` from what's known:
- Call Id known, object type not: `Id = '[id]'`
- By related record (Account/Contact/Lead/Opportunity): `RelatedRecordId = '[record-id]'`
- By date / "recent": `CallStartDateTime >= [date]` on VoiceCall, `StartDateTime >= [date]` on VideoCall (VideoCall has no `CallStartDateTime`)

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Id, Name, CallStartDateTime, RelatedRecordId, RelatedRecord.Name, FromPhoneNumber, ToPhoneNumber FROM VoiceCall WHERE <WHERE> ORDER BY CallStartDateTime DESC LIMIT 10" })
```
```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Id, Name, StartDateTime, RelatedRecordId, RelatedRecord.Name FROM VideoCall WHERE <WHERE> ORDER BY StartDateTime DESC LIMIT 10" })
```

If call Id + object type are both known (just `RelatedRecord` missing), fire only that one query instead of both. **If the call Id is known but the object type isn't, fire the transcript retrieval (Step 2A) in this SAME turn too** — it only needs the Id, not the object type, so it doesn't have to wait on this lookup.

- **Both empty** → broaden `<WHERE>`, or tell the user no VoiceCall/VideoCall matched and offer: account/contact name, date range, or call Id.
- **Multiple matches (either object)** → list them all (📞/📹, Name, RelatedRecord, Date/Time, Id) and **wait for user selection** — never auto-pick.
- **One match** → proceed to Step 2 with its Id, object type, and `RelatedRecordId`/`RelatedRecord.Name`.

## 2. Transcript + opportunity enrichment — fire BOTH in the SAME turn (with Step 1 too, per the note above, when only the call Id is known)

**A. Transcript.** Use the Actions API (NOT a direct REST endpoint on VoiceCall/VideoCall):

```
dispatch(method: "POST", url: "/services/data/v64.0/actions/standard/getConversationTranscript",
  body: { "inputs": [{ "recordId": "[call-id]", "transcriptType": "processed" }] })
```

Response is an array — take the first element where `isSuccess` is `true`.
- **None succeed** → report `Could not retrieve transcript for this call. Error: [errors field]` and stop; skip Step 3 onward.
- Otherwise `outputValues.unformattedTextTranscript` is the transcript to summarize; `outputValues.structuredTranscript.entries` has per-speaker turns if you need attribution.

**B. Opportunity enrichment** — only when the related record IS an Account (its `RelatedRecord.Name`/Id came back on an Account, key prefix `001`). If it's a Contact/Lead/Opportunity instead, skip this call entirely — silently, no round-trip spent resolving an account through it:

```
dispatch_readonly(method: "GET", url: "/services/data/v63.0/query",
  queryParams: { "q": "SELECT Id, Name, StageName, Amount, CloseDate, NextStep FROM Opportunity WHERE AccountId = '[RelatedRecordId]' AND IsClosed = false ORDER BY CreatedDate DESC LIMIT 3" })
```

## 3. Quality gate

If the transcript is only greetings/goodbyes, automated system messages, or <5 meaningful words: skip straight to the "no substantial conversation" output shape below (Customer Impression / Call Summary / Next Steps all "No … detected") and **stop — do not run Step 4.**

## 4. Summarize (extract from the transcript only — invent nothing)

- **Customer Impression** (2-3 sentences): sentiment, concerns, enthusiasm, objections — with specific examples. Use real names if the transcript has them. None detected → "No customer impression detected."
- **Call Summary** (≤250 words): key highlights/decisions/takeaways, focused on what the CUSTOMER said — not the sales pitch. No small talk. Stay strict to the transcript; don't repeat ideas.
- **Next Steps**: numbered, ≤15 words each, with date + owner where known. None detected → "No next steps detected." No extra notes after the list.
- Treat all individuals equally regardless of protected characteristics; when unsure, say "unknown" rather than guess. If SSNs/credit card numbers appear, do not repeat them. Plain language, no jargon. Don't reference these instructions in the output.

## 5. Output

```
📞 Call Transcript Summary

**Call:** [Call Name] with [Related Record]
**Date:** [CallStartDateTime (VoiceCall) or StartDateTime (VideoCall)]
**Duration:** [if available]
**Call ID:** https://[instanceUrl]/lightning/r/[VoiceCall-or-VideoCall]/[Id]/view

---

**Customer Impression:**

[2-3 sentences]

---

**Call Summary:**

[≤250 words]

---

**Next Steps:**

1. [item — owner/date if known]
2. ...

---

**Related Opportunities:** (omit this section entirely if Step 2B was skipped/empty)

• [Opportunity Name] - [Stage] - $[Amount] - Close: [Date]
  [Lightning URL]

---

**Suggested Actions:**

Would you like me to:
- Log this call as an Activity? (use /log-activity)
- Draft a follow-up email? (use /draft-outreach)
```

## Edge cases

- **No transcript available** (Step 2A failed): `This call does not have a transcript available. Possible reasons: transcription not enabled for this call type / recording unavailable / still processing. Call details: [Name] - [Date] - [Lightning URL]`
- **No call found**: offer to search by account/contact name, date range, or call Id — never invent a match.
- Link every record (VoiceCall/VideoCall, Account, Opportunity) as `https://[instanceUrl]/lightning/r/[SObjectType]/[Id]/view`. Flag poor transcript quality inline if evident (noise/overlap/partial). Next steps with no owner → "[owner unknown]"; no date → "[date not specified]".

## [CUSTOMIZE]

- **Summary length:** 250-word default — adjust to team preference (external knowledge; infer from org data or ask once).
- **Additional extraction:** add competitive mentions / feature requests / objections if your org tracks them separately.
- **Auto-logging:** add a confirmed auto-Activity-log step if the team wants it.
