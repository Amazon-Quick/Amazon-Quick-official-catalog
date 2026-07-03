#!/usr/bin/env python3
"""Locate lines, blocks, and sections in a text file, with line numbers.

An editing aid: find exactly where something lives before making a surgical
edit, without reading the whole file into context. Works on any UTF-8 text file
(SKILL.md, references, scripts, anything). Standard library only.

Modes:
  grep     Find lines matching a pattern (regex by default), with line numbers.
  block    Show the start/end line of an XML block, e.g. <Rules>...</Rules>,
           or a workflow, e.g. "Workflow - Eval".
  heading  Show the line range of a Markdown heading section (## Foo) up to the
           next heading of the same or higher level.
  rule     Show the line of a numbered rule N inside <Rules>.
  show     Print an explicit line range.

Usage:
  python locate.py <file> grep <pattern> [-i] [-C N] [--fixed]
  python locate.py <file> block <name>
  python locate.py <file> heading "<heading text>"
  python locate.py <file> rule <N>
  python locate.py <file> show <start> <end>

Examples:
  python locate.py SKILL.md grep "preferred_model"
  python locate.py SKILL.md grep "todo" -i -C 2
  python locate.py SKILL.md block Rules
  python locate.py SKILL.md block "Workflow - Eval"
  python locate.py SKILL.md heading "## Overview"
  python locate.py SKILL.md rule 12
  python locate.py SKILL.md show 120 140

Every mode prints 1-indexed line numbers so the output feeds directly into a
line-addressed edit.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def read_lines(path: str) -> list[str]:
    return Path(path).read_text(encoding="utf-8").splitlines()


def mode_grep(lines: list[str], args: argparse.Namespace) -> int:
    if args.fixed:
        pattern = re.compile(re.escape(args.pattern), re.I if args.ignore_case else 0)
    else:
        try:
            pattern = re.compile(args.pattern, re.I if args.ignore_case else 0)
        except re.error as exc:
            print(f"error: bad regex: {exc}", file=sys.stderr)
            return 2
    hits = [i for i, ln in enumerate(lines) if pattern.search(ln)]
    if not hits:
        print("no matches")
        return 1
    ctx = args.context
    printed = set()
    for i in hits:
        lo, hi = max(0, i - ctx), min(len(lines), i + ctx + 1)
        for j in range(lo, hi):
            if j in printed:
                continue
            printed.add(j)
            marker = ">" if j == i or (ctx and pattern.search(lines[j])) else " "
            print(f"{marker} {j + 1}: {lines[j]}")
        if ctx:
            print("  --")
    print(f"\n{len(hits)} match(es) on lines: {[i + 1 for i in hits]}")
    return 0


def _find_block(lines: list[str], name: str) -> tuple[int | None, int | None]:
    """Return (start_idx, end_idx) for <name>...</name> or a workflow opener.

    Workflows use inline attributes and close with '>' on their own line, so a
    name like 'Workflow - Eval' is matched from '<Workflow - Eval' to the
    matching '</Workflow - Eval>'.
    """
    open_pat = re.compile(rf"^\s*<{re.escape(name)}\b")
    close_pat = re.compile(rf"^\s*</{re.escape(name)}>")
    start = end = None
    for i, ln in enumerate(lines):
        if start is None and open_pat.search(ln):
            start = i
        elif start is not None and close_pat.search(ln):
            end = i
            break
    return start, end


def mode_block(lines: list[str], args: argparse.Namespace) -> int:
    start, end = _find_block(lines, args.name)
    if start is None:
        print(f"block <{args.name}> not found")
        return 1
    print(f"<{args.name}> opens at line {start + 1}")
    if end is None:
        print(f"  (no closing </{args.name}> found)")
        return 1
    print(f"</{args.name}> closes at line {end + 1}  ({end - start + 1} lines)")
    return 0


def mode_heading(lines: list[str], args: argparse.Namespace) -> int:
    target = args.text.strip()
    level = len(target) - len(target.lstrip("#"))
    start = None
    for i, ln in enumerate(lines):
        if ln.strip() == target:
            start = i
            break
    if start is None:
        print(f"heading '{target}' not found")
        return 1
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = lines[j].lstrip()
        if s.startswith("#"):
            lvl = len(lines[j]) - len(lines[j].lstrip("#"))
            if lvl <= level:
                end = j
                break
    print(f"'{target}' section: lines {start + 1} to {end}  ({end - start} lines)")
    return 0


def mode_rule(lines: list[str], args: argparse.Namespace) -> int:
    start, end = _find_block(lines, "Rules")
    if start is None:
        print("no <Rules> block")
        return 1
    pat = re.compile(rf"^\s*{args.number}\.\s")
    for i in range(start, end if end else len(lines)):
        if pat.search(lines[i]):
            print(f"rule {args.number} at line {i + 1}:")
            print(f"  {i + 1}: {lines[i]}")
            return 0
    print(f"rule {args.number} not found in <Rules>")
    return 1


def mode_show(lines: list[str], args: argparse.Namespace) -> int:
    lo = max(1, args.start)
    hi = min(len(lines), args.end)
    for i in range(lo - 1, hi):
        print(f"{i + 1}: {lines[i]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Locate lines, blocks, and sections in a text file."
    )
    parser.add_argument("file", help="Path to the text file.")
    sub = parser.add_subparsers(dest="mode", required=True)

    g = sub.add_parser("grep", help="Find lines matching a pattern.")
    g.add_argument("pattern")
    g.add_argument("-i", "--ignore-case", action="store_true")
    g.add_argument(
        "-C", "--context", type=int, default=0, help="Context lines around each match."
    )
    g.add_argument(
        "--fixed",
        action="store_true",
        help="Treat pattern as a literal string, not regex.",
    )

    b = sub.add_parser("block", help="Locate an XML block or workflow by name.")
    b.add_argument("name")

    h = sub.add_parser("heading", help="Locate a Markdown heading section.")
    h.add_argument("text")

    r = sub.add_parser("rule", help="Locate a numbered rule inside <Rules>.")
    r.add_argument("number", type=int)

    s = sub.add_parser("show", help="Print an explicit line range.")
    s.add_argument("start", type=int)
    s.add_argument("end", type=int)

    args = parser.parse_args()
    if not Path(args.file).is_file():
        print(f"error: not a file: {args.file}", file=sys.stderr)
        return 2

    lines = read_lines(args.file)
    return {
        "grep": mode_grep,
        "block": mode_block,
        "heading": mode_heading,
        "rule": mode_rule,
        "show": mode_show,
    }[args.mode](lines, args)


if __name__ == "__main__":
    sys.exit(main())
