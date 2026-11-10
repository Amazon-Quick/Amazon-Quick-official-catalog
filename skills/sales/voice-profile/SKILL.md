---
name: voice-profile
display_name: Voice Profile
description: "Build a reusable voice profile from recent sent emails to capture a user's greetings, sign-offs, length, structure, tone and recurring phrases. Use during setup or when outreach drafts should sound more like the user; requires access to sent mail."
author: Salesforce
roles:
  - role/sales
icon: assets/salesforce.svg
checksum: "sha256:db6bc2679320a8262d20741aa9465003ba6c7b9cfa1d1822c077e225b9c151b9"
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


# Voice Profile

Extract your real writing patterns from sent email → a pasteable Voice & Messaging profile (draft-outreach and inbox-sweep reuse it). No Salesforce. One-time setup.

## 0. Email available? (hard gate)

No email connected / can't read sent mail → exit gracefully, exactly:

```
To build your voice profile, I need access to your email sent folder. Please connect email via /mcp and re-run this skill.
```

Do NOT attempt workarounds, ask clarifying questions, or invent a profile. Just stop.

## 1. Pull + clean

Search sent folder: last 60 messages to **external** recipients (not your own domain). Dedupe by thread (keep the opener over replies). Strip quoted/forwarded text, signature blocks (repeated trailing lines), calendar boilerplate.

## 2. Analyze the cleaned set

- **Greeting** — top 3 openers + frequency ("Hi [Name]," 60% / …)
- **Sign-off** — top 3 closers + frequency
- **Length** — median words, openers vs replies
- **Structure** — bullets vs prose, paragraph count
- **Tone** — formality (contractions? exclamations? lowercase?), directness (questions vs statements)
- **Phrases you use** — recurring non-generic 3–5 word phrases
- **What you don't do** — notable absences (no "hope this finds you well", no emoji, etc.)

**Deterministic profile evidence — Quick/Kiro adaptation:** Key the cleaned set by message and thread after deduplication. Compute first-touch and reply medians from cleaned authored-text word counts (with one message in a class, that message's count is the median). Normalize phrase candidates only for case, whitespace, punctuation, and recipient-name placeholders; do not merge semantic paraphrases. Include a phrase only when it contains 3–5 words and appears in at least two distinct included messages, and show its distinct-message count. If none qualifies, write `None established from <N> messages` under `Phrases I use`; never promote a one-message excerpt to a recurring habit. Detect and retain a repeated trailing signature value before stripping signatures from analyzed bodies, and always render `Signature block:` with that value or `None detected`.

## 3. Output — the profile + 2 anchors

```
# Voice Profile — built from <N> sent emails

## Voice & Messaging
**Greeting:** <top opener> (<N%>)
**Sign-off:** <top closer>
**Length:** ~<N> words first-touch, ~<N> replies
**Structure:** <prose / bullets / mixed>
**Tone:** <2–3 adjectives>
**Phrases I use:** "<phrase>" · "<phrase>"
**What I don't do:** <pattern> · <pattern>
**Signature block:** <detected signature>

## Anchor examples
**Opener:** > <excerpt from a real sent email>
**Reply:** > <excerpt>

Look right? If you'd like, paste this into your own Claude instructions so draft-outreach and inbox-sweep can reuse your voice.
```
