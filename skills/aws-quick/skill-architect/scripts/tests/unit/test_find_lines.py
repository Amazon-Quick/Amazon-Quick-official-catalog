"""
description: Unit tests for find_lines.py. Filesystem-free: each locator is given an injected list of lines, so grep, block, heading, rule, and range location are verified without reading any file.
last_updated: 2026-09-13
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from find_lines import (
    BlockLocator,
    GrepLocator,
    HeadingLocator,
    RangeLocator,
    RuleLocator,
)

LINES = [
    "# Title",  # 1
    "intro text",  # 2
    "<Rules>",  # 3
    "1. first rule",  # 4
    "2. second rule",  # 5
    "</Rules>",  # 6
    "## Section",  # 7
    "body foo",  # 8
    "more",  # 9
]


class TestGrepLocator(unittest.TestCase):
    def test_matches_regex(self) -> None:
        hits = GrepLocator(LINES, "rule", ignore_case=False, fixed=False).locate().hits
        self.assertEqual([hit.number for hit in hits], [4, 5])

    def test_fixed_treats_pattern_as_literal(self) -> None:
        hits = (
            GrepLocator(["a.b", "axb"], "a.b", ignore_case=False, fixed=True)
            .locate()
            .hits
        )
        self.assertEqual([hit.number for hit in hits], [1])


class TestBlockLocator(unittest.TestCase):
    def test_finds_block_span(self) -> None:
        result = BlockLocator(LINES, "Rules").locate()
        self.assertEqual((result.start, result.end), (3, 6))

    def test_missing_block_not_found(self) -> None:
        self.assertFalse(BlockLocator(LINES, "Nope").locate().found)


class TestHeadingLocator(unittest.TestCase):
    def test_section_range_runs_to_end(self) -> None:
        result = HeadingLocator(LINES, "## Section").locate()
        self.assertEqual((result.start, result.end), (7, 9))


class TestRuleLocator(unittest.TestCase):
    def test_finds_rule_line(self) -> None:
        self.assertEqual(RuleLocator(LINES, 2).locate().hit.number, 5)

    def test_missing_rule(self) -> None:
        self.assertIsNone(RuleLocator(LINES, 9).locate().hit)


class TestRangeLocator(unittest.TestCase):
    def test_range_clamped_to_file(self) -> None:
        hits = RangeLocator(LINES, 8, 100).locate().hits
        self.assertEqual([hit.number for hit in hits], [8, 9])


if __name__ == "__main__":
    unittest.main()
