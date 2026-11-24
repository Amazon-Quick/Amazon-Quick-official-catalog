"""
description: Unit tests for series_workbook.write to a buffer. Filesystem-free: the workbook is written to a BytesIO buffer and its XML is checked for formulas built from line names.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime as dt
import io
import unittest
import zipfile

import series_review as sr
import series_workbook as swb


class TestWorkbookText(unittest.TestCase):
    def test_line_names_are_written_as_text_never_formulas(self) -> None:
        dates = [f"{2023 + i // 12}-{i % 12 + 1:02d}-01" for i in range(24)]
        names = ['=HYPERLINK("https://example.invalid/x","Open")', "Payroll!B7 adj"]
        series = {
            n: {"dates": dates, "values": [100.0 + i * (k + 1) for i in range(24)]}
            for k, n in enumerate(names)
        }
        res = sr.run(series, freq="monthly", today=dt.date(2026, 11, 24))
        buffer = io.BytesIO()
        swb.write(res, buffer)
        with zipfile.ZipFile(buffer) as book:
            xml = "".join(
                book.read(n).decode("utf-8")
                for n in book.namelist()
                if n.endswith(".xml")
            )
        self.assertNotIn("<f>HYPERLINK", xml)
        self.assertNotIn("<c:f>Payroll!B7", xml)


if __name__ == "__main__":
    unittest.main()
