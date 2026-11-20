---
description: "The header every README, reference file, and script in a skill carries (description, last_updated, and optional sources), why each field exists, and the staleness rule the Audit workflow enforces."
last_updated: 2026-11-18
---

# Reference File Header Standard

<purpose>
Every README, reference file, and script in a skill opens with a short header that says what the file holds and when it last changed. This standard defines the header fields and the staleness rule the Audit workflow enforces.
</purpose>

<scope>
Applies to:
- `assets/README.md` frontmatter.
- `references/*.md` frontmatter.
- `references/*.json` and the `*_rule.json` files in `references/rules/`: the same fields as top-level keys of the JSON object. The generated `*.schema.json` files and the sandbox manifests (quick-sandbox-requirements.txt, quick-sandbox-package.json) are exempt.
- `scripts/*.py` module docstrings: the same fields at the top of the docstring.
- `scripts/*.js`: the same fields in a `/** ... */` comment at the top of the file.

SKILL.md has its own frontmatter, defined in `<Definition - Frontmatter>`.
</scope>

<fields>
- `description` (required): what the file holds, in one line.
- `last_updated` (required): the ISO `YYYY-MM-DD` date the file last changed. The staleness rule below reads it.
- `sources` (optional): a list of the URLs the file copies content from, such as snippets or tables taken from documentation. The Audit workflow refreshes a stale file from these pages. Leave it out when the file has no outside source.
</fields>

<staleness>
A file is stale when its `last_updated` is more than six calendar months before today (UTC). A stale file, or a stale `SKILL.md`, produces a WARNING, not a failure: the skill still runs, but the audit flags it. `check_skill.py` reports staleness for `SKILL.md` and every README, reference file, and script. The Audit workflow says how to refresh a stale file.
</staleness>

<generating>
Scaffold a new file with the generators instead of writing the header by hand. Each sets `last_updated` to today, and `--source` adds a URL to `sources` (repeat it for each page):

- Reference file: `create_reference_file.py references <name> --description "..." [--source URL ...]`
- Script: `create_script.py scripts <file_name> --description "..." --class-name "..." --method-name "..." [--source URL ...]`
- README: `create_readme.py <skill_dir> --title "..." --summary "..." --prefix <prefix> [--dependency "Name|TYPE|Y|URL" ...]`
</generating>

<examples>
<example type="correct">
A reference file that copies a table from the docs:

```yaml
---
description: "AWS Quick connector setup steps, by connector."
last_updated: 2026-11-18
sources:
  - https://docs.aws.amazon.com/quick/latest/userguide/connections-desktop.html
  - https://docs.aws.amazon.com/quick/latest/userguide/mcp-integration.html
---
```
</example>

<example type="correct">
A script written from scratch, with no outside source:

```python
"""
description: Compute a skill's sha256 content digest and write it into SKILL.md.
last_updated: 2026-11-18
"""
```
</example>

<example type="incorrect">
A `sources` entry that isn't a URL, so nobody can open it to refresh the file:

```yaml
---
description: "Connector setup steps."
last_updated: 2026-11-18
sources:
  - the AWS Quick User Guide
---
```
</example>
</examples>
