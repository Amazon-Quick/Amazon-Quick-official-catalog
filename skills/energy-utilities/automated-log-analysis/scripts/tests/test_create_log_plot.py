"""
description: Test five-track composite log rendering and the two-megabyte output limit.
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
    "plot_test_create",
    "skills/energy-utilities/automated-log-analysis/scripts/create_synthetic_las.py",
)
PARSE = _load(
    "plot_test_parse",
    "skills/energy-utilities/automated-log-analysis/scripts/run_las_parse.py",
)
EVALUATE = _load(
    "plot_test_evaluate",
    "skills/energy-utilities/automated-log-analysis/scripts/run_evaluation.py",
)
PLOT = _load(
    "create_log_plot",
    "skills/energy-utilities/automated-log-analysis/scripts/create_log_plot.py",
)


class TestCreateLogPlot(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_log_plot_exists_and_is_under_two_megabytes(self) -> None:
        created = CREATE.run({"workspace_dir": str(self.workspace)})
        PARSE.run(
            {
                "workspace_dir": str(self.workspace),
                "las_path": created["relative_path"],
            }
        )
        EVALUATE.run({"workspace_dir": str(self.workspace)})

        result = PLOT.run({"workspace_dir": str(self.workspace)})

        self.assertEqual(result["status"], "created")
        self.assertTrue(Path(result["path"]).is_file())
        self.assertLess(result["bytes"], 2 * 1024 * 1024)
        self.assertIn(result["dpi"], {100, 150})


if __name__ == "__main__":
    unittest.main()
