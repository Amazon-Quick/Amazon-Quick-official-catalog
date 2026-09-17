"""
description: Test deterministic synthetic LAS generation and confined output paths.
last_updated: 2026-09-16
origin: original
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(
    "skills/energy-utilities/automated-log-analysis/scripts/create_synthetic_las.py"
).resolve()
SPEC = importlib.util.spec_from_file_location("create_synthetic_las", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _module() -> object:
    return MODULE


class TestCreateSyntheticLas(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_synthetic_las_is_deterministic_and_contains_vendor_curves(self) -> None:
        first = _module().run({"workspace_dir": str(self.workspace / "first")})
        second = _module().run({"workspace_dir": str(self.workspace / "second")})
        self.assertEqual(first["status"], "created")
        self.assertEqual(first["sample_count"], 1501)
        self.assertEqual(
            first["curves"], ["DEPT", "GRMA", "ROBB", "TNPH", "P40H", "DTCO", "HCAL"]
        )
        self.assertEqual(
            Path(first["path"]).read_text(encoding="utf-8"),
            Path(second["path"]).read_text(encoding="utf-8"),
        )
        self.assertIn(" 1.8500 ", Path(first["path"]).read_text(encoding="utf-8"))

    def test_synthetic_las_rejects_unsafe_paths_and_identifiers(self) -> None:
        traversal = _module().run(
            {"workspace_dir": str(self.workspace), "data_root": "../outside"}
        )
        identifier = _module().run(
            {"workspace_dir": str(self.workspace), "well_id": "../unsafe"}
        )
        self.assertEqual(traversal["status"], "error")
        self.assertIn("parent traversal", traversal["error"])
        self.assertEqual(
            identifier,
            {"status": "error", "error": "well_id must match ^[A-Za-z0-9._-]+$"},
        )


if __name__ == "__main__":
    unittest.main()
