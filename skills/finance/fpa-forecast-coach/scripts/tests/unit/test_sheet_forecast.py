"""
description: Unit test for sheet_forecast.write_forecast_sheet in an in-memory workbook: the title is text even when it starts with '=' (SEC-1), and a balance is compared with the prior run at the last shared period (RUN-1, RUN-4). No filesystem.
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
from sheet_forecast import write_forecast_sheet
from workbook_formats import WORKBOOK_OPTIONS, formats

LABELS = ["Jan-27", "Feb-27", "Mar-27"]


def _ctx(title: str, stocks: frozenset) -> RunContext:
    hist = np.array([100.0 + i for i in range(24)])
    fc = {"Inv": sm.baseline(hist, 3, "MS")}
    methods = {"Inv": {sm.BASELINE_LABEL: fc["Inv"]["p50"]}}
    return RunContext(
        ["Inv"],
        {"Inv": {"values": hist, "dates": None}},
        fc,
        {"Inv": {}},
        methods,
        {"Inv": []},
        {"Inv": sm.BASELINE_LABEL},
        stocks,
        LABELS,
        3,
        "MS",
        12,
        "$K",
        title,
        "abc",
    )


def _write(ctx, prior):
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {**WORKBOOK_OPTIONS, "in_memory": True})
    movers, issues = write_forecast_sheet(wb, formats(wb), ctx, prior)
    wb.close()
    return load_workbook(io.BytesIO(buf.getvalue()))["Forecast"], movers, issues


class TestForecastSheet(unittest.TestCase):
    def test_title_starting_with_equals_is_text(self) -> None:
        ws, _, _ = _write(_ctx("=1+1", frozenset()), None)
        self.assertEqual(ws["A1"].data_type, "s")

    def test_balance_is_compared_at_the_last_shared_period(self) -> None:
        ctx = _ctx("t", frozenset({"Inv"}))
        prior = {"Inv": {"Jan-27": 1.0, "Feb-27": 2.0}}
        _, movers, _ = _write(ctx, prior)
        self.assertEqual(movers[0][4], "balance at Feb-27")
        self.assertAlmostEqual(movers[0][2], float(ctx.fc["Inv"]["p50"][1]) - 2.0)

    def test_no_shared_periods_is_reported(self) -> None:
        _, movers, issues = _write(_ctx("t", frozenset()), {"Inv": {"Dec-30": 1.0}})
        self.assertEqual(movers, [])
        self.assertIn("no shared forecast periods", issues[0])


if __name__ == "__main__":
    unittest.main()
