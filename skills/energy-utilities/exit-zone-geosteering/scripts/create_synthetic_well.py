"""
description: Create a deterministic synthetic geosteering well, reference pack, JSONL stream, and initial read model inside the Amazon Quick workspace.
last_updated: 2026-09-15
origin: original
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

WELLBORE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_WELLBORE_ID = "SYN1"
DEFAULT_DATA_ROOT = "exit-zone-geosteering-data"
DEFAULT_TICKS = 19
START_DEPTH_FT = 10000.5
DEPTH_PER_TICK_FT = 5.0
MINUTES_PER_TICK = 5.0
ROP_FT_PER_HR = 60.0
GAMMA_SEED = 20260817
GAMMA_MIN_API = 35.0
GAMMA_MAX_API = 60.0
BASE_TIME = datetime(2026, 9, 1, 14, 4, tzinfo=UTC)


class Mode(StrEnum):
    CREATE = "create"
    APPEND_TICK = "append_tick"


class _PrintStream:
    """Route logging to stdout, the stream returned by the sandbox."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO, format="%(message)s", stream=_PrintStream(), force=True
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StreamRecord:
    wellbore_id: str
    depth_md: float
    ts: str
    channels: dict[str, float]
    id: str


class SyntheticWellBuilder:
    """Build one deterministic stream from injected configuration."""

    def __init__(self, wellbore_id: str, ticks: int) -> None:
        self._wellbore_id = wellbore_id
        self._ticks = ticks

    def build(self) -> list[StreamRecord]:
        if not WELLBORE_ID_PATTERN.fullmatch(self._wellbore_id):
            raise ValueError("wellbore_id must match ^[A-Za-z0-9._-]+$")
        if self._ticks < 2 or self._ticks > 10000:
            raise ValueError("ticks must be between 2 and 10000")
        return [self._record(tick) for tick in range(self._ticks)]

    def _record(self, tick: int) -> StreamRecord:
        stamp = BASE_TIME + timedelta(minutes=MINUTES_PER_TICK * tick)
        gamma = random.Random(GAMMA_SEED + tick).uniform(  # nosec B311 - seeded synthetic jitter, not security randomness
            GAMMA_MIN_API, GAMMA_MAX_API
        )
        return StreamRecord(
            wellbore_id=self._wellbore_id,
            depth_md=round(START_DEPTH_FT + DEPTH_PER_TICK_FT * tick, 3),
            ts=stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            channels={"gr": round(gamma, 3), "rop": ROP_FT_PER_HR},
            id=f"stream:{self._wellbore_id}:{tick}",
        )


class SyntheticTickAppender:
    """Build the one deterministic record that follows an existing stream."""

    def __init__(self, wellbore_id: str, records: list[StreamRecord]) -> None:
        self._wellbore_id = wellbore_id
        self._records = records

    def append(self) -> StreamRecord:
        if not self._records:
            raise ValueError("append_tick requires an existing non-empty stream")
        if any(record.wellbore_id != self._wellbore_id for record in self._records):
            raise ValueError("stream contains a different wellbore_id")
        next_index = len(self._records)
        if next_index >= 10000:
            raise ValueError("stream cannot exceed 10000 records")
        return SyntheticWellBuilder(self._wellbore_id, next_index + 1).build()[-1]


class WorkspaceRootResolver:
    """Resolve a relative data root below WORKSPACE_DIR."""

    def __init__(self, workspace_dir: str, requested_root: str) -> None:
        self._workspace_dir = workspace_dir
        self._requested_root = requested_root

    def resolve(self) -> Path:
        workspace = Path(self._workspace_dir).resolve()
        requested = Path(self._requested_root)
        if requested.is_absolute():
            raise ValueError("data_root must be relative to WORKSPACE_DIR")
        resolved = (workspace / requested).resolve()
        if resolved != workspace and workspace not in resolved.parents:
            raise ValueError("data_root escapes WORKSPACE_DIR")
        return resolved


class SyntheticWellWriter:
    """Write the stream, references, empty sink, and initial read model."""

    def __init__(
        self,
        root: Path,
        wellbore_id: str,
        records: list[StreamRecord],
        refs: dict[str, Any],
    ) -> None:
        self._root = root
        self._wellbore_id = wellbore_id
        self._records = records
        self._refs = refs

    def write(self) -> dict[str, Any]:
        well_dir = self._root / "wells" / self._wellbore_id
        ref_dir = self._root / "references"
        state_dir = well_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        ref_dir.mkdir(parents=True, exist_ok=True)
        self._write_jsonl(
            well_dir / "stream.jsonl", [asdict(record) for record in self._records]
        )
        self._write_jsonl(well_dir / "observations.jsonl", [])
        for name in ("offsets", "price_deck", "zone_tops"):
            payload = self._refs.get(name)
            if not isinstance(payload, dict):
                raise ValueError(f"missing reference payload: {name}")
            self._write_json(ref_dir / f"{name}.json", payload)
        self._write_json(
            state_dir / "latest.json",
            {
                "count": 0,
                "observations": [],
                "latest": None,
                "latest_by_type": {},
                "zone_status": {"status": "unknown", "basis": None, "as_of": None},
            },
        )
        return {
            "status": "created",
            "wellbore_id": self._wellbore_id,
            "records": len(self._records),
            "data_root": str(self._root),
        }

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n"
        )

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        body = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)
        path.write_text(body, encoding="utf-8", newline="\n")


class SyntheticTickWriter:
    """Append one deterministic record to an existing confined well stream."""

    def __init__(self, root: Path, wellbore_id: str) -> None:
        self._root = root
        self._wellbore_id = wellbore_id

    def write(self) -> dict[str, Any]:
        stream_path = self._root / "wells" / self._wellbore_id / "stream.jsonl"
        rows = [
            json.loads(line)
            for line in stream_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        records = [StreamRecord(**row) for row in rows]
        record = SyntheticTickAppender(self._wellbore_id, records).append()
        with stream_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(asdict(record), separators=(",", ":")) + "\n")
        return {
            "status": "appended",
            "wellbore_id": self._wellbore_id,
            "records": len(records) + 1,
            "record": asdict(record),
            "data_root": str(self._root),
        }


class CreateSyntheticWell:
    """Facade that validates input, builds records, and writes the data root."""

    def __init__(self, request: dict[str, Any], workspace_dir: str) -> None:
        self._request = request
        self._workspace_dir = workspace_dir

    def run(self) -> dict[str, Any]:
        wellbore_id = str(self._request.get("wellbore_id", DEFAULT_WELLBORE_ID))
        root = WorkspaceRootResolver(
            self._workspace_dir, str(self._request.get("data_root", DEFAULT_DATA_ROOT))
        ).resolve()
        mode = Mode(str(self._request.get("mode", Mode.CREATE.value)))
        if mode is Mode.APPEND_TICK:
            return SyntheticTickWriter(root, wellbore_id).write()

        ticks = int(self._request.get("ticks", DEFAULT_TICKS))
        records = SyntheticWellBuilder(wellbore_id, ticks).build()
        refs = self._request.get("references")
        if not isinstance(refs, dict):
            raise ValueError(
                "input.references must contain offsets, price_deck, and zone_tops"
            )
        return SyntheticWellWriter(root, wellbore_id, records, refs).write()


def resolve_workspace_dir(request: dict[str, Any]) -> str:
    """Use explicit sandbox input, falling back to the environment only if absent."""
    workspace_dir = (
        request["workspace_dir"]
        if "workspace_dir" in request
        else os.environ.get("WORKSPACE_DIR")
    )
    if not isinstance(workspace_dir, str) or not workspace_dir:
        raise ValueError("workspace_dir input or WORKSPACE_DIR is required")
    return workspace_dir


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Create or advance a synthetic well from an already-parsed request object."""
    if not isinstance(request, dict):
        raise ValueError("input must be a JSON object")
    return CreateSyntheticWell(request, resolve_workspace_dir(request)).run()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a deterministic synthetic geosteering well."
    )
    parser.add_argument("--input", required=True, help="JSON request object")
    args = parser.parse_args()
    try:
        result = run(json.loads(args.input))
    except (ValueError, OSError, json.JSONDecodeError) as error:
        logger.info(json.dumps({"status": "error", "error": str(error)}))
        return 2
    logger.info(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
