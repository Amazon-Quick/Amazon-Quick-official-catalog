---
description: "Wording rules and per-surface rendering for the generated weekly digest, so phrasing stays the same from week to week."
last_updated: 2026-11-16
origin: original
---

# Writing standard and surface rendering

How the report is worded, and how each delivery surface draws it. Every other module defers to this
one on wording.

This report is generated prose, delivered weekly, to an external business audience, with nobody
checking it before it arrives. That creates three problems a template would not have, and every rule
below addresses one of them.

**A generated report drifts.** Nothing constrains the wording between one week and the next unless
this document does. Left alone, the same funding expiry is "expiring soon" one week, "at risk" the
next, and "$45K SDF, action needed" the week after. A partner cannot build a scanning habit against a
moving target, and the report's value is precisely that it can be scanned in sixty seconds.

**A generated report is fluent before it is useful.** Well-formed sentences come free, which is
exactly why generated business writing reads as padding: openers that announce what follows, hedges
stacked on hedges, tricolons that say one thing three ways, closing lines that restate the list above
them. Each is individually harmless. Together they make a partner read four sentences to extract one
fact, which is when they stop reading.

**A generated report can be confidently wrong in prose while its data is right.** An estimate
described as a measurement, a partial total described as complete, a missing value rendered as zero,
an inferred cause stated as fact. This failure survives every data-level check, because the numbers
themselves reconcile.

So these rules are about restraint more than style. The report's authority comes from being
verifiably accurate and scannable in sixty seconds. Every rule serves one of those two.

## 1. Voice

1. Write in a **neutral reporting voice**.
2. **Do not address the partner in the second person within the executive summary.** The action lines
   are instructions to one person and use imperative verbs; the summary reports. The two voices are
   deliberate and are not a contradiction. The reason is functional rather than stylistic: the summary
   must be pasteable into a leadership update, and "you have 39 opportunities" cannot be pasted
   anywhere, while "pipeline stands at 39 open opportunities" can.
3. **Express no enthusiasm, congratulation or encouragement.**
4. **Express urgency only through the urgency vocabulary.** Not through emphasis, capitalisation or
   punctuation.
5. **No sentence whose only function is to introduce what follows.**
6. **Do not restate a section's content as a summary of that section.**
7. **Use no phrase from the forbidden list** in section 5.
8. **No intensifying adverb qualifying a quantity.**
9. **At most one hedge on a statement.** One hedge is honest; two is noise.

## 2. Item lines

The priority action line has a fixed shape, and the order of its parts is the main lever on
scannability:

```
{urgency treatment}: {verb} {specific subject}  -  {amount}   [{source}]
{at most one supporting line}
```

Deadline first, because the partner is triaging by time. Verb next, because the line must say what to
**do**. Subject named specifically, because "review your funding" is unactionable. Amount last,
because it decides priority between items but does not help identify the item.

Rules:

1. **Begin each priority action line with its deadline treatment.**
2. **State the action the partner must take**, as a verb directing the partner.
3. **Name the specific subject** the action concerns.
4. **State the amount at stake where one exists, and never where one does not.**
5. **One action per line.** One line per item, plus at most one supporting line.
6. **Respect authority and fidelity.** Partner Central MCP is authoritative for Partner Central records. Marketplace MCP is authoritative only for Marketplace. A communication signal must label its origin and extraction fidelity, disclose its retrieval scope or bound, and direct the partner to verify current state in the relevant system of record. Structured Partner Central or Marketplace values win when the same item or field conflicts.
7. **Never describe a state in place of an action.**

Worked examples. The contrast in each pair is the intent made concrete.

| Weak | Strong | What changed |
|---|---|---|
| Funding expiring soon for GlobalTech | `EXPIRED JUL 8: Claim the GlobalTech Industries SDF allocation  -  $45,000` | Real deadline treatment, a verb, the specific allocation, the amount |
| You have a stalled opportunity | `BY FRIDAY AUG 1: Update next steps on Meridian Healthcare  -  $200,000, no update in 34 days` | Deadline, verb, named customer, amount, and the reason in the supporting position |
| 2 referrals need attention | `TOMORROW: Accept the Contoso data-platform referral  -  $180,000, expires Jul 30` | One item per line, named, with the irreversible consequence stated |
| Blocked application | `Provide the requested information on the MAP application  -  awaiting your response 8 days` | Names what the partner must supply and uses age because the source provides no deadline |
| Competency renewal is coming up | `BY AUG 1: Submit DevOps Competency renewal documentation  -  affects funding eligibility` | Deadline, verb, and the business consequence rather than a bare fact |
| Your MAP application is blocked | `Provide the requested information on the MAP application  -  awaiting your response 8 days` | Names what the partner must supply; ranks on age because no deadline exists |
| Opportunity hygiene is incomplete | `Add a dated next step to Contoso: next steps do not include a date` | A concrete action on one individually scoped opportunity, with no team comparison or rollup |
| Verification action required | `BY JUL 31: Complete business verification  -  window closes and the process must restart` | Deadline, verb, and the consequence that makes it urgent |

The last row illustrates the state-versus-action rule. "Verification action required" describes a
state. "Complete business verification" directs the partner. The difference is small in words and
large in whether the line gets acted on.

## 3. The urgency vocabulary

Closed, exhaustive and non-overlapping. Boundaries are in calendar days remaining, computed in the
partner's configured timezone on calendar-day boundaries.

| Days remaining | Class | Term the report uses |
|---|---|---|
| less than 0 | Expired | `EXPIRED {date}` |
| 0 | Due today | `TODAY` |
| 1 | Due tomorrow | `TOMORROW` |
| 2 to 6 | Due this week | `BY {weekday} {date}` |
| 7 to 30 | Approaching | `BY {date}` |
| more than 30 | Distant | `BY {date}` |
| unknown | Undated | `NO DEADLINE STATED` |

**Use these terms verbatim.** Position and style them, but never reword them. Apply the same
vocabulary in every section of every digest, however many items qualify for a class.

Why the boundaries are what they are:

- **Expired is a class, not an error state.** It sorts most urgent and carries the date it passed,
  because "expired" without a date leaves the partner unable to judge whether it is recoverable.
- **Today and tomorrow are separate classes with distinct single-word terms.** These are the two
  cases where the partner may still act and where a bare date leaves them to work out that the date
  is now. They are also the two most easily corrupted by a timezone error.
- **The this-week class names the weekday**, which is how a partner reasons about the next few days.
  A bare "this week" is ambiguous in the one situation where precision matters most: it does not
  distinguish Wednesday from Saturday, and a partner reading on Monday cannot tell whether they have
  two days or five.
- **Approaching and distant share a term but differ as a class.** The distinction drives ranking and
  inclusion, not vocabulary. A date is sufficient once a deadline is more than a week out, and a
  fourth adjective would dilute the vocabulary that matters.
- **Undated is explicit.** Omitting any deadline treatment reads as "no deadline exists" when the
  truth is "no deadline is known".

**Assign the class from days remaining alone, independently of the item's amount.** Folding amount
into the urgency label would describe a large item as more urgent than a small one with the same
deadline, which is false: they are equally urgent and unequally important. Keeping them separate is
what lets the ranking weigh them against each other.

**Never assign a class more severe than the days remaining qualify for.** A partner who finds that
last week's `TOMORROW` had no deadline behind it discounts this week's, however accurate the data.

Where an allowed MCP returns an ambiguous or conflicting date, treat the deadline as unknown. State the
consequence of inaction for every item presented with a deadline.

## 4. Quantitative honesty

1. **Present a derived value as derived**, never as a value obtained from a system of record.
2. **State, alongside any total computed over an incomplete set, that the set was incomplete.**
3. **Never present a total over a mixed-currency set as a single figure.** One subtotal per currency.
4. **Render an absent value as unavailable**, never as zero, never as an em dash, a blank, or any
   token that could be read as a value.
5. **State the freshness of data not retrieved during the current run.**
6. **Never assert a causal relationship the sources do not state.**
7. **Where the report repeats a claim its source qualifies, carry the qualification.**
8. **Never attribute a digest-derived figure to AWS.**
9. **Present the same value with the same wording at every place it appears in one report.**
10. **For Marketplace Monthly recurring revenue, state that it is contracted fixed monthly recurring
    revenue, not recognized or collected revenue.** Keep currencies separate, name contributing and
    non-qualifying ACTIVE agreement counts, and never substitute opportunity forecast MRR or imply that
    excluded agreements are represented.

### Rendering absence

One recurring decision: how a value the digest does not have is rendered. Get it wrong and the report
states a value it never obtained.

| Situation | Render | Never render |
|---|---|---|
| No amount stated on the record | `no amount stated` | `$0`, a dash, blank |
| Not yet assessed by AWS | `not yet scored` | `0/100`, a dash |
| Retrieval failed | optional section omitted, with a footer disclosure | `0`, `unknown`, an empty section |
| Deadline unknown | `no deadline stated` | a guessed date, blank |
| Conflicting source values | `date unclear` | one of the candidates |

**An em dash is banned as an absence marker precisely because it is conventional.** In a table of
dollar figures it reads as zero, or as "nothing at risk", which is the opposite of "we do not know".

## 5. Forbidden language

Each entry is here because it consumes scanning attention without adding information.

**Openers and connectives that announce rather than inform:** "It's worth noting that",
"Importantly", "As mentioned above", "In this section", "Let's take a look at", "Here's what you need
to know", "The following", "Below you'll find", "First and foremost", "That said", "At the end of the
day", "Moving forward".

**Empty intensifiers and evaluations:** "significant", "substantial", "considerable", "notable",
"critical" as a standalone adjective, "robust", "seamless", "exciting", "great news",
"unfortunately", "impressive", "strong performance", "healthy pipeline".

**Hedge stacks:** "may potentially", "could possibly", "might suggest that", "appears to indicate",
"seems to be roughly".

**False precision:** "approximately exactly", "roughly $45,231", "nearly all", "the vast majority",
"about 87%" where the figure is known precisely.

**Padding structures:** a tricolon expressing one idea three ways; a sentence restating the preceding
sentence; a closing line summarising what was just listed; "not only ... but also".

**Second-person urgency in the summary:** "you need to", "you should", "you must", "don't forget",
"make sure you".

**Fabricated authority:** describing a digest-derived figure as an AWS number; naming a criterion AWS
does not publish; asserting that a score predicts an outcome the source does not claim.

## 6. Consistency across weeks

1. **Use the urgency vocabulary terms without substitution.**
2. **Use the section titles without substitution.**
3. **Use the same term for a given concept throughout the report.**
4. **Do not vary an item line's phrasing pattern according to how many items the section contains.**

## 7. Links

1. **Link text describes the destination.**
2. **Never use a positional or generic phrase as link text.**
3. **Never present a link whose target was not obtained from a source.** An item with no link is
   valid; record the absence rather than fabricating a plausible address.

## 8. Emoji and decoration

Not used in the report body. The urgency vocabulary carries urgency; decoration competes with it and
does not survive being read aloud or rendered without styling. Where a surface's conventions expect a
leading glyph on a message, that belongs to the delivery envelope, not to the report.

## 9. Executive summary examples

**Good, a mixed week.**

> Pipeline stands at 39 open opportunities totalling $4.76M annualised, up one deal this week.
> CloudFirst Media launched at $890K and $125K of MAP funding was approved for Acme Corp, bringing
> the week's recognised wins to $1.02M. Attention is needed on $157,500 of funding allocations
> expiring within nine days, the first on July 8, and on 17 rejected opportunities worth $575K
> awaiting resubmission. The priority this week is claiming the GlobalTech SDF allocation before it
> expires on Tuesday.

Why it works: pasteable as written; every figure appears in a section above; both sides of the week
are stated; the closing sentence names one specific thing.

That example's $157,500 is written as a complete total, which is correct **only** where the funding
section claimed complete account coverage. Where the run reached only some programs, the same
sentence reads: "Attention is needed on at least $157,500 of funding allocations expiring within nine
days across the programs this run could reach, the first on July 8". One clause longer, and the
difference between a figure the partner can act on and a floor under one.

**Good, a difficult week.**

> Pipeline stands at 22 open opportunities totalling $2.1M annualised, unchanged from last week. No
> opportunities launched and no funding was approved. Three funding allocations totalling $210,000
> have already expired, the earliest on June 30, and the Meridian Healthcare opportunity has had no
> update in 41 days against a $200,000 estimate. The priority this week is confirming with AWS
> whether the expired SDF allocations can be reinstated.

Why it works: reports a bad week without editorialising; "no opportunities launched" states the
absence rather than omitting the sentence; the focus is actionable even though the news is bad.

**Good, a quiet week.**

> Pipeline stands at 31 open opportunities totalling $3.4M annualised, unchanged since July 14. Two
> opportunities advanced stage during the week. The current report found no action-bearing item in the
> available report data. Nothing requires action before the next digest.

Why it works: it states pipeline standing and the absence of action without making claims about omitted
optional sections or unavailable capabilities.

**Bad, problems only.**

> $157,500 in funding is expiring and 17 opportunities have been rejected. Meridian Healthcare has
> not been updated in 41 days. Three referrals are close to expiring. Immediate action is required
> across funding and pipeline.

What is wrong: a week with an $890K launch is described as pure crisis, so balance fails. No pipeline
position, so the figures have no denominator. No partner pastes this into a leadership update.
"Immediate action is required" is padding.

**The bad example is stale and intentionally excludes comparative win rate.** Do not use a win-rate trend, team average, or representative comparison as a critique example because those measures are outside this release. A current bad example is:

> Great news, the pipeline looks robust at around $4.8M with impressive momentum. There are a few funding items to keep an eye on, but overall things are moving in the right direction. Keep up the great work.

What is wrong: "Robust", "impressive", and "moving in the right direction" are evaluations the figures do not support. The $157,500 at risk is reduced to "a few funding items", with no amount and no deadline. The language is not pasteable into a leadership update, and $4.76M is rounded without reason.

## 10. Surface rendering

The report must reach the partner through whichever surface they chose. Four surfaces, one report.

**There is exactly one composed report, and rendering is a projection of it.** Writing it once per
surface makes the variants diverge within weeks: one grows a section, another keeps a title the
others renamed, a third loses the footer because it did not fit.

### Content is invariant

1. **The same sections, in the same order, under the same titles, on every surface receiving one
   composed report.**
2. **The same items, with the same values and the same wording, on every surface.**
3. **Never add, remove, reorder or reword content during rendering.**
4. **For the final setup digest, compose once at one occurrence instant, email that exact artifact, then show the identical full artifact in the current chat.** Preserve the canonical subject on email and subject-equivalent identification in chat, the canonical banner, Marketplace decision, values, and order. Show the chat copy even if email fails.

### Email is semantic HTML with a plain-text alternative

Every email delivery uses a `multipart/alternative` message with UTF-8 `text/plain` and `text/html` parts. The HTML part is the primary email rendering and the plain-text part is the fallback for clients that cannot render HTML. Both parts carry the same report content, values, item order, section order, links, and footer.

The HTML part uses semantic headings, paragraphs, ordered lists, links, tables with header cells, and a distinct footer. Use email-safe inline styles for spacing, typography, borders, and the banner. Do not emit Markdown notation into the HTML part. Escape every composed value before inserting it into HTML and validate each source-provided link before using it as an `href`. Never insert a full Slack or email message body, executable content, scripts, forms, tracking pixels, or remote images.

An outbound email capability is verified only when it accepts the HTML body and plain-text alternative. If the available operation cannot send HTML, treat HTML email delivery as unavailable rather than silently sending the Markdown baseline as a plain-text email. The in-chat rendering remains available and unchanged.

If a surface cannot draw something, degrade its **presentation**, never its **content**. Any change
that alters what the report says belongs in composition, where it happens once for every surface.

### Structure degrades before content

- Where a surface does not support tabular presentation, render each table row's fields in a form
  that surface supports, **preserving every field and labelling each one**. Labelling is required
  because an unlabelled sequence of values is interpretable only against a table header the reader
  can no longer see.
- Render the priority action list as a plain ordered list on every surface. **Never render its
  numbers as styled tokens.**
- **Emit each surface's own notation** for emphasis, links and lists. These surfaces are not four
  dialects of one notation. Never emit markdown to a surface that does not interpret markdown, and
  escape the characters each surface reserves.
- Where a surface's table construct requires a declared fallback for clients that cannot render it,
  declare that fallback.
- Render a table only where that surface's aggregate table budget accommodates it, and otherwise
  render the same fields as labelled lines.
- Where a surface derives a notification preview from one designated field, populate that field with
  the week covered, the count of urgent items and the aggregate amount at risk.

A degraded row keeps every field and labels each one:

```
Meridian Healthcare
  Value: $200,000 · Stage: Business Validation · Owner: J. Rivera
```

### Length

1. **Apply a length bound to each surface**, held by this skill rather than discovered by exceeding a
   platform limit. The failure mode of exceeding an undocumented limit is silent truncation at the
   end of the message, which, given the report's ordering, removes the executive summary and the
   footer: exactly the copy-forward artifact and the provenance disclosure.
2. Where a rendered report exceeds the bound, **continue it across additional units** rather than
   truncating, preserving the section sequence so a partner reading two messages reads one report.
3. **Render the priority action section, the executive summary and the footer on every surface
   irrespective of length.** A length bound must not achieve by truncation what no preference is
   allowed to do. If something must go, it is overflow within a capped section.
4. **Never omit content at a surface boundary without stating the omission.**
5. **Where the surface cannot carry a continuation, state on that surface what was omitted.** The
   statement goes in the delivered content, not only in the footer, because the footer may itself be part
   of what did not fit. This is the only circumstance in which rule 4 fires, and it is the one outcome
   this projection must never produce silently: a partner who receives a report cut mid-list, with
   nothing saying so, has no way to know that the items they most needed were the ones that did not
   arrive.

Rendering also never decides that a subdivision does not fit. Which subdivisions a section contains
was resolved in composition. A subdivision too large for a surface degrades in presentation, exactly
as a table does.

### Accessibility

1. **Convey every distinction the report draws in text.** Never by colour alone, never by weight,
   size or styling alone.
2. **Render link text that describes the destination.**
3. **Render a table with a header identifying each column.**
4. **The content survives being presented without styling.**

The practical check: read the report aloud, or strip every style from it, and every distinction it
draws must survive. A report that passes reads correctly for a screen reader, in a plain-text mail
client, and in a messaging client that ignores half the markup.

Most of this is already satisfied upstream: the urgency vocabulary is words rather than colours,
successful no-item omission and failed or unavailable omission differ through footer disclosure, and
absence renders as a phrase rather than a dash. Rendering must not undo that by substituting a visual
signal for the text.

### Surface identification

Render the report's identification, covering the product and the week covered, on every surface.
Where a surface has no subject concept, render it as the report's leading content.

### Surface capabilities

Establish each surface's real capabilities against the partner's own install rather than assuming
them. What to determine, and what to do with the answer:

| Question to establish | What it changes |
|---|---|
| Does this surface interpret markdown, or its own notation? | Which notation to emit, and which characters to escape |
| Does it support tables, and under what aggregate budget? | Whether a table renders or degrades to labelled lines |
| Do any of its clients reject the table construct? | Whether a declared simpler fallback is mandatory |
| Does it have a subject concept? | Whether identification is a subject or leading content |
| What length bound applies, and does the runtime add its own? | Where continuation begins |
| Does it derive a notification preview from one field? | Whether that field must carry the week, the urgent count and the amount at risk |

Markdown including tables is the baseline representation for every element. Richer renderings are
enhancements, used only where verified against the partner's install.

**Two asymmetries to expect, because they defeat the obvious approach.** A messaging surface may
support tables while using a notation that is **not** markdown, so passing markdown through produces
literal punctuation and broken links. A collaboration surface may accept a markdown subset that
**excludes** tables, headers and preformatted text while supporting a native table element its own
mobile client will not render. So degradation is decided **per surface and per section**, against that
surface's notation and budget, never once for a category. And a table on a surface whose mobile
client cannot render it must always carry a simpler fallback, or a partner reading on a phone sees
nothing where the table was.

### What rendering may not do

- **No surface-specific summarisation.** A shorter version for a messaging channel is a different
  report.
- **No emoji or decoration added at render time.**
- **No re-ranking and no re-capping.** Both are composition decisions, already resolved.
- **No inferred link target.** A link renders only where composition supplied one.
