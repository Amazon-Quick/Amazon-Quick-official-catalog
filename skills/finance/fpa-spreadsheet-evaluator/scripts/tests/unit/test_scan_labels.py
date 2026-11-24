"""
description: Unit tests for scan_labels: range labels for findings. Filesystem-free.
last_updated: 2026-11-24
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_labels import range_label  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402


class TestRangeLabel(unittest.TestCase):
    def test_range_label_returns_empty_for_an_unreadable_reference(self):
        wb = load(workbook_bytes(lambda ws, wb: ws.cell(1, 1, 1)))
        self.assertEqual(range_label(wb.sheets["Sheet"], "not a range"), "")

    def test_range_label_names_a_cell_by_row_and_column_labels(self):
        def build(ws, wb):
            ws["A1"], ws["B1"] = "Line", "Jan 2026"
            ws["A2"], ws["B2"] = "Revenue", 100

        wb = load(workbook_bytes(build))
        self.assertEqual(
            range_label(wb.sheets["Sheet"], "B2"), "Revenue \u00b7 Jan 2026"
        )


if __name__ == "__main__":
    unittest.main()
