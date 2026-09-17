---
description: "Reference for the Amazon Quick skill format: folder layout, SKILL.md frontmatter and body, desktop-only constraints, and sharing behavior."
last_updated: 2026-09-08
origin: original
---

# The Amazon Quick skill format

A Quick skill is a **folder** containing a `SKILL.md` (YAML frontmatter + markdown body) and,
optionally, bundled reference files, helper scripts, and a `scratchpad.md`. The `SKILL.md` is the
entry point; reference files are pulled in as the workflow needs them. No code and no APIs required.

Skills are **desktop-only** (Windows and Mac): not available on Quick web, mobile, or the browser
extension. They **can be shared** with teammates on the desktop - publish/share from the Skills tab,
or export the folder as a `.zip`/`.qplugin` - but each person runs their own installed copy (so an
update means re-sharing, not central propagation). See **Sharing** below.

## Frontmatter

```yaml
---
name: my-skill-name
display_name: My Skill Name
description: What this skill does (shown in skill list, and used to match requests)
icon: "⚡"
trigger: "trigger phrase here"
tools:
  - browser_navigate
  - browser_read_page
  - file_write
---
```

| Field | Rule |
| --- | --- |
| `name` | Kebab-case identifier. **Must match the folder name.** |
| `display_name` | Human-readable name shown in the skill list. |
| `description` | Shown in the skill picker **and** used to match a request to the skill. Front-load the trigger vocabulary. |
| `icon` | A single emoji. |
| `trigger` | The phrase that activates the skill. 2-4 words. Must not collide with a built-in skill. |
| `tools` | Tools the skill may use. Verify names against the user's build - see `knowledge-and-tools-remap.md`. Omit rather than guess. |

Richer skills follow the Agent Skills specification and may add `depends-on` and typed `inputs`:

```yaml
trigger: build quick app
depends-on: [browser]
inputs:
  - name: account_name
    description: "Quick account name (e.g. 'amazonbi')."
    type: string
    required: true
    default: amazonbi
```

Use `inputs` when the source agent's starter prompts implied parameters ("summarise emails from
*[team]*") - typed inputs beat asking the user mid-run.

### The delimiters and the line breaks are part of the contract

A frontmatter block that is *nearly* right does not error - it installs, and the skill shows up in Quick
with **a blank name, `0 tools`, and the whole block sitting in the Instructions panel as prose**. The
values were correct; the framing was not. Four rules:

| Rule | Why it matters |
| --- | --- |
| Line 1 is exactly `---`, with nothing above it | Any character before it - a heading, a blank line, an intro sentence - means no frontmatter is found at all |
| A line that is exactly `---` closes the block | An unclosed block swallows the body; Quick finds no keys |
| One key per line, starting at column 1 | Several keys on one line parses as a single key whose value is all the others. `name` then fails its kebab-case check and `tools` is never seen |
| No `#` before a key | `#` starts a YAML comment. `## name: my-skill` drops `name` silently - the most misleading version of this bug, because the text is right there on screen. A comment on a line of its own is fine; a comment in front of a key is not |

Broken, and it looks fine at a glance:

```
---
## name: my-skill display_name: My Skill description: "..." tools: [file_read, file_write]
---
```

**Read the file back after writing it** and confirm line 1, the closing `---`, and one key per line.
`scripts/package_skill.py` checks all four rules and names the symptom in the error, so run it whenever
code execution is available.

**Creating a skill through Quick's Custom skill form is different.** There, the frontmatter values are
the form's own fields - name, display name, description, icon, trigger - and **only the body**, meaning
everything below the closing `---`, goes into the Instructions box. Pasting the whole `SKILL.md` into
Instructions produces exactly the blank-name failure above.

## Body structure

```markdown
# My Skill Name

## Overview
What it does, when to use it, and what it is not for.

## Prerequisites
Connectors, folders, files the user must have. Actionable by a non-author.

## Workflow Steps
### Step 1: ...
### Step 2: ...

## Example invocations
(from the source agent's starter prompts)

## Best Practices
...

## Failure handling
What to do when a step cannot complete.
```

## Deterministic vs agentic steps

Write a step **deterministically** - exact clicks, exact fields, exact order - when the target is
stable and a wrong guess is expensive (filling a form, posting to an API, editing a wiki). Write it
**agentically** - state the goal and the success criterion - when the path varies (finding the right
document, summarising, judging relevance). Source agent instructions are usually written agentically
throughout; upgrade the brittle steps to deterministic during conversion.

## Writing for a zero-context agent

The agent reading a skill was not in the room when it was written. **Precision over compactness:**

- Every instruction atomic and self-contained.
- Never reference "the thing we discussed" - there is no shared history.
- Include full context inline, or give a path the agent can follow to find it.

This inverts the usual advice. In live conversation with Quick you share context, so be concise.
Precision applies only to durable instructions read by stateless readers - skills, scheduled tasks,
scratchpad notes.

## Self-improvement

After a run that needed adaptation, Quick may offer to improve the skill; you can also say
`improve the <skill name> skill`. It targets failed steps, missing error handling, new best
practices, and changed tool names, while preserving the core workflow.

Bake the loop in with a `scratchpad.md` in the folder - read before running, appended after:

```markdown
## Improvement Queue
- [ ] IMP01: [description of needed improvement]

## Lessons Learned
- 2026-09-01: [what went wrong and how to avoid it]
```

**Checkboxes are the sole source of truth.** Agents have no memory between sessions; an unchecked
box stays undone regardless of what was discussed. If it is not a checklist item, it will not happen.

## Installing

Skills created **with AI** or **saved from a completed workflow** install themselves. To install a
shared one:

**Settings → Capabilities → Skills → Upload** *or* **Settings → Agents & skills → Skills →
+ Create → Import from file** - the panel label differs across builds; they do the same thing.
Accepts a `.zip` of the folder, or a bare `SKILL.md`.

Then **restart Quick desktop**. The skill will not activate until you do. Upload processing can take
up to five minutes; if Quick does not recognise the skill, restart again. Confirm with
`Tell me about <skill name>`.

Manually authored folders dropped on disk are picked up on the next restart:

| Platform | Path |
| --- | --- |
| macOS / Linux | `~/.quickwork/profiles/federate-prod/skills/` |
| Windows | `%USERPROFILE%\.quickwork\profiles\federate-prod\skills\` |

## Invoking

- **Trigger phrase** or skill name in chat.
- **Automatic selection** - Quick matches the request against skill descriptions. This is why
  `description` quality matters.
- **Run button** - Skills tab → select → **Run** starts a conversation with the skill pre-loaded.

## Sharing

Skills **can** be shared on the desktop - three ways:

1. **Publish / Share to teammates** - from **Agents & skills → Skills**, open the skill's detail pane
   and use Publish/Share. Recipients add it from **Browse more → "Shared with you"** (curated
   first-party skills appear under **"Official"**). This installs an editable local copy they own.
2. **Export the folder** - as a `.zip` or bundle it into a `.qplugin` and send it; the recipient
   imports via **+ Create → Import from file** (or double-clicks the `.qplugin`).
3. **Org catalog**, if your organisation runs one.

In every case each person runs their own installed copy - sharing is a one-click add, not a re-author,
but an update means re-sharing rather than propagating centrally. To stay shareable: no hardcoded
paths, no user-specific references, prerequisites documented in Overview, example usage in the
description, and test from a fresh install. Recipients need the same connectors the skill uses;
browser-based skills need Chrome with your organization's SSO / authenticated access for internal
sites.

## Related: AGENTS.md

Distinct mechanism, often confused with skills. `AGENTS.md` is a governance file in a connected
local folder, read at the **start of every session** via a Customization Panel instruction
(**Settings → Customization → Response preferences**). It is *not* uploaded to the skill registry.
It carries identity, rules, and workspace map. A skill is on-demand and costs nothing until invoked;
`AGENTS.md` is always on. If the source agent was really encoding *standing preferences* rather than
a workflow, it belongs in `AGENTS.md`, not in a skill.

---

Sources: AWS documentation, "Skills and agents" (Amazon Quick on desktop) and "How Amazon Quick
works"; internal Amazon Quick skill-authoring guidance.
