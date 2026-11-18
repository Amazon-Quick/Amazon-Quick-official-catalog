---
description: "Activation, scheduled, check-in, and item-detail commands, grouped by what each command may change and what it must do as a result."
last_updated: 2026-11-16
origin: original
---

# Commands

Every activation, scheduled, and on-demand compile scans Partner Central and each saved selected Slack or Email source within its configured bounds. A check-in performs the current bounded scans needed for its fresh comparison. An item-detail command performs no broad communication scan and uses retained communication-signal metadata for a communication-derived item. Authoritative MCP reads are always attempted where applicable and always win.

Read `shared-reference.md` before this file.

## What a command may change

This is the organising distinction, because the three categories carry different risks and therefore
different obligations.

| Category | Commands | Obligation |
|---|---|---|
| **Nothing** | item detail; mid-week check-in; list recipients; list what can be changed | Read-only. No write to a system of record and no write to persisted data |
| **State** | snooze; unsnooze; reset snoozes; filter; escalate | Mutate a state item. **No backup required** |
| **Configuration** | content preference at any grain; threshold; roster add; recipient add; recipient remove | Mutate the partner's decisions. **Retain a recoverable copy before the write**, and **regenerate the scheduled run's instructions afterwards** |

The asymmetry is deliberate: configuration loss means the partner must set up again, so it is protected;
state loss degrades a comparison, so it is not. Backing up state on every snooze would spend the write
quota protecting something this skill can rebuild.

**No command writes to a system of record.** Escalation sends a message to a person; it does not update an
opportunity, accept a referral, reassign anything or submit a claim.

## The catalog

The trigger column records intent. The partner's wording is classified, never matched literally.

| Intent | Mutates | Persona | Compile follows |
|---|---|---|---|
| Item detail | nothing | all | no |
| Mid-week check-in | nothing | all | no |
| Snooze a section or a subdivision | state | all | no |
| Unsnooze, or reset all snoozes | state | all | no |
| Filter the next digest | state | all | **yes** |
| Turn a section or subdivision on or off | configuration | all | no |
| Change which action streams reach the priority actions | configuration | all | no |
| Change a partner-adjustable threshold | configuration | all | no |
| List what can be changed | nothing | all | no |
| Escalate to an owner | state | **Alliance Lead** | no |
| Add a roster entry | configuration | **Alliance Lead** | no |
| Add, remove or list recipients | configuration or nothing | all | no |

**The filter is the only one that compiles afterwards**, and that is what makes it coherent: a one-shot
filter that applies to "the next digest" would otherwise consume itself next Monday, which is not what a
partner asking to focus **right now** wants. Producing the digest immediately also makes the one-shot
semantics observable: the partner sees exactly the digest their filter produced, and it is gone.

Note what that row's mutation column means: it records what the **command** writes, which is a filter.
The compile it triggers then does what every compile does, persisting a snapshot and a run record and
clearing the filter. A command that failed before compiling has written a filter and nothing else, which
is exactly the state the next run must find.

**Snooze deliberately does not compile.** A snooze is a statement about future weeks; producing a digest
to demonstrate it would deliver an unrequested digest and consume the freshness of the next scheduled one.

## Rules binding every command

1. **Read-only surface.** No command writes to any system of record.
2. **Configuration mutations are backed up first**, retaining exactly one copy and replacing any earlier
   one.
3. **Every mutation is confirmed back concretely.** State the resulting condition: the section and its
   expiry date, the address and its label, the threshold and its basis, the roster entry as recorded.
   "Done" is not a confirmation, and after several changes in one conversation the partner needs the
   resulting **set** to know all of them landed.
4. **Structural content is out of reach at every grain.** No command disables, snoozes or filters away the
   priority action section, the executive summary or the footer, shortens the action cap, or reorders it.
5. **Compliance obligations are never suppressible**, at any grain, by any mechanism.
6. **A command suppresses a register, never an obligation.** Where a command suppresses a section or a
   subdivision, items requiring the partner's action from that content continue to reach the priority
   action section.
7. **Persona gates capability.** A command available to one persona only is refused for the others, with
   the reason stated.
8. **A command runs against current configuration**, read through the same resolved location as every
   other path. A command finding no configuration directs the partner to set up rather than improvising
   defaults.
9. **Where a state item a command needs cannot be interpreted**, reset it to empty, state that the reset
   occurred, and continue. Never abort the command because of it.
10. **Where a write fails**, state that the change was **not** applied and leave the prior configuration
    in effect.

## Classification: never do the adjacent thing

A misclassification here is not a wrong answer, it is this skill doing something the partner did not ask
for.

- **Classify into exactly one intent.** A more specific intent beats a general one, and every command
  intent outranks compile.
- **Where a target cannot be resolved, ask one clarifying question naming the candidates.** Never select
  a target on the partner's behalf when more than one candidate matches.
- **Never perform an action other than the one the classified intent specifies.**
- **Where a command cannot be satisfied, say so.** Do not perform a different command in its place.

Five substitutions to refuse. **Each would report success**, which is precisely why each is worse than a
refusal: the partner believes their instruction took effect and discovers otherwise weeks later, if at
all.

| The partner asks | The tempting adjacent action | Required behaviour |
|---|---|---|
| Snooze the priority actions | Snooze everything else instead | **Refuse**; state it cannot be suppressed |
| Snooze compliance alerts | Snooze the section carrying them | **Refuse**; state compliance cannot be suppressed |
| Stop seeing a section | Also stop that section's stream reaching the priority actions | Record the **section** preference only. The stream is a separate, confirmed request |
| Snooze an action stream | Suppress it durably instead | **Refuse**; state that changing which streams reach the priority actions is a preference rather than a window |
| Remove the primary recipient | Remove the nearest additional recipient | **Refuse**; direct to reconfigure |

## 1. Item detail

The partner names something from a digest they read, possibly on their phone, possibly three days ago.

### Resolving the reference

1. **Resolve against the items presented in the most recent digest.**
2. Where it matches exactly one item, proceed.
3. **Where it matches more than one, ask which is meant, naming each candidate.** Never select on the
   partner's behalf. A guess is unacceptable even for a read-only command, because the partner will act on
   what they are shown believing it is the item they asked about.
4. Where it matches nothing in the most recent digest, state that the item was not found and **name the
   item kinds detail can be retrieved for**.
5. Where no digest has been produced yet, resolve against a fresh retrieval rather than reporting that no
   items exist.
6. **Restrict resolvable items to the configured persona's scope.**

### Presenting the detail

1. **Retrieve the full available detail at the time the command is issued.**
2. **Present every attribute the retrieval returned.** This is the opposite of the report's discipline,
   deliberately: the report is capped and curated because it must be readable in sixty seconds, and this
   command exists because that curation necessarily drops things and the partner has now asked for what
   was dropped. Re-curating here would defeat the command.
3. **State, for each attribute, whether its value was read directly from an allowed MCP or derived by this
   skill.**
4. Present a link into the system of record where one is available. **Where none is, say so and never
   present a constructed one.**
5. Where the retrieved detail differs from what the most recent digest reported, **present the current
   value and state that it has changed since the digest.**
6. Where retrieval fails, state that detail could not be retrieved, state the cause, **and present what
   the most recent digest recorded for that item.**
7. **Write nothing.** Not to a system of record, not to configuration, not to state.

What this command does **not** do is invent structure. It presents what the source returned, with
provenance and a link. It does not compose a mini-report, does not rank and does not add a section.

### Fidelity differs by item kind, and that is disclosed

| Item kind | Allowed detail basis | Fidelity |
|---|---|---|
| Opportunity | Partner Central MCP per-opportunity detail | authoritative structured record |
| Funding application | Partner Central MCP fund-request history at the available scope | authoritative structured record |
| Funding allocation | Partner Central MCP funding detail, including per-credit-code expiry where returned | authoritative structured record |
| Referral or invitation | Partner Central MCP invitation detail | authoritative structured record |
| Marketplace private offer, listing, or agreement | Marketplace MCP Catalog and Agreement reads; unavailable when the atomic dataset contract is unmet | authoritative Marketplace record |
| Communication-derived item | signal metadata retained from the most recent digest's bounded scan of a saved Slack or Email scope | non-authoritative communication signal only |

Communication-derived item detail is limited to the signal metadata retained from the most recent digest. Present business type, origin, sender or channel, message identity, received instant, extracted fields, extraction fidelity, retrieval scope and window, and completeness or applied bound. State that the signal is non-authoritative and does not establish unstated status, amount, deadline, owner, completeness, or absence. Do not perform a fresh inbound read from an item-detail command and do not present the full message body.

### Program requirement lookup

Where the resolved item concerns an AWS program and the partner asks what that program requires, consult
the documentation search capability. **Attribute the guidance to its source** and **present it separately
from the item's own retrieved attributes**. Where the search returns nothing for the topic, state that no
guidance was found and **supply none from any other basis**.

**Never use the documentation search as a source of recent announcements.** It does not answer "what
launched recently"; it is a reference lookup.

### What this command does not do

**No drafted outreach.** Drafting and sending a message is escalation, with its own confirmation and audit
obligations. Folding a send into a read-only command would put a message-sending action behind an
utterance the partner issued expecting to read something.

## 2. Mid-week check-in

### The comparison

1. **Compare the current state of the partner's items against the snapshot persisted by the most recent
   digest.**
2. Report as changes: **priority actions that are new** since that snapshot; **items whose state
   advanced**; and **wins that occurred**.
3. **State the instant of the snapshot the comparison was made against.**
4. **Apply the configured persona's scope filter.**
5. **Bound the retrieval and disclose any bound applied.**
6. Where the fresh retrieval partially fails, report the changes that could be determined and **disclose
   which sources were not reached**.
7. Where nothing has changed, **state that nothing has changed.**

### When no snapshot exists

This is the case a partner hits most often, in the week they set up. **Disclose and offer; do not
fabricate and do not refuse.**

| | Behaviour |
|---|---|
| **Disclose** | that no baseline is available, **and why**: either no digest has been produced yet, or the snapshot was reset |
| **Never** | present anything as a change, or construct a baseline from a fresh fetch and call it last week |
| **Offer** | the current state of the partner's items instead of a comparison |

**Never derive a comparison from any basis other than a persisted snapshot.** Week-over-week change is
derived by this skill comparing against its own prior snapshot; no source provides history. A
prose-implemented skill will be tempted to improvise something plausible here, such as "here is what looks
new", and that is fabrication. With an empty baseline, a comparison written to always produce output makes
**every** item new: a partner told "you have 47 new priority actions since your last digest" on the day
they set up has learned that this skill cannot count.

### Write nothing

1. **Do not update the persisted snapshot.** The snapshot is the weekly baseline. If a Thursday check-in
   overwrote it, Monday's digest would compute week-over-week change against Thursday, and every change
   from Monday to Thursday would silently vanish from the weekly report: the partner would have been shown
   it once, mid-week, and never again in the artifact they keep. Worse, a partner who checks in daily would
   receive a weekly digest reporting almost no movement and would reasonably conclude it was broken.
2. **Do not clear an active one-shot filter.** The filter clears when **a digest** has been produced, and a
   check-in is not a digest. Clearing it here would silently consume the partner's focus request.

### Three deliberate exclusions

- **No news.** It is not partner state and has no snapshot basis, and it ranks last in every persona's
  demand mix.
- **No re-ranking.** A partner asking "anything I missed?" wants the delta. A fresh ranking is a digest,
  and asking for one is a different request.
- **No removals as a headline.** An item that disappeared between Monday and Thursday most often
  disappeared because the partner dealt with it. Reporting resolutions is legitimate and useful; reporting
  them in the same voice as new actions creates false urgency.

## 3. Snooze, unsnooze and filter

Three levers that differ in a way worth fixing precisely: **a preference is a decision, a snooze is a
window, a filter is a single shot.**

| | Preference change | Snooze | Filter |
|---|---|---|---|
| Scope | a section, a subdivision, an action stream, a threshold | a section or a subdivision | the sections and subdivisions to show |
| Duration | until changed again | a window with an expiry date | exactly the next digest |
| Cleared by | nothing; it is a decision | expiry, or an explicit unsnooze | the production of one digest |
| Mutates | **configuration** | state | state |
| Disclosed | a suppressed stream, in every footer | in the footer, with the expiry | not persisted long enough to disclose |

### Which grains each reaches

| Grain | Preference | Snooze | Filter |
|---|---|---|---|
| Section | yes | yes | yes |
| Subdivision | yes | yes | yes |
| Action stream | yes | **no** | **no** |

**Snooze and filter cannot reach a stream.** Everything a partner sees disappear under a snooze or a
filter, they can **see** disappear: a section is gone from the report, a subdivision is gone from its
section, and the footer names the snooze with its expiry. A suppressed stream is different in kind:
nothing is missing that the partner could notice, because the action list is still ten items and still
ranked. A partner who could snooze a stream for four weeks would have bought four weeks of a quieter
action list, disclosed once, and would then forget. That is a deadline passing unseen, reached through a
command intended to reduce noise.

### Snooze

1. **Record a suppression window with an expiry**, for a section or for one subdivision.
2. **Derive the expiry from the duration the partner stated.** Where they state none, **ask, and never
   apply a default duration.** A partner who says "snooze wins" without a duration has not expressed an
   indefinite suppression, they have expressed one whose length they have not thought about. Choosing four
   weeks for them creates a section that vanishes and reappears on a date nobody chose.
3. **State the resulting expiry as a calendar date**, not as the duration. "Snoozed for 4 weeks" is
   unverifiable a month later; "snoozed until 25 August" is checkable against a calendar and is the same
   string the footer will show.
4. **Compute the expiry against the partner's configured timezone.**
5. **Do not suppress the remainder of a section when snoozing one of its subdivisions.**
6. **Refuse** to snooze a structural section, stating it cannot be suppressed. **Refuse** a request whose
   target is a compliance obligation or the compliance and tier obligations subdivision, stating that
   compliance obligations cannot be suppressed. **Refuse** a request to snooze an action stream, stating
   that changing which streams reach the priority actions is a preference rather than a window.
7. Where the target names content the digest does not offer, **ask which is meant, naming the snoozeable
   options** of the section concerned. Where it names something that is both a section and one of its
   subdivisions, **ask which was meant.**
8. Allow more than one snooze at a time. Where the target is already snoozed, **replace the window and
   state the new expiry.**
9. **Do not modify content preferences when recording a snooze.**

**Two statements every snooze confirmation makes:**

- **Which content continues to appear**, including, when a subdivision was snoozed, which other parts of
  that section remain.
- **That items requiring action from that content will continue to appear among the priority actions.**

That second statement is the one with a dollar cost. A partner snoozing the funding section is asking not
to read a table of funding status every week. They are **not** asking to stop being told that $45,000
expires on Tuesday. Reading the first request as the second would mean a partner who snoozed funding in
August stopped hearing about expiring money until October, with this skill's cooperation, silently. **So:
suppression quiets the register, never the obligation.** The section or the table disappears; its actions
do not. Compliance obligations continue to appear whatever was snoozed.

### Unsnooze

1. Remove the suppression window for the named section or subdivision, and **state that it will appear in
   the next digest.**
2. Where it is not snoozed, say so.
3. **Where the content is suppressed by preference rather than by a window, state that it is turned off in
   the partner's preferences and do not change the preference.** This is the case a partner reaches most
   easily, because from their side the two look identical: the section is absent either way. Naming which
   mechanism is responsible and leaving the preference alone is the only response that does not act beyond
   the request.
4. On "clear all snoozes", remove every window and **state which sections and which subdivisions were
   restored.**
5. **Never re-enable content the partner disabled in configuration** when removing a snooze.

### Expiry

Where a window's expiry has passed, include that content in the next digest and **remove the window
rather than retaining it as expired**. Disclose each currently snoozed section and subdivision, with its
expiry, in the footer.

### The one-shot filter

1. **Record a filter naming the sections, or the subdivisions, to show.** Where it names a subdivision,
   include the containing section and restrict it to the named subdivisions. **Include every subdivision
   of a filtered-in section the partner did not narrow.**
2. **Refuse** a filter naming an action stream, stating that changing which streams reach the priority
   actions is a preference rather than a filter.
3. **Apply it to exactly one digest, and clear it once that digest is produced, whether or not delivery
   succeeded.** A report composed and awaiting approval **has been produced**; retaining the filter until
   an approval that may never come would leave it armed indefinitely.
4. **Produce a digest immediately after recording it**, and **state that the filter applies to one digest
   only.**
5. **Include structural sections regardless of the filter.**
6. Where the filter names a section the digest does not offer, ask which are meant, naming the selectable
   sections. Where it names **only** structural sections, state that those always appear and ask which
   optional sections to include.
7. **Where a filter is recorded while something is snoozed, apply both.** Neither overrides the other.
8. **Do not modify content preferences when recording a filter.**

A partner can produce an empty selection this way: filtering to Wins while Wins is snoozed yields a digest
with no optional sections at all. That digest is still valid, because structural sections appear, and the
footer discloses the snooze with its expiry, which is how the partner discovers why their filter appeared
to do nothing.

## 4. Changing a content preference

1. **A section may be enabled only if the latest setup or reconfigure offered it.** If the section is
   unavailable, do not enable it. State that reconfigure must repeat inspection and preview and can offer
   it only after finding at least one real qualifying item. For AWS Marketplace, that also requires the
   complete atomic Catalog and Agreement dataset.
2. **Record an available section or subdivision as disabled, or as enabled again**, in the partner's
   content preferences. **Record a subdivision preference without altering the preference for its
   containing section.**
3. **Refuse** a request to turn off the priority action section, the executive summary or the footer,
   stating that the content cannot be suppressed. **Refuse** a request to turn off the compliance and tier
   obligations subdivision, stating that compliance obligations cannot be suppressed.
4. **Where the partner turns off every subdivision of a section, state that the section will no longer
   appear.**
5. **State, when confirming, that items requiring the partner's action from that content continue to appear
   among the priority actions.**
6. **State the resulting set of content the digest will include.**
7. **Never record a content preference change as a snooze window**, and never record a snooze as a
   preference.

Three cases, and the boundary between them:

| The partner says | Record as | Why not the other |
|---|---|---|
| "stop showing me the hygiene callout" | **preference** | A window would restore content they asked to be rid of, on a date nobody chose |
| "hide wins for four weeks" | **window** | A preference would make a temporary request permanent, and would trigger the configuration backup for a four-week quiet period |
| "unsnooze wins" when wins is off in preferences | **neither**; state which mechanism is responsible | Silently re-enabling a preference the partner set is the adjacent action |

## 5. Suppressing an action stream

**This is the only preference in the product that narrows the ranked action list**, so most of this
section is gates in front of it. A snoozed section shows up in the next digest twice, as a section that is
gone and as a footer line naming its expiry, so a partner who did not mean it finds out on Monday and can
undo it. A suppressed stream leaves nothing missing to notice.

**Before recording it, state all three of these, then obtain explicit confirmation:**

1. **Which items will stop appearing among the priority actions.**
2. **That those items will no longer be ranked against the partner's other work.**
3. **In which section that stream's items continue to appear.**

Then:

4. **Where the partner does not confirm, leave every stream contributing.**
5. **Refuse** a request to suppress the compliance and tier stream, stating that compliance obligations
   cannot be suppressed.
6. **State, when confirming, that the suppression is disclosed in every digest's footer**, and **name the
   request that restores the stream.**
7. **Do not reduce the priority action section's item count as a consequence.** The purpose is to get the
   slots back, not to shorten the list: ten items drawn from three streams, not seven items and three
   blanks.
8. **Never record a stream suppression as a consequence of a request that named a section or a
   subdivision.**

That last rule guards the failure most likely to be implemented by accident, because the utterances are
close. **"Stop showing me opportunities needing action" is a section request. "Stop putting opportunity
actions in my priority list" is a stream request.** They are different preferences with different
disclosure obligations, and one clarifying question resolves them.

What each gate prevents:

| Gate | What it prevents |
|---|---|
| Statements 1 and 2 | A partner suppressing opportunity actions while believing they are only tidying a section |
| Statement 3 | The partner concluding the digest will no longer track those items at all |
| The explicit confirmation | The suppression being recorded from an ambiguous utterance |
| The compliance refusal | A compliance obligation being suppressed by any route |
| The footer statement | The partner forgetting, with no weekly reminder |
| Naming the restoring request | The partner knowing it is suppressed and not knowing how to undo it |
| The cap rule | The action list quietly becoming a six-item list |
| The no-consequence rule | A section-level request being over-interpreted as a stream-level one |

## 6. Changing a threshold

1. **State the threshold's current value before changing it.**
2. Record the value the partner supplied, and **state the resulting value and its basis** afterwards.
3. **Refuse** a request to change a threshold that is not partner-adjustable, **and state why it is
   fixed.**
4. On a request to restore a default, record that threshold's default and state it.
5. **Where the supplied value cannot be interpreted as a duration or an amount, ask again and record no
   substitute.**

`shared-reference.md` holds which thresholds are adjustable and each one's basis. The basis matters
because a partner acts differently on "AWS requires this" than on "the digest suggests this": only the
invitation acceptance window may be presented as an AWS requirement, and every other threshold is
presented as a digest setting or as observed AWS behaviour.

## 7. Listing what can be changed

This command exists because setup asks one content question. Everything else in the preference and
threshold inventory is reachable only by a partner who knows it is there, and the only channel guaranteed
to reach every partner every week is the footer, which points here.

1. **List every section, subdivision and action stream the report contract marks suppressible.**
2. **List every partner-adjustable threshold.**
3. **State each item's current value and its default value.**
4. **Identify, for each listed item currently snoozed, the date its snooze expires.**
5. **State that the priority action section, the executive summary and the footer always appear.**
6. **State that compliance obligations cannot be suppressed.**
7. **Name each item by the title, subdivision name or stream label the digest shows for it**, and never
   after a data source.
8. **Modify nothing.** A listing that normalised or repaired anything would be a configuration mutation
   performed without a backup and without the partner asking.

Three of these do more work than they appear to:

- **Current value beside default.** A partner deciding whether to change a stall threshold needs to know
  it is 14 days **and** that 14 is the default. Without the default they cannot tell a value they set
  months ago from the shipped one, and "restore the default" is not a request they can form.
- **The snooze expiry.** This is the second place a snooze surfaces, after the footer, and a partner asking
  what they can change is very often a partner trying to work out why something is missing.
- **The two negatives.** Stating what **cannot** be changed is part of what the list is for. A partner who
  suspects the action section might be disableable and finds no option for it is left uncertain; told
  plainly that it always appears, they stop looking. The same holds for compliance obligations, and
  stating it here is cheaper than refusing the request later.

## 8. Escalation, Alliance Lead only

Handing an item to the team member who owns it: draft a message, show it to the partner, send it on their
confirmation, and record that it happened.

**This is the only path by which one persona's action reaches another persona's surface, and that
constrains what escalation may return.** An Alliance Lead cannot read an individual Partner Sales digest.
Escalation is not a way for a lead to reach into a representative's data: it is a way to put an item in
front of the person who can act on it, on **their** surface, with **their** persona's scope. The lead sends
a notification; the recipient's own digest does the rest.

1. **Where the persona is not Alliance Lead, refuse and state that escalation is available to the Alliance
   Lead persona.**
2. **Never return the target's own digest, digest items or persona-scoped data to the requesting partner.**
3. **Never alter the target's configuration or state.**

### Resolving the target and the item

1. **Resolve the target against the configured team roster.** Where it matches one entry, proceed. Where it
   matches several, **ask which is meant, naming the candidates.**
2. **Where it matches no roster entry, state that and offer to add them.** Where the roster is empty, state
   that escalation requires a roster entry and offer to add one.
3. **Never derive an address or handle for a target that has no roster entry.** Deriving one from a name,
   by inferring a pattern from the organisation's other addresses, would send partner business data to an
   address nobody verified. The pattern is guessable and often right, which is what makes it dangerous.
4. **Resolve the item against the items presented in the most recent digest.** Where it matches several,
   ask which is meant. Where it matches none, state that and **do not escalate.**
5. Where the partner names no target and the item carries a known owner, **propose that owner and obtain
   confirmation.** Where the owner is unknown, ask which roster entry to notify.

**Adding to the roster is a separate command with its own backup**, not a side effect of escalation. An
escalation that quietly wrote a roster entry would be a state command mutating configuration.

### Drafting and review

Compose a draft addressed to the resolved target concerning the resolved item.

| Element | Rule |
|---|---|
| The item | named as the digest named it |
| Deadline | included **only where known** |
| Amount at risk | included **only where known**, with its currency |
| Action required | expressed as something the **recipient** does |
| Link | included where available |
| Attribution | **always** identified as originating from the requesting partner |

**Never include a deadline, amount or consequence the item does not carry.** This is the one place where a
violation leaves this skill's boundary and cannot be retracted. The report may say "no deadline stated" for
a funding application, because no deadline attribute exists. A draft that manufactures "please action by
Friday" to make the request feel urgent has invented a deadline and put it in a colleague's inbox over the
partner's name. It will be checked, and it will be wrong.

**Attribution matters because the recipient's response depends on it.** A message that reads as automated
gets triaged as automated; one that reads as personally written but was not damages the lead's credibility
when the recipient replies conversationally and gets nothing.

Then:

1. **Present the draft before any send**, together with the channel and destination it will go to.
2. **Allow the partner to amend it.**
3. Where the configured escalation channel is more than one channel, present a draft for each.

### Confirmation and sending

1. **Send only after the partner has confirmed**, except where the configured confirmation policy and the
   item's amount together permit sending without confirmation.
2. Where the policy requires confirmation for every escalation, obtain it **irrespective of the amount.**
3. Where the policy permits sending above a threshold, compare the item's amount at risk against the
   configured threshold.
4. **Where the amount is absent, obtain confirmation** rather than treating the amount as exceeding or not
   exceeding the threshold.
5. **Where the amount is in a currency other than the threshold's, obtain confirmation and convert
   neither.** A threshold comparison needs a comparable number: absent is distinct from zero, and
   conversion is forbidden everywhere, so both cases resolve to confirmation. That is the safe direction:
   the cost is one question, and the alternative is either sending an unreviewed message about an item
   whose value is unknown, or suppressing an auto-send the partner configured.
6. **Before sending without confirmation, state that the send is proceeding under the partner's configured
   auto-send policy.**
7. Where the partner does not confirm, **do not send.**

**The platform's own gate is independent of the partner's policy, and is disclosed.**

- **Where the channel requires per-send approval, state that the send requires the partner's approval
  irrespective of the configured policy.** The partner's policy governs whether **this skill** asks; the
  platform governs whether the **send** proceeds. Both are real, and conflating them produces a setting
  that appears not to work.
- **Determine whether approval is required from the recorded outcome of a send on that same channel, to an
  address of the same kind as the escalation's target.**
- **Where the channel's approval requirement has not been established, state that the send may require the
  partner's approval.** Do not promise either outcome.
- **Never state that an escalation send proceeds without approval on the basis of an outcome recorded for a
  send to the partner's own address.** Every escalation target is a colleague, so every escalation is in
  the population that outcome does not cover.
8. Where the escalation channel's connection is not verified, state that the channel is unavailable and
   offer another verified channel.
9. **Where a send fails, state that the message was not delivered, state the cause, and retain the draft.**
   Where one channel of a multi-channel escalation succeeds and another fails, state which did which.

### The audit record

**Record an entry whenever an escalation is sent, and also when one was drafted and not sent**, with the
outcome recorded as not sent. Record the entry **irrespective of whether the send succeeded**: that is what
makes the log a record of what the partner **did** rather than of what happened to succeed. A partner who
escalated three items and saw two arrive needs the third in the log to know it needs redoing.

| Field | Recorded |
|---|---|
| Target | the roster entry escalated to |
| Item | the item's identity |
| Channel | the channel or channels attempted |
| Instant | when the escalation was performed |
| Outcome | sent, not sent, or failed with cause |

**Do not record the message body.** The audit's purpose is follow-up: knowing **that** an escalation
happened, about what, to whom. The body adds bulk against a bounded quota and creates a durable local copy
of correspondence about named colleagues, which is a privacy cost with no corresponding benefit.

**Confirm to the partner what was sent, to whom, and on which channel.**

**On following up.** This skill can honestly detect the **item's** subsequent movement, because it
snapshots pipeline state, and can therefore report in a later digest that an escalated item advanced. It
**cannot** observe what the owner did, and cannot observe the owner's own digest. The audit entry plus the
item's own snapshot-detected movement is the follow-up. **Nothing claims to know the owner acted.**

### Read-only boundary

**Never write to any system of record in the course of an escalation.** Do not reassign the item, do not
update it, do not change its state, do not add a note to it.

**Never escalate to a non-roster address the partner supplies inline.** The roster is the authorised set. A
partner wanting to notify someone new adds them to the roster first, which is a confirmed configuration
change with a validated address.

## 9. Roster and recipients

Two commands, two purposes, and they are frequently confused.

| | Roster | Recipients |
|---|---|---|
| What it is | who the partner's team members are | who **receives** the digest |
| What it is for | owner attribution and escalation targeting | distribution |
| Persona | **Alliance Lead only** | all |
| Effect on delivery | **none** | the digest is sent to these addresses |

**The distinction is load-bearing.** A partner who adds a colleague to the **roster** has not subscribed
them to anything. A partner who adds a colleague as a **recipient** has sent them the partner's pipeline
values, customer names and, for an Alliance Lead, per-owner attribution of stalled deals. Conflating them
in either direction is a defect: treating a roster addition as a subscription leaks data, and treating a
recipient addition as a roster entry silently disables escalation to someone the partner believes is on
their team.

### Roster additions, Alliance Lead only

1. **Where the persona is not Alliance Lead, refuse and state that the roster applies to the Alliance Lead
   persona.**
2. Obtain the entry's **name and email address**, and the messaging handle where the messaging connection
   is verified, treating the handle as optional.
3. **Validate the email address as well-formed** before recording it, and where it is not, state that and
   do not record the entry.
4. **Read the entry back and obtain confirmation before recording it.**
5. **Where the partner supplies only a name, ask for the email address and record no entry without one.**
   A name-only entry attributes nothing and can be escalated to on no channel.
6. **Never derive an email address or messaging handle from the supplied name.**
7. Where an entry with the same address exists, **state that and create no duplicate.**
8. **State two things when confirming: that the entry enables owner attribution and escalation targeting,
   and that it does not cause the added person to receive the digest.** A partner typing "add Sara to my
   team" may well expect Sara to start receiving the digest. Saying plainly that she will not, and that
   recipients are a separate command, costs one sentence and prevents both a surprise and a data
   disclosure the partner did not intend.

**There is no roster removal command.** Removal is available by reconfiguring, where the roster is
presented for editing, and the addition confirmation says so.

### Recipient additions

1. Obtain the address, **validate it as well-formed**, and where it is not, state that and do not record
   it.
2. **Read the address back and obtain confirmation before recording it.** Validation checks form, not
   existence: it cannot check that the address exists, that it belongs to who the partner thinks, or that
   its holder wants the digest. The read-back is the only defence against a typo that is nonetheless
   well-formed, which is precisely the case validation cannot catch and the case where partner business
   data reaches a stranger.
3. Accept an optional label.
4. **Obtain the partner's attestation of consent** before recording them. The attestation is a step this
   command performs, not a field to be audited: what matters is that the partner is asked and answers
   before the address is recorded.
5. **Never send a verification message to the address**, and **state that none is sent.**
6. **State that the recipient receives the same canonical digest content as every selected destination and other recipient.**
7. **Where delivery to additional recipients has not been established as completing without the partner's
   approval, state that when adding one.** Never infer one recipient leg's unattended capability from a
   different email address or selected destination. Two sends that look alike are two capabilities.
8. Where the address is already a recipient, state that and do not add it twice. Where it case-insensitively matches the confirmed user email or a selected Mailbox target, state that the normalized delivery plan already contains that email leg and do not add it as an additional recipient.
9. Additional recipients are email legs independent of selected delivery destinations. Record the recipient after validation, confirmation, and consent attestation whether or not Mailbox is selected.

### Recipient removal

1. Remove the matching additional-recipient address and **state which address was removed**, together with the resulting list.
2. **Refuse to treat the confirmed user email or a selected Mailbox target as an additional-recipient removal.** State that the confirmed user identity and selected delivery destinations are changed only through reconfiguration. For Partner Sales, the confirmed email is also the scope filter, so recipient removal never changes it.
3. Where the address is not on the list, state that and **modify nothing.**
4. Where the partner names a recipient by **label**, resolve it to an address and **confirm the resolved
   address before removing it.** Where a label matches more than one, ask which is meant, naming the
   candidates.

### Listing recipients and destinations

List every selected delivery destination with its target label and every additional-recipient email leg with its recipient label. Identify the confirmed user email separately as the mandatory first-digest activation address. Do not imply that it receives scheduled email when no matching Mailbox destination is selected. Modify nothing.

This distinction makes the list actionable: selected destinations control recurring delivery, additional recipients are recurring email legs, and the confirmed user email always receives the one-time first digest.

### Ordering within a configuration mutation

Every command in this section, and every content-preference and threshold change above, follows this
order. **Step 3 must precede step 4**, because a copy retained after the write is a copy of the new
configuration and recovers nothing.

| # | Step |
|---|---|
| 1 | Resolve the target of the change and confirm it with the partner |
| 2 | Validate whatever must be validated; refuse outright where the content is structural or a compliance obligation |
| 3 | **Retain the recoverable copy of the current configuration** |
| 4 | Write the changed configuration to the resolved location. Where the write fails, state that the change was not applied and leave the prior configuration in effect |
| 5 | **Regenerate the scheduled run's instructions** |
| 6 | State the resulting list, set or value to the partner |

**Step 5 is the one most easily forgotten, and its failure is silent.** A partner who turned off the
hygiene callout on Wednesday, or added a colleague to the roster, would get the old behaviour on Monday
because the scheduled run is still executing the previous version.

## What this module deliberately does not do

- **Pause and resume.** The platform owns that primitive. A request to pause is directed to the platform's
  own scheduling control, **never satisfied by writing a paused flag into configuration**, and a request to
  pause is not treated as a configuration change.
- **Reconfigure.** That is an entry into setup, which owns its overwrite confirmation and backup.
- **Compile.** The digest itself.
- **Any grain of content control the report contract does not enumerate.** In particular **no per-item
  suppression**: quieting the single allocation that expires on Tuesday is the outcome this product exists
  to prevent.
- **Retrospective delivery.** No command re-sends a past digest to a channel. A missed run is disclosed in
  the next digest, never replayed.
- **Fuzzy matching anywhere.** Not on an item reference, not on a roster name, not on a recipient label.
  Ask one clarifying question instead.
- **Unsubscribe for recipients.** A recipient who no longer wants the digest asks the partner, who removes
  them. A recipient-facing opt-out would require identifying and authenticating people who never installed
  this skill.
- **Per-recipient content variation, or per-recipient scheduling.** One composed report per run, one
  schedule per configuration.
- **Group expansion.** A distribution list address may be used and the partner's own mail system resolves
  it.
- **Read receipts or engagement tracking.** No author-side observability exists, and inferring engagement
  from a channel would be both unreliable and a surprise to the partner.
