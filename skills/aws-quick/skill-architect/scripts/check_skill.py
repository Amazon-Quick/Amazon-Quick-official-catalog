"""
description: Run the mechanical pass/fail checks on a SKILL.md (frontmatter fields, naming, length limits, XML tag balance, block order, em dashes and emojis, rule numbering and references, declared and unused tools, file headers, the checksum, and eval fixtures no case uses), plus staleness WARNINGs for files over six months old and for superseded eval summaries. Qualitative review is done by reading, not here.
last_updated: 2026-11-20

Usage:
    python check_skill.py <path/to/SKILL.md>
    In AWS Quick: import check_skill; check_skill.main(["<path/to/SKILL.md>"])
"""

from __future__ import annotations

import argparse
import datetime
import logging
import re
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from create_checksum import ManifestDigest, SkillManifest
from run_rules import (
    RULES_DIR,
    CheckRunner,
    Level,
    Rule,
    RuleId,
    RuleLoader,
    SkillFile,
    SkillSource,
    SkillView,
    Status,
)


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

# Six calendar months, per the staleness rule in references/reference-file-standard.md.
STALENESS_MONTHS = 6

BLOCK_ORDER = (
    "Goal",
    "Definitions",
    "Rules",
    "Agent Annotations",
    "Gotchas",
    "Instructions",
    "Resources",
)

# Compiled once, named for intent, referenced wherever needed.
FENCE_RE = re.compile(r"```.*?```", re.S)
DEFINITIONS_RE = re.compile(r"<Definitions>.*?</Definitions>", re.S)
RULES_BLOCK_RE = re.compile(r"^<Rules>(.*?)</Rules>\s*$", re.S | re.M)
NAME_RE = re.compile(r'^name\s*:\s*"?([^"\n]+)"?', re.M)
PAIRED_OPEN_RE = re.compile(r"^\s*<([A-Z][A-Za-z ]*?)>\s*$", re.M)
PAIRED_CLOSE_RE = re.compile(r"^\s*</([A-Z][A-Za-z ]*?)>\s*$", re.M)
WORKFLOW_OPEN_RE = re.compile(r"^\s*<Workflow - [^\n>]*$", re.M)
WORKFLOW_CLOSE_RE = re.compile(r"^\s*</Workflow - [^\n>]+>\s*$", re.M)
WORKFLOW_OPENER_RE = re.compile(r"<Workflow - [^\n]+\n(?:[^\n]*\n)*?\s*>")
WORKFLOW_NAME_RE = re.compile(r"<Workflow - ([^\n]+)")
RULE_NUMBER_RE = re.compile(r"^(\d+)\.\s", re.M)
RULE_SELF_REF_RE = re.compile(r"Rules \(1-(\d+)\)")
RULE_CROSSREF_RE = re.compile(r"Rule (\d+)")
STEP_START_RE = re.compile(r"^\s*1\. \[[A-Za-z ]+\]")
STEP_PREFIX_RE = re.compile(r"^\s*1\. \[([A-Za-z ]+)\]")
FRONTMATTER_TOOLS_RE = re.compile(r"^tools\s*:\s*\[([^\]]*)\]", re.M)
WORKFLOW_TOOLS_RE = re.compile(r"tools=\[([^\]]*)\]")
INPUT_NAME_RE = re.compile(r"^\s*-\s*name:\s*([A-Za-z0-9_]+)", re.M)
PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")
INPUT_SPLIT_RE = re.compile(r"\n\s*-\s*name\s*:")
CHECKSUM_VALUE_RE = re.compile(r'^checksum\s*:\s*"?sha256:[0-9a-f]{64}"?\s*$', re.M)
CHECKSUM_CAPTURE_RE = re.compile(r'^checksum\s*:\s*"?(sha256:[0-9a-f]{64})"?', re.M)
LAST_UPDATED_VALUE_RE = re.compile(r'^last_updated\s*:\s*"?(\d{4}-\d{2}-\d{2})', re.M)
SKILL_FILENAME = "SKILL.md"
# Reference-file header standard: every references/*.md and scripts/*.py must
# declare description and last_updated; an optional sources field lists URLs.
HEADER_DESCRIPTION_RE = re.compile(r"^description\s*:", re.M)
HEADER_LAST_UPDATED_RE = re.compile(r"^last_updated\s*:", re.M)
SOURCES_KEY_RE = re.compile(r"^sources\s*:(.*)$", re.M)
SOURCE_ITEM_RE = re.compile(r"^\s+-\s*(.*?)\s*$")
URL_RE = re.compile(r"^https?://\S+$")
SOURCES_PROBLEM = "sources (must be a list of URLs)"
# Placeholder names a workflow's tools=[...] example may use; never real tools.
TOOL_PLACEHOLDERS = frozenset({"...", "built_in_tool"})
PY_DOCSTRING_RE = re.compile(r'"""(.*?)"""', re.S)
MD_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S)
HEADER_FILE_GROUPS = (("references", "*.md"), ("scripts", "*.py"))
EVAL_SUMMARY_GLOB = "eval_result_*.md"
EVAL_REFERENCE_GLOBS = ("evals.json", "**/*.py")


class CheckStatus(StrEnum):
    """Outcome category for a single check result."""

    PASS = "PASS"  # nosec B105  # enum status label, not a credential
    FAIL = "FAIL"
    WARNING = "WARNING"


@dataclass(frozen=True)
class CheckResult:
    """One check outcome: a status category and a natural-language reason."""

    status_code: CheckStatus
    status_reason: str

    @classmethod
    def passed(cls, reason: str) -> CheckResult:
        return cls(CheckStatus.PASS, reason)

    @classmethod
    def failed(cls, reason: str) -> CheckResult:
        return cls(CheckStatus.FAIL, reason)

    @classmethod
    def warned(cls, reason: str) -> CheckResult:
        return cls(CheckStatus.WARNING, reason)

    @classmethod
    def of(cls, ok: bool, reason: str) -> CheckResult:
        return cls(CheckStatus.PASS if ok else CheckStatus.FAIL, reason)


@dataclass(frozen=True)
class ValidationReport:
    """The rolled-up result of every applicable check for one document."""

    results: list[CheckResult]

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if r.status_code is CheckStatus.FAIL]

    @property
    def warnings(self) -> list[CheckResult]:
        return [r for r in self.results if r.status_code is CheckStatus.WARNING]

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0


@dataclass(frozen=True)
class SkillDocument:
    """A parsed SKILL.md: frontmatter, body, and the directory it lives in.

    Parsed once at the boundary (from_path) so checks receive a trusted value
    object instead of re-reading or re-parsing the file.
    """

    frontmatter: str
    body: str
    dirname: str
    skill_dir: Path | None = None

    @classmethod
    def from_path(cls, path: Path) -> SkillDocument:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        fences = [i for i, ln in enumerate(lines) if ln.strip() == "---"]
        if len(fences) >= 2:
            frontmatter = "\n".join(lines[fences[0] + 1 : fences[1]])
            body = "\n".join(lines[fences[1] + 1 :])
        else:
            frontmatter, body = "", text
        resolved = path.resolve().parent
        return cls(
            frontmatter=frontmatter,
            body=body,
            dirname=resolved.name,
            skill_dir=resolved,
        )

    def body_without_fences(self) -> str:
        return FENCE_RE.sub("", self.body)

    def body_without_examples(self) -> str:
        """Body with fenced code and the Definitions block removed, since both
        carry illustrative syntax that must not count as real usage."""
        return DEFINITIONS_RE.sub("", self.body_without_fences())

    def rules_block(self) -> str | None:
        """The inner text of <Rules>...</Rules>, or None when absent."""
        m = RULES_BLOCK_RE.search(self.body)
        return m.group(1) if m else None

    def rule_numbers(self) -> list[int]:
        block = self.rules_block()
        return [int(n) for n in RULE_NUMBER_RE.findall(block)] if block else []

    def name_value(self) -> str | None:
        m = NAME_RE.search(self.frontmatter)
        return m.group(1).strip() if m else None

    def last_updated(self) -> str | None:
        """The last_updated date string from frontmatter, or None if absent."""
        m = LAST_UPDATED_VALUE_RE.search(self.frontmatter)
        return m.group(1) if m else None

    def checksum_value(self) -> str | None:
        """The stored sha256 checksum from frontmatter, or None if absent."""
        m = CHECKSUM_CAPTURE_RE.search(self.frontmatter)
        return m.group(1) if m else None


class StalenessEvaluator:
    """Decides whether an ISO last_updated date is stale: strictly more than
    `months` calendar months before the injected reference date (pure)."""

    def __init__(
        self, reference_date: datetime.date, months: int = STALENESS_MONTHS
    ) -> None:
        self.reference_date = reference_date
        self.months = months

    def is_stale(self, last_updated: str) -> bool:
        """True when last_updated parses and falls before the cutoff. An unparseable
        date is left to the date-format and header checks, not judged here."""
        parsed = self._parse(last_updated)
        return parsed is not None and parsed < self._cutoff()

    def _cutoff(self) -> datetime.date:
        """The oldest date still considered current: `months` calendar months back,
        clamping the day so a short target month stays a real date."""
        zero_based = self.reference_date.month - 1 - self.months
        year = self.reference_date.year + zero_based // 12
        month = zero_based % 12 + 1
        day = min(self.reference_date.day, self._last_day_of_month(year, month))
        return datetime.date(year, month, day)

    @staticmethod
    def _last_day_of_month(year: int, month: int) -> int:
        if month == 12:
            return 31
        return (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day

    @staticmethod
    def _parse(value: str) -> datetime.date | None:
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None


class Check(Protocol):
    """A single validation. Returns one result, or None when not applicable."""

    def run(self, document: SkillDocument) -> CheckResult | None: ...


class _RuleFileCheck:
    """Runs one standard check from references/rules/standard_rule.json through
    the rule engine, and reports it as a PASS, FAIL, or WARNING with the rule's
    message, so the output matches what the catalog build parses."""

    def __init__(self, rule: Rule, check_id: str) -> None:
        self.rule = rule
        self.check = next(c for c in rule.checks if c.id == check_id)

    def run(self, document: SkillDocument) -> CheckResult | None:
        text = f"---\n{document.frontmatter}\n---\n{document.body}"
        skill = SkillFile(path=SKILL_FILENAME, data=text.encode("utf-8"))
        view = SkillView.from_source(SkillSource(location="", root="", files=[skill]))
        results = CheckRunner(self.rule, self.check, view).run()
        if not results:
            return None
        result = results[0]
        if result.status is Status.PASSED:
            return CheckResult.passed(result.message)
        if result.level is Level.WARNING:
            return CheckResult.warned(result.message)
        return CheckResult.failed(result.message)


class _BlockOrderCheck:
    """Present canonical blocks appear in the defined relative order."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        no_fences = document.body_without_fences()
        seen = [
            block
            for block in BLOCK_ORDER
            if re.search(rf"^<{re.escape(block)}>", no_fences, re.M)
        ]
        canonical = [b for b in BLOCK_ORDER if b in seen]
        if seen == canonical:
            return CheckResult.passed(f"block ordering correct ({', '.join(seen)})")
        return CheckResult.failed(
            f"block ordering off: found {seen}, expected order {canonical}"
        )


class _TagBalanceCheck:
    """Every paired block and workflow opener has a matching close."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        no_fences = document.body_without_fences()
        opens = PAIRED_OPEN_RE.findall(no_fences)
        closes = PAIRED_CLOSE_RE.findall(no_fences)
        wf_opens = WORKFLOW_OPEN_RE.findall(no_fences)
        wf_closes = WORKFLOW_CLOSE_RE.findall(no_fences)
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
            return CheckResult.failed("tag balance issues: " + "; ".join(unbalanced))
        return CheckResult.passed("all block and workflow tags balanced")


class _RuleSequentialNumberingCheck:
    """Rules are numbered sequentially from 1."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        if document.rules_block() is None:
            return None
        nums = document.rule_numbers()
        if not nums:
            return CheckResult.failed("Rules block present but no numbered rules found")
        if nums == list(range(1, len(nums) + 1)):
            return CheckResult.passed(f"rules numbered sequentially 1-{len(nums)}")
        return CheckResult.failed(f"rule numbering not sequential: {nums}")


class _RuleSelfReferenceCheck:
    """A 'Rules (1-N)' self-reference matches the actual rule count.

    Only applies when numbering is sequential, mirroring the original: a
    non-sequential block reports that failure and does not also self-check.
    """

    def run(self, document: SkillDocument) -> CheckResult | None:
        block = document.rules_block()
        if block is None:
            return None
        nums = document.rule_numbers()
        if not nums or nums != list(range(1, len(nums) + 1)):
            return None
        ref = RULE_SELF_REF_RE.search(block)
        if not ref:
            return None
        n = int(ref.group(1))
        ok = n == len(nums)
        return CheckResult.of(
            ok,
            f"rule self-reference says 1-{n}, actual count {len(nums)}"
            + ("" if ok else " MISMATCH"),
        )


class _StepFailurePathCheck:
    """[Agent] and [Ask user] steps declare an 'If fails:' path."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        offenders = []
        for prefix, block in self._workflow_steps(document.body):
            if prefix in ("Agent", "Ask user") and "If fails:" not in block:
                offenders.append(f"[{prefix}] {block.splitlines()[0].strip()[:50]}")
        if offenders:
            return CheckResult.failed(
                f"steps missing 'If fails:' ({len(offenders)}): " + "; ".join(offenders)
            )
        return CheckResult.passed(
            "all [Agent]/[Ask user] steps have an 'If fails:' path"
        )

    @staticmethod
    def _workflow_steps(body: str):
        no_fences = FENCE_RE.sub("", body)
        if "<Instructions>" not in no_fences:
            return
        region = no_fences[no_fences.index("<Instructions>") :]
        lines = region.splitlines()
        starts = [i for i, ln in enumerate(lines) if STEP_START_RE.match(ln)]
        for idx, start in enumerate(starts):
            end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
            block = "\n".join(lines[start:end])
            yield STEP_PREFIX_RE.match(lines[start]).group(1).strip(), block


@dataclass(frozen=True)
class ToolUsage:
    """The tools a SKILL.md declares in frontmatter and the tools its workflows use."""

    declared: frozenset[str]
    used: frozenset[str]


class ToolUsageReader:
    """Reads a document's declared and workflow-used tools (pure)."""

    def __init__(self, document: SkillDocument) -> None:
        self.document = document

    def read(self) -> ToolUsage:
        m = FRONTMATTER_TOOLS_RE.search(self.document.frontmatter)
        declared = (
            {t.strip() for t in m.group(1).split(",") if t.strip()} if m else set()
        )
        used: set[str] = set()
        for block in WORKFLOW_TOOLS_RE.findall(self.document.body_without_examples()):
            used |= {t.strip() for t in block.split(",") if t.strip()}
        return ToolUsage(
            declared=frozenset(declared), used=frozenset(used - TOOL_PLACEHOLDERS)
        )


class _WorkflowToolsCheck:
    """Every tool used in a workflow tools=[...] is declared in frontmatter."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        usage = ToolUsageReader(document).read()
        undeclared = sorted(usage.used - usage.declared)
        if undeclared:
            return CheckResult.failed(
                f"workflow tools not in frontmatter `tools`: {undeclared}"
            )
        return CheckResult.passed("all workflow tools are declared in frontmatter")


class _UnusedToolsCheck:
    """WARNING when a tool declared in frontmatter is used by no workflow, so a
    skill holds no more tools than its workflows need (least privilege). A
    warning, not a failure, until existing skills drop their unused tools."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        usage = ToolUsageReader(document).read()
        if not usage.declared:
            return None
        unused = sorted(usage.declared - usage.used)
        if unused:
            return CheckResult.warned(f"frontmatter `tools` no workflow uses: {unused}")
        return CheckResult.passed("every declared tool is used by a workflow")


class _InputPlaceholderCheck:
    """Declared inputs and {{placeholders}} used in the body stay consistent."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        declared = set(INPUT_NAME_RE.findall(document.frontmatter))
        used = set(PLACEHOLDER_RE.findall(document.body_without_examples()))
        undeclared = sorted(used - declared)
        if undeclared:
            return CheckResult.failed(
                f"input placeholder issues: used but not declared: {undeclared}"
            )
        return CheckResult.passed("input placeholders consistent with declarations")


class _WorkflowAttributesCheck:
    """Every workflow opener carries description=, tools=, and triggers=."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        openers = WORKFLOW_OPENER_RE.findall(document.body_without_fences())
        missing = []
        for opener in openers:
            name = WORKFLOW_NAME_RE.search(opener).group(1).strip()
            for attr in ("description=", "tools=", "triggers="):
                if attr not in opener:
                    missing.append(f"'{name}' missing {attr.rstrip('=')}")
        if missing:
            return CheckResult.failed("workflow attribute gaps: " + "; ".join(missing))
        return CheckResult.passed(
            f"all {len(openers)} workflows have description, tools, triggers"
        )


class _RuleCrossRefCheck:
    """Every 'Rule N' reference in the body, including one rule citing another,
    points to a rule that exists."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        if document.rules_block() is None:
            return None
        rule_count = len(document.rule_numbers())
        refs = sorted({int(n) for n in RULE_CROSSREF_RE.findall(document.body)})
        broken = [n for n in refs if n < 1 or n > rule_count]
        if broken:
            return CheckResult.failed(
                f"'Rule N' references out of range (rule count {rule_count}): {broken}"
            )
        if refs:
            return CheckResult.passed(
                f"all {len(refs)} 'Rule N' references point to existing rules (1-{rule_count})"
            )
        return CheckResult.passed("no 'Rule N' cross-references to validate")


class _NameMatchesDirectoryCheck:
    """Frontmatter name matches the skill directory name."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        if not document.dirname:
            return None
        name = document.name_value()
        if name is None:
            return None
        if name == document.dirname:
            return CheckResult.passed(f"name '{name}' matches directory")
        return CheckResult.failed(
            f"name '{name}' does not match directory '{document.dirname}'"
        )


class _ChoiceOptionsCheck:
    """Any input with type: choice also declares options."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        blocks = INPUT_SPLIT_RE.split(document.frontmatter)
        offenders = []
        for blk in blocks[1:]:
            first = blk.splitlines()[0].strip().strip('"') if blk.strip() else "?"
            if re.search(r"type\s*:\s*choice", blk) and not re.search(
                r"options\s*:", blk
            ):
                offenders.append(first)
        if offenders:
            return CheckResult.failed(
                f"inputs with type choice missing options: {offenders}"
            )
        return CheckResult.passed("choice inputs declare options (or none present)")


class _DateOrderCheck:
    """created_date is on or before last_updated."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        c = re.search(
            r'^created_date\s*:\s*"?(\d{4}-\d{2}-\d{2})', document.frontmatter, re.M
        )
        u = re.search(
            r'^last_updated\s*:\s*"?(\d{4}-\d{2}-\d{2})', document.frontmatter, re.M
        )
        if not (c and u):
            return None
        if c.group(1) <= u.group(1):
            return CheckResult.passed("created_date is on or before last_updated")
        return CheckResult.failed(
            f"created_date {c.group(1)} is after last_updated {u.group(1)}"
        )


class _SkillChecksumFieldCheck:
    """The frontmatter carries a well-formed checksum (sha256 + 64 hex chars).

    Only the field's presence and format are validated. create_checksum.py owns
    computing the digest, so this check never recomputes it.
    """

    def run(self, document: SkillDocument) -> CheckResult | None:
        line = re.search(r"^checksum\s*:.*$", document.frontmatter, re.M)
        if line is None:
            return CheckResult.failed("checksum field missing (run create_checksum.py)")
        ok = bool(CHECKSUM_VALUE_RE.search(document.frontmatter))
        return CheckResult.of(
            ok,
            (
                "checksum field well-formed (sha256:<64 hex>)"
                if ok
                else f"checksum field malformed: {line.group(0).strip()}"
            ),
        )


class _ChecksumIntegrityCheck:
    """FAILs when the stored checksum does not match a recomputed digest. Field
    presence and format stay _SkillChecksumFieldCheck's job; skipped when there is
    no stored checksum or no skill_dir (a hand-built SkillDocument in a test)."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        if document.skill_dir is None:
            return None
        stored = document.checksum_value()
        if stored is None:
            return None
        computed = ManifestDigest(SkillManifest(document.skill_dir).collect()).compute()
        if stored == computed:
            return CheckResult.passed("checksum matches recomputed digest")
        return CheckResult.failed(
            f"checksum mismatch: stored {stored}, computed {computed} "
            "(files changed; run create_checksum.py to regenerate)"
        )


class HeaderExtractor:
    """Extracts a skill file's header text (pure): a .py module docstring, or the
    YAML frontmatter of a .md file."""

    def __init__(self, text: str, is_python: bool) -> None:
        self.text = text
        self.is_python = is_python

    def extract(self) -> str:
        if self.is_python:
            match = PY_DOCSTRING_RE.search(self.text)
            return match.group(1) if match else ""
        match = MD_FRONTMATTER_RE.match(self.text)
        return match.group(1) if match else ""


class SourcesValidator:
    """Checks an optional `sources` header field (pure): when present, it is a
    YAML list whose every item is an http or https URL."""

    def __init__(self, header: str) -> None:
        self.header = header

    def is_valid(self) -> bool:
        match = SOURCES_KEY_RE.search(self.header)
        if match is None:
            return True
        inline = match.group(1).strip()
        if inline:
            items = [i.strip().strip("\"'") for i in inline.strip("[]").split(",")]
        else:
            items = self._block_items(self.header[match.end() :])
        return bool(items) and all(URL_RE.match(item) for item in items if item)

    @staticmethod
    def _block_items(rest: str) -> list[str]:
        items = []
        for line in rest.splitlines()[1:]:
            item = SOURCE_ITEM_RE.match(line)
            if item is None:
                break
            items.append(item.group(1).strip("\"'"))
        return items


class FileHeaderValidator:
    """Validates that a file's header carries the required fields (pure).

    Given a file's text and whether it is Python, it extracts the header (the
    module docstring for .py, the YAML frontmatter for .md) and returns the list
    of problems: a missing description or last_updated, or a malformed sources.
    """

    def __init__(self, text: str, is_python: bool) -> None:
        self.text = text
        self.is_python = is_python

    def validate(self) -> list[str]:
        """Return the header problems (empty if valid)."""
        header = self._header()
        missing = []
        if not HEADER_DESCRIPTION_RE.search(header):
            missing.append("description")
        if not HEADER_LAST_UPDATED_RE.search(header):
            missing.append("last_updated")
        if not SourcesValidator(header).is_valid():
            missing.append(SOURCES_PROBLEM)
        return missing

    def _header(self) -> str:
        return HeaderExtractor(self.text, self.is_python).extract()


class HeaderFileFinder:
    """Lists every file that must carry a header: assets/README.md,
    references/*.md, scripts/*.py (I/O)."""

    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir

    def find(self) -> list[Path]:
        found: list[Path] = []
        readme = self.skill_dir / "assets" / "README.md"
        if readme.is_file():
            found.append(readme)
        for sub, pattern in HEADER_FILE_GROUPS:
            base = self.skill_dir / sub
            if not base.is_dir():
                continue
            found.extend(
                path
                for path in sorted(base.rglob(pattern))
                if "__pycache__" not in path.parts
            )
        return found


class _FileHeadersCheck:
    """Every assets/README.md, references/*.md, and scripts/*.py carries the required
    header fields.

    Enforces the reference-file header standard across the skill's files, not
    just SKILL.md. Skipped when the document was not loaded from a directory (a
    unit test building a SkillDocument by hand), so pure checks stay pure.
    """

    def run(self, document: SkillDocument) -> CheckResult | None:
        if document.skill_dir is None:
            return None
        offenders = []
        for path in HeaderFileFinder(document.skill_dir).find():
            missing = FileHeaderValidator(
                path.read_text(encoding="utf-8"), path.suffix == ".py"
            ).validate()
            if missing:
                rel = path.relative_to(document.skill_dir).as_posix()
                offenders.append(f"{rel} (missing {', '.join(missing)})")
        if offenders:
            return CheckResult.failed("file header issues: " + "; ".join(offenders))
        return CheckResult.passed(
            "README, references, and scripts carry required headers"
        )


class _SkillStalenessCheck:
    """WARNING when SKILL.md's last_updated is stale. See references/reference-file-standard.md."""

    def __init__(self, evaluator: StalenessEvaluator) -> None:
        self.evaluator = evaluator

    def run(self, document: SkillDocument) -> CheckResult | None:
        last_updated = document.last_updated()
        if last_updated is None:
            return None
        if self.evaluator.is_stale(last_updated):
            return CheckResult.warned(
                f"SKILL.md is stale: last_updated {last_updated} is over "
                f"{self.evaluator.months} months old; run a full re-evaluation and "
                "refresh it against the current standard"
            )
        return CheckResult.passed(
            f"SKILL.md last_updated {last_updated} is within "
            f"{self.evaluator.months} months"
        )


class _FileStalenessCheck:
    """WARNING listing each README/reference/script whose header is stale. See references/reference-file-standard.md."""

    def __init__(self, evaluator: StalenessEvaluator) -> None:
        self.evaluator = evaluator

    def run(self, document: SkillDocument) -> CheckResult | None:
        if document.skill_dir is None:
            return None
        stale = []
        for path in HeaderFileFinder(document.skill_dir).find():
            header = HeaderExtractor(
                path.read_text(encoding="utf-8"), path.suffix == ".py"
            ).extract()
            match = LAST_UPDATED_VALUE_RE.search(header)
            if match and self.evaluator.is_stale(match.group(1)):
                rel = path.relative_to(document.skill_dir).as_posix()
                stale.append(f"{rel} ({match.group(1)})")
        if stale:
            return CheckResult.warned(
                f"stale files (last_updated over {self.evaluator.months} months old); "
                "refresh a file with sources from those pages, and review one "
                "without sources by hand: " + "; ".join(stale)
            )
        return CheckResult.passed("all file headers are within the staleness window")


@dataclass(frozen=True)
class EvalFiles:
    """What the evals folder holds: the fixture paths under evals/files/, the text
    of the files that can use a fixture (evals.json and fixture generators), and
    the eval summary file names."""

    fixtures: list[str]
    references: str
    summaries: list[str]


class EvalFilesAudit:
    """Finds fixtures no eval case or generator names, and eval summaries a newer
    one supersedes (pure). A fixture counts as used when its path under
    evals/files/, its file name, or its top folder appears in a reference."""

    def __init__(self, files: EvalFiles) -> None:
        self.files = files

    def unused(self) -> list[str]:
        refs = self.files.references
        return [
            f
            for f in self.files.fixtures
            if f not in refs
            and f.rsplit("/", 1)[-1] not in refs
            and f.split("/")[0] not in refs
        ]

    def superseded(self) -> list[str]:
        return sorted(self.files.summaries)[:-1]


class EvalFilesReader:
    """Reads a skill's evals folder into EvalFiles (I/O)."""

    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir

    def read(self) -> EvalFiles:
        evals = self.skill_dir / "evals"
        fixtures_dir = evals / "files"
        fixtures = (
            sorted(
                p.relative_to(fixtures_dir).as_posix()
                for p in fixtures_dir.rglob("*")
                if p.is_file()
            )
            if fixtures_dir.is_dir()
            else []
        )
        references = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for pattern in EVAL_REFERENCE_GLOBS
            for p in evals.glob(pattern)
            if p.is_file() and fixtures_dir not in p.parents
        )
        summaries = (
            [p.name for p in evals.glob(EVAL_SUMMARY_GLOB)] if evals.is_dir() else []
        )
        return EvalFiles(fixtures=fixtures, references=references, summaries=summaries)


class _UnusedEvalFixturesCheck:
    """FAILs on a fixture under evals/files/ that no eval case or generator names."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        if document.skill_dir is None or not (document.skill_dir / "evals").is_dir():
            return None
        unused = EvalFilesAudit(EvalFilesReader(document.skill_dir).read()).unused()
        if unused:
            return CheckResult.failed(
                "eval fixtures no case uses (delete them): " + ", ".join(unused)
            )
        return CheckResult.passed("every eval fixture is used by a case")


class _SupersededEvalSummaryCheck:
    """WARNING when evals/ holds more than one eval summary. results.jsonl keeps
    every run's numbers, so only the latest summary is kept."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        if document.skill_dir is None or not (document.skill_dir / "evals").is_dir():
            return None
        older = EvalFilesAudit(EvalFilesReader(document.skill_dir).read()).superseded()
        if older:
            return CheckResult.warned(
                "superseded eval summaries (results.jsonl keeps their numbers; delete them): "
                + ", ".join(older)
            )
        return None


def build_checks(today: datetime.date | None = None) -> list[Check]:
    """The ordered list of checks. Injected into SkillChecker by main().

    `today` is the staleness reference date. It defaults to UTC today and is
    injected by tests so staleness results are deterministic.
    """
    evaluator = StalenessEvaluator(today or datetime.datetime.now(datetime.UTC).date())
    rules = {rule.id: rule for rule in RuleLoader(RULES_DIR).load()}
    frontmatter, headings = rules[RuleId.FRONTMATTER], rules[RuleId.HEADINGS]
    return [
        _RuleFileCheck(frontmatter, "required_name"),
        _RuleFileCheck(frontmatter, "required_description"),
        _RuleFileCheck(frontmatter, "required_created_date"),
        _RuleFileCheck(frontmatter, "required_last_updated"),
        _RuleFileCheck(frontmatter, "name_format"),
        _RuleFileCheck(frontmatter, "description_length"),
        _RuleFileCheck(frontmatter, "created_date_format"),
        _RuleFileCheck(frontmatter, "last_updated_format"),
        _RuleFileCheck(headings, "heading_overview"),
        _RuleFileCheck(headings, "heading_workflow"),
        _BlockOrderCheck(),
        _TagBalanceCheck(),
        _RuleFileCheck(rules[RuleId.BODY_LENGTH], "max_lines"),
        _RuleFileCheck(rules[RuleId.PROSE], "em_dash"),
        _RuleFileCheck(rules[RuleId.PROSE], "emoji"),
        _RuleSequentialNumberingCheck(),
        _RuleSelfReferenceCheck(),
        _StepFailurePathCheck(),
        _WorkflowToolsCheck(),
        _UnusedToolsCheck(),
        _InputPlaceholderCheck(),
        _WorkflowAttributesCheck(),
        _RuleFileCheck(frontmatter, "preferred_model"),
        _RuleFileCheck(frontmatter, "preferred_thinking"),
        _RuleCrossRefCheck(),
        _NameMatchesDirectoryCheck(),
        _ChoiceOptionsCheck(),
        _DateOrderCheck(),
        _SkillChecksumFieldCheck(),
        _ChecksumIntegrityCheck(),
        _FileHeadersCheck(),
        _UnusedEvalFixturesCheck(),
        _SupersededEvalSummaryCheck(),
        _SkillStalenessCheck(evaluator),
        _FileStalenessCheck(evaluator),
    ]


class SkillChecker:
    """Applies an injected list of checks to one SKILL.md and rolls up a report."""

    def __init__(self, path: Path, checks: list[Check]) -> None:
        self.path = path
        self.checks = checks

    def check(self) -> ValidationReport:
        document = SkillDocument.from_path(self.path)
        results = [
            result
            for check in self.checks
            if (result := check.run(document)) is not None
        ]
        return ValidationReport(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical pass/fail checks for a SKILL.md."
    )
    parser.add_argument("skill_md", help="Path to the SKILL.md file.")
    args = parser.parse_args(argv)

    path = Path(args.skill_md)
    if not path.is_file():
        logger.error("Not a file: %s", path)
        return 2

    report = SkillChecker(path, build_checks()).check()
    for result in report.results:
        logger.info("%s  %s", result.status_code.value, result.status_reason)
    logger.info(
        "%d checks, %d failures, %d warnings",
        len(report.results),
        len(report.failures),
        len(report.warnings),
    )
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
