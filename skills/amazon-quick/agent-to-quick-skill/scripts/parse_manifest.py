#!/usr/bin/env python3
"""
description: Parse an agent or skill definition into an Amazon Quick conversion intake. Extracts the fields that port mechanically and emits an explicit TODO for every knowledge source and capability that needs a human decision. Never invents an Amazon Quick equivalent.
last_updated: 2026-09-08
origin: original

Two input shapes are detected automatically:

  JSON     -- a declarative agent config exported from a low-code authoring UI. Instructions live
              in an `instructions` key; grounding lives in `capabilities` / `actions`.
  Markdown -- a definition file with YAML frontmatter and a prose body, as used by agent
              definitions (`agents/<name>.md`) and skill definitions (`SKILL.md`) on
              filesystem-based platforms. The body IS the instructions, and `tools:` names the
              capabilities. These convert more directly, because the source object already has the
              same shape as a Quick skill.

Usage:
    python3 parse_manifest.py agent.json  [--out intake.md] [--json]
    python3 parse_manifest.py agent.md    [--out intake.md] [--json]
    python3 parse_manifest.py agent.json --wrapper app-manifest.json

Platform-neutral by design. Capability entries are classified by inspecting the identifier the
input file happens to use -- there is no hardcoded vendor lookup table, so unfamiliar platforms and
schema versions still classify usefully. Identifiers are echoed back verbatim as opaque data, and
anything the classifier is unsure of is reported as UNCLASSIFIED rather than dropped.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Substring hints -> (bucket, generic gloss). Checked in order against a lowercased identifier.
# These are shape heuristics over whatever the input file calls things, not a vendor mapping.
HINTS = [
    ("interpreter", "capability", "Code execution / interpreter"),
    ("code", "capability", "Code execution / interpreter"),
    ("image", "capability", "Image generation"),
    ("graphic", "capability", "Image generation"),
    ("art", "capability", "Image generation"),
    ("mcp", "capability", "MCP server tools"),
    ("agent", "capability", "Nested sub-agent"),
    ("search", "knowledge", "Web or enterprise search grounding"),
    ("web", "knowledge", "Public web content"),
    ("mail", "knowledge", "The user's mailbox"),
    ("message", "knowledge", "Team chat messages"),
    ("chat", "knowledge", "Team chat messages"),
    ("connector", "knowledge", "Indexed external system (ticketing, ITSM, wiki, ...)"),
    ("index", "knowledge", "Indexed external system"),
    ("site", "knowledge", "Managed document library / intranet site"),
    ("point", "knowledge", "Managed document library / intranet site"),
    ("drive", "knowledge", "Cloud file storage"),
    ("file", "knowledge", "Files or documents"),
    ("doc", "knowledge", "Files or documents"),
    ("people", "knowledge", "People / org graph"),
    ("person", "knowledge", "People / org graph"),
    ("data", "knowledge", "Structured business data"),
]

KNOWN_TOP_LEVEL = {
    "$schema",
    "version",
    "id",
    "name",
    "description",
    "instructions",
    "conversation_starters",
    "conversationStarters",
    "starter_prompts",
    "capabilities",
    "actions",
    "behavior_overrides",
    "behaviorOverrides",
}

KNOWN_FRONTMATTER = {
    "name",
    "description",
    "tools",
    "model",
    "display_name",
    "icon",
    "trigger",
    "allowed-tools",
    "allowed_tools",
    "license",
    "version",
    "argument-hint",
}

# Tool-name translation for markdown-sourced definitions. Filesystem-based agent platforms and
# Amazon Quick both declare tools in frontmatter, but the vocabularies are disjoint -- so this is
# the bulk of the real work when converting a markdown agent, and getting it wrong is silent.
#
# Keys are lowercased source tool names. Values are (quick_names, note). An empty quick_names list
# means "no equivalent" -- report it, never guess a substitute.
TOOL_MAP = {
    "read": (["file_read"], ""),
    "write": (["file_write"], ""),
    "edit": (["file_edit"], ""),
    "multiedit": (["file_edit"], "one Quick tool covers both single and batch edits"),
    "notebookedit": (
        ["file_edit"],
        "no notebook-aware editor in Quick; plain file edit only",
    ),
    "ls": (["folder_list"], ""),
    "glob": (
        ["folder_list", "fdfind"],
        "`fdfind` for pattern matching, `folder_list` for a plain listing",
    ),
    "grep": (["ripgrep"], ""),
    "websearch": (["web_search"], ""),
    "webfetch": (["url_fetch"], ""),
    "todowrite": (
        ["add_todo", "list_todos", "complete_todo"],
        "one source tool splits into several in Quick",
    ),
    "task": (
        ["start_task", "create_task_group", "get_task_group_result"],
        "sub-agent dispatch; verify these exist on the build",
    ),
    "agent": (
        ["start_task", "create_task_group", "get_task_group_result"],
        "sub-agent dispatch; verify these exist on the build",
    ),
    "bash": (
        ["run_python"],
        "NO general shell in Quick. Rewrite shell steps as Python, or as explicit prose instructions. Do not assume a shell is available.",
    ),
    "bashoutput": ([], "background-process polling has no Quick equivalent"),
    "killshell": ([], "background-process control has no Quick equivalent"),
    "slashcommand": (
        [],
        "no slash-command dispatch in Quick; inline the workflow instead",
    ),
    "askuserquestion": (
        [],
        "no structured question tool; Quick asks in chat prose instead",
    ),
    "exitplanmode": (
        [],
        "no plan-approval gate; state the plan in prose and wait for a reply",
    ),
}

# Printed above every knowledge-source table. The order matters: the link is what the source
# platform's Knowledge section actually holds, and the local path is the fallback users forget
# they have. One question per message -- a batch gets a partial answer.
ASK_SEQUENCE = """**Connect natively first - a download is the last resort.** Quick reaches document libraries and
cloud file storage through connectors and spaces, so reference a source *where it already lives*.

**Per source, ask these one message each, and stop as soon as one resolves it:**

1. *"Can you paste the link to it?"* The Knowledge section holds links into a shared document library
   or site rather than uploaded copies, so the link is what exists. Ask for it exactly as it appears.
2. *"Is that library already connected under Settings → Capabilities → Connections?"* If yes, you are
   done - reference it by link and record the connection as the prerequisite. If no, ask whether they
   can add it. **This is the question that prevents an unnecessary download.**
3. *"Is there a copy on your machine, or is that library synced to disk?"* Only if no connector exists
   or the user declines one. A synced folder keeps updating; a fresh manual download does not.

A sign-in wall on a link means **add the connection**, not "download the file and send it to me" - the
failure is a fact about the source, not a transient error. Any copy you do end up taking is a dated
snapshot: record the date and name the staleness in section 7. If nothing resolves the source, mark the
row `dropped` with its consequence. Confirm any local path sits inside a connected folder; if not, say
so and name the menu: **Settings → My computer → Local folders → Add folder**.
"""

DESTINATION_BLOCK = """## 0. Destination - settle this before anything else

**Two independent decisions. Do not let the second answer the first.** "No ordered steps in the source"
decides only whether the output has a `## Workflow Steps` section. It says nothing about skill vs agent
vs `AGENTS.md` - a persona of pure guidelines is the *most* likely thing to want to be a shared agent.

**Decision A - destination.** Determined by who uses it, where they need it, and how it is invoked.
Any single agent signal wins; do not average the answers.

| Question | Answer | Points to |
| --- | --- | --- |
| Just for you, or will the team use it? | **TODO** | team → **agent** |
| Desktop only, or also web / mobile / browser / chat platform? | **TODO** | beyond desktop → **agent** |
| Always on, or invoked deliberately? | **TODO** | always → **`AGENTS.md`**; invoked → **skill** |
| A few stable documents, or a large changing corpus? | **TODO** | changing corpus → **agent + space** |

**Put the shape in front of the user as a pick-one list before building anything.** Your recommendation
is not the confirmation. Name the surface in each option, and include any MCP server or connection the
data needs - on AWS an MCP server for a system of record can be hosted on Bedrock AgentCore.

| Option offered | Text used |
| --- | --- |
| Desktop shape - **skill** (+ MCP server / connection if a system of record is involved) | **TODO** |
| Web shape - **agent + space** (+ the same data component) | **TODO** |
| **Explain the tradeoffs** first | **TODO** |

- Chosen destination: **TODO** - `skill` / `agent + space` / `AGENTS.md` / split
- The user picked it from the list: **TODO** - yes / no
- Data component in the chosen shape: **TODO** - none / connection / space knowledge base / MCP server

**Decision B - shape.** Does the source contain an ordered procedure? **TODO** - yes → write
`## Workflow Steps`; no → omit it and record that as a deliberate finding in section 7.
"""


def classify(identifier):
    low = (identifier or "").lower()
    for needle, bucket, gloss in HINTS:
        if needle in low:
            return bucket, gloss
    return "unclassified", "UNCLASSIFIED -- inspect manually and place by hand"


def translate_tool(source_name):
    """Map one source tool name to (quick_names, note). Never guesses a substitute."""
    key = (source_name or "").strip().strip("\"'").lower()
    if key in TOOL_MAP:
        return TOOL_MAP[key]
    if key.startswith("browser_") or key.startswith("mcp__"):
        return (
            [source_name],
            "same name may exist in Quick -- VERIFY against the build",
        )
    return (
        [],
        "UNRECOGNISED -- find the Quick equivalent by hand, or drop the capability",
    )


def parse_frontmatter(text):
    """Parse a YAML-frontmatter document into (mapping, body).

    Deliberately a small YAML subset -- scalars, quoted scalars, inline arrays, block lists and
    folded/literal blocks -- so the script has no third-party dependency. Anything it cannot parse
    is kept as a raw string rather than dropped.
    """
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    block, body = m.group(1), m.group(2)

    data, key, mode, buf = {}, None, None, []

    def flush():
        if key is None:
            return
        if mode == "list":
            data[key] = list(buf)
        elif mode == "block":
            data[key] = "\n".join(buf).strip()

    for line in block.splitlines():
        stripped = line.strip()
        indented = line[:1] in (" ", "\t")

        if mode == "block" and (indented or not stripped):
            buf.append(stripped)
            continue
        if mode == "list" and stripped.startswith("- "):
            buf.append(stripped[2:].strip().strip("\"'"))
            continue

        if not stripped or stripped.startswith("#"):
            continue

        top = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", stripped)
        if not top:
            continue

        flush()
        key, raw = top.group(1), top.group(2).strip()
        mode, buf = None, []

        if raw in (">", "|", ">-", "|-"):
            mode = "block"
        elif raw.startswith("[") and raw.endswith("]"):
            data[key] = [
                p.strip().strip("\"'") for p in raw[1:-1].split(",") if p.strip()
            ]
        elif raw == "":
            mode = "list"  # may turn out to be an empty value; flush() handles both
        else:
            data[key] = raw.strip("\"'")
    flush()

    # A key that opened a list but collected nothing was really an empty scalar.
    for k, v in list(data.items()):
        if v == []:
            data[k] = ""
    return data, body


def kebab(text, limit=48):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug[:limit].rstrip("-")) or "converted-agent"


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.exit(f"error: no such file: {path}")
    except UnicodeDecodeError:
        sys.exit(f"error: {path} is not a UTF-8 text file")


def load(path):
    """JSON-only loader, for --wrapper."""
    text = read_text(path)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        sys.exit(f"error: {path} is not valid JSON: {exc}")


def load_source(path):
    """Detect the input shape and return (cfg, kind) where kind is 'json' or 'markdown'.

    Markdown definitions are normalised into the same dict shape as a JSON config, so everything
    downstream stays shape-agnostic. Detection is by content, not file extension.
    """
    text = read_text(path)
    head = text.lstrip()

    if head.startswith("{"):
        try:
            return json.loads(text), "json"
        except json.JSONDecodeError as exc:
            sys.exit(f"error: {path} looks like JSON but does not parse: {exc}")

    fm, body = parse_frontmatter(text)
    if fm is None:
        sys.exit(
            f"error: {path} is neither JSON nor a YAML-frontmatter markdown file.\n"
            f"       A markdown definition must start with '---' on line 1."
        )

    tools = fm.get("tools") or fm.get("allowed-tools") or fm.get("allowed_tools") or []
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]

    cfg = {
        "name": fm.get("name", ""),
        "description": fm.get("description", ""),
        "instructions": body.strip(),
        "_source_tools": tools,
        "_frontmatter": fm,
        "_unknown_frontmatter": sorted(set(fm) - KNOWN_FRONTMATTER),
    }
    return cfg, "markdown"


def first(d, *keys, default=""):
    for k in keys:
        if d.get(k):
            return d[k]
    return default


def extract(cfg, wrapper=None, kind="json"):
    caps = []
    for entry in cfg.get("capabilities") or []:
        if isinstance(entry, dict):
            ident = entry.get("name") or entry.get("type") or "(unnamed)"
            detail = {k: v for k, v in entry.items() if k not in ("name", "type")}
        else:
            ident, detail = str(entry), {}
        bucket, gloss = classify(ident)
        caps.append({"id": ident, "bucket": bucket, "gloss": gloss, "detail": detail})

    starters = []
    raw_starters = first(
        cfg,
        "conversation_starters",
        "conversationStarters",
        "starter_prompts",
        default=[],
    )
    for s in raw_starters or []:
        if isinstance(s, dict):
            starters.append(
                {
                    "title": first(s, "title", "name"),
                    "text": first(s, "text", "prompt", "body"),
                }
            )
        else:
            starters.append({"title": "", "text": str(s)})

    actions = []
    for a in cfg.get("actions") or []:
        if isinstance(a, dict):
            actions.append(
                {"id": first(a, "id", "name"), "file": first(a, "file", "spec", "url")}
            )

    tool_rows = []
    for source_tool in cfg.get("_source_tools") or []:
        quick_names, note = translate_tool(source_tool)
        tool_rows.append({"source": source_tool, "quick": quick_names, "note": note})

    name = cfg.get("name", "")
    unknown = (
        cfg.get("_unknown_frontmatter")
        if kind == "markdown"
        else sorted(set(cfg) - KNOWN_TOP_LEVEL)
    )
    out = {
        "kind": kind,
        "name": name,
        "proposed_quick_name": kebab(name),
        "description": cfg.get("description", ""),
        "instructions": first(cfg, "instructions", "instruction", "prompt"),
        "starters": starters,
        "capabilities": caps,
        "actions": actions,
        "tool_rows": tool_rows,
        "frontmatter": cfg.get("_frontmatter") or {},
        "unknown_keys": [k for k in (unknown or []) if not k.startswith("_")],
        "schema_version": cfg.get("version") or cfg.get("$schema", ""),
    }
    if wrapper:
        out["wrapper"] = {
            "app_name": (wrapper.get("name") or {}).get("short", "")
            if isinstance(wrapper.get("name"), dict)
            else wrapper.get("name", ""),
            "keys": sorted(wrapper.keys()),
        }
    return out


def fence(text):
    """Fence content without letting embedded backticks break out."""
    body = text or ""
    runs = re.findall(r"`+", body)
    ticks = "`" * (max((len(r) for r in runs), default=2) + 1 if runs else 3)
    if len(ticks) < 3:
        ticks = "```"
    return f"{ticks}\n{body}\n{ticks}"


def cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False) if value else "-"
    return str(value).replace("|", "\\|").replace("\n", " ") or "-"


def render(d):
    L = []
    a = L.append
    md = d["kind"] == "markdown"
    a(f"# Conversion intake - {d['name'] or '<unnamed agent>'}\n")
    if md:
        a("Source: **markdown definition** (YAML frontmatter + prose body).\n")
        a(
            "This shape converts more directly than a declarative config: the source object already "
            "has the same structure as a Quick skill. `name`, `description` and the body port "
            "near-verbatim. **The real work is the `tools:` translation in section 5** - the "
            "vocabularies are disjoint, and a wrong name fails silently at runtime.\n"
        )
    else:
        a(
            "Source: agent config JSON"
            + (f" (schema: `{d['schema_version']}`)" if d["schema_version"] else "")
            + "\n"
        )

    a(DESTINATION_BLOCK)

    a("## 1. Identity\n")
    a(
        "**Ask the user what to call the Quick skill before accepting the proposals below.** The source "
        "name is a default, not a decision - offer it, and show that keeping it produces "
        f"`display_name: {cell(d['name'])}` and a folder named `{d['proposed_quick_name']}`. Ask it as one "
        "question on its own.\n"
    )
    a("| Field | Value |")
    a("| --- | --- |")
    a(f"| Source **Name** | {cell(d['name'])} |")
    a(
        "| **Name the user chose** | **TODO** - ask; do not assume the source name carries over |"
    )
    a(
        f"| Proposed Quick `name` | `{d['proposed_quick_name']}` - re-derive if the name changed |"
    )
    a(f"| Proposed `display_name` | {cell(d['name'])} - replace if the name changed |")
    fm = d["frontmatter"]
    if fm.get("display_name"):
        a(f"| Source `display_name` | {cell(fm['display_name'])} - ports as-is |")
    if fm.get("icon"):
        a(f"| Source `icon` | {cell(fm['icon'])} - ports as-is |")
    else:
        a("| Proposed `icon` | **TODO** - one emoji (source image is not portable) |")
    if fm.get("trigger"):
        a(
            f"| Source `trigger` | {cell(fm['trigger'])} - ports as-is; check it does not collide "
            "with a built-in skill |"
        )
    else:
        a(
            "| Proposed `trigger` | **TODO** - 2-4 words, invented; no source counterpart |"
        )
    if fm.get("model"):
        a(
            f"| Source `model` | {cell(fm['model'])} - **dropped**, no Quick equivalent |"
        )
    if d.get("wrapper"):
        a(f"| Wrapper app name | {cell(d['wrapper']['app_name'])} |")
    a("")

    a("## 2. Description\n")
    a("Source **Description**, verbatim:\n")
    a(fence(d["description"]))
    a(
        "\nQuick `description`: **TODO** - the above, plus the trigger vocabulary appended.\n"
    )

    a("## 3. Instructions\n")
    a(f"Source **Instructions**, verbatim ({len(d['instructions'])} chars):\n")
    a(fence(d["instructions"]))
    if md:
        a(
            "\nThis body was already written for an agent that reads it on demand, so it is probably "
            "close to the right shape already. Keep its structure. Check only for: a `## Prerequisites` "
            "section (Quick needs connectors and folders named explicitly), references to tools that "
            "section 5 could not translate, and shell commands - Quick has no general shell.\n"
        )
        a("Restructuring notes: **TODO**\n")
    else:
        a(
            "\nRestructuring notes: **TODO** - which blocks become Overview / Workflow Steps / "
            "Best Practices / Failure handling / a `references/` file / cut as boilerplate.\n"
        )

    knowledge = [c for c in d["capabilities"] if c["bucket"] == "knowledge"]
    a("## 4. Knowledge sources\n")
    if md:
        a(
            "A markdown definition has **no knowledge-sources field**. Its grounding comes from "
            "whatever folders and connectors the host platform had configured around it - which is "
            "not in this file.\n"
        )
        a(
            "**Ask the user directly:** which folders, connected tools and data sources did this agent "
            "rely on? Then resolve each one through `references/knowledge-and-tools-remap.md` as "
            "normal. Do not skip this section just because the file is silent about it.\n"
        )
        a(ASK_SEQUENCE)
        a(
            "| # | Source named by the user | Link (as pasted) | Local path | Consumed by step "
            "| Changes? | Red Data? | Quick landing spot | Prereq | Status |"
        )
        a("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        a(
            "| 1 | **TODO** | **TODO** | **TODO** | **TODO** | **TODO** | **TODO** | **TODO** "
            "| **TODO** | unresolved |"
        )
        a("")
    elif knowledge:
        a(ASK_SEQUENCE)
        a(
            "| # | Identifier in file | Read as | Detail | Link (as pasted) | Local path "
            "| Consumed by step | Changes? | Red Data? | Quick landing spot | Prereq | Status |"
        )
        a("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for i, c in enumerate(knowledge, 1):
            a(
                f"| {i} | `{cell(c['id'])}` | {c['gloss']} | {cell(c['detail'])} | **TODO** | **TODO** "
                f"| **TODO** | **TODO** | **TODO** | **TODO** | **TODO** | unresolved |"
            )
        a(
            "\n**Every row must end as `remapped` or `dropped`.** See "
            "`references/knowledge-and-tools-remap.md`."
        )
    else:
        a(
            "None detected in the file. **This does not mean there are none.** Confirm with the user - an "
            "authoring UI can hold sources a hand-edited config omits, and the instructions in section 3 "
            "may refer to documents that were never attached at all. Search that text for phrases like "
            '"refer to", "see the ... document", "follow the ... guidelines" and run the two '
            "questions below against each hit."
        )
        a("")
        a(ASK_SEQUENCE)
    a("")

    caps = [
        c for c in d["capabilities"] if c["bucket"] in ("capability", "unclassified")
    ]
    a("## 5. Capabilities\n")
    if md:
        rows = d["tool_rows"]
        if rows:
            a(
                "Declared `tools:`, translated. **Verify every proposed name against the target build**"
                " - see the verification command in `references/knowledge-and-tools-remap.md`.\n"
            )
            a("| Source tool | Proposed Quick tool(s) | Note | Status |")
            a("| --- | --- | --- | --- |")
            for r in rows:
                proposed = (
                    ", ".join(f"`{q}`" for q in r["quick"])
                    if r["quick"]
                    else "**none**"
                )
                status = "needs verification" if r["quick"] else "**dropped**"
                a(
                    f"| `{cell(r['source'])}` | {proposed} | {cell(r['note']) if r['note'] else '-'} "
                    f"| {status} |"
                )
            dropped = [r for r in rows if not r["quick"]]
            if dropped:
                a(
                    f"\n**{len(dropped)} source tool(s) have no Quick equivalent.** For each one, find "
                    "where the body uses it and rewrite that step, or record the capability as dropped "
                    "in the final report. Do not substitute a different tool and hope."
                )
            if any(r["source"].strip().strip("\"'").lower() == "bash" for r in rows):
                a(
                    "\n**Shell dependency detected.** The source agent could run arbitrary shell "
                    "commands; Quick cannot. Audit the body for shell invocations and rewrite each as "
                    "Python (`run_python`) or as prose instructions. This is the most common cause of a "
                    "converted markdown agent failing part-way through."
                )
        else:
            a(
                "No `tools:` declared in the frontmatter. Either the agent inherited every tool from "
                "its host, or it needs none. Ask the user which - an agent that assumed full tool "
                "access needs its `tools:` list built from scratch by reading the body."
            )
        a("")
    elif caps:
        a(
            "| Identifier in file | Read as | Detail | Consumed by step | Quick equivalent | Status |"
        )
        a("| --- | --- | --- | --- | --- | --- |")
        for c in caps:
            a(
                f"| `{cell(c['id'])}` | {c['gloss']} | {cell(c['detail'])} | **TODO** | **TODO** "
                "| unresolved |"
            )
    else:
        a("None detected.")
    a("")

    a("### API actions\n")
    if d["actions"]:
        a("| id | API specification | Quick equivalent | Status |")
        a("| --- | --- | --- | --- |")
        for act in d["actions"]:
            a(
                f"| `{cell(act['id'])}` | `{cell(act['file'])}` | action connector or MCP from "
                "**the same specification** | unresolved |"
            )
        a("\nObtain each specification file. Do not reimplement the API by hand.")
    else:
        a("None declared.")
    a("")

    a("## 6. Starter prompts\n")
    if d["starters"]:
        a("| Name | Prompt text | Most-used? |")
        a("| --- | --- | --- |")
        for s in d["starters"]:
            a(f"| {cell(s['title'])} | {cell(s['text'])} | **TODO** |")
        a(
            "\nThese become `## Example invocations`, and their vocabulary goes into the `description` to "
            "widen matching. **They are examples, not a statement of scope: do not seed the `trigger` "
            "from one.** Derive the trigger from the description and purpose, then check it covers the "
            "breadth of these prompts. Confirm each is untruncated - authoring UIs clip prompt text to "
            "the column width."
        )
    else:
        a("None declared.")
    a("")

    a("## 7. Not portable - report as dropped\n")
    if md:
        a("- `model:` selection → no equivalent. Quick chooses the model.")
        a(
            "- Sub-agent nesting → if this agent dispatched other agents, Quick's task tools are not a "
            "like-for-like replacement. Confirm the behaviour is preserved or report it as changed."
        )
        a(
            "- Plugin packaging → if the agent shipped inside a plugin alongside other agents, skills "
            "and connectors, Quick has no plugin equivalent. Each piece installs separately: skills as "
            "skills, connectors under Settings → Capabilities → Connections. Say so explicitly."
        )
        a("- Shell access → see section 5.")
    else:
        a("- Icon / avatar image → replaced by one emoji.")
        a(
            "- Response mode / reasoning depth → no equivalent. If the agent defaulted to extended "
            "reasoning, write explicit validation criteria into the body instead."
        )
    a("")

    a("## 8. Baseline for verification\n")
    if md:
        a(
            "**TODO** - run the agent on its most representative task in the source platform and paste "
            "the output here. It is the only baseline for verifying the conversion.\n"
        )
    else:
        a(
            "**TODO** - run the most representative starter prompt in the source platform's preview "
            "mode and paste the output here. It is the only baseline for Step 5.\n"
        )

    a("## 9. Proposed `tools:` list\n")
    if md and d["tool_rows"]:
        proposed = []
        for r in d["tool_rows"]:
            for q in r["quick"]:
                if q not in proposed:
                    proposed.append(q)
        a(
            "Derived from section 5. **Every name still needs verification against the target build** "
            "before it goes in the frontmatter:\n"
        )
        a(
            f"```yaml\ntools: [{', '.join(proposed)}]\n```\n"
            if proposed
            else "No translatable tools - build the list from the body by hand.\n"
        )
        a("Drop any name that does not verify. Do not substitute a guess.\n")
    else:
        a(
            "**TODO** - verify each name against this build (Agents & skills → Skills → open a built-in "
            "skill → attached tools). Omit unverified names rather than guessing.\n"
        )

    a("## 10. Output location\n")
    a(
        "**Resolved, not asked.** Find the connected local folder whose subfolders contain `SKILL.md` "
        "files - that is where the user's skills live, and the new folder goes beside them. Only ask if "
        "more than one candidate exists, and then only as a pick-one. Fill this in as you write:\n"
    )
    a("| Field | Value |")
    a("| --- | --- |")
    a("| Connected folders searched | **TODO** |")
    a("| Folder containing existing skills | **TODO** |")
    a("| How many skills it already holds | **TODO** |")
    a("| Path written to | **TODO** - `<skills-folder>/<skill-name>/` |")
    a("| Created the folder because none existed? | **TODO** - no / yes |")
    a(
        "| Frontmatter read back after writing: line 1 is `---`, block closed, one key per line, no `#` "
        "before a key | **TODO** - pass / fail |"
    )
    a(
        "\nThat last row is not a formality. A frontmatter block whose keys end up on one line, or behind "
        "a `#`, installs without error and shows up in Quick with a blank name and `0 tools`. Run "
        "`package_skill.py`, which names that symptom in its error text."
    )
    a(
        "\nNever hardcode this path into the generated skill. Writing the folder is not installing it: "
        "Quick loads skills from its own profile directory, which is not writable from here, so the zip "
        "still has to be uploaded and Quick restarted.\n"
    )

    a("## 11. Outstanding decisions for the user\n")
    a("One question per message. Keep the queue here, not in the message.\n")
    a("- **TODO**\n")

    if d["unknown_keys"]:
        a("## 12. Unrecognised keys\n")
        a("Reported rather than dropped - inspect these manually:\n")
        for k in d["unknown_keys"]:
            a(f"- `{k}`")
        a("")

    return "\n".join(L) + "\n"


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "config",
        help="agent config JSON, or a markdown definition with YAML frontmatter",
    )
    p.add_argument(
        "--wrapper", help="path to a broader app manifest that nests the agent config"
    )
    p.add_argument("--out", help="write the intake here (default: stdout)")
    p.add_argument(
        "--json", action="store_true", help="emit raw JSON instead of the intake"
    )
    args = p.parse_args()

    cfg, kind = load_source(args.config)
    data = extract(cfg, load(args.wrapper) if args.wrapper else None, kind=kind)
    text = json.dumps(data, indent=2, ensure_ascii=False) if args.json else render(data)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        todos = text.count("**TODO**") + text.count("unresolved")
        print(
            f"wrote {args.out} - detected a {kind} definition - "
            f"{todos} item(s) need a human decision",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
