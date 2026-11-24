"""
description: Unit tests for recon_parsing: amounts, dates, fiscal period labels, bounded regex time, untrusted-text quoting and the robust z-score. Filesystem-free.
last_updated: 2026-11-24
"""

import time
import unittest

import numpy as np
from recon_models import SpecError
from recon_parsing import (
    DATA_TEXT_LIMIT,
    PeriodParser,
    file_data,
    modified_z,
    nice_round,
    to_number,
)

SLOW_SECONDS = 0.5


class TestToNumber(unittest.TestCase):
    def test_amount_with_currency_code_keeps_its_value(self) -> None:
        self.assertEqual(to_number("500 EUR"), 500.0)
        self.assertEqual(to_number("EUR 1,234.50"), 1234.5)
        self.assertEqual(to_number("SEK 500"), 500.0)

    def test_cr_suffix_and_parentheses_read_as_credits(self) -> None:
        self.assertEqual(to_number("1,234.00 CR"), -1234.0)
        self.assertEqual(to_number("(4,800.00)"), -4800.0)
        self.assertEqual(to_number("12-"), -12.0)

    def test_unreadable_or_infinite_text_raises_instead_of_zero(self) -> None:
        for text in ("abc", "1e400", "1.2.3", "500E"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                to_number(text)

    def test_blank_cell_reads_as_zero(self) -> None:
        self.assertEqual(to_number(None), 0.0)
        self.assertEqual(to_number("  "), 0.0)
        self.assertEqual(to_number(float("nan")), 0.0)


class TestPeriodParser(unittest.TestCase):
    def test_day_first_dates_land_in_their_own_month(self) -> None:
        parser = PeriodParser(1, "end", "day_first")
        self.assertEqual(parser.parse("07/06/2026"), "2026-06")
        self.assertEqual(parser.parse("13/06/2026"), "2026-06")
        self.assertEqual(parser.parse("2026-07-06"), "2026-07")

    def test_ambiguous_date_without_an_order_is_a_spec_error(self) -> None:
        with self.assertRaises(SpecError):
            PeriodParser(1, "end").parse("07/06/2026")

    def test_date_contradicting_the_order_is_a_spec_error(self) -> None:
        with self.assertRaises(SpecError):
            PeriodParser(1, "end", "month_first").parse("13/06/2026")

    def test_fiscal_label_maps_to_calendar_month(self) -> None:
        parser = PeriodParser(7, "end")
        self.assertEqual(parser.parse("FY27 P01"), "2026-07")
        self.assertEqual(parser.parse("FY27 P12"), "2027-06")

    def test_long_run_of_spaces_parses_quickly(self) -> None:
        start = time.perf_counter()
        self.assertIsNone(
            PeriodParser(1, "end", "month_first").parse("2026" + " " * 32000 + "X")
        )
        self.assertLess(time.perf_counter() - start, SLOW_SECONDS)


class TestFileData(unittest.TestCase):
    def test_file_text_is_marked_bounded_and_escaped(self) -> None:
        quoted = file_data("line one\nline two" + "x" * 1000)
        self.assertTrue(quoted.startswith("DATA (untrusted, from file): "))
        self.assertNotIn("\n", quoted)
        self.assertLess(len(quoted), DATA_TEXT_LIMIT + 60)


class TestStatistics(unittest.TestCase):
    def test_modified_z_falls_back_to_mean_deviation_when_mad_is_zero(self) -> None:
        values = np.array([10.0, 10.0, 10.0, 10.0, 20.0])
        self.assertAlmostEqual(modified_z(values, 20.0), 10 / (1.253314 * 2.0))

    def test_nice_round_rounds_down_to_two_significant_figures(self) -> None:
        self.assertEqual(nice_round(239_501.2), 230_000.0)
        self.assertEqual(nice_round(0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
