"""
description: The rule engine. Loads the rule files in references/rules/ (security_rule.json and standard_rule.json, one file per rule type), validates them, runs their code checks on a skill read as data, writes the results and the agent's review tasks in one standard results.json, verifies the agent's verdicts and quotes, and renders the security report.
last_updated: 2026-11-18

Usage:
    python run_rules.py check <skill folder, .zip, or SKILL.md> --out <dir> [--type security|standard]
    python run_rules.py verify --out <dir>
    python run_rules.py report --out <dir>
    python run_rules.py schema --out <dir>
In AWS Quick, import the module and call main([...]) with the same arguments.
Exit codes: 0 done, 1 the review is incomplete or a quote doesn't match, 2 bad input.
"""

from __future__ import annotations

import argparse
import ast
import bisect
import datetime
import fnmatch
import io
import ipaddress
import json
import logging
import re
import stat
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
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

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_BAD_INPUT = 2
RULES_DIR = Path(__file__).resolve().parents[1] / "references" / "rules"
RULE_FILE_SUFFIX = "_rule.json"
RULE_SCHEMA_FILE = "rule.schema.json"
RESULTS_SCHEMA_FILE = "results.schema.json"
RESULTS_FILE = "results.json"
REVIEW_DIR = "review"
SAFE_FOLDER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
SKILL_FILE = "SKILL.md"
EVALS_DIR = "evals"
QUOTE_CHARS = 160
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
REDACTED_CHARS = 12
TEXT_SUFFIXES = frozenset(
    {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".csv", ".py", ".js"}
    | {".svg", ".html", ".htm"}
)
FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
FENCE_LINE_PREFIX = "```"
WORKFLOW_TOOLS_RE = re.compile(r"^tools=\[([^\]]*)\]", re.MULTILINE)
HTML_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)
IPV4_RE = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
JS_IMPORT_RE = re.compile(
    r"""(?:require\(\s*|import\(\s*|\bfrom\s+|^\s*import\s+)['"]([^'"]+)['"]""", re.M
)
YAML_TAG_RE = re.compile(r"!!python|!!\w+/|![A-Za-z_][\w./:-]*\s")
DECLARED_TOOLS_RE = re.compile(r"^tools\s*:\s*\[([^\]]*)\]", re.M)
REPORT_FILE = "report.md"
DISCLAIMER = (
    "This is an automated, agentic review to help you decide. It isn't a professional "
    "security assessment, and no review catches everything. For a skill that touches "
    "sensitive data or production systems, ask your security team to review it too."
)


# --- Enums: the closed vocabulary every rule file and result uses -------------


class RuleType(StrEnum):
    """What a rule protects."""

    SECURITY = "security"
    STANDARD = "standard"


class RuleId(StrEnum):
    """Every rule the engine knows. Each is defined once, in the rule file of its type."""

    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    MALICIOUS_REFERENCES = "malicious_references"
    DANGEROUS_INSTRUCTIONS = "dangerous_instructions"
    SECURITY_GUIDANCE = "security_guidance"
    SUPPLY_CHAIN = "supply_chain"
    EXCESSIVE_PERMISSIONS = "excessive_permissions"
    OBFUSCATED_INTENT = "obfuscated_intent"
    TOOL_HIJACKING = "tool_hijacking"
    CONTEXT_POISONING = "context_poisoning"
    SECRETS_AND_PERSONAL_DATA = "secrets_and_personal_data"
    FRONTMATTER = "frontmatter"
    HEADINGS = "headings"
    BODY_LENGTH = "body_length"
    PROSE = "prose"


class Level(StrEnum):
    """How sure a check is when it matches."""

    ERROR = "error"
    WARNING = "warning"


class Status(StrEnum):
    """Where a result stands."""

    PASSED = "passed"
    OPEN = "open"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    UNSURE = "unsure"


class Source(StrEnum):
    """Who produced a result."""

    CODE = "code"
    AGENT = "agent"


class Scope(StrEnum):
    """What one review task covers."""

    FILE = "file"
    SKILL = "skill"


class Target(StrEnum):
    """Which part of a text file a text check reads."""

    FILE = "file"
    FRONTMATTER = "frontmatter"
    BODY_PROSE = "body_prose"


class NoMatch(StrEnum):
    """What a frontmatter_value check does when its extract pattern finds no value."""

    SKIP = "skip"
    FAIL = "fail"


class CheckKind(StrEnum):
    """Every kind of code check the engine can run. A rule file chooses a kind and
    gives its parameters; the engine owns how each kind works."""

    REGEX = "regex"
    HTML_COMMENT = "html_comment"
    INVISIBLE_CHARS = "invisible_chars"
    BLANK_RUN = "blank_run"
    LONG_LINE = "long_line"
    PUBLIC_IP = "public_ip"
    FILE_MATCH = "file_match"
    HIDDEN_PATH = "hidden_path"
    UNSAFE_PATH = "unsafe_path"
    IMAGE_MAGIC = "image_magic"
    BINARY_TEXT = "binary_text"
    UNKNOWN_FILE_TYPE = "unknown_file_type"
    FILE_COUNT = "file_count"
    FILE_SIZE = "file_size"
    FRONTMATTER_PARSE = "frontmatter_parse"
    UNUSED_TOOLS = "unused_tools"
    PYTHON_IMPORT = "python_import"
    PYTHON_THIRD_PARTY = "python_third_party"
    PYTHON_CALL = "python_call"
    PYTHON_YAML_LOAD = "python_yaml_load"
    PYTHON_SYNTAX = "python_syntax"
    JS_MODULE = "js_module"
    JS_THIRD_PARTY = "js_third_party"
    FRONTMATTER_REQUIRED = "frontmatter_required"
    FRONTMATTER_VALUE = "frontmatter_value"
    HEADING_REQUIRED = "heading_required"
    BODY_MAX_LINES = "body_max_lines"
    PROSE_FORBIDDEN = "prose_forbidden"


@dataclass(frozen=True)
class EnumSpec:
    """One enum of the rule vocabulary: its name, what it means, and a definition
    for every value. The JSON schemas are generated from these."""

    name: str
    enum: type[StrEnum]
    description: str
    definitions: dict[str, str]


ENUM_SPECS: tuple[EnumSpec, ...] = (
    EnumSpec(
        name="RuleType",
        enum=RuleType,
        description="What a rule protects.",
        definitions={
            "security": "Protects the user from a skill that could harm them: sending data out, hiding instructions, or running what it shouldn't.",
            "standard": "Checks that the skill follows the Skill Architect standard, so it is consistent, testable, and maintainable.",
        },
    ),
    EnumSpec(
        name="RuleId",
        enum=RuleId,
        description="Every rule the engine knows. Each is defined once, in the rule file of its type.",
        definitions={
            "prompt_injection": "Lines that override instructions, hide a step from the user, change the agent's role, claim prior approval, or speak to a reviewer.",
            "data_exfiltration": "Steps that send, post, upload, or save the user's content somewhere the description doesn't need.",
            "malicious_references": "Links whose domain doesn't fit the purpose, or that the agent fetches and follows at run time.",
            "dangerous_instructions": "Steps that bypass a security control, run commands or programs, or change system settings.",
            "security_guidance": "Advice that would weaken someone's security if they followed it.",
            "supply_chain": "Packages the sandbox doesn't provide, install steps, or code pulled from somewhere that can change.",
            "excessive_permissions": "Tools the workflows don't use or the purpose doesn't need, and changes made without the user's confirmation.",
            "obfuscated_intent": "Anything that hides what the skill does: hidden text, encoded strings, unreadable files, or a description that doesn't match the workflows.",
            "tool_hijacking": "Steps that chain tools to reach systems the purpose doesn't need.",
            "context_poisoning": "Steps that write to memory or files later conversations read, to change how the agent behaves next time.",
            "secrets_and_personal_data": "Real credentials, personal data, or account details in the files, or steps that collect personal data the purpose doesn't need.",
            "frontmatter": "SKILL.md frontmatter has the required fields, each in a valid format.",
            "headings": "SKILL.md has the headings save_skill requires.",
            "body_length": "The SKILL.md body stays under the line limit, since every line loads on every run.",
            "prose": "The SKILL.md body prose has no em dashes or emojis.",
        },
    ),
    EnumSpec(
        name="Level",
        enum=Level,
        description="How sure a check is when it matches.",
        definitions={
            "error": "The code is certain the line breaks the rule, such as a real access key. An error always counts as a finding.",
            "warning": "The line might break the rule, and might be a false alarm. The agent reads it and decides. A warning never fails anything until the agent confirms it.",
        },
    ),
    EnumSpec(
        name="Status",
        enum=Status,
        description="Where a result stands.",
        definitions={
            "passed": "The check ran on the whole skill and found nothing.",
            "open": "A warning the agent hasn't judged yet. A review with an open result is incomplete.",
            "confirmed": "A finding: an error, or a warning or agent result the agent judged to break the rule.",
            "dismissed": "A warning the agent judged to be a false alarm, with the reason. It stays in the results so anyone can see what was filtered out.",
            "unsure": "The agent can't decide and asks the user. After the user answers, it becomes confirmed or dismissed.",
        },
    ),
    EnumSpec(
        name="Source",
        enum=Source,
        description="Who produced a result.",
        definitions={
            "code": "A code check in a rule file produced the result.",
            "agent": "The agent produced the result while reading a file or answering a review task.",
        },
    ),
    EnumSpec(
        name="Scope",
        enum=Scope,
        description="What one review task covers.",
        definitions={
            "file": "One task per file: the agent reads the whole file against the rule.",
            "skill": "One task for the whole skill, such as comparing the description with the workflows.",
        },
    ),
    EnumSpec(
        name="NoMatch",
        enum=NoMatch,
        description="What a frontmatter_value check does when its extract pattern finds no value.",
        definitions={
            "skip": "Report nothing: another check covers a missing or unquoted value.",
            "fail": "Report the check as failed, since the value is in the wrong format.",
        },
    ),
    EnumSpec(
        name="Target",
        enum=Target,
        description="Which part of a text file a text check reads.",
        definitions={
            "file": "The whole text of the file.",
            "frontmatter": "Only the YAML frontmatter of SKILL.md.",
            "body_prose": "The SKILL.md body with fenced code blanked out, keeping line numbers.",
        },
    ),
    EnumSpec(
        name="CheckKind",
        enum=CheckKind,
        description="Every kind of code check the engine can run. A rule file chooses a kind and gives its parameters; the engine owns how each kind works.",
        definitions={
            "regex": "Flags every match of a regular expression in the target text, minus matches the exclude pattern finds.",
            "html_comment": "Flags every HTML comment, since an agent reads text a person doesn't see.",
            "invisible_chars": "Flags lines with invisible or control characters that can hide text.",
            "blank_run": "Flags a run of blank lines that can push text out of sight.",
            "long_line": "Flags a line longer than the limit, where text can hide past the edge of the screen.",
            "public_ip": "Flags public IPv4 addresses, leaving out private and documentation ranges.",
            "file_match": "Flags files whose suffix or name is on the list.",
            "hidden_path": "Flags hidden files and cache folders.",
            "unsafe_path": "Flags symbolic links and paths that escape the skill folder.",
            "image_magic": "Flags an image file whose bytes don't match its suffix.",
            "binary_text": "Flags a text file that contains binary data.",
            "unknown_file_type": "Flags files whose suffix isn't on the known list.",
            "file_count": "Flags a skill with more files than the limit.",
            "file_size": "Flags a file larger than the limit.",
            "frontmatter_parse": "Flags a SKILL.md with no frontmatter, frontmatter that doesn't parse, or a custom YAML tag.",
            "unused_tools": "Flags frontmatter tools that no workflow's tools=[...] names.",
            "python_import": "Flags Python imports of the listed modules.",
            "python_third_party": "Flags Python imports outside the standard library and the skill's own modules.",
            "python_call": "Flags Python calls to the listed functions.",
            "python_yaml_load": "Flags yaml.load without a safe loader.",
            "python_syntax": "Flags Python that doesn't parse, since unparsed code can't be reviewed.",
            "js_module": "Flags JavaScript imports of the listed modules.",
            "js_third_party": "Flags JavaScript imports outside the listed Node.js modules.",
            "frontmatter_required": "Passes when SKILL.md frontmatter has the field.",
            "frontmatter_value": "When the field is present, passes if its value matches the pattern, length limit, or allowed values.",
            "heading_required": "Passes when the SKILL.md body contains the heading.",
            "body_max_lines": "Passes when the SKILL.md body is within the line limit.",
            "prose_forbidden": "Passes when no body prose line matches the pattern.",
        },
    ),
)


# --- Rule file models ----------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


ExampleText = str | list[str]


class Examples(_Strict):
    """Lines or files the check must flag and must ignore. They are the check's tests.
    An example given as a list of parts is joined before the test runs, so a rule
    file never holds a working secret or encoded string that a security audit of the
    rule file itself would flag."""

    flags: list[ExampleText] = Field(min_length=1)
    ignores: list[ExampleText] = Field(min_length=1)


class _CheckBase(_Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    level: Level
    message: str = Field(min_length=1)
    files: list[str] = ["*"]
    exclude_files: list[str] = []
    skip_evals: bool = False
    fix: str = ""


class _ExampleCheck(_CheckBase):
    examples: Examples


def _compiled(pattern: str) -> str:
    try:
        re.compile(pattern)
    except re.error as error:
        raise ValueError(f"invalid regex {pattern!r}: {error}") from error
    return pattern


Pattern = Annotated[str, AfterValidator(_compiled)]


class RegexCheck(_ExampleCheck):
    kind: Literal[CheckKind.REGEX]
    pattern: Pattern
    exclude: Pattern = ""
    target: Target = Target.FILE
    redact: bool = False


class HtmlCommentCheck(_ExampleCheck):
    kind: Literal[CheckKind.HTML_COMMENT]
    skip_evals: bool = True


class InvisibleCharsCheck(_ExampleCheck):
    kind: Literal[CheckKind.INVISIBLE_CHARS]


class BlankRunCheck(_ExampleCheck):
    kind: Literal[CheckKind.BLANK_RUN]
    max_blank_lines: int = Field(gt=0)


class LongLineCheck(_ExampleCheck):
    kind: Literal[CheckKind.LONG_LINE]
    max_chars: int = Field(gt=0)


class PublicIpCheck(_ExampleCheck):
    kind: Literal[CheckKind.PUBLIC_IP]


class FileMatchCheck(_ExampleCheck):
    kind: Literal[CheckKind.FILE_MATCH]
    suffixes: list[str] = []
    names: list[str] = []


class HiddenPathCheck(_ExampleCheck):
    kind: Literal[CheckKind.HIDDEN_PATH]


class UnsafePathCheck(_ExampleCheck):
    kind: Literal[CheckKind.UNSAFE_PATH]


class ImageMagicCheck(_CheckBase):
    kind: Literal[CheckKind.IMAGE_MAGIC]
    signatures: dict[str, list[str]] = Field(min_length=1)


class BinaryTextCheck(_CheckBase):
    kind: Literal[CheckKind.BINARY_TEXT]


class UnknownFileTypeCheck(_ExampleCheck):
    kind: Literal[CheckKind.UNKNOWN_FILE_TYPE]
    known_suffixes: list[str] = Field(min_length=1)


class FileCountCheck(_CheckBase):
    kind: Literal[CheckKind.FILE_COUNT]
    max_files: int = Field(gt=0)


class FileSizeCheck(_CheckBase):
    kind: Literal[CheckKind.FILE_SIZE]
    max_bytes: int = Field(gt=0)


class FrontmatterParseCheck(_ExampleCheck):
    kind: Literal[CheckKind.FRONTMATTER_PARSE]


class UnusedToolsCheck(_ExampleCheck):
    kind: Literal[CheckKind.UNUSED_TOOLS]
    ignore_tools: list[str] = []


class PythonImportCheck(_ExampleCheck):
    kind: Literal[CheckKind.PYTHON_IMPORT]
    modules: list[str] = Field(min_length=1)
    include_imported_names: bool = False


class PythonThirdPartyCheck(_ExampleCheck):
    kind: Literal[CheckKind.PYTHON_THIRD_PARTY]


class PythonCallCheck(_ExampleCheck):
    kind: Literal[CheckKind.PYTHON_CALL]
    names: list[str] = []
    name_pattern: Pattern = ""


class PythonYamlLoadCheck(_ExampleCheck):
    kind: Literal[CheckKind.PYTHON_YAML_LOAD]
    unsafe_calls: list[str] = Field(min_length=1)
    safe_loaders: list[str] = Field(min_length=1)


class PythonSyntaxCheck(_ExampleCheck):
    kind: Literal[CheckKind.PYTHON_SYNTAX]


class JsModuleCheck(_ExampleCheck):
    kind: Literal[CheckKind.JS_MODULE]
    modules: list[str] = Field(min_length=1)


class JsThirdPartyCheck(_ExampleCheck):
    kind: Literal[CheckKind.JS_THIRD_PARTY]
    builtins: list[str] = Field(min_length=1)


class _OneResultCheck(_ExampleCheck):
    """A standard check: one result per skill, passed or not, with both messages."""

    pass_message: str = Field(min_length=1)


class FrontmatterRequiredCheck(_OneResultCheck):
    kind: Literal[CheckKind.FRONTMATTER_REQUIRED]
    field: str


class FrontmatterValueCheck(_OneResultCheck):
    kind: Literal[CheckKind.FRONTMATTER_VALUE]
    field: str
    extract: Pattern
    on_no_match: NoMatch
    pattern: Pattern = ""
    max_length: int = 0
    one_of: list[str] = []
    strip: bool = False


class HeadingRequiredCheck(_OneResultCheck):
    kind: Literal[CheckKind.HEADING_REQUIRED]
    heading: str


class BodyMaxLinesCheck(_OneResultCheck):
    kind: Literal[CheckKind.BODY_MAX_LINES]
    max_lines: int = Field(gt=0)


class ProseForbiddenCheck(_OneResultCheck):
    kind: Literal[CheckKind.PROSE_FORBIDDEN]
    pattern: Pattern


CheckSpec = Annotated[
    RegexCheck
    | HtmlCommentCheck
    | InvisibleCharsCheck
    | BlankRunCheck
    | LongLineCheck
    | PublicIpCheck
    | FileMatchCheck
    | HiddenPathCheck
    | UnsafePathCheck
    | ImageMagicCheck
    | BinaryTextCheck
    | UnknownFileTypeCheck
    | FileCountCheck
    | FileSizeCheck
    | FrontmatterParseCheck
    | UnusedToolsCheck
    | PythonImportCheck
    | PythonThirdPartyCheck
    | PythonCallCheck
    | PythonYamlLoadCheck
    | PythonSyntaxCheck
    | JsModuleCheck
    | JsThirdPartyCheck
    | FrontmatterRequiredCheck
    | FrontmatterValueCheck
    | HeadingRequiredCheck
    | BodyMaxLinesCheck
    | ProseForbiddenCheck,
    Field(discriminator="kind"),
]


class Review(_Strict):
    """What the agent answers by reading, when code can't decide."""

    scope: Scope
    question: str = Field(min_length=1)
    look_for: list[str] = []
    finding_example: str = Field(min_length=1)
    pass_example: str = Field(min_length=1)


class RuleSpec(_Strict):
    """One rule as a rule file writes it. Its type comes from the file it is in."""

    id: RuleId
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    fix: str = Field(min_length=1)
    checks: list[CheckSpec] = []
    review: Review | None = None

    @field_validator("checks")
    @classmethod
    def _unique_check_ids(cls, checks: list[CheckSpec]) -> list[CheckSpec]:
        ids = [check.id for check in checks]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate check ids: {duplicates}")
        return checks


class RuleFile(_Strict):
    """One rule file: references/rules/<type>_rule.json, every rule of one type."""

    type: RuleType
    description: str = Field(min_length=1)
    last_updated: datetime.date
    rules: list[RuleSpec] = Field(min_length=1)


class Rule(RuleSpec):
    """A loaded rule, with the type of the file it came from."""

    type: RuleType


# --- Results models ------------------------------------------------------------


class Result(_Strict):
    """One result, from a code check or from the agent. The standard output."""

    rule_id: RuleId
    check_id: str = ""
    type: RuleType
    level: Level
    status: Status
    source: Source
    path: str = ""
    line: int = 0
    quote: str = ""
    message: str
    fix: str = ""
    reason: str = ""


class ReviewTask(_Strict):
    """One task for the agent: read a file, or the whole skill, against rules."""

    task_id: str
    scope: Scope
    rule_ids: list[RuleId]
    path: str = ""
    line_count: int = 0
    lines_read: int = 0
    done: bool = False


class Results(_Strict):
    """results.json: everything one run produced, then the agent's verdicts."""

    skill: str
    source: str
    review_dir: str
    rule_ids: list[RuleId]
    results: list[Result]
    tasks: list[ReviewTask]


# --- Loading a skill as data ---------------------------------------------------


class SkillFile(_Strict):
    path: str
    data: bytes
    is_symlink: bool = False


class SkillSource(_Strict):
    location: str
    root: str
    files: list[SkillFile]
    folder_name: str = "skill"


class InputError(ValueError):
    """The source, a rule file, or an output folder is unusable. The message names it."""


class ArchiveReader:
    """Reads a skill from zip bytes in memory (pure)."""

    def __init__(self, data: bytes) -> None:
        self.data = data

    def read(self) -> SkillSource:
        try:
            archive = zipfile.ZipFile(io.BytesIO(self.data))
        except zipfile.BadZipFile as error:
            raise InputError(f"not a valid zip file: {error}") from error
        entries = [info for info in archive.infolist() if not info.is_dir()]
        unpacked = sum(info.file_size for info in entries)
        if unpacked > MAX_ARCHIVE_BYTES:
            raise InputError(
                f"the zip unpacks to {unpacked} bytes, over the {MAX_ARCHIVE_BYTES} limit"
            )
        root = self._root([info.filename for info in entries])
        files = [
            SkillFile(
                path=info.filename.removeprefix(root),
                data=archive.read(info),
                is_symlink=stat.S_ISLNK(info.external_attr >> 16),
            )
            for info in entries
        ]
        return SkillSource(location="", root=root, files=files)

    @staticmethod
    def _root(names: list[str]) -> str:
        """The wrapper folder when SKILL.md sits one folder down, else empty."""
        if SKILL_FILE in names:
            return ""
        wrapped = [
            n for n in names if n.count("/") == 1 and n.endswith("/" + SKILL_FILE)
        ]
        return wrapped[0].removesuffix(SKILL_FILE) if len(wrapped) == 1 else ""


class SourceLoader:
    """Loads a skill folder, zip, or lone SKILL.md from disk (I/O). Follows no link."""

    def __init__(self, location: Path) -> None:
        self.location = location

    def load(self) -> SkillSource:
        if self.location.is_file() and self.location.suffix.lower() == ".md":
            item = SkillFile(path=SKILL_FILE, data=self.location.read_bytes())
            return SkillSource(
                location=str(self.location),
                root="",
                files=[item],
                folder_name=_folder_name(self.location.parent.name),
            )
        if self.location.is_file():
            source = ArchiveReader(self.location.read_bytes()).read()
            name = source.root.rstrip("/") or self.location.stem
            return source.model_copy(
                update={
                    "location": str(self.location),
                    "folder_name": _folder_name(name),
                }
            )
        if not self.location.is_dir():
            raise InputError(
                f"{self.location} is not a skill folder, a zip, or a .md file"
            )
        files = []
        for path in sorted(self.location.rglob("*")):
            relative = path.relative_to(self.location).as_posix()
            if path.is_symlink():
                files.append(SkillFile(path=relative, data=b"", is_symlink=True))
            elif path.is_file():
                files.append(SkillFile(path=relative, data=path.read_bytes()))
        return SkillSource(
            location=str(self.location),
            root="",
            files=files,
            folder_name=_folder_name(self.location.resolve().name),
        )


def _folder_name(name: str) -> str:
    """The review copy's folder name: the source's own folder name, so checks that
    compare the skill's name with its folder see the same folder (pure)."""
    return name if SAFE_FOLDER_RE.fullmatch(name) else "skill"


def is_text_path(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in TEXT_SUFFIXES or path == SKILL_FILE


def is_safe_path(item: SkillFile) -> bool:
    parts = PurePosixPath(item.path).parts
    escapes = item.path.startswith("/") or ".." in parts or "\\" in item.path
    return not (escapes or item.is_symlink)


def in_evals(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(parts) and parts[0] == EVALS_DIR


class Span(_Strict):
    """A character range in a text."""

    start: int
    end: int


class TextFile(_Strict):
    """A text file of the skill, decoded once. A data carrier: its helpers are
    computed properties, plus line_at(), which turns an offset into a line number."""

    path: str
    text: str

    @property
    def lines(self) -> list[str]:
        return self.text.split("\n")

    @property
    def frontmatter(self) -> str:
        match = FRONT_MATTER_RE.match(self.text)
        return match.group(1) if match else ""

    @property
    def frontmatter_span(self) -> Span:
        match = FRONT_MATTER_RE.match(self.text)
        if match is None:
            return Span(start=0, end=0)
        return Span(start=match.start(1), end=match.end(1))

    @property
    def fence_lines(self) -> list[int]:
        """The indexes of the lines that are exactly ---."""
        return [i for i, ln in enumerate(self.text.splitlines()) if ln.strip() == "---"]

    @property
    def frontmatter_text(self) -> str:
        """Frontmatter between the first two --- lines, as check_skill.py reads it."""
        fences, lines = self.fence_lines, self.text.splitlines()
        if len(fences) < 2:
            return ""
        return "\n".join(lines[fences[0] + 1 : fences[1]])

    @property
    def body_offset_lines(self) -> int:
        fences = self.fence_lines
        return fences[1] + 1 if len(fences) >= 2 else 0

    @property
    def body_lines(self) -> list[str]:
        """The body after the second --- line (the whole text when none), split the
        way check_skill.py splits it, so line counts and numbers match."""
        body = self.text.splitlines()[self.body_offset_lines :]
        return "\n".join(body).splitlines()

    @property
    def prose_lines(self) -> list[str]:
        """Body lines with fenced code blanked, line numbers kept."""
        out, in_fence = [], False
        for line in self.body_lines:
            if line.strip().startswith(FENCE_LINE_PREFIX):
                in_fence = not in_fence
                out.append("")
                continue
            out.append("" if in_fence else line)
        return out

    def line_at(self, offset: int) -> int:
        starts = [0] + [i + 1 for i, char in enumerate(self.text) if char == "\n"]
        return bisect.bisect_right(starts, offset)


class SkillView(_Strict):
    """Everything a check can look at: the files and the decoded text files."""

    files: list[SkillFile]
    texts: list[TextFile]

    @classmethod
    def from_source(cls, source: SkillSource) -> SkillView:
        texts = [
            TextFile(path=item.path, text=item.data.decode("utf-8", errors="replace"))
            for item in source.files
            if not item.is_symlink and is_text_path(item.path)
        ]
        return cls(files=source.files, texts=texts)

    @property
    def skill_text(self) -> TextFile | None:
        return next((t for t in self.texts if t.path == SKILL_FILE), None)


# --- Matching --------------------------------------------------------------------


class Match(_Strict):
    """Where a check matched, before it becomes a Result."""

    path: str
    line: int = 0
    quote: str = ""


class OneResult(_Strict):
    """The outcome of a standard check: passed or not, with its message values."""

    passed: bool
    values: dict[str, str] = {}
    line: int = 0


def _matches_glob(path: str, patterns: list[str]) -> bool:
    name = PurePosixPath(path).name
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)


def _clip(text: str) -> str:
    flat = " ".join(text.strip().split())
    return flat if len(flat) <= QUOTE_CHARS else flat[:QUOTE_CHARS]


class FileSelector:
    """Picks the files and text files one check applies to (pure)."""

    def __init__(self, check: _CheckBase, view: SkillView) -> None:
        self.check = check
        self.view = view

    def _wanted(self, path: str) -> bool:
        if self.check.skip_evals and in_evals(path):
            return False
        return _matches_glob(path, self.check.files) and not _matches_glob(
            path, self.check.exclude_files
        )

    def select(self) -> SkillView:
        return SkillView(
            files=[item for item in self.view.files if self._wanted(item.path)],
            texts=[text for text in self.view.texts if self._wanted(text.path)],
        )


class TextMatcher:
    """Runs the text-based check kinds over one text file (pure)."""

    def __init__(self, check: _CheckBase, text: TextFile) -> None:
        self.check = check
        self.text = text

    def matches(self) -> list[Match]:
        match self.check.kind:
            case CheckKind.REGEX:
                return self._regex()
            case CheckKind.HTML_COMMENT:
                return self._html_comments()
            case CheckKind.INVISIBLE_CHARS:
                return self._invisible()
            case CheckKind.BLANK_RUN:
                return self._blank_runs()
            case CheckKind.LONG_LINE:
                return self._long_lines()
            case CheckKind.PUBLIC_IP:
                return self._public_ips()
            case _:
                return []

    def _regex(self) -> list[Match]:
        check = self.check
        pattern, exclude = (
            re.compile(check.pattern),
            re.compile(check.exclude or "(?!)"),
        )
        if check.target == Target.BODY_PROSE:
            offset = self.text.body_offset_lines
            return [
                Match(path=self.text.path, line=offset + i + 1, quote=_clip(m.group(0)))
                for i, line in enumerate(self.text.prose_lines)
                for m in pattern.finditer(line)
                if not exclude.search(m.group(0))
            ]
        span = (
            self.text.frontmatter_span
            if check.target == Target.FRONTMATTER
            else Span(start=0, end=len(self.text.text))
        )
        found = []
        for m in pattern.finditer(self.text.text, span.start, span.end):
            if exclude.search(m.group(0)):
                continue
            quote = (
                m.group(0)[:REDACTED_CHARS] + "..."
                if check.redact
                else _clip(m.group(0))
            )
            found.append(
                Match(
                    path=self.text.path, line=self.text.line_at(m.start()), quote=quote
                )
            )
        return _dedupe(found)

    def _html_comments(self) -> list[Match]:
        return [
            Match(
                path=self.text.path,
                line=self.text.line_at(m.start()),
                quote=_clip(m.group(0)),
            )
            for m in HTML_COMMENT_RE.finditer(self.text.text)
        ]

    def _invisible(self) -> list[Match]:
        found = []
        for number, line in enumerate(self.text.lines, start=1):
            hidden = sorted({c for c in line if _is_hidden_char(c)})
            if hidden:
                codes = ", ".join(
                    f"U+{ord(c):04X} {unicodedata.name(c, 'unnamed')}" for c in hidden
                )
                found.append(Match(path=self.text.path, line=number, quote=codes))
        return found

    def _blank_runs(self) -> list[Match]:
        found, run = [], 0
        for number, line in enumerate(self.text.lines, start=1):
            run = run + 1 if not line.strip() else 0
            if run == self.check.max_blank_lines:
                found.append(
                    Match(path=self.text.path, line=number, quote=f"{run} blank lines")
                )
        return found

    def _long_lines(self) -> list[Match]:
        return [
            Match(path=self.text.path, line=number, quote=f"{len(line)} characters")
            for number, line in enumerate(self.text.lines, start=1)
            if len(line) > self.check.max_chars
        ]

    def _public_ips(self) -> list[Match]:
        found = []
        for m in IPV4_RE.finditer(self.text.text):
            if _is_public_ip(m.group(0)):
                found.append(
                    Match(
                        path=self.text.path,
                        line=self.text.line_at(m.start()),
                        quote=m.group(0),
                    )
                )
        return found


def _dedupe(matches: list[Match]) -> list[Match]:
    seen, unique = set(), []
    for match in matches:
        key = (match.path, match.line)
        if key not in seen:
            seen.add(key)
            unique.append(match)
    return unique


def _is_hidden_char(char: str) -> bool:
    if char in "\t\r\n":
        return False
    return char == "\ufeff" or unicodedata.category(char) in ("Cf", "Co", "Cs", "Cc")


DOCUMENTATION_NETWORKS = tuple(
    ipaddress.ip_network(net)
    for net in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
)


def _is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_global and not any(address in n for n in DOCUMENTATION_NETWORKS)


class FileMatcher:
    """Runs the file-based check kinds over the skill's files (pure)."""

    def __init__(self, check: _CheckBase, files: list[SkillFile]) -> None:
        self.check = check
        self.files = files

    def matches(self) -> list[Match]:
        match self.check.kind:
            case CheckKind.FILE_MATCH:
                return self._each(self._listed)
            case CheckKind.HIDDEN_PATH:
                return self._each(_is_hidden_path)
            case CheckKind.UNSAFE_PATH:
                return self._each(lambda item: not is_safe_path(item))
            case CheckKind.IMAGE_MAGIC:
                return self._each(self._fake_image)
            case CheckKind.BINARY_TEXT:
                return self._each(lambda i: is_text_path(i.path) and b"\x00" in i.data)
            case CheckKind.UNKNOWN_FILE_TYPE:
                return self._each(self._unknown)
            case CheckKind.FILE_SIZE:
                return self._each(lambda item: len(item.data) > self.check.max_bytes)
            case CheckKind.FILE_COUNT:
                if len(self.files) > self.check.max_files:
                    return [Match(path="", quote=f"{len(self.files)} files")]
                return []
            case _:
                return []

    def _each(self, predicate) -> list[Match]:
        return [Match(path=i.path, quote=i.path) for i in self.files if predicate(i)]

    def _listed(self, item: SkillFile) -> bool:
        path = PurePosixPath(item.path)
        suffixes = {s.lower() for s in self.check.suffixes}
        names = {n.lower() for n in self.check.names}
        return path.suffix.lower() in suffixes or path.name.lower() in names

    def _fake_image(self, item: SkillFile) -> bool:
        signatures = self.check.signatures.get(PurePosixPath(item.path).suffix.lower())
        if signatures is None:
            return False
        return not any(item.data.startswith(bytes.fromhex(s)) for s in signatures)

    def _unknown(self, item: SkillFile) -> bool:
        if _is_hidden_path(item) or not is_safe_path(item) or item.path == SKILL_FILE:
            return False
        known = {s.lower() for s in self.check.known_suffixes}
        return PurePosixPath(item.path).suffix.lower() not in known


def _is_hidden_path(item: SkillFile) -> bool:
    parts = PurePosixPath(item.path).parts
    return any(p.startswith(".") for p in parts) or "__pycache__" in parts


class CodeMatcher:
    """Runs the Python and JavaScript check kinds over one source file, read with
    ast or as text and never run (pure)."""

    def __init__(
        self, check: _CheckBase, text: TextFile, local_modules: frozenset[str]
    ) -> None:
        self.check = check
        self.text = text
        self.local_modules = local_modules

    def matches(self) -> list[Match]:
        kind = self.check.kind
        if kind in (CheckKind.JS_MODULE, CheckKind.JS_THIRD_PARTY):
            return self._js_modules()
        try:
            tree = ast.parse(self.text.text)
        except SyntaxError as error:
            if kind == CheckKind.PYTHON_SYNTAX:
                return [
                    Match(
                        path=self.text.path,
                        line=error.lineno or 0,
                        quote=_clip(str(error)),
                    )
                ]
            return []
        if kind == CheckKind.PYTHON_SYNTAX:
            return []
        found = []
        for node in ast.walk(tree):
            found += self._node_matches(node)
        return found

    def _node_matches(self, node: ast.AST) -> list[Match]:
        match self.check.kind:
            case CheckKind.PYTHON_IMPORT:
                refs = _imports(node, self.check.include_imported_names)
                return [self._import(r) for r in refs if self._listed(r.module)]
            case CheckKind.PYTHON_THIRD_PARTY:
                refs = _imports(node, False)
                return [self._import(r) for r in refs if self._third_party(r.module)]
            case CheckKind.PYTHON_CALL if isinstance(node, ast.Call):
                name = _call_name(node.func)
                pattern = self.check.name_pattern
                listed = name in self.check.names or bool(
                    pattern and re.match(pattern, name)
                )
                return [self._at(node, name)] if listed else []
            case CheckKind.PYTHON_YAML_LOAD if isinstance(node, ast.Call):
                return (
                    [self._at(node, _call_name(node.func))]
                    if self._unsafe_yaml(node)
                    else []
                )
            case _:
                return []

    def _import(self, ref: ImportRef) -> Match:
        return Match(path=self.text.path, line=ref.line, quote=ref.module)

    def _at(self, node: ast.AST, quote: str) -> Match:
        return Match(path=self.text.path, line=getattr(node, "lineno", 0), quote=quote)

    def _listed(self, module: str) -> bool:
        if module.split(".")[0] in self.local_modules:
            return False
        return any(
            module == m or module.startswith(m + ".") for m in self.check.modules
        )

    def _third_party(self, module: str) -> bool:
        top = module.split(".")[0]
        return top not in self.local_modules and top not in sys.stdlib_module_names

    def _unsafe_yaml(self, node: ast.Call) -> bool:
        name = _call_name(node.func)
        if name in self.check.unsafe_calls:
            return True
        if name != "yaml.load":
            return False
        loaders = [k.value for k in node.keywords if k.arg == "Loader"] + node.args[1:2]
        return not any(
            ast.unparse(v).endswith(tuple(self.check.safe_loaders)) for v in loaders
        )

    def _js_modules(self) -> list[Match]:
        found = []
        for m in JS_IMPORT_RE.finditer(self.text.text):
            name = m.group(1).removeprefix("node:")
            if name.startswith("."):
                continue
            top = name.split("/")[0]
            listed = (
                name in self.check.modules
                if self.check.kind == CheckKind.JS_MODULE
                else top not in self.check.builtins and name not in self.check.builtins
            )
            if listed:
                found.append(
                    Match(
                        path=self.text.path,
                        line=self.text.line_at(m.start()),
                        quote=name,
                    )
                )
        return found


class ImportRef(_Strict):
    """One module an import statement names, with its line."""

    module: str
    line: int


def _imports(node: ast.AST, include_imported_names: bool) -> list[ImportRef]:
    if isinstance(node, ast.Import):
        return [ImportRef(module=a.name, line=node.lineno) for a in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        found = [ImportRef(module=node.module, line=node.lineno)]
        if include_imported_names:
            found += [
                ImportRef(module=f"{node.module}.{a.name}", line=node.lineno)
                for a in node.names
            ]
        return found
    return []


def _call_name(func: ast.expr) -> str:
    parts = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
    return ".".join(reversed(parts))


class SkillMatcher:
    """Runs the whole-skill check kinds on SKILL.md (pure): frontmatter_parse and
    unused_tools."""

    def __init__(self, check: _CheckBase, skill: TextFile | None) -> None:
        self.check = check
        self.skill = skill

    def matches(self) -> list[Match]:
        if self.skill is None:
            if self.check.kind == CheckKind.FRONTMATTER_PARSE:
                return [Match(path=SKILL_FILE, quote="SKILL.md not found")]
            return []
        match self.check.kind:
            case CheckKind.FRONTMATTER_PARSE:
                return self._frontmatter_problems()
            case CheckKind.UNUSED_TOOLS:
                return self._unused_tools()
            case _:
                return []

    def _frontmatter_problems(self) -> list[Match]:
        match = FRONT_MATTER_RE.match(self.skill.text)
        if not match:
            return [Match(path=SKILL_FILE, line=1, quote="no --- block")]
        source = match.group(1)
        found = []
        tag = YAML_TAG_RE.search(source)
        if tag:
            found.append(Match(path=SKILL_FILE, line=1, quote=tag.group(0).strip()))
        try:
            data = yaml.safe_load(source)
        except yaml.YAMLError as error:
            return found + [Match(path=SKILL_FILE, line=1, quote=_clip(str(error)))]
        if not isinstance(data, dict):
            found.append(
                Match(path=SKILL_FILE, line=1, quote="frontmatter is not a mapping")
            )
        return found

    def _unused_tools(self) -> list[Match]:
        frontmatter = self.skill.frontmatter_text
        declared_match = DECLARED_TOOLS_RE.search(frontmatter)
        lists = WORKFLOW_TOOLS_RE.findall(self.skill.text)
        if not declared_match or not lists:
            return []
        declared = [t.strip() for t in declared_match.group(1).split(",") if t.strip()]
        used = {t.strip() for entry in lists for t in entry.split(",") if t.strip()}
        unused = [
            t for t in declared if t not in used and t not in self.check.ignore_tools
        ]
        if not unused:
            return []
        line = self.skill.line_at(self.skill.text.index(declared_match.group(0)))
        return [Match(path=SKILL_FILE, line=line, quote=", ".join(unused))]


class StandardEvaluator:
    """Runs one standard check kind on SKILL.md and returns its one outcome (pure)."""

    def __init__(self, check: _CheckBase, skill: TextFile | None) -> None:
        self.check = check
        self.skill = skill

    def evaluate(self) -> OneResult | None:
        if self.skill is None:
            return None
        frontmatter = self.skill.frontmatter_text
        match self.check.kind:
            case CheckKind.FRONTMATTER_REQUIRED:
                present = bool(
                    re.search(rf"^{re.escape(self.check.field)}\s*:", frontmatter, re.M)
                )
                return OneResult(passed=present, values={"field": self.check.field})
            case CheckKind.FRONTMATTER_VALUE:
                return self._frontmatter_value(frontmatter)
            case CheckKind.HEADING_REQUIRED:
                body = "\n".join(self.skill.body_lines)
                return OneResult(
                    passed=self.check.heading in body,
                    values={"heading": self.check.heading},
                )
            case CheckKind.BODY_MAX_LINES:
                count = len(self.skill.body_lines)
                return OneResult(
                    passed=count <= self.check.max_lines,
                    values={"count": str(count), "limit": str(self.check.max_lines)},
                )
            case CheckKind.PROSE_FORBIDDEN:
                pattern = re.compile(self.check.pattern)
                lines = [
                    i + 1
                    for i, ln in enumerate(self.skill.prose_lines)
                    if pattern.search(ln)
                ]
                return OneResult(passed=not lines, values={"lines": str(lines)})
            case _:
                return None

    def _frontmatter_value(self, frontmatter: str) -> OneResult | None:
        check = self.check
        if not re.search(rf"^{re.escape(check.field)}\s*:", frontmatter, re.M):
            return None
        found = re.search(check.extract, frontmatter, re.M)
        if found is None:
            if check.on_no_match == NoMatch.SKIP:
                return None
            return OneResult(passed=False, values={"field": check.field})
        value = found.group(1).strip() if check.strip else found.group(1)
        values = {
            "field": check.field,
            "value": value,
            "length": str(len(value)),
            "limit": str(check.max_length),
        }
        valid = (
            (not check.pattern or bool(re.fullmatch(check.pattern, value)))
            and (not check.max_length or len(value) <= check.max_length)
            and (not check.one_of or value in check.one_of)
        )
        return OneResult(
            passed=valid, values=values | {"allowed": ", ".join(check.one_of)}
        )


# --- The engine ----------------------------------------------------------------

TEXT_KINDS = frozenset(
    {CheckKind.REGEX, CheckKind.HTML_COMMENT, CheckKind.INVISIBLE_CHARS}
    | {CheckKind.BLANK_RUN, CheckKind.LONG_LINE, CheckKind.PUBLIC_IP}
)
FILE_KINDS = frozenset(
    {CheckKind.FILE_MATCH, CheckKind.HIDDEN_PATH, CheckKind.UNSAFE_PATH}
    | {CheckKind.IMAGE_MAGIC, CheckKind.BINARY_TEXT, CheckKind.UNKNOWN_FILE_TYPE}
    | {CheckKind.FILE_COUNT, CheckKind.FILE_SIZE}
)
CODE_KINDS = frozenset(
    {CheckKind.PYTHON_IMPORT, CheckKind.PYTHON_THIRD_PARTY, CheckKind.PYTHON_CALL}
    | {CheckKind.PYTHON_YAML_LOAD, CheckKind.PYTHON_SYNTAX}
    | {CheckKind.JS_MODULE, CheckKind.JS_THIRD_PARTY}
)
SKILL_KINDS = frozenset({CheckKind.FRONTMATTER_PARSE, CheckKind.UNUSED_TOOLS})
ONE_RESULT_KINDS = frozenset(
    {CheckKind.FRONTMATTER_REQUIRED, CheckKind.FRONTMATTER_VALUE}
    | {CheckKind.HEADING_REQUIRED, CheckKind.BODY_MAX_LINES, CheckKind.PROSE_FORBIDDEN}
)
EXAMPLE_PATH_KINDS = FILE_KINDS


class RuleLoader:
    """Loads and validates every rule file in a folder (I/O). A bad file fails here."""

    def __init__(self, rules_dir: Path) -> None:
        self.rules_dir = rules_dir

    def load(self) -> list[Rule]:
        rules: list[Rule] = []
        for path in sorted(self.rules_dir.glob("*" + RULE_FILE_SUFFIX)):
            try:
                group = RuleFile.model_validate_json(path.read_text(encoding="utf-8"))
            except ValidationError as error:
                raise InputError(
                    f"{path.name} is not a valid rule file: {error}"
                ) from error
            if path.name != group.type + RULE_FILE_SUFFIX:
                raise InputError(
                    f"{path.name} holds {group.type} rules; rename it {group.type}{RULE_FILE_SUFFIX}"
                )
            rules += [
                Rule.model_validate(spec.model_dump() | {"type": group.type})
                for spec in group.rules
            ]
        ids = [rule.id for rule in rules]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        missing = sorted(set(RuleId) - set(ids))
        if duplicates or missing:
            raise InputError(
                f"rules defined twice: {duplicates}; rules missing: {missing}"
            )
        return rules


class CheckRunner:
    """Runs one check over a skill and returns its results (pure)."""

    def __init__(self, rule: Rule, check: _CheckBase, view: SkillView) -> None:
        self.rule = rule
        self.check = check
        self.view = view

    def run(self) -> list[Result]:
        kind = self.check.kind
        if kind in ONE_RESULT_KINDS:
            return self._one()
        return [self._result(m) for m in self._matches(kind)]

    def _matches(self, kind: CheckKind) -> list[Match]:
        selected = FileSelector(self.check, self.view).select()
        if kind in TEXT_KINDS:
            return [
                m for t in selected.texts for m in TextMatcher(self.check, t).matches()
            ]
        if kind in FILE_KINDS:
            return FileMatcher(self.check, selected.files).matches()
        if kind in CODE_KINDS:
            local = frozenset(
                PurePosixPath(t.path).stem
                for t in self.view.texts
                if t.path.endswith(".py")
            )
            return [
                m
                for t in selected.texts
                for m in CodeMatcher(self.check, t, local).matches()
            ]
        return SkillMatcher(self.check, self.view.skill_text).matches()

    def _one(self) -> list[Result]:
        outcome = StandardEvaluator(self.check, self.view.skill_text).evaluate()
        if outcome is None:
            return []
        template = self.check.pass_message if outcome.passed else self.check.message
        status = Status.PASSED if outcome.passed else self._found_status()
        return [
            self._base(status).model_copy(
                update={
                    "path": SKILL_FILE,
                    "message": template.format(**outcome.values),
                }
            )
        ]

    def _found_status(self) -> Status:
        return Status.CONFIRMED if self.check.level == Level.ERROR else Status.OPEN

    def _base(self, status: Status) -> Result:
        return Result(
            rule_id=self.rule.id,
            check_id=self.check.id,
            type=self.rule.type,
            level=self.check.level,
            status=status,
            source=Source.CODE,
            message=self.check.message,
            fix=self.check.fix or self.rule.fix,
        )

    def _result(self, match: Match) -> Result:
        return self._base(self._found_status()).model_copy(
            update={"path": match.path, "line": match.line, "quote": match.quote}
        )


class RuleEngine:
    """Runs every code check of the chosen rules over a skill (pure)."""

    def __init__(self, rules: list[Rule], view: SkillView) -> None:
        self.rules = rules
        self.view = view

    def run(self) -> list[Result]:
        results = [
            r
            for rule in self.rules
            for c in rule.checks
            for r in CheckRunner(rule, c, self.view).run()
        ]
        return sorted(
            results,
            key=lambda r: (
                r.status == Status.PASSED,
                r.level != Level.ERROR,
                r.path,
                r.line,
            ),
        )


class TaskBuilder:
    """Turns every rule's review into tasks for the agent (pure)."""

    def __init__(self, rules: list[Rule], view: SkillView) -> None:
        self.rules = rules
        self.view = view

    def build(self) -> list[ReviewTask]:
        per_file = [
            r.id for r in self.rules if r.review and r.review.scope == Scope.FILE
        ]
        per_skill = [
            r.id for r in self.rules if r.review and r.review.scope == Scope.SKILL
        ]
        tasks = [
            ReviewTask(
                task_id=f"file:{t.path}",
                scope=Scope.FILE,
                rule_ids=per_file,
                path=t.path,
                line_count=len(t.text.splitlines()),
            )
            for t in self._review_texts()
            if per_file
        ]
        tasks += [
            ReviewTask(task_id=f"skill:{rid}", scope=Scope.SKILL, rule_ids=[rid])
            for rid in per_skill
        ]
        return tasks

    def _review_texts(self) -> list[TextFile]:
        order = {SKILL_FILE: 0, "references": 1, "scripts": 2, "assets": 3}
        texts = [t for t in self.view.texts if not in_evals(t.path)]
        return sorted(
            texts,
            key=lambda t: (
                order.get(t.path, order.get(PurePosixPath(t.path).parts[0], 4)),
                t.path,
            ),
        )


class ReviewCopier:
    """Copies the skill's safe files to the review folder (I/O). Runs nothing."""

    def __init__(self, source: SkillSource, review_dir: Path) -> None:
        self.source = source
        self.review_dir = review_dir

    def copy(self) -> None:
        if self.review_dir.exists() and any(self.review_dir.iterdir()):
            raise InputError(
                f"{self.review_dir} is not empty; give an empty --out folder"
            )
        for item in self.source.files:
            if is_safe_path(item):
                target = self.review_dir.joinpath(*PurePosixPath(item.path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(item.data)


class CheckRequest(_Strict):
    source: Path
    out: Path
    rule_type: RuleType | None = None


class CheckCommand:
    """Facade for check: load the rules and the skill, run, copy, write results (I/O)."""

    def __init__(self, request: CheckRequest) -> None:
        self.request = request

    def run(self) -> Results:
        rules = [
            r
            for r in RuleLoader(RULES_DIR).load()
            if self.request.rule_type in (None, r.type)
        ]
        source = SourceLoader(self.request.source).load()
        view = SkillView.from_source(source)
        review_dir = self.request.out / REVIEW_DIR / source.folder_name
        ReviewCopier(source, review_dir).copy()
        results = Results(
            skill=_skill_name(view.skill_text),
            source=str(self.request.source),
            review_dir=str(review_dir),
            rule_ids=[r.id for r in rules],
            results=RuleEngine(rules, view).run(),
            tasks=TaskBuilder(rules, view).build(),
        )
        ResultsWriter(self.request.out).write(results)
        return results


class ResultsWriter:
    """Writes <out>/results.json (I/O)."""

    def __init__(self, out: Path) -> None:
        self.out = out

    def write(self, results: Results) -> None:
        path = self.out / RESULTS_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        text = results.model_dump_json(indent=2) + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")


class ResultsReader:
    """Reads and validates <out>/results.json (I/O)."""

    def __init__(self, out: Path) -> None:
        self.out = out

    def read(self) -> Results:
        path = self.out / RESULTS_FILE
        try:
            return Results.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as error:
            raise InputError(f"cannot read {path}: {error}") from error


class VerifyIssue(_Strict):
    task_or_result: str
    problem: str


class VerdictVerifier:
    """Checks the agent finished the review and every quote is real (pure)."""

    def __init__(self, results: Results, texts: dict[str, str]) -> None:
        self.results = results
        self.texts = texts

    def verify(self) -> list[VerifyIssue]:
        issues = [
            VerifyIssue(task_or_result=t.task_id, problem=self._task_problem(t))
            for t in self.results.tasks
            if self._task_problem(t)
        ]
        for index, result in enumerate(self.results.results):
            problem = self._result_problem(result)
            if problem:
                issues.append(
                    VerifyIssue(
                        task_or_result=f"result {index} ({result.rule_id})",
                        problem=problem,
                    )
                )
        return issues

    @staticmethod
    def _task_problem(task: ReviewTask) -> str:
        if not task.done:
            return "not done"
        if task.scope == Scope.FILE and task.lines_read != task.line_count:
            return f"read {task.lines_read} of {task.line_count} lines"
        return ""

    def _result_problem(self, result: Result) -> str:
        if result.status == Status.OPEN:
            return "warning not judged (open)"
        if result.source == Source.AGENT and result.status == Status.PASSED:
            return "an agent result is a finding, so it can't be passed"
        if result.status in (Status.DISMISSED, Status.UNSURE) and not result.reason:
            return f"{result.status} needs a reason"
        if result.source == Source.AGENT and result.status != Status.DISMISSED:
            return self._quote_problem(result)
        return ""

    def _quote_problem(self, result: Result) -> str:
        if not result.reason:
            return "an agent finding needs a reason"
        if not result.path:
            return ""
        text = self.texts.get(result.path)
        if text is None:
            return f"no file {result.path}"
        lines = text.splitlines()
        span = result.quote.count("\n") + 1
        window = " ".join(
            " ".join(lines[max(result.line - 1, 0) : result.line - 1 + span]).split()
        )
        quote = " ".join(result.quote.split()).removesuffix("...")
        if result.line < 1 or not quote or quote not in window:
            return f"quote not found at {result.path}:{result.line}"
        return ""


class ReportBuilder:
    """Renders the security report from results.json (pure)."""

    def __init__(self, results: Results, rules: dict[RuleId, Rule]) -> None:
        self.results = results
        self.rules = rules

    def build(self) -> str:
        findings = [r for r in self.results.results if r.status == Status.CONFIRMED]
        unsure = [r for r in self.results.results if r.status == Status.UNSURE]
        dismissed = [r for r in self.results.results if r.status == Status.DISMISSED]
        warnings = [
            r
            for r in self.results.results
            if r.level == Level.WARNING and r.source == Source.CODE
        ]
        file_tasks = [t for t in self.results.tasks if t.scope == Scope.FILE]
        today = datetime.datetime.now(datetime.UTC).date().isoformat()
        lines = [f"**{self.results.skill or 'Skill'}, review of {today}**", ""]
        lines.append(f"**{self._verdict(findings, unsure)}**")
        if findings or unsure:
            lines += [
                "",
                "| # | Rule | Where | What it says | Why it matters | Fix |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        for number, r in enumerate(findings + unsure, start=1):
            where = f"`{r.path}:{r.line}`" if r.path else "the skill"
            why = r.reason or r.message
            name = self.rules[r.rule_id].name + (
                " (unsure)" if r.status == Status.UNSURE else ""
            )
            lines.append(
                f'| {number} | {name} | {where} | "{_cell(r.quote)}" | {_cell(why)} | {_cell(r.fix)} |'
            )
        lines += [
            "",
            "**What was checked**",
            f"- Code checks: {len(self.results.rule_ids)} rules over the skill's files.",
            f"- Line-by-line reading: {len(file_tasks)} files, {sum(t.lines_read for t in file_tasks)} lines.",
            f"- Warnings judged: {len(warnings)} ({len([w for w in warnings if w.status == Status.CONFIRMED])} findings, {len(dismissed)} false alarms dismissed).",
            "",
            DISCLAIMER,
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _verdict(findings: list[Result], unsure: list[Result]) -> str:
        if findings:
            return f"Don't install or publish yet: {len(findings)} findings"
        if unsure:
            return f"Check {len(unsure)} lines first"
        return "No findings in the checks below"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


class SchemaBuilder:
    """Builds rule.schema.json and results.schema.json from the models, with every
    enum value's definition (pure)."""

    def build(self) -> dict[str, dict]:
        return {
            RULE_SCHEMA_FILE: self._with_definitions(RuleFile.model_json_schema()),
            RESULTS_SCHEMA_FILE: self._with_definitions(Results.model_json_schema()),
        }

    @staticmethod
    def _with_definitions(schema: dict) -> dict:
        for spec in ENUM_SPECS:
            schema.setdefault("$defs", {})[spec.name] = {
                "title": spec.name,
                "description": spec.description,
                "type": "string",
                "oneOf": [
                    {"const": value, "description": text}
                    for value, text in spec.definitions.items()
                ],
            }
        return schema


def _skill_name(skill: TextFile | None) -> str:
    if skill is None:
        return ""
    try:
        front = yaml.safe_load(skill.frontmatter or "{}")
    except yaml.YAMLError:
        return ""
    return str(front.get("name", "")) if isinstance(front, dict) else ""


def _texts_from(review_dir: Path) -> dict[str, str]:
    return {
        p.relative_to(review_dir).as_posix(): p.read_text(
            encoding="utf-8", errors="replace"
        )
        for p in review_dir.rglob("*")
        if p.is_file() and is_text_path(p.name)
    }


def _run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    match args.command:
        case "check":
            rule_type = RuleType(args.type) if args.type else None
            results = CheckCommand(
                CheckRequest(source=Path(args.source), out=out, rule_type=rule_type)
            ).run()
            found = [r for r in results.results if r.status != Status.PASSED]
            logger.info(
                "%s: %d results, %d review tasks",
                results.skill,
                len(found),
                len(results.tasks),
            )
            for r in found:
                logger.info(
                    "[%s %s] %s %s:%d %s | %s",
                    r.level,
                    r.status,
                    r.rule_id,
                    r.path,
                    r.line,
                    r.message,
                    r.quote,
                )
            logger.info("Wrote %s", out / RESULTS_FILE)
            return EXIT_OK
        case "verify":
            results = ResultsReader(out).read()
            issues = VerdictVerifier(
                results, _texts_from(Path(results.review_dir))
            ).verify()
            for issue in issues:
                logger.info("FAIL  %s: %s", issue.task_or_result, issue.problem)
            for r in results.results:
                if r.status == Status.UNSURE:
                    logger.info(
                        "ASK   %s %s:%d %s", r.rule_id, r.path, r.line, r.reason
                    )
            logger.info(
                "%d tasks, %d results, %d problems",
                len(results.tasks),
                len(results.results),
                len(issues),
            )
            return EXIT_INCOMPLETE if issues else EXIT_OK
        case "report":
            results = ResultsReader(out).read()
            rules = {r.id: r for r in RuleLoader(RULES_DIR).load()}
            report = ReportBuilder(results, rules).build()
            path = out / REPORT_FILE
            path.write_text(report, encoding="utf-8", newline="\n")
            logger.info("Wrote %s\n%s", path, report)
            return EXIT_OK
        case _:
            for name, schema in SchemaBuilder().build().items():
                (out / name).write_text(
                    json.dumps(schema, indent=2) + "\n", encoding="utf-8", newline="\n"
                )
                logger.info("Wrote %s", out / name)
            return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the skill rules.")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser(
        "check", help="Run the code checks and write the review tasks."
    )
    check.add_argument("source", help="Skill folder, .zip, or SKILL.md.")
    check.add_argument(
        "--out",
        required=True,
        help="An empty folder for results.json and the review copy.",
    )
    check.add_argument(
        "--type", choices=[t.value for t in RuleType], help="Only rules of this type."
    )
    for name, text in (
        ("verify", "Check the agent's verdicts."),
        ("report", "Print the report."),
    ):
        commands.add_parser(name, help=text).add_argument("--out", required=True)
    commands.add_parser("schema", help="Write the JSON schemas.").add_argument(
        "--out", required=True
    )
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except InputError as error:
        logger.error("%s", error)
        return EXIT_BAD_INPUT


if __name__ == "__main__":
    sys.exit(main())
