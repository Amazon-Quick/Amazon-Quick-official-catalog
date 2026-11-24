"""
description: Unit test for workbook_formats: the formula guard and the options that keep user text as text (no filesystem).
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import unittest

from workbook_formats import WORKBOOK_OPTIONS, defang


class TestWorkbookFormats(unittest.TestCase):
    def test_defang_prefixes_formula_starts(self) -> None:
        for text in ("=1+1", "+1", "-1", "@SUM(A1)"):
            self.assertEqual(defang(text), "'" + text)
        self.assertEqual(defang("Revenue"), "Revenue")

    def test_strings_never_become_formulas_or_links(self) -> None:
        self.assertFalse(WORKBOOK_OPTIONS["strings_to_formulas"])
        self.assertFalse(WORKBOOK_OPTIONS["strings_to_urls"])


if __name__ == "__main__":
    unittest.main()
