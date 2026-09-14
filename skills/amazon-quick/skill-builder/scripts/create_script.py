"""
description: Scaffold a new scripts/*.py file with a standard-conforming header (description, last_updated, and exactly one of source_url or origin) and a one-public-method class plus main()/argparse skeleton, so a new script starts compliant with the Python sandbox code standard. Run as: python create_script.py scripts <file_name> --description "..." --class-name "..." --method-name "..." (--source-url "..." | --origin original).
last_updated: 2026-09-13
origin: original

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
class ScriptSpec:
    """The values a new script needs, collected before generation."""

    file_name: str
    description: str
    class_name: str
    method_name: str
    source_url: str | None
    origin: str | None


class ScriptRenderer:
    """Renders a standard-conforming scripts/*.py file from a spec (pure)."""

    def __init__(self, spec: ScriptSpec) -> None:
        self.spec = spec

    def render(self) -> str:
        """Return the full text of the new script."""
        spec = self.spec
        provenance = (
            f"source_url: {spec.source_url}"
            if spec.source_url
            else f"origin: {spec.origin}"
        )
        return f'''"""
description: {spec.description}
last_updated: {date.today().isoformat()}
{provenance}
"""

from __future__ import annotations

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


class {spec.class_name}:
    """One-line statement of what this class does."""

    def __init__(self, target: Path) -> None:
        self.target = target

    def {spec.method_name}(self) -> int:
        """Do the one thing this class is responsible for."""
        raise NotImplementedError


def main() -> int:
    parser = argparse.ArgumentParser(description="{spec.description}")
    parser.add_argument("target", help="Path this script operates on.")
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        logger.error("Not found: %s", target)
        return 2

    return {spec.class_name}(target).{spec.method_name}()


if __name__ == "__main__":
    sys.exit(main())
'''


class ScriptGenerator:
    """Facade: render a script from a spec and write it to scripts/ (I/O)."""

    def __init__(self, scripts_dir: Path, spec: ScriptSpec) -> None:
        self.scripts_dir = scripts_dir
        self.spec = spec

    def generate(self) -> Path:
        """Write the script file and return its path."""
        target = self.scripts_dir / f"{self.spec.file_name}.py"
        target.write_text(
            ScriptRenderer(self.spec).render(), encoding="utf-8", newline="\n"
        )
        return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a standard-conforming scripts/*.py file."
    )
    parser.add_argument("scripts_dir", help="Path to the skill's scripts/ directory.")
    parser.add_argument("file_name", help="Script file name without the .py extension.")
    parser.add_argument("--description", required=True, help="What the script does.")
    parser.add_argument(
        "--class-name", required=True, help="Class name, e.g. SkillManifest."
    )
    parser.add_argument(
        "--method-name", required=True, help="Public method name, e.g. collect."
    )
    provenance = parser.add_mutually_exclusive_group(required=True)
    provenance.add_argument(
        "--source-url", help="URL the script is derived from (derived files)."
    )
    provenance.add_argument(
        "--origin", choices=["original"], help="Mark internal-authored content."
    )
    args = parser.parse_args(argv)

    scripts_dir = Path(args.scripts_dir)
    if not scripts_dir.is_dir():
        logger.error("Not a directory: %s", scripts_dir)
        return 2

    logger.info("Generating script %s in %s", args.file_name, scripts_dir)
    spec = ScriptSpec(
        file_name=args.file_name,
        description=args.description,
        class_name=args.class_name,
        method_name=args.method_name,
        source_url=args.source_url,
        origin=args.origin,
    )
    target = ScriptGenerator(scripts_dir, spec).generate()
    logger.info("Wrote %s", target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
