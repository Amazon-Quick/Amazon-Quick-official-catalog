---
name: skill-architect
display_name: Skill Architect
icon: assets/wrench.svg
description: "Build agent skills for Amazon Quick following skill construction best practices. Use when the user asks to 'build a skill', 'create a skill', 'make a new skill', 'author a skill', 'convert this to a skill', 'save this as a skill', 'test a skill', 'run evals on a skill', 'audit a skill', 'sa help', or wants to turn an agent prompt, workflow, or completed task into a reusable skill."
created_date: "2026-05-21"
last_updated: "2026-10-22"
origin: original
license: "MIT-0"
preferred_model: smart
preferred_thinking: high
tools: [get_current_time, file_read, file_write, folder_create, save_skill, extract_session_data, file_rag_search, web_search, url_fetch, run_python, start_task]
readme: "Read assets/README.md for an overview, installation, and getting started. This skill uses only built-in tools and needs no external connectors."
checksum: "sha256:92f0998987aa40c1478ce5b931b06f85587fc597fea0428e072d0ec41296049e"
---

## Overview

Produces a tested, reusable production ready agent skill.

## Workflow

<Goal>
Produce a skill that is consistent with <Definition - Quick Skills Standard>, testable via <Definition - Evals> and the save_skill / check_skill validators, complete with all necessary components per <Definition - Skill Directory Structure>, and reusable without modification across sessions.
</Goal>

<Definitions>

<Definition - Quick Skills Standard>
The Amazon Quick agent skills standard uses a prescriptive standard for creating a skill directory following prescriptive, prompting, and engineering best practices. We use XML tags to help Quick parse complex prompts unambiguously, especially when your prompt mixes instructions, context, examples, and variable inputs. Each type of content gets its own tag.
</Definition - Quick Skills Standard>

<Definition - Skill Directory Structure>
A skill is a directory containing:

- `SKILL.md`: The only required file. Contains YAML frontmatter (metadata for discovery) and a markdown body (instructions for execution).
- `scripts/`: Executable python or JavaScript code the agent runs during a workflow step. Self-contained, callable, returns a result.
- `references/`: Data the agent reads to make decisions or execute workflows. Example: `references/ticket-routing.md`
- `assets/`: Static resources that shape or appear in the deliverable. Templates the agent fills in, schemas to validate against, images to include. The user receives these. Example: `assets/my-static-data.json`, `assets/README.md`, or `assets/my-skill-icon.svg`.
- `evals/`: Test cases that verify the skill works correctly. Contains evals.json, eval output, and optionally evals/files/ for test input data.
- `assets/README.md`: Optional human-facing overview, pre-requisites, installation, and getting-started. Mandatory when the skill has any dependency (Rule 21). Its presence is signaled by the `readme` frontmatter field.
  </Definition - Skill Directory Structure>

<Definition - Frontmatter>
The YAML block between `---` delimiters at the top of SKILL.md. All possible fields:

- `name` (required): Kebab-case identifier. Lowercase + hyphens only, max 64 chars. Must match directory name.
- `display_name` (optional): Human-friendly name shown in UI.
- `icon` (optional): Emoji identifier. Alternatively, if using Quick you can reference the path to your SVG icon. e.g. `assets/icon.svg`
- `description` (required): Max 1024 chars. What the skill does and when to use it. Imperative phrasing, include trigger keywords. When a user asks what version of the skill they are on, refer them to the last_updated field.
- `created_date` (required): ISO date the skill was first created. Format: YYYY-MM-DD.
- `last_updated` (required): ISO date the skill was last modified. Format: YYYY-MM-DD.
- `tools` (optional): Built-in (system connectors) Amazon Quick tools this skill calls directly (e.g., `file_read`, `web_search`). Anything that needs an external integration (a connector, local MCP, or coding agent) is documented in the README `## Pre-requisites`, not here.
- `readme` (optional): Instruction for the agent about the skill's `README.md`, present only when a README exists. It is the machine-readable signal that the agent must read the README before running, which is mandatory when the skill has any dependency (Rule 21). The README `## Pre-requisites` declares each dependency (type, which connector, cloud or local runtime, required or optional) and `## Installation` points to the reference docs in `<Resources>`. Example: `readme: "Read assets/README.md before running. Its ## Pre-requisites lists required connectors; verify each is available and stop if a required one is missing."`
- `preferred_model` (optional): Recommended model tier: `fast`, `balanced`, `smart`, `auto`. `auto` picks the model and thinking effort for you, so omit `preferred_thinking` with it. If omitted, the skill runs on the user's session tier.
- `preferred_thinking` (optional): Recommended thinking effort: `off`, `low`, `medium`, or `high`. Advisory, like `preferred_model`.
- `checksum` (required): Integrity digest of the skill's core files (SKILL.md, assets/README.md, scripts/, references/, assets/; evals/, tests/, and transient files excluded), in the form `sha256:<hex>`. Generated by `scripts/create_checksum.py` (its single owner), which excludes this line from its own hash so writing it back is idempotent. Regenerated on save; check_skill.py requires it and verifies it is present and well-formed on audit.
- `inputs` (optional): Parameters that vary between invocations. Each input has:
  - `name` (required): identifier used as `{{name}}` placeholder
  - `description` (required): what this input is for
  - `type` (optional): string, url, path, number, choice, boolean
  - `options` (required if type is choice): list of valid values
  - `required` (optional): true/false
  - `default` (optional): value if not provided
</Definition - Frontmatter>

<Definition - Progressive Disclosure>
Skill description loaded at startup for all skills. Full SKILL.md loaded on activation. Other files loaded on demand during execution.
</Definition - Progressive Disclosure>

<Definition - Evals>
The tests that measure whether a skill does its job better than the agent alone. Everything is defined in evals/evals.json. Each eval run appends one line of results to evals/results.jsonl, so scores can be compared over time.

evals.json is a JSON object with:

- `skill_name` (required): name of the skill being tested.
- `settings` (optional): `repeats`, how many times each case runs per configuration. Default 3.
- `targets` (optional): the bars the scorecard reports against. Nothing blocks on them, and the user sets them. Defaults: `pass_rate` 0.9, `min_lift` 0 (judged after the margin of error), `max_regressions` 0, `consistency` 1.0.
- `cases` (required): list of test cases. Each case has:
  - `id` (required): stable kebab-case identifier, never reused.
  - `prompt` (required): a realistic user message. Do not name the skill, so the run shows whether the description triggers it.
  - `should_trigger` (optional, default true): false marks a negative control, a prompt the skill must not activate on. Negative controls run only with the skill, never as a baseline.
  - `replies` (optional): scripted user answers, in order, for the skill's [Ask user] steps, so checks after the first question can be reached.
  - `files` (optional): input files under evals/files/, including canned connector or Quick data responses the run reads instead of calling the live service.
  - `checks` (required): pass/fail checks, written before any run and changed only on purpose. Each has a stable `id`, a `type` (`outcome`: the result is correct; `process`: the right steps happened; `triggering`: the skill activated, or stayed off), and `check` (what to verify).
</Definition - Evals>

<Definition - XML Blocks>
Each block type and what belongs in it. Some carry a "Test:" placement check, a question an author asks to decide whether a piece of content belongs in that block. It is an authoring aid, not something the running agent executes.

- `<Goal>`: Success criteria. Measurable outcomes you could evaluate a run against.
- `<Rules>`: Your behavioral constraints on the agent. Test: "Would the agent's default behavior violate YOUR standards without this?"
- `<Definitions>`: Terms the agent would otherwise misinterpret.
- `<Agent Annotations>`: See <Agent Annotations> for definition
- `<Gotchas>`: Non-obvious environment facts that contradict likely assumptions. Test: "Would the agent make a FACTUAL ERROR without this?"
- `<Instructions>`: Wrapper containing all `<Workflow>` blocks.
- `<Workflow - X>`: Step-by-step procedures using <Agent Annotations> prefixes. Required inline attributes: `description="..."`, `tools=[built_in_tool, ...]`, `triggers=["when X", "when Y"]`. Optional advisory execution hints (guidance to the orchestrating agent, not service-enforced): `background=true` if the workflow's work should run as a spawned task. Test: "Does this tell the agent what to DO in sequence?"
- `<Resources>`: Files and URLs the agent loads on demand, one `<Resource key="...">` entry each. e.g. `<Resource key="amazon-quick-desktop">https://docs.aws.amazon.com/quick/latest/userguide/amazon-quick-desktop.html</Resource>`. Workflow steps cite an entry by key, e.g. `<Resource key="amazon-quick-desktop">`.

**Block ordering (top to bottom):** Goal, Definitions, Rules, Agent Annotations, Gotchas, Instructions (Workflows), Resources (if needed). The agent reads sequentially: context and constraints before procedures, lookup data last.
</Definition - XML Blocks>

<Definition - Description Writing Formula>
Format: [What it does, one sentence] + [Trigger phrases: "Use when asked to..." with 3-6 quoted variations, including the help command `<prefix> help`]. The prefix is the initials of the skill name, e.g. api-design-helper is `adh`.
</Definition - Description Writing Formula>

<Definition - Run Metrics>
Every skill records each workflow run in a local SQLite database with scripts/record_event.py. When the Router dispatches a workflow, record `start` with the skill name, its frontmatter `checksum` as the version, and the workflow name, and keep the printed run_id. When that workflow and any workflow it hands off to are done, record `end` with `completed`, `failed`, or `stopped` and the number of tool calls made. Ask the user once per session where to keep the database file. Metrics never block a workflow: if the user declines or recording fails, continue without them.
</Definition - Run Metrics>

</Definitions>


<Rules>
1. Before acting, read this entire skill. Do not begin until you can confirm you have internalized every line.
2. Every structural choice must trace to <Definition - Quick Skills Standard>, so the skill stays consistent with its own validators and evals.
3. Never one-shot a user-authored skill: present approach options and build with checkpoints, since one-shotting buries mistakes the user cannot catch until it fails in use. Generating a template or scaffold from the standard is the exception. Humans must read and approve the skill, so simplify decisions and don't present the user with walls of text.
4. Description must follow <Definition - Description Writing Formula>. It is the only text loaded at startup, so it alone decides whether the skill triggers.
5. Content in each block must match that block's definition in <Definition - XML Blocks>, with no overlap between blocks. Misplaced content makes the agent miss instructions that are present but in the wrong place.
6. Inputs must only include what genuinely varies between runs; hardcode constants. Parametrizing a constant clutters invocation, and hardcoding a real variable breaks the next run.
7. Show what will be saved before calling save_skill. An explicit save request is itself the approval; do not pause again for a separate confirmation.
8. Cross-reference blocks by their XML tag name (inline) or file path (external), never a vague pointer the agent has to guess at.
9. A skill must be completely self-contained and not rely on a user's specific memories or context unless they agree that the skill is for their own purpose. Nothing is inherited from memories, knowledge graph, or assumed context. If a value isn't written in the skill directory, the skill cannot use it.
10. Every workflow step needs a validation condition and a failure path (inline "If fails:" notation), or the agent cannot tell a step failed and cannot recover.
11. SKILL.md body must stay under 500 lines and focused on logic, since every line is loaded on every run. Keep in SKILL.md what each run needs: the Goal, the Rules (a rule in another file applies only when the agent opens it), and every workflow's steps with their Validate and If fails lines. Move out, in this order: large lookup data (tables, schemas) to `references/`, per-variant detail per Rule 15, templates and examples to `assets/` or `references/`, then a rarely used workflow's detailed method to a reference its steps point to.
12. When a skill depends on a web or local connector (email, calendar, ticketing, messaging): (a) Describe actions in natural language in workflow steps (e.g., "Send an email to the user with the summary"). Do not hardcode connector function names or parameter signatures; they vary across environments and versions. (b) Never store, log, or expose credentials, API keys, or tokens in skill files; authentication is handled by the service. (c) Do not ask users for secrets that come from connector configuration. (d) Determine if there is pagination and how to handle it appropriately.
13. Before finalizing any output, re-read every Rule and verify compliance. If any violation is found, fix it before presenting to the user.
14. Never use code (run_python, regex scripts, or programmatic analysis) to assess a skill's quality, structural coherence, logical flow, voice, or design soundness. Read the full SKILL.md and other files in context and reason about it directly. Code-based tooling is appropriate ONLY for mechanical pass/fail schema checks (frontmatter fields present, tags balanced, character limits). All qualitative judgment must come from reading and thinking, not pattern matching.
15. Design for extensibility and breadth. If a skill handles multiple variations of a task, use a single workflow with a decision point and reference files (like `references/{category}/{name}.md`) rather than enumerating every case inline, so adding a variation means adding a file, not editing SKILL.md. If a skill is over-prescriptive (handles one narrow case when it could serve a broader set), suggest generalizing: a skill for 'weekly team standups' could become 'meeting facilitation' with format references.
16. Never hardcode variables or file paths for skill output. If the skill generates files (reports, exports, templates), ask the user where to save them. An author-specific path fails for everyone else.
17. Design for longevity. Do not depend on tool behaviors, API responses, or library interfaces that are likely to change. Use stable abstractions and natural language descriptions of actions. If something will break when a tool updates, it does not belong hardcoded in the skill.
18. Design multi-step skills to survive conditions the author does not control: long conversations, a weaker model tier, and execution limits. Checkpoint to disk, make steps resumable, write incrementally, and author for a fast-tier model. See `references/resilient-skills.md`. Match the investment to the risk: a long workflow needs this, a short one does not.
19. Before running evals, analyze the skill by reading it in full, never with code. Evals measure behavior, so fixing structural flaws first avoids spending a full run on a known-broken skill.
20. Do not repeat yourself (DRY). State each fact, rule, or instruction once, in the place it belongs, and cross-reference it elsewhere by tag name or file path rather than restating it. This applies within a file and between SKILL.md and its references.
21. When a skill depends on anything beyond built-in tools, it MUST have a README whose `## Pre-requisites` declares each dependency: its type (cloud connector, system tool, local connector, or coding agent), which specific connector (or custom mechanism: custom-remote MCP, OpenAPI, local MCP, or ACP), where it runs (cloud or the user's local machine), and whether it is required or optional. Set the `readme` frontmatter field. Generate a prerequisite-introspection step into the built skill so that, before its main work, the running agent reads the README pre-requisites and verifies each dependency is available: stop on a missing required dependency and link its install reference, note reduced capability for a missing optional one.
22. When generating any code (a skill's scripts/, code shown in examples, or the skill-architect's own scripts), follow the sandbox coding standards in references/quick-sandbox-code-standards.md and the matching language companion (references/python-sandbox-code-standards.md or references/javascript-sandbox-code-standards.md). Verify every imported dependency against references/quick-sandbox-requirements.txt, references/quick-sandbox-package.json, or introspection before using it, since a package absent from the manifest is unavailable in the sandbox.
23. Every file in a skill carries a compliant header per references/reference-file-standard.md: SKILL.md, assets/README.md, and references/*.md in frontmatter, and scripts/*.py in the module docstring, each declaring description, last_updated, and exactly one of source_url or origin. Scaffold new files with the generators (scripts/create_script.py, scripts/create_reference_file.py, scripts/create_readme.py) instead of hand-writing headers, and give every scripts/*.py a filesystem-free unit test in scripts/tests/unit/. check_skill.py enforces the headers, the checksum field, and the other mechanical rules so the standard is validated in code, not by eye.
24. No em dashes in skill output. Use commas, periods, or colons instead.
25. All written content in a skill must be truthful, use natural prose, and never fabricate. Specifically: (a) Do not claim a tool or capability exists unless verified in the session. (b) Do not invent "best practices" or cite sources that weren't consulted. (c) Write in plain, direct language. No filler, no corporate fluff, no AI-sounding hedging. (d) Every factual claim in Rules, Gotchas, or Definitions must be verifiable. If you're not sure something is true, omit it or flag it for the user to confirm.
</Rules>


<Agent Annotations>
Workflow steps are annotated with prefixes that indicate who acts and what happens next:
- [Agent] = Execute using tools. Do not involve the user.
- [Ask user] = Present to user and wait for response before continuing. When the step needs a decision, offer numbered options with the recommended one first and marked "(recommended)", and make the last option "Other", answered by typing its number and the user's own answer (for example, "4 rank it below LOW"). Never leave a decision as an open question when a sensible default exists.
- [Decide] = Evaluate conditions and follow the appropriate branch.
- [Think] = Reason internally, no tools or output. Generate 3+ candidate approaches, score them against <Goal> and <Rules>, pick the best and say why, then pre-mortem it ("what could go wrong, what did I miss?") before continuing.
</Agent Annotations>

<Gotchas>
- The save_skill validator requires `## Overview` and `## Workflow` headings even when using XML scaffold. They're thin wrappers. All XML goes inside `## Workflow`.
- Input placeholders (the `{{ }}` form) trigger validator warnings if declared but not used in the body. For XML scaffold skills, inputs flow in through the workflow steps.
- created_date and last_updated are required by our standard but the save_skill validator does not enforce them. You must set them.
- `run_python` (default 60s) and `run_javascript` (default 30s) stop at their default timeout unless you pass a per-call `timeout`.
- The integration guides index page only shows its guide list in a web browser, so url_fetch sees an almost empty page. Load <Resource key="quick-docs-toc"> instead; it lists every guide.
- To locate lines, blocks, rules, or headings before a surgical edit, run scripts/find_lines.py via run_python instead of reading the whole file or re-deriving line numbers. It is an editing aid, not a workflow tool, so it is not declared in any workflow's tools.
</Gotchas>

<Instructions>

<Workflow - Router
description="Determine what the user needs and dispatch to the correct phase."
tools=[run_python]
triggers=["User asks to build, create, modify, save, test, or audit a skill", "sa help or any sa command"]
>

1. [Decide] What is the user asking?
   Validate: Exactly one path is chosen. If ambiguous, ask user to clarify before proceeding.
   - Create a new skill → <Workflow - Plan>
   - Modify an existing skill → <Workflow - Plan> (load existing skill as context first)
   - Convert a just-completed workflow into a skill → <Workflow - Plan> (use extract_session_data during introspection to pull tools and context from the live session)
   - Continue building a skill already planned → <Workflow - Build>
   - Save a skill that's ready → <Workflow - Save>
   - Test a skill → <Workflow - Eval>
   - Check a skill against the standard → <Workflow - Audit>
   - `sa help`, a bare `sa`, or "what can skill-architect do" → <Workflow - Help>
   - A specific `sa` command dispatches straight to its workflow: `sa plan` → <Workflow - Plan>, `sa build` → <Workflow - Build>, `sa save` → <Workflow - Save>, `sa eval` → <Workflow - Eval>, `sa audit` → <Workflow - Audit>

1. [Agent] Before dispatching, record the run start per <Definition - Run Metrics>.
   Validate: record_event.py printed a run_id, or the user declined metrics.
   If fails: dispatch without metrics.

1. [Agent] When the dispatched workflow, and any workflow it hands off to, is done, record the run end per <Definition - Run Metrics>.
   Validate: record_event.py confirmed the end, or no run was started.
   If fails: continue without metrics.
     </Workflow - Router>

<Workflow - Help
description="Render the skill-architect command menu, or dispatch a specific sa command."
tools=[]
triggers=["sa help", "sa", "User asks what skill-architect can do or how to use it"]
>

1. [Agent] Render <Resource key="help-menu"> populated for skill-architect, then stop and wait for the user's choice. The Router sends only menu requests here (`sa help`, a bare `sa`, or "what can skill-architect do"); a specific `sa` command is dispatched by the Router straight to its workflow.
   Validate: the menu lists every command with a one-line description.
   If fails: re-render from <Resource key="help-menu">.
   </Workflow - Help>

<Workflow - Plan
description="Research, identify requirements, and determine the approach."
tools=[file_read, file_rag_search, web_search, url_fetch, extract_session_data]
triggers=["Create a new skill", "Modify an existing skill", "Convert a workflow into a skill"]
>

1. [Agent] Set the conversation objective with a ready-to-copy `/goal` prompt. From the user's opening description of what they want, draft a one-line objective and output it as a single fenced code block containing only the `/goal ...` line, preceded by exactly one lead-in sentence: "Copy this to set the goal of the conversation (edit as needed):". Output nothing after the code block. `/goal` is Amazon Quick's native command that runs the session in goal-completion mode, so the agent works until the objective is met and self-checks before handing back. If the user opened cold with no description, ask for the objective in one sentence first, then produce the block.
   Example output:
   ```
   /goal Build a skill that <does X> so that <outcome>.
   ```
   Validate: output is one lead-in line plus one code block containing only a `/goal` line; no trailing prose.
   If fails: re-render as the lead-in line plus the code block only.

1. [Ask user] What should this skill do? Accept:

   - A description of the desired behavior
   - An agent prompt to convert
   - A file path to a document or runbook
     Validate: User provides at least one of the above. If vague, ask a clarifying question.
     If fails: Re-ask with examples of each input type.

1. [Agent] If a file path was provided, read it via file_read.
   Validate: File content loaded successfully and is non-empty.
   If fails: Report "file not found" or "file empty" to user and ask for alternative input.

1. [Agent] Introspection. Check what's already available:

   - Tools in the current session (core registry + connected connectors)
   - For each connector the skill will use: introspect its available actions and required parameters. Understand what data the connector needs (recipients, subject lines, body content, channel names, ticket fields, etc.) so the skill collects the right inputs from the user and workflow steps provide sufficient context for the agent to call the connector correctly at runtime. If the connector is not connected in this session, read its docs instead: for a web connector, load <Resource key="quick-docs-toc"> with url_fetch, find the connector under "Integration-specific guides", open its guide, and read the "Available actions" table; for any other type, use its doc in <Resources>.
   - Skills that already exist (could we extend one instead of creating new?)
   - Knowledge graph and memories for prior work on this topic
   - Data sources and integrations the user has access to
     Validate: At least one relevant tool or data source identified. For each connector dependency, the agent can describe what parameters it requires.
     If fails: Note "no existing tools found" and continue. The skill may need new MCPs.

1. [Agent] Public research. Search the web for:

   - Relevant MCPs (local or remote) that might be needed
   - Existing patterns, implementations, or libraries
     Validate: Search returned results (even if none are relevant).
     If fails: Note "no relevant patterns found online" and continue with what's available.

1. [Decide] Are all required tools/MCPs/connectors available?
   Validate: A clear yes/no determination is made for every dependency. For each dependency, record its type, which connector, runtime (cloud or local), and required or optional, so Build can write the README `## Pre-requisites` per Rule 21.

   - All available → continue to presenting findings.
   - Exists but not connected → tell user to enable in Settings. Pause.
   - Doesn't exist → present options: build with placeholder, build the MCP first, or scope to what's available.

1. [Ask user] Present findings: available tools, dependencies identified, any blockers, and whether the planned skill risks the 500-line SKILL.md limit (Rule 11) and what would move out. Confirm direction.
   Validate: User confirms or redirects. Do not proceed without explicit approval.
   If fails: Re-present with simpler summary if user seems confused.

1. [Agent] Suggest 2-3 skill name options. Names must be:

   - Kebab-case per <Definition - Frontmatter>
   - Descriptive of what the skill DOES, not what it's about
   - Short (2-3 words, e.g., `quick-ticket-agent`, `field-signal-harvester`)
     Validate: all names are valid kebab-case per <Definition - Frontmatter>.
     If fails: Regenerate compliant names.

1. [Ask user] Confirm: name, trigger phrase, inputs, dependencies. User always has final say on naming.
   Validate: User explicitly confirms or provides alternatives.
   If fails: Do not assume silence is approval. Re-ask.

1. [Ask user] How do you want to build this?

   - Section by section (review each block together)
   - Draft then review (I write a first pass, we iterate)
     Validate: User picks one approach.
     If fails: Default to "section by section" (safer, more checkpoints).

1. [Agent] Write the description per <Definition - Description Writing Formula>.
   Validate: Description follows <Definition - Description Writing Formula>.
   If fails: Rewrite until it does.

1. [Ask user] Approve description before proceeding to <Workflow - Build>.
   Confirm the description and the planned skill serve the recorded `/goal` objective.
   Validate: Explicit "yes" or equivalent from user.
   If fails: Revise description per user feedback and re-present.
   </Workflow - Plan>

<Workflow - Build
description="Construct the skill section by section or as a draft, per the approach chosen in Plan."
tools=[file_read, file_write, folder_create, get_current_time]
triggers=["Called from <Workflow - Plan> after user approves direction"]
>

1. [Agent] Identify blocks needed from <Definition - XML Blocks>.
   Every skill gets: Goal, Rules, Agent Annotations, Instructions (with at least one Workflow).
   Optional (include only if needed): Gotchas (only when real non-obvious facts exist, do not invent filler), Definitions, Resources.
   Validate: The 4 required blocks are present, each optional block included only when it earns its place.
   If fails: Cross-reference <Definition - XML Blocks> and add missing blocks.

1. [Agent] Implicit assumptions audit. Scan every workflow step and ask: "Does this reference a value that only works in the skill author's environment?" Catch ALL of:

   - File/folder paths (Obsidian vaults, output directories, config locations)
   - URLs and endpoints (dashboards, wikis, internal tools)
   - Channel/group names (Slack channels, Teams groups, distribution lists)
   - People/team names and aliases
   - Routing tables, category lists, priority tiers
   - Tool configurations or API-specific values
   - Vague integration references (e.g., "send a notification" without specifying which integration or what data to include in the message)
   - Hardcoded output file paths (see Rule 16)
   - Over-prescriptive scope (see Rule 15)
   - Brittle tool/API dependencies (see Rule 17)
     For each one found: it MUST be placed in `<Definitions>` (short values), `<Resources>` (lookup tables), `references/` (large datasets), or an input (a value that changes between runs, per Rule 6, including output paths per Rule 16). No value that varies by environment or breaks over time can appear only inside a workflow step.
     Validate: Produce a list of all findings with proposed placement. Include any extensibility or longevity concerns.
     If fails: Re-scan. If truly none found, document "no issues detected" and continue.

1. [Ask user] Present the list of environment-specific values discovered. Confirm each value and where it should live (Definitions, Resources, references/ file, or an input).
   Validate: User confirms every value's placement.
   If fails: Adjust placement per user feedback and re-confirm.

1. [Agent] Identify supporting files per <Definition - Skill Directory Structure>:

   - Lookup tables, routing maps, URL lists → `references/`
   - Templates, schemas, static resources → `assets/`
   - Executable helper scripts → `scripts/`
   - Everything else stays in SKILL.md body
     Validate: Every file is assigned to exactly one directory.
     If fails: Re-categorize using the taxonomy test for each directory type.

1. [Agent] Write the SKILL.md body: `## Overview`, then `## Workflow` holding the blocks in the canonical order from <Definition - XML Blocks>. For a minimal complete example, read <Resource key="example-skill">.
   Validate: `## Overview`, `## Workflow`, and the 4 required blocks are present, any blocks in canonical order, body under 500 lines.
   If fails: Remove redundancy, then move content out in the order Rule 11 gives until under the limit.

1. [Agent] Write supporting files per <Definition - Skill Directory Structure>. Any code written (scripts, example snippets) follows the sandbox coding standards per Rule 22.
   Scaffold every reference file and script with the generators per `references/reference-file-standard.md` so each carries a compliant header.
   Validate: Each file exists at its declared path and is non-empty, each carries a compliant header per `references/reference-file-standard.md`, and any generated code follows references/quick-sandbox-code-standards.md and its language companion with every import present in the applicable manifest.
   If fails: Regenerate missing files or correct code that violates the sandbox standards.

1. [Decide] Does the skill depend on anything beyond built-in tools?
   - No: the README is optional. Offer one, then continue.
   - Yes: scaffold the README with scripts/create_readme.py, fill `## Pre-requisites` per Rule 21, set the `readme` frontmatter field, point `## Installation` at the `<Resources>` docs, and generate a prerequisite-introspection step as the skill's first workflow action.
   Validate: every dependency appears in `## Pre-requisites`, `readme` is set, and a prerequisite step exists that introspects each dependency and links the install reference for missing required ones.
   If fails: add the missing README section, `readme` field, or prerequisite step, then re-check.

1. [Agent] Generate the skill's help menu. Use the command prefix from <Definition - Description Writing Formula>. Map a command (`<prefix> <verb>`) to each user-invocable workflow, plus `<prefix> help`. Write a <Workflow - Help> into the built skill that renders <Resource key="help-menu"> populated with these commands, and wire the commands into the built skill's <Workflow - Router> and its triggers: menu requests (`<prefix> help`, a bare `<prefix>`) route to <Workflow - Help>, and each `<prefix> <verb>` routes straight to its workflow.
   Validate: the built skill has a <Workflow - Help>, a `<prefix> help` command, one command per user-invocable workflow, and its Router dispatches each `<prefix> <verb>` to the matching workflow.
   If fails: add the missing help workflow, commands, or router entries, then re-check.

1. [Agent] Add run metrics to the built skill: copy scripts/record_event.py into its scripts/, copy <Definition - Run Metrics> into its Definitions, and add the record-start and record-end steps to its Router (with run_python in the Router's tools).
   Validate: the built skill has scripts/record_event.py, the definition, and Router steps that record the start and the end.
   If fails: add the missing piece, then re-check.

1. [Think] Writing quality review. Read through all written content (Goal, Rules, Gotchas, Definitions, descriptions) and check:

   - Verify Rule 25 compliance: every factual claim verifiable, prose natural and direct, no invented "best practices" or uncited sources.
   - Do Rules state clear prohibitions, not vague aspirations?
   - Do Gotchas state surprising facts, not obvious things dressed up as warnings?

1. [Agent] Present full preview (SKILL.md + file tree) to user.
   Validate: Preview shows the complete SKILL.md content plus all supporting file paths.
   If fails: Ensure nothing was omitted. Re-present.

1. [Decide] User approves → proceed to <Workflow - Save>. User wants changes → adjust and re-preview.
   Validate: Clear approval signal from user.
   If fails: Ask "What would you like me to change?" and loop back to relevant step.
   </Workflow - Build>

<Workflow - Save
description="Persist the skill directory and set metadata."
tools=[get_current_time, save_skill, file_read]
triggers=["Called from <Workflow - Build> after user approves preview", "User asks to save an existing skill draft directly"]
>

1. [Agent] If the skill was not built in this session (the user pointed at an existing draft), read that draft via file_read and show its content as the preview. An explicit save request is the approval per Rule 7, so continue without pausing.
   Validate: The SKILL.md content to save is loaded, from this session's Build or the provided draft.
   If fails: Ask the user for the draft path.

1. [Agent] Get current date via get_current_time.
   Validate: Date returned in ISO format.
   If fails: Use today's date from context as fallback.

1. [Agent] Set created_date (if new skill) and last_updated (always) in frontmatter.
   Validate: created_date and last_updated are set.
   If fails: Re-set manually.

1. [Agent] Call save_skill with the SKILL.md content and every companion file bundled in its `scripts` parameter as `{"filename": "<skill-relative path>", "code": "<contents>"}` (for example `scripts/analyze.py`, `references/routing.md`, `assets/template.json`). Bundling is the only way to write a skill's companion files: generic file_write into the skills directory is blocked. A bare filename lands under `scripts/`; a relative path is preserved at that path.
   Validate: save_skill returns success and reports the bundled files as written.
   If fails: Check for validator errors (missing ## Overview or ## Workflow, a hallucinated tool, or an absolute or `..` filename that rejects the whole save). Fix and retry once.

1. [Agent] Regenerate the skill's checksum: run scripts/create_checksum.py so the stored `checksum` reflects the final files. Do this after all files are written and before the audit, so the audit sees a current checksum.
   Validate: create_checksum.py exits 0 and the `checksum` field is present in SKILL.md.
   If fails: re-run once; if it still fails, report the error to the user.

1. [Agent] Run <Workflow - Audit> automatically.
   Validate: Audit returns zero issues.
   If fails: Fix reported issues and re-audit until clean.

1. [Ask user] Generate eval test cases via <Workflow - Eval>?
   Validate: User responds yes or no.
   If fails: Default to generating evals (better to have them).
   </Workflow - Save>

<Workflow - Eval
description="Measure a skill against the agent alone: run fixed checks with and without the skill, grade them, and score the results over time."
tools=[file_read, file_write, run_python, start_task, get_current_time]
triggers=["User asks to test a skill", "Called from <Workflow - Save>"]
>

1. [Agent] Read the target SKILL.md and `references/evals.md`.
   Validate: SKILL.md loaded, at least one <Workflow> found, and evals.md read.
   If fails: Check the path. If the skill is not saved yet, run <Workflow - Save> first.

1. [Agent] Write or update evals/evals.json per <Definition - Evals> and `<step-1-define>` in evals.md, with fixed checks for every user-invocable workflow and at least one negative control.
   Validate: evals.json parses, and every case and check has an id.
   If fails: Fix the JSON and re-write.

1. [Ask user] Review the cases, checks, and targets. Add, remove, or adjust before any runs?
   Validate: User confirms or provides edits.
   If fails: Apply edits and re-present.

1. [Agent] Analyze before running (Rule 19). Read the full SKILL.md and reason directly, no code, about structure, step order, claim verifiability, and voice. Fix what you find before spawning any runs.
   Validate: Analysis is written and any blocking issues resolved.
   If fails: Resolve the issues. If the skill needs a rewrite, return to <Workflow - Build> first.

1. [Agent] Run every case per `<step-2-run>` in evals.md, then grade every run per `<step-3-grade>`.
   Validate: Every run has outputs, metrics.json, and a grading.json with a verdict for each check id.
   If fails: Re-run or re-grade the missing runs. If a task errored, read its result and report before continuing.

1. [Agent] Score the iteration per `<step-4-score>` in evals.md, then read the results per `<reading-the-results>`.
   Validate: create_benchmark.py appended a line to evals/results.jsonl and printed the scorecard, and each note names a case or check with a number.
   If fails: Fix the run folders the script reported, then re-run it.

1. [Ask user] Present the scorecard and notes. Change the skill, keep it, or add cases?
   Validate: User picks a direction.
   If fails: Summarize the results plainly and re-ask. Iteration reruns this workflow, comparing against the last saved result.
   </Workflow - Eval>

<Workflow - Audit
description="Check a skill against the Quick Skills standard."
tools=[file_read, run_python]
triggers=["User asks to audit a skill", "Called from <Workflow - Save>"]
>

1. [Agent] Load the target skill via file_read.
   Validate: SKILL.md content loaded and non-empty.
   If fails: Check path. If skill doesn't exist, inform user.

1. [Agent] Run scripts/check_skill.py via run_python for all mechanical checks (its docstring lists them), which now include checksum integrity (it recomputes the digest and FAILs on mismatch) and non-blocking staleness WARNINGs. This is the mechanical half only (Rule 14); the checks below are qualitative and done by reading.
   Validate: check_skill.py exits 0. Staleness WARNINGs do not affect the exit code and are handled in the staleness step below.
   If fails: Fix each reported failure and re-run until it exits 0. A checksum-mismatch FAIL means files changed without regenerating, so run scripts/create_checksum.py, then re-run.

1. [Agent] Check directory structure against <Definition - Skill Directory Structure>.
   Validate: No files in wrong directories. evals/ exists.
   If fails: Log misplaced files as issues.

1. [Agent] Check dependency documentation. Determine whether the skill uses anything beyond built-in tools (inspect workflow steps and tools for connectors, MCP, or coding agents).
   Validate: if it has any dependency, README.md exists with a `## Pre-requisites` section declaring each dependency (type, which connector, runtime, required or optional), the `readme` frontmatter field is set, and `## Installation` points to reference docs rather than copying them. If it has no dependency, no README is required.
   If fails: Log the missing README, `## Pre-requisites` entries, `readme` field, or copied-documentation violation as an issue with the fix.

1. [Decide] Review staleness from check_skill.py, which flags SKILL.md and any assets/README.md, references/*.md, or scripts/*.py that is stale per the staleness rule in `references/reference-file-standard.md`.
   Validate: a branch is chosen for the reported staleness WARNINGs (none, SKILL.md, or a reference/script file).
   - None → the skill is current; continue.
   - SKILL.md stale → recommend a full re-evaluation via <Workflow - Eval> and a review of every Rule, Gotcha, and workflow step against the current standard.
   - A reference or script stale → regenerate each file that has a `source_url` from that source, and review each `origin: original` file by hand.
   After refreshing any file, bump its `last_updated` and rerun <Workflow - Save> so the checksum is regenerated.
   If fails: if the warnings are unclear, list the flagged files and ask the user how to proceed.

1. [Agent] Check each XML block's content against its definition in <Definition - XML Blocks>.
   Validate: Each block's content matches its definition. No content in wrong blocks.
   If fails: Log misplaced content with recommendation for correct block.

1. [Agent] Report findings: pass/fail per check, specific issues to fix.
   Validate: Report contains at least one finding per check category (even if "pass").
   If fails: Re-run checks that produced no output.

1. [Decide] Issues found → present fixes to user. No issues → report clean.
   Validate: Clear resolution: either fixes presented or clean bill of health.
   If fails: Summarize ambiguous findings and ask user for guidance.
   </Workflow - Audit>

</Instructions>

<Resources>
<Resource key="example-skill">references/example-skill.md</Resource>
<Resource key="help-menu">assets/help-menu.md</Resource>
<Resource key="connectors-overview">https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html</Resource>
<Resource key="connector-setup-guides">https://docs.aws.amazon.com/quick/latest/userguide/integration-guides.html</Resource>
<Resource key="quick-docs-toc">https://docs.aws.amazon.com/quick/latest/userguide/toc-contents.json</Resource>
<Resource key="custom-mcp-integration">https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html</Resource>
<Resource key="openapi-integration">https://docs.aws.amazon.com/quick/latest/userguide/openapi-integration.html</Resource>
<Resource key="coding-agents">https://docs.aws.amazon.com/quick/latest/userguide/coding-agents.html</Resource>
<Resource key="install-a-skill">https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html</Resource>
</Resources>
