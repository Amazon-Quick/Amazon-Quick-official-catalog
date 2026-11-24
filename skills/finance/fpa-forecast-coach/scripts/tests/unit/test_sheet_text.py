"""
description: Unit test for sheet_text: Commentary lines and Run_Info rows are stored as text, and Run_Info names the baseline method used (LIC-3). In-memory workbook, no filesystem.
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
from sheet_text import write_commentary_sheet, write_run_info_sheet
from workbook_formats import WORKBOOK_OPTIONS, formats


class TestTextSheets(unittest.TestCase):
    def test_text_sheets(self) -> None:
        hist = np.array([10.0 + i for i in range(12)])
        ctx = RunContext(
            ["S"],
            {"S": {"values": hist, "dates": None}},
            {"S": sm.baseline(hist, 2, "MS")},
            {"S": {}},
            {"S": {}},
            {"S": []},
            {"S": sm.BASELINE_LABEL},
            frozenset(),
            ["a", "b"],
            2,
            "MS",
            12,
            "",
            "t",
            "id",
        )
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {**WORKBOOK_OPTIONS, "in_memory": True})
        f = formats(wb)
        write_commentary_sheet(wb, f, ["=1+1 summary"], ["flag"])
        write_run_info_sheet(wb, f, ctx, "=evil.csv", None)
        wb.close()
        book = load_workbook(io.BytesIO(buf.getvalue()))
        self.assertEqual(book["Commentary"]["A3"].data_type, "s")
        info = {r[0]: r[1] for r in book["Run_Info"].iter_rows(values_only=True)}
        self.assertEqual(info["Baseline method used"], sm.ETS_THETA_NAME)
        self.assertEqual(info["Source file"], "'=evil.csv")
        self.assertNotIn("Weights", info)


if __name__ == "__main__":
    unittest.main()
