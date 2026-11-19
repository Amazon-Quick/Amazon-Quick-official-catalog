"""
description: Unit tests for create_reference_file.py. Filesystem-free: ReferenceRenderer is given an injected spec, so the generated Markdown text is verified without writing any file.
last_updated: 2026-11-18

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from create_reference_file import ReferenceFileSpec, ReferenceRenderer


def _spec(sources: tuple[str, ...] = ()) -> ReferenceFileSpec:
    return ReferenceFileSpec(name="my-ref", description="A reference.", sources=sources)


class TestReferenceRenderer(unittest.TestCase):
    def test_frontmatter_fields_present(self) -> None:
        text = ReferenceRenderer(_spec()).render()
        self.assertTrue(text.startswith("---\n"))
        self.assertIn('description: "A reference."', text)
        self.assertIn("last_updated:", text)

    def test_header_without_sources_omits_the_field(self) -> None:
        self.assertNotIn("sources:", ReferenceRenderer(_spec()).render())

    def test_sources_render_as_a_list(self) -> None:
        text = ReferenceRenderer(_spec(("https://a.example",))).render()
        self.assertIn("sources:\n  - https://a.example\n---", text)

    def test_title_derived_from_name(self) -> None:
        self.assertIn("# My Ref", ReferenceRenderer(_spec()).render())


if __name__ == "__main__":
    unittest.main()
