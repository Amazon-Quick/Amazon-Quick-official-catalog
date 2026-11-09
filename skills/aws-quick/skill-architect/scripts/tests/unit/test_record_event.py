"""
description: Unit tests for record_event.py. Filesystem-free: StartStatement and EndStatement are given injected events, so the SQL and parameters for each run event are verified without opening a database.
last_updated: 2026-10-22
origin: original

Run: PYTHONPATH=scripts python -m unittest discover -s scripts/tests/unit -p "test_*.py"
"""

import unittest

from pydantic import ValidationError
from record_event import (
    INSERT_RUN,
    UPDATE_RUN,
    EndEvent,
    EndStatement,
    RunResult,
    StartEvent,
    StartStatement,
)


def _start() -> StartEvent:
    return StartEvent(
        run_id="abc",
        skill="skill-architect",
        version="sha256:x",
        workflow="Plan",
        started_at="2026-10-22T10:00:00+00:00",
    )


def _end(tool_calls: int | None = 7) -> EndEvent:
    return EndEvent(
        run_id="abc",
        result=RunResult.COMPLETED,
        tool_calls=tool_calls,
        ended_at="2026-10-22T10:05:00+00:00",
    )


class TestStartStatement(unittest.TestCase):
    def test_build_start_event_inserts_run_row(self) -> None:
        statement = StartStatement(_start()).build()
        self.assertEqual(statement.sql, INSERT_RUN)
        self.assertEqual(
            statement.params,
            ["abc", "skill-architect", "sha256:x", "Plan", "2026-10-22T10:00:00+00:00"],
        )

    def test_start_event_rejects_empty_skill(self) -> None:
        with self.assertRaises(ValidationError):
            StartEvent(
                run_id="abc",
                skill="",
                version="v",
                workflow="Plan",
                started_at="2026-10-22T10:00:00+00:00",
            )


class TestEndStatement(unittest.TestCase):
    def test_build_end_event_updates_open_run(self) -> None:
        statement = EndStatement(_end()).build()
        self.assertEqual(statement.sql, UPDATE_RUN)
        self.assertEqual(
            statement.params,
            ["2026-10-22T10:05:00+00:00", "completed", 7, "abc"],
        )

    def test_build_end_event_without_tool_calls_stores_null(self) -> None:
        statement = EndStatement(_end(tool_calls=None)).build()
        self.assertIsNone(statement.params[2])

    def test_end_event_rejects_negative_tool_calls(self) -> None:
        with self.assertRaises(ValidationError):
            _end(tool_calls=-1)


if __name__ == "__main__":
    unittest.main()
