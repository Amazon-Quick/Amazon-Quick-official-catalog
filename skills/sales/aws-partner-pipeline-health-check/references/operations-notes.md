---
description: "Operating guidance for the recurring weekly briefing, including suggested cadence, prompt, delivery, and alert deduplication across runs."
last_updated: 2026-11-16
origin: original
---

# Operations Notes

This file holds operating guidance referenced by `SKILL.md`. "Email" means the connected email and calendar
connector; "chat" means the connected team chat connector.

## Recurring Weekly Briefing

The skill can run as a weekly briefing. Scheduling itself is a runtime feature of the host client, not something
this skill controls, so treat the schedule as host configuration:

- Suggested cadence: every Monday morning in the user's time zone.
- Suggested prompt: "Run my pipeline health check for the last 7 days".
- Delivery: present the briefing in the conversation, or to a configured channel if the host supports it.

Because the same signals can appear across runs, the already-applied verification in the workflow is what
prevents the skill from recommending the same action every week.

## Three-Action Selection Order

The briefing closes with exactly three actions. Choose the top three that apply this run, in this priority order:

1. Anything blocking a deal (an Action Required response, or review feedback owed).
2. Unactioned customer response (the customer replied after your last opportunity update and is waiting on you).
   Draft the reply or update the deal.
3. Time-sensitive preparation (a customer meeting within seven days).
4. Highest-revenue active-deal advancement (the next step for the largest active deal).
5. Bulk cleanup (when three or more deals need closing).
6. Cold-deal triage (an overdue deal needing an alive-or-dead decision).
7. New-deal engagement planning.
8. Pending-submission help.
9. Re-engagement outreach drafting.

Never present more than three. Never include an action that does not map to a real finding in the current run.
Offer additional help in a single closing line rather than expanding the list.

## Do

- Pull open opportunities only (exclude Closed Won, Closed Lost, Launched, Rejected), and page through every
  result so the entire open pipeline is retrieved, not just the first page.
- Search email and chat by both customer name and opportunity title.
- Map each signal to a specific opportunity ID, only at High confidence.
- Verify each signal against current deal state before recommending an action.
- Give a reason for every at-risk flag.
- Prefer stage-transition requirements returned by the connector over hardcoded criteria.
- Include a cleanup section for open deals that are effectively dead, test, or duplicate.

## Do Not

- Do not write to Partner Central without explicit user confirmation.
- Do not use fuzzy or partial-string customer matching to create a signal-to-deal mapping.
- Do not produce a generic "advance to the next stage" recommendation.
- Do not treat every stalled deal as equally urgent.
- Do not recommend an action that has already been applied.
- Do not stop at the first page of the Partner Central pull; page through all results or the pipeline is
  silently truncated.
- Do not copy full email bodies, phone numbers, addresses, or personal contact records into the saved briefing.
  Reference deals by ID or title.
- Do not present more than three closing actions.

## Common Failures

- Partner Central connector not connected: ask the user to confirm the connection, then stop.
- Empty pipeline on the first pull: confirm the open-only filter is not excluding valid deals (for example a
  stage-name mismatch), and confirm the connector returned data.
- Only one page of opportunities returned: the pull was not paginated. Follow the next-page marker and keep
  calling until all pages are retrieved.
- CRM connector not connected: skip the reconciliation module, mark CRM as not connected in Data Sources, and
  continue with the rest of the briefing.
- Email or chat not connected: state which source is missing and degrade gracefully.
- A signal maps to the wrong deal: disambiguate with the opportunity title, division keyword, or a named contact,
  and drop to "needs confirmation" if it cannot be resolved.
- Duplicate recommendations across runs: rely on the last-updated versus signal-timestamp check.

## When to Ask the User

- More than 50 active deals: offer to focus on one stage or deal type.
- No time window given and it is not the weekly-briefing context: ask for the timeframe.
- More than one partner org detected: ask which org.
- A signal is Medium or Low confidence: ask the user to confirm the mapping before acting.
- A signal appears partially applied: ask whether to skip it or verify the remaining part.
