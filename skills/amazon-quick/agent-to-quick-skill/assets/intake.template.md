# Conversion intake - <source agent name>

Date: <YYYY-MM-DD> · Source: <authoring UI configuration view | agent config JSON>

## 0. Destination - settle this before anything else

Two independent decisions. Do not let the second answer the first.

**Decision A - destination.** Determined by who, where, and how invoked. Any single agent signal wins.

| Question | Answer | Points to |
| --- | --- | --- |
| Just for you, or will the team use it? | | team → **agent** |
| Desktop only, or also web / mobile / browser / chat platform? | | beyond desktop → **agent** |
| Always on, or invoked deliberately? | | always → **`AGENTS.md`**; invoked → **skill** |
| Grounded in a few stable documents, or a large changing corpus? | | changing corpus → **agent + space** |

**The options actually put in front of the user**, as a pick-one list naming the surface and every
component the data needs - fill in the text you sent:

| Option offered | Text used |
| --- | --- |
| Desktop shape - **skill** (+ MCP server / connection, if a system of record is involved) | |
| Web shape - **agent + space** (+ the same data component) | |
| **Explain the tradeoffs** first | |

Chosen destination: `skill` / `agent + space` / `AGENTS.md` / split →

**The user picked it from the list** (a recommendation you made is not a pick): yes / no →

Data component included in the chosen shape: none / connection / space knowledge base / MCP server →

**Decision B - shape.** Do the source instructions contain an ordered procedure?

- Ordered procedure present → write `## Workflow Steps`.
- No ordered procedure → omit `## Workflow Steps`. Record it as a deliberate finding in section 7.
  **This does not change Decision A.**

## 1. Identity

| Field | Value |
| --- | --- |
| Source **Name** | |
| **Name the user chose for the Quick skill** (asked, not assumed - source name offered as default) | |
| Proposed Quick `name` (kebab-case of the chosen name, = folder name) | |
| Proposed Quick `display_name` (the chosen name, verbatim) | |
| Proposed `icon` (one emoji) | |
| Proposed `trigger` (2-4 words - **invented; usually no source counterpart**) | |
| Built via conversational authoring? (affects how much boilerplate to cut) | |
| Template used, if any | |

## 2. Description

Source **Description**, verbatim:

```
```

Quick `description` (source text + trigger vocabulary appended):

```
```

## 3. Instructions

Source **Instructions**, verbatim - do not summarise:

```
```

Restructuring notes (which blocks become Overview / Workflow Steps / Best Practices / Failure
handling / a `references/` file / cut as boilerplate):

-

## 4. Knowledge sources

One row per source. Resolve **every** row before writing `SKILL.md`. Include sources the instructions
merely *refer to* ("see the standards document") even if the Knowledge section never listed them.

Ask for the **link**, then whether that system is **already connected**. A local path is the fallback and
a manual download is the last resort. One question per message.

| # | Source type | Link (as pasted) | Connector exists? | Local path (fallback only) | Which instruction step consumes it | Changes? | Red Data? | Quick landing spot | Prereq for user | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | | | | | unresolved |

`Connector exists?` - already connected / can be added / none available for that system. A link behind a
sign-in wall means **add the connection**, not download the file. Only `none available` justifies a copy.

Copies made anyway (no connector available): list each with the date taken, because it is a snapshot and
the original will drift.

-

Status must end as `remapped` or `dropped` - never `unresolved`. A source with no link, no connector and
no local copy is `dropped`; name the consequence in section 7.

## 5. Capabilities

| Source capability | On? | Which step needs it | Quick equivalent | Status |
| --- | --- | --- | --- | --- |
| Code execution / interpreter | | | built-in code execution + document skills | |
| Image generation | | | built-in image generation skill | |
| Web search grounding | | | built-in web browsing skill | |
| API action / plugin | | | action connector / MCP from the same specification | |

API specification files obtained: <paths, or "none">

## 6. Starter prompts

Copy each **from the full field**, not the displayed row - UIs clip long prompt text to the column
width. These are *examples*, not a statement of scope: do not seed the `trigger` from one of them.

| Name | Prompt text (full) | Confirmed untruncated? |
| --- | --- | --- |
| | | |

Their first-invoke display role does not port - record it in section 7 as dropped.

## 7. Not portable - report as dropped

- Icon / avatar image → replaced by one emoji.
- First-invoke display of the starter prompts → Quick has no prompt-chip surface; `## Example
  invocations` is read by the model, not shown to the user. Tell the user the trigger phrase instead.
- Workflow steps the source did not contain → **not invented.** Note this explicitly if the source was
  standing preferences rather than a procedure.
- Model / response-mode selector → not agent configuration; nothing to port.
- Other:

  -

## 8. Baseline for verification

Output captured from the source platform's preview mode for the most representative starter prompt:

```
```

## 9. Proposed `tools:` list

Each name **verified** against the user's build (Agents & skills → Skills → open a built-in skill →
attached tools). Unverified names must be omitted, not guessed.

| Tool name | Verified? | Needed by step |
| --- | --- | --- |
| | | |

## 10. Output location

Resolved, not asked. Fill in as you write.

| Field | Value |
| --- | --- |
| Connected folders searched | |
| Folder containing existing skills (subfolders with `SKILL.md`) | |
| How many skills it already holds | |
| Path written to | `<skills-folder>/<skill-name>/` |
| Created the folder because none existed? | no / yes |

If more than one candidate was found, note which the user picked and what the alternatives were.

## 11. Outstanding decisions for the user

-
