"""
description: Unit tests for report_format: HTML escaping, compact money, and the inspect-item count shared by the headline and the workbook. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest

from report_format import esc, inspect_items, money, signed_money


class TestFormatting(unittest.TestCase):
    def test_escape_neutralizes_markup_and_quotes(self) -> None:
        self.assertEqual(
            esc('<img src=x onerror="a">'), "&lt;img src=x onerror=&quot;a&quot;&gt;"
        )

    def test_money_is_compact_and_signed(self) -> None:
        self.assertEqual(money("$", 1_234_567), "$1.2M")
        self.assertEqual(signed_money("$", 48_000), "+$48K")
        self.assertEqual(money("$", -950), "-$950")


class TestInspectItems(unittest.TestCase):
    def test_document_flags_count_each_and_lines_count_once(self) -> None:
        result = {
            "flags": [
                {"key": "A", "view": "ytd", "id": "F01", "tier": "inspect"},
                {"key": "A", "view": "current", "id": "F02", "tier": "inspect"},
                {"key": "A", "view": "document", "id": "F03", "tier": "inspect"},
                {"key": "B", "view": "ytd", "id": "F04", "tier": "watch"},
            ],
            "headcount_flags": [{"tier": "inspect"}],
        }
        self.assertEqual(inspect_items(result), 3)


if __name__ == "__main__":
    unittest.main()
