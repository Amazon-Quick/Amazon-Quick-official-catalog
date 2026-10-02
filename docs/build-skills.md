---
title: Build reliable skills for Amazon Quick
description: Apply dependency, validation, versioning, security, and evaluation practices when you build reusable skills for Amazon Quick.
---

# Build skills with software engineering practices in Amazon Quick

When you build a skill for yourself, it works because everything it depends on is already set up in your account. When you share it, the people you share it with need those same things. For example, your skill might use the Microsoft Outlook connector or a specific Microsoft SharePoint knowledge base. If the person you share it with doesn't have access to that connector or knowledge base, the steps that use it fail. Other dependencies are harder to see, such as the response mode, which tools are available, whether the skill still works months later, and whether code the skill generates can run.

Software engineers deal with the same problem every time their code runs on someone else's computer, and they handle it with practices such as declaring dependencies, keeping settings out of the code, handling errors, versioning releases, and testing before they ship. You don't need to know any of those practices to build a skill that works for other people, because Skill Builder, a skill in the official catalog, applies them for you. It asks about the things that tend to break for other people while it plans your skill, writes checks into each step while it builds, and audits the skill every time you save it. That way anyone can build and share a skill safely, even if they've never written code. In this post, we walk through each practice, what goes wrong without it, and how Skill Builder applies it, so you understand what it does on your behalf.

## Prerequisites

To follow along, you need Amazon Quick on desktop with the Skill Builder skill installed, which [Install a skill](install.md) walks through. Skill Builder uses only tools that are built into Amazon Quick, so you don't need to set up any connectors. Once it's installed, enter `sb help` in a conversation to see its commands. This post also assumes you know how a skill's files are laid out, which [What is a skill?](getting-started.md) covers.

## Getting started with Skill Builder

You don't have to start from nothing. Skill Builder can turn a multi-step task you just finished in a conversation into a skill, convert a runbook, process document, or agent prompt you already use, or plan a skill from a description of the task, asking clarifying questions when the description is too vague to plan from.

The examples in this post use a weekly status update skill that reads your notes for the week, adds the emails you sent, and posts a summary to your team's channel. Skill Builder starts each step with a label for who acts, such as `[Agent]` for a step Amazon Quick does without asking you. Below the step, a `Validate:` line says how to confirm the step worked, and an `If fails:` line says what to do when it didn't.

## Write the description for someone who has never seen the skill

Amazon Quick decides which skill to use from each skill's name and description, so someone who doesn't know your skill exists only gets it when the description matches the words they use. The following description works for you, because you know to ask for the skill by name, but it gives Amazon Quick little to match against anyone else's request:

```yaml
description: "Status update helper."
```

A better description says what the skill does and lists the phrases people might use when they ask for it:

```yaml
description: "Prepare a weekly status update from your notes using the team template. Use when asked for a 'weekly update', 'status report', 'what I did this week', or any request to summarize the week's work."
```

Other developers decide whether to use a function from its name and documentation alone, without reading the code inside, which is why both need to be clear. Skill Builder drafts the description before it writes any steps and asks you to approve it, so the line that decides whether the skill gets used is settled first.

## Keep values that change out of the steps

A step that names your folder or your channel works for you and breaks for everyone else. When a teammate runs the following step, Amazon Quick looks for notes in a folder that only exists on your computer and posts to your team's channel instead of theirs:

```markdown
1. [Agent] Read the notes in /Users/me/notes and post the update to #my-team.
```

Instead, declare those values as inputs in the frontmatter, so the person running the skill provides their own:

```yaml
inputs:
  - name: notes_folder
    description: "Folder that holds this week's notes"
    type: path
    required: true
  - name: channel
    description: "Channel to post the update to"
    type: string
    required: true
```

{% raw %}

Then refer to the inputs in the step, where `{{notes_folder}}` and `{{channel}}` stand for the values that person provides:

```markdown
1. [Agent] Read the notes in {{notes_folder}} and post the update to {{channel}}.
```

Engineers call this separating configuration from code. The steps stay the same for everyone, and each person brings their own settings. Only make a value an input when it changes from one person or run to the next, though, because asking for a value that never changes adds a question with the same answer every time. Skill Builder looks for file paths, web addresses, channel and team names, and routing tables in the steps it writes, and asks you which ones should become inputs.

## Declare what the skill depends on

A skill that uses a connector works for you because the connector is set up in your account. Share it with someone who doesn't have that connector, and the skill fails at the first step that needs it without telling them why. The following step looks fine until someone else runs it:

```markdown
1. [Agent] Find the emails you sent this week and add them to the summary.
```

Name the dependency in the skill's README, where the person installing the skill reads what to set up. The entry says what kind of dependency it is, where it runs (in this case, in the cloud rather than on their computer), and whether the skill can run without it:

```markdown
## Pre-requisites
- Microsoft Outlook (cloud connector, cloud runtime, required)
```

Then add a first step that checks for the connector before the skill does any work, so a missing connector stops the skill with a message that tells the person what to do:

```markdown
1. [Agent] Check that the Microsoft Outlook connector is available.
   Validate: The connector is connected and can search mail.
   If fails: Stop. Tell the user this skill needs the Outlook connector, and link the setup guide.
```

This is why software projects list their dependencies in one place, so whoever runs the code can install everything up front instead of finding out from an error halfway through. Skill Builder records each connector while it plans the skill, writes the README's Pre-requisites section for you, and adds the check as the skill's first step.

## Say how each step can fail

An agent can't tell that a step failed if the step never says what success looks like. Nothing in the following step tells Amazon Quick to stop when there are no notes for the week, so the skill can post an empty update to your team:

```markdown
2. [Agent] Summarize the notes.
```

A check and a failure path make the skill stop and tell the person what's wrong:

```markdown
2. [Agent] Summarize the notes.
   Validate: At least one note from this week was found.
   If fails: Stop, and tell the user that no notes from this week were found in {{notes_folder}}.
```

{% endraw %}

This is error handling. Code that checks its results stops at the first problem, while code that doesn't keeps going and passes bad output along as if nothing happened. Skill Builder writes a validation and a failure path for every step, and its audit flags any step that's missing a failure path.

## Record when the skill changed

Skills installed from the catalog update automatically when a new version is published, so a skill can behave differently today than it did last month. When that happens, the people running it need a way to tell that it changed. Two dates in the frontmatter give them that:

```yaml
created_date: "2026-05-21"
last_updated: "2026-09-13"
```

These dates work like the version number on a software release, telling people which version they have and when it last changed. Skill Builder sets both dates when it saves a skill, and the [skill catalog](skill-catalog.md) shows `last_updated` in its **Updated** column. If a skill hasn't been updated in more than six months, Skill Builder's audit marks it as stale and recommends testing it again.

## Record where reference files came from

Some skills include reference files with information their steps rely on, such as a list of package names or a lookup table. When that information is copied from somewhere else, it goes out of date when the source changes, and whoever fixes it needs to know where it came from. Each reference file starts with a short header. This one, which Skill Builder's standard uses as an example of what not to do, leaves the next person guessing:

```yaml
---
description: "Eval methodology."
last_updated: 2026-09-13
---
```

This one tells them where to rebuild the file from:

```yaml
---
description: "Amazon Quick Python sandbox package names, grouped by use."
last_updated: 2026-09-13
source_url: <URL of the documentation page the list came from>
---
```

When someone writes a file from scratch, the header records `origin: original` instead, so the maintainer knows there's no source to compare against and reviews the file by hand. Developers keep a note of where they copied code from, so they can pull in updates later. Skill Builder creates every reference file and script from a generator that requires exactly one of `source_url` or `origin: original`, and the [reference file header standard](https://github.com/Amazon-Quick/amazon-quick-official-catalog/blob/main/skills/amazon-quick/skill-builder/references/reference-file-standard.md) lists every field.

## Fingerprint the files you checked

Once a skill passes its checks, any edit or copy can make it different from what was checked, and nothing about the files shows it. A checksum makes that difference visible. It's a fingerprint calculated from the contents of the skill's files and stored in the frontmatter, and changing any of those files changes the fingerprint:

```yaml
checksum: "sha256:<fingerprint of SKILL.md, README.md, scripts/, references/, and assets/>"
```

Say you download a skill's folder from the catalog repository and change one of its scripts for your team. When you run `sb audit` on your copy, the stored checksum no longer matches the files, which tells you that your copy differs from the version that was audited. The same check catches a copied folder that's missing a file. Software downloads publish checksums for the same purpose, so you can confirm that the file you have is the one that was released. Skill Builder calculates the checksum every time it saves a skill, and its audit recalculates it and compares the two.

## Check the structure after every change

A later edit can undo any of these practices without anyone noticing. If you edit a step by hand and leave out its failure path, or change a file without updating the checksum, the skill still reads fine. That's why Skill Builder audits a skill every time it saves it, and why you should enter `sb audit` after you edit a skill's files yourself.

The audit works in two passes. First, a script checks what a program can check, such as required fields, the order of the instruction sections, failure paths, listed tools, and the checksum. Then Skill Builder reads the skill for what needs judgment, such as whether each rule is a real constraint. Developers rely on the same kind of automatic check, called a linter, to catch mistakes before anyone reviews their code.

## Test the skill against no skill at all

A skill that worked once on your own request hasn't shown that it does better than Amazon Quick does without it, and a skill that adds nothing still takes up space in every conversation where it loads. Enter `sb eval` to find out. Skill Builder drafts a few realistic requests, including at least one unusual one, and you review them before anything runs.

Each request then runs twice, once with the skill and once without it. For the status update skill, that comparison shows whether Amazon Quick already follows your template without the skill. If it does, you don't need the skill.

Each run happens in a separate session that can't see the conversation where you built the skill, because the people you share it with can't see that conversation either. Software teams test on a clean computer, since a test on the developer's own computer can pass because of something only that computer has. The runs also use the model tier set in the skill's `preferred_model` field (fast, balanced, or smart), so a skill meant for the fast tier is tested on the fast tier.

A separate session grades each run, because whoever built the skill knows what they meant and grades with that bias, which is also why code is reviewed by someone other than its author. The results show each run's pass rate next to how long it took and how many tool calls it made, so you can tell when a change made the skill more accurate but slower. Change one thing between rounds, so you know which change made the difference.

## Publish through a gate

Installing a skill from the catalog means running instructions, and sometimes scripts, that someone else wrote, with your connectors and your data. Software teams manage that kind of risk with automated checks before every release, and the [official catalog](https://github.com/Amazon-Quick/amazon-quick-official-catalog) does the same for skills. Before a skill is published, the catalog runs Skill Builder's checks on it, scans its content for security issues, and other criteria. It also records each published skill's checksum, so a change to a published skill fails the catalog's checks until the checksum is regenerated.

## Conclusion

Every practice in this post exists to make a skill work for someone who wasn't in the conversation where you built it. You don't have to remember them, because Skill Builder applies them each time it plans, builds, saves, audits, or tests a skill, and the catalog checks them again before it publishes one. To get started, [install Skill Builder](install.md), enter `sb help`, and turn a task you keep explaining into a skill. If you find a problem with a skill or want to request a new one, [open an issue](https://github.com/Amazon-Quick/amazon-quick-official-catalog/issues).
