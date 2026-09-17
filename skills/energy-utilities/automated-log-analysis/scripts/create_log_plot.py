"""
description: Render a confined five-track composite well log PNG from parsed and evaluated JSON data.
last_updated: 2026-09-16
origin: original
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

WELL_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_WELL_ID = "SYN-LAS-1"
DEFAULT_DATA_ROOT = "automated-log-analysis-data"
DEFAULT_DOWNSAMPLE = 1
PRIMARY_DPI = 150
FALLBACK_DPI = 100
MAX_PNG_BYTES = 2 * 1024 * 1024


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
    """Resolve one relative path beneath an explicit workspace directory."""

    def __init__(self, workspace_dir: str, relative_path: str, label: str) -> None:
        self._workspace_dir = workspace_dir
        self._relative_path = relative_path
        self._label = label

    def resolve(self) -> Path:
        if not self._workspace_dir:
            raise ValueError("workspace_dir is required")
        requested = Path(self._relative_path)
        if requested.is_absolute():
            raise ValueError(f"{self._label} must be relative to workspace_dir")
        if ".." in requested.parts:
            raise ValueError(f"{self._label} must not contain parent traversal")
        workspace = Path(self._workspace_dir).resolve()
        resolved = (workspace / requested).resolve()
        if resolved != workspace and workspace not in resolved.parents:
            raise ValueError(f"{self._label} escapes workspace_dir")
        return resolved


class LogPlotBuilder:
    """Build and write one five-track composite log plot."""

    def __init__(
        self,
        output_path: Path,
        parsed: dict[str, Any],
        evaluation: dict[str, Any],
        downsample: int,
    ) -> None:
        self._output_path = output_path
        self._parsed = parsed
        self._evaluation = evaluation
        self._downsample = downsample

    def build(self) -> int:
        columns = self._evaluation.get("sample_columns")
        if not isinstance(columns, dict):
            raise ValueError("evaluation JSON must contain sample_columns")
        depth = self._values(columns, "DEPTH")
        if len(depth) == 0:
            raise ValueError("evaluation contains no depth samples")
        selection = slice(None, None, self._downsample)
        depth = depth[selection]
        gr = self._values(columns, "GR")[selection]
        rhob = self._values(columns, "RHOB")[selection]
        nphi = self._values(columns, "NPHI")[selection]
        rt = self._values(columns, "RT")[selection]
        phie = self._values(columns, "PHIE")[selection]
        sw = self._values(columns, "SW")[selection]
        pay = self._values(columns, "NET_PAY_FLAG")[selection]
        figure, axes = plt.subplots(
            1,
            5,
            figsize=(14, 10),
            sharey=True,
            gridspec_kw={"wspace": 0.15},
        )
        figure.patch.set_facecolor("white")
        self._track_gr(axes[0], depth, gr)
        self._track_density_neutron(axes[1], depth, rhob, nphi)
        self._track_resistivity(axes[2], depth, rt)
        self._track_porosity_saturation(axes[3], depth, phie, sw)
        self._track_pay(axes[4], depth, pay)
        axes[0].invert_yaxis()
        axes[0].set_ylabel("Measured depth (ft)")
        for axis in axes:
            axis.grid(True, axis="y", color="#dddddd", linewidth=0.5)
            axis.set_facecolor("white")
        figure.suptitle(
            f"Composite Log — {self._evaluation.get('well_id', DEFAULT_WELL_ID)}"
        )
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        dpi = PRIMARY_DPI
        figure.savefig(
            self._output_path,
            dpi=dpi,
            bbox_inches="tight",
            facecolor="white",
        )
        if self._output_path.stat().st_size > MAX_PNG_BYTES:
            dpi = FALLBACK_DPI
            figure.savefig(
                self._output_path,
                dpi=dpi,
                bbox_inches="tight",
                facecolor="white",
            )
        plt.close(figure)
        return dpi

    def _track_gr(self, axis: Any, depth: np.ndarray, gr: np.ndarray) -> None:
        baselines = self._evaluation.get("gr_baselines", {})
        clean = float(baselines.get("clean_gr", 20.0))
        shaley = float(baselines.get("shaley_gr", 120.0))
        axis.axvspan(0.0, clean, color="#f4d35e", alpha=0.45)
        axis.axvspan(shaley, 150.0, color="#a0a0a0", alpha=0.35)
        axis.plot(gr, depth, color="black", linewidth=0.8)
        axis.axvline(clean, color="#b8860b", linestyle="--", linewidth=0.8)
        axis.axvline(shaley, color="#666666", linestyle="--", linewidth=0.8)
        axis.set_xlim(0, 150)
        axis.set_xlabel("GR (API)")
        axis.set_title("T1 Gamma Ray")

    @staticmethod
    def _track_density_neutron(
        axis: Any, depth: np.ndarray, rhob: np.ndarray, nphi: np.ndarray
    ) -> None:
        axis.plot(rhob, depth, color="red", linewidth=0.8)
        axis.set_xlim(1.95, 2.95)
        axis.set_xlabel("RHOB (g/cc)", color="red")
        neutron_axis = axis.twiny()
        neutron_axis.plot(nphi, depth, color="blue", linewidth=0.8)
        neutron_axis.set_xlim(0.45, -0.15)
        neutron_axis.set_xlabel("NPHI (v/v)", color="blue")
        axis.set_title("T2 Density / Neutron")

    @staticmethod
    def _track_resistivity(axis: Any, depth: np.ndarray, rt: np.ndarray) -> None:
        axis.plot(rt, depth, color="#6a3d9a", linewidth=0.8)
        axis.set_xscale("log")
        axis.set_xlim(0.2, 2000)
        axis.set_xlabel("RT (ohm-m)")
        axis.set_title("T3 Resistivity")

    @staticmethod
    def _track_porosity_saturation(
        axis: Any, depth: np.ndarray, phie: np.ndarray, sw: np.ndarray
    ) -> None:
        axis.plot(phie, depth, color="blue", linewidth=0.8)
        axis.set_xlim(0, 0.4)
        axis.set_xlabel("PHIE", color="blue")
        saturation_axis = axis.twiny()
        saturation_axis.plot(sw, depth, color="red", linewidth=0.8)
        saturation_axis.set_xlim(0, 1)
        saturation_axis.set_xlabel("SW", color="red")
        axis.set_title("T4 Reservoir")

    @staticmethod
    def _track_pay(axis: Any, depth: np.ndarray, pay: np.ndarray) -> None:
        axis.fill_betweenx(depth, 0, pay, where=pay > 0.5, color="green", alpha=0.65)
        axis.set_xlim(0, 1)
        axis.set_xlabel("Pay flag")
        axis.set_title("T5 Net Pay")

    @staticmethod
    def _values(columns: dict[str, Any], name: str) -> np.ndarray:
        values = columns.get(name)
        if not isinstance(values, list):
            raise ValueError(f"sample_columns.{name} must be an array")
        return np.array(
            [np.nan if value is None else float(value) for value in values], dtype=float
        )


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Create a five-track PNG from an already-parsed request object."""
    try:
        if not isinstance(request, dict):
            raise ValueError("input must be a JSON object")
        workspace_dir = request.get("workspace_dir")
        if not isinstance(workspace_dir, str) or not workspace_dir:
            raise ValueError("workspace_dir is required")
        well_id = str(request.get("well_id", DEFAULT_WELL_ID))
        if not WELL_ID_PATTERN.fullmatch(well_id):
            raise ValueError("well_id must match ^[A-Za-z0-9._-]+$")
        data_root = str(request.get("data_root", DEFAULT_DATA_ROOT))
        output_root = WorkspacePathResolver(
            workspace_dir, data_root, "data_root"
        ).resolve()
        parsed_relative = str(
            request.get("parsed_path", str(Path(data_root) / f"{well_id}_parsed.json"))
        )
        evaluation_relative = str(
            request.get(
                "evaluation_path", str(Path(data_root) / f"{well_id}_evaluation.json")
            )
        )
        parsed_path = WorkspacePathResolver(
            workspace_dir, parsed_relative, "parsed_path"
        ).resolve()
        evaluation_path = WorkspacePathResolver(
            workspace_dir, evaluation_relative, "evaluation_path"
        ).resolve()
        parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        downsample = int(request.get("downsample", DEFAULT_DOWNSAMPLE))
        if downsample < 1:
            raise ValueError("downsample must be at least 1")
        output_path = output_root / f"{well_id}_log_plot.png"
        dpi = LogPlotBuilder(output_path, parsed, evaluation, downsample).build()
        size = output_path.stat().st_size
        if size > MAX_PNG_BYTES:
            raise ValueError("rendered PNG exceeds 2 MB after fallback")
        return {
            "status": "created",
            "well_id": well_id,
            "path": str(output_path),
            "bytes": size,
            "dpi": dpi,
        }
    except (ValueError, OSError, json.JSONDecodeError, TypeError) as error:
        return {"status": "error", "error": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a five-track log plot.")
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
