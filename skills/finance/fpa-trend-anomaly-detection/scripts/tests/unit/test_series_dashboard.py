"""
description: Unit tests for series_dashboard. build is filesystem-free apart from reading the skill's own page template, and text from the source cannot end the page script or fill a placeholder; write never replaces an existing file unless asked.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import datetime as dt
import tempfile
import unittest
from pathlib import Path

import series_dashboard as sd
import series_review as sr


def result(name: str) -> dict:
    dates = [f"{2023 + i // 12}-{i % 12 + 1:02d}-01" for i in range(24)]
    return sr.run(
        {name: {"dates": dates, "values": [100.0 + i for i in range(24)]}},
        freq="monthly",
        today=dt.date(2026, 11, 24),
    )


class TestDashboardEscaping(unittest.TestCase):
    def test_comment_and_script_text_in_a_line_name_is_escaped(self) -> None:
        page = sd.build(result("<!--<script></script>"))
        self.assertNotIn("<!--<script>", page)
        self.assertEqual(page.count("</script>"), 1)

    def test_placeholder_text_in_the_title_is_not_filled(self) -> None:
        page = sd.build(result("Revenue"), title="{{DATA}}")
        self.assertIn("<h1>{{DATA}}</h1>", page)


class TestDashboardWrite(unittest.TestCase):
    """Uses a temporary folder, because the behavior under test is not replacing a file."""

    def test_existing_file_is_not_replaced_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "review.html"
            target.write_text("the user's file", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                sd.write(result("Revenue"), str(target))
            self.assertEqual(target.read_text(encoding="utf-8"), "the user's file")
            sd.write(result("Revenue"), str(target), overwrite=True)
            self.assertIn("<html", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
