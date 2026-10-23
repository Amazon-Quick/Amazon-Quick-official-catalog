"""
description: Append one skill run event (start or end) to a local SQLite metrics database so a user can query invocations, success rate, and duration per skill and workflow over time. Run as: python record_event.py <db_path> start --skill NAME --version CHECKSUM --workflow NAME, then python record_event.py <db_path> end --run-id ID --result completed|failed|stopped [--tool-calls N].
last_updated: 2026-10-22
origin: original

Standard library plus pydantic (in the sandbox manifest). A single self-contained
file: StartStatement and EndStatement turn an injected event into SQL (pure,
unit-tested); MetricsStore runs a statement against the database file (I/O);
EventRecorder is the facade main() calls. Each run is one row in the `runs`
table; the first row for a skill marks when it was installed.
"""

from __future__ import annotations

import argparse
import datetime
import logging
import sqlite3
import sys
import uuid
from contextlib import closing
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class _PrintStream:
    """Routes log records to stdout via print (the sandbox only returns stdout)."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=_PrintStream(),
    force=True,
)
logger = logging.getLogger(__name__)

CREATE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    skill TEXT NOT NULL,
    version TEXT NOT NULL,
    workflow TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    result TEXT,
    tool_calls INTEGER
)
"""
INSERT_RUN = (
    "INSERT INTO runs (run_id, skill, version, workflow, started_at) "
    "VALUES (?, ?, ?, ?, ?)"
)
UPDATE_RUN = (
    "UPDATE runs SET ended_at = ?, result = ?, tool_calls = ? "
    "WHERE run_id = ? AND ended_at IS NULL"
)
EXIT_UNKNOWN_RUN = 1
EXIT_BAD_PATH = 2


class EventKind(StrEnum):
    """Which point of a workflow run is being recorded."""

    START = "start"
    END = "end"


class RunResult(StrEnum):
    """How a workflow run finished."""

    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class StartEvent(BaseModel):
    """A workflow run beginning."""

    run_id: str
    skill: str = Field(min_length=1)
    version: str = Field(min_length=1)
    workflow: str = Field(min_length=1)
    started_at: str


class EndEvent(BaseModel):
    """A workflow run finishing."""

    run_id: str = Field(min_length=1)
    result: RunResult
    tool_calls: int | None = Field(default=None, ge=0)
    ended_at: str


class Statement(BaseModel):
    """One parameterized SQL statement."""

    sql: str
    params: list[str | int | None]


class StartStatement:
    """Builds the INSERT for a start event (pure)."""

    def __init__(self, event: StartEvent) -> None:
        self.event = event

    def build(self) -> Statement:
        """Return the INSERT that adds the run's row."""
        event = self.event
        return Statement(
            sql=INSERT_RUN,
            params=[
                event.run_id,
                event.skill,
                event.version,
                event.workflow,
                event.started_at,
            ],
        )


class EndStatement:
    """Builds the UPDATE for an end event (pure)."""

    def __init__(self, event: EndEvent) -> None:
        self.event = event

    def build(self) -> Statement:
        """Return the UPDATE that closes the run's row."""
        event = self.event
        return Statement(
            sql=UPDATE_RUN,
            params=[
                event.ended_at,
                event.result.value,
                event.tool_calls,
                event.run_id,
            ],
        )


class MetricsStore:
    """Runs one statement against the metrics database, creating it if needed (I/O)."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def execute(self, statement: Statement) -> int:
        """Run the statement and return how many rows it changed."""
        with closing(sqlite3.connect(self.db_path)) as connection:
            with connection:
                connection.execute(CREATE_RUNS_TABLE)
                cursor = connection.execute(statement.sql, statement.params)
            return cursor.rowcount


class EventRecorder:
    """Facade: write one event's statement to the metrics database."""

    def __init__(self, db_path: Path, statement: Statement) -> None:
        self.db_path = db_path
        self.statement = statement

    def record(self) -> int:
        """Write the statement and return how many rows it changed."""
        return MetricsStore(self.db_path).execute(self.statement)


def _now() -> str:
    """The current UTC time as an ISO 8601 string."""
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record a skill workflow run in a local SQLite database."
    )
    parser.add_argument("db_path", help="Path to the metrics database file.")
    sub = parser.add_subparsers(dest="kind", required=True)

    start = sub.add_parser(EventKind.START.value, help="Record a run starting.")
    start.add_argument("--skill", required=True, help="Skill name.")
    start.add_argument("--version", required=True, help="Skill checksum.")
    start.add_argument("--workflow", required=True, help="Workflow name.")

    end = sub.add_parser(EventKind.END.value, help="Record a run finishing.")
    end.add_argument("--run-id", required=True, help="ID printed by start.")
    end.add_argument("--result", required=True, choices=[r.value for r in RunResult])
    end.add_argument("--tool-calls", type=int, default=None)
    return parser


def _statement_for(args: argparse.Namespace) -> Statement:
    """Build the statement for the requested event kind."""
    match EventKind(args.kind):
        case EventKind.START:
            event = StartEvent(
                run_id=uuid.uuid4().hex,
                skill=args.skill,
                version=args.version,
                workflow=args.workflow,
                started_at=_now(),
            )
            return StartStatement(event).build()
        case EventKind.END:
            event = EndEvent(
                run_id=args.run_id,
                result=RunResult(args.result),
                tool_calls=args.tool_calls,
                ended_at=_now(),
            )
            return EndStatement(event).build()


def main() -> int:
    args = _build_parser().parse_args()

    db_path = Path(args.db_path)
    if not db_path.parent.is_dir():
        logger.error("Folder does not exist: %s", db_path.parent)
        return EXIT_BAD_PATH

    statement = _statement_for(args)
    changed = EventRecorder(db_path, statement).record()
    run_id = statement.params[0] if args.kind == EventKind.START else args.run_id
    if changed == 0:
        logger.error("No open run with id %s", run_id)
        return EXIT_UNKNOWN_RUN
    logger.info("run_id=%s recorded %s", run_id, args.kind)
    return 0


if __name__ == "__main__":
    sys.exit(main())
