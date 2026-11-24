"""
description: Unit tests for scan_checks_layout: hidden columns with an oversized max in the sheet XML. Filesystem-free.
last_updated: 2026-11-24
"""

import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_checks_formatting import check_cell_formats  # noqa: E402
from scan_checks_layout import check_hidden  # noqa: E402
from scan_findings import Findings  # noqa: E402
from workbook_fixtures import (  # noqa: E402
    SLOW_SECONDS,
    load,
    rewrite_member,
    workbook_bytes,
)


class TestColumnDimensions(unittest.TestCase):
    def test_check_hidden_clamps_a_huge_col_max_to_the_grid(self):
        def build(ws, wb):
            for r in range(1, 6):
                for c in range(1, 5):
                    ws.cell(r, c, r * c)
            ws.column_dimensions["B"].hidden = True
            ws.column_dimensions["B"].width = 20

        buf = rewrite_member(
            workbook_bytes(build),
            "xl/worksheets/sheet1.xml",
            lambda d: re.sub(
                rb"<col [^>]*/>",
                b'<col hidden="1" width="20" customWidth="1" min="2" max="300000000"/>',
                d,
            ),
        )
        wb = load(buf)
        fs = Findings()
        start = time.time()
        check_hidden(wb, fs)
        check_cell_formats(wb, fs, True)
        self.assertLess(time.time() - start, SLOW_SECONDS)
        hidden = [i for i in fs.items if i["check"] == "hidden_rows_in_block"]
        self.assertEqual([i["cell"] for i in hidden], ["B:C"])


if __name__ == "__main__":
    unittest.main()
