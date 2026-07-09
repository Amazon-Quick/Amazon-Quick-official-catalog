"""Skill security scan for the Amazon Quick Official Catalog.

Runs the Cisco AI skill-scanner against the published surface of every skill.
Evaluation fixtures under ``evals/`` are stripped from a temporary staging copy
before scanning, mirroring the release (see ``.releaseignore`` ``**/evals/``).

Those fixtures are binary test documents (PDF, DOCX) that never ship. Scanning
them does not improve safety coverage; it only lowers the scanner's
analyzability score and raises false ``LOW_ANALYZABILITY`` HIGH findings for
skills that legitimately carry document fixtures. Scanning the release-equivalent
tree keeps every shipped file under scrutiny while excluding unpublished fixtures.

Run with: uv run python -m scripts.skill_security
"""

import shutil
import subprocess
import sys
import tempfile
from enum import StrEnum
from pathlib import Path

from loguru import logger
from pydantic import BaseModel

STRIPPED_SUBDIRS = {"evals"}
POLICY_FILE = "skill-scanner-policy.yaml"
FAIL_ON_SEVERITY = "high"


class ScanStatus(StrEnum):
    """Status of the skill security scan."""

    PASSED = "PASSED"
    FAILED = "FAILED"


class ScanResponse(BaseModel):
    """Result of the skill security scan run."""

    status: ScanStatus
    return_code: int


class SkillSecurityScanner:
    """Stages the published skill surface and runs the skill-scanner on it."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.skills_dir = project_dir / "skills"
        self.policy_path = project_dir / POLICY_FILE

    def run(self) -> ScanResponse:
        """Stage skills without eval fixtures, then scan the staged tree."""
        staging_root = Path(tempfile.mkdtemp(prefix="skill-security-"))
        try:
            staged_skills = staging_root / "skills"
            self._stage_skills(staged_skills)
            return_code = self._scan(staged_skills)
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

        match return_code:
            case 0:
                status = ScanStatus.PASSED
            case _:
                status = ScanStatus.FAILED

        return ScanResponse(status=status, return_code=return_code)

    def _stage_skills(self, destination: Path) -> None:
        """Copy skills/ into destination, dropping stripped sub-directories."""
        shutil.copytree(
            self.skills_dir,
            destination,
            ignore=self._ignore_stripped_subdirs,
        )

    def _ignore_stripped_subdirs(self, directory: str, contents: list[str]) -> set[str]:
        """Return sub-directory names to skip during staging (e.g. evals)."""
        base = Path(directory)
        return {
            name
            for name in contents
            if name in STRIPPED_SUBDIRS and (base / name).is_dir()
        }

    def _scan(self, staged_skills: Path) -> int:
        """Invoke the skill-scanner against the staged skills tree."""
        command = [
            "skill-scanner",
            "scan-all",
            str(staged_skills),
            "--use-behavioral",
            "--fail-on-severity",
            FAIL_ON_SEVERITY,
            "--lenient",
            "--policy",
            str(self.policy_path),
        ]
        process = subprocess.run(command)  # nosec B603
        return process.returncode


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    project_dir = Path(__file__).resolve().parent.parent
    scanner = SkillSecurityScanner(project_dir)
    response = scanner.run()

    match response.status:
        case ScanStatus.PASSED:
            logger.success("Skill security scan passed (published surface).")
            sys.exit(0)
        case ScanStatus.FAILED:
            logger.error("Skill security scan found blocking findings.")
            sys.exit(response.return_code or 1)
