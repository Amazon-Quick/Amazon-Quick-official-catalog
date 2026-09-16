"""
description: Filesystem-free golden-value unit test for trajectory-derived zone-exit projection and urgency tier.
last_updated: 2026-09-15
origin: original
"""

import unittest

from create_synthetic_well import SyntheticTickAppender, SyntheticWellBuilder
from run_zone_exit import ExitProjectionCalculator


class TestExitProjectionCalculator(unittest.TestCase):
    def test_reproduces_exit_eta_and_margin(self) -> None:
        records = [
            record.__dict__ for record in SyntheticWellBuilder("SYN1", 19).build()
        ]
        zones = {
            "rows": [{"name": "TargetZone", "top_md": 10070.0, "base_md": 10100.0}]
        }

        result = ExitProjectionCalculator(records, zones).calculate()

        self.assertEqual(result.depth_md, 10090.5)
        self.assertEqual(result.margin_ft, 9.5)
        self.assertEqual(result.rate_ft_per_hr, 60.0)
        self.assertEqual(result.eta_minutes, 9.5)
        self.assertEqual(result.severity, "Escalate")

    def test_replay_tick_first_enters_warn(self) -> None:
        records = SyntheticWellBuilder("SYN1", 14).build()
        records.append(SyntheticTickAppender("SYN1", records).append())
        zones = {
            "rows": [{"name": "TargetZone", "top_md": 10070.0, "base_md": 10100.0}]
        }

        result = ExitProjectionCalculator(
            [record.__dict__ for record in records], zones
        ).calculate()

        self.assertEqual(result.depth_md, 10070.5)
        self.assertEqual(result.margin_ft, 29.5)
        self.assertEqual(result.eta_minutes, 29.5)
        self.assertEqual(result.severity, "Warn")

    def test_twelve_record_reseed_progresses_through_all_tiers(self) -> None:
        records = SyntheticWellBuilder("SYN1", 12).build()
        zones = {
            "rows": [{"name": "TargetZone", "top_md": 10070.0, "base_md": 10100.0}]
        }
        first_tick_by_tier = {
            ExitProjectionCalculator([record.__dict__ for record in records], zones)
            .calculate()
            .severity: 0
        }

        for tick in range(1, 8):
            records.append(SyntheticTickAppender("SYN1", records).append())
            severity = (
                ExitProjectionCalculator([record.__dict__ for record in records], zones)
                .calculate()
                .severity
            )
            first_tick_by_tier.setdefault(severity, tick)

        self.assertEqual(first_tick_by_tier, {"Watch": 0, "Warn": 3, "Escalate": 7})

    def test_run_uses_input_workspace_dir_without_environment(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from run_zone_exit import run

        with TemporaryDirectory() as workspace:
            request = {"workspace_dir": workspace, "data_root": "data"}
            with (
                patch.dict("run_zone_exit.os.environ", {}, clear=True),
                patch("run_zone_exit.ZoneExitRunner") as runner,
            ):
                runner.return_value.run.return_value = {"status": "no_alert"}
                result = run(request)

        self.assertEqual(result, {"status": "no_alert"})
        runner.assert_called_once_with(Path(workspace).resolve() / "data", "SYN1")


if __name__ == "__main__":
    unittest.main()
