"""
description: Unit tests for create_readme.py. Filesystem-free: ReadmeRenderer is given an injected spec, so the generated README text is verified without writing any file.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from create_readme import ReadmeRenderer, ReadmeSpec


def _spec(source_url: str | None = None, origin: str | None = "original") -> ReadmeSpec:
    return ReadmeSpec(
        name="my-skill",
        description="Adds X.",
        source_url=source_url,
        origin=origin,
    )


class TestReadmeRenderer(unittest.TestCase):
    def test_frontmatter_and_title(self) -> None:
        text = ReadmeRenderer(_spec()).render()
        self.assertTrue(text.startswith("---\n"))
        self.assertIn('description: "Adds X."', text)
        self.assertIn("origin: original", text)
        self.assertIn("# my-skill", text)

    def test_has_standard_sections(self) -> None:
        text = ReadmeRenderer(_spec()).render()
        for section in (
            "## Overview",
            "## Pre-requisites",
            "## Installation",
            "## Getting started",
        ):
            self.assertIn(section, text)

    def test_source_url_provenance(self) -> None:
        text = ReadmeRenderer(
            _spec(source_url="https://example.com", origin=None)
        ).render()
        self.assertIn("source_url: https://example.com", text)


if __name__ == "__main__":
    unittest.main()
