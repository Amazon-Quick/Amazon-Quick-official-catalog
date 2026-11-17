"""
description: Unit tests for create_script.py. Filesystem-free: ScriptRenderer is given an injected spec, so the generated script text is verified without writing any file.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from create_script import ScriptRenderer, ScriptSpec


def _spec(source_url: str | None = None, origin: str | None = "original") -> ScriptSpec:
    return ScriptSpec(
        file_name="do_thing",
        description="Do the thing.",
        class_name="ThingDoer",
        method_name="do",
        source_url=source_url,
        origin=origin,
    )


class TestScriptRenderer(unittest.TestCase):
    def test_header_fields_present(self) -> None:
        text = ScriptRenderer(_spec()).render()
        self.assertIn("description: Do the thing.", text)
        self.assertIn("last_updated:", text)
        self.assertIn("origin: original", text)

    def test_class_and_method_rendered(self) -> None:
        text = ScriptRenderer(_spec()).render()
        self.assertIn("class ThingDoer:", text)
        self.assertIn("def do(self)", text)

    def test_source_url_provenance_excludes_origin(self) -> None:
        text = ScriptRenderer(
            _spec(source_url="https://example.com", origin=None)
        ).render()
        self.assertIn("source_url: https://example.com", text)
        self.assertNotIn("origin:", text)


if __name__ == "__main__":
    unittest.main()
