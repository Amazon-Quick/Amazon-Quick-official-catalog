"""
description: Unit tests for find_data_profile: period headers need a month name, long header cells match in bounded time, date-order evidence is counted, a wide file profiles quickly, and display names are clipped. Filesystem-free.
last_updated: 2026-11-24
"""

import json
import time
import unittest

import pandas as pd
from find_data_profile import (
    PERIOD_HEADER_RE,
    DateOrderEvidence,
    SheetProfiler,
    SpecDrafter,
)

SLOW_SECONDS = 2.0


class TestPeriodHeader(unittest.TestCase):
    def test_month_and_fiscal_headers_match(self) -> None:
        for header in ("Jan-26", "Sept 2026", "2026-09", "FY27 P01", "P3 FY27"):
            with self.subTest(header=header):
                self.assertIsNotNone(PERIOD_HEADER_RE.fullmatch(header))

    def test_code_columns_are_not_periods(self) -> None:
        for header in ("dept10", "Marketing 26", "Acct 6200"):
            with self.subTest(header=header):
                self.assertIsNone(PERIOD_HEADER_RE.fullmatch(header))

    def test_long_run_of_spaces_matches_quickly(self) -> None:
        start = time.perf_counter()
        PERIOD_HEADER_RE.fullmatch("FY" + " " * 20000 + "26" + " " * 20000 + "x")
        self.assertLess(time.perf_counter() - start, SLOW_SECONDS)


class TestDateOrderEvidence(unittest.TestCase):
    def test_counts_dates_only_one_order_can_read(self) -> None:
        counts = DateOrderEvidence(
            ["07/06/2026", "07/13/2026", "13/07/2026", "x"]
        ).count()
        self.assertEqual(
            (counts.ambiguous_dates, counts.month_first_dates, counts.day_first_dates),
            (1, 1, 1),
        )

    def test_one_sided_evidence_suggests_a_default(self) -> None:
        raw = pd.DataFrame(
            [
                ["Date", "Dept", "Amount"],
                ["07/06/2026", "A", "1"],
                ["07/13/2026", "B", "2"],
            ],
            dtype=object,
        )
        sheet = SheetProfiler("gl.csv", None, raw).profile()
        _, questions = SpecDrafter([sheet]).draft()
        self.assertTrue(any("Suggested default: month_first" in q for q in questions))


class TestSheetProfiler(unittest.TestCase):
    def test_wide_file_of_code_columns_profiles_quickly(self) -> None:
        header = [f"dept{i}" for i in range(400)]
        rows = [[f"v{(r * 7 + c) % 50}" for c in range(400)] for r in range(300)]
        raw = pd.DataFrame([header, *rows], dtype=object)
        start = time.perf_counter()
        sheet = SheetProfiler("wide.csv", None, raw).profile()
        self.assertLess(time.perf_counter() - start, 20 * SLOW_SECONDS)
        self.assertEqual(sheet.wide_period_columns, [])

    def test_long_header_is_clipped_in_the_profile_json(self) -> None:
        name = "Long header " + "x" * 200
        raw = pd.DataFrame([[name, "Amount"], ["A", "1"], ["B", "2"]], dtype=object)
        sheet = SheetProfiler("f.csv", None, raw).profile()
        dumped = json.loads(sheet.model_dump_json())
        self.assertEqual(len(dumped["columns"][0]["name"]), 60)


if __name__ == "__main__":
    unittest.main()
