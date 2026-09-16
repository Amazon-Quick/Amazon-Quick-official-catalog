"""
description: Filesystem-free unit tests for deterministic petrophysics formulas and the locked synthetic hydrate-margin result.
last_updated: 2026-09-14
origin: original
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "run_petrophysics.py"
SPEC = importlib.util.spec_from_file_location("run_petrophysics", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PetrophysicsCalculator = MODULE.PetrophysicsCalculator
PetrophysicsRequest = MODULE.PetrophysicsRequest


class PetrophysicsCalculatorTests(unittest.TestCase):
    def test_golden_hydrate_and_log_calculations(self) -> None:
        hydrate = PetrophysicsCalculator(
            PetrophysicsRequest(
                operation="hydrate_equilibrium",
                arguments={
                    "pressure_psi": 4560,
                    "meg_weight_pct": 21.5,
                    "current_temp_degc": 15.7,
                },
            )
        ).calculate()
        density = PetrophysicsCalculator(
            PetrophysicsRequest(
                operation="density_porosity",
                arguments={"bulk_density_gcc": [2.65, 2.32, 1.0]},
            )
        ).calculate()
        shale = PetrophysicsCalculator(
            PetrophysicsRequest(
                operation="shale_volume",
                arguments={
                    "gamma_ray_gapi": [30.0, 90.0, 150.0],
                    "clean_gr_gapi": 30.0,
                    "shale_gr_gapi": 150.0,
                },
            )
        ).calculate()
        saturation = PetrophysicsCalculator(
            PetrophysicsRequest(
                operation="archie_water_saturation",
                arguments={
                    "true_resistivity_ohm_m": [10.0],
                    "total_porosity_fraction": [0.2],
                    "water_resistivity_ohm_m": 0.1,
                },
            )
        ).calculate()

        self.assertAlmostEqual(hydrate["inhibited_equilibrium_degc"], 14.22, delta=0.05)
        self.assertAlmostEqual(hydrate["signed_scenario_margin_degc"], 1.48, delta=0.05)
        self.assertEqual(hydrate["risk_band"], "HIGH")
        self.assertEqual(density["density_porosity_fraction"], [0.0, 0.2, 1.0])
        self.assertEqual(shale["shale_volume_fraction"], [0.0, 0.5, 1.0])
        self.assertEqual(saturation["water_saturation_fraction"], [0.5])


class RunEntryPointTests(unittest.TestCase):
    def test_run_reproduces_hydrate_golden_values(self) -> None:
        from run_petrophysics import run

        result = run(
            {
                "operation": "hydrate_equilibrium",
                "arguments": {
                    "pressure_psi": 4560,
                    "current_temp_degc": 15.7,
                    "meg_weight_pct": 21.5,
                },
            }
        )
        self.assertEqual(result["status"], "success")
        self.assertAlmostEqual(result["inhibited_equilibrium_degc"], 14.22, places=2)
        self.assertEqual(result["risk_band"], "HIGH")


if __name__ == "__main__":
    unittest.main()
