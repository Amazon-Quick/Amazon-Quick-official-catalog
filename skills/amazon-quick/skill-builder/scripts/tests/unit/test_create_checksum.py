"""
description: Unit tests for create_checksum.py. Dependency-injected and filesystem-free: the pure classes receive their inputs directly, so the digest and the frontmatter rendering are verified without reading or writing any file.
last_updated: 2026-09-13
origin: original

Run from the skill root (scripts/ on the path, no in-code sys.path edits):
    PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from create_checksum import ChecksumRenderer, ManifestDigest


class TestManifestDigest(unittest.TestCase):
    def test_digest_is_order_independent(self) -> None:
        first = ManifestDigest({"a.md": b"one", "b.md": b"two"}).compute()
        second = ManifestDigest({"b.md": b"two", "a.md": b"one"}).compute()
        self.assertEqual(first, second)

    def test_digest_changes_with_content(self) -> None:
        base = ManifestDigest({"a.md": b"one"}).compute()
        changed = ManifestDigest({"a.md": b"two"}).compute()
        self.assertNotEqual(base, changed)

    def test_digest_has_sha256_prefix(self) -> None:
        self.assertTrue(
            ManifestDigest({"a.md": b"one"}).compute().startswith("sha256:")
        )


class TestChecksumRenderer(unittest.TestCase):
    def test_inserts_when_absent(self) -> None:
        rendered = ChecksumRenderer(
            "---\nname: demo\n---\nbody\n", "sha256:abc"
        ).render()
        self.assertIn('checksum: "sha256:abc"', rendered)

    def test_replaces_when_present(self) -> None:
        text = '---\nname: demo\nchecksum: "sha256:old"\n---\nbody\n'
        rendered = ChecksumRenderer(text, "sha256:new").render()
        self.assertIn('checksum: "sha256:new"', rendered)
        self.assertNotIn("sha256:old", rendered)

    def test_is_idempotent(self) -> None:
        once = ChecksumRenderer("---\nname: demo\n---\nbody\n", "sha256:abc").render()
        twice = ChecksumRenderer(once, "sha256:abc").render()
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
