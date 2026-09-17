"""
description: Test confined LAS parsing, vendor aliases, wrapped data, and unsafe-path rejection.
last_updated: 2026-09-16
origin: original
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


def _load(name: str, relative_path: str) -> Any:
    module_path = Path(relative_path).resolve()
    specification = importlib.util.spec_from_file_location(name, module_path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


CREATE = _load(
    "parse_test_create",
    "skills/energy-utilities/automated-log-analysis/scripts/create_synthetic_las.py",
)
PARSE = _load(
    "run_las_parse",
    "skills/energy-utilities/automated-log-analysis/scripts/run_las_parse.py",
)


class TestRunLasParse(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_parse_resolves_vendor_aliases_and_wrap_yes(self) -> None:
        created = CREATE.run({"workspace_dir": str(self.workspace)})
        las_path = Path(created["path"])
        las_path.write_text(
            las_path.read_text(encoding="utf-8").replace("WRAP. NO", "WRAP. YES"),
            encoding="utf-8",
            newline="\n",
        )
        result = PARSE.run(
            {"workspace_dir": str(self.workspace), "las_path": created["relative_path"]}
        )
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["wrap"])
        self.assertEqual(result["sample_count"], 1501)
        self.assertEqual(result["alias_mapping"]["GRMA"], "GR")
        self.assertEqual(result["alias_mapping"]["ROBB"], "RHOB")
        self.assertEqual(result["alias_mapping"]["P40H"], "RT")
        self.assertTrue(result["required_curves"]["valid"])

    def test_parse_rejects_traversal_and_absolute_las_paths(self) -> None:
        traversal = PARSE.run(
            {"workspace_dir": str(self.workspace), "las_path": "../outside.las"}
        )
        absolute = PARSE.run(
            {
                "workspace_dir": str(self.workspace),
                "las_path": str(self.workspace / "well.las"),
            }
        )
        self.assertEqual(traversal["status"], "error")
        self.assertIn("parent traversal", traversal["error"])
        self.assertEqual(absolute["status"], "error")
        self.assertEqual(
            absolute["error"], "las_path must be relative to workspace_dir"
        )


if __name__ == "__main__":
    unittest.main()
