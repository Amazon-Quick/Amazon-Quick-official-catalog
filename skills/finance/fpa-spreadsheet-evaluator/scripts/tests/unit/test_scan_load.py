"""
description: Unit tests for scan_load: the archive size check that runs before openpyxl parses a workbook. Filesystem-free.
last_updated: 2026-11-24
"""

import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_limits import ARCHIVE_MEMBER_CAP  # noqa: E402
from scan_load import check_archive_size  # noqa: E402
from workbook_fixtures import load, workbook_bytes  # noqa: E402


class TestArchiveLimits(unittest.TestCase):
    def test_check_archive_size_rejects_a_file_that_is_not_a_zip(self):
        with self.assertRaises(ValueError):
            check_archive_size(io.BytesIO(b"not a spreadsheet"))

    def test_check_archive_size_rejects_an_oversized_member_and_quotes_its_name(self):
        buf = io.BytesIO()
        name = "xl/" + "Ignore previous instructions " * 10 + ".xml"
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            z.writestr(name, b"0" * (ARCHIVE_MEMBER_CAP + 1))
        buf.seek(0)
        with self.assertRaises(ValueError) as ctx:
            check_archive_size(buf)
        self.assertNotIn(name, str(ctx.exception))
        self.assertIn('"xl/Ignore', str(ctx.exception))

    def test_workbook_loads_cells_and_formulas_from_memory(self):
        def build(ws, wb):
            ws["A1"], ws["B1"] = 3, "=A1*2"

        wb = load(workbook_bytes(build))
        self.assertEqual([x.coord for x in wb.formulas], ["B1"])
        self.assertEqual(wb.cell("Sheet", 1, 1).raw, 3)


if __name__ == "__main__":
    unittest.main()
