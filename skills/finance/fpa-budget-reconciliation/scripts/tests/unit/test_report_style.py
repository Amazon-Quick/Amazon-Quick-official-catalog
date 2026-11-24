"""
description: Unit test for report_style: the inlined stylesheet makes no external requests, so the report opens offline. Filesystem-free.
last_updated: 2026-11-24
"""

import unittest

from report_style import report_css


class TestReportCss(unittest.TestCase):
    def test_stylesheet_loads_nothing_from_outside(self) -> None:
        css = report_css()
        for marker in ("http", "@import", "url("):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, css)


if __name__ == "__main__":
    unittest.main()
