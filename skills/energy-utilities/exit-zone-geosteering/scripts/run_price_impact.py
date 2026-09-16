"""
description: Price an accepted pay-zone delta and a three-stand hold scenario with deterministic code-owned formulas, then append one impact observation.
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
from pathlib import Path
from typing import Any

WELLBORE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_DATA_ROOT = "exit-zone-geosteering-data"
DEFAULT_WELLBORE_ID = "SYN1"
BBL_PER_FT = 100.0
SIDETRACK_COST_USD_AVOIDED = 250000.0
HOLD_STANDS = 3
STAND_FT = 5.0


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
class ImpactScenario:
    scenario: str
    pay_delta_ft: float
    out_of_zone_ft: float
    usd: float
    unit: str


class ImpactCalculator:
    """Compute correct-now and hold-three-stands outcomes without model input."""

    def __init__(
        self, pay_delta_ft: float, margin_ft: float, usd_per_bbl: float
    ) -> None:
        self._pay_delta_ft = pay_delta_ft
        self._margin_ft = margin_ft
        self._usd_per_bbl = usd_per_bbl

    def calculate(self) -> list[ImpactScenario]:
        correct = self._scenario("correct_now", self._pay_delta_ft, 0.0)
        advance = HOLD_STANDS * STAND_FT
        out_of_zone = max(0.0, advance - self._margin_ft)
        hold_delta = self._pay_delta_ft - out_of_zone
        hold = self._scenario("hold_3_stands", hold_delta, out_of_zone)
        return [correct, hold]

    def _scenario(
        self, name: str, delta_ft: float, out_of_zone_ft: float
    ) -> ImpactScenario:
        revenue = delta_ft * BBL_PER_FT * self._usd_per_bbl
        avoided = SIDETRACK_COST_USD_AVOIDED if delta_ft > 0 else 0.0
        return ImpactScenario(
            name,
            round(delta_ft, 3),
            round(out_of_zone_ft, 3),
            round(revenue + avoided, 2),
            "USD",
        )


class PriceImpactRunner:
    """Read latest verified inputs, calculate both scenarios, and persist one observation."""

    def __init__(self, root: Path, wellbore_id: str) -> None:
        self._root = root
        self._wellbore_id = wellbore_id

    def run(self) -> dict[str, Any]:
        if not WELLBORE_ID_PATTERN.fullmatch(self._wellbore_id):
            raise ValueError("wellbore_id must match ^[A-Za-z0-9._-]+$")
        well_dir = self._root / "wells" / self._wellbore_id
        rows = self._read_jsonl(well_dir / "observations.jsonl")
        delta = next(
            (row for row in reversed(rows) if row.get("type") == "payzone_delta"), None
        )
        if delta is None:
            raise ValueError(
                "no payzone_delta observation exists; run verification first"
            )
        if not delta.get("value", {}).get("accepted"):
            raise ValueError("latest payzone_delta is below the confidence threshold")
        price = self._read_json(self._root / "references" / "price_deck.json")
        zones = self._read_json(self._root / "references" / "zone_tops.json")
        depth = float(delta["depth_md"])
        boundaries = [
            float(row["base_md"])
            for row in zones.get("rows", [])
            if float(row["base_md"]) > depth
        ]
        if not boundaries:
            raise ValueError("no zone boundary lies ahead of the bit")
        margin = min(boundaries) - depth
        scenarios = ImpactCalculator(
            float(delta["value"]["p50_delta_ft"]), margin, float(price["usd_per_bbl"])
        ).calculate()
        observation = {
            "id": f"{self._wellbore_id}:impact:{delta['id']}",
            "type": "impact_estimate",
            "value": {
                "scenarios": [asdict(item) for item in scenarios],
                "basis": {
                    "bbl_per_ft": BBL_PER_FT,
                    "sidetrack_cost_usd_avoided": SIDETRACK_COST_USD_AVOIDED,
                    "usd_per_bbl": float(price["usd_per_bbl"]),
                    "price_deck_source": price.get("source"),
                    "price_deck_as_of": price.get("as_of"),
                    "margin_ft": round(margin, 3),
                },
            },
            "confidence": float(delta["confidence"]),
            "reasoning": "Deterministic outcomes from pay delta x 100 bbl/ft x price plus one sidetrack-cost credit; model-generated text may not alter these figures.",
            "source": [
                {"id": delta["id"], "kind": "observation"},
                {"id": "ref:price_deck", "kind": "reference"},
                {"id": "ref:zone_tops", "kind": "reference"},
            ],
            "wellbore_id": self._wellbore_id,
            "depth_md": depth,
            "ts": delta["ts"],
            "feature": "price-impact",
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
                "status": "drifting",
                "basis": "payzone_delta",
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
    """Calculate price impact from an already-parsed request object."""
    if not isinstance(request, dict):
        raise ValueError("input must be a JSON object")
    root = WorkspaceRootResolver(
        resolve_workspace_dir(request),
        str(request.get("data_root", DEFAULT_DATA_ROOT)),
    ).resolve()
    return PriceImpactRunner(
        root, str(request.get("wellbore_id", DEFAULT_WELLBORE_ID))
    ).run()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calculate deterministic geosteering price impact."
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
