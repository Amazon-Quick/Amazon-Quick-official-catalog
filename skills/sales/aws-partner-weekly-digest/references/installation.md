---
description: "Setup and support guide for partners, covering required and optional capabilities and how setup behaves when one is unavailable."
last_updated: 2026-11-16
origin: original
---

# Setup and support

For the partner setting up this skill.

## What this skill needs

**Partner Central is required. Slack and Email are optional recurring sources.** Setup shows exactly those three choices in one multi-select, establishes optional connection scope once, and saves retrieval bounds and provenance rules. Marketplace MCP remains an internal automatic source restricted to AWS Marketplace and is not a fourth choice. Every activation, scheduled, and on-demand digest scans the saved selected sources without asking again. Step 4 separately tests Slack and email outbound sends. In-application delivery is always available.

| Capability | What it adds | Setup behavior when unavailable |
|---|---|---|
| Partner Central MCP reads | Opportunities, funding, engagements, profile, recommendations, and related Partner Central records | Setup stops because no digest can be produced |
| Marketplace MCP atomic reads | Pending private offers, active listings, and contracted monthly recurring revenue | AWS Marketplace is offered only with at least one current reportable Marketplace item and complete Catalog and Agreement reads |
| Slack inbound signals | Bounded Support Cases Pending candidates | No support candidate is inferred from Slack; other sections are unaffected |
| Email inbound signals | Bounded Support Cases Pending candidates | No support candidate is inferred from email; other sections are unaffected |
| Slack outbound sends | Slack delivery | Slack is offered only when its own send test succeeds |
| Email outbound sends | Email delivery | Email is offered only when its own send test succeeds |

The six capability states remain independent. Inbound signal inspection never authorizes outbound delivery, and an outbound send never authorizes an inbound read. Communication signals never establish business status, amount, completeness, absence, or any non-support domain.

## Setting up

1. Say **"set up my digest"**.
2. Setup inspects Partner Central MCP, Marketplace MCP atomic reads, bounded Slack inbound signals, and bounded email inbound signals in that order, then shows a live preview.
3. The preview and section selector include only optional sections with at least one current reportable
   item. Every offered section starts enabled. Other optional sections are omitted from the preview and
   selector until reconfigure finds and offers qualifying data.
4. **Nothing is saved until setup finishes.** If you stop after the preview there is no new configuration,
   stored data, or scheduled task.

Setup takes about ten minutes, of which about two are the preview.

## Before you rely on scheduled delivery

Three facts about the schedule, stated here because they change what "delivered every Monday" means.

1. **The run happens on your own machine.** If the machine is off or the application is closed at the
   scheduled time, **the run does not happen.**
2. **A missed run is not made up later.** There is no retry and no notification when one is missed.
3. **The digest tells you.** The footer of the next digest you actually receive states how many scheduled
   deliveries did not occur. That line is the only place this appears, so it is worth reading after a
   holiday.

Two further points on timing and delivery:

- **The timezone is the application's, not a setting inside this skill.** Setup reads it and confirms the
  resulting local delivery time with you. **Changing the application's timezone moves your digest**, and
  the digest discloses the change in the next report.
- **Activation creates one canonical artifact and one normalized plan.** Before sending, setup unions your confirmed email, additional-recipient email legs, selected destinations, and one current-chat rendering, then removes duplicate email addresses and channel-target identities. Each unique target is attempted once, the full chat copy appears even if every external delivery fails, and your future schedule stays unchanged.

## Where your data is stored

Everything this skill remembers stays **on your own machine**, in the application's own durable storage
area for this skill. Setup tells you the resolved location, so a support conversation can establish where
it actually is.

What is stored: your configuration, the six independent capability states, one recoverable backup, a record of the last digest, your snooze windows, any active one-shot filter, an escalation audit log without message bodies, a bounded set of pipeline snapshots for week-over-week comparison, and a cache of opportunity contact-team membership.

What is **not** stored: inbound email or Slack message bodies, mailbox content, feed content, and anything unrelated to the partner's AWS partnership. A retained communication signal is limited to its origin, sender or channel, stable message identity, received instant, typed business meaning, extracted fields, extraction fidelity, retrieval scope and window, and completeness or applied bound.

This skill is **read-only** against every AWS system. It aggregates, ranks and displays. It never accepts
a referral, submits a claim, updates an opportunity or changes anything's state on your behalf. The one
outbound action it can take is an escalation message to a colleague on your roster, which it drafts,
shows you, and sends only after you confirm, unless you configured an auto-send threshold yourself.

## Changing things afterwards

You do not need to re-run setup to change what the digest contains.

| To change | Say something like |
|---|---|
| See what is adjustable | "what can I change about my digest" |
| Turn a section or one part of it off | "stop showing me the data hygiene callout" |
| Quiet something temporarily | "snooze wins for four weeks" |
| Focus one digest, right now | "only show me funding and referrals" |
| Adjust what counts as stalled | "change my stall threshold to 21 days" |
| Manage who receives it | "who receives my digest", "add finance@example.com as a recipient" |
| Look closer at one item | "show me more about the MAP claim" |
| Catch up mid-week | "what changed since last week" |

**Re-running setup** is the route for changing your persona, delivery destinations, identity, or the set of
available sections. It repeats source inspection and the live preview, replaces your configuration after
confirmation, and keeps snapshots, snooze windows, and escalation history intact. A previously unavailable
section becomes selectable only when reconfigure finds qualifying data and offers it.

**Pausing and resuming** the schedule is the application's own control rather than something this skill
manages, and it will point you there.

Setup asks about sections only. Individual parts of a section, which action streams compete for your
priority list, and the thresholds all default to sensible values and are changed by command once you have
read a digest and formed an opinion. The footer of every digest names where to do it.

## Things that look like faults and are not

| What you see | What it means |
|---|---|
| "Funding totals cover the programs this run could reach" | Partner Central MCP returned bounded coverage. Check the stated population before using the total as account-wide |
| A footer line saying an optional source was unavailable | The content could not be retrieved for that run. The optional section is omitted and the failure appears in the footer |
| "The authoritative referral list could not be retrieved" | Partner Central MCP did not establish the authoritative set. Check Partner Central directly |
| A section missing that you turned off | Suppressed content is not reported as unavailable, because you already know |
| An optional section missing after a successful read | No current reportable item existed. The digest omits the heading, empty state, and placeholder |
| A quiet-week digest | Every source that could answer did, and nothing needs you. Optional sections with no current reportable item are omitted |
