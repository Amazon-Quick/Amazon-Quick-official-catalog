"""
description: Filesystem-free unit test for the deterministic synthetic geosteering stream builder.
last_updated: 2026-09-15
origin: original
"""

import unittest

from create_synthetic_well import SyntheticTickAppender, SyntheticWellBuilder


class TestSyntheticWellBuilder(unittest.TestCase):
    def test_builds_reproducible_alert_tick_stream(self) -> None:
        first = SyntheticWellBuilder("SYN1", 19).build()
        second = SyntheticWellBuilder("SYN1", 19).build()

        self.assertEqual(first, second)
        self.assertEqual(len(first), 19)
        self.assertEqual(first[-1].depth_md, 10090.5)
        self.assertEqual(first[-1].ts, "2026-09-01T15:34:00.000Z")
        self.assertEqual(first[-1].channels["rop"], 60.0)

    def test_appends_exactly_one_deterministic_tick(self) -> None:
        records = SyntheticWellBuilder("SYN1", 14).build()

        appended = SyntheticTickAppender("SYN1", records).append()

        self.assertEqual(appended.id, "stream:SYN1:14")
        self.assertEqual(appended.depth_md, 10070.5)
        self.assertEqual(appended.ts, "2026-09-01T15:14:00.000Z")
        self.assertEqual(appended, SyntheticWellBuilder("SYN1", 15).build()[-1])

    def test_run_uses_input_workspace_dir_without_environment(self) -> None:
        from unittest.mock import patch

        from create_synthetic_well import run

        request = {"workspace_dir": "/explicit/workspace", "wellbore_id": "SYN1"}
        with (
            patch.dict("create_synthetic_well.os.environ", {}, clear=True),
            patch("create_synthetic_well.CreateSyntheticWell") as facade,
        ):
            facade.return_value.run.return_value = {"status": "created"}
            result = run(request)

        self.assertEqual(result, {"status": "created"})
        facade.assert_called_once_with(request, "/explicit/workspace")


if __name__ == "__main__":
    unittest.main()
