#!/usr/bin/env python3
"""
description: Validate and zip an Amazon Quick skill folder for upload to Quick desktop. Checks the frontmatter contract before packaging, so an invalid skill fails here rather than after a five-minute upload and a restart. Run as: python3 package_skill.py <skill-folder> [--out <name>.zip] [--check-only].
last_updated: 2026-09-08
origin: original

Usage:
    python3 package_skill.py <skill-folder> [--out <name>.zip] [--check-only]
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path

SKIP_DIRS = {"__pycache__", ".git", ".DS_Store", "node_modules", ".venv"}
REQUIRED = ["name", "display_name", "description"]
RECOMMENDED = ["trigger", "icon"]
# Keys that turning up mid-line prove the block was flattened rather than newline-separated.
KNOWN_KEYS = ["display_name", "description", "icon", "trigger", "tools", "name"]


def read_frontmatter(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not m:
        return None, text, []
    block, keys, shape = m.group(1), {}, []
    current = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            # A '#' makes the line a YAML comment, so any key on it is silently dropped.
            # Quick then shows the skill with a blank name, which is impossible to diagnose
            # from the UI -- catch it here and name the symptom.
            if re.match(r"^\s*#+\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:", line):
                shape.append(
                    f"a frontmatter key is commented out with '#': {line.strip()[:60]!r} - "
                    f"'#' starts a YAML comment, so Quick sees the key as missing and the "
                    f"skill installs with a blank name"
                )
            continue
        top = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if top:
            current = top.group(1)
            keys[current] = top.group(2).strip()
            # More than one key on a single line means the newlines were lost in the write.
            others = [
                k
                for k in KNOWN_KEYS
                if k != current and re.search(rf"(?<![\w-]){k}\s*:", top.group(2))
            ]
            if others:
                shape.append(
                    f"line for `{current}` also contains {', '.join(sorted(others))} - "
                    f"the frontmatter keys were written on one line instead of one per "
                    f"line, so none of them parse"
                )
        elif line.lstrip().startswith("-") and current:
            keys[current] = (keys.get(current) or "") + " " + line.strip()
        elif line.startswith((" ", "\t")):
            pass  # continuation of a block scalar or a nested mapping
        else:
            shape.append(f"frontmatter line is not `key: value`: {line.strip()[:60]!r}")
    return keys, text, shape


def validate(folder):
    """Return (errors, warnings)."""
    errors, warnings = [], []
    skill_md = folder / "SKILL.md"

    if not skill_md.is_file():
        return [
            f"{folder}/SKILL.md not found - a Quick skill folder must contain SKILL.md"
        ], []

    keys, text, shape = read_frontmatter(skill_md)
    if keys is None:
        first = (text.splitlines() or [""])[0]
        hint = (
            "SKILL.md has no parseable YAML frontmatter block: line 1 must be exactly '---' and a "
            f"line that is exactly '---' must close it (line 1 is currently {first[:60]!r}). "
            "Without it Quick installs the skill with a blank name, reports 0 tools, and renders "
            "the whole block as body text."
        )
        return [hint], []

    errors.extend(shape)

    for field in REQUIRED:
        if not keys.get(field):
            errors.append(f"frontmatter is missing required field: {field}")
    for field in RECOMMENDED:
        if not keys.get(field):
            warnings.append(
                f"frontmatter has no `{field}` - Quick can still auto-select the skill "
                f"by description, but explicit invocation gets harder"
            )

    name = (keys.get("name") or "").strip().strip("\"'")
    if name:
        shown = name if len(name) <= 50 else name[:47] + "..."
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
            errors.append(
                f"`name: {shown}` is not kebab-case (lowercase, digits, single hyphens)"
            )
        if name != folder.name:
            errors.append(f"`name: {shown}` must match the folder name `{folder.name}`")

    if "<" in (keys.get("description") or "") or "TODO" in text:
        warnings.append(
            "template placeholders (`<...>` or `TODO`) still present - "
            "unfilled placeholders ship as instructions to the agent"
        )

    if re.search(r"/Users/[^/\s]+/|C:\\Users\\[^\\\s]+", text):
        warnings.append(
            "an absolute user-specific path appears in SKILL.md - this makes the skill "
            "unshareable; take the folder as an input or state it in Prerequisites"
        )

    body = text[text.find("---", 3) + 3 :] if keys else text
    if len(body.strip()) < 200:
        warnings.append(
            "body is very short - Quick skills are multi-step workflows, not prompt "
            "templates; confirm this is intentional"
        )

    return errors, warnings


def files_to_pack(folder):
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts) or path.name == ".DS_Store":
            continue
        if path.suffix == ".pyc":
            continue
        yield path


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "folder", help="the skill folder (its name must equal frontmatter `name`)"
    )
    p.add_argument(
        "--out", help="output zip path (default: <folder-name>.zip beside the folder)"
    )
    p.add_argument(
        "--check-only", action="store_true", help="validate without writing a zip"
    )
    args = p.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        sys.exit(f"error: not a directory: {folder}")

    errors, warnings = validate(folder)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.check_only:
        print(
            f"{folder.name}: frontmatter valid"
            + (f" ({len(warnings)} warning(s))" if warnings else ""),
            file=sys.stderr,
        )
        return

    out = Path(args.out) if args.out else folder.parent / f"{folder.name}.zip"
    packed = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files_to_pack(folder):
            # Keep the folder as the zip's top-level entry -- Quick expects a skill folder.
            zf.write(path, folder.name / path.relative_to(folder))
            packed += 1

    print(f"wrote {out} ({packed} file(s))", file=sys.stderr)
    print(
        "\nInstall: Amazon Quick desktop → Settings → Capabilities → Skills → Upload\n"
        "         (or Settings → Agents & skills → Skills → + Create → Import from file)\n"
        "Then RESTART Quick desktop. Processing can take up to five minutes; if the skill is not\n"
        "recognised, restart again. Verify with: Tell me about "
        f"{folder.name}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
