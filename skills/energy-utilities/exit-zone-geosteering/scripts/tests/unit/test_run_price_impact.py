"""
description: Filesystem-free golden-value unit test for deterministic correct-now and hold-three-stands economics.
last_updated: 2026-09-14
origin: original
"""

import unittest

from run_price_impact import ImpactCalculator


class TestImpactCalculator(unittest.TestCase):
    def test_reproduces_both_price_scenarios(self) -> None:
        scenarios = ImpactCalculator(
            pay_delta_ft=14.5, margin_ft=9.5, usd_per_bbl=78.5
        ).calculate()

        self.assertEqual(scenarios[0].scenario, "correct_now")
        self.assertEqual(scenarios[0].usd, 363825.0)
        self.assertEqual(scenarios[1].scenario, "hold_3_stands")
        self.assertEqual(scenarios[1].out_of_zone_ft, 5.5)
        self.assertEqual(scenarios[1].pay_delta_ft, 9.0)
        self.assertEqual(scenarios[1].usd, 320650.0)

    def test_run_uses_input_workspace_dir_without_environment(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from run_price_impact import run

        with TemporaryDirectory() as workspace:
            request = {"workspace_dir": workspace, "data_root": "data"}
            with (
                patch.dict("run_price_impact.os.environ", {}, clear=True),
                patch("run_price_impact.PriceImpactRunner") as runner,
            ):
                runner.return_value.run.return_value = {"type": "impact_estimate"}
                result = run(request)

        self.assertEqual(result, {"type": "impact_estimate"})
        runner.assert_called_once_with(Path(workspace).resolve() / "data", "SYN1")


if __name__ == "__main__":
    unittest.main()
