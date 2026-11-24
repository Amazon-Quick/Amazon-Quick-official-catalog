"""
description: Unit tests for variance_table: money cells parse to finite floats or None (nan and inf are missing), shown decimals are counted, and CSV and Markdown tables parse to the same rows. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest

from variance_table import clean_num, decimals, find_col, parse_table


class TestCleanNum(unittest.TestCase):
    def test_parses_money_formats(self) -> None:
        self.assertEqual(clean_num("$1,234"), 1234.0)
        self.assertEqual(clean_num("(1,234)"), -1234.0)
        self.assertEqual(clean_num("1.2M"), 1.2e6)
        self.assertEqual(clean_num("-5%"), -5.0)

    def test_non_finite_values_are_missing(self) -> None:
        for text in ("nan", "NaN", "inf", "-inf", "Infinity", "1e400"):
            with self.subTest(text=text):
                self.assertIsNone(clean_num(text))

    def test_blank_and_text_are_missing(self) -> None:
        for text in ("", "-", "n/a", "abc", None):
            with self.subTest(text=text):
                self.assertIsNone(clean_num(text))


class TestParseTable(unittest.TestCase):
    def test_counts_shown_decimals(self) -> None:
        self.assertEqual(decimals("1,234.50"), 2)
        self.assertEqual(decimals("(300)"), 0)

    def test_markdown_and_csv_give_the_same_rows(self) -> None:
        csv_text = "Line,Actual,Budget\nRevenue,10,9\n"
        md_text = "| Line | Actual | Budget |\n|---|---|---|\n| Revenue | 10 | 9 |\n"
        self.assertEqual(parse_table(csv_text), parse_table(md_text))

    def test_short_markdown_row_does_not_raise(self) -> None:
        header, rows = parse_table(
            "| line | actual | budget |\n|---|---|---|\n| Revenue | 10 |\n"
        )
        self.assertEqual(rows, [{"line": "Revenue", "actual": "10"}])
        self.assertEqual(find_col(header, "comparison"), "budget")


if __name__ == "__main__":
    unittest.main()
