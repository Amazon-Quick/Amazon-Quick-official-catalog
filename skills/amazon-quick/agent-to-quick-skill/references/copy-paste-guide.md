---
description: "Field-by-field transfer instructions for a conversion: what to copy from the source authoring UI and exactly which Amazon Quick window, menu, and field to paste it into, including alternate menu labels across Quick builds."
last_updated: 2026-09-08
origin: original
---

# Copy-and-paste transfer guide

Field-by-field: what to copy from the source authoring UI, and exactly where to paste it in Amazon
Quick. Read this to the user one row at a time - do not hand them the whole table and hope.

**Menu labels differ across Quick builds.** Where two labels are given, only one will be present on
their build. Offer both and let them tell you which they see.

**One question per message.** Where a row needs something from the user, ask for that one thing and
wait. These tables are a script to walk, not a form to send.

## Before you start

1. **Both windows open, side by side.** The source authoring UI in its configuration view, Quick
   desktop next to it. Every field below is a copy from the left and a paste on the right.
2. **Put the shape in front of the user as named options and get a pick** (Step 1, Decision A of the
   workflow) before you paste anything. Not a recommendation - a pick-one list that names the surface,
   desktop or web, and every component the data needs: "**Skill + MCP server** - per-user desktop skill
   plus an MCP server for the CRM and library data", "**Agent + space + MCP server** - web-configured,
   shareable, cross-surface", "**Explain the tradeoffs**". The destination is set by who uses it, where
   they need it, and how it is invoked - *not* by whether the instructions contain steps. Landing in the
   wrong one means redoing the whole transfer. Three different destinations take different pastes:
   - **A skill** - text goes into files you write. Most of this guide.
   - **An agent + space** - text goes into Quick web forms. See "Path 2".
   - **`AGENTS.md`** - one file, all the standing preferences. See "Path 3".
3. **Copy from the full field, not the displayed row.** Instructions boxes scroll and prompt tables
   clip to column width. For every multi-line field: click into it, select all, copy. Verify the paste
   is not truncated before moving on.

---

## Path 1 - source agent → Quick skill

The skill is files on disk, so most of this is paste-into-a-file, not paste-into-a-form.

| # | Copy from the source | Paste into | Notes for the user |
| --- | --- | --- | --- |
| 1 | **Name** (top of the configuration view) | `display_name:` in `SKILL.md` frontmatter | **Ask first: do they want to keep this name for the Quick skill, or use a different one?** Offer the source name as the default. Whatever they choose goes in verbatim, spaces and capitals intact. |
| 2 | - | `name:` in frontmatter | Not a copy - kebab-case the name they chose. **Must equal the folder name.** |
| 3 | **Description** (under the name) | `description:` in frontmatter | Near-verbatim. Then append the starter-prompt phrasings so the model matches more requests. Keep it one line, quoted. |
| 4 | **Instructions** - click in, select all, copy | the body of `SKILL.md`, restructured | The one field you must not paste raw. See `field-mapping.md` for which block becomes which section. Purpose → `## Overview`, Guidelines → `## Best Practices`. |
| 5 | **Suggested / starter prompts** - each Message field, opened individually | `## Example invocations` | Copy from inside each field; the table view clips them. |
| 6 | **Knowledge** - each source's exact target (link, file name, connector name) | nowhere directly - each becomes a prerequisite | This is a decision, not a paste. **Ask for the link, then ask whether that library is already connected** under Settings → Capabilities → Connections. Reference it where it lives; a local copy is the fallback and a manual download is the last resort. Work `knowledge-and-tools-remap.md` per source, then write the outcome into `## Prerequisites`. |
| 7 | **A baseline output** - run the agent in the source's preview/test mode, copy the result | a scratch note outside the skill | Not part of the skill. It is the only thing you can verify the conversion against. |

Then, in Quick desktop:

| # | Action | Where |
| --- | --- | --- |
| 8 | Write the skill folder next to their existing skills | Resolved, not asked - find the connected folder whose subfolders contain `SKILL.md` files. See "Locating the skills folder" in `SKILL.md` Step 5. Only if none exists: **Settings → My computer → Local folders → Add folder** |
| 9 | **Read the finished `SKILL.md` back and check the frontmatter block** | Line 1 exactly `---`, a closing `---`, one key per line, no `#` before a key. Run `scripts/package_skill.py`. Skip this and the skill installs with a blank name and `0 tools` - see `quick-skill-format.md` |
| 10 | Upload the zip | **Settings → Capabilities → Skills → Upload**, or **Settings → Agents & skills → Skills → + Create → Import from file** |
| 11 | Restart Quick desktop | - Required. Processing can take up to five minutes. |
| 12 | Add each connection the Prerequisites named | **Settings → Capabilities → Connections** |

**If the user creates the skill through Quick's Custom skill form instead of uploading a folder**, the
frontmatter is not pasted at all - each value goes in its own field (name, display name, description,
icon, trigger) and only the body, everything below the closing `---`, goes into Instructions. Walk the
fields one at a time. Pasting the whole file into the Instructions box is what leaves the name blank.

## Path 2 - source agent → Quick agent + space

Use this when Step 1 decided the source is a shared persona, is grounded in a large changing corpus,
or is needed somewhere other than the desktop app. **Agents and spaces are configured on Quick web,
not in the desktop app** - say that up front, because the user will be looking in the wrong window.

**Order matters: build the space first.** An agent is assigned a space; if the space has no knowledge
in it yet, the agent has nothing to ground against and its first answers will mislead you into
thinking the instructions are wrong.

| # | Copy from the source | Paste into | Notes for the user |
| --- | --- | --- | --- |
| 1 | **Knowledge** sources, one at a time - the link, not a downloaded copy | Quick web → create a **space** → add a **knowledge base** → add the source | Do this before anything else. A permissioned link needs the matching connection to exist first - add it under Settings → Capabilities → Connections rather than downloading the file. Confirm each source type is on the currently supported list before promising it. |
| 2 | **Name** | the agent's name field | Verbatim. |
| 3 | **Description** | the agent's description field | Verbatim. This is what teammates read when choosing the agent. |
| 4 | **Instructions** - select all, copy | the agent's instructions field | **This paste is near-verbatim** - unlike Path 1, no restructuring needed. An agent's instructions are re-read every turn, same as the source, so the original prose genre is correct here. This is the main reason Path 2 is less work than Path 1 for a persona-style agent. |
| 5 | **Suggested / starter prompts** | the agent's starter-prompt or example-prompt field, if the build has one | Closer to a true port than Path 1: agents can display prompts to the user, skills cannot. If the field is absent, fold the phrasings into the description. |
| 6 | - | assign the **space** to the agent | The step people forget. An agent without its space is an agent without knowledge. |
| 7 | **Capabilities** that were switched on | the agent's tools / capabilities selection | Code execution and image generation are built in; tick the equivalents rather than rebuilding them. |

Then: share the agent with whoever used the source agent, and have **them** confirm they can see the
space's knowledge. Access is per-person, so it working for the author proves nothing about the team.

## Path 3 - source agent → `AGENTS.md`

Use this when the source was standing preferences with no procedure (Step 1, "No workflow in the
source").

| # | Copy from the source | Paste into |
| --- | --- | --- |
| 1 | **Instructions** - the whole thing, Purpose and Guidelines together | a file named `AGENTS.md` in the folder the user's skills already live in - resolved, not asked, exactly as in `SKILL.md` Step 5. It sits *beside* the skill folders, not inside one. |
| 2 | **Any document the Instructions refer to** - ask for the link, then for a local path if there is no link | a section of the same `AGENTS.md`, or a sibling file it points at. Say which parts of the document you pulled in. |
| 3 | - | turn it on: **Settings → Customization → Response preferences**, pointing at that folder |

Light editing only: cut "you are an agent that…" role-play, keep every always/never constraint. It is
read at the start of every session, so it must stand alone. It is **not** uploaded to the skill
registry and cannot be shared as a skill - if the user needs to share it, Path 1 or 2 instead.

---

## What has no paste target

Tell the user each of these explicitly rather than letting them discover it:

| Source item | Why there is nowhere to paste it |
| --- | --- |
| **Icon / avatar image** | Quick takes one emoji. Pick one together. |
| **Starter prompts, as a display feature** (Path 1 only) | Skills have no first-invoke prompt chips. The text still helps the model match, but the user will never see clickable examples - give them the trigger phrase instead. On Path 2 this may survive. |
| **Model / response-mode selector** | Session-level UI setting, not agent configuration. Quick chooses the model. |
| **A knowledge source the user will not rebuild** | Record as dropped and name what the skill will get wrong without it. |
| **Anything Red Data / HIPAA / PII** | Hard stop. Quick desktop is Highly Confidential but not Red Data certified. Do not connect it, and do not offer a workaround. |

## Verify the transfer, in this order

1. `Tell me about <skill or agent name>` - Quick should describe its purpose. If it cannot, the
   install did not land. Restart before troubleshooting anything else.
2. Say the **trigger phrase** (skill) or open the agent (Path 2). Confirm it loads.
3. Run the **starter prompt you captured a baseline for**, and compare against that baseline. This is
   the only step that actually tests the conversion; the first two only test the plumbing.
