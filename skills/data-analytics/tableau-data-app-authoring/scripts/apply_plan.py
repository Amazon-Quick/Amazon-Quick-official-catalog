#!/usr/bin/env python3
"""
description: Finalize a scaffolded data-app workspace by applying the postUnzip plan from the scaffold-data-app tool.
last_updated: 2026-11-22

Finalize a scaffolded data-app workspace by applying the `postUnzip` plan from
the `scaffold-data-app` MCP tool. Plan shape:
  { instructions, edits: [{ file, replacements: [{ find, replace }] }],
    renames: [{ from, to }] }
Every path is relative to the unzip dir, incl. the template root prefix
(e.g. "Data App Name/...").

Order is why this is a script, not freehand edits: apply ALL edits first, THEN
renames in the given order (deepest first, root last). Renaming before editing
invalidates edit paths; reordering renames orphans a child under its parent.

Usage: python3 apply_plan.py <unzipDir> <planJsonPath>
"""

import json
import os
import sys

PLACEHOLDER_TOKENS = ["TODO-MANIFEST-ID", "TODO App Name", "TODO Sheet Name"]


def die(message):
    print(f"✗ {message}", file=sys.stderr)
    sys.exit(1)


def main(argv=None):
    # argv: the arguments as a list, for callers that import this script; default: the command line.
    argv = sys.argv if argv is None else ["apply_plan.py", *argv]
    if len(argv) < 3:
        die("Usage: python3 apply_plan.py <unzipDir> <planJsonPath>")
    unzip_dir_arg, plan_path_arg = argv[1], argv[2]

    unzip_dir = os.path.abspath(unzip_dir_arg)

    try:
        with open(plan_path_arg, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as error:
        die(f"Could not read/parse plan JSON at {plan_path_arg}: {error}")
        return

    edits = plan.get("edits") if isinstance(plan.get("edits"), list) else []
    renames = plan.get("renames") if isinstance(plan.get("renames"), list) else []
    if len(edits) == 0 and len(renames) == 0:
        die("Plan has no edits or renames — did you pass the full postUnzip object?")

    def safe_join(rel):
        abs_path = os.path.abspath(os.path.join(unzip_dir, rel))
        if abs_path != unzip_dir and not abs_path.startswith(unzip_dir + "/"):
            die(f"Plan path escapes the unzip directory: {rel}")
        return abs_path

    # 1) Apply edits: literal (non-regex) find/replace on each file's contents.
    for edit in edits:
        file = edit.get("file")
        replacements = edit.get("replacements") or []
        abs_path = safe_join(file)
        try:
            with open(abs_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as error:
            die(f"Edit target missing: {file} ({error})")
            return
        for replacement in replacements:
            find = replacement.get("find")
            replace = replacement.get("replace")
            if find not in content:
                die(
                    f'Placeholder "{find}" not found in {file} — template/plan out of sync.'
                )
            content = content.replace(find, replace)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  edited  {file}", file=sys.stderr)

    # 2) Apply renames in the given order (deepest-first, root last).
    for rename in renames:
        from_rel, to_rel = rename.get("from"), rename.get("to")
        try:
            os.rename(safe_join(from_rel), safe_join(to_rel))
        except Exception as error:
            die(f"Rename failed: {from_rel} -> {to_rel} ({error})")
            return
        print(f"  renamed {from_rel} -> {to_rel}", file=sys.stderr)

    # 3) The finalized workspace root is the target of the last rename.
    final_root_rel = renames[-1].get("to") if renames else None
    final_root = safe_join(final_root_rel) if final_root_rel else unzip_dir

    # 4) Verify no placeholder tokens survived. Recompute each edited file's final
    #    path through every rename — a file can move via more than one (e.g. the
    #    root-dir rename AND a nested package-dir rename).
    def remap_through_renames(rel_path):
        current = rel_path
        for rename in renames:
            from_rel, to_rel = rename.get("from"), rename.get("to")
            if current == from_rel:
                current = to_rel
            elif current.startswith(from_rel + "/"):
                current = to_rel + current[len(from_rel) :]
        return current

    residual = []
    for edit in edits:
        file = edit.get("file")
        final_rel = remap_through_renames(file)
        try:
            with open(safe_join(final_rel), encoding="utf-8") as f:
                content = f.read()
        except Exception as error:
            die(f"Finalized file missing for placeholder check: {final_rel} ({error})")
            return
        for token in PLACEHOLDER_TOKENS:
            if token in content:
                residual.append(f'{final_rel}: "{token}"')
    if len(residual) > 0:
        die("Residual placeholders after finalize:\n  " + "\n  ".join(residual))

    print(f"✓ Finalized workspace at {final_root}", file=sys.stderr)
    print(final_root)


if __name__ == "__main__":
    main()
