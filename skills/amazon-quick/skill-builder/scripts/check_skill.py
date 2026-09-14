"""
description: Run the mechanical, objective pass/fail schema checks on a SKILL.md (frontmatter fields, naming, character and line limits, XML tag balance, block ordering, em dashes and body emojis, rule numbering, a well-formed checksum field, and checksum integrity by recomputing the content digest and comparing it to the stored checksum), plus non-blocking staleness WARNINGs when SKILL.md or a header file is over six months old; qualitative review is done by reading, not here. Run as: python check_skill.py <path/to/SKILL.md>.
last_updated: 2026-09-13
origin: original

Usage:
    python check_skill.py <path/to/SKILL.md>
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import logging
import re
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


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

MAX_DESCRIPTION = 1024
MAX_BODY_LINES = 1024
MAX_NAME = 64

# Six calendar months, per the staleness rule in references/reference-file-standard.md.
STALENESS_MONTHS = 6

REQUIRED_FRONTMATTER = ("name", "description", "created_date", "last_updated")
DATE_FIELDS = ("created_date", "last_updated")
HEADINGS = ("## Overview", "## Workflow")
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
VALID_MODELS = ("fast", "balanced", "smart")
VALID_THINKING = ("off", "low", "medium", "high")
DEFAULT_THINKING = "high"
# Fast mode does not support thinking effort, so it pairs only with "off".
FAST_MODEL = "fast"

# Compiled once, named for intent, referenced wherever needed.
FENCE_RE = re.compile(r"```.*?```", re.S)
DEFINITIONS_RE = re.compile(r"<Definitions>.*?</Definitions>", re.S)
RULES_BLOCK_RE = re.compile(r"<Rules>(.*?)</Rules>", re.S)
NAME_RE = re.compile(r'^name\s*:\s*"?([^"\n]+)"?', re.M)
DESCRIPTION_RE = re.compile(r'^description\s*:\s*"(.*)"\s*$', re.M)
KEBAB_RE = re.compile(rf"[a-z][a-z0-9-]{{0,{MAX_NAME - 1}}}")
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
PREFERRED_MODEL_RE = re.compile(r"preferred_model=([A-Za-z]+)")
PREFERRED_THINKING_RE = re.compile(r"preferred_thinking=([A-Za-z]+)")
INPUT_SPLIT_RE = re.compile(r"\n\s*-\s*name\s*:")
# Emoji live across several Unicode blocks. Each range is named so a human
# reviewer reads the intent instead of decoding raw code points.
EMOJI_PICTOGRAPHS = ("\U0001f300", "\U0001faff")  # symbols, pictographs, emoticons
EMOJI_MISC_SYMBOLS = ("\U00002600", "\U000027bf")  # miscellaneous symbols and dingbats
EMOJI_CARDS_AND_TILES = ("\U0001f000", "\U0001f0ff")  # mahjong, dominoes, playing cards
EMOJI_BLOCKS = (EMOJI_PICTOGRAPHS, EMOJI_MISC_SYMBOLS, EMOJI_CARDS_AND_TILES)
EMOJI_RE = re.compile(
    "[" + "".join(f"{low}-{high}" for low, high in EMOJI_BLOCKS) + "]"
)
EM_DASH = "\u2014"  # the em dash character, rendered "—"
CHECKSUM_VALUE_RE = re.compile(r'^checksum\s*:\s*"?sha256:[0-9a-f]{64}"?\s*$', re.M)
CHECKSUM_CAPTURE_RE = re.compile(r'^checksum\s*:\s*"?(sha256:[0-9a-f]{64})"?', re.M)
CHECKSUM_LINE_RE = re.compile(r"^checksum\s*:\s*.*$", re.M)
LAST_UPDATED_VALUE_RE = re.compile(r'^last_updated\s*:\s*"?(\d{4}-\d{2}-\d{2})', re.M)
SKILL_FILENAME = "SKILL.md"
# Digest inputs; must mirror create_checksum.py, which a standalone script cannot import.
DIGEST_ROOT_FILES = (SKILL_FILENAME, "README.md")
DIGEST_DIRS = ("scripts", "references", "assets")
DIGEST_EXCLUDE_DIRS = frozenset({"evals", "tests", "__pycache__", ".git"})
DIGEST_EXCLUDE_SUFFIXES = frozenset({".pyc"})
DIGEST_EXCLUDE_NAMES = frozenset({".DS_Store"})
DIGEST_TEST_FILE_RE = re.compile(r"^test_.*\.py$")
DIGEST_PREFIX = "sha256"
# Reference-file header standard: every references/*.md and scripts/*.py must
# declare description, last_updated, and exactly one of source_url or origin.
HEADER_DESCRIPTION_RE = re.compile(r"^description\s*:", re.M)
HEADER_LAST_UPDATED_RE = re.compile(r"^last_updated\s*:", re.M)
HEADER_PROVENANCE_RE = re.compile(r"^(?:source_url|origin)\s*:", re.M)
PY_DOCSTRING_RE = re.compile(r'"""(.*?)"""', re.S)
MD_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S)
HEADER_FILE_GROUPS = (("references", "*.md"), ("scripts", "*.py"))


class CheckStatus(StrEnum):
    """Outcome category for a single check result."""

    PASS = "PASS"  # nosec B105 - enum status label, not a credential
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


class _RequiredFieldCheck:
    """One required frontmatter field is present."""

    def __init__(self, field: str) -> None:
        self.field = field

    def run(self, document: SkillDocument) -> CheckResult | None:
        present = bool(re.search(rf"^{self.field}\s*:", document.frontmatter, re.M))
        return CheckResult.of(
            present,
            (
                f"frontmatter: {self.field} present"
                if present
                else f"frontmatter: {self.field} MISSING"
            ),
        )


class _NameFormatCheck:
    """Frontmatter name is valid kebab-case."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        name = document.name_value()
        if name is None:
            return None
        valid = bool(KEBAB_RE.fullmatch(name))
        return CheckResult.of(
            valid,
            (
                f"name '{name}' is valid kebab-case"
                if valid
                else f"name '{name}' is not valid kebab-case (lowercase, hyphens, <= {MAX_NAME} chars)"
            ),
        )


class _DescriptionLengthCheck:
    """Description is within the character limit."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        m = DESCRIPTION_RE.search(document.frontmatter)
        if not m:
            return None
        n = len(m.group(1))
        return CheckResult.of(
            n <= MAX_DESCRIPTION, f"description length {n} (limit {MAX_DESCRIPTION})"
        )


class _DateFormatCheck:
    """A date field, when present, is ISO YYYY-MM-DD."""

    def __init__(self, field: str) -> None:
        self.field = field

    def run(self, document: SkillDocument) -> CheckResult | None:
        if not re.search(rf"^{self.field}\s*:", document.frontmatter, re.M):
            return None
        m = re.search(
            rf'^{self.field}\s*:\s*"?(\d{{4}}-\d{{2}}-\d{{2}})"?',
            document.frontmatter,
            re.M,
        )
        return CheckResult.of(
            bool(m),
            (
                f"{self.field} is ISO YYYY-MM-DD"
                if m
                else f"{self.field} not ISO YYYY-MM-DD"
            ),
        )


class _HeadingCheck:
    """A required markdown heading is present."""

    def __init__(self, heading: str) -> None:
        self.heading = heading

    def run(self, document: SkillDocument) -> CheckResult | None:
        ok = self.heading in document.body
        return CheckResult.of(
            ok,
            (
                f"heading '{self.heading}' present"
                if ok
                else f"heading '{self.heading}' MISSING (save_skill requires it)"
            ),
        )


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


class _BodyLengthCheck:
    """Body stays within the line limit."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        n = len(document.body.splitlines())
        return CheckResult.of(
            n <= MAX_BODY_LINES, f"body length {n} lines (limit {MAX_BODY_LINES})"
        )


class _EmDashCheck:
    """No em dashes in body prose (fenced code excluded)."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        scan = _blank_fences(document.body)
        em_lines = [i + 1 for i, ln in enumerate(scan) if EM_DASH in ln]
        return CheckResult.of(
            not em_lines,
            "no em dashes" if not em_lines else f"em dashes on body lines {em_lines}",
        )


class _EmojiCheck:
    """No emojis in body prose (fenced code excluded)."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        scan = _blank_fences(document.body)
        emoji_lines = [i + 1 for i, ln in enumerate(scan) if EMOJI_RE.search(ln)]
        return CheckResult.of(
            not emoji_lines,
            (
                "no body emojis"
                if not emoji_lines
                else f"emojis on body lines {emoji_lines}"
            ),
        )


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


class _WorkflowToolsCheck:
    """Every tool used in a workflow tools=[...] is declared in frontmatter."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        m = FRONTMATTER_TOOLS_RE.search(document.frontmatter)
        declared = (
            {t.strip() for t in m.group(1).split(",") if t.strip()} if m else set()
        )
        used = set()
        for block in WORKFLOW_TOOLS_RE.findall(document.body_without_examples()):
            used |= {t.strip() for t in block.split(",") if t.strip()}
        undeclared = sorted(
            t for t in (used - declared) if t not in ("...", "built_in_tool")
        )
        if undeclared:
            return CheckResult.failed(
                f"workflow tools not in frontmatter `tools`: {undeclared}"
            )
        return CheckResult.passed("all workflow tools are declared in frontmatter")


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
    """Every workflow opener carries description=, tools=, triggers=, and any
    advisory hints hold valid enum values."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        openers = WORKFLOW_OPENER_RE.findall(document.body_without_fences())
        missing = []
        for opener in openers:
            name = WORKFLOW_NAME_RE.search(opener).group(1).strip()
            for attr in ("description=", "tools=", "triggers="):
                if attr not in opener:
                    missing.append(f"'{name}' missing {attr.rstrip('=')}")
            hm = PREFERRED_MODEL_RE.search(opener)
            if hm and hm.group(1) not in VALID_MODELS:
                missing.append(f"'{name}' preferred_model={hm.group(1)} invalid")
            ht = PREFERRED_THINKING_RE.search(opener)
            if ht and ht.group(1) not in VALID_THINKING:
                missing.append(f"'{name}' preferred_thinking={ht.group(1)} invalid")
        if missing:
            return CheckResult.failed("workflow attribute gaps: " + "; ".join(missing))
        return CheckResult.passed(
            f"all {len(openers)} workflows have description, tools, triggers"
        )


class _PreferredFieldCheck:
    """A preferred_* frontmatter field, when present, holds a valid value."""

    def __init__(self, field: str, valid: tuple[str, ...]) -> None:
        self.field = field
        self.valid = valid

    def run(self, document: SkillDocument) -> CheckResult | None:
        m = re.search(
            rf'^{self.field}\s*:\s*"?([A-Za-z]+)"?', document.frontmatter, re.M
        )
        if not m:
            return None
        val = m.group(1)
        return CheckResult.of(
            val in self.valid,
            (
                f"{self.field} '{val}' is valid"
                if val in self.valid
                else f"{self.field} '{val}' invalid (must be one of {', '.join(self.valid)})"
            ),
        )


class _RuleCrossRefCheck:
    """Every 'Rule N' reference in the body points to a rule that exists."""

    def run(self, document: SkillDocument) -> CheckResult | None:
        if document.rules_block() is None:
            return None
        rule_count = len(document.rule_numbers())
        body = document.body
        outside = body[: body.index("<Rules>")] + body[body.index("</Rules>") :]
        refs = sorted({int(n) for n in RULE_CROSSREF_RE.findall(outside)})
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


class SkillContentManifest:
    """Reads a skill directory into a {relpath: content} manifest (I/O). Mirrors
    create_checksum.py."""

    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir

    def collect(self) -> dict[str, bytes]:
        manifest: dict[str, bytes] = {}
        for name in DIGEST_ROOT_FILES:
            path = self.skill_dir / name
            if path.is_file():
                manifest[name] = self._content_for(name, path)
        for directory in DIGEST_DIRS:
            base = self.skill_dir / directory
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if self._is_included(path):
                    relpath = path.relative_to(self.skill_dir).as_posix()
                    manifest[relpath] = self._content_for(relpath, path)
        return manifest

    def _content_for(self, relpath: str, path: Path) -> bytes:
        if relpath == SKILL_FILENAME:
            stripped = CHECKSUM_LINE_RE.sub(
                "", path.read_text(encoding="utf-8"), count=1
            )
            return stripped.encode("utf-8")
        return path.read_bytes()

    def _is_included(self, path: Path) -> bool:
        if not path.is_file():
            return False
        parts = set(path.relative_to(self.skill_dir).parts)
        if parts & DIGEST_EXCLUDE_DIRS:
            return False
        if path.suffix in DIGEST_EXCLUDE_SUFFIXES or path.name in DIGEST_EXCLUDE_NAMES:
            return False
        return not DIGEST_TEST_FILE_RE.match(path.name)


class ContentDigest:
    """Hashes a manifest into a deterministic, order-independent digest (pure).
    Mirrors create_checksum.py."""

    def __init__(self, manifest: dict[str, bytes]) -> None:
        self.manifest = manifest

    def compute(self) -> str:
        lines = [
            f"{relpath}\t{hashlib.sha256(content).hexdigest()}"
            for relpath, content in sorted(self.manifest.items())
        ]
        body = "\n".join(lines).encode("utf-8")
        return f"{DIGEST_PREFIX}:{hashlib.sha256(body).hexdigest()}"


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
        computed = ContentDigest(
            SkillContentManifest(document.skill_dir).collect()
        ).compute()
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


class FileHeaderValidator:
    """Validates that a file's header carries the required fields (pure).

    Given a file's text and whether it is Python, it extracts the header (the
    module docstring for .py, the YAML frontmatter for .md) and returns the list
    of missing fields: description, last_updated, and source_url-or-origin.
    """

    def __init__(self, text: str, is_python: bool) -> None:
        self.text = text
        self.is_python = is_python

    def validate(self) -> list[str]:
        """Return the required header fields that are missing (empty if valid)."""
        header = self._header()
        missing = []
        if not HEADER_DESCRIPTION_RE.search(header):
            missing.append("description")
        if not HEADER_LAST_UPDATED_RE.search(header):
            missing.append("last_updated")
        if not HEADER_PROVENANCE_RE.search(header):
            missing.append("source_url or origin")
        return missing

    def _header(self) -> str:
        return HeaderExtractor(self.text, self.is_python).extract()


class HeaderFileFinder:
    """Lists every file that must carry a header: README.md, references/*.md,
    scripts/*.py (I/O)."""

    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir

    def find(self) -> list[Path]:
        found: list[Path] = []
        readme = self.skill_dir / "README.md"
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
    """Every README.md, references/*.md, and scripts/*.py carries the required
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
                "regenerate a derived file from its source_url or review an "
                "origin: original file by hand: " + "; ".join(stale)
            )
        return CheckResult.passed("all file headers are within the staleness window")


def _blank_fences(text: str) -> list[str]:
    """Return body lines with fenced code blanked, preserving line numbers."""
    out, in_fence = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return out


def build_checks(today: datetime.date | None = None) -> list[Check]:
    """The ordered list of checks. Injected into SkillChecker by main().

    `today` is the staleness reference date. It defaults to UTC today and is
    injected by tests so staleness results are deterministic.
    """
    evaluator = StalenessEvaluator(today or datetime.datetime.now(datetime.UTC).date())
    return [
        _RequiredFieldCheck("name"),
        _RequiredFieldCheck("description"),
        _RequiredFieldCheck("created_date"),
        _RequiredFieldCheck("last_updated"),
        _NameFormatCheck(),
        _DescriptionLengthCheck(),
        _DateFormatCheck("created_date"),
        _DateFormatCheck("last_updated"),
        _HeadingCheck("## Overview"),
        _HeadingCheck("## Workflow"),
        _BlockOrderCheck(),
        _TagBalanceCheck(),
        _BodyLengthCheck(),
        _EmDashCheck(),
        _EmojiCheck(),
        _RuleSequentialNumberingCheck(),
        _RuleSelfReferenceCheck(),
        _StepFailurePathCheck(),
        _WorkflowToolsCheck(),
        _InputPlaceholderCheck(),
        _WorkflowAttributesCheck(),
        _PreferredFieldCheck("preferred_model", VALID_MODELS),
        _PreferredFieldCheck("preferred_thinking", VALID_THINKING),
        _RuleCrossRefCheck(),
        _NameMatchesDirectoryCheck(),
        _ChoiceOptionsCheck(),
        _DateOrderCheck(),
        _SkillChecksumFieldCheck(),
        _ChecksumIntegrityCheck(),
        _FileHeadersCheck(),
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mechanical pass/fail checks for a SKILL.md."
    )
    parser.add_argument("skill_md", help="Path to the SKILL.md file.")
    args = parser.parse_args()

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
