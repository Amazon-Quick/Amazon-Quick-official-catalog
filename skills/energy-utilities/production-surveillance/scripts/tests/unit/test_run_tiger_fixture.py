"""
description: Filesystem-free unit tests for the synthetic TIGER fixture analyzer, including reservoir diagnosis and safety-veto behavior.
last_updated: 2026-09-14
origin: original
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "run_tiger_fixture.py"
SPEC = importlib.util.spec_from_file_location("run_tiger_fixture", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

TigerFixtureAnalyzer = MODULE.TigerFixtureAnalyzer
TigerRequest = MODULE.TigerRequest


def _fixture() -> dict:
    return {
        "timestamp": "2026-08-07T14:30:12Z",
        "field": {"total_wells": 1},
        "summary": {"total_gas_production_mmscfd": 22},
        "manifolds": [{"manifold_id": "Manifold B", "status": "DEGRADED"}],
        "wells": [
            {
                "well_id": "SK-14",
                "manifold": "Manifold B",
                "measurements": {
                    "wellhead_pressure_psi": 4560,
                    "tubing_pressure_psi": 4780,
                    "annulus_pressure_psi": 1520,
                    "gas_rate_mmscfd": 22,
                    "water_rate_bwpd": 8200,
                    "water_cut_pct": 8.7,
                    "wellhead_temp_degc": 15.7,
                    "choke_position_pct": 65,
                    "meg_injection_rate_m3hr": 2.1,
                    "sand_rate_pptb": 0.85,
                },
                "status": "PRODUCING",
                "alarms": [
                    {
                        "alarm_id": "SYN-001",
                        "severity": "RED",
                        "type": "HYDRATE_RISK",
                        "message": "Synthetic hydrate-risk alarm.",
                        "triggered_at": "2026-08-07T13:45:00Z",
                    }
                ],
                "completion_type": "HORIZONTAL_FRAC",
                "water_depth_m": 2100,
                "total_depth_m": 4250,
            }
        ],
    }


class TigerFixtureAnalyzerTests(unittest.TestCase):
    def test_sk14_constraint_and_safety_results_are_review_only(self) -> None:
        analyzer = TigerFixtureAnalyzer(_fixture())

        reservoir = analyzer.execute(
            TigerRequest(
                operation="reservoir_constraints", arguments={"well_id": "SK-14"}
            )
        )
        safety = analyzer.execute(
            TigerRequest(
                operation="safety_compliance",
                arguments={
                    "well_id": "SK-14",
                    "proposed_action": "Evaluate MEG injection through the approved process",
                    "action_class": "chemical",
                },
            )
        )

        self.assertEqual(reservoir["status"], "success")
        self.assertAlmostEqual(reservoir["drawdown"]["fbhp_psi"], 6473, delta=1)
        self.assertEqual(
            reservoir["decline_diagnosis"]["diagnosis"], "DOWNSTREAM_RESTRICTION"
        )
        self.assertEqual(
            reservoir["water"]["water_trend_basis"], "60_minute_window_only"
        )
        self.assertEqual(safety["status"], "success")
        self.assertFalse(safety["blocking"])
        self.assertEqual(safety["execution_status"], "not_executed")
        self.assertEqual(safety["precedent"]["precedent_basis"], "active_alarm_set")


class RunEntryPointTests(unittest.TestCase):
    def test_run_returns_dict_and_reports_missing_fixture(self) -> None:
        from run_tiger_fixture import run

        result = run({"operation": "alarms", "arguments": {"severity": "all"}})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["code"], "INPUT_ERROR")


if __name__ == "__main__":
    unittest.main()
