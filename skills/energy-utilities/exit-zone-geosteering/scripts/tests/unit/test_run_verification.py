"""
description: Filesystem-free golden-value unit test for pay-zone verification and confidence reasoning.
last_updated: 2026-09-14
origin: original
"""

import unittest

from create_synthetic_well import SyntheticWellBuilder
from run_verification import VerificationCalculator


class TestVerificationCalculator(unittest.TestCase):
    def test_reproduces_pay_delta_and_confidence(self) -> None:
        records = [
            record.__dict__ for record in SyntheticWellBuilder("SYN1", 19).build()
        ]
        zones = {
            "rows": [{"name": "TargetZone", "top_md": 10070.0, "base_md": 10100.0}]
        }
        offsets = {
            "rows": [{"well": "A", "agrees": True}, {"well": "B", "agrees": True}]
        }

        result = VerificationCalculator(records, zones, offsets).calculate()

        self.assertEqual(result.live_pay_ft, 35.0)
        self.assertEqual(result.model_pay_ft, 20.5)
        self.assertEqual(result.p50_delta_ft, 14.5)
        self.assertEqual(result.p30_delta_ft, 13.189)
        self.assertEqual(result.confidence, 0.917)
        self.assertEqual(result.threshold, 0.65)
        self.assertTrue(result.accepted)
        self.assertIn("A, B", result.reasoning)

    def test_run_uses_input_workspace_dir_without_environment(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from run_verification import run

        with TemporaryDirectory() as workspace:
            request = {"workspace_dir": workspace, "data_root": "data"}
            with (
                patch.dict("run_verification.os.environ", {}, clear=True),
                patch("run_verification.VerificationRunner") as runner,
            ):
                runner.return_value.run.return_value = {"type": "payzone_delta"}
                result = run(request)

        self.assertEqual(result, {"type": "payzone_delta"})
        runner.assert_called_once_with(Path(workspace).resolve() / "data", "SYN1")


if __name__ == "__main__":
    unittest.main()
