---
description: "Risk detection thresholds, scoring rubric, and signal-mapping rules for the pipeline health briefing."
last_updated: 2026-11-16
origin: original
---

# Scoring Rubric and Signal-Mapping Rules

This file holds the detailed logic referenced by the Generate Pipeline Health Briefing workflow in
`SKILL.md`. "Email" means the connected email and calendar connector; "chat" means the connected team
chat connector.

## Risk Detection Thresholds

- Stall: no stage change in more than 14 days.
- Funding expiration: associated funding expires within 14 days.
- Engagement cold: zero engagement signals across email and chat within the time window.
- Stage regression: the deal moved backward to an earlier stage.
- Blocked: review status is "Action Required" or "Pending Submission".
- Overdue: the current date is past the target close date.
- Effectively dead: an open deal that is long overdue (for example more than 60 days past target close)
  with no engagement in the window. These are cleanup candidates the seller should close. The open-pipeline
  pull is filtered to open deals only, so already-Rejected, Closed, or Launched records are out of scope.
- Launching soon: target close date is within the next 14 days. Treat target close date as the launch
  milestone. If a distinct target launch date field is present and populated, prefer it; otherwise fall
  back to target close date.
- Unactioned customer response: the most recent inbound customer touch is dated after the opportunity's
  last-update date. An inbound customer touch is a reply from the customer in email or a message from the
  customer in a chat channel. This means the customer has responded and the opportunity has not been updated
  since, so the next move is the seller's. Only flag this when the signal maps to the deal at High
  confidence, and use the inbound message timestamp, not an outbound message the seller sent. For a chat
  message, confirm the sender is the customer before counting it (see Chat Customer-Sender Verification).
- Untouched: an open opportunity with no engagement signal in email or chat and no stage change in more than
  30 days. Compute this over a fixed 30-day lookback, independent of the requested time window, so the count
  is stable across runs. Open excludes Closed Won, Closed Lost, Launched, and Rejected opportunities.

## Headline Counts

Always compute and report these three counts in the briefing, regardless of the requested time window:

- Untouched deals: open opportunities meeting the Untouched threshold above. Report the count and total
  revenue, and list them so the leader can decide alive-or-dead.
- Launching soon and needs input: open opportunities that are Launching soon AND also Blocked (review status
  "Action Required" or "Pending Submission"). Report the count first, then each deal with its target close
  date, what input is needed, and the recommended action. Also report the broader count of all deals launching
  within 14 days, whether or not they need input.
- Awaiting your response: open opportunities meeting the Unactioned customer response detector. Report the
  count, then list each deal with the inbound response date, the source (email or chat), a one-line summary of
  what the customer said, and the recommended reply or opportunity update. This is the seller's ball-in-court
  list and is usually the most time-sensitive.

## Scoring Model

Rank active deals by a combination of:

- Stage advancement (later stage scores higher).
- Revenue impact (larger annual value scores higher).
- Engagement recency (recent, deal-specific signal scores higher).
- Signal strength (a confirmed, mapped signal scores higher than an inferred one).

Sort the prioritized list by revenue impact and close-probability, boosted by fresh, high-confidence
engagement signals. Do not let a low-confidence signal raise a deal's rank.

## Risk Tiers

Use plain-text tier labels in all output.

- Critical: blocked (Action Required), significantly overdue (more than 60 days), launching soon while also
  needing input, or an unactioned customer response on a deal that is also launching soon.
- Warning: stalled (more than 14 days without movement), pending submission, engagement cold, launching soon,
  an unactioned customer response, or approaching the target close date.
- Watch: distant close date with no recent activity, or a low-value prospect with no urgency.
- Cleanup: open deals that are effectively dead, test, or duplicate and should be closed or merged.

Precedence when a deal matches more than one category: a hard blocker (Critical) wins first, then Customer
replied awaiting you, then Stalled, then Warning, then In track. A deal with a verified customer reply newer
than its last update is always placed in Customer replied awaiting you and is never labeled Stalled, because
the required action is a reply, not re-engagement.

## Signal-Mapping Confidence Rules

When mapping a signal from email or chat to a deal, assign confidence by match type:

- High: the signal names the exact opportunity title, or names a division or unit that maps to exactly one
  deal, or names a contact tied to exactly one deal.
- Medium: the signal names the customer and one deal term, and the customer has only one active deal.
- Low: the signal names only the customer, and the customer has more than one active deal.

Only High-confidence mappings become recommended actions. Report Medium and Low as "possible, needs
confirmation" and ask the user to confirm before acting. Do not use fuzzy or partial-string customer matching
to create a mapping, because it produces false matches and fabricated recommendations. If a signal cannot be
mapped, list it as unmapped rather than forcing it onto a deal.

## Chat Customer-Sender Verification

Before a chat message can count as an inbound customer response, confirm the sender is actually the customer.
Resolve the author with the chat connector's user-profile lookup, then apply, in order of strength:

- Confirmed by email: the sender's chat profile email matches a customer contact email on the deal, or matches
  the customer's email domain. This is the strongest check and is preferred.
- Confirmed by full name: the sender's chat full name (display name or real name) matches a known customer
  contact full name for that deal. Use the full name, not a partial or first-name-only match.
- Unconfirmed: neither the email nor the full name can be matched. Do not count the message as a customer
  response. List it as "possible, needs confirmation".

Keep this conservative. When the sender is internal, a partner teammate, or cannot be resolved, the message
does not drive an Awaiting your response flag. Prefer the email match when both an email and a name are
available, because display names are easier to spoof or duplicate than a verified email.

## CRM Reconciliation Flags

For each opportunity the CRM shows as closed (won or lost) in the last 2 months, match it to a Partner Central
opportunity at High confidence, then assign one flag:

- Not submitted to AWS: no matching Partner Central opportunity exists. Cleanup or follow-up flag. A Closed Won
  CRM deal with no Partner Central submission is a likely missed co-sell submission and should be called out,
  because it can mean lost co-sell credit.
- Stale in Partner Central: the CRM shows the deal closed but the matching Partner Central opportunity is still
  open. Cleanup-needed flag; recommend updating Partner Central to Closed Won or Closed Lost to match.
- Status mismatch: the CRM and Partner Central disagree on the outcome (one won, one lost). Reconcile flag;
  recommend confirming the true outcome and correcting the wrong record.
- In sync: both closed with the same outcome. No flag, no action.

Only flag on a High-confidence CRM-to-Partner-Central match. Report lower-confidence matches as "possible,
needs confirmation". Never write to Partner Central from this reconciliation; recommend only, and require
explicit confirmation before any write.

## Already-Applied Verification

Before recommending a mapped action, confirm it is not already reflected in the deal:

- Contact update: check whether the named contact is already on the deal.
- Close-date change: check whether the target close date was already moved.
- Stage change: check whether the deal is already at or beyond the implied stage.
- Spend update: check whether the current figure already matches.
- Next-steps update: check whether the next-steps field already contains the information.

Heuristic: if the opportunity last-updated date is after the signal timestamp, fetch current deal details and
check the specific field. Classify each action as New, Already applied, or Partially applied. Recommend only
New actions.

## Stage-Readiness Assessment

For each priority deal, determine the current stage, the next stage, and that transition's requirements. Prefer
requirements returned by the Partner Central connector over hardcoded criteria. Mark which requirements are
already met, which are missing, and how any recent high-confidence signal satisfies a requirement (for example,
a scheduled discovery meeting satisfies a discovery requirement).
