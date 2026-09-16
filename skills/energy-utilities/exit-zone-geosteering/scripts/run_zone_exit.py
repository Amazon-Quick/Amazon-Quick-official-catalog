"""
description: Project the next zone exit from measured-depth timestamps, classify Watch, Warn, or Escalate, and append an auditable alert without generating a steer.
last_updated: 2026-09-14
origin: original
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

WELLBORE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_DATA_ROOT = "exit-zone-geosteering-data"
DEFAULT_WELLBORE_ID = "SYN1"
ESCALATE_MINUTES = 10.0
WARN_MINUTES = 30.0
WATCH_MINUTES = 60.0


class _PrintStream:
    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO, format="%(message)s", stream=_PrintStream(), force=True
)
logger = logging.getLogger(__name__)


class Severity(StrEnum):
    WATCH = "Watch"
    WARN = "Warn"
    ESCALATE = "Escalate"


@dataclass(frozen=True)
class ExitProjection:
    boundary_zone: str
    boundary_md: float
    depth_md: float
    margin_ft: float
    rate_ft_per_hr: float
    rate_basis: str
    eta_minutes: float
    severity: str | None


class ExitProjectionCalculator:
    """Calculate the next boundary, measured rate, ETA, and urgency tier."""

    def __init__(self, records: list[dict[str, Any]], zones: dict[str, Any]) -> None:
        self._records = records
        self._zones = zones

    def calculate(self) -> ExitProjection:
        if len(self._records) < 2:
            raise ValueError("at least two stream records are required")
        records = sorted(self._records, key=lambda row: row["ts"])
        previous, latest = records[-2], records[-1]
        depth = float(latest["depth_md"])
        candidates = [
            (float(row["base_md"]), str(row["name"]))
            for row in self._zones.get("rows", [])
            if float(row["base_md"]) > depth
        ]
        if not candidates:
            raise ValueError("no zone boundary lies ahead of the bit")
        boundary_md, zone_name = min(candidates)
        elapsed_hours = (
            self._parse(latest["ts"]) - self._parse(previous["ts"])
        ).total_seconds() / 3600.0
        if elapsed_hours <= 0:
            raise ValueError("latest timestamps do not advance")
        rate = (depth - float(previous["depth_md"])) / elapsed_hours
        if rate <= 0:
            raise ValueError("measured depth is not advancing")
        margin = boundary_md - depth
        eta = margin / rate * 60.0
        return ExitProjection(
            zone_name,
            boundary_md,
            depth,
            round(margin, 3),
            round(rate, 3),
            "trajectory",
            round(eta, 3),
            self._tier(eta),
        )

    @staticmethod
    def _parse(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _tier(eta_minutes: float) -> str | None:
        if eta_minutes <= ESCALATE_MINUTES:
            return Severity.ESCALATE.value
        if eta_minutes <= WARN_MINUTES:
            return Severity.WARN.value
        if eta_minutes <= WATCH_MINUTES:
            return Severity.WATCH.value
        return None


class ZoneExitRunner:
    """Read confined data, calculate a projection, and persist an alert when tiered."""

    def __init__(self, root: Path, wellbore_id: str) -> None:
        self._root = root
        self._wellbore_id = wellbore_id

    def run(self) -> dict[str, Any]:
        if not WELLBORE_ID_PATTERN.fullmatch(self._wellbore_id):
            raise ValueError("wellbore_id must match ^[A-Za-z0-9._-]+$")
        well_dir = self._root / "wells" / self._wellbore_id
        stream = self._read_jsonl(well_dir / "stream.jsonl")
        zones = self._read_json(self._root / "references" / "zone_tops.json")
        projection = ExitProjectionCalculator(stream, zones).calculate()
        if projection.severity is None:
            return {"status": "no_alert", "projection": asdict(projection)}
        rows = self._read_jsonl(well_dir / "observations.jsonl")
        verification = next(
            (row for row in reversed(rows) if row.get("type") == "payzone_delta"), None
        )
        impact = next(
            (row for row in reversed(rows) if row.get("type") == "impact_estimate"),
            None,
        )
        source = [
            {"id": stream[-2]["id"], "kind": "stream"},
            {"id": stream[-1]["id"], "kind": "stream"},
            {"id": "ref:zone_tops", "kind": "reference"},
        ]
        if verification:
            source.append({"id": verification["id"], "kind": "observation"})
        if impact:
            source.append({"id": impact["id"], "kind": "observation"})
        observation = {
            "id": f"{self._wellbore_id}:exit:{projection.boundary_zone}:{projection.boundary_md}",
            "type": "exit_alert",
            "value": {
                **asdict(projection),
                "steer": None,
                "steer_status": "not generated; obtain steering direction from the geoscience system",
            },
            "confidence": float(verification["confidence"]) if verification else 0.0,
            "reasoning": f"{projection.severity}: {projection.margin_ft:.1f} ft and {projection.eta_minutes:.1f} min to {projection.boundary_zone} base from trajectory-derived {projection.rate_ft_per_hr:.1f} ft/hr. Quick does not interpret the geology or make the steer.",
            "source": source,
            "wellbore_id": self._wellbore_id,
            "depth_md": projection.depth_md,
            "ts": stream[-1]["ts"],
            "feature": "zone-exit-warning",
            "schema_version": "v1",
        }
        self._append_and_materialise(well_dir, rows, observation)
        return observation

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object: {path.name}")
        return payload

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @staticmethod
    def _append_and_materialise(
        well_dir: Path, rows: list[dict[str, Any]], observation: dict[str, Any]
    ) -> None:
        sink = well_dir / "observations.jsonl"
        with sink.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(observation, separators=(",", ":")) + "\n")
        all_rows = [*rows, observation]
        state = {
            "count": len(all_rows),
            "observations": all_rows,
            "latest": observation,
            "latest_by_type": {row["type"]: row for row in all_rows},
            "zone_status": {
                "status": "exit_warning",
                "basis": "exit_alert",
                "as_of": observation["ts"],
            },
        }
        (well_dir / "state" / "latest.json").write_text(
            json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n"
        )


class WorkspaceRootResolver:
    def __init__(self, workspace_dir: str, requested_root: str) -> None:
        self._workspace_dir = workspace_dir
        self._requested_root = requested_root

    def resolve(self) -> Path:
        workspace = Path(self._workspace_dir).resolve()
        requested = Path(self._requested_root)
        if requested.is_absolute():
            raise ValueError("data_root must be relative to WORKSPACE_DIR")
        result = (workspace / requested).resolve()
        if result != workspace and workspace not in result.parents:
            raise ValueError("data_root escapes WORKSPACE_DIR")
        return result


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
    """Project a zone exit from an already-parsed request object."""
    if not isinstance(request, dict):
        raise ValueError("input must be a JSON object")
    root = WorkspaceRootResolver(
        resolve_workspace_dir(request),
        str(request.get("data_root", DEFAULT_DATA_ROOT)),
    ).resolve()
    return ZoneExitRunner(
        root, str(request.get("wellbore_id", DEFAULT_WELLBORE_ID))
    ).run()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project and tier a deterministic zone-exit warning."
    )
    parser.add_argument("--input", required=True, help="JSON request object")
    args = parser.parse_args()
    try:
        result = run(json.loads(args.input))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        logger.info(json.dumps({"status": "error", "error": str(error)}))
        return 2
    logger.info(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
