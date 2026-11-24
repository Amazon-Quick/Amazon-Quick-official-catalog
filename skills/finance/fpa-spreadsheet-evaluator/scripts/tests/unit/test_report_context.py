"""
description: Unit tests for report_context.source_display: the report header shows only the file name, never a folder or local path. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import report_context  # noqa: E402


class TestSourceDisplay(unittest.TestCase):
    def test_local_paths_show_only_the_file_name(self) -> None:
        for path in (
            "/home/user/Downloads/payroll.xlsx",
            "/Users/someone/workspace/team/finance/payroll.xlsx",
            "/mnt/attached_files/abc/payroll.xlsx",
            "/x/outposts/o1/workspace/sub/payroll.xlsx",
            "C:\\Users\\someone\\payroll.xlsx",
        ):
            with self.subTest(path=path):
                self.assertEqual(report_context.source_display(path), "payroll.xlsx")

    def test_missing_source_shows_nothing(self) -> None:
        self.assertEqual(report_context.source_display(None), "")


if __name__ == "__main__":
    unittest.main()
