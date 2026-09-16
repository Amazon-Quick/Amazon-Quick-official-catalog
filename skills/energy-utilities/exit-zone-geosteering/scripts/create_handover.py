"""
description: Check observation lineage for dangling references and build a deterministic shift-handover record only when provenance integrity passes.
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
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WELLBORE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_DATA_ROOT = "exit-zone-geosteering-data"
DEFAULT_WELLBORE_ID = "SYN1"
EXTERNAL_PREFIXES = ("stream:", "ref:", "osdu:", "lwd:")


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
class IntegrityResult:
    status: str
    orphan_count: int
    orphans: list[dict[str, Any]]


class IntegrityChecker:
    """Resolve observation references against the readable set or external prefixes."""

    def __init__(self, observations: list[dict[str, Any]], wellbore_id: str) -> None:
        self._observations = observations
        self._wellbore_id = wellbore_id

    def check(self) -> IntegrityResult:
        known = {row.get("id") for row in self._observations}
        orphans = []
        for row in self._observations:
            dangling = []
            for ref in row.get("source", []):
                ref_id = ref.get("id") if isinstance(ref, dict) else None
                if not isinstance(ref_id, str):
                    dangling.append(str(ref_id))
                elif ref_id not in known and not ref_id.startswith(EXTERNAL_PREFIXES):
                    dangling.append(ref_id)
            wrong_well = row.get("wellbore_id") != self._wellbore_id
            if dangling or wrong_well:
                reasons = (["unresolved_source"] if dangling else []) + (
                    ["unresolved_wellbore"] if wrong_well else []
                )
                orphans.append(
                    {
                        "id": row.get("id"),
                        "unresolved_sources": dangling,
                        "wellbore_resolves": not wrong_well,
                        "reasons": reasons,
                    }
                )
        return IntegrityResult("pass" if not orphans else "fail", len(orphans), orphans)


class HandoverBuilder:
    """Build an audit-only handover summary from time-ordered observations."""

    def __init__(
        self,
        observations: list[dict[str, Any]],
        integrity: IntegrityResult,
        wellbore_id: str,
    ) -> None:
        self._observations = observations
        self._integrity = integrity
        self._wellbore_id = wellbore_id

    def build(self) -> dict[str, Any]:
        ordered = sorted(
            self._observations, key=lambda row: (str(row.get("ts")), str(row.get("id")))
        )
        by_type = dict(sorted(Counter(str(row.get("type")) for row in ordered).items()))
        alerts = [
            row for row in ordered if row.get("type") in ("exit_alert", "qc_finding")
        ]
        latest_delta = next(
            (row for row in reversed(ordered) if row.get("type") == "payzone_delta"),
            None,
        )
        impacts = [row for row in ordered if row.get("type") == "impact_estimate"]
        return {
            "wellbore_id": self._wellbore_id,
            "what_happened": {
                "observation_count": len(ordered),
                "by_type": by_type,
                "first_ts": ordered[0]["ts"] if ordered else None,
                "last_ts": ordered[-1]["ts"] if ordered else None,
            },
            "open_alerts": [
                {
                    "id": row["id"],
                    "severity": row.get("value", {}).get("severity"),
                    "reasoning": row.get("reasoning"),
                    "source": row.get("source", []),
                }
                for row in alerts
            ],
            "zone_status": latest_delta.get("value") if latest_delta else None,
            "price_impacts": [
                {
                    "id": row["id"],
                    "scenarios": row.get("value", {}).get("scenarios", []),
                    "source": row.get("source", []),
                }
                for row in impacts
            ],
            "integrity": {
                "status": self._integrity.status,
                "orphan_count": self._integrity.orphan_count,
                "orphans": self._integrity.orphans,
            },
        }


class HandoverRunner:
    """Read observations, enforce integrity, and append one handover note."""

    def __init__(self, root: Path, wellbore_id: str) -> None:
        self._root = root
        self._wellbore_id = wellbore_id

    def run(self) -> dict[str, Any]:
        if not WELLBORE_ID_PATTERN.fullmatch(self._wellbore_id):
            raise ValueError("wellbore_id must match ^[A-Za-z0-9._-]+$")
        well_dir = self._root / "wells" / self._wellbore_id
        rows = self._read_jsonl(well_dir / "observations.jsonl")
        if not rows:
            raise ValueError("no observations exist for the handover")
        integrity = IntegrityChecker(rows, self._wellbore_id).check()
        if integrity.status != "pass":
            return {
                "status": "provenance_failure",
                "integrity": {
                    "orphan_count": integrity.orphan_count,
                    "orphans": integrity.orphans,
                },
            }
        audit = HandoverBuilder(rows, integrity, self._wellbore_id).build()
        observation = {
            "id": f"{self._wellbore_id}:handover:{rows[-1]['ts']}",
            "type": "handover_note",
            "value": audit,
            "confidence": 1.0,
            "reasoning": "Deterministic shift handover assembled from the complete readable observation lineage.",
            "source": [{"id": row["id"], "kind": "observation"} for row in rows],
            "wellbore_id": self._wellbore_id,
            "depth_md": None,
            "ts": rows[-1]["ts"],
            "feature": "shift-handover",
            "schema_version": "v1",
        }
        self._append_and_materialise(well_dir, rows, observation)
        return observation

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
        latest_by_type = {row["type"]: row for row in all_rows}
        alert = latest_by_type.get("exit_alert")
        state = {
            "count": len(all_rows),
            "observations": all_rows,
            "latest": observation,
            "latest_by_type": latest_by_type,
            "zone_status": {
                "status": "exit_warning" if alert else "unknown",
                "basis": "exit_alert" if alert else None,
                "as_of": alert.get("ts") if alert else None,
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
    """Create a handover from an already-parsed request object."""
    if not isinstance(request, dict):
        raise ValueError("input must be a JSON object")
    root = WorkspaceRootResolver(
        resolve_workspace_dir(request),
        str(request.get("data_root", DEFAULT_DATA_ROOT)),
    ).resolve()
    return HandoverRunner(
        root, str(request.get("wellbore_id", DEFAULT_WELLBORE_ID))
    ).run()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a provenance-checked geosteering handover."
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
