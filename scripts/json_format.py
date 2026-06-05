"""JSON formatter for the Amazon Quick Official Marketplace.

Validates and formats JSON files with consistent indentation and trailing newlines.
Follows the same runner pattern as the build system.

Run with: uv run python -m scripts.json_format --check
"""

import json
import sys
from enum import StrEnum
from pathlib import Path

import click
from loguru import logger
from pydantic import BaseModel

EXCLUDE_DIRS = {".venv", "node_modules", "site", ".git", ".kiro"}
INDENT = 2


class FormatStatus(StrEnum):
    """Status of a JSON format operation."""

    FORMATTED = "FORMATTED"
    UNFORMATTED = "UNFORMATTED"
    ERROR = "ERROR"


class FileResult(BaseModel):
    """Result of formatting a single file."""

    path: str
    status: FormatStatus


class FormatRequest(BaseModel):
    """Configuration for a JSON format run."""

    check: bool = False


class FormatResponse(BaseModel):
    """Result of the JSON format run."""

    results: list[FileResult]
    success: bool


class JsonFormatter:
    """Formats JSON files with consistent indentation and trailing newlines."""

    def run(self, request: FormatRequest) -> FormatResponse:
        """Execute JSON formatting and return the result."""
        files = self._find_files()
        results: list[FileResult] = []

        for path in files:
            result = self._process_file(path, check=request.check)
            results.append(result)

            match result.status:
                case FormatStatus.UNFORMATTED if request.check:
                    logger.warning(f"Would reformat: {result.path}")
                case FormatStatus.UNFORMATTED:
                    logger.info(f"Reformatted: {result.path}")
                case FormatStatus.ERROR:
                    logger.error(f"Invalid JSON: {result.path}")

        success = all(r.status != FormatStatus.ERROR for r in results)
        if request.check:
            success = all(r.status == FormatStatus.FORMATTED for r in results)

        return FormatResponse(results=results, success=success)

    def _find_files(self) -> list[Path]:
        """Find all JSON files in the project, excluding build artifacts."""
        return sorted(
            path
            for path in Path(".").rglob("*.json")
            if not any(part in EXCLUDE_DIRS for part in path.parts)
        )

    def _process_file(self, path: Path, *, check: bool) -> FileResult:
        """Process a single JSON file."""
        try:
            content = path.read_text()
            parsed = json.loads(content)
            expected = json.dumps(parsed, indent=INDENT) + "\n"

            if content == expected:
                return FileResult(path=str(path), status=FormatStatus.FORMATTED)

            if not check:
                path.write_text(expected)

            return FileResult(path=str(path), status=FormatStatus.UNFORMATTED)
        except (json.JSONDecodeError, OSError):
            return FileResult(path=str(path), status=FormatStatus.ERROR)


@click.command()
@click.option("--check", is_flag=True, help="Check without modifying files.")
def main(check: bool) -> None:
    """Format or check JSON files."""
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    formatter = JsonFormatter()
    response = formatter.run(FormatRequest(check=check))

    if response.success:
        logger.success("All JSON files are formatted.")
        sys.exit(0)
    else:
        logger.error("JSON formatting issues found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
