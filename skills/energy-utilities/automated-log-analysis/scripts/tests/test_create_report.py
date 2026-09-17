"""
description: Test deterministic Word and Markdown report generation from evaluated log data.
last_updated: 2026-09-16
origin: original
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import zipfile
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
    "report_test_create",
    "skills/energy-utilities/automated-log-analysis/scripts/create_synthetic_las.py",
)
PARSE = _load(
    "report_test_parse",
    "skills/energy-utilities/automated-log-analysis/scripts/run_las_parse.py",
)
EVALUATE = _load(
    "report_test_evaluate",
    "skills/energy-utilities/automated-log-analysis/scripts/run_evaluation.py",
)
PLOT = _load(
    "report_test_plot",
    "skills/energy-utilities/automated-log-analysis/scripts/create_log_plot.py",
)
REPORT = _load(
    "create_report",
    "skills/energy-utilities/automated-log-analysis/scripts/create_report.py",
)


class TestCreateReport(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_report_creates_docx_and_markdown_with_supplied_recommendations(
        self,
    ) -> None:
        created = CREATE.run({"workspace_dir": str(self.workspace)})
        PARSE.run(
            {"workspace_dir": str(self.workspace), "las_path": created["relative_path"]}
        )
        EVALUATE.run({"workspace_dir": str(self.workspace)})
        PLOT.run({"workspace_dir": str(self.workspace)})
        result = REPORT.run(
            {
                "workspace_dir": str(self.workspace),
                "recommendations": [
                    "Validate formation-water resistivity before booking reserves."
                ],
            }
        )

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["warnings"], [])
        self.assertTrue(Path(result["docx_path"]).is_file())
        markdown_path = Path(result["markdown_path"])
        self.assertTrue(markdown_path.is_file())
        markdown = markdown_path.read_text(encoding="utf-8")
        self.assertIn(
            "Validate formation-water resistivity before booking reserves.", markdown
        )
        self.assertIn("195437364.0 STB", markdown)
        self.assertIn("| Drainage area (acres) | 500.0 |", markdown)
        self.assertNotIn("| area_acres |", markdown)
        with zipfile.ZipFile(result["docx_path"]) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Drainage area (acres)", document_xml)
        self.assertIn("Thickness (ft)", document_xml)
        self.assertNotIn(">zone_id<", document_xml)
        self.assertNotIn(">area_acres<", document_xml)

    def test_no_resistivity_report_states_limited_accuracy(self) -> None:
        created = CREATE.run(
            {"workspace_dir": str(self.workspace), "mode": "no_resistivity"}
        )
        PARSE.run(
            {"workspace_dir": str(self.workspace), "las_path": created["relative_path"]}
        )
        evaluation = EVALUATE.run({"workspace_dir": str(self.workspace)})
        self.assertFalse(evaluation["net_pay_summary"]["sw_cutoff_applied"])
        result = REPORT.run(
            {"workspace_dir": str(self.workspace), "recommendations": []}
        )

        self.assertEqual(result["status"], "created")
        markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
        self.assertNotIn("| None |", markdown)
        self.assertNotIn("None STB", markdown)
        self.assertNotIn("SW: None", markdown)
        self.assertIn("porosity and shale cutoffs only; limited accuracy", markdown)
        self.assertIn("Average pay SW: n/a (no resistivity)", markdown)
        self.assertIn("OOIP: not estimated (OOIP requires water saturation", markdown)
        with zipfile.ZipFile(result["docx_path"]) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
        self.assertNotIn(">None<", document_xml)
        self.assertIn("limited accuracy", document_xml)
        self.assertIn("n/a (no resistivity)", document_xml)


if __name__ == "__main__":
    unittest.main()
