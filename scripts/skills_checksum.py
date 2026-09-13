"""Per-skill checksums for the Amazon Quick Official Catalog.

Computes a deterministic SHA-256 content digest for each skill and records it in
two places, plus a catalog-wide roll-up:

  - ``SKILL.md`` frontmatter: ``checksum: "sha256:<hex>"`` for every skill on
    disk, so the digest travels with the skill when it is installed on its own.
  - ``catalog.json``: a ``checksum`` field on each published skill asset, so a
    consumer can verify every shipped skill and see which one changed from the
    single catalog manifest.
  - ``catalog.json`` top-level ``skillsChecksum``: a roll-up hash over the
    published set (``path\\tchecksum`` lines), a one-line whole-catalog signal.

The per-skill algorithm matches the skill-builder skill's create_checksum.py
exactly, so a skill authored there produces the same digest the catalog expects:
files are keyed by POSIX relative path, each contributes a ``relpath\\tsha256``
line to a manifest, and the manifest is hashed. ``evals/``, ``tests/``, caches,
``.pyc``, and ``.DS_Store`` are excluded, mirroring the release surface
(.releaseignore ``**/evals/``); SKILL.md contributes its content with the
checksum line removed, so re-writing is idempotent.

The published set is defined by ``catalog.json`` (its skill assets), which
excludes internal, release-ignored skills such as catalog-skill-contributor.
Every skill on disk still receives a SKILL.md checksum for uniform
self-integrity; only published skills feed the catalog fields and the roll-up.

Written by the ``fix`` flow and verified by the build:

  - Write:  uv run python -m scripts.skills_checksum
  - Verify: uv run python -m scripts.skills_checksum --check

In ``--check`` mode every stored value is recomputed from disk and compared;
any mismatch, missing value, or catalog path that does not resolve on disk fails
the build, so a skill change that was not accompanied by a checksum
regeneration is caught in CI.
"""

import hashlib
import json
import re
import sys
from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path

import click
from loguru import logger
from pydantic import BaseModel

CATALOG_FILE = "catalog.json"
SKILLS_DIR = "skills"
SKILL_FILE = "SKILL.md"
ROLLUP_KEY = "skillsChecksum"
ASSET_CHECKSUM_KEY = "checksum"
SKILL_ASSET_TYPE = "skill"
DIGEST_PREFIX = "sha256"
INDENT = 2

# Per-skill manifest surface — identical to skill-builder's create_checksum.py.
INCLUDE_ROOT_FILES = ("SKILL.md", "README.md")
INCLUDE_DIRS = ("scripts", "references", "assets")
EXCLUDE_DIR_NAMES = frozenset({"evals", "tests", "__pycache__", ".git"})
EXCLUDE_SUFFIXES = frozenset({".pyc"})
EXCLUDE_NAMES = frozenset({".DS_Store"})
TEST_FILE_RE = re.compile(r"^test_.*\.py$")

# The checksum line is stripped from SKILL.md before hashing so writing the
# digest back never changes the digest (idempotent). The strip consumes the
# trailing newline too, so a freshly-checksummed file hashes identically to a
# clean one -- stripping is the exact inverse of insertion.
CHECKSUM_STRIP_RE = re.compile(r"^checksum\s*:.*\n?", re.M)
# Line-only form (newline preserved) for detecting and replacing in place.
CHECKSUM_LINE_RE = re.compile(r"^checksum\s*:\s*.*$", re.M)
CHECKSUM_VALUE_RE = re.compile(r'^checksum\s*:\s*"?(sha256:[0-9a-f]{64})"?\s*$', re.M)


class SkillManifest:
    """Reads a skill directory into a {relpath: content} manifest (I/O)."""

    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir

    def collect(self) -> dict[str, bytes]:
        """Map each included file to its bytes, keyed by POSIX relative path."""
        manifest: dict[str, bytes] = {}
        for name in INCLUDE_ROOT_FILES:
            path = self.skill_dir / name
            if path.is_file():
                manifest[name] = self._content_for(name, path)
        for directory in INCLUDE_DIRS:
            base = self.skill_dir / directory
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if not self._is_included(path):
                    continue
                relpath = path.relative_to(self.skill_dir).as_posix()
                manifest[relpath] = self._content_for(relpath, path)
        return manifest

    def _content_for(self, relpath: str, path: Path) -> bytes:
        if relpath == SKILL_FILE:
            stripped = CHECKSUM_STRIP_RE.sub(
                "", path.read_text(encoding="utf-8"), count=1
            )
            return stripped.encode("utf-8")
        return path.read_bytes()

    def _is_included(self, path: Path) -> bool:
        if not path.is_file():
            return False
        parts = set(path.relative_to(self.skill_dir).parts)
        if parts & EXCLUDE_DIR_NAMES:
            return False
        if path.suffix in EXCLUDE_SUFFIXES or path.name in EXCLUDE_NAMES:
            return False
        return not TEST_FILE_RE.match(path.name)


class ManifestDigest:
    """Hashes a supplied manifest into a deterministic digest (pure)."""

    def __init__(self, manifest: dict[str, bytes]) -> None:
        self.manifest = manifest

    def compute(self) -> str:
        """Return the order-independent digest of the manifest."""
        lines = [
            f"{relpath}\t{hashlib.sha256(content).hexdigest()}"
            for relpath, content in sorted(self.manifest.items())
        ]
        body = "\n".join(lines).encode("utf-8")
        return f"{DIGEST_PREFIX}:{hashlib.sha256(body).hexdigest()}"


class ChecksumRenderer:
    """Inserts or replaces the checksum line in SKILL.md text (pure)."""

    def __init__(self, text: str, digest: str) -> None:
        self.text = text
        self.digest = digest

    def render(self) -> str:
        """Return SKILL.md text with checksum: "<digest>" set in frontmatter."""
        line = f'checksum: "{self.digest}"'
        if CHECKSUM_LINE_RE.search(self.text):
            return CHECKSUM_LINE_RE.sub(line, self.text, count=1)
        parts = self.text.split("---", 2)
        if len(parts) < 3:
            raise ValueError("SKILL.md has no frontmatter block")
        parts[1] = parts[1].rstrip("\n") + f"\n{line}\n"
        return "---".join(parts)


class ChecksumStatus(StrEnum):
    """Status of a checksum operation."""

    WRITTEN = "WRITTEN"
    MATCHED = "MATCHED"
    MISMATCHED = "MISMATCHED"


class ChecksumResponse(BaseModel):
    """Result of a checksum run.

    ``problems`` is empty on success; each entry is a human-readable drift or
    coverage issue found during ``--check``.
    """

    status: ChecksumStatus
    rollup: str
    problems: list[str] = []


class SkillsChecksumService:
    """Computes and persists per-skill checksums and the catalog roll-up."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.skills_dir = project_dir / SKILLS_DIR
        self.catalog_file = project_dir / CATALOG_FILE

    def write(self) -> ChecksumResponse:
        """Write per-skill checksums into every SKILL.md and catalog.json.

        Writes the SKILL.md frontmatter checksum for every skill on disk, the
        ``checksum`` field on every published catalog skill asset, and the
        top-level roll-up over the published set.
        """
        digests = self._compute_digests()

        for skill_dir in self._iter_skill_dirs():
            self._write_frontmatter(skill_dir, digests[self._skill_key(skill_dir)])

        catalog = self._load_catalog()
        published = self._published_digests(catalog, digests)
        for asset in self._skill_assets(catalog):
            digest = digests.get(asset["path"])
            if digest is not None:
                asset[ASSET_CHECKSUM_KEY] = digest
        rollup = self._roll_up(published)
        catalog[ROLLUP_KEY] = rollup
        self.catalog_file.write_text(json.dumps(catalog, indent=INDENT) + "\n")

        return ChecksumResponse(status=ChecksumStatus.WRITTEN, rollup=rollup)

    def check(self) -> ChecksumResponse:
        """Recompute every checksum from disk and compare to stored values."""
        digests = self._compute_digests()
        problems: list[str] = []

        for skill_dir in self._iter_skill_dirs():
            key = self._skill_key(skill_dir)
            stored = self._read_frontmatter_checksum(skill_dir)
            if stored != digests[key]:
                problems.append(
                    f"{key}: SKILL.md checksum {self._describe(stored)} "
                    f"!= computed {digests[key]}"
                )

        catalog = self._load_catalog()
        for asset in self._skill_assets(catalog):
            path = asset["path"]
            computed = digests.get(path)
            if computed is None:
                problems.append(f"{path}: catalog lists it but no skill on disk")
                continue
            stored = asset.get(ASSET_CHECKSUM_KEY)
            if stored != computed:
                problems.append(
                    f"{path}: catalog.json checksum {self._describe(stored)} "
                    f"!= computed {computed}"
                )

        expected_rollup = self._roll_up(self._published_digests(catalog, digests))
        stored_rollup = catalog.get(ROLLUP_KEY)
        if stored_rollup != expected_rollup:
            problems.append(
                f"{ROLLUP_KEY}: stored {self._describe(stored_rollup)} "
                f"!= computed {expected_rollup}"
            )

        status = ChecksumStatus.MATCHED if not problems else ChecksumStatus.MISMATCHED
        return ChecksumResponse(
            status=status, rollup=expected_rollup, problems=problems
        )

    def _compute_digests(self) -> dict[str, str]:
        """Map each on-disk skill's project-relative path to its digest."""
        return {
            self._skill_key(skill_dir): ManifestDigest(
                SkillManifest(skill_dir).collect()
            ).compute()
            for skill_dir in self._iter_skill_dirs()
        }

    def _published_digests(
        self, catalog: dict, digests: dict[str, str]
    ) -> dict[str, str]:
        """Digests for catalog skill assets that resolve on disk, keyed by path.

        Keying by path dedupes any repeated catalog entry, so the roll-up is
        stable even if a skill is mistakenly listed more than once.
        """
        return {
            asset["path"]: digests[asset["path"]]
            for asset in self._skill_assets(catalog)
            if asset["path"] in digests
        }

    def _roll_up(self, path_to_digest: dict[str, str]) -> str:
        """Return the roll-up digest over a path->digest map (pure)."""
        lines = [f"{path}\t{digest}" for path, digest in sorted(path_to_digest.items())]
        body = "\n".join(lines).encode("utf-8")
        return f"{DIGEST_PREFIX}:{hashlib.sha256(body).hexdigest()}"

    def _iter_skill_dirs(self) -> Iterator[Path]:
        """Yield every skill directory, supporting flat and categorized layouts.

        A directory directly under skills/ with a SKILL.md is a skill; otherwise
        it is treated as a category folder and its children are enumerated.
        """
        if not self.skills_dir.exists():
            return
        for entry in sorted(self.skills_dir.iterdir()):
            if not entry.is_dir():
                continue
            if (entry / SKILL_FILE).is_file():
                yield entry
            else:
                for child in sorted(entry.iterdir()):
                    if child.is_dir() and (child / SKILL_FILE).is_file():
                        yield child

    def _skill_key(self, skill_dir: Path) -> str:
        """Return the skill's project-relative POSIX path (catalog asset key)."""
        return skill_dir.relative_to(self.project_dir).as_posix()

    def _write_frontmatter(self, skill_dir: Path, digest: str) -> None:
        """Set the checksum line in a skill's SKILL.md frontmatter (idempotent)."""
        skill_md = skill_dir / SKILL_FILE
        rendered = ChecksumRenderer(
            skill_md.read_text(encoding="utf-8"), digest
        ).render()
        skill_md.write_text(rendered, encoding="utf-8", newline="\n")

    def _read_frontmatter_checksum(self, skill_dir: Path) -> str | None:
        """Return the checksum stored in a skill's SKILL.md, or None."""
        text = (skill_dir / SKILL_FILE).read_text(encoding="utf-8")
        match = CHECKSUM_VALUE_RE.search(text)
        return match.group(1) if match else None

    def _skill_assets(self, catalog: dict) -> Iterator[dict]:
        """Yield every skill-type asset entry across all catalog categories."""
        for category in catalog.get("categories", []):
            for asset in category.get("assets", []):
                if asset.get("type") == SKILL_ASSET_TYPE:
                    yield asset

    @staticmethod
    def _describe(value: str | None) -> str:
        """Render a stored checksum for a message, naming absence explicitly."""
        return value if value else "MISSING"

    def _load_catalog(self) -> dict:
        """Load catalog.json as a dict."""
        return json.loads(self.catalog_file.read_text(encoding="utf-8"))


@click.command()
@click.option("--check", is_flag=True, help="Verify stored checksums without writing.")
def main(check: bool) -> None:
    """Write or verify the catalog's per-skill checksums and roll-up."""
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    service = SkillsChecksumService(Path(__file__).resolve().parent.parent)

    if not check:
        response = service.write()
        logger.success(f"Wrote per-skill checksums; {ROLLUP_KEY}: {response.rollup}")
        sys.exit(0)

    response = service.check()
    if response.status is ChecksumStatus.MATCHED:
        logger.success(f"All skill checksums match; {ROLLUP_KEY}: {response.rollup}")
        sys.exit(0)

    logger.error(
        f"Skill checksum drift ({len(response.problems)} issue(s)). "
        f"Run 'uv run python -m scripts.skills_checksum' to regenerate:"
    )
    for problem in response.problems:
        logger.error(f"  {problem}")
    sys.exit(1)


if __name__ == "__main__":
    main()
