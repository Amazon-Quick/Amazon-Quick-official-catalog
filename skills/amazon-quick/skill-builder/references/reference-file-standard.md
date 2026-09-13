---
description: "The header standard every skill file must carry: SKILL.md frontmatter, references/*.md frontmatter, and scripts/*.py module docstrings. Defines required and conditional fields and the staleness rule."
last_updated: 2026-09-13
origin: original
---

# Reference File Header Standard

<purpose>
Every file in a skill declares who it is and where it came from, so a file that has gone stale can be found and rebuilt from its source. This standard defines the header fields and the staleness rule that the Audit workflow enforces.
</purpose>

<scope>
Applies to:
- `SKILL.md` frontmatter.
- `README.md` frontmatter.
- `references/*.md` frontmatter.
- `scripts/*.py` module docstrings (a script cannot carry YAML frontmatter, so the same fields live in the top-of-file docstring).
</scope>

<fields>
- `description` (required, all files): what the file contains and why the skill needs it.
- `last_updated` (required, all files): ISO `YYYY-MM-DD` date the file was last changed.
- `source_url` (required when derived): the URL the file was built from, when its content comes from an external source. A derived file must record where to rebuild it.
- `origin: original` (required when not derived): marks internal-authored content that has no upstream source.

Exactly one of `source_url` or `origin: original` is present on every file, so "no source" is always a deliberate declaration rather than an omission.
</fields>

<staleness>
A file is stale when its `last_updated` is more than six months before today. A stale file, or a stale `SKILL.md`, produces a WARNING (not a failure): the skill still runs, but the report flags it for rebuild from its `source_url`.
</staleness>

<generating>
Do not hand-write the header. Scaffold a new file with a compliant header using the bundled generators, run from the skill root:

- Reference file: `python scripts/create_reference_file.py references <name> --description "..." (--source-url "..." | --origin original)`
- Script: `python scripts/create_script.py scripts <file_name> --description "..." --class-name "..." --method-name "..." (--source-url "..." | --origin original)`
- README: `python scripts/create_readme.py <skill_dir> --description "..." (--source-url "..." | --origin original)`

Each generator sets `last_updated` to today, requires exactly one of `--source-url` (derived) or `--origin original` (internal), and emits the skeleton this standard defines. Use `--source-url` when the content comes from an external source, so the file records where to rebuild from.
</generating>

<examples>
<example type="correct">
Markdown reference file derived from an external source:

```yaml
---
description: "Amazon Quick Python sandbox package names, grouped by use."
last_updated: 2026-09-13
source_url: https://docs.aws.amazon.com/quick/latest/userguide/...
---
```
</example>

<example type="correct">
Script header (same fields, in the module docstring):

```python
"""
description: Compute a skill's deterministic sha256 content digest and write it into SKILL.md.
last_updated: 2026-09-13
origin: original
"""
```
</example>

<example type="incorrect">
Missing both source_url and origin, so staleness cannot suggest a rebuild path:

```yaml
---
description: "Eval methodology."
last_updated: 2026-09-13
---
```
</example>
</examples>
