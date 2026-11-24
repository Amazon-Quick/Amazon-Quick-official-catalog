"""
description: Unit tests for scan_checks_reconciliation: numbers stored as text inside running-total SUM ranges. Filesystem-free.
last_updated: 2026-11-24
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scan_checks_reconciliation import check_text_in_sums  # noqa: E402
from scan_findings import Findings  # noqa: E402
from workbook_fixtures import (  # noqa: E402
    SLOW_SECONDS,
    load,
    prepare_finance,
    workbook_bytes,
)


class TestTextInSums(unittest.TestCase):
    def test_running_total_over_text_numbers_is_fast_and_flags_the_short_total(self):
        def build(ws, wb):
            for r in range(2, 4002):
                ws.cell(r, 1, r if r % 100 else str(r))
                ws.cell(r, 2, f"=SUM($A$2:A{r})")

        wb = load(workbook_bytes(build))
        prepare_finance(wb)
        fs = Findings()
        start = time.time()
        check_text_in_sums(wb, fs)
        self.assertLess(time.time() - start, SLOW_SECONDS)
        self.assertTrue(any(i["cell"] == "B4001" for i in fs.items))


if __name__ == "__main__":
    unittest.main()
