"""
description: Unit tests for create_report: a stem with a path separator or parent reference is refused before any file is read or written, and a bad argument list returns 2. Filesystem-free.
last_updated: 2026-11-24
"""

import contextlib
import io
import unittest
from pathlib import PurePosixPath

from create_report import ReportFacade, main


class TestReportFacade(unittest.TestCase):
    def test_stem_that_leaves_the_output_folder_is_refused(self) -> None:
        for stem in ("../../x", "/abs/x", "a/b", "..", ""):
            with self.subTest(stem=stem), self.assertRaises(ValueError):
                ReportFacade(
                    PurePosixPath("results.json"), PurePosixPath("out"), stem
                ).create()


class TestMain(unittest.TestCase):
    def test_missing_arguments_return_two(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
