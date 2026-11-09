"""
description: Locate lines, XML blocks, Markdown headings, numbered rules, or an explicit line range in a UTF-8 text file and print 1-based line numbers, so an agent can make a surgical edit without reading the whole file. Run as: python find_lines.py <file> <mode> ... (modes: grep, block, heading, rule, show).
last_updated: 2026-09-13
origin: original

"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class _PrintStream:
    """Routes log records to stdout via print (the sandbox only returns stdout)."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=_PrintStream(),
    force=True,
)
logger = logging.getLogger(__name__)


class Mode(StrEnum):
    """The kinds of location a run can request."""

    GREP = "grep"
    BLOCK = "block"
    HEADING = "heading"
    RULE = "rule"
    SHOW = "show"


class LineHit(BaseModel):
    """A single located line: its 1-based number and text."""

    number: int
    text: str

    def render(self) -> str:
        return f"{self.number}: {self.text}"


class LocateResult(BaseModel):
    """Base result: every result knows whether it found something and how to
    render itself, so callers never branch on the result type."""

    @property
    def found(self) -> bool:
        raise NotImplementedError

    @property
    def report(self) -> str:
        raise NotImplementedError


class LineHitsResult(LocateResult):
    """Result for modes that return a set of lines (grep, show)."""

    hits: list[LineHit]

    @property
    def found(self) -> bool:
        return bool(self.hits)

    @property
    def report(self) -> str:
        if not self.hits:
            return "no matches"
        return "\n".join(hit.render() for hit in self.hits)


class BlockResult(LocateResult):
    name: str
    start: int | None
    end: int | None

    @property
    def found(self) -> bool:
        return self.start is not None

    @property
    def report(self) -> str:
        if self.start is None:
            return f"block <{self.name}> not found"
        if self.end is None:
            return f"<{self.name}> opens at line {self.start} (no closing tag found)"
        return f"<{self.name}> lines {self.start}..{self.end} ({self.end - self.start + 1} lines)"


class SectionResult(LocateResult):
    title: str
    start: int | None
    end: int | None

    @property
    def found(self) -> bool:
        return self.start is not None

    @property
    def report(self) -> str:
        if self.start is None:
            return f"heading '{self.title}' not found"
        return f"'{self.title}' lines {self.start}..{self.end}"


class RuleResult(LocateResult):
    number: int
    hit: LineHit | None

    @property
    def found(self) -> bool:
        return self.hit is not None

    @property
    def report(self) -> str:
        if self.hit is None:
            return f"rule {self.number} not found in <Rules>"
        return self.hit.render()


class FileLines:
    """Reads a text file into a list of lines (I/O)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> list[str]:
        """Return the file's lines without trailing newlines."""
        return self.path.read_text(encoding="utf-8").splitlines()


class GrepLocator:
    """Finds lines matching a pattern (pure)."""

    def __init__(
        self, lines: list[str], pattern: str, ignore_case: bool, fixed: bool
    ) -> None:
        self.lines = lines
        self.pattern = pattern
        self.ignore_case = ignore_case
        self.fixed = fixed

    def locate(self) -> LineHitsResult:
        """Return every line matching the pattern."""
        raw = re.escape(self.pattern) if self.fixed else self.pattern
        compiled = re.compile(raw, re.I if self.ignore_case else 0)
        hits = [
            LineHit(number=i + 1, text=line)
            for i, line in enumerate(self.lines)
            if compiled.search(line)
        ]
        return LineHitsResult(hits=hits)


class BlockLocator:
    """Finds the open/close line of an XML block or workflow by name (pure)."""

    def __init__(self, lines: list[str], name: str) -> None:
        self.lines = lines
        self.name = name

    def locate(self) -> BlockResult:
        """Return the 1-based start and end lines of the named block."""
        open_re = re.compile(rf"^\s*<{re.escape(self.name)}\b")
        close_re = re.compile(rf"^\s*</{re.escape(self.name)}>")
        start = end = None
        for i, line in enumerate(self.lines):
            if start is None and open_re.search(line):
                start = i + 1
            elif start is not None and close_re.search(line):
                end = i + 1
                break
        return BlockResult(name=self.name, start=start, end=end)


class HeadingLocator:
    """Finds a Markdown heading's section range (pure)."""

    def __init__(self, lines: list[str], text: str) -> None:
        self.lines = lines
        self.text = text

    def locate(self) -> SectionResult:
        """Return the section from the heading to the next same-or-higher heading."""
        target = self.text.strip()
        level = len(target) - len(target.lstrip("#"))
        start = next(
            (i for i, line in enumerate(self.lines) if line.strip() == target), None
        )
        if start is None:
            return SectionResult(title=target, start=None, end=None)
        end = len(self.lines)
        for j in range(start + 1, len(self.lines)):
            stripped = self.lines[j].lstrip()
            if stripped.startswith("#"):
                depth = len(self.lines[j]) - len(self.lines[j].lstrip("#"))
                if depth <= level:
                    end = j
                    break
        return SectionResult(title=target, start=start + 1, end=end)


class RuleLocator:
    """Finds a numbered rule inside a <Rules> block (pure)."""

    def __init__(self, lines: list[str], number: int) -> None:
        self.lines = lines
        self.number = number

    def locate(self) -> RuleResult:
        """Return the line carrying "<number>. " within <Rules>, if present."""
        block = BlockLocator(self.lines, "Rules").locate()
        if block.start is None:
            return RuleResult(number=self.number, hit=None)
        end = block.end or len(self.lines)
        pattern = re.compile(rf"^\s*{self.number}\.\s")
        for i in range(block.start - 1, end):
            if pattern.search(self.lines[i]):
                return RuleResult(
                    number=self.number, hit=LineHit(number=i + 1, text=self.lines[i])
                )
        return RuleResult(number=self.number, hit=None)


class RangeLocator:
    """Returns an explicit inclusive 1-based line range (pure)."""

    def __init__(self, lines: list[str], start: int, end: int) -> None:
        self.lines = lines
        self.start = start
        self.end = end

    def locate(self) -> LineHitsResult:
        """Return the lines in [start, end], clamped to the file."""
        lo = max(1, self.start)
        hi = min(len(self.lines), self.end)
        hits = [LineHit(number=i + 1, text=self.lines[i]) for i in range(lo - 1, hi)]
        return LineHitsResult(hits=hits)


class LineFinder:
    """Facade: build the locator for the requested mode and return its result."""

    def __init__(self, lines: list[str], args: argparse.Namespace) -> None:
        self.lines = lines
        self.args = args

    def find(self) -> LocateResult:
        """Dispatch on the Mode enum to the matching locator and return its result."""
        args = self.args
        match Mode(args.mode):
            case Mode.GREP:
                return GrepLocator(
                    self.lines, args.pattern, args.ignore_case, args.fixed
                ).locate()
            case Mode.BLOCK:
                return BlockLocator(self.lines, args.name).locate()
            case Mode.HEADING:
                return HeadingLocator(self.lines, args.text).locate()
            case Mode.RULE:
                return RuleLocator(self.lines, args.number).locate()
            case Mode.SHOW:
                return RangeLocator(self.lines, args.start, args.end).locate()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Locate lines, blocks, and sections in a file."
    )
    parser.add_argument("file", help="Path to the text file.")
    sub = parser.add_subparsers(dest="mode", required=True)

    grep = sub.add_parser(Mode.GREP.value, help="Find lines matching a pattern.")
    grep.add_argument("pattern")
    grep.add_argument("-i", "--ignore-case", action="store_true")
    grep.add_argument("--fixed", action="store_true", help="Literal string, not regex.")

    block = sub.add_parser(Mode.BLOCK.value, help="Locate an XML block or workflow.")
    block.add_argument("name")

    heading = sub.add_parser(
        Mode.HEADING.value, help="Locate a Markdown heading section."
    )
    heading.add_argument("text")

    rule = sub.add_parser(
        Mode.RULE.value, help="Locate a numbered rule inside <Rules>."
    )
    rule.add_argument("number", type=int)

    show = sub.add_parser(Mode.SHOW.value, help="Print an explicit line range.")
    show.add_argument("start", type=int)
    show.add_argument("end", type=int)
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    path = Path(args.file)
    if not path.is_file():
        logger.error("Not a file: %s", path)
        return 2

    logger.info("Locating %s in %s", args.mode, path)
    result = LineFinder(FileLines(path).read(), args).find()
    logger.info("%s", result.report)
    return 0 if result.found else 1


if __name__ == "__main__":
    sys.exit(main())
