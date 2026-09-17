---
description: "Mapping table from source declarative-agent configuration fields to their Amazon Quick SKILL.md equivalents, covering what ports verbatim and what must be transformed."
last_updated: 2026-09-08
origin: original
---

# Field-by-field mapping: source agent → Amazon Quick skill

## The mechanical part

| Source configuration field | Quick `SKILL.md` | How to convert |
| --- | --- | --- |
| **Name** (~30 chars) | `display_name` | Verbatim. |
| - | `name` | Kebab-case the display name. **Must equal the folder name.** |
| **Icon / avatar** (raster image) | `icon` | Not portable. Pick one emoji. Report the image as dropped. |
| **Description** (~1000 chars) | `description` | Near-verbatim - both are read by the model to decide whether to invoke. Append the trigger phrasings so matching is reliable. |
| **Instructions** (~8000 chars) | body of `SKILL.md` | **Restructure, do not paste.** See below. |
| **Knowledge sources** (~20 max) | prerequisites + `references/` + connections + spaces | Per-source decision. See `knowledge-and-tools-remap.md`. |
| **Capabilities** (code execution, image generation) | built-in Quick skills; `tools:` | See `knowledge-and-tools-remap.md`. |
| **Starter prompts** | `## Example invocations`; vocabulary into `description` | All of them go in the body, copied from the full field (UIs clip the display). They are *examples*, not scope - do not seed the trigger from one. Their first-invoke display role is **dropped**: Quick has no prompt-chip surface, and Example invocations is read by the model, not shown to the user. |
| **Model / response-mode selector** | - | **Not agent configuration** - a session-level UI setting on most builders. Do not interview about it. Quick picks the model. |
| **API actions** (spec-defined plugins) | action connector or MCP server | Reuse the same API specification. Do not reimplement. |
| - | `trigger` | **Usually no counterpart. Must be invented.** 2-4 words derived from the **Description and Purpose** - the job, not one example task. Verify it covers the breadth of the starter prompts. Must not collide with a built-in skill. |
| - | `scratchpad.md` (optional) | No counterpart. Offer it: improvement queue + lessons learned, so the skill sharpens with use. |

## Restructuring instructions into a skill body

A source agent's instructions field is one continuous block written for a chat persona that will be
re-read on every turn of a live conversation. A Quick skill body is loaded on demand and read by a
**zero-context agent**. Different genre, same content.

| Source instruction pattern | Becomes |
| --- | --- |
| "You are a … that helps users …" | One-paragraph `## Overview`. Cut the role-play; keep the scope. |
| "Follow these steps: 1… 2… 3…" | `## Workflow Steps` with `### Step N:` headings. Keep the numbering; make each step atomic. |
| "Always / Never / Make sure to …" | `## Best Practices`, or inline in the step it constrains - whichever the agent will actually read at the right moment. |
| "If you cannot find … then …" | `## Failure handling`. Source agents often bury this; pull it out and make it explicit. |
| "For example: …" (long examples) | A file in `references/`, pointed at from the step. Keeps the body scannable. |
| Long rubrics, scoring tables, templates | A file in `references/`. This is the mechanism that lets a skill carry a whole methodology. |
| Tone / voice instructions | Keep, in `## Best Practices`. These usually port perfectly. |
| Boilerplate from a builder template | **Cut.** It is generic filler and costs context on every load. |

Two rules that override style preference:

- **Precision over compactness.** Every instruction atomic and self-contained. Never "the thing we
  discussed above" - the receiving agent was not in the room. Full context inline, or a path it can
  follow. (This is the opposite of how you write in live chat, where brevity wins.)
- **Checkboxes are the only durable state.** If the skill needs something to happen on a later run,
  it must be an unchecked checklist item in `scratchpad.md`. Prose intentions are not remembered
  between sessions.

## When to build a Quick agent instead of a skill

**This is decided by who uses it, where they need it, and how it is invoked - not by what the
instructions contain.** In particular, "the source has no ordered steps" is not an argument for
`AGENTS.md` or against an agent. It only means the output will have no `## Workflow Steps` section. A
persona of pure guidelines is the *most* common thing to want to be a shared agent. Keep the two
decisions apart; `SKILL.md` Step 1 works them separately.

A skill is the right target when the source agent is **something fired on demand from the desktop by
trigger phrase**. Skills are desktop-only, and each person runs their own installed copy - but they
**can be shared** with teammates (publish/share from the Skills tab, or export as `.zip`/`.qplugin`), so
"a teammate needs it" is not on its own a reason to reject a skill.

Build a **Quick agent + space** instead when the source agent is:

- **A shared team persona that must stay centrally managed.** Both skills and agents can be shared, but
  an agent is one central object - you share it (with a space bundling documents, dashboards, datasets,
  knowledge bases and action connectors), updates reach everyone, and it works cross-surface. A shared
  skill instead gives each teammate their own copy that only updates on re-share. Choose the agent when
  central management and cross-surface reach matter; a shared skill is fine for a lightweight
  desktop-only hand-off.
- **Grounded in a large, changing corpus.** Knowledge bases in a space index the sources listed in
  the Quick console and stay in sync. A skill's bundled reference files are static.
- **Needed on web, mobile, a team chat platform, or a browser.** Skills are desktop-only; agents reach
  the extensions.

The two compose: an agent can be given a space for grounding while the user still has a skill that
drives a repeatable workflow. If the source agent is both a persona *and* a workflow - common -
recommend agent for the grounding, skill for the workflow, and say which half goes where.
