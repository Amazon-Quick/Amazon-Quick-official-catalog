"""
description: Test locked petrophysics values and graceful no-resistivity evaluation.
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
    "evaluation_test_create",
    "skills/energy-utilities/automated-log-analysis/scripts/create_synthetic_las.py",
)
PARSE = _load(
    "evaluation_test_parse",
    "skills/energy-utilities/automated-log-analysis/scripts/run_las_parse.py",
)
EVALUATE = _load(
    "run_evaluation",
    "skills/energy-utilities/automated-log-analysis/scripts/run_evaluation.py",
)


class TestRunEvaluation(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _evaluate(self, mode: str = "create") -> dict[str, Any]:
        created = CREATE.run({"workspace_dir": str(self.workspace), "mode": mode})
        parsed = PARSE.run(
            {"workspace_dir": str(self.workspace), "las_path": created["relative_path"]}
        )
        self.assertEqual(parsed["status"], "success")
        return EVALUATE.run({"workspace_dir": str(self.workspace)})

    def test_evaluation_matches_locked_synthetic_golden_values(self) -> None:
        result = self._evaluate()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["gr_baselines"]["clean_gr"], 35.0)
        self.assertEqual(result["gr_baselines"]["shaley_gr"], 120.0)
        self.assertEqual(result["net_pay_summary"]["net_pay_ft"], 325.0)
        self.assertEqual(result["net_pay_summary"]["net_to_gross"], 0.433)
        self.assertEqual(result["net_pay_summary"]["avg_phie_pay"], 0.2286)
        self.assertEqual(result["net_pay_summary"]["avg_sw_pay"], 0.1184)
        self.assertEqual(
            [(zone["top"], zone["base"]) for zone in result["zones"]],
            [(8100.0, 8199.5), (8300.0, 8424.5), (8550.0, 8649.5)],
        )
        self.assertEqual(result["ooip"]["ooip_stb"], 195437364.0)
        self.assertEqual(result["ooip"]["recoverable_stb"], 68403077.0)
        self.assertEqual(result["qc_summary"]["overall_quality"], "good")

    def test_no_resistivity_returns_null_sw_and_warning(self) -> None:
        result = self._evaluate(mode="no_resistivity")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["warnings"], ["RT not found; water saturation skipped"])
        self.assertTrue(all(value is None for value in result["sample_columns"]["SW"]))
        summary = result["net_pay_summary"]
        self.assertEqual(summary["net_pay_ft"], 325.0)
        self.assertIsNone(summary["avg_sw_pay"])
        self.assertFalse(summary["sw_cutoff_applied"])
        self.assertTrue(summary["accuracy"].startswith("limited"))
        self.assertIsNone(result["ooip"]["ooip_stb"])
        self.assertTrue(all(zone["avg_sw"] is None for zone in result["zones"]))


if __name__ == "__main__":
    unittest.main()
