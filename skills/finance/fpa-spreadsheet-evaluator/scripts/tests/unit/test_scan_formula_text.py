"""
description: Unit tests for scan_formula_text: IF nesting, function context and linear time on long formulas. Filesystem-free.
last_updated: 2026-11-24
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_formula_text import (  # noqa: E402
    function_context,
    if_depth,
    literal_numbers,
    mask_strings,
)
from workbook_fixtures import SLOW_SECONDS  # noqa: E402


class TestFormulaParsing(unittest.TestCase):
    def test_if_depth_counts_nested_ifs(self):
        self.assertEqual(if_depth(mask_strings("=IF(A1,IF(B1,1,IFS(C1,2)),3)")), 3)

    def test_function_context_names_the_innermost_call_and_argument(self):
        masked = mask_strings("=ROUND(SUM(A1,B1),2)")
        self.assertEqual(masked[18], "2")
        self.assertEqual(function_context(masked)[18], ("ROUND", 1))
        self.assertEqual(function_context(masked)[14], ("SUM", 1))

    def test_long_formula_scan_is_linear(self):
        formula = "=" + "A" * 8000 + "+" + "(1)" * 50
        masked = mask_strings(formula)
        start = time.time()
        if_depth(masked)
        function_context(masked)
        literal_numbers(formula)
        self.assertLess(time.time() - start, SLOW_SECONDS)


if __name__ == "__main__":
    unittest.main()
