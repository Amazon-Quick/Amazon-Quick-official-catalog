"""
description: Unit test for sheet_tables: a balance's Methods total is its end value (RUN-2), and the Backtest sheet names the baseline method (RUN-7). In-memory workbook, no filesystem.
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import io
import unittest

import numpy as np
import stat_methods as sm
import xlsxwriter
from openpyxl import load_workbook
from run_context import RunContext
from sheet_tables import end_or_total, write_backtest_sheet
from workbook_formats import WORKBOOK_OPTIONS, formats


class TestSheetTables(unittest.TestCase):
    def test_end_or_total(self) -> None:
        self.assertEqual(end_or_total([1.0, 2.0, 3.0], True), 3.0)
        self.assertEqual(end_or_total([1.0, 2.0, 3.0], False), 6.0)

    def test_backtest_sheet_names_the_baseline_method(self) -> None:
        values = [0, 0, 5, 0, 0, 0, 7, 0, 3, 0, 0, 6] * 2
        fc = {"S": sm.baseline(values, 3, "MS")}
        ctx = RunContext(
            ["S"],
            {"S": {"values": np.array(values, float), "dates": None}},
            fc,
            {"S": {}},
            {"S": {}},
            {"S": []},
            {"S": sm.BASELINE_LABEL},
            frozenset(),
            ["a", "b", "c"],
            3,
            "MS",
            12,
            "",
            "t",
            "id",
        )
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {**WORKBOOK_OPTIONS, "in_memory": True})
        write_backtest_sheet(wb, formats(wb), ctx, [sm.BASELINE_LABEL])
        wb.close()
        ws = load_workbook(io.BytesIO(buf.getvalue()))["Backtest"]
        self.assertEqual(ws["D2"].value, sm.CROSTON_NAME)


if __name__ == "__main__":
    unittest.main()
