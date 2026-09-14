"""
description: Unit test for the translate-ms glossary module verifying column matching and instruction building on in-memory data with no filesystem or network access.
last_updated: 2026-09-13
origin: original
"""

import unittest

try:
    from glossary import _GlossaryColumnMatcher, _GlossaryInstructionBuilder

    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - only triggers if deps are missing
    _IMPORT_ERROR = exc


@unittest.skipIf(_IMPORT_ERROR is not None, f"glossary import failed: {_IMPORT_ERROR}")
class GlossaryLogicTest(unittest.TestCase):
    def test_match_columns_finds_source_and_target(self) -> None:
        matcher = _GlossaryColumnMatcher(match_type_key="match_type")
        glossary = [{"english": "cloud", "french": "nuage", "match_type": "exact"}]

        source, target, headers = matcher.match(glossary, "English", "French")

        self.assertEqual(source, "english")
        self.assertEqual(target, "french")
        self.assertEqual(headers, ["english", "french"])

    def test_instruction_includes_matched_term(self) -> None:
        builder = _GlossaryInstructionBuilder()
        glossary = [{"english": "cloud", "french": "nuage", "match_type": "exact"}]
        batch = [{"full_paragraph": "The cloud is blue", "runs": []}]

        instruction = builder.build(batch, glossary, "english", "french")

        self.assertIn("cloud|nuage|exact", instruction)


if __name__ == "__main__":
    unittest.main()
