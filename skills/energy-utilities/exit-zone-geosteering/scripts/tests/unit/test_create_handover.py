"""
description: Filesystem-free unit test proving a dangling observation reference blocks provenance integrity.
last_updated: 2026-09-14
origin: original
"""

import unittest

from create_handover import IntegrityChecker


class TestIntegrityChecker(unittest.TestCase):
    def test_flags_dangling_observation_reference(self) -> None:
        observations = [
            {
                "id": "SYN1:impact:1",
                "type": "impact_estimate",
                "wellbore_id": "SYN1",
                "source": [{"id": "SYN1:missing-delta"}],
                "ts": "2026-09-01T15:34:00.000Z",
            }
        ]

        result = IntegrityChecker(observations, "SYN1").check()

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.orphan_count, 1)
        self.assertEqual(
            result.orphans[0]["unresolved_sources"], ["SYN1:missing-delta"]
        )

    def test_run_uses_input_workspace_dir_without_environment(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from create_handover import run

        with TemporaryDirectory() as workspace:
            request = {"workspace_dir": workspace, "data_root": "data"}
            with (
                patch.dict("create_handover.os.environ", {}, clear=True),
                patch("create_handover.HandoverRunner") as runner,
            ):
                runner.return_value.run.return_value = {"type": "handover_note"}
                result = run(request)

        self.assertEqual(result, {"type": "handover_note"})
        runner.assert_called_once_with(Path(workspace).resolve() / "data", "SYN1")


if __name__ == "__main__":
    unittest.main()
