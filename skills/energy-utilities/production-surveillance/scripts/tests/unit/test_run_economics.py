"""
description: Filesystem-free unit tests for production economics, locking the synthetic current-deferral and full-well-exposure values.
last_updated: 2026-09-14
origin: original
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "run_economics.py"
SPEC = importlib.util.spec_from_file_location("run_economics", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

EconomicsCalculator = MODULE.EconomicsCalculator
EconomicsRequest = MODULE.EconomicsRequest


class EconomicsCalculatorTests(unittest.TestCase):
    def test_golden_daily_deferral_and_exposure_values(self) -> None:
        assumptions = {"gas_price_per_mmbtu": 3.5, "btu_per_scf": 1050.0}
        current_deferral = EconomicsCalculator(
            EconomicsRequest(
                operation="deferred_production",
                arguments={
                    **assumptions,
                    "shut_in_wells": [],
                    "constrained_wells": [
                        {
                            "well_id": "SK-14",
                            "current_rate_mmscfd": 22.0,
                            "potential_rate_mmscfd": 38.0,
                        }
                    ],
                },
            )
        ).calculate()
        full_exposure = EconomicsCalculator(
            EconomicsRequest(
                operation="deferred_production",
                arguments={
                    **assumptions,
                    "shut_in_wells": [
                        {"well_id": "SK-14", "potential_rate_mmscfd": 38.0}
                    ],
                    "constrained_wells": [],
                },
            )
        ).calculate()
        field_revenue = EconomicsCalculator(
            EconomicsRequest(
                operation="daily_revenue",
                arguments={
                    **assumptions,
                    "gas_rate_mmscfd": 1004.0,
                    "condensate_bpd": 68000.0,
                    "condensate_price_per_bbl": 72.5,
                },
            )
        ).calculate()

        self.assertEqual(current_deferral["total_deferred_mmscfd"], 16.0)
        self.assertEqual(current_deferral["total_deferred_value_usd_per_day"], 58800.0)
        self.assertEqual(full_exposure["total_deferred_value_usd_per_day"], 139650.0)
        self.assertEqual(
            field_revenue["revenue_breakdown"]["total_daily_revenue_usd"],
            8619700.0,
        )


class RunEntryPointTests(unittest.TestCase):
    def test_run_reproduces_deferral_golden_value(self) -> None:
        from run_economics import run

        result = run(
            {
                "operation": "deferred_production",
                "arguments": {
                    "gas_price_per_mmbtu": 3.5,
                    "btu_per_scf": 1050,
                    "constrained_wells": [
                        {
                            "well_id": "SK-14",
                            "current_rate_mmscfd": 22,
                            "potential_rate_mmscfd": 38,
                        }
                    ],
                },
            }
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_deferred_value_usd_per_day"], 58800.0)


if __name__ == "__main__":
    unittest.main()
