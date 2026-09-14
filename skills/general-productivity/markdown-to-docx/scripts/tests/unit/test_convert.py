"""
description: Unit tests for the pure markdown parsing logic in convert.py, exercising inline formatting parsing and block-level document element parsing without any filesystem or network access.
last_updated: 2026-09-13
origin: original
"""

import unittest

from convert import (
    BlockquoteElement,
    BulletElement,
    CodeBlockElement,
    HeadingElement,
    HorizontalRuleElement,
    InlineFormatParser,
    InlineSegment,
    MarkdownDocumentParser,
    NumberedElement,
    ParagraphElement,
    TableElement,
)


class InlineFormatParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = InlineFormatParser()

    def test_parse_plain_text_yields_single_segment(self) -> None:
        segments = self.parser.parse("plain text")
        self.assertEqual(segments, [InlineSegment(text="plain text")])

    def test_parse_mixed_inline_formatting(self) -> None:
        segments = self.parser.parse("a **b** c")
        self.assertEqual(
            segments,
            [
                InlineSegment(text="a "),
                InlineSegment(text="b", bold=True),
                InlineSegment(text=" c"),
            ],
        )

    def test_parse_link_bold_italic_and_code(self) -> None:
        self.assertEqual(
            self.parser.parse("[t](u)"),
            [InlineSegment(text="t", link="u")],
        )
        self.assertEqual(
            self.parser.parse("***bi***"),
            [InlineSegment(text="bi", bold=True, italic=True)],
        )
        self.assertEqual(
            self.parser.parse("`c`"),
            [InlineSegment(text="c", code=True)],
        )
        self.assertEqual(
            self.parser.parse("*i*"),
            [InlineSegment(text="i", italic=True)],
        )


class MarkdownDocumentParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = MarkdownDocumentParser(InlineFormatParser())

    def _sample_lines(self) -> list:
        return [
            "# Title\n",
            "\n",
            "Hello world.\n",
            "continued.\n",
            "\n",
            "- item one\n",
            "1. num one\n",
            "> quote\n",
            "---\n",
            "| a | b |\n",
            "| --- | --- |\n",
            "| c | d |\n",
        ]

    def test_parse_produces_expected_element_sequence(self) -> None:
        elements = self.parser.parse(self._sample_lines(), title=None)

        self.assertEqual(len(elements), 7)
        self.assertIsInstance(elements[0], HeadingElement)
        self.assertIsInstance(elements[1], ParagraphElement)
        self.assertIsInstance(elements[2], BulletElement)
        self.assertIsInstance(elements[3], NumberedElement)
        self.assertIsInstance(elements[4], BlockquoteElement)
        self.assertIsInstance(elements[5], HorizontalRuleElement)
        self.assertIsInstance(elements[6], TableElement)

    def test_heading_level_and_paragraph_buffering(self) -> None:
        elements = self.parser.parse(self._sample_lines(), title=None)

        heading = elements[0]
        self.assertEqual(heading.doc_level, 0)
        self.assertEqual(heading.segments, [InlineSegment(text="Title")])

        paragraph = elements[1]
        self.assertEqual(
            paragraph.segments,
            [InlineSegment(text="Hello world. continued.")],
        )

    def test_title_overrides_first_h1(self) -> None:
        elements = self.parser.parse(self._sample_lines(), title="Override")

        heading = elements[0]
        self.assertEqual(heading.segments, [InlineSegment(text="Override")])

    def test_list_items_carry_indent_and_segments(self) -> None:
        elements = self.parser.parse(self._sample_lines(), title=None)

        bullet = elements[2]
        self.assertEqual(bullet.indent, 0)
        self.assertEqual(bullet.segments, [InlineSegment(text="item one")])

        numbered = elements[3]
        self.assertEqual(numbered.indent, 0)
        self.assertEqual(numbered.segments, [InlineSegment(text="num one")])

    def test_table_separator_rows_are_filtered(self) -> None:
        elements = self.parser.parse(self._sample_lines(), title=None)

        table = elements[6]
        self.assertEqual(len(table.rows), 2)
        self.assertEqual(len(table.rows[0].cells), 2)
        self.assertEqual(table.rows[0].cells[0].segments, [InlineSegment(text="a")])
        self.assertEqual(table.rows[1].cells[1].segments, [InlineSegment(text="d")])

    def test_fenced_code_block_is_collected_verbatim(self) -> None:
        lines = [
            "```python\n",
            "x = 1\n",
            "y = 2\n",
            "```\n",
        ]
        elements = self.parser.parse(lines, title=None)

        self.assertEqual(len(elements), 1)
        self.assertIsInstance(elements[0], CodeBlockElement)
        self.assertEqual(elements[0].text, "x = 1\ny = 2")


if __name__ == "__main__":
    unittest.main()
