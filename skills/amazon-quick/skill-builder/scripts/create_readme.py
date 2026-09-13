"""
description: Scaffold a skill's README.md with a standard-conforming frontmatter header (description, last_updated, and exactly one of source_url or origin) and the section skeleton the Quick Skills Standard expects (Overview, Pre-requisites, Installation, Getting started). Run as: python create_readme.py <skill_dir> --description "..." (--source-url "..." | --origin original).
last_updated: 2026-09-13
origin: original

Single self-contained file. ReadmeRenderer turns an injected spec into the file
text (pure, unit-tested); ReadmeGenerator writes it to the skill root (I/O
facade); main() builds the spec from CLI arguments.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import date
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


@dataclass(frozen=True)
class ReadmeSpec:
    """The values a README needs, collected before generation."""

    name: str
    description: str
    source_url: str | None
    origin: str | None


class ReadmeRenderer:
    """Renders a compliant README.md from a spec (pure)."""

    def __init__(self, spec: ReadmeSpec) -> None:
        self.spec = spec

    def render(self) -> str:
        """Return the full text of the new README."""
        spec = self.spec
        provenance = (
            f"source_url: {spec.source_url}"
            if spec.source_url
            else f"origin: {spec.origin}"
        )
        return (
            "---\n"
            f'description: "{spec.description}"\n'
            f"last_updated: {date.today().isoformat()}\n"
            f"{provenance}\n"
            "---\n\n"
            f"# {spec.name}\n\n"
            f"{spec.description}\n\n"
            "## Overview\n\n"
            "What problem this skill solves, who it is for, and how it extends Amazon Quick.\n\n"
            "## Pre-requisites\n\n"
            "List each dependency (type, which connector, runtime, required or optional), "
            "or state that the skill uses only built-in tools.\n\n"
            "## Installation\n\n"
            "1. Download the skill and add it in Customize > Skills.\n"
            "2. Install and enable any connectors listed above.\n\n"
            "## Getting started\n\n"
            "Start with the help menu by saying: `<prefix> help`.\n"
        )


class ReadmeGenerator:
    """Facade: render a README from a spec and write it to the skill root (I/O)."""

    def __init__(self, skill_dir: Path, spec: ReadmeSpec) -> None:
        self.skill_dir = skill_dir
        self.spec = spec

    def generate(self) -> Path:
        """Write README.md to the skill root and return its path."""
        target = self.skill_dir / "references" / "README.md"
        target.write_text(
            ReadmeRenderer(self.spec).render(), encoding="utf-8", newline="\n"
        )
        return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a compliant skill README.md."
    )
    parser.add_argument(
        "skill_dir", help="Path to the skill directory (README.md is written here)."
    )
    parser.add_argument(
        "--description", required=True, help="What capability the skill adds."
    )
    provenance = parser.add_mutually_exclusive_group(required=True)
    provenance.add_argument(
        "--source-url", help="URL the file is derived from (derived files)."
    )
    provenance.add_argument(
        "--origin", choices=["original"], help="Mark internal-authored content."
    )
    args = parser.parse_args(argv)

    skill_dir = Path(args.skill_dir)
    if not skill_dir.is_dir():
        logger.error("Not a directory: %s", skill_dir)
        return 2

    logger.info("Generating README.md in %s", skill_dir)
    spec = ReadmeSpec(
        name=skill_dir.name,
        description=args.description,
        source_url=args.source_url,
        origin=args.origin,
    )
    target = ReadmeGenerator(skill_dir, spec).generate()
    logger.info("Wrote %s", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
