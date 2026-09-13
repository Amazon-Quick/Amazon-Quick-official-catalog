---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
name: python-sandbox-code-standards
description: "Readable, correct, testable Python for the Amazon Quick sandbox: type hints, enums, Pydantic data models, one-public-method classes (SRP), constructor dependency injection, pure-vs-I/O separation, DRY via shared classes, facade and builder patterns, timestamped logging, cross-platform writes, and one dependency-injected unit test per file. Companion to quick-sandbox-code-standards."
scope: python
created_date: 2026-09-13
last_updated: 2026-09-13
origin: original
---

<purpose>
Python syntax, design, and testability rules for the Amazon Quick sandbox. These
rules make generated code modular, readable, and unit-testable by anyone. Shared
runtime rules live in quick-sandbox-code-standards.
</purpose>

<rules>
1. Type-hint every parameter and return value, including a None return.
2. Represent a finite set of related values as a (str, Enum), never raw string literals.
3. Define magic values as named constants at module top.
4. Carry structured data across function and class boundaries in a Pydantic model (preferred) or a frozen dataclass, never a dict or a tuple of positional values.
5. Parse external or unvalidated input at the boundary into a Pydantic model, then rely on that typed model downstream. Do not scatter defensive re-checks (isinstance, .get, null-guards) through code that already received a parsed model.
6. Suffix custom exceptions with Error and inherit from an existing exception. Wrap only the statement that can raise, and catch specific exceptions: no bare except, no except that passes. Raise ValueError for a violated precondition.
7. Never use a mutable default argument (use None and construct in the body), and bind the loop variable immediately when creating a closure inside a loop.
8. Do not use importlib, sys.executable, dunder attribute access, or sys.path manipulation. The sandbox blocks them. Do not import one script from another either: each runnable script is a single self-contained file (Rule 17).
9. Use pathlib and context managers for file access, and build paths from WORKSPACE_DIR. Write text with encoding="utf-8" and newline="\n" so output is byte-identical on Windows and macOS (this also keeps content hashes stable across platforms).
10. Put business logic in a class with exactly ONE public method, named for its action (SkillDigest.compute, ChecksumWriter.write). Every other method is private (leading underscore). This is the Single Responsibility Principle: one class, one reason to change. Data carriers are exempt from the one-method rule: a Pydantic model or frozen dataclass holds data and may expose fields, validators, and computed properties, but no action methods.
11. Inject collaborators and configuration that varies through __init__ (constructor dependency injection). __init__ only assigns its arguments to attributes: no I/O, parsing, or other fallible work. Do the reading and parsing inside the public method. Reference static module constants directly rather than injecting them.
12. Separate pure logic from I/O so the logic is unit-testable without a filesystem or network. A pure class receives already-loaded data (a string, a list, a manifest) through __init__ and returns a result. An I/O class only reads or writes. The I/O class depends on the pure class, never the reverse (Dependency Inversion).
13. State shared logic once (DRY): put it in one class and have the other classes in the same file use it. Because each runnable script is a single self-contained file that cannot import another (Rule 17), avoid cross-script sharing by giving each concern a single owner, never by duplicating logic across scripts. For example, create_checksum.py owns computing and writing the checksum; the validator does not recompute it, it only checks that the frontmatter carries a well-formed checksum field.
14. When an action composes several collaborators, expose a facade: one class with a single public method that wires the collaborators together and returns the result. Callers depend on the facade, not on its internal parts.
15. Assemble a complex artifact with a builder: a dedicated class whose single public method combines the parts and returns the finished model. Keep reading (an I/O class), assembling (the builder, pure), and writing (an I/O class) as separate single-purpose classes.
16. Emit progress, diagnostics, and any human-readable result through the logging module with timestamps. The sandbox returns only stdout (a script's stderr is discarded), so route logging to stdout through a small `_PrintStream` adapter and configure it once at module top with `logging.basicConfig(stream=_PrintStream(), force=True)`. Write durable output to files (Rule 9) rather than hand-printing it, and keep bare `print()` out of the code except inside the stream adapter.
17. Give a runnable script a verb_noun action name from the standard prefix set (create_, check_, find_, run_) and a standard entry point: an argparse.ArgumentParser, a main() that returns an exit code, and an if __name__ == "__main__" guard. Logging is configured once at module top (Rule 16); main() parses arguments, constructs one class (usually a facade or builder), and calls its single method. A runnable script is a single self-contained file: define all of its classes in that one file and import only the standard library and packages from the sandbox manifest, never another script.
18. Ship one unit test per source file, named test_<module>.py beside it, that constructs inputs through dependency injection and asserts on a pure class with no filesystem or network access. Test the pure logic class, not the I/O wrapper. The test imports the module under test; this development-time import is the one place one file imports another, and it never runs in the skill's sandbox flow.
</rules>

<examples>
<example type="correct">
```python
# SRP + DI + pure-vs-I/O split + facade. Each class has one public method.
from pathlib import Path

from pydantic import BaseModel


class LineCount(BaseModel):  # data carrier: no action method (Rule 4, 10)
    non_empty: int


class LineReader:  # I/O only; __init__ just assigns (Rule 11)
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> list[str]:
        return self.path.read_text(encoding="utf-8").splitlines()


class LineCounter:  # pure; injected list; unit-tested without disk (Rule 12, 18)
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    def count(self) -> LineCount:
        return LineCount(non_empty=sum(1 for line in self.lines if line.strip()))


class LineCountReport:  # facade: one public method wires collaborators (Rule 14)
    def __init__(self, path: Path) -> None:
        self.path = path

    def build(self) -> LineCount:
        return LineCounter(LineReader(self.path).read()).count()
```
</example>

<example type="correct">
```python
# Builder assembles a model from parts (Rule 15). Pure: injected records in,
# finished model out, no I/O.
from pydantic import BaseModel


class Summary(BaseModel):
    name: str
    total: int


class SummaryBuilder:
    def __init__(self, name: str, counts: list[LineCount]) -> None:
        self.name = name
        self.counts = counts

    def build(self) -> Summary:
        return Summary(name=self.name, total=sum(c.non_empty for c in self.counts))
```
</example>

<example type="correct">
```python
# Entry point: verb_noun name (count_lines.py). Logging is configured once at
# module top and routed to stdout via _PrintStream, since the sandbox returns
# only stdout; main() constructs one facade and calls it (Rules 16, 17).
import argparse
import logging
import sys
from pathlib import Path


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Count non-empty lines in a file.")
    parser.add_argument("path")
    args = parser.parse_args()

    logger.info("Counting lines in %s", args.path)   # progress -> stdout
    result = LineCountReport(Path(args.path)).build()
    logger.info("non_empty=%d", result.non_empty)    # result -> stdout
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
</example>

<example type="correct">
```python
# One dependency-injected unit test per file, no filesystem (Rule 18).
import unittest


class TestLineCounter(unittest.TestCase):
    def test_counts_only_non_empty_lines(self) -> None:
        counter = LineCounter(["alpha", "", "   ", "beta"])  # injected, no disk
        self.assertEqual(counter.count().non_empty, 2)


if __name__ == "__main__":
    unittest.main()
```
</example>

<example type="incorrect">
```python
# God class with several public methods (10), I/O and no encoding in __init__
# (9, 11), a dict across a boundary (4), and progress mixed into stdout (16).
class Records:
    def __init__(self, path):                 # no type hints (1); reads in __init__ (11)
        self.lines = open(path).read().split("\n")  # no encoding/newline (9)

    def count(self): ...                      # multiple public methods on a
    def summarize(self): ...                  # logic class violates SRP (10)

    def write(self, out):
        print("writing report...")            # bare print instead of logging (16)
        return {"total": len(self.lines)}     # dict across a boundary (4)
```
</example>
</examples>

<references>
- #[[file:references/quick-sandbox-code-standards.md]] - Shared runtime rules
- #[[file:references/quick-sandbox-requirements.txt]] - Python package manifest (names only)
- https://docs.pydantic.dev/latest/ - Pydantic
- https://docs.python.org/3/library/enum.html - Enum
- https://docs.python-guide.org/writing/gotchas/ - Mutable defaults, late-binding closures
- https://docs.python.org/3/library/argparse.html - argparse
- https://docs.python.org/3/library/logging.html - logging
- https://docs.python.org/3/library/unittest.html - unittest
- https://refactoring.guru/design-patterns/facade - Facade pattern
- https://refactoring.guru/design-patterns/builder - Builder pattern
</references>
