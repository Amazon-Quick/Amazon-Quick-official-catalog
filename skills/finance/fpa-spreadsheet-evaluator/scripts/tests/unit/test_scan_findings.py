"""
description: Unit tests for scan_findings.data_text: workbook text is clipped and quoted without a label prefix, and controls are escaped. Filesystem-free.
last_updated: 2026-11-24
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_findings import data_text  # noqa: E402


class TestDataText(unittest.TestCase):
    def test_data_text_quotes_and_clips_without_a_label_prefix(self):
        self.assertEqual(data_text("Q1 2026"), '"Q1 2026"')
        self.assertEqual(data_text("x" * 50), '"' + "x" * 40 + '..."')
        self.assertNotIn("DATA", data_text("Revenue"))

    def test_data_text_keeps_letters_and_escapes_controls(self):
        self.assertEqual(data_text("Umsatz für März"), '"Umsatz für März"')
        self.assertEqual(data_text("a\u202eb\nc\x00"), '"a\\u202eb\\nc\\u0000"')


if __name__ == "__main__":
    unittest.main()
