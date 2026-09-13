"""
description: Compute a skill's deterministic SHA-256 content digest and write it into SKILL.md frontmatter as checksum: "sha256:<hex>", so the validator only verifies the field rather than recomputing it. Run as: python create_checksum.py <skill_dir>.
last_updated: 2026-09-13
origin: original

Owns the checksum end to end so no other script recomputes it: check_skill.py
only verifies that the frontmatter carries a well-formed checksum field. This is
a single self-contained file (the sandbox runs it alone); every class lives here
and it imports only the standard library.

The digest is deterministic and order-independent: files are sorted by POSIX
relative path and each contributes a tab-separated "relpath<TAB>sha256(bytes)"
line to a manifest, which is then hashed. SKILL.md contributes its content with
the checksum line removed, so writing the digest back is idempotent. evals/,
caches, and test files are excluded: they change independently of the shipped
skill. Runs identically on Windows and macOS (pathlib, POSIX keys, LF newlines).

Design: SkillManifest reads files (I/O); ManifestDigest hashes a supplied
manifest (pure); ChecksumRenderer inserts the digest into frontmatter text
(pure); ChecksumWriter is the facade that wires them and writes the file. The two
pure classes are unit-tested by test_create_checksum.py without touching disk.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sys
from pathlib import Path

INCLUDE_ROOT_FILES = ("SKILL.md", "README.md")
INCLUDE_DIRS = ("scripts", "references", "assets")
EXCLUDE_DIR_NAMES = frozenset({"evals", "tests", "__pycache__", ".git"})
EXCLUDE_SUFFIXES = frozenset({".pyc"})
EXCLUDE_NAMES = frozenset({".DS_Store"})
TEST_FILE_RE = re.compile(r"^test_.*\.py$")
CHECKSUM_LINE_RE = re.compile(r"^checksum\s*:\s*.*$", re.M)
SKILL_FILE = "SKILL.md"
DIGEST_PREFIX = "sha256"


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
            stripped = CHECKSUM_LINE_RE.sub(
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


class ChecksumWriter:
    """Facade: compute the skill's digest and write it into SKILL.md."""

    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir

    def write(self) -> str:
        """Compute the digest, store it in SKILL.md, and return it. Idempotent."""
        skill_md = self.skill_dir / SKILL_FILE
        digest = ManifestDigest(SkillManifest(self.skill_dir).collect()).compute()
        rendered = ChecksumRenderer(
            skill_md.read_text(encoding="utf-8"), digest
        ).render()
        skill_md.write_text(rendered, encoding="utf-8", newline="\n")
        return digest


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a skill's content checksum.")
    parser.add_argument("skill_dir", help="Path to the skill directory.")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    if not (skill_dir / SKILL_FILE).is_file():
        logger.error("No %s in %s", SKILL_FILE, skill_dir)
        return 2

    logger.info("Computing checksum for %s", skill_dir)
    digest = ChecksumWriter(skill_dir).write()
    logger.info("Wrote checksum %s to %s", digest, skill_dir / SKILL_FILE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
