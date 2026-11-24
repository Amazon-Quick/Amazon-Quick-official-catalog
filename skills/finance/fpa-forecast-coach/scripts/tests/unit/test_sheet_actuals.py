"""
description: Unit test for sheet_actuals.write_actuals_sheet: a series name starting with '=' is text in the header and the chart title (comment 4674019674). In-memory workbook, no filesystem.
last_updated: 2026-11-24
origin: original

Run: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import io
import unittest
import zipfile

import numpy as np
import stat_methods as sm
import xlsxwriter
from openpyxl import load_workbook
from run_context import RunContext
from sheet_actuals import write_actuals_sheet
from sheet_tables import write_bands_sheet
from workbook_formats import WORKBOOK_OPTIONS, formats


class TestActualsSheet(unittest.TestCase):
    def test_formula_like_name_stays_text(self) -> None:
        hist = np.array([10.0 + i for i in range(12)])
        name = "=HYPERLINK(1)"
        ctx = RunContext(
            [name],
            {name: {"values": hist, "dates": None}},
            {name: sm.baseline(hist, 2, "MS")},
            {name: {}},
            {name: {}},
            {name: []},
            {name: sm.BASELINE_LABEL},
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
        write_bands_sheet(wb, f, ctx)
        write_actuals_sheet(wb, f, ctx)
        wb.close()
        data = buf.getvalue()
        self.assertEqual(
            load_workbook(io.BytesIO(data))["Actuals"]["B1"].data_type, "s"
        )
        chart = zipfile.ZipFile(io.BytesIO(data)).read("xl/charts/chart1.xml").decode()
        self.assertIn("'=HYPERLINK(1): actuals and forecast", chart)


if __name__ == "__main__":
    unittest.main()
