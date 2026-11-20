"""
description: Scaffold a skill's assets/README.md: the header, a one-line summary, the Pre-requisites table of dependencies (name, type, required), and the Installation and Getting started sections. It never overwrites an existing README.
last_updated: 2026-11-20

Usage:
    python create_readme.py <skill_dir> --title "..." --summary "..." --prefix <prefix> [--dependency "Name|TYPE|Y|URL" ...]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
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

SKILLS_DOC_URL = (
    "https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html"
)
DEPENDENCY_FIELD_SEPARATOR = "|"
DEPENDENCY_FIELD_COUNT = 4
CONNECTOR_TYPES_PATH = (
    Path(__file__).resolve().parents[1] / "references" / "connector-types.json"
)


class DependencyType(StrEnum):
    """The README Type values other than a built-in connector's ConnectorType value."""

    SPACE = "SPACE"
    DATASET = "DATASET"
    TOPIC = "TOPIC"
    DASHBOARD = "DASHBOARD"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    CLOUD_CONNECTOR_CUSTOM_MCP = "CLOUD_CONNECTOR_CUSTOM_MCP"
    CLOUD_CONNECTOR_CUSTOM_OPENAPI = "CLOUD_CONNECTOR_CUSTOM_OPENAPI"
    LOCAL_CONNECTOR_MCP_LOCAL = "LOCAL_CONNECTOR_MCP_LOCAL"
    LOCAL_CONNECTOR_MCP_REMOTE = "LOCAL_CONNECTOR_MCP_REMOTE"
    LOCAL_CONNECTOR_ACP = "LOCAL_CONNECTOR_ACP"
    SYSTEM_TOOL = "SYSTEM_TOOL"
    SKILL = "SKILL"


class Required(StrEnum):
    """Whether the skill stops without the dependency."""

    YES = "Y"
    NO = "N"


@dataclass(frozen=True)
class Dependency:
    """One row of the Pre-requisites table."""

    name: str
    kind: str
    required: Required
    link: str


@dataclass(frozen=True)
class ReadmeSpec:
    """The values a README needs, collected before generation."""

    skill_name: str
    title: str
    summary: str
    prefix: str
    dependencies: tuple[Dependency, ...] = ()


class ConnectorTypeCatalog:
    """Loads the built-in connector types from references/connector-types.json (I/O)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> frozenset[str]:
        """Return every ConnectorType value the file lists."""
        catalog = json.loads(self.path.read_text(encoding="utf-8"))
        return frozenset(entry["type"] for entry in catalog["connector_types"])


class DependencyParser:
    """Parses one --dependency value, "Name|TYPE|Y|URL", into a Dependency (pure)."""

    def __init__(self, raw: str, connector_types: frozenset[str]) -> None:
        self.raw = raw
        self.connector_types = connector_types

    def parse(self) -> Dependency:
        """Return the Dependency, or raise ValueError naming the bad field."""
        fields = [f.strip() for f in self.raw.split(DEPENDENCY_FIELD_SEPARATOR)]
        if len(fields) != DEPENDENCY_FIELD_COUNT:
            raise ValueError(f"expected Name|TYPE|Y|URL, got {self.raw!r}")
        name, kind, required, link = fields
        if kind not in DependencyType.__members__ and kind not in self.connector_types:
            raise ValueError(
                f"unknown Type {kind!r}: use a type from references/dependencies.md"
                " or a ConnectorType value from references/connector-types.json"
            )
        return Dependency(
            name=name,
            kind=kind,
            required=Required(required),
            link=link,
        )


class ReadmeRenderer:
    """Renders a README from a spec (pure)."""

    def __init__(self, spec: ReadmeSpec) -> None:
        self.spec = spec

    def render(self) -> str:
        """Return the full text of the new README."""
        spec = self.spec
        install = "Install the skill in AWS Quick"
        if spec.dependencies:
            install += ", then set up each dependency above"
        return (
            "---\n"
            f'description: "What {spec.skill_name} needs, how to install it, and how to start."\n'
            f"last_updated: {date.today().isoformat()}\n"
            "---\n\n"
            f"# {spec.title}\n\n"
            f"{spec.summary}\n\n"
            "## Pre-requisites\n\n"
            f"{self._prerequisites()}\n\n"
            "## Installation\n\n"
            f"{install}. See [Skills in AWS Quick]({SKILLS_DOC_URL}).\n\n"
            "## Getting started\n\n"
            f"Enter `{spec.prefix} help` to see its commands.\n"
        )

    def _prerequisites(self) -> str:
        if not self.spec.dependencies:
            return "None."
        rows = [
            f"| [{d.name}]({d.link}) | {d.kind} | {d.required.value} |"
            for d in self.spec.dependencies
        ]
        return "\n".join(
            [
                "The first step checks each dependency and stops when a required one is missing.",
                "",
                "| Name | Type | Required |",
                "| --- | --- | --- |",
                *rows,
            ]
        )


class ReadmeGenerator:
    """Facade: render a README from a spec and write it to assets/ (I/O)."""

    def __init__(self, skill_dir: Path, spec: ReadmeSpec) -> None:
        self.skill_dir = skill_dir
        self.spec = spec

    def generate(self) -> Path:
        """Write README.md to assets/ and return its path. Never overwrites a README."""
        assets_dir = self.skill_dir / "assets"
        target = assets_dir / "README.md"
        if target.exists():
            raise FileExistsError(f"{target} already exists; edit it instead")
        assets_dir.mkdir(exist_ok=True)
        target.write_text(
            ReadmeRenderer(self.spec).render(), encoding="utf-8", newline="\n"
        )
        return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a skill's assets/README.md.")
    parser.add_argument("skill_dir", help="Path to the skill directory.")
    parser.add_argument("--title", required=True, help="The skill's display name.")
    parser.add_argument(
        "--summary", required=True, help="One line: what the skill does."
    )
    parser.add_argument(
        "--prefix", required=True, help="The help command prefix, e.g. sa."
    )
    parser.add_argument(
        "--dependency",
        action="append",
        default=[],
        help='One dependency as "Name|TYPE|Y|URL". Repeat for each.',
    )
    args = parser.parse_args(argv)

    skill_dir = Path(args.skill_dir)
    if not skill_dir.is_dir():
        logger.error("Not a directory: %s", skill_dir)
        return 2
    connector_types = ConnectorTypeCatalog(CONNECTOR_TYPES_PATH).load()
    try:
        dependencies = tuple(
            DependencyParser(raw, connector_types).parse() for raw in args.dependency
        )
    except ValueError as e:
        logger.error("Bad --dependency: %s", e)
        return 2

    logger.info("Generating README.md in %s", skill_dir)
    spec = ReadmeSpec(
        skill_name=skill_dir.resolve().name,
        title=args.title,
        summary=args.summary,
        prefix=args.prefix,
        dependencies=dependencies,
    )
    try:
        target = ReadmeGenerator(skill_dir, spec).generate()
    except FileExistsError as e:
        logger.error("%s", e)
        return 2
    logger.info("Wrote %s", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
