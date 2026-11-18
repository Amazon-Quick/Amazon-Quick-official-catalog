---
description: "Fallback co-sell stage model and criteria, signal-mapping confidence rules, same-customer benchmark method, people-discovery and PII rules, and the context-packaging spec for the sales-play handoff."
last_updated: 2026-11-16
origin: original
---

# Stage Gates, Benchmark, and Handoff Detail

This file holds the detailed logic referenced by `SKILL.md`.

## Contents

- Fallback co-sell stage model and criteria
- Signal-mapping confidence rules
- Same-customer benchmark method
- People-discovery and PII rules
- Context-packaging spec for the sales-play handoff

## Fallback co-sell stage model and criteria

Always prefer the current stage and next-stage criteria returned by the Partner Central connector.
Use this model only when the connector does not return criteria, and say the criteria are standard
defaults rather than deal-specific.

Stage sequence, in order:

1. Prospect: an identified customer opportunity exists with a named account and a described use
   case.
2. Qualified: budget, need, and timeline are established, and a customer decision-maker is
   identified.
3. Business Validation: the solution fit is confirmed with the customer, pricing or commercial
   terms are in discussion, and a target close or launch date is set.
4. Committed: the customer has verbally or contractually committed, and the deal has a signed or
   near-signed agreement with a firm date.
5. Launched: the workload or product is live and generating usage or revenue.

For the transition into each stage, the typical missing requirement to look for:

| Advancing to | Typical gate requirement to verify |
|---|---|
| Qualified | Decision-maker identified, budget and timeline confirmed |
| Business Validation | Solution fit confirmed, target date set, commercials opened |
| Committed | Signed or near-signed agreement, firm launch date |
| Launched | Deployment complete, usage or revenue confirmed |

The single blocker is the most important requirement that is Missing or Unknown for the next
transition. Report exactly one blocker.

## Signal-mapping confidence rules

When attributing a chat, email, or calendar signal to this deal, assign confidence by match type:

- High: the signal names the exact opportunity title, or names a contact tied to exactly this
  deal, or is a calendar meeting whose subject names this opportunity or customer and the customer
  has only this one active deal.
- Medium: the signal names the customer and one deal term, and the customer has only one active
  deal.
- Low: the signal names only the customer, and the customer has more than one active deal.

Only High-confidence signals inform the stage gate and the proposed updates. Report Medium and Low
as "possible, needs confirmation" and ask the user before acting on them. Do not use fuzzy or
partial-string customer matching to create a mapping, because it produces false matches and
fabricated context.

## Same-customer benchmark method

Goal: tell the rep whether this deal is on-track or slow compared to the partner's own history with
this specific customer.

1. Ask the connector for the partner's prior opportunities with the same customer that reached the
   Launched stage. Capture, per deal, the creation date and the launch date.
2. With run_python, compute days from creation to launch for each prior deal, and this deal's days
   since creation.
3. Report according to how many prior launched deals exist with this customer:
   - Two or more: average the prior deals' create-to-launch days and compare this deal against the
     average. On-track if at or below the average, slow if above (state by how many days). Report
     the average and the count of deals it is based on.
   - Exactly one: report that single prior deal's create-to-launch days as a reference point. State
     plainly it is one prior deal, not an average, so it is a rough comparison only. Note whether
     this deal is running faster or slower than that one deal.
   - Zero: state there is no prior launched history with this customer to compare against, and give
     no number.
4. Always say the comparison is drawn only from this partner's own prior deals with this customer,
   so it reflects that relationship and is not a market benchmark. Never invent or extrapolate a
   number.

## People-discovery and PII rules

Purpose: give the rep the right people to engage and a warm-introduction path.

- Customer-side contacts: from the customer's prior opportunities, list the contact people who held
  a role on those deals, with name and role. Ask the connector for contact roles rather than
  guessing.
- Internal warm-intro path: identify a seller or colleague on the partner side who worked this
  customer before. Sources, in order of strength: the owner or team on the customer's prior
  opportunities in Partner Central, then internal colleagues who appear in chat or email threads
  about this customer. Recommend the rep ask that colleague for an introduction to the relevant
  customer-side persona.
- Only surface people who appear in the data. Never fabricate a person, a role, or a contact
  detail.
- PII: it is fine to name people and their roles in the live response so the rep can act. Do not
  copy phone numbers, home addresses, or full personal contact records, and do not write personal
  contact details into any saved file. In saved output, reference people by name and role only.

## Context-packaging spec for the sales-play handoff

Before handing off to the partner-central agent to author the play, assemble a compact brief with
these fields, so the agent has everything it needs in one message:

- Deal summary: opportunity title, customer, current stage, next stage, associated AWS services or
  products, revenue, and target date.
- Stage-gate result: the requirements checked, which are met, and the single blocker.
- Conversation signals (High confidence only): customer questions and objections, competitor
  mentions, and business programs or funding already discussed or attempted.
- Same-customer benchmark: the on-track or slow verdict and the basis, if one was computed.
- People: customer-side contacts and the internal warm-intro path.

Then ask the agent to return: discovery questions tailored to the open objections, competitive
positioning against the mentioned competitors, recommended architecture patterns for the
associated services, and concrete next steps with owners and timelines. The skill presents the
agent's play together with its own findings. It does not author the play itself.
