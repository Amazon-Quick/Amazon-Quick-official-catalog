"""
description: Scaffold a new references/*.md file with a standard-conforming frontmatter header (description, last_updated, and exactly one of source_url or origin) plus a purpose skeleton, so a new reference file starts compliant with the reference-file header standard. Run as: python create_reference_file.py references <name> --description "..." (--source-url "..." | --origin original).
last_updated: 2026-09-13
origin: original

Single self-contained file. ReferenceRenderer turns an injected spec into the
file text (pure, unit-tested); ReferenceFileGenerator writes it (I/O facade);
main() builds the spec from CLI arguments.
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
    source_url: str | None
    origin: str | None


class ReferenceRenderer:
    """Renders a compliant references/*.md file from a spec (pure)."""

    def __init__(self, spec: ReferenceFileSpec) -> None:
        self.spec = spec

    def render(self) -> str:
        """Return the full text of the new reference file."""
        spec = self.spec
        provenance = (
            f"source_url: {spec.source_url}"
            if spec.source_url
            else f"origin: {spec.origin}"
        )
        title = spec.name.replace("-", " ").replace("_", " ").title()
        return (
            "---\n"
            f'description: "{spec.description}"\n'
            f"last_updated: {date.today().isoformat()}\n"
            f"{provenance}\n"
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
    provenance = parser.add_mutually_exclusive_group(required=True)
    provenance.add_argument(
        "--source-url", help="URL the file is derived from (derived files)."
    )
    provenance.add_argument(
        "--origin", choices=["original"], help="Mark internal-authored content."
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
        source_url=args.source_url,
        origin=args.origin,
    )
    target = ReferenceFileGenerator(references_dir, spec).generate()
    logger.info("Wrote %s", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
