"""
description: Create a deterministic LAS 2.0 well log with vendor mnemonics inside the Amazon Quick workspace.
last_updated: 2026-09-16
origin: original
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

WELL_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_WELL_ID = "SYN-LAS-1"
DEFAULT_DATA_ROOT = "automated-log-analysis-data"
START_DEPTH_FT = 8000.0
STOP_DEPTH_FT = 8750.0
STEP_FT = 0.5
NULL_VALUE = -999.25
PAY_INTERVALS = ((8100.0, 8199.5), (8300.0, 8424.5), (8550.0, 8649.5))
WASHOUT_INTERVAL = (8460.0, 8464.5)


class Mode(StrEnum):
    CREATE = "create"
    NO_RESISTIVITY = "no_resistivity"


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


class WorkspacePathResolver:
    """Resolve a relative path beneath an explicit workspace directory."""

    def __init__(self, workspace_dir: str, relative_path: str) -> None:
        self._workspace_dir = workspace_dir
        self._relative_path = relative_path

    def resolve(self) -> Path:
        if not self._workspace_dir:
            raise ValueError("workspace_dir is required")
        requested = Path(self._relative_path)
        if requested.is_absolute():
            raise ValueError("data_root must be relative to workspace_dir")
        if ".." in requested.parts:
            raise ValueError("data_root must not contain parent traversal")
        workspace = Path(self._workspace_dir).resolve()
        resolved = (workspace / requested).resolve()
        if resolved != workspace and workspace not in resolved.parents:
            raise ValueError("data_root escapes workspace_dir")
        return resolved


class SyntheticLasBuilder:
    """Build deterministic LAS text for one synthetic well."""

    def __init__(self, well_id: str, mode: Mode) -> None:
        self._well_id = well_id
        self._mode = mode

    def build(self) -> tuple[str, list[str], int]:
        if not WELL_ID_PATTERN.fullmatch(self._well_id):
            raise ValueError("well_id must match ^[A-Za-z0-9._-]+$")
        curves = ["DEPT", "GRMA", "ROBB", "TNPH"]
        if self._mode is not Mode.NO_RESISTIVITY:
            curves.append("P40H")
        curves.extend(["DTCO", "HCAL"])
        rows = [self._row(index, curves) for index in range(self._sample_count())]
        curve_lines = {
            "DEPT": " DEPT.FT : Measured depth",
            "GRMA": " GRMA.API : Vendor gamma ray",
            "ROBB": " ROBB.G/CC : Vendor bulk density",
            "TNPH": " TNPH.V/V : Vendor neutron porosity",
            "P40H": " P40H.OHMM : Vendor deep resistivity",
            "DTCO": " DTCO.US/FT : Compressional slowness",
            "HCAL": " HCAL.IN : Caliper",
        }
        header = [
            "~V",
            " VERS. 2.0 : LAS version",
            " WRAP. NO : One line per depth sample",
            "~W",
            f" WELL. {self._well_id} : Well name",
            f" STRT.FT {START_DEPTH_FT:.1f} : Start depth",
            f" STOP.FT {STOP_DEPTH_FT:.1f} : Stop depth",
            f" STEP.FT {STEP_FT:.1f} : Sample interval",
            f" NULL. {NULL_VALUE:.2f} : Null value",
            "~C",
            *(curve_lines[curve] for curve in curves),
            "~A",
        ]
        return "\n".join([*header, *rows]) + "\n", curves, len(rows)

    @staticmethod
    def _sample_count() -> int:
        return int(round((STOP_DEPTH_FT - START_DEPTH_FT) / STEP_FT)) + 1

    @staticmethod
    def _in_interval(depth: float, interval: tuple[float, float]) -> bool:
        return interval[0] <= depth <= interval[1]

    def _row(self, index: int, curves: list[str]) -> str:
        depth = START_DEPTH_FT + index * STEP_FT
        is_pay = any(self._in_interval(depth, interval) for interval in PAY_INTERVALS)
        is_washout = self._in_interval(depth, WASHOUT_INTERVAL)
        values = {
            "DEPT": depth,
            "GRMA": 35.0 if is_pay else 120.0,
            "ROBB": 1.85 if is_washout else (2.25 if is_pay else 2.55),
            "TNPH": 0.22 if is_pay else 0.08,
            "P40H": 50.0 if is_pay else 1.5,
            "DTCO": 85.0 if is_pay else 65.0,
            "HCAL": 12.5 if is_washout else 8.5,
        }
        return " ".join(f"{values[curve]:.4f}" for curve in curves)


class SyntheticLasWriter:
    """Write one generated LAS document."""

    def __init__(self, output_path: Path, text: str) -> None:
        self._output_path = output_path
        self._text = text

    def write(self) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text(self._text, encoding="utf-8", newline="\n")


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic LAS file from an already-parsed request object."""
    try:
        if not isinstance(request, dict):
            raise ValueError("input must be a JSON object")
        workspace_dir = request.get("workspace_dir")
        if not isinstance(workspace_dir, str) or not workspace_dir:
            raise ValueError("workspace_dir is required")
        well_id = str(request.get("well_id", DEFAULT_WELL_ID))
        mode = Mode(str(request.get("mode", Mode.CREATE.value)))
        data_root = str(request.get("data_root", DEFAULT_DATA_ROOT))
        root = WorkspacePathResolver(workspace_dir, data_root).resolve()
        text, curves, sample_count = SyntheticLasBuilder(well_id, mode).build()
        output_path = root / f"{well_id}.las"
        SyntheticLasWriter(output_path, text).write()
        return {
            "status": "created",
            "well_id": well_id,
            "path": str(output_path),
            "relative_path": str(Path(data_root) / f"{well_id}.las"),
            "sample_count": sample_count,
            "curves": curves,
            "mode": mode.value,
        }
    except (ValueError, OSError) as error:
        return {"status": "error", "error": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a deterministic LAS 2.0 file.")
    parser.add_argument("--input", required=True, help="JSON request object")
    args = parser.parse_args()
    try:
        request = json.loads(args.input)
    except json.JSONDecodeError as error:
        logger.info(json.dumps({"status": "error", "error": str(error)}))
        return 2
    result = run(request)
    logger.info(json.dumps(result, separators=(",", ":")))
    return 0 if result.get("status") != "error" else 2


if __name__ == "__main__":
    sys.exit(main())
