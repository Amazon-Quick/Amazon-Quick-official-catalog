"""
description: Filesystem-light unit tests for LAS 2.0 parsing, null handling, aliases, unit conversion, unsupported variants, and the locked synthetic SK-14 inventory.
last_updated: 2026-09-15
origin: original
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "run_las_reader.py"
SPEC = importlib.util.spec_from_file_location("run_las_reader", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

AliasResolver = MODULE.AliasResolver
CurveReader = MODULE.CurveReader
ErrorCode = MODULE.ErrorCode
LasParser = MODULE.LasParser
LasReaderError = MODULE.LasReaderError

INLINE_LAS = """~Version Information
 VERS. 2.0 : LAS version
 WRAP. NO : one row per depth
~Well Information
 NULL. -999.25 : null value
 WELL. INLINE-1 : well name
~Curve Information
 DEPT.M : measured depth
 SGR.GAPI : gamma ray
 TNPH.PU : neutron porosity
 DEN.G/C3 : bulk density
 RILD.OHMM : deep resistivity
~ASCII
 100.0 30.0 20.0 2.30 10.0
 101.0 -999.25 25.0 2.40 20.0
"""


class LasReaderTests(unittest.TestCase):
    def test_inline_parse_null_aliases_and_unit_conversion(self) -> None:
        document = LasParser(INLINE_LAS).parse()
        result = CurveReader(document, 100.0, 101.0).read()
        aliases = AliasResolver(["SGR", "TNPH", "DEN", "RILD"]).resolve()

        self.assertEqual(document.version, "2.0")
        self.assertEqual(document.wrap, "NO")
        self.assertEqual(result["curves"]["SGR"], [30.0, None])
        self.assertEqual(result["canonical_curves"]["GR"], [30.0, None])
        self.assertEqual(result["canonical_curves"]["NPHI"], [0.2, 0.25])
        self.assertEqual(result["canonical_curves"]["RHOB"], [2.3, 2.4])
        self.assertEqual(result["canonical_curves"]["RT"], [10.0, 20.0])
        self.assertAlmostEqual(result["canonical_curves"]["DEPTH"][0], 328.084)
        self.assertEqual(result["canonical_units"]["DEPTH"], "FT")
        self.assertEqual(
            [item["canonical_name"] for item in aliases],
            ["GR", "NPHI", "RHOB", "RT"],
        )

    def test_unsupported_wrap_and_version_have_documented_codes(self) -> None:
        wrapped = INLINE_LAS.replace("WRAP. NO", "WRAP. YES")
        version_three = INLINE_LAS.replace("VERS. 2.0", "VERS. 3.0")

        with self.assertRaises(LasReaderError) as wrapped_error:
            LasParser(wrapped).parse()
        with self.assertRaises(LasReaderError) as version_error:
            LasParser(version_three).parse()

        self.assertEqual(
            wrapped_error.exception.code, ErrorCode.WRAPPED_LAS_UNSUPPORTED
        )
        self.assertEqual(
            version_error.exception.code, ErrorCode.UNSUPPORTED_LAS_VERSION
        )

    def test_sk14_curve_inventory(self) -> None:
        skill_root = Path(__file__).resolve().parents[3]
        text = (skill_root / "evals" / "files" / "SK-14.las").read_text(
            encoding="utf-8"
        )
        document = LasParser(text).parse()

        self.assertEqual(
            [
                (curve.mnemonic, curve.unit, curve.description)
                for curve in document.curves
            ],
            [
                ("DEPT", "M", "MEASURED DEPTH"),
                ("GR", "GAPI", "GAMMA RAY"),
                ("NPHI", "V/V", "THERMAL NEUTRON POROSITY"),
                ("RHOB", "G/CC", "BULK DENSITY"),
                ("DT", "US/FT", "COMPRESSIONAL SONIC TRANSIT TIME"),
                ("CALI", "IN", "CALIPER"),
                ("ILD", "OHMM", "DEEP INDUCTION RESISTIVITY"),
            ],
        )
        self.assertEqual(document.null_value, -999.25)


class RunEntryPointTests(unittest.TestCase):
    def test_run_requires_workspace_dir_when_env_absent(self) -> None:
        import os

        from run_las_reader import run

        saved = os.environ.pop("WORKSPACE_DIR", None)
        try:
            result = run({"operation": "read_metadata", "arguments": {"path": "x.las"}})
        finally:
            if saved is not None:
                os.environ["WORKSPACE_DIR"] = saved
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "WORKSPACE_DIR_MISSING")

    def test_run_resolves_cali_to_cali_not_rt(self) -> None:
        from run_las_reader import run

        result = run(
            {
                "operation": "resolve_aliases",
                "arguments": {"mnemonics": ["CALI", "ILD"]},
            }
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mapping"]["CALI"], "CALI")
        self.assertEqual(result["mapping"]["ILD"], "RT")


if __name__ == "__main__":
    unittest.main()
