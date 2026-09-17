---
description: "Human-facing overview, prerequisites, installation, and getting started for the Agent To Quick Skill conversion skill."
last_updated: 2026-09-08
origin: original
---

# agent-to-quick-skill

Convert a declarative chat agent from another assistant platform into an Amazon Quick desktop skill.

## What it does

Interviews the user one question at a time for the six things a conversion needs (name,
description, instructions, knowledge sources, capabilities, starter prompts), maps each field to
its Amazon Quick equivalent, writes a spec-correct `SKILL.md` folder, and walks the install.

Roughly 70% of a conversion is mechanical (name, description, instructions, tools). The other 30%
- knowledge sources and capabilities - cannot be ported, only *remapped*, and remapping needs
explicit decisions from the user.

## Structure

```
agent-to-quick-skill/
├── SKILL.md                 # frontmatter + workflow
├── references/              # field mappings, copy-paste guide, format contract
├── assets/                  # SKILL.template.md, intake.template.md
├── scripts/                 # parse_manifest.py, package_skill.py (stdlib only)
└── evals/                   # evals.json test cases
```

## Tools

`file_read, file_write, file_edit, folder_create, folder_list, run_python, open_in_session_tab, get_current_time`

## Testing

Test cases live in `evals/evals.json`. Each case is a realistic trigger prompt plus behavioral
assertions (destination confirmation, one-question-at-a-time, tool-name verification, team→agent
routing, PII hard-stop).

## Dependencies

None required. Works from a pasted config or a file. Code execution is optional (the scripts are a
convenience, not a dependency).
