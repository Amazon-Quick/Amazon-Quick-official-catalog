"""
description: Verify a trailing geosteering stand against zone and offset references, calculate the pay delta and auditable confidence, and append one observation.
last_updated: 2026-09-14
origin: original
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

WELLBORE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_DATA_ROOT = "exit-zone-geosteering-data"
DEFAULT_WELLBORE_ID = "SYN1"
WINDOW_RECORDS = 8
PAY_GR_MAX_API = 80.0
CUT_MARGIN_API = 8.0
P30_Z = 0.5244005127080407
MARGIN_HALF_FT = 5.0
CONFIDENCE_THRESHOLD = 0.65
WEIGHTS = {"curve_agreement": 0.45, "offset_match": 0.25, "margin": 0.30}
OFFSET_FULL_AGREEMENT_COUNT = 2


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
class VerificationResult:
    p30_delta_ft: float
    p50_delta_ft: float
    zone_name: str
    model_pay_ft: float
    live_pay_ft: float
    stand_records: int
    stand_top_md: float
    stand_base_md: float
    sample_spacing_ft: float
    pay_boundaries: int
    sigma_ft: float
    confidence: float
    threshold: float
    accepted: bool
    factors: list[dict[str, Any]]
    reasoning: str
    source: list[dict[str, Any]]


class VerificationCalculator:
    """Calculate pay footage, model overlap, and transparent confidence."""

    def __init__(
        self,
        records: list[dict[str, Any]],
        zones: dict[str, Any],
        offsets: dict[str, Any],
    ) -> None:
        self._records = records
        self._zones = zones
        self._offsets = offsets

    def calculate(self) -> VerificationResult:
        records = sorted(self._records, key=lambda row: float(row["depth_md"]))[
            -WINDOW_RECORDS:
        ]
        if len(records) < 2:
            raise ValueError("at least two stream records are required")
        samples = [(float(row["depth_md"]), self._is_pay(row), row) for row in records]
        top, base = samples[0][0], samples[-1][0]
        live_pay = sum(
            samples[index + 1][0] - samples[index][0]
            for index in range(len(samples) - 1)
            if samples[index][1]
        )
        boundaries = sum(
            1
            for index in range(len(samples) - 1)
            if samples[index][1] != samples[index + 1][1]
        )
        spacing = (base - top) / (len(samples) - 1)
        sigma = 0.5 * spacing * math.sqrt(max(1, boundaries))
        zone = self._target_zone(base)
        if zone is None:
            raise ValueError("no zone reference covers the latest bit depth")
        model_pay = max(
            0.0, min(float(zone["base_md"]), base) - max(float(zone["top_md"]), top)
        )
        p50 = round(live_pay - model_pay, 3)
        p30 = round(p50 - P30_Z * sigma, 3)
        curve = sum(1 for _, _, row in samples if self._is_unambiguous(row)) / len(
            samples
        )
        offset_rows = self._offsets.get("rows", [])
        agree = sum(1 for row in offset_rows if row.get("agrees") is True)
        disagree = sum(1 for row in offset_rows if row.get("agrees") is False)
        offset_factor = min(
            1.0, max(0.0, (agree - disagree) / OFFSET_FULL_AGREEMENT_COUNT)
        )
        margin_factor = abs(p30) / (abs(p30) + MARGIN_HALF_FT)
        values = {
            "curve_agreement": curve,
            "offset_match": offset_factor,
            "margin": margin_factor,
        }
        factors = []
        for name in ("curve_agreement", "offset_match", "margin"):
            value = round(values[name], 3)
            weight = WEIGHTS[name]
            factors.append(
                {
                    "name": name,
                    "value": value,
                    "weight": weight,
                    "contribution": round(value * weight, 3),
                }
            )
        confidence = round(sum(item["contribution"] for item in factors), 3)
        accepted = confidence >= CONFIDENCE_THRESHOLD
        offset_citations = (
            ", ".join(
                str(row.get("well")) for row in offset_rows if row.get("agrees") is True
            )
            or "none"
        )
        reasoning = (
            f"Live pay {live_pay:.1f} ft minus model overlap {model_pay:.1f} ft gives P50 {p50:+.1f} ft; "
            f"P30 is {p30:+.3f} ft from sigma {sigma:.3f} ft. Confidence {confidence:.3f} = "
            + " + ".join(
                f"{item['name']}({item['value']:.3f} x {item['weight']:.3f} = {item['contribution']:.3f})"
                for item in factors
            )
            + f"; threshold {CONFIDENCE_THRESHOLD:.3f}; agreeing offsets: {offset_citations}."
        )
        source = [{"id": row["id"], "kind": "stream"} for _, _, row in samples]
        source.extend(
            [
                {"id": "ref:zone_tops", "kind": "reference"},
                {"id": "ref:offsets", "kind": "reference"},
            ]
        )
        return VerificationResult(
            p30_delta_ft=p30,
            p50_delta_ft=p50,
            zone_name=str(zone["name"]),
            model_pay_ft=round(model_pay, 3),
            live_pay_ft=round(live_pay, 3),
            stand_records=len(samples),
            stand_top_md=top,
            stand_base_md=base,
            sample_spacing_ft=round(spacing, 3),
            pay_boundaries=boundaries,
            sigma_ft=round(sigma, 3),
            confidence=confidence,
            threshold=CONFIDENCE_THRESHOLD,
            accepted=accepted,
            factors=factors,
            reasoning=reasoning,
            source=source,
        )

    @staticmethod
    def _is_pay(row: dict[str, Any]) -> bool:
        value = row.get("channels", {}).get("gr")
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and float(value) <= PAY_GR_MAX_API
        )

    @staticmethod
    def _is_unambiguous(row: dict[str, Any]) -> bool:
        value = row.get("channels", {}).get("gr")
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and abs(float(value) - PAY_GR_MAX_API) > CUT_MARGIN_API
        )

    def _target_zone(self, depth_md: float) -> dict[str, Any] | None:
        rows = self._zones.get("rows", [])
        return next(
            (
                row
                for row in rows
                if float(row["top_md"]) <= depth_md < float(row["base_md"])
            ),
            None,
        )


class VerificationRunner:
    """Read confined inputs, calculate, append, and refresh the read model."""

    def __init__(self, root: Path, wellbore_id: str) -> None:
        self._root = root
        self._wellbore_id = wellbore_id

    def run(self) -> dict[str, Any]:
        if not WELLBORE_ID_PATTERN.fullmatch(self._wellbore_id):
            raise ValueError("wellbore_id must match ^[A-Za-z0-9._-]+$")
        well_dir = self._root / "wells" / self._wellbore_id
        records = self._read_jsonl(well_dir / "stream.jsonl")
        zones = self._read_json(self._root / "references" / "zone_tops.json")
        offsets = self._read_json(self._root / "references" / "offsets.json")
        result = VerificationCalculator(records, zones, offsets).calculate()
        value = asdict(result)
        reasoning = value.pop("reasoning")
        source = value.pop("source")
        confidence = value.pop("confidence")
        observation = {
            "id": f"{self._wellbore_id}:payzone_delta:{result.stand_base_md}",
            "type": "payzone_delta",
            "value": value,
            "confidence": confidence,
            "reasoning": reasoning,
            "source": source,
            "wellbore_id": self._wellbore_id,
            "depth_md": result.stand_base_md,
            "ts": records[-1]["ts"],
            "feature": "verification",
            "schema_version": "v1",
        }
        self._append_and_materialise(well_dir, observation)
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

    def _append_and_materialise(
        self, well_dir: Path, observation: dict[str, Any]
    ) -> None:
        sink = well_dir / "observations.jsonl"
        with sink.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(observation, separators=(",", ":")) + "\n")
        rows = self._read_jsonl(sink)
        latest_by_type = {row["type"]: row for row in rows}
        state = {
            "count": len(rows),
            "observations": rows,
            "latest": rows[-1],
            "latest_by_type": latest_by_type,
            "zone_status": {
                "status": "in_zone"
                if abs(result_delta(latest_by_type.get("payzone_delta"))) <= 2
                else "drifting",
                "basis": "payzone_delta",
                "as_of": observation["ts"],
            },
        }
        state_path = well_dir / "state" / "latest.json"
        state_path.write_text(
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


def result_delta(observation: dict[str, Any] | None) -> float:
    if not observation or not isinstance(observation.get("value"), dict):
        return 0.0
    return float(observation["value"].get("p50_delta_ft", 0.0))


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
    """Verify a stand from an already-parsed request object."""
    if not isinstance(request, dict):
        raise ValueError("input must be a JSON object")
    root = WorkspaceRootResolver(
        resolve_workspace_dir(request),
        str(request.get("data_root", DEFAULT_DATA_ROOT)),
    ).resolve()
    return VerificationRunner(
        root, str(request.get("wellbore_id", DEFAULT_WELLBORE_ID))
    ).run()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a geosteering stand against the model."
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
