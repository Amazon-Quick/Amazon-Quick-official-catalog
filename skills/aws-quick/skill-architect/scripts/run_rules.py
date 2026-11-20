"""
description: The rule engine. Loads the rule files in references/rules/ (security_rule.json and standard_rule.json, one file per rule type), validates them, runs their code checks on a skill read as data, judges each match's context as the code lens, writes the results and the agent's review tasks in one standard results.json, verifies the verdicts, quotes, and three-lens dismissals, records each confirmed finding the user accepts, lists the findings still waiting for the user's decision, and renders the security report.
last_updated: 2026-11-20

Usage:
    python run_rules.py check <skill folder, .zip, or SKILL.md> --out <dir> [--type security|standard]
    python run_rules.py verify --out <dir>
    python run_rules.py accept --out <dir> --result <index>
    python run_rules.py pending --out <dir>
    python run_rules.py report --out <dir>
    python run_rules.py schema --out <dir>
In AWS Quick, import the module and call main([...]) with the same arguments.
Exit codes: 0 done, 1 the review is incomplete, a quote doesn't match, or a finding waits for the user's decision, 2 bad input.
"""

from __future__ import annotations

import argparse
import ast
import base64
import bisect
import datetime
import fnmatch
import io
import ipaddress
import itertools
import json
import logging
import re
import stat
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
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
# A Windows drive path such as C:/x escapes the skill folder like an absolute path.
DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:")
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
DATA_URI_RE = re.compile(
    r"data:([A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+);base64,([A-Za-z0-9+/=]+)"
)
XMLNS_RE = re.compile(r"\bxmlns(?::[A-Za-z]+)?\s*=\s*[\"']https?://www\.w3\.org/")
MEDIA_SIGNATURES: dict[str, tuple[int, bytes]] = {
    "image/png": (0, bytes.fromhex("89504e470d0a1a0a")),
    "image/jpeg": (0, bytes.fromhex("ffd8ff")),
    "image/gif": (0, b"GIF8"),
    "image/webp": (8, b"WEBP"),
    "video/mp4": (4, b"ftyp"),
    "audio/mp4": (4, b"ftyp"),
    "video/webm": (0, bytes.fromhex("1a45dfa3")),
    "audio/mpeg": (0, b"ID3"),
    "audio/wav": (8, b"WAVE"),
}
SVG_MEDIA = "image/svg+xml"
# Base64 writes every three bytes as four characters.
B64_GROUP_BYTES = 3
B64_GROUP_CHARS = 4
B64_TEXT_RE = re.compile(r"[A-Za-z0-9+/]+={0,2}")
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
    RESOURCE_ABUSE = "resource_abuse"
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
    CODE_BLOCKS = "code_blocks"


class NoMatch(StrEnum):
    """What a frontmatter_value check does when its extract pattern finds no value."""

    SKIP = "skip"
    FAIL = "fail"


class Lens(StrEnum):
    """One independent way of judging a finding."""

    CODE = "code"
    AGENT = "agent"
    REVIEWER = "reviewer"


class LensVerdict(StrEnum):
    """What one lens concluded about a finding."""

    BENIGN = "benign"
    RISK = "risk"
    UNCLEAR = "unclear"


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
    SKILL_SIZE = "skill_size"
    FRONTMATTER_PARSE = "frontmatter_parse"
    UNUSED_TOOLS = "unused_tools"
    PYTHON_IMPORT = "python_import"
    PYTHON_THIRD_PARTY = "python_third_party"
    PYTHON_CALL = "python_call"
    PYTHON_YAML_LOAD = "python_yaml_load"
    PYTHON_SYNTAX = "python_syntax"
    PYTHON_LONG_LITERAL = "python_long_literal"
    PYTHON_RESOURCE = "python_resource"
    DATA_URI = "data_uri"
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
            "dangerous_instructions": "Steps that get around a security control, run commands or programs, or change system settings.",
            "security_guidance": "Advice that would weaken someone's security if they followed it.",
            "supply_chain": "Packages the sandbox doesn't provide, install steps, or code pulled from somewhere that can change.",
            "excessive_permissions": "Tools the workflows don't use or the purpose doesn't need, and changes made without the user's confirmation.",
            "obfuscated_intent": "Anything that hides what the skill does: hidden text, encoded strings, unreadable files, or a description that doesn't match the workflows.",
            "tool_hijacking": "Steps that chain tools to reach systems the purpose doesn't need.",
            "context_poisoning": "Steps that save notes or files that later conversations read, to change how the agent behaves next time.",
            "secrets_and_personal_data": "Real credentials, personal data, or account details in the files, or steps that collect personal data the purpose doesn't need.",
            "resource_abuse": "Code that uses far more CPU, RAM, or disk than the task needs, or runs without a bound, even when it works.",
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
            "code_blocks": "Only the fenced code blocks of a Markdown file, with everything else blanked out, keeping line numbers.",
        },
    ),
    EnumSpec(
        name="Lens",
        enum=Lens,
        description="One independent way of judging a finding. A finding is dismissed as a false alarm only when the lenses agree.",
        definitions={
            "code": "A second program the engine runs at check time on the match's context, such as its syntax tree, its arguments, or its surrounding attribute. It is different from the check that raised the match.",
            "agent": "The agent's reading of the finding in its surrounding text, against the rule's review question.",
            "reviewer": "A separate background task with no conversation history that judges the finding from the file and the rule alone.",
        },
    ),
    EnumSpec(
        name="LensVerdict",
        enum=LensVerdict,
        description="What one lens concluded about a finding.",
        definitions={
            "benign": "The lens found evidence the match is harmless.",
            "risk": "The lens found evidence the match is a real risk. A finding with any risk verdict can't be dismissed.",
            "unclear": "The lens can't tell. The code lens says unclear when only reading can judge the meaning, such as what a word means in a sentence.",
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
            "file_match": "Flags files whose suffix or name is on the list, or whose name matches the pattern.",
            "hidden_path": "Flags hidden files and cache folders.",
            "unsafe_path": "Flags symbolic links and paths that escape the skill folder.",
            "image_magic": "Flags an image file whose bytes don't match its suffix.",
            "binary_text": "Flags a text file that contains binary data.",
            "unknown_file_type": "Flags files whose suffix isn't on the allowed list.",
            "file_count": "Flags a skill with more files than the limit.",
            "file_size": "Flags a file larger than the limit.",
            "skill_size": "Flags a skill whose selected files add up to more than the limit.",
            "frontmatter_parse": "Flags a SKILL.md with no frontmatter, frontmatter that doesn't parse, or a custom YAML tag.",
            "unused_tools": "Flags frontmatter tools that no workflow's tools=[...] names.",
            "python_import": "Flags Python imports of the listed modules.",
            "python_third_party": "Flags Python imports outside the standard library, the skill's own modules, and the allowed list.",
            "python_call": "Flags Python calls to the listed functions.",
            "python_yaml_load": "Flags yaml.load without a safe loader.",
            "python_syntax": "Flags Python that doesn't parse, since unparsed code can't be reviewed.",
            "python_resource": "Flags Python that can hold the CPU, RAM, or disk: a while True loop with no break or return, and a call or repetition whose size is a literal over the limit.",
            "data_uri": "Flags a base64 data URI whose media type isn't on the allowed list, whose payload doesn't start with that type's encoded signature, or that holds an SVG, which can't be checked for active content without decoding it. A real image, video, or audio file of the declared type passes.",
            "python_long_literal": "Flags a Python string or bytes literal, other than a docstring, that is longer than the limit or has a long run with no whitespace, which is how data or code is hidden in a script.",
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
    name_pattern: Pattern = ""


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


class SkillSizeCheck(_CheckBase):
    kind: Literal[CheckKind.SKILL_SIZE]
    max_total_bytes: int = Field(gt=0)


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
    allowed: list[str] = []


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


class PythonResourceCheck(_ExampleCheck):
    kind: Literal[CheckKind.PYTHON_RESOURCE]
    max_size: int = Field(gt=0)
    sized_calls: list[str] = Field(min_length=1)


class DataUriCheck(_ExampleCheck):
    kind: Literal[CheckKind.DATA_URI]
    allowed_media: list[str] = Field(min_length=1)


class PythonLongLiteralCheck(_ExampleCheck):
    kind: Literal[CheckKind.PYTHON_LONG_LITERAL]
    max_chars: int = Field(gt=0)
    max_unbroken: int = Field(gt=0)


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
    | SkillSizeCheck
    | FrontmatterParseCheck
    | UnusedToolsCheck
    | PythonImportCheck
    | PythonThirdPartyCheck
    | PythonCallCheck
    | PythonYamlLoadCheck
    | PythonSyntaxCheck
    | PythonLongLiteralCheck
    | PythonResourceCheck
    | DataUriCheck
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


class LensResult(_Strict):
    """One lens's verdict on a finding, with the evidence it rests on."""

    lens: Lens
    verdict: LensVerdict
    evidence: str = Field(min_length=1)


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
    lenses: list[LensResult] = []


class Acceptance(_Strict):
    """One confirmed finding the user accepted after seeing its evidence. It records
    no name: the user's own answer in the conversation is the consent."""

    rule_id: RuleId
    path: str
    line: int
    quote: str
    date: datetime.date


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
    acceptances: list[Acceptance] = []


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
    """Reads a skill from the zip bytes it is given (pure)."""

    def __init__(self, data: bytes) -> None:
        self.data = data

    def read(self) -> SkillSource:
        try:
            archive = zipfile.ZipFile(io.BytesIO(self.data))
        except zipfile.BadZipFile as error:
            raise InputError(f"not a valid zip file: {error}") from error
        entries = [info for info in archive.infolist() if not info.is_dir()]
        names = [info.filename for info in entries]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise InputError(
                f"the zip holds more than one entry named {duplicates}, so a reviewer "
                "can't tell which one installs"
            )
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
    escapes = (
        item.path.startswith("/")
        or ".." in parts
        or "\\" in item.path
        or bool(DRIVE_PATH_RE.match(item.path))
    )
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

    @property
    def code_lines(self) -> list[str]:
        """Every line of the file with only fenced code kept, line numbers kept."""
        out, in_fence = [], False
        for line in self.text.split("\n"):
            if line.strip().startswith(FENCE_LINE_PREFIX):
                in_fence = not in_fence
                out.append("")
                continue
            out.append(line if in_fence else "")
        return out

    def line_at(self, offset: int) -> int:
        return bisect.bisect_right(self.line_starts, offset)

    @cached_property
    def line_starts(self) -> list[int]:
        """The offset each line starts at, computed once per file."""
        return [0] + [i + 1 for i, char in enumerate(self.text) if char == "\n"]


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
            case CheckKind.DATA_URI:
                return self._data_uris()
            case _:
                return []

    def _data_uris(self) -> list[Match]:
        found = []
        for m in DATA_URI_RE.finditer(self.text.text):
            problem = MediaPayload(m.group(1).lower(), m.group(2)).problem(
                self.check.allowed_media
            )
            if problem:
                found.append(
                    Match(
                        path=self.text.path,
                        line=self.text.line_at(m.start()),
                        quote=_clip(f"data:{m.group(1)};base64 ({problem})"),
                    )
                )
        return found

    def _regex(self) -> list[Match]:
        check = self.check
        pattern, exclude = (
            re.compile(check.pattern),
            re.compile(check.exclude or "(?!)"),
        )
        if check.target == Target.CODE_BLOCKS:
            return _dedupe(
                [
                    Match(path=self.text.path, line=i + 1, quote=_clip(m.group(0)))
                    for i, line in enumerate(self.text.code_lines)
                    for m in pattern.finditer(line)
                    if not exclude.search(m.group(0))
                ]
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


class MediaPayload:
    """Decides whether a base64 payload is the media file its type declares (pure).
    It compares the payload's text with the type's encoded signature, so the engine
    never decodes what a skill embeds."""

    def __init__(self, media: str, payload: str) -> None:
        self.media = media
        self.payload = payload

    def problem(self, allowed: list[str]) -> str:
        """Empty when the payload is a real file of an allowed media type."""
        if self.media not in allowed:
            return f"{self.media} is not an allowed media type"
        if len(self.payload) % B64_GROUP_CHARS:
            return "the payload is not valid base64"
        if self.media == SVG_MEDIA:
            return (
                "a base64 SVG can't be read for active content; embed the SVG as text"
            )
        groups = MEDIA_PREFIXES.get(self.media)
        if groups is None:
            return f"no signature is known for {self.media}"
        if not SignatureMatcher(self.payload, groups).matches():
            return f"the bytes are not {self.media}"
        return ""


class EncodedGroup(_Strict):
    """One four-character base64 group a payload holds when it starts with a
    media signature: its position in the payload and the texts it can be."""

    start: int
    options: frozenset[str]


class SignatureEncoder:
    """Turns a media signature into the base64 groups a payload of that type
    starts with (pure). Base64 encodes three bytes as four characters, so a group
    the signature covers fully has one text. A group that shares one byte with the
    file's own content has 256, and a group with two unknown bytes is left out."""

    def __init__(self, offset: int, magic: bytes) -> None:
        self.offset = offset
        self.magic = magic

    def encode(self) -> list[EncodedGroup]:
        end = self.offset + len(self.magic)
        indexes = range(
            self.offset // B64_GROUP_BYTES, (end - 1) // B64_GROUP_BYTES + 1
        )
        unknown = {i: self._unknown_count(i) for i in indexes}
        chosen = [i for i in indexes if unknown[i] == 0] or [
            i for i in indexes if unknown[i] == 1
        ]
        return [self._group(i) for i in chosen]

    def _byte_choices(self, index: int) -> list[range | list[int]]:
        choices: list[range | list[int]] = []
        for position in range(index * B64_GROUP_BYTES, (index + 1) * B64_GROUP_BYTES):
            inside = self.offset <= position < self.offset + len(self.magic)
            choices.append(
                [self.magic[position - self.offset]] if inside else range(256)
            )
        return choices

    def _unknown_count(self, index: int) -> int:
        return sum(1 for choice in self._byte_choices(index) if len(choice) > 1)

    def _group(self, index: int) -> EncodedGroup:
        options = frozenset(
            base64.b64encode(bytes(combo)).decode("ascii")
            for combo in itertools.product(*self._byte_choices(index))
        )
        return EncodedGroup(start=index * B64_GROUP_CHARS, options=options)


class SignatureMatcher:
    """Decides whether a payload's text holds every encoded group (pure)."""

    def __init__(self, payload: str, groups: list[EncodedGroup]) -> None:
        self.payload = payload
        self.groups = groups

    def matches(self) -> bool:
        return bool(self.groups) and all(
            self.payload[g.start : g.start + B64_GROUP_CHARS] in g.options
            for g in self.groups
        )


MEDIA_PREFIXES: dict[str, list[EncodedGroup]] = {
    media: SignatureEncoder(offset, magic).encode()
    for media, (offset, magic) in MEDIA_SIGNATURES.items()
}


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
            case CheckKind.SKILL_SIZE:
                total = sum(len(item.data) for item in self.files)
                if total > self.check.max_total_bytes:
                    return [Match(path="", quote=f"{total} bytes")]
                return []
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
        pattern = self.check.name_pattern
        return (
            path.suffix.lower() in suffixes
            or path.name.lower() in names
            or bool(pattern and re.search(pattern, path.name))
        )

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
        if kind == CheckKind.PYTHON_LONG_LITERAL:
            return self._long_literals(tree)
        if kind == CheckKind.PYTHON_RESOURCE:
            return self._resource_hogs(tree)
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

    def _long_literals(self, tree: ast.AST) -> list[Match]:
        docstrings = _docstring_nodes(tree)
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or id(node) in docstrings:
                continue
            if not isinstance(node.value, str | bytes):
                continue
            value = node.value
            text = value if isinstance(value, str) else value.decode("latin-1")
            run = max((len(part) for part in text.split()), default=0)
            if len(text) > self.check.max_chars or run > self.check.max_unbroken:
                found.append(
                    self._at(node, f"{len(text)} characters, longest run {run}")
                )
        return found

    def _resource_hogs(self, tree: ast.AST) -> list[Match]:
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.While) and _always_true(node.test):
                if not _has_exit(node):
                    found.append(
                        self._at(node, "while True loop with no break or return")
                    )
            elif isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name in self.check.sized_calls:
                    size = max((_literal_size(a) for a in node.args), default=0)
                    if size > self.check.max_size:
                        found.append(self._at(node, f"{name} sized {size}"))
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                size = max(_literal_size(node.left), _literal_size(node.right))
                if size > self.check.max_size:
                    found.append(self._at(node, f"repetition of size {size}"))
        return found

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
        return (
            top not in self.local_modules
            and top not in sys.stdlib_module_names
            and top not in self.check.allowed
        )

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


def _always_true(test: ast.expr) -> bool:
    return isinstance(test, ast.Constant) and bool(test.value) is True


def _has_exit(loop: ast.While) -> bool:
    """True when the loop body can leave the loop: a break, return, or raise
    that isn't inside a nested loop or function."""
    stack = list(loop.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Break | ast.Return | ast.Raise):
            return True
        if isinstance(
            node,
            ast.For | ast.While | ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda,
        ):
            if isinstance(node, ast.For | ast.While):
                stack.extend(n for n in node.orelse)
            continue
        stack.extend(ast.iter_child_nodes(node))
    return False


def _literal_size(node: ast.expr) -> int:
    """The integer a literal expression evaluates to, such as 10**9, else 0."""
    try:
        value = _fold(node)
    except (ValueError, OverflowError, ZeroDivisionError):
        return 0
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _fold(node: ast.expr) -> int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.BinOp):
        left, right = _fold(node.left), _fold(node.right)
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Pow) and 0 <= right <= 64:
            return left**right
        if isinstance(node.op, ast.LShift) and 0 <= right <= 64:
            return left << right
        if isinstance(node.op, ast.Add):
            return left + right
    if isinstance(node, ast.Tuple | ast.List):
        sizes = [_fold(e) for e in node.elts]
        out = 1
        for size in sizes:
            out *= size
        return out
    raise ValueError("not a literal size")


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """The ids of the Constant nodes that are module, class, or function docstrings."""
    found = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
        ):
            found.add(id(body[0].value))
    return found


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


# --- The code lens ----------------------------------------------------------------

DYNAMIC_CODE_CALLS = frozenset({"exec", "eval", "compile", "breakpoint"})
CERTAIN_KINDS = frozenset(
    {CheckKind.FILE_MATCH, CheckKind.HIDDEN_PATH, CheckKind.UNSAFE_PATH}
    | {CheckKind.IMAGE_MAGIC, CheckKind.BINARY_TEXT, CheckKind.UNKNOWN_FILE_TYPE}
    | {CheckKind.SKILL_SIZE, CheckKind.FRONTMATTER_PARSE, CheckKind.UNUSED_TOOLS}
    | {
        CheckKind.PYTHON_IMPORT,
        CheckKind.PYTHON_THIRD_PARTY,
        CheckKind.PYTHON_YAML_LOAD,
    }
    | {CheckKind.PYTHON_SYNTAX, CheckKind.PYTHON_RESOURCE, CheckKind.DATA_URI}
    | {CheckKind.JS_MODULE, CheckKind.JS_THIRD_PARTY, CheckKind.INVISIBLE_CHARS}
    | {CheckKind.BLANK_RUN}
)


class ContextLens:
    """The code lens: a second program that judges one match from its context
    (pure). It never runs the skill's code; it reads the syntax tree, the
    arguments, the encoded signature of an embedded file, or the surrounding
    attribute."""

    def __init__(self, check: _CheckBase, match: Match, view: SkillView) -> None:
        self.check = check
        self.match = match
        self.view = view

    def judge(self) -> LensResult:
        kind = self.check.kind
        if kind == CheckKind.PYTHON_CALL:
            return self._call()
        if kind == CheckKind.PYTHON_LONG_LITERAL:
            return self._literal()
        if kind == CheckKind.REGEX and XMLNS_RE.search(self._line()):
            return self._lens(
                LensVerdict.BENIGN,
                "The match is an XML namespace identifier in an xmlns attribute, which no tool fetches.",
            )
        if kind in CERTAIN_KINDS and self.check.level == Level.ERROR:
            return self._lens(
                LensVerdict.RISK,
                f"The check is certain for this kind of match: {self.check.message}.",
            )
        if kind == CheckKind.PYTHON_RESOURCE:
            return self._lens(
                LensVerdict.RISK,
                f"The syntax tree shows {self.match.quote}, which can hold the CPU, RAM, or disk.",
            )
        return self._lens(
            LensVerdict.UNCLEAR,
            "Code can't judge what this match means in its context; only reading can.",
        )

    def _lens(self, verdict: LensVerdict, evidence: str) -> LensResult:
        return LensResult(lens=Lens.CODE, verdict=verdict, evidence=evidence)

    def _text(self) -> str:
        found = next((t for t in self.view.texts if t.path == self.match.path), None)
        return found.text if found else ""

    def _line(self) -> str:
        lines = self._text().split("\n")
        index = self.match.line - 1
        return lines[index] if 0 <= index < len(lines) else ""

    def _nodes(self) -> list[ast.AST]:
        try:
            tree = ast.parse(self._text())
        except SyntaxError:
            return []
        return [n for n in ast.walk(tree) if getattr(n, "lineno", 0) == self.match.line]

    def _call(self) -> LensResult:
        name = self.match.quote
        if name in DYNAMIC_CODE_CALLS:
            return self._lens(LensVerdict.RISK, f"{name} runs text as code.")
        calls = [
            n
            for n in self._nodes()
            if isinstance(n, ast.Call) and _call_name(n.func) == name
        ]
        if name == "__import__" and calls:
            literal = all(
                all(
                    isinstance(a, ast.Constant) and isinstance(a.value, str)
                    for a in c.args
                )
                and c.args
                for c in calls
            )
            if literal:
                modules = ", ".join(repr(a.value) for c in calls for a in c.args[:1])
                return self._lens(
                    LensVerdict.BENIGN,
                    f"Every argument is a fixed string, so it imports only {modules}.",
                )
            return self._lens(
                LensVerdict.RISK,
                "The module name is built at run time, so any module with that name would run.",
            )
        return self._lens(
            LensVerdict.UNCLEAR,
            f"Code can't tell what {name} does with its input here; only reading can.",
        )

    def _literal(self) -> LensResult:
        for node in self._nodes():
            if isinstance(node, ast.Constant) and isinstance(node.value, str | bytes):
                text = (
                    node.value
                    if isinstance(node.value, str)
                    else node.value.decode("latin-1")
                )
                media = _encoded_media(text)
                if media:
                    return self._lens(
                        LensVerdict.BENIGN,
                        f"The literal's base64 starts with the {media} file signature.",
                    )
        return self._lens(
            LensVerdict.UNCLEAR,
            "The literal doesn't start with a known image, video, or audio signature.",
        )


def _encoded_media(text: str) -> str:
    """The media type whose signature a base64 literal starts with, or empty. It
    compares encoded text and never decodes the literal (pure)."""
    uri = DATA_URI_RE.search(text)
    if uri:
        media, payload = uri.group(1).lower(), uri.group(2)
    else:
        media, payload = "", "".join(text.split())
    if len(payload) % B64_GROUP_CHARS or not B64_TEXT_RE.fullmatch(payload):
        return ""
    for name, groups in MEDIA_PREFIXES.items():
        if media in ("", name) and SignatureMatcher(payload, groups).matches():
            return name
    return ""


# --- The engine ----------------------------------------------------------------

TEXT_KINDS = frozenset(
    {CheckKind.REGEX, CheckKind.HTML_COMMENT, CheckKind.INVISIBLE_CHARS}
    | {CheckKind.BLANK_RUN, CheckKind.LONG_LINE, CheckKind.PUBLIC_IP}
    | {CheckKind.DATA_URI}
)
FILE_KINDS = frozenset(
    {CheckKind.FILE_MATCH, CheckKind.HIDDEN_PATH, CheckKind.UNSAFE_PATH}
    | {CheckKind.IMAGE_MAGIC, CheckKind.BINARY_TEXT, CheckKind.UNKNOWN_FILE_TYPE}
    | {CheckKind.FILE_COUNT, CheckKind.FILE_SIZE, CheckKind.SKILL_SIZE}
)
CODE_KINDS = frozenset(
    {CheckKind.PYTHON_IMPORT, CheckKind.PYTHON_THIRD_PARTY, CheckKind.PYTHON_CALL}
    | {CheckKind.PYTHON_YAML_LOAD, CheckKind.PYTHON_SYNTAX}
    | {CheckKind.PYTHON_LONG_LITERAL, CheckKind.PYTHON_RESOURCE}
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
        lens = ContextLens(self.check, match, self.view).judge()
        return self._base(self._found_status()).model_copy(
            update={
                "path": match.path,
                "line": match.line,
                "quote": match.quote,
                "lenses": [lens],
            }
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
        if result.status == Status.DISMISSED:
            return DismissalJudge(result).problem()
        if result.source == Source.AGENT:
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


class DismissalJudge:
    """Decides whether a dismissal has the three-lens agreement it needs (pure).
    The agent and the reviewer must both find the match benign, no lens may find
    a risk, and an error raised by code also needs the code lens to find it benign."""

    def __init__(self, result: Result) -> None:
        self.result = result

    def problem(self) -> str:
        verdicts = {lens.lens: lens.verdict for lens in self.result.lenses}
        if LensVerdict.RISK in verdicts.values():
            return "a lens found a risk, so it can't be dismissed (confirm it, or mark it unsure)"
        missing = [
            lens.value
            for lens in (Lens.AGENT, Lens.REVIEWER)
            if verdicts.get(lens) != LensVerdict.BENIGN
        ]
        if missing:
            return "dismissed without a benign verdict from: " + ", ".join(missing)
        if self.result.source == Source.CODE and Lens.CODE not in verdicts:
            return "the code lens is missing; rerun check"
        needs_code = (
            self.result.source == Source.CODE and self.result.level == Level.ERROR
        )
        if needs_code and verdicts.get(Lens.CODE) != LensVerdict.BENIGN:
            return (
                "an error can be dismissed only when the code lens also finds it benign"
            )
        return ""


class CodeResultsGuard:
    """Checks that results.json still holds every code result the engine raises on
    the review copy, unchanged in level and code lens (pure). It stops a review
    from deleting or downgrading what code found."""

    def __init__(self, recorded: list[Result], recomputed: list[Result]) -> None:
        self.recorded = recorded
        self.recomputed = recomputed

    def verify(self) -> list[VerifyIssue]:
        recorded = {_key(r): r for r in self.recorded if r.source == Source.CODE}
        issues = []
        for fresh in self.recomputed:
            if fresh.status == Status.PASSED:
                continue
            kept = recorded.get(_key(fresh))
            name = f"{fresh.rule_id}.{fresh.check_id} {fresh.path}:{fresh.line}"
            if kept is None:
                issues.append(
                    VerifyIssue(task_or_result=name, problem="code result removed")
                )
                continue
            if kept.level != fresh.level or _code_lens(kept) != _code_lens(fresh):
                issues.append(
                    VerifyIssue(
                        task_or_result=name,
                        problem="code result level or code lens changed",
                    )
                )
        return issues


def _key(result: Result) -> tuple:
    return (result.rule_id, result.check_id, result.path, result.line, result.quote)


def _code_lens(result: Result) -> tuple:
    return tuple(
        (item.verdict, item.evidence)
        for item in result.lenses
        if item.lens == Lens.CODE
    )


# --- Acceptance and pending decisions -------------------------------------------


class Decision(_Strict):
    """One finding still waiting for the user to decide."""

    subject: str
    problem: str


def _accepts(acceptance: Acceptance, result: Result) -> bool:
    return (
        acceptance.rule_id == result.rule_id
        and acceptance.path == result.path
        and acceptance.line == result.line
        and acceptance.quote == result.quote
    )


def _is_accepted(results: Results, result: Result) -> bool:
    return any(_accepts(a, result) for a in results.acceptances)


class PendingDecisions:
    """Lists the security findings the user hasn't decided on yet (pure): every
    unsure finding, and every confirmed one they haven't accepted or fixed."""

    def __init__(self, results: Results) -> None:
        self.results = results

    def list(self) -> list[Decision]:
        security = [r for r in self.results.results if r.type == RuleType.SECURITY]
        pending = [
            Decision(subject=_where(r), problem="unsure: the user must decide")
            for r in security
            if r.status == Status.UNSURE
        ]
        pending += [
            Decision(
                subject=_where(r), problem="confirmed: the user fixes or accepts it"
            )
            for r in security
            if r.status == Status.CONFIRMED and not _is_accepted(self.results, r)
        ]
        return pending


def _where(result: Result) -> str:
    place = f"{result.path}:{result.line}" if result.path else "the skill"
    return f"{result.rule_id} {place}"


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
        pending = PendingDecisions(self.results).list()
        file_tasks = [t for t in self.results.tasks if t.scope == Scope.FILE]
        today = datetime.datetime.now(datetime.UTC).date().isoformat()
        lines = [f"**{self.results.skill or 'Skill'}, review of {today}**", ""]
        lines.append(f"**{self._verdict(findings, pending)}**")
        if findings or unsure:
            lines += [
                "",
                "| # | Rule | Where | What it says | Why it matters | Fix | Accepted |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        for number, r in enumerate(findings + unsure, start=1):
            where = f"`{r.path}:{r.line}`" if r.path else "the skill"
            why = r.reason or r.message
            name = self.rules[r.rule_id].name + (
                " (unsure)" if r.status == Status.UNSURE else ""
            )
            accepted = "yes" if _is_accepted(self.results, r) else "no"
            lines.append(
                f'| {number} | {name} | {where} | "{_cell(r.quote)}" | {_cell(why)} | {_cell(r.fix)} | {accepted} |'
            )
        if pending:
            lines += ["", "**Waiting for your decision**", ""]
            lines += [f"- {item.subject}: {item.problem}" for item in pending]
        if dismissed:
            lines += [
                "",
                "**False alarms, dismissed by the code, agent, and reviewer lenses**",
                "",
            ]
            lines += [
                f"- `{r.path}:{r.line}` {r.rule_id}: {_cell(r.reason)}"
                for r in dismissed
            ]
        lines += [
            "",
            "**What was checked**",
            f"- Code checks: {len(self.results.rule_ids)} rules over the skill's files.",
            f"- Line-by-line reading: {len(file_tasks)} files, {sum(t.lines_read for t in file_tasks)} lines.",
            f"- Warnings judged: {len(warnings)} ({len([w for w in warnings if w.status == Status.CONFIRMED])} findings, {len(dismissed)} false alarms dismissed).",
            f"- Findings the user accepted: {len(self.results.acceptances)}.",
            "",
            DISCLAIMER,
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _verdict(findings: list[Result], pending: list[Decision]) -> str:
        if pending:
            return (
                f"Warning: {_count(len(pending), 'finding')} to review. Fix each one, "
                "or accept it before you continue"
            )
        if findings:
            return f"The user accepted {_count(len(findings), 'finding')}"
        return "No findings in the checks below"


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" + ("" if number == 1 else "s")


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


def _verify_all(results: Results) -> list[VerifyIssue]:
    review_dir = Path(results.review_dir)
    issues = VerdictVerifier(results, _texts_from(review_dir)).verify()
    rules = [r for r in RuleLoader(RULES_DIR).load() if r.id in results.rule_ids]
    fresh = RuleEngine(
        rules, SkillView.from_source(SourceLoader(review_dir).load())
    ).run()
    return issues + CodeResultsGuard(results.results, fresh).verify()


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
            issues = _verify_all(results)
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
        case "pending":
            results = ResultsReader(out).read()
            pending = [
                Decision(
                    subject=i.task_or_result, problem="review incomplete: " + i.problem
                )
                for i in _verify_all(results)
            ]
            pending += PendingDecisions(results).list()
            for item in pending:
                logger.info("DECIDE %s: %s", item.subject, item.problem)
            logger.info("%d findings waiting for the user's decision", len(pending))
            return EXIT_INCOMPLETE if pending else EXIT_OK
        case "accept":
            results = ResultsReader(out).read()
            if not 0 <= args.result < len(results.results):
                raise InputError(f"no result {args.result} in {out / RESULTS_FILE}")
            finding = results.results[args.result]
            if finding.status != Status.CONFIRMED:
                raise InputError(
                    f"result {args.result} is {finding.status}, not confirmed"
                )
            acceptance = Acceptance(
                rule_id=finding.rule_id,
                path=finding.path,
                line=finding.line,
                quote=finding.quote,
                date=datetime.datetime.now(datetime.UTC).date(),
            )
            kept = [a for a in results.acceptances if not _accepts(a, finding)]
            ResultsWriter(out).write(
                results.model_copy(update={"acceptances": kept + [acceptance]})
            )
            logger.info(
                "Accepted result %d (%s %s)", args.result, finding.rule_id, finding.path
            )
            return EXIT_OK
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
        ("verify", "Check the verdicts, quotes, and three-lens dismissals."),
        ("report", "Print the report."),
        ("pending", "List the findings waiting for the user to fix or accept."),
    ):
        commands.add_parser(name, help=text).add_argument("--out", required=True)
    accept = commands.add_parser(
        "accept", help="Record that the user accepted one confirmed finding."
    )
    accept.add_argument("--out", required=True)
    accept.add_argument(
        "--result",
        type=int,
        required=True,
        help="The finding's index in results.json's results list.",
    )
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
