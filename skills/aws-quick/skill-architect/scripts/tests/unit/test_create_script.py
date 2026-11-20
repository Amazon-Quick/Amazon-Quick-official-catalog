"""
description: Unit tests for create_script.py. Filesystem-free: ScriptRenderer is given an injected spec, so the generated script text is checked without writing any file.
last_updated: 2026-11-20

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import ast
import unittest

from create_script import ScriptRenderer, ScriptSpec


def _spec(sources: tuple[str, ...] = ()) -> ScriptSpec:
    return ScriptSpec(
        file_name="do_thing",
        description="Do the thing.",
        class_name="ThingDoer",
        method_name="do",
        sources=sources,
    )


class TestScriptRenderer(unittest.TestCase):
    def test_header_fields_present(self) -> None:
        text = ScriptRenderer(_spec()).render()
        self.assertIn("description: Do the thing.", text)
        self.assertIn("last_updated:", text)

    def test_header_without_sources_omits_the_field(self) -> None:
        self.assertNotIn("sources:", ScriptRenderer(_spec()).render())

    def test_sources_render_as_a_list(self) -> None:
        text = ScriptRenderer(
            _spec(("https://a.example", "https://b.example"))
        ).render()
        self.assertIn("sources:\n  - https://a.example\n  - https://b.example\n", text)

    def test_class_and_method_rendered(self) -> None:
        text = ScriptRenderer(_spec()).render()
        self.assertIn("class ThingDoer:", text)
        self.assertIn("def do(self)", text)

    def test_main_accepts_argv(self) -> None:
        text = ScriptRenderer(_spec()).render()
        self.assertIn("def main(argv: list[str] | None = None) -> int:", text)
        self.assertIn("parser.parse_args(argv)", text)

    def test_description_with_quotes_stays_valid_python(self) -> None:
        spec = ScriptSpec(
            file_name="x",
            description='Say "hi"',
            class_name="Greeter",
            method_name="greet",
        )
        ast.parse(ScriptRenderer(spec).render())


if __name__ == "__main__":
    unittest.main()
