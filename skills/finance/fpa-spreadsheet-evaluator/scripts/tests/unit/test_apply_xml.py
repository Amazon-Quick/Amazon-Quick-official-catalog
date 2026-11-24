"""
description: Unit tests for apply_xml: attribute helpers, escaping, literal protection and the prefix-free worksheet view. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import apply_xml as AX  # noqa: E402

MAIN = AX.SHEET_NAMESPACE


class TestAttributes(unittest.TestCase):
    def test_set_attr_adds_replaces_and_removes(self) -> None:
        tag = '<c r="A1"/>'
        added = AX.set_attr(tag, "s", 3)
        self.assertEqual(added, '<c r="A1" s="3"/>')
        self.assertEqual(AX.set_attr(added, "s", 7), '<c r="A1" s="7"/>')
        self.assertEqual(AX.set_attr(added, "s", None), tag)
        self.assertEqual(AX.attr(added, "s"), "3")
        self.assertIsNone(AX.attr(tag, "s"))

    def test_esc_escapes_markup_characters(self) -> None:
        self.assertEqual(AX.esc('a<b>&"c"'), "a&lt;b&gt;&amp;&quot;c&quot;")


class TestLiterals(unittest.TestCase):
    def test_comments_and_cdata_are_hidden_then_restorable(self) -> None:
        xml = '<?xml version="1.0"?><a><!-- <c r="A1"/> --><![CDATA[<x>]]></a>'
        protected, literals = AX.protect_xml_literals(xml)
        self.assertNotIn('<c r="A1"/>', protected)
        self.assertNotIn("CDATA", protected)
        for marker, literal in literals.items():
            protected = protected.replace(marker, literal)
        self.assertEqual(protected, xml)


class TestWorksheetView(unittest.TestCase):
    def test_uniform_prefix_is_stripped_and_reported(self) -> None:
        xml = f'<x:worksheet xmlns:x="{MAIN}"><x:sheetData/></x:worksheet>'
        view, prefix = AX.worksheet_view(xml)
        self.assertEqual(prefix, "x:")
        self.assertIn("<sheetData/>", view)

    def test_unprefixed_sheet_is_unchanged_and_other_namespaces_are_refused(
        self,
    ) -> None:
        plain = f'<worksheet xmlns="{MAIN}"><sheetData/></worksheet>'
        self.assertEqual(AX.worksheet_view(plain), (plain, ""))
        with self.assertRaises(ValueError):
            AX.worksheet_view('<x:worksheet xmlns:x="urn:other"/>')

    def test_cf_signature_ignores_range_and_priority(self) -> None:
        a = '<conditionalFormatting sqref="A1"><cfRule priority="1"/></conditionalFormatting>'
        b = '<conditionalFormatting sqref="B9"><cfRule priority="4"/></conditionalFormatting>'
        self.assertEqual(AX.cf_signature(a), AX.cf_signature(b))


if __name__ == "__main__":
    unittest.main()
