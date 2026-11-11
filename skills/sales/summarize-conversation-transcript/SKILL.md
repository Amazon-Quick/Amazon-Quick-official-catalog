---
name: summarize-conversation-transcript
display_name: Summarize Conversation Transcript
description: "Build a call brief from a Salesforce VoiceCall or VideoCall transcript, covering customer sentiment, decisions, next steps and related opportunities. Use to recall or summarize a recorded Salesforce call or the user's last conversation with an account, including explicit no-transcript-source requests that require an unavailable result without an invented summary. External transcripts supplied by the user: call-follow-up."
author: Salesforce
icon: assets/salesforce.svg
checksum: "sha256:e396543942b005289eed87e8f6e31e8cfaf8a55433142940e9885e5ca37efae7"
id: "093b1aa7-a20f-402e-b6ec-dac96eded814"
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
# Rules:

- Resolve to ONE account before the deep read. When the name is ambiguous, ask the user to pick — don't probe candidates or guess.

# Summarize Conversation Transcript

Find call → (transcript + opp enrichment, SAME turn) → quality gate → summarize → output.

**Explicit unavailable-source branch — Quick/Kiro adaptation (candidate-derived):** If the request
itself states that no transcript source is available in the current harness or context, treat that as
an input-availability constraint, not as evidence that the Salesforce connector is disconnected,
that no call exists, or that a particular call has no transcript. Make no connector call. Return the
following output and stop:

```
📞 Call Transcript Summary
**Transcript Source:** Unavailable in this harness. Salesforce was not searched, and no transcript request was sent.
**Customer Impression:** Unavailable without a transcript source.
**Call Summary:** Unavailable without a transcript source.
**Next Steps:** Unavailable without a transcript source.
```

Do not include call details, record links, Related Opportunities, or Suggested Actions on this
branch. Do not use “No ... detected,” which would imply a transcript was examined. A later request
that supplies external transcript text or notes routes to `call-follow-up`.

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
- Update opportunity fields based on this call? (use /update-opportunity)
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
