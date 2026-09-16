"""
description: Project chart-ready geosteering data and render a plain-HTML fallback inside the Amazon Quick workspace.
last_updated: 2026-09-15
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
from pathlib import Path
from typing import Any

WELLBORE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_DATA_ROOT = "exit-zone-geosteering-data"
DEFAULT_WELLBORE_ID = "SYN1"
DATA_TOKEN = "__GEOSTEERING_DATA__"  # nosec B105 - HTML placeholder, not a credential


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


@dataclass(frozen=True)
class DashboardData:
    wellbore_id: str
    empty: bool
    message: str
    observation_count: int
    latest_depth_md: float | None
    zone_status: dict[str, Any]
    verification: dict[str, Any] | None
    price_impact: dict[str, Any] | None
    zone_exit: dict[str, Any] | None
    handover: dict[str, Any] | None
    lwd_curves: dict[str, list[list[float]]]
    trajectory: list[dict[str, float]]
    zone_bands: list[dict[str, Any]]
    confidence_trend: list[dict[str, Any]]
    alert_feed: list[dict[str, Any]]
    observations: list[dict[str, Any]]


class DashboardDataBuilder:
    """Project stable cards, chart series, and feeds from already-loaded data."""

    def __init__(
        self,
        wellbore_id: str,
        state: dict[str, Any] | None,
        stream: list[dict[str, Any]] | None = None,
        zones: dict[str, Any] | None = None,
    ) -> None:
        self._wellbore_id = wellbore_id
        self._state = state
        self._stream = stream or []
        self._zones = zones or {}

    def build(self) -> DashboardData:
        observations = list((self._state or {}).get("observations", []))
        latest_by_type = (self._state or {}).get("latest_by_type", {})
        stream = sorted(self._stream, key=lambda row: float(row["depth_md"]))
        latest_depth = float(stream[-1]["depth_md"]) if stream else None
        return DashboardData(
            wellbore_id=self._wellbore_id,
            empty=not observations,
            message=(
                "No geosteering observations yet. Seed and run a workflow to populate this dashboard."
                if not observations
                else ""
            ),
            observation_count=len(observations),
            latest_depth_md=latest_depth,
            zone_status=(self._state or {}).get("zone_status", {"status": "unknown"}),
            verification=latest_by_type.get("payzone_delta"),
            price_impact=latest_by_type.get("impact_estimate"),
            zone_exit=latest_by_type.get("exit_alert"),
            handover=latest_by_type.get("handover_note"),
            lwd_curves=self._build_lwd_curves(stream),
            trajectory=self._build_trajectory(stream),
            zone_bands=self._build_zone_bands(),
            confidence_trend=self._build_confidence_trend(observations),
            alert_feed=self._build_alert_feed(observations),
            observations=observations,
        )

    @staticmethod
    def _build_lwd_curves(
        stream: list[dict[str, Any]],
    ) -> dict[str, list[list[float]]]:
        curves: dict[str, list[list[float]]] = {}
        for row in stream:
            depth = float(row["depth_md"])
            channels = row.get("channels", {})
            if not isinstance(channels, dict):
                continue
            for name, value in sorted(channels.items()):
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    curves.setdefault(str(name), []).append([depth, float(value)])
        return curves

    @staticmethod
    def _build_trajectory(stream: list[dict[str, Any]]) -> list[dict[str, float]]:
        if not stream:
            return []
        origin = float(stream[0]["depth_md"])
        return [
            {
                "section_ft": round(float(row["depth_md"]) - origin, 3),
                "depth_md": float(row["depth_md"]),
            }
            for row in stream
        ]

    def _build_zone_bands(self) -> list[dict[str, Any]]:
        return [
            {
                "name": str(row["name"]),
                "from_md": float(row["top_md"]),
                "to_md": float(row["base_md"]),
            }
            for row in self._zones.get("rows", [])
        ]

    @staticmethod
    def _build_confidence_trend(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "depth_md": row.get("depth_md"),
                "confidence": row.get("confidence"),
                "timestamp": row.get("ts"),
                "observation_id": row.get("id"),
            }
            for row in observations
            if row.get("type") == "payzone_delta"
        ]

    @staticmethod
    def _build_alert_feed(
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": row.get("id"),
                "tier": row.get("value", {}).get("severity"),
                "eta_minutes": row.get("value", {}).get("eta_minutes"),
                "margin_ft": row.get("value", {}).get("margin_ft"),
                "boundary_zone": row.get("value", {}).get("boundary_zone"),
                "boundary_md": row.get("value", {}).get("boundary_md"),
                "timestamp": row.get("ts"),
                "confidence": row.get("confidence"),
                "reasoning": row.get("reasoning"),
                "source": row.get("source", []),
            }
            for row in observations
            if row.get("type") == "exit_alert"
        ]


class DashboardRenderer:
    """Inject escaped projected JSON into the bundled plain-HTML fallback."""

    def __init__(self, template: str, data: DashboardData) -> None:
        self._template = template
        self._data = data

    def render(self) -> str:
        if DATA_TOKEN not in self._template:
            raise ValueError(f"dashboard template is missing {DATA_TOKEN}")
        payload = json.dumps(asdict(self._data), separators=(",", ":")).replace(
            "<", "\\u003c"
        )
        return self._template.replace(DATA_TOKEN, payload)


class DashboardRunner:
    """Read confined inputs and write chart data plus the fallback artifact."""

    def __init__(self, root: Path, wellbore_id: str, template: str) -> None:
        self._root = root
        self._wellbore_id = wellbore_id
        self._template = template

    def run(self) -> dict[str, Any]:
        if not WELLBORE_ID_PATTERN.fullmatch(self._wellbore_id):
            raise ValueError("wellbore_id must match ^[A-Za-z0-9._-]+$")
        well_dir = self._root / "wells" / self._wellbore_id
        state = self._read_optional_json(well_dir / "state" / "latest.json")
        stream = self._read_optional_jsonl(well_dir / "stream.jsonl")
        zones = self._read_optional_json(self._root / "references" / "zone_tops.json")
        data = DashboardDataBuilder(self._wellbore_id, state, stream, zones).build()
        output_dir = self._root / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        data_output = output_dir / f"{self._wellbore_id}-dashboard-data.json"
        fallback_output = output_dir / f"{self._wellbore_id}-dashboard-fallback.html"
        data_output.write_text(
            json.dumps(asdict(data), indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        fallback_output.write_text(
            DashboardRenderer(self._template, data).render(),
            encoding="utf-8",
            newline="\n",
        )
        return {
            "status": "projected",
            "data_output": str(data_output),
            "fallback_output": str(fallback_output),
            "empty": data.empty,
            "observation_count": data.observation_count,
            "stream_record_count": len(stream),
            "chart_series": {
                "lwd_curves": len(data.lwd_curves),
                "trajectory_points": len(data.trajectory),
                "zone_bands": len(data.zone_bands),
                "confidence_points": len(data.confidence_trend),
                "alerts": len(data.alert_feed),
            },
        }

    @staticmethod
    def _read_optional_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object: {path.name}")
        return payload

    @staticmethod
    def _read_optional_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


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
    """Project dashboard data from an already-parsed request object."""
    if not isinstance(request, dict):
        raise ValueError("input must be a JSON object")
    template = request.get("template")
    if not isinstance(template, str) or not template:
        raise ValueError("input.template must contain assets/dashboard.html")
    root = WorkspaceRootResolver(
        resolve_workspace_dir(request),
        str(request.get("data_root", DEFAULT_DATA_ROOT)),
    ).resolve()
    return DashboardRunner(
        root, str(request.get("wellbore_id", DEFAULT_WELLBORE_ID)), template
    ).run()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Project geosteering dashboard data and render its fallback."
    )
    parser.add_argument(
        "--input", required=True, help="JSON request object, including template text"
    )
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
