"""
description: Filesystem-free unit tests for chart-ready dashboard projection and the plain-HTML fallback.
last_updated: 2026-09-15
origin: original
"""

import json
import unittest

from create_dashboard import DashboardDataBuilder, DashboardRenderer


class TestDashboardDataBuilder(unittest.TestCase):
    def test_builds_honest_empty_state(self) -> None:
        result = DashboardDataBuilder("SYN1", {"observations": []}).build()

        self.assertTrue(result.empty)
        self.assertEqual(result.observation_count, 0)
        self.assertIn("No geosteering observations yet", result.message)
        self.assertEqual(result.zone_status, {"status": "unknown"})

    def test_projects_required_chart_series(self) -> None:
        verification = {
            "id": "SYN1:payzone_delta:10070.5",
            "type": "payzone_delta",
            "value": {"p50_delta_ft": 9.5},
            "confidence": 0.81,
            "reasoning": "cited verification",
            "source": [{"id": "stream:SYN1:14"}],
            "depth_md": 10070.5,
            "ts": "2026-09-01T15:14:00.000Z",
        }
        alert = {
            "id": "SYN1:exit:TargetZone:10100.0",
            "type": "exit_alert",
            "value": {
                "severity": "Warn",
                "eta_minutes": 29.5,
                "margin_ft": 29.5,
                "boundary_zone": "TargetZone",
                "boundary_md": 10100.0,
            },
            "confidence": 0.81,
            "reasoning": "cited warning",
            "source": [{"id": verification["id"]}],
            "depth_md": 10070.5,
            "ts": "2026-09-01T15:14:00.000Z",
        }
        observations = [verification, alert]
        state = {
            "observations": observations,
            "latest_by_type": {"payzone_delta": verification, "exit_alert": alert},
            "zone_status": {"status": "exit_warning"},
        }
        stream = [
            {"depth_md": 10065.5, "channels": {"gr": 41.0, "rop": 60.0}},
            {"depth_md": 10070.5, "channels": {"gr": 44.0, "rop": 60.0}},
        ]
        zones = {
            "rows": [{"name": "TargetZone", "top_md": 10070.0, "base_md": 10100.0}]
        }

        result = DashboardDataBuilder("SYN1", state, stream, zones).build()

        self.assertEqual(result.lwd_curves["gr"], [[10065.5, 41.0], [10070.5, 44.0]])
        self.assertEqual(
            result.trajectory[-1], {"section_ft": 5.0, "depth_md": 10070.5}
        )
        self.assertEqual(result.zone_bands[0]["to_md"], 10100.0)
        self.assertEqual(result.confidence_trend[0]["confidence"], 0.81)
        self.assertEqual(result.alert_feed[0]["tier"], "Warn")

    def test_fallback_contains_parseable_projected_json(self) -> None:
        result = DashboardDataBuilder("SYN1", {"observations": []}).build()
        rendered = DashboardRenderer(
            '<script type="application/json">__GEOSTEERING_DATA__</script>', result
        ).render()
        payload = rendered.split(">", 1)[1].rsplit("<", 1)[0]

        self.assertEqual(json.loads(payload)["wellbore_id"], "SYN1")
        self.assertNotIn("__GEOSTEERING_DATA__", rendered)

    def test_run_uses_input_workspace_dir_without_environment(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from create_dashboard import run

        with TemporaryDirectory() as workspace:
            request = {
                "workspace_dir": workspace,
                "data_root": "data",
                "template": "<html>template</html>",
            }
            with (
                patch.dict("create_dashboard.os.environ", {}, clear=True),
                patch("create_dashboard.DashboardRunner") as runner,
            ):
                runner.return_value.run.return_value = {"status": "projected"}
                result = run(request)

        self.assertEqual(result, {"status": "projected"})
        runner.assert_called_once_with(
            Path(workspace).resolve() / "data", "SYN1", "<html>template</html>"
        )


if __name__ == "__main__":
    unittest.main()
