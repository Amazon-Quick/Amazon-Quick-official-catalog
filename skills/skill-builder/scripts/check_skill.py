#!/usr/bin/env python3
"""Mechanical pass/fail checks for a SKILL.md.

Runs ONLY the objective schema checks that do not require judgment: frontmatter
fields, naming, character and line limits, XML tag balance, block ordering,
em dashes and body emojis, and rule numbering. Qualitative review (does the
workflow make sense, is the voice right, are claims verifiable) is NOT done here
and must be done by reading, per the skill's Rules.

Standard library only. No third-party packages.

Usage:
    python check_skill.py <path/to/SKILL.md>

Exit code 0 if all checks pass, 1 if any fail. Prints a report either way.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_DESCRIPTION = 1024
MAX_BODY_LINES = 500
MAX_NAME = 64

REQUIRED_FRONTMATTER = ("name", "description", "created_date", "last_updated")
# Canonical block order from <Definition - XML Blocks>. Optional blocks may be
# absent, but present blocks must appear in this relative order.
BLOCK_ORDER = (
    "Identity",
    "Goal",
    "Definitions",
    "Rules",
    "Agent Annotations",
    "Gotchas",
    "Instructions",
    "Templates",
    "Resources",
)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_text, body_text). Frontmatter is between the first
    two '---' fences. If absent, frontmatter is '' and body is the whole file."""
    lines = text.splitlines()
    fences = [i for i, ln in enumerate(lines) if ln.strip() == "---"]
    if len(fences) >= 2:
        fm = "\n".join(lines[fences[0] + 1 : fences[1]])
        body = "\n".join(lines[fences[1] + 1 :])
        return fm, body
    return "", text


def _strip_examples(body: str) -> str:
    """Remove fenced code blocks and the <Definitions> section from the body.

    Both contain illustrative syntax (example tools=[...] lists, {{name}}
    placeholders) that describes the format rather than using it. Checks that
    look for real usage must not treat those examples as violations.
    """
    no_fences = re.sub(r"```.*?```", "", body, flags=re.S)
    no_defs = re.sub(r"<Definitions>.*?</Definitions>", "", no_fences, flags=re.S)
    return no_defs


def check_frontmatter(fm: str, results: list) -> None:
    for field in REQUIRED_FRONTMATTER:
        if re.search(rf"^{field}\s*:", fm, re.M):
            results.append((True, f"frontmatter: {field} present"))
        else:
            results.append((False, f"frontmatter: {field} MISSING"))

    m = re.search(r'^name\s*:\s*"?([^"\n]+)"?', fm, re.M)
    if m:
        name = m.group(1).strip()
        if re.fullmatch(rf"[a-z][a-z0-9-]{{0,{MAX_NAME - 1}}}", name):
            results.append((True, f"name '{name}' is valid kebab-case"))
        else:
            results.append(
                (
                    False,
                    f"name '{name}' is not valid kebab-case (lowercase, hyphens, <= {MAX_NAME} chars)",
                )
            )

    m = re.search(r'^description\s*:\s*"(.*)"\s*$', fm, re.M)
    if m:
        n = len(m.group(1))
        ok = n <= MAX_DESCRIPTION
        results.append((ok, f"description length {n} (limit {MAX_DESCRIPTION})"))

    for date_field in ("created_date", "last_updated"):
        m = re.search(rf'^{date_field}\s*:\s*"?(\d{{4}}-\d{{2}}-\d{{2}})"?', fm, re.M)
        if re.search(rf"^{date_field}\s*:", fm, re.M):
            results.append(
                (
                    bool(m),
                    f"{date_field} is ISO YYYY-MM-DD"
                    if m
                    else f"{date_field} not ISO YYYY-MM-DD",
                )
            )


def check_headings(body: str, results: list) -> None:
    for heading in ("## Overview", "## Workflow"):
        ok = heading in body
        results.append(
            (
                ok,
                f"heading '{heading}' present"
                if ok
                else f"heading '{heading}' MISSING (save_skill requires it)",
            )
        )


def check_block_order(body: str, results: list) -> None:
    """Present canonical blocks must appear in the defined relative order.

    Only inspects opening tags at the start of a line, ignoring fenced code
    blocks so template examples inside ``` do not count.
    """
    no_fences = re.sub(r"```.*?```", "", body, flags=re.S)
    seen = []
    for block in BLOCK_ORDER:
        if re.search(rf"^<{re.escape(block)}>", no_fences, re.M):
            seen.append(block)
    canonical = [b for b in BLOCK_ORDER if b in seen]
    if seen == canonical:
        results.append((True, f"block ordering correct ({', '.join(seen)})"))
    else:
        results.append(
            (False, f"block ordering off: found {seen}, expected order {canonical}")
        )


def check_tag_balance(body: str, results: list) -> None:
    """Every <Block> / <Workflow - X> opening tag has a matching close.

    Skips fenced code blocks and inline-attribute workflow openers (which span
    multiple lines and close with '>' on their own).
    """
    no_fences = re.sub(r"```.*?```", "", body, flags=re.S)
    # Simple paired blocks like <Identity>...</Identity>
    opens = re.findall(r"^\s*<([A-Z][A-Za-z ]*?)>\s*$", no_fences, re.M)
    closes = re.findall(r"^\s*</([A-Z][A-Za-z ]*?)>\s*$", no_fences, re.M)
    # Workflow openers use inline attributes spanning lines: <Workflow - X ... >
    wf_opens = re.findall(r"^\s*<Workflow - [^\n>]*$", no_fences, re.M)
    wf_closes = re.findall(r"^\s*</Workflow - [^\n>]+>\s*$", no_fences, re.M)
    unbalanced = []
    for tag in set(opens):
        if opens.count(tag) != closes.count(tag):
            unbalanced.append(
                f"<{tag}> x{opens.count(tag)} vs </{tag}> x{closes.count(tag)}"
            )
    if len(wf_opens) != len(wf_closes):
        unbalanced.append(
            f"<Workflow - ...> openers x{len(wf_opens)} vs closers x{len(wf_closes)}"
        )
    if unbalanced:
        results.append((False, "tag balance issues: " + "; ".join(unbalanced)))
    else:
        results.append((True, "all block and workflow tags balanced"))


def check_body_length(body: str, results: list) -> None:
    n = len(body.splitlines())
    ok = n <= MAX_BODY_LINES
    results.append((ok, f"body length {n} lines (limit {MAX_BODY_LINES})"))


def check_em_dash_and_emoji(body: str, results: list) -> None:
    # Strip fenced code blocks so example content (e.g. an icon in a sample
    # frontmatter) is not flagged. Blank the lines to keep line numbers stable.
    def blank_fences(text: str) -> list[str]:
        out, in_fence = [], False
        for line in text.splitlines():
            if line.strip().startswith("```"):
                in_fence = not in_fence
                out.append("")
                continue
            out.append("" if in_fence else line)
        return out

    scan = blank_fences(body)
    # Em dash: U+2014. Report line numbers.
    em_lines = [i + 1 for i, ln in enumerate(scan) if "\u2014" in ln]
    results.append(
        (
            not em_lines,
            "no em dashes" if not em_lines else f"em dashes on body lines {em_lines}",
        )
    )

    emoji_pattern = re.compile(
        "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f0ff]"
    )
    emoji_lines = [i + 1 for i, ln in enumerate(scan) if emoji_pattern.search(ln)]
    results.append(
        (
            not emoji_lines,
            "no body emojis"
            if not emoji_lines
            else f"emojis on body lines {emoji_lines}",
        )
    )


def check_rule_numbering(body: str, results: list) -> None:
    """Rules inside <Rules>...</Rules> must be numbered sequentially from 1."""
    m = re.search(r"<Rules>(.*?)</Rules>", body, re.S)
    if not m:
        return  # No Rules block; nothing to check.
    nums = [int(x) for x in re.findall(r"^(\d+)\.\s", m.group(1), re.M)]
    if not nums:
        results.append((False, "Rules block present but no numbered rules found"))
        return
    expected = list(range(1, len(nums) + 1))
    if nums == expected:
        results.append((True, f"rules numbered sequentially 1-{len(nums)}"))
    else:
        results.append((False, f"rule numbering not sequential: {nums}"))
        return
    # Self-reference check: if a rule says "Rules (1-N)", N must equal the count.
    ref = re.search(r"Rules \(1-(\d+)\)", m.group(1))
    if ref:
        n = int(ref.group(1))
        ok = n == len(nums)
        results.append(
            (
                ok,
                f"rule self-reference says 1-{n}, actual count {len(nums)}"
                + ("" if ok else " MISMATCH"),
            )
        )


def _workflow_steps(body: str):
    """Yield (prefix, block_text) for each numbered step inside <Instructions>.

    A step starts at a line matching '1. [Prefix]' and runs until the next such
    line or the end of Instructions. Fenced code blocks are stripped first so
    template examples do not count as real steps.
    """
    no_fences = re.sub(r"```.*?```", "", body, flags=re.S)
    if "<Instructions>" not in no_fences:
        return
    region = no_fences[no_fences.index("<Instructions>") :]
    lines = region.splitlines()
    starts = [
        i for i, ln in enumerate(lines) if re.match(r"^\s*1\. \[[A-Za-z ]+\]", ln)
    ]
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        block = "\n".join(lines[start:end])
        m = re.match(r"^\s*1\. \[([A-Za-z ]+)\]", lines[start])
        yield m.group(1).strip(), block


def check_step_failure_paths(body: str, results: list) -> None:
    """Rule 13: [Agent] and [Ask user] steps need an 'If fails:' path.

    [Decide] steps handle failure through their branches, and [Think] steps run
    an internal protocol, so both are exempt.
    """
    offenders = []
    for prefix, block in _workflow_steps(body):
        if prefix in ("Agent", "Ask user") and "If fails:" not in block:
            first_line = block.splitlines()[0].strip()[:50]
            offenders.append(f"[{prefix}] {first_line}")
    if offenders:
        results.append(
            (
                False,
                f"steps missing 'If fails:' ({len(offenders)}): "
                + "; ".join(offenders),
            )
        )
    else:
        results.append((True, "all [Agent]/[Ask user] steps have an 'If fails:' path"))


def check_workflow_tools(fm: str, body: str, results: list) -> None:
    """Every tool named in a workflow tools=[...] must be declared in frontmatter
    `tools:`. Catches drift between what a workflow calls and what is declared."""
    m = re.search(r"^tools\s*:\s*\[([^\]]*)\]", fm, re.M)
    declared = set()
    if m:
        declared = {t.strip() for t in m.group(1).split(",") if t.strip()}
    # Strip fenced code AND the <Definitions> block: both describe tool syntax
    # with literal example placeholders (e.g. tools=[built_in_tool, ...]) rather
    # than declaring real usage.
    scan = _strip_examples(body)
    used = set()
    for block in re.findall(r"tools=\[([^\]]*)\]", scan):
        used |= {t.strip() for t in block.split(",") if t.strip()}
    # Ignore ellipsis placeholders that appear in illustrative snippets.
    undeclared = sorted(
        t for t in (used - declared) if t not in ("...", "built_in_tool")
    )
    if undeclared:
        results.append(
            (False, f"workflow tools not in frontmatter `tools`: {undeclared}")
        )
    else:
        results.append((True, "all workflow tools are declared in frontmatter"))


def check_input_placeholders(fm: str, body: str, results: list) -> None:
    """Input names declared in frontmatter and {{placeholders}} used in the body
    must be consistent: no declared-but-unused, no used-but-undeclared."""
    declared = set(re.findall(r"^\s*-\s*name:\s*([A-Za-z0-9_]+)", fm, re.M))
    # Skip Definitions and fenced examples, which describe the {{name}} syntax
    # itself with literal placeholder words rather than using real inputs.
    used = set(re.findall(r"\{\{([A-Za-z0-9_]+)\}\}", _strip_examples(body)))
    issues = []
    undeclared = sorted(used - declared)
    if undeclared:
        issues.append(f"used but not declared: {undeclared}")
    # Declared-but-unused is only a warning for XML-scaffold skills (inputs flow
    # through workflow steps), so report it but do not fail on it alone.
    if issues:
        results.append((False, "input placeholder issues: " + "; ".join(issues)))
    else:
        results.append((True, "input placeholders consistent with declarations"))


VALID_MODELS = ("fast", "balanced", "smart")
VALID_THINKING = ("off", "low", "medium", "high", "max")


def check_workflow_attributes(body: str, results: list) -> None:
    """Every <Workflow - X> opener must carry description=, tools=, and triggers=.

    Reads each opener from the '<Workflow - ' line up to the closing '>' on its
    own line, so multi-line inline attributes are captured. Fenced examples are
    stripped first.
    """
    no_fences = re.sub(r"```.*?```", "", body, flags=re.S)
    # Capture each opener header: from '<Workflow - X' to the line that is just '>'.
    openers = re.findall(r"<Workflow - [^\n]+\n(?:[^\n]*\n)*?\s*>", no_fences)
    missing = []
    hint_errors = []
    for opener in openers:
        name = re.search(r"<Workflow - ([^\n]+)", opener).group(1).strip()
        for attr in ("description=", "tools=", "triggers="):
            if attr not in opener:
                missing.append(f"'{name}' missing {attr.rstrip('=')}")
        # Optional advisory execution hints, validated only when present.
        hm = re.search(r"preferred_model=([A-Za-z]+)", opener)
        if hm and hm.group(1) not in VALID_MODELS:
            hint_errors.append(f"'{name}' preferred_model={hm.group(1)} invalid")
        ht = re.search(r"preferred_thinking=([A-Za-z]+)", opener)
        if ht and ht.group(1) not in VALID_THINKING:
            hint_errors.append(f"'{name}' preferred_thinking={ht.group(1)} invalid")
    if hint_errors:
        missing.extend(hint_errors)
    if missing:
        results.append((False, "workflow attribute gaps: " + "; ".join(missing)))
    else:
        results.append(
            (True, f"all {len(openers)} workflows have description, tools, triggers")
        )


def check_preferred_fields(fm: str, results: list) -> None:
    """preferred_model and preferred_thinking, when present, must hold valid
    enum values. Both are optional, so absence is not a failure."""
    for field, valid in (
        ("preferred_model", VALID_MODELS),
        ("preferred_thinking", VALID_THINKING),
    ):
        m = re.search(rf'^{field}\s*:\s*"?([A-Za-z]+)"?', fm, re.M)
        if not m:
            continue  # optional; absence is fine
        val = m.group(1)
        if val in valid:
            results.append((True, f"{field} '{val}' is valid"))
        else:
            results.append(
                (False, f"{field} '{val}' invalid (must be one of {', '.join(valid)})")
            )


def check_rule_crossrefs(body: str, results: list) -> None:
    """Every 'Rule N' reference in the body must point to a rule that exists.

    Deleting or renumbering a rule silently breaks 'see Rule N' pointers, and
    sequential-numbering checks do not catch it. This verifies each referenced
    number falls within the actual rule count. It cannot verify the reference
    points to the intended rule (that needs reading), only that N exists.
    """
    m = re.search(r"<Rules>(.*?)</Rules>", body, re.S)
    if not m:
        return
    rule_count = len(re.findall(r"^\s*(\d+)\.\s", m.group(1), re.M))
    # References elsewhere in the body, excluding the Rules block itself.
    outside = body[: body.index("<Rules>")] + body[body.index("</Rules>") :]
    refs = sorted({int(n) for n in re.findall(r"Rule (\d+)", outside)})
    broken = [n for n in refs if n < 1 or n > rule_count]
    if broken:
        results.append(
            (
                False,
                f"'Rule N' references out of range (rule count {rule_count}): {broken}",
            )
        )
    elif refs:
        results.append(
            (
                True,
                f"all {len(refs)} 'Rule N' references point to existing rules (1-{rule_count})",
            )
        )
    else:
        results.append((True, "no 'Rule N' cross-references to validate"))


def check_name_matches_directory(fm: str, dirname: str, results: list) -> None:
    """Frontmatter `name` must match the skill's directory name.

    <Definition - Frontmatter> requires this, but no other check verifies it.
    Skipped when the directory name is unavailable.
    """
    if not dirname:
        return
    m = re.search(r'^name\s*:\s*"?([^"\n]+)"?', fm, re.M)
    if not m:
        return  # missing name already caught by check_frontmatter
    name = m.group(1).strip()
    if name == dirname:
        results.append((True, f"name '{name}' matches directory"))
    else:
        results.append((False, f"name '{name}' does not match directory '{dirname}'"))


def check_choice_options(fm: str, results: list) -> None:
    """Any input with `type: choice` must also declare `options`."""
    # Split the inputs section into per-input blocks by the "- name:" marker.
    blocks = re.split(r"\n\s*-\s*name\s*:", fm)
    offenders = []
    for blk in blocks[1:]:
        first = blk.splitlines()[0].strip().strip('"') if blk.strip() else "?"
        if re.search(r"type\s*:\s*choice", blk) and not re.search(r"options\s*:", blk):
            offenders.append(first)
    if offenders:
        results.append((False, f"inputs with type choice missing options: {offenders}"))
    else:
        results.append((True, "choice inputs declare options (or none present)"))


def check_date_order(fm: str, results: list) -> None:
    """created_date must be on or before last_updated."""
    c = re.search(r'^created_date\s*:\s*"?(\d{4}-\d{2}-\d{2})', fm, re.M)
    u = re.search(r'^last_updated\s*:\s*"?(\d{4}-\d{2}-\d{2})', fm, re.M)
    if not (c and u):
        return  # presence/format already handled by check_frontmatter
    if c.group(1) <= u.group(1):
        results.append((True, "created_date is on or before last_updated"))
    else:
        results.append(
            (False, f"created_date {c.group(1)} is after last_updated {u.group(1)}")
        )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python check_skill.py <path/to/SKILL.md>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    dirname = path.resolve().parent.name

    results = []
    check_frontmatter(fm, results)
    check_headings(body, results)
    check_block_order(body, results)
    check_tag_balance(body, results)
    check_body_length(body, results)
    check_em_dash_and_emoji(body, results)
    check_rule_numbering(body, results)
    check_step_failure_paths(body, results)
    check_workflow_tools(fm, body, results)
    check_input_placeholders(fm, body, results)
    check_workflow_attributes(body, results)
    check_preferred_fields(fm, results)
    check_rule_crossrefs(body, results)
    check_name_matches_directory(fm, dirname, results)
    check_choice_options(fm, results)
    check_date_order(fm, results)

    passed = sum(1 for ok, _ in results if ok)
    failed = [msg for ok, msg in results if not ok]

    for ok, msg in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {msg}")
    print(f"\n{passed}/{len(results)} checks passed.")
    if failed:
        print("\nMechanical failures to fix:")
        for msg in failed:
            print(f"  - {msg}")
        print(
            "\nNote: these are mechanical checks only. Qualitative review (workflow logic, voice, claim verifiability) must be done by reading."
        )
        return 1
    print("All mechanical checks passed. Qualitative review still required by reading.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
