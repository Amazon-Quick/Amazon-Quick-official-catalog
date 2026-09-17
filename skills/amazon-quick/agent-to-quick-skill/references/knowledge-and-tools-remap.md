---
description: "Decision procedure for remapping knowledge sources and capabilities that cannot be ported directly, including when to connect natively versus copy files locally."
last_updated: 2026-09-08
origin: original
---

# Remapping knowledge sources and capabilities

This is the part of a conversion that cannot be automated. Resolve **every** row before writing
`SKILL.md`. An unresolved knowledge source produces a skill that runs and silently returns nothing.

## Decision procedure, per source

**Connect natively before you move anything.** Quick reaches document libraries and cloud file storage
through connectors and spaces. The right answer for a source that lives in one of those is to reference
it *where it already is*, by link, through a connection - not to copy it. Copying is the last resort,
and the ordered landing-spot list in `SKILL.md` Step 3 is the authority on precedence.

For each source knowledge item, ask in this order:

1. **Which instruction step consumes it?** If none does, drop it - conversational authoring modes
   add sources speculatively and they often go unused.
2. **Where does it live, and is that system connectable?** A document library, intranet site, cloud
   drive, mailbox, chat platform or ticketing system → a **connection**, or a knowledge base in a space.
   Ask whether the connection already exists before proposing anything else.
3. **Does the content change?** Changing (a live site, a ticket queue, a document under active
   revision) → connection or knowledge base, which stay in sync. Static and small (a rubric, a
   template, a fixed list) → a bundled reference file is acceptable.
4. **How much is there?** A few files → connection, or a local folder if already synced. A corpus →
   knowledge base in a space.
5. **Is it Red Data / HIPAA / PII?** → **Hard stop.** Amazon Quick desktop is rated Highly
   Confidential and is not Red Data certified. Do not connect it. Record as dropped, with the reason.
6. **Is the user willing to set up the prerequisite?** If not, record as dropped and list it in the
   final report. Do not pretend it ported.

### Extra questions when the source is a link

Authoring UIs commonly accept a URL as a knowledge source ("Enter a link"). A link is not an uploaded
file, and the whole point of a link is that the content stays where it is. Two questions place it:

1. **One document, or a whole site or library?** A single document in a connectable system → reference
   it by link through the connection. A library or site → knowledge base in a space, configured on Quick
   **web**. If it is a library, revisit the destination decision: a skill cannot create the space it
   needs.
2. **Public, or permission-controlled?** The built-in browsing skill reads public URLs and **cannot
   authenticate** to a permissioned one. Do not offer browsing as a substitute for a connection, and do
   not read a sign-in page as the document's content.

Sharing was already settled in `SKILL.md` Step 1, Decision A, so do not re-ask it - just record the
consequence: a link resolves only for someone who already has access, and a recipient without it gets
an empty result that looks identical to a broken skill. Put the access requirement in
`## Prerequisites` and say so in the final report.

### Do not resolve a link by downloading it

When a fetch of a permissioned link fails at the sign-in wall, the correct next move is **add the
connection**, not "ask the user to download the file and hand it over". The failure is evidence about
the source, not a transient error. Handing the download back to the user is worse on four counts:

- **It freezes the content** at the moment of download, while the original keeps changing.
- **It breaks sharing** - a connection resolves per-person against real permissions; a copy resolves for
  whoever holds the copy.
- **It is manual work**, repeated on every update.
- **It can move data out of its permission boundary**, which is usually the reason the document lived in
  a managed library in the first place.

Fall back to a local or bundled copy only when no connector exists for that system, or the user declines
to add one. **Any copy is a snapshot.** The body will present it as current indefinitely. Date it, mark
it as a snapshot in the file itself, and name the staleness in the report. This is the decision the
"Changes?" column exists to force - a link is almost always the "changing" answer, which makes copying a
deliberate trade, never the default.

## Knowledge sources

Rows are in preference order where more than one option is listed. Take the first that fits.

| Source knowledge item | Amazon Quick equivalent | Where the user sets it up | Notes |
| --- | --- | --- | --- |
| Managed document library / intranet site (changing) | Knowledge base in a space; or a connection to the library | Quick web → space → knowledge base; then assign the space. Connections: Settings → Capabilities → Connections | Closest thing to a true port. Index stays in sync. Confirm the source type is on the current supported list in the console. |
| Individual documents from a library | **Connection to the library, referenced by link.** Bundle in `references/` only if no connector exists | Settings → Capabilities → Connections; `references/` next to `SKILL.md` as the fallback | Do **not** download-and-bundle by default. A bundled copy is a dated snapshot and breaks per-person access. Bundling is right only for small static material the user owns - a rubric, a template, a fixed list. |
| Cloud drive folder | Connection to the drive; or a local folder if it is already synced to disk | Settings → Capabilities → Connections; Settings → My computer → Local folders | An already-synced folder is fine - it keeps updating. A fresh manual download is not the same thing. |
| Public website / URL | Built-in web browsing skill; or a web-crawler knowledge base for a whole site | Built-in; crawler in a space | One-off reads → browsing. Repeated grounding → crawler. |
| **Permissioned link** to a document or library | **Connection to that system** (single document, referenced by link) or knowledge base in a space (library). Local/bundled copy only as a last resort | Settings → Capabilities → Connections; Quick web for a knowledge base | Browsing **cannot** authenticate to it - a sign-in wall means "add the connection", not "download it". Access is per-recipient, so a copy breaks shareability. See "Do not resolve a link by downloading it". |
| The user's mailbox | Mail connection | Settings → Capabilities → Connections | Genuinely equivalent - Quick desktop reads mail and calendar. |
| Team chat messages | Chat connection, where available on their build | Settings → Capabilities → Connections | Confirm availability on their build rather than assuming; otherwise drop. |
| Enterprise search connector over an external system (ticketing, ITSM, wiki, …) | MCP server, or an action connector from the system's API specification | Settings → Capabilities → Connections | Not a port - a rebuild. Check whether an internal MCP server already exists before building one. |
| Structured business data | Structured data connection (Quick Sight side) | Quick web | Only if the agent genuinely did analytics. Otherwise usually over-engineering. |
| Anything with no equivalent | **Dropped** | - | Name it in the final report, with what the skill will do wrong without it. |

## Capabilities

| Source capability | Amazon Quick equivalent | Notes |
| --- | --- | --- |
| **Code execution / interpreter** ("create documents, charts, and code") | Built-in code execution + document creation skills | **Strictly more capable** - real local filesystem, no sandbox upload/download dance. Tell the user this is an upgrade, not a substitution. |
| **Image generation** ("create images") | Built-in image generation skill | Direct equivalent. |
| Web search grounding | Built-in web browsing skill | Browser-based skills require Chrome with your organization's SSO / authenticated access for internal sites. |
| API action / plugin defined by a specification | Action connector built from **the same specification**, or an MCP server | Reuse the spec file. Do not reimplement the API by hand. |
| A nested sub-agent | A separate Quick skill, or a scheduled task | No nesting equivalent; split it. |

Built-in Quick skills cover document creation, web browsing, image generation, code execution,
knowledge graph management, agent orchestration and transcription. Check the live list at
**Agents & skills → Skills → BUILT-IN SKILLS** before deciding something needs building.

## The `tools:` frontmatter list

`tools:` names the tools the skill is allowed to use. Getting a name wrong is worse than omitting
the field, because the skill will load and then fail mid-workflow.

**Syntax:** a single-line inline array - `tools: [file_read, file_write, run_python]`. Names
unquoted.

**Verify against the build you are installing into**, rather than trusting any list including this
one. Tool names move between releases. The fastest verification is to read what the already-installed
skills declare:

```
grep -h '^tools: \[' ~/.quickwork/profiles/<profile>/skills/*/SKILL.md \
  | sed 's/^tools: \[//; s/\]$//' | tr ',' '\n' | sed 's/ //g' | sort -u
```

Vocabulary observed across installed skills, grouped by what it is for. Use these as the candidate
set, then confirm with the command above:

| Purpose | Tool names |
| --- | --- |
| Files | `file_read`, `file_write`, `file_edit`, `file_copy`, `file_move`, `file_delete`, `open_file` |
| Typed file reads | `file_read_pdf`, `file_read_docx`, `file_read_pptx`, `file_read_image`, `file_get_page_raster` |
| Folders and search | `folder_list`, `folder_create`, `fdfind`, `ripgrep`, `file_rag_search` |
| Code execution | `run_python`, `run_python_with_write`, `run_javascript` |
| Session UI | `open_in_session_tab`, `list_session_tabs`, `extract_session_data` |
| Web | `web_search`, `url_fetch`, `browser_navigate`, `browser_click`, `browser_type`, `browser_extract_text`, `browser_run_js`, `browser_wait`, `browser_screenshot`, `browser_scroll`, `browser_batch` |
| Mail and calendar | `email_search`, `email_read`, `email_send`, `email_folders`, `calendar_meeting` |
| Chat | `search_messages`, `conversations_history`, `conversations_replies`, `conversations_add_message` |
| Knowledge graph | `kg_search` |
| Tasks and orchestration | `start_task`, `create_task_group`, `get_task_group_result`, `send_message_to_acp_agent` |
| Skill authoring | `save_skill`, `load_skill_for_improvement`, `generate_skill_evals`, `load_tools` |
| Misc | `get_current_time`, `use_computer` |

### Translating a markdown definition's `tools:` list

When the source is a markdown definition (Step 2, Path C), it already declares `tools:` - but in a
different vocabulary. This is the bulk of the conversion work. `scripts/parse_manifest.py` emits this
mapping automatically in intake section 5; the table below is the same mapping for hand conversions.

| Source tool | Quick equivalent | Watch out for |
| --- | --- | --- |
| `Read` | `file_read` | typed variants exist: `file_read_pdf`, `file_read_docx`, `file_read_pptx`, `file_read_image` |
| `Write` | `file_write` | - |
| `Edit` / `MultiEdit` | `file_edit` | one Quick tool covers both |
| `NotebookEdit` | `file_edit` | no notebook-aware editing; plain text edits only |
| `LS` | `folder_list` | - |
| `Glob` | `fdfind`, `folder_list` | `fdfind` for patterns, `folder_list` for a plain listing |
| `Grep` | `ripgrep` | - |
| `WebSearch` | `web_search` | - |
| `WebFetch` | `url_fetch` | - |
| `TodoWrite` | `add_todo`, `list_todos`, `complete_todo` | one source tool splits into several |
| `Task` / sub-agent dispatch | `start_task`, `create_task_group`, `get_task_group_result` | **not** like-for-like; confirm the orchestration behaviour survives |
| `Bash` | `run_python` | **no general shell.** See below. |
| `BashOutput`, `KillShell` | none | background-process control has no equivalent |
| `SlashCommand` | none | inline the workflow instead |
| `AskUserQuestion` | none | Quick asks in chat prose instead |
| `ExitPlanMode` | none | state the plan in prose and wait for a reply |
| `browser_*`, `mcp__*` | possibly the same name | verify - do not assume |

**The shell is the trap.** `Bash` → `run_python` looks like a clean swap and is not. A source agent
with shell access usually has shell commands *in its body* - `./scripts/build.sh`, a pipeline of
`grep | sort`, a `curl`. Those steps will not run. Audit the body for every shell invocation and
rewrite it as Python or as explicit prose instructions. A converted agent that fails three steps in,
having looked fine at load time, is almost always this.

**A tool with no equivalent is a body-rewriting job, not a frontmatter job.** Find where the body
uses it and change that step. Report it as dropped. Never substitute a different tool and hope.

- **Declare only what the workflow actually uses.** A long speculative list widens the skill's
  permissions for no benefit.
- **If a name cannot be verified, omit it** and describe the capability need in prose in the body.
  Quick auto-selects built-ins by relevance, so a prose description degrades gracefully. A bad tool
  name does not.
- **Never author `id:`.** Some installed skills carry a 32-hex `id:`; Quick assigns it. Writing one
  by hand risks colliding with an existing skill's identity.

## Prerequisites section

Every remap that needs setup becomes a line in the skill's `## Prerequisites`, written so a
recipient who is not the author can act on it:

```markdown
## Prerequisites
1. Amazon Quick desktop app (macOS or Windows) - skills do not run on web.
2. <Connector> connected: Settings → Capabilities → Connections.
3. A local folder added under Settings → My computer → Local folders, containing:
   - <file> (<format>) - <what it is>
```

Do not hardcode absolute paths or user-specific references in the skill body - it makes the skill
unshareable. Take the folder as an input, or state the convention in Prerequisites.
