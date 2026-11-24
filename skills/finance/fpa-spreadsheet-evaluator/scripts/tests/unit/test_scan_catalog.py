"""
description: Unit tests for scan_catalog: every check has a known group and severity, judgment checks are never critical, area overrides, and Excel version tables agree. Filesystem-free.
last_updated: 2026-11-24

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import scan_catalog as SC  # noqa: E402


class TestCatalog(unittest.TestCase):
    def test_every_check_has_known_group_severity_and_a_fix(self):
        for check, (group, sev, fix) in SC.CHECKS.items():
            with self.subTest(check=check):
                self.assertIn(group, SC.AREA_OF_GROUP)
                self.assertIn(sev, SC.SEV_ORDER)
                self.assertTrue(fix.strip())

    def test_judgment_checks_exist_and_are_never_critical(self):
        for check in SC.JUDGMENT_CHECKS:
            with self.subTest(check=check):
                self.assertIn(check, SC.CHECKS)
                self.assertNotEqual(SC.CHECKS[check][1], "critical")

    def test_area_of_prefers_check_override_then_group(self):
        self.assertEqual(SC.area_of("hidden_sheet", "Risk"), "structure")
        self.assertEqual(SC.area_of("long_formula", "Risk"), "structure")
        self.assertEqual(SC.area_of("volatile_function", "Risk"), "formula")
        self.assertEqual(SC.area_of("anything", "No such group"), "formula")
        self.assertTrue(set(SC.AREA_OF_GROUP.values()) <= set(SC.AREAS))

    def test_function_versions_and_targets_use_known_versions(self):
        self.assertEqual(SC.FUNCTION_VERSION["XLOOKUP"], "2021")
        self.assertEqual(SC.FUNCTION_VERSION["LAMBDA"], "365")
        self.assertTrue(set(SC.FUNCTION_VERSION.values()) <= set(SC.VERSION_ORDER))
        targets = {v for v in SC.TARGETS.values() if v is not None}
        self.assertTrue(targets <= set(SC.VERSION_ORDER))


if __name__ == "__main__":
    unittest.main()
