"""
description: Unit tests for report_html: line labels and the currency symbol are escaped, only a SYNTHETIC DATA notice is labeled synthetic, revenue lines color a beat as favorable, and the page makes no external requests. Filesystem-free.
last_updated: 2026-11-24
"""

import re
import unittest

from recon_models import Nature
from report_html import HeadlineWriter, HtmlReportBuilder
from result_factory import line, result

PAYLOAD = "<img src=x onerror=alert(1)>"


class TestHtmlReport(unittest.TestCase):
    def test_unplanned_line_label_is_escaped(self) -> None:
        data = result(
            [
                line("Eng | 6200", 900.0, 1000.0),
                line(f"Eng | {PAYLOAD}", 0.0, 50.0, in_plan=False),
            ]
        )
        page = HtmlReportBuilder(data, "book.xlsx").build()
        self.assertNotIn(PAYLOAD, page)
        self.assertIn("no plan", page)

    def test_currency_symbol_is_escaped_in_page_and_headline(self) -> None:
        data = result([line("Eng | 6200", 900.0, 1000.0)], currency_symbol="<i>X</i> ")
        self.assertNotIn("<i>X</i>", HtmlReportBuilder(data, "book.xlsx").build())
        self.assertNotIn("<i>X</i>", HeadlineWriter(data, True).write())

    def test_grain_name_in_table_heading_is_escaped(self) -> None:
        data = result(
            [line("Eng | 6200", 900.0, 1000.0)], grain=["<b>dept</b>", "account"]
        )
        self.assertNotIn("<b>dept</b>", HtmlReportBuilder(data, "b.xlsx").build())

    def test_ampersand_symbol_is_escaped_once(self) -> None:
        unplanned = line("Eng | 6700", 0.0, 50.0, in_plan=False)
        data = result(
            [line("Eng | 6200", 900.0, 1000.0), unplanned], currency_symbol="A&B "
        )
        page = HtmlReportBuilder(data, "b.xlsx").build()
        self.assertIn("A&amp;B", page)
        self.assertNotIn("&amp;amp;", page)

    def test_real_data_notice_is_labeled_note(self) -> None:
        page = HtmlReportBuilder(
            result(
                [line("Eng | 6200", 900.0, 1000.0)],
                data_notice="Excludes the Tokyo entity.",
            ),
            "b.xlsx",
        ).build()
        self.assertIn("<b>Note</b>", page)
        self.assertNotIn("Synthetic data", page)

    def test_synthetic_notice_keeps_its_label(self) -> None:
        page = HtmlReportBuilder(
            result(
                [line("Eng | 6200", 900.0, 1000.0)],
                data_notice="SYNTHETIC DATA: test files.",
            ),
            "b.xlsx",
        ).build()
        self.assertIn("<b>Synthetic data</b>", page)

    def test_revenue_beat_is_colored_favorable(self) -> None:
        data = result(
            [line("Sales | 4000", 900.0, 1000.0, nature=Nature.REVENUE)],
            grain=["account"],
        )
        page = HtmlReportBuilder(data, "b.xlsx").build()
        self.assertIn('<td class="u">+$100</td>', page)
        self.assertNotIn('<td class="o">+$100</td>', page)

    def test_page_has_no_external_requests(self) -> None:
        page = HtmlReportBuilder(
            result([line("Eng | 6200", 900.0, 1000.0)]), "b.xlsx"
        ).build()
        self.assertEqual(re.findall(r"(?:src|href)=[\"']?https?:", page), [])


if __name__ == "__main__":
    unittest.main()
