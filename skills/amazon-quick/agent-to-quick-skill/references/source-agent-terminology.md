---
description: "Platform-neutral vocabulary for interviewing a user about their source declarative agent, with exactly what to capture for each concept."
last_updated: 2026-09-08
origin: original
---

# Source-agent vocabulary, and what to capture

Use this to interview a user who has their agent open in an external assistant platform's authoring
UI and does not know which parts matter. Written platform-neutrally: the concepts below are common
to low-code declarative agent builders generally. Ask the user what their platform calls each one
and use their words back.

Each entry gives: what the concept is, and **exactly what to capture**.

---

## Container concepts

**Declarative agent.** What these builders produce. It is *not* a model or a hosted service - it is
the host assistant's own orchestrator plus your configuration: instructions, grounding, and tools.
This is why conversion to a Quick skill works at all: both are configuration over someone else's
agent runtime.
→ *Capture:* nothing directly. Establish this so the user does not expect to migrate a "model".

**Authoring UI.** The low-code builder. Typically offers three entry points: describe what you want
in natural language, skip to a manual form, or start from a template.
→ *Capture:* nothing. Just get them to the manual configuration view.

**Conversational authoring mode.** The pane where the user types what they want and the platform
writes the name / description / instructions for them, suggests refinements, and auto-adds knowledge
sources and capabilities.
→ *Capture:* nothing from here - its output all lands in the configuration view. But **ask whether
they built this way**, because auto-generated instructions are usually verbose and template-shaped,
which means the Quick body needs more restructuring, not less.

**Configuration view.** The form listing every field. **This is the source of truth for conversion.**
→ *Capture:* all of it. Ask them to work top to bottom.

**Preview / test mode.** The in-authoring test instance, usually live once the agent has a name,
description and instructions.
→ *Capture:* have them run their top starter prompt and **save the output verbatim**. It is the only
baseline you get for verifying the Quick skill in Step 5. Ask for this early - it is easy to lose
access to the source agent mid-migration.

**Template.** A preconfigured starting point (description + instructions + prompts).
→ *Capture:* whether one was used. Tells you how much of the instruction text is generic boilerplate
to cut rather than port.

---

## The configuration fields

**Walk these as single questions.** The list below is in dependency order. Ask for one field, wait for
the answer, then ask for the next. Do not send it as a numbered list of questions - a batch gets a
partial answer, and fields 5 onward often turn out not to apply once you have field 4 in hand.

### 1. Name
Short display name, commonly capped around 30 characters.
→ **Capture verbatim** - then **ask whether the Quick skill should keep it.** The source name is a
default, not a decision. Users rename when the name is long, when they are converting a set of agents
and want a consistent prefix, when the old name carries their previous platform's branding, or when
Step 1 split one agent into two objects that now need distinct names. Ask it as one question with the
source name offered as the default, and show what the default produces: the `display_name` verbatim and
the kebab-case folder name derived from it.

### 2. Icon / avatar
Usually an uploaded or generated raster image.
→ **Do not capture.** Quick skills use a single emoji (`icon:`). Ask for one emoji instead, or pick
one matching the agent's job. Tell the user the image is dropped.

### 3. Description
Commonly capped around 1,000 characters. Critically: it is what the **host model reads to decide
whether to use this agent**, and it usually also shows in a catalog listing.
→ **Capture verbatim.** Highest-value field after the instructions, because it does the identical
job in Quick - `description:` is used to match a request to the skill. It ports almost unchanged;
you only append trigger phrasings.

### 4. Instructions
The behavioural prompt: tasks, how to complete them, guidelines, steps, error handling, examples.
Commonly capped around 8,000 characters.
→ **Capture verbatim, in full.** Do not accept a paraphrase. Ask them to select-all in the box and
paste. This is the asset the user actually spent time tuning; everything else is cheap to rebuild.
Then flag the restructuring work - see `field-mapping.md`.

### 5. Knowledge sources
Grounding attachments, commonly capped around 20. Types you will encounter, described generically:

| They will describe it as | Treat it as |
| --- | --- |
| "our intranet site" / "the team site" / "a document library" | Managed document library - sites, folders, or individual files |
| "a public website" / "these URLs" | Public web content |
| "my email" / "my inbox" | The user's own mailbox, via a platform connector |
| "our chat" / "my channels" | Team chat messages, via a platform connector |
| "a connector" / "our enterprise search index" | An indexed external system (ticketing, ITSM, wiki, …), tenant-configured |
| "our business data" / "the records table" | Structured business data platform |
| "a synced drive folder" | Cloud file storage, sometimes already synced to disk |

Note that some of these require a paid add-on licence on the source platform; the user will know
which. That licence dependency is a good argument for the migration, and worth mentioning.

→ **Capture, per source:** the type, the exact target (site URL, file name, connector name), and
**why the agent needs it** - which step of the instructions consumes it. That "why" is what lets you
pick the right Quick landing spot. A folder of six static templates becomes bundled reference files;
a site that changes weekly needs a real knowledge base.

→ **Ask for the link, then ask for the local path.** Two questions, in that order, one message each, per
source:

1. *"Can you paste the link to it?"* - the Knowledge section holds links into a shared document library
   or site rather than uploaded copies, so the link is what exists and what you should ask for first.
2. *"If it's not in a shared library, where is it on your machine?"* - only after the first answer comes
   back empty. A local file is frequently the better resolution: no connection to configure, no
   sign-in wall, readable immediately. **A missing link is not the end of the conversation.** Users who
   say "it's not in a library" very often have the file on disk and will not volunteer it unasked.

Then confirm the file is inside a connected local folder. If it is not, name the folder and the menu -
**Settings → My computer → Local folders → Add folder** - rather than leaving the user to work it out.

→ **The instructions themselves will name sources the Knowledge section does not.** Phrases like "refer
to the standards section" or "follow the brand guidelines document" mean a document exists somewhere,
whether or not it was ever attached. Treat every such phrase as a knowledge source to run the two
questions above against. If neither a link nor a local copy exists, record it as dropped and name the
consequence - do not silently let the instructions keep pointing at nothing.

Also ask: **is any of it Red Data / HIPAA / PII?** Amazon Quick desktop is rated Highly Confidential
and is *not* Red Data certified - such content must not be connected. This is a hard stop for that
source, not a preference.

### 6. Capabilities
Toggles that add abilities. The two you will almost always find:

| Toggle, however it is labelled | Capability | Quick equivalent |
| --- | --- | --- |
| "create documents, charts, and code" | **Code execution / interpreter** - math, data analysis, visualisations | Built-in code execution + document skills (strictly more capable: real local filesystem) |
| "create images" | **Image generation** | Built-in image generation skill |

Some platforms also expose web search grounding as a capability rather than a knowledge source.
→ **Capture:** which toggles are on, and which instruction steps depend on them.

### 7. Starter prompts / suggested prompts
Each typically has a short name and the prompt text, shown to the user as clickable examples the
first time they open the agent.

→ **Capture all of them, from the full field rather than the displayed row** - authoring UIs clip
long prompt text to the column width, and a half-copied prompt is easy to miss.

→ They become the **Example invocations** section of the Quick skill body, and their vocabulary
belongs in the `description` to widen matching.

→ **They are examples, not a specification of scope.** Do not read a list of prompts as a list of
distinct workflows, and do not derive the `trigger` from one of them - that narrows the trigger to a
single task and it then fails to match the agent's actual range. Derive the trigger from the
Description and Purpose; use the prompts to *check* it covers the breadth.

→ **Their display role does not port.** Quick has no first-invoke prompt-chip surface. `## Example
invocations` is read by the model to decide whether to invoke; the user never sees it. Report the loss
and tell the user the trigger phrase instead.

### 8. Model / response-mode selector
Usually a dropdown near the agent name - automatic, fast, extended-thinking, or a named model.

→ **Not part of the agent.** On most builders this is a UI-level setting for the current session, not
saved agent configuration. Do not interview the user about it and do not put it in the intake. Quick
has no equivalent field and chooses the model itself.

→ The one case worth a note: if the agent was *deliberately* pinned to extended reasoning because the
work is analysis-heavy, that is a signal to write explicit validation criteria into the Quick body
rather than relying on the model to be thorough on its own.

### 9. API actions / plugins
Some agents attach real tools defined by an API specification (typically OpenAPI).
→ **Capture the specification files.** These are the closest thing the agent has to real tools, and
Quick's equivalent is an **action connector built from the same specification**, or an MCP server.
Ask for the spec file; do not try to reimplement the API by hand.

---

## If they have a config file instead of a UI

An agent authored or round-tripped through a toolkit usually has a JSON config, sometimes nested
inside a broader app manifest. Keys vary by platform and version, but the shape is consistent:

| Typical key | Configuration field |
| --- | --- |
| `name` | Name |
| `description` | Description |
| `instructions` | Instructions |
| `conversation_starters[]` (`title`, `text`) | Starter prompts |
| `capabilities[]` (each with a `name` identifier) | Knowledge sources **and** capabilities - many platforms model both here |
| `actions[]` (`id`, `file` → an API spec) | API actions / plugins |

`scripts/parse_manifest.py` reads these and tolerates keys it does not recognise - schema versions
move. Unknown entries are reported as TODOs rather than dropped.

**Note:** many hosted authoring UIs have no documented config-export button. If the user built the
agent only in the UI, expect the interview path.

---

## If the source is a markdown definition

A different family of platforms defines agents and skills as files on disk rather than rows in a
hosted UI: a markdown file with YAML frontmatter and a prose body. You will meet two variants, and
they convert almost identically:

- **An agent definition** - typically under an `agents/` directory, named for the agent. Frontmatter
  carries `name`, `description`, `tools` and sometimes `model`. The body is the instructions.
- **A skill definition** - a `SKILL.md`, sometimes with sibling `references/` and `scripts/`
  directories. Same frontmatter idea, often already step-structured.

On these platforms the surrounding vocabulary matters too, because it decides how many objects you
are really converting:

| Term | What it means | Consequence for conversion |
| --- | --- | --- |
| **Sub-agent** | A task-scoped specialist the main agent dispatches to | Becomes one Quick skill. If it was dispatched *by* another agent, that orchestration does not port cleanly - flag it. |
| **Skill** | On-demand instructions the agent loads by relevance | Becomes one Quick skill, nearly one-to-one. |
| **Connector** | A link to an external tool or data source | Becomes a Quick connection: Settings → Capabilities → Connections. |
| **Plugin** | A bundle of skills, connectors and sub-agents installed together | **No Quick equivalent.** Decomposes into several separate installs. Say so before starting. |
| **Marketplace** | Where plugins are browsed and installed | Quick has a comparable path: skills are published/shared to teammates and browsed under **Agents & skills → Skills → Browse more** ("Shared with you" / "Official"), or shared as `.zip`/`.qplugin` files, or through an org catalog. |

**Why this shape is easier.** A markdown definition is already the same kind of object as a Quick
skill - frontmatter plus a body written for an agent that loads it on demand. There is no instruction
box to transcribe and no persona prose to restructure. Field-for-field:

| Frontmatter key | Quick frontmatter | Effort |
| --- | --- | --- |
| `name` | `name` | kebab-case it; must match the folder name |
| `description` | `description` | near-verbatim - both exist so the model can decide whether to invoke |
| body | body | keep the structure; check for shell commands and untranslatable tools |
| `display_name`, `icon`, `trigger` | same names | port as-is when present, invent when absent |
| `tools` | `tools` | **full name translation** - see `knowledge-and-tools-remap.md` |
| `model` | - | dropped; Quick chooses the model |

**Two things the file will not tell you.** Ask about both:

1. **Knowledge sources.** There is no knowledge field. Grounding came from whatever folders and
   connected tools the host platform had configured around the agent. The file's silence is not
   evidence that there were none.
2. **Assumed tool access.** An agent with no `tools:` key inherited everything its host offered. Read
   the body to work out what it actually needs.
