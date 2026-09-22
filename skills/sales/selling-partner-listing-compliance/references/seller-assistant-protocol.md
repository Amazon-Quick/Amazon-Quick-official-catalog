---
description: "How to use the Seller Assistant create-then-poll tools exposed by the Selling Partner connector: schemas, the verbatim-question rule, polling cadence, every status and the required action for each, the destructive classification, and observed quirks."
last_updated: 2026-09-16
origin: "Tool schemas and behavior observed via the Selling Partner connector, 2026-09-16"
---

# Seller Assistant protocol

Seller Assistant is Amazon's AI assistant for seller questions. The connector exposes it as two tools. There is no dedicated "policies" or "compliance" SP-API operation; searching the connector's tools for "program policies" returns nothing, so Seller Assistant is the live source for rule confirmation.

## Tools

**sellerAssistant_sellerAssistantCreate** — submit a question.

| Parameter | Required | Notes |
|-----------|----------|-------|
| `query` | yes | The seller's message, as stated, max 10,000 chars. Do not rephrase. |
| `entityId` | yes | The seller's MCID. |
| `conversation_id` | no | Omit for a new conversation; pass a prior response's value to continue one. |

Returns `conversation_id`, `interaction_id`, `status: PROCESSING`. It never returns the answer.

**sellerAssistant_sellerAssistantGet** — retrieve the answer.

| Parameter | Required | Notes |
|-----------|----------|-------|
| `conversation_id` | yes | From Create. Never fabricate. |
| `interaction_id` | yes | From Create. Never fabricate. |
| `entityId` | yes | The seller's MCID. |

## Classification and call path

Both tools are classified **destructive** in the current connector, including Get, which is a pure poll. `call_read_only_tool` rejects them with "Tool is destructive". Use `call_destructive_tool`. `_meta.humanReview.requiresHumanReview` is `false` for Create ("elicitation not supported"), so no separate human-review step applies beyond the seller having asked the question. Load each schema once with `get_tool_schema` and reuse it.

## Polling cadence

- Call Get immediately after Create, then every 3 to 5 seconds. Never more often than every 2 seconds.
- Simple policy questions complete in one or two polls (under 10 s). Compliance and regulatory questions take 15 to 35 seconds and three to five polls. Do not give up before 90 seconds.
- After any status other than PROCESSING, do not call Get again for that interaction_id.

## Status handling

| Status | Meaning | Required action |
|--------|---------|-----------------|
| PROCESSING | Not ready | Wait 3–5 s, poll again with the same arguments |
| COMPLETE | Answer in `response` (markdown) | Use it; present verbatim when showing the seller; keep the help-hub links |
| REQUIRES_CONFIRMATION | `confirmation` object with prompt and options | Show prompt and options to the seller, then call `seller_assistant_update` with their choice. If that tool is not discoverable, tell the seller and record the gap with `functional_feedback` |
| STOPPED | Generation cancelled | Conversation still open; seller may send a new message via Create |
| MODERATED | Response withheld | Tell the seller the content could not be provided |
| OUT_OF_SCOPE | Not a Seller Assistant topic | Tell the seller; fall back to the reference map with a caveat |
| FAILED | Error | Tell the seller; they may retry with a new Create |

## Conversation threading

Pass the same `conversation_id` for follow-ups. In practice each follow-up in a thread ("any other requirements?") returns new material rather than repeating, which is a useful way to exhaust a topic. Start a new conversation when the product or topic changes.

## Observed quirks

- **Citations vary.** A general-policies answer carried per-section links; a listing-guardrails answer had every link pointing to the same page (GXPFG3RRZB9WFPJE); the FDA/EPA/CPSC answer carried no links at all. When links are absent, say so and point the seller to Seller Central Help > Product compliance.
- **Encoding artifacts.** Em-dashes and check marks render as `?`. Render sensibly; do not otherwise alter wording.
- **`seller_assistant_update` may not surface** in the connector's tool search even though Get's description references it.
- **Feedback.** Record malformed-request failures, unhelpful answers, or missing tools with `functional_feedback`. Never record 429, 5xx, 401, or 403; those have their own observability.
