"""
description: Scaffold a new references/*.md file with a standard-conforming frontmatter header (description, last_updated, and optional sources) plus a purpose skeleton, so a new reference file starts compliant with the reference-file header standard.
last_updated: 2026-11-18

Usage:
    python create_reference_file.py references <name> --description "..." [--source URL ...]
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
class ReferenceFileSpec:
    """The values a reference file needs, collected before generation."""

    name: str
    description: str
    sources: tuple[str, ...] = ()


class ReferenceRenderer:
    """Renders a compliant references/*.md file from a spec (pure)."""

    def __init__(self, spec: ReferenceFileSpec) -> None:
        self.spec = spec

    def render(self) -> str:
        """Return the full text of the new reference file."""
        spec = self.spec
        sources = (
            "sources:\n" + "".join(f"  - {url}\n" for url in spec.sources)
            if spec.sources
            else ""
        )
        title = spec.name.replace("-", " ").replace("_", " ").title()
        return (
            "---\n"
            f'description: "{spec.description}"\n'
            f"last_updated: {date.today().isoformat()}\n"
            f"{sources}"
            "---\n\n"
            f"# {title}\n\n"
            "<purpose>\n"
            "Explain why this file exists and what the skill uses it for.\n"
            "</purpose>\n"
        )


class ReferenceFileGenerator:
    """Facade: render a reference file from a spec and write it (I/O)."""

    def __init__(self, references_dir: Path, spec: ReferenceFileSpec) -> None:
        self.references_dir = references_dir
        self.spec = spec

    def generate(self) -> Path:
        """Write the reference file and return its path."""
        target = self.references_dir / f"{self.spec.name}.md"
        target.write_text(
            ReferenceRenderer(self.spec).render(), encoding="utf-8", newline="\n"
        )
        return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a compliant references/*.md file."
    )
    parser.add_argument(
        "references_dir", help="Path to the skill's references/ directory."
    )
    parser.add_argument("name", help="File name without the .md extension.")
    parser.add_argument(
        "--description", required=True, help="What the file contains and why."
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="A URL the file's content comes from. Repeat for each page.",
    )
    args = parser.parse_args(argv)

    references_dir = Path(args.references_dir)
    if not references_dir.is_dir():
        logger.error("Not a directory: %s", references_dir)
        return 2

    logger.info("Generating reference file %s in %s", args.name, references_dir)
    spec = ReferenceFileSpec(
        name=args.name,
        description=args.description,
        sources=tuple(args.source),
    )
    target = ReferenceFileGenerator(references_dir, spec).generate()
    logger.info("Wrote %s", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
