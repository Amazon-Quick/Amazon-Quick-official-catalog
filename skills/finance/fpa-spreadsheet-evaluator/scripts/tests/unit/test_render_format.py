"""
description: Unit tests for render_format.readable: JSON-quoted workbook fragments in descriptions are shown decoded, with control characters kept escaped. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import render_format as RF  # noqa: E402


class TestReadable(unittest.TestCase):
    def test_unicode_escapes_in_a_quoted_fragment_are_decoded(self) -> None:
        self.assertEqual(
            RF.readable('Total for "Caf\\u00e9 \\u00b7 Q1" is typed.'),
            'Total for "Café · Q1" is typed.',
        )

    def test_bidi_and_control_characters_stay_escaped(self) -> None:
        self.assertEqual(
            RF.readable('Label "a\\u202eb\\nc"'), 'Label "a\\u202eb\\u000ac"'
        )

    def test_fragments_without_escapes_are_unchanged(self) -> None:
        self.assertEqual(RF.readable('Tab "Summary" cell'), 'Tab "Summary" cell')

    def test_excel_prefixes_are_hidden(self) -> None:
        self.assertEqual(RF.readable("Uses _xlfn.XLOOKUP"), "Uses XLOOKUP")

    def test_html_is_left_for_the_caller_to_escape(self) -> None:
        self.assertEqual(
            RF.E(RF.readable('"\\u003cscript\\u003e"')), "&quot;&lt;script&gt;&quot;"
        )


if __name__ == "__main__":
    unittest.main()
