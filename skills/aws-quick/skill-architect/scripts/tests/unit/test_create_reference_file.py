"""
description: Unit tests for create_reference_file.py. Filesystem-free: ReferenceRenderer is given an injected spec, so the generated Markdown text is verified without writing any file.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from create_reference_file import ReferenceFileSpec, ReferenceRenderer


def _spec(
    source_url: str | None = None, origin: str | None = "original"
) -> ReferenceFileSpec:
    return ReferenceFileSpec(
        name="my-ref",
        description="A reference.",
        source_url=source_url,
        origin=origin,
    )


class TestReferenceRenderer(unittest.TestCase):
    def test_frontmatter_fields_present(self) -> None:
        text = ReferenceRenderer(_spec()).render()
        self.assertTrue(text.startswith("---\n"))
        self.assertIn('description: "A reference."', text)
        self.assertIn("last_updated:", text)
        self.assertIn("origin: original", text)

    def test_title_derived_from_name(self) -> None:
        self.assertIn("# My Ref", ReferenceRenderer(_spec()).render())

    def test_source_url_provenance(self) -> None:
        text = ReferenceRenderer(
            _spec(source_url="https://example.com", origin=None)
        ).render()
        self.assertIn("source_url: https://example.com", text)


if __name__ == "__main__":
    unittest.main()
