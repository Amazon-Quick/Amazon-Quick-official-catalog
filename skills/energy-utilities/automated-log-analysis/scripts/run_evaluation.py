"""
description: Run deterministic petrophysical evaluation on parsed LAS data and persist JSON-safe per-sample results.
last_updated: 2026-09-16
origin: original
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

WELL_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_WELL_ID = "SYN-LAS-1"
DEFAULT_DATA_ROOT = "automated-log-analysis-data"
DEFAULT_AREA_ACRES = 500.0
DEFAULT_MATRIX_DENSITY = 2.65
DEFAULT_FLUID_DENSITY = 0.9
DEFAULT_A = 1.0
DEFAULT_M = 1.87
DEFAULT_N = 2.45
DEFAULT_RW = 0.017
DEFAULT_PHIE_MIN = 0.06
DEFAULT_SW_MAX = 0.50
DEFAULT_VSH_MAX = 0.50
DEFAULT_BOI = 1.3
DEFAULT_RF = 0.35


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


def pick_gr_baselines(
    gr_array: np.ndarray, method: str = "histogram"
) -> dict[str, Any]:
    valid = gr_array[~np.isnan(gr_array)]
    if len(valid) == 0:
        return {
            "clean_gr": 20.0,
            "shaley_gr": 120.0,
            "method": method,
            "gr_min": None,
            "gr_max": None,
            "gr_mean": None,
        }
    if method == "histogram":
        clean_gr = float(np.percentile(valid, 5))
        shaley_gr = float(np.percentile(valid, 95))
    else:
        clean_gr = float(np.min(valid))
        shaley_gr = float(np.max(valid))
    if shaley_gr - clean_gr < 10:
        shaley_gr = clean_gr + 10
    return {
        "clean_gr": round(clean_gr, 2),
        "shaley_gr": round(shaley_gr, 2),
        "method": method,
        "gr_min": round(float(np.min(valid)), 2),
        "gr_max": round(float(np.max(valid)), 2),
        "gr_mean": round(float(np.mean(valid)), 2),
    }


def calc_vshale(gr: np.ndarray, clean_gr: float, shaley_gr: float) -> np.ndarray:
    gr = np.asarray(gr, dtype=float)
    denominator = shaley_gr - clean_gr
    if abs(denominator) < 1e-6:
        return np.full_like(gr, 0.5)
    return np.clip((gr - clean_gr) / denominator, 0.0, 1.0)


def calc_porosity_density(
    rhob: np.ndarray,
    matrix_density: float = DEFAULT_MATRIX_DENSITY,
    fluid_density: float = DEFAULT_FLUID_DENSITY,
) -> np.ndarray:
    rhob = np.asarray(rhob, dtype=float)
    denominator = matrix_density - fluid_density
    if abs(denominator) < 1e-6:
        return np.full_like(rhob, np.nan)
    return np.clip((matrix_density - rhob) / denominator, 0.0, 0.5)


def calc_archie_sw(
    phit: np.ndarray,
    rt: np.ndarray,
    a: float = DEFAULT_A,
    m: float = DEFAULT_M,
    n: float = DEFAULT_N,
    rw: float = DEFAULT_RW,
) -> np.ndarray:
    phit = np.asarray(phit, dtype=float)
    rt = np.asarray(rt, dtype=float)
    phit_safe = np.where(phit > 0.001, phit, np.nan)
    rt_safe = np.where(rt > 0.001, rt, np.nan)
    sw_n = (a * rw) / (np.power(phit_safe, m) * rt_safe)
    sw = np.power(np.abs(sw_n), 1.0 / n)
    return np.clip(np.where(np.isnan(sw), 1.0, sw), 0.0, 1.0)


def calc_effective_porosity(phit: np.ndarray, vshale: np.ndarray) -> np.ndarray:
    phit = np.asarray(phit, dtype=float)
    vshale = np.asarray(vshale, dtype=float)
    return np.clip(phit * (1.0 - vshale), 0.0, 0.5)


def calc_net_pay(
    depth: np.ndarray,
    phie: np.ndarray,
    sw: np.ndarray,
    vshale: np.ndarray,
    phie_min: float = DEFAULT_PHIE_MIN,
    sw_max: float = DEFAULT_SW_MAX,
    vsh_max: float = DEFAULT_VSH_MAX,
) -> dict[str, Any]:
    depth = np.asarray(depth, dtype=float)
    phie = np.asarray(phie, dtype=float)
    sw = np.asarray(sw, dtype=float)
    vshale = np.asarray(vshale, dtype=float)
    flag = np.zeros(len(depth), dtype=int)
    # Documented degradation: when no resistivity curve exists every Sw is NaN.
    # Net pay then uses the porosity and shale cutoffs only and is reported as
    # limited accuracy instead of collapsing to zero.
    sw_available = bool(np.any(~np.isnan(sw)))
    valid = ~(np.isnan(phie) | np.isnan(vshale))
    meets_cutoff = valid & (phie >= phie_min) & (vshale <= vsh_max)
    if sw_available:
        meets_cutoff &= ~np.isnan(sw) & (sw <= sw_max)
    flag[meets_cutoff] = 1
    step = abs(float(np.median(np.diff(depth)))) if len(depth) > 1 else 1.0
    pay_count = int(np.sum(flag))
    net_pay_ft = round(pay_count * step, 2)
    gross_ft = round((depth[-1] - depth[0]) + step, 2) if len(depth) > 1 else step
    net_to_gross = round(net_pay_ft / gross_ft, 4) if gross_ft > 0 else 0.0
    pay_mask = flag == 1
    avg_phie = round(float(np.nanmean(phie[pay_mask])), 4) if pay_count > 0 else 0.0
    avg_sw = (
        round(float(np.nanmean(sw[pay_mask])), 4)
        if pay_count > 0 and sw_available
        else None
    )
    avg_vsh = round(float(np.nanmean(vshale[pay_mask])), 4) if pay_count > 0 else 0.0
    return {
        "net_pay_flag": flag,
        "net_pay_ft": net_pay_ft,
        "gross_ft": gross_ft,
        "net_to_gross": net_to_gross,
        "avg_phie_pay": avg_phie,
        "avg_sw_pay": avg_sw,
        "avg_vsh_pay": avg_vsh,
        "sw_cutoff_applied": sw_available,
        "accuracy": "full"
        if sw_available
        else "limited: no resistivity, Sw cutoff skipped",
        "cutoffs": {
            "phie_min": phie_min,
            "sw_max": sw_max,
            "vsh_max": vsh_max,
        },
    }


def identify_pay_zones(
    depth: np.ndarray,
    phie: np.ndarray,
    sw: np.ndarray,
    rt: np.ndarray,
    net_pay_flag: np.ndarray,
    min_thickness: float = 0.3,
) -> list[dict[str, Any]]:
    depth = np.asarray(depth, dtype=float)
    flag = np.asarray(net_pay_flag, dtype=int)
    step = abs(float(np.median(np.diff(depth)))) if len(depth) >= 2 else 1.0
    grouped: list[list[int]] = []
    zone_indices: list[int] = []
    for index, value in enumerate(flag):
        if value == 1:
            zone_indices.append(index)
        elif zone_indices:
            grouped.append(list(zone_indices))
            zone_indices = []
    if zone_indices:
        grouped.append(list(zone_indices))
    result: list[dict[str, Any]] = []
    for zone_id, indices in enumerate(grouped, 1):
        selected = np.array(indices)
        top = float(depth[selected[0]])
        base = float(depth[selected[-1]])
        thickness = round((base - top) + step, 2)
        if thickness < min_thickness:
            continue
        rt_values = np.asarray(rt, dtype=float)[selected]
        finite_rt = rt_values[~np.isnan(rt_values)]
        result.append(
            {
                "zone_id": zone_id,
                "top": round(top, 2),
                "base": round(base, 2),
                "thickness": thickness,
                "avg_phie": round(float(np.nanmean(phie[selected])), 4),
                "avg_sw": round(float(np.nanmean(sw[selected])), 4)
                if np.any(~np.isnan(sw[selected]))
                else None,
                "avg_rt": round(float(np.mean(finite_rt)), 2)
                if len(finite_rt)
                else None,
                "sample_count": len(selected),
            }
        )
    return result


def calc_ooip(
    area_acres: float,
    net_pay_ft: float,
    avg_porosity: float,
    avg_sw: float | None,
    boi: float = DEFAULT_BOI,
    rf: float = DEFAULT_RF,
) -> dict[str, Any]:
    if any(
        value is None or value <= 0 for value in [area_acres, net_pay_ft, avg_porosity]
    ):
        return {
            "ooip_stb": 0.0,
            "recoverable_stb": 0.0,
            "inputs": {
                "area_acres": area_acres,
                "net_pay_ft": net_pay_ft,
                "avg_porosity": avg_porosity,
                "avg_sw": avg_sw,
                "boi": boi,
                "rf": rf,
            },
        }
    if avg_sw is None:
        return {
            "ooip_stb": None,
            "recoverable_stb": None,
            "note": "OOIP requires water saturation; no resistivity curve was available",
            "inputs": {
                "area_acres": area_acres,
                "net_pay_ft": net_pay_ft,
                "avg_porosity": round(avg_porosity, 4),
                "avg_sw": None,
                "boi": boi,
                "rf": rf,
            },
        }
    hydrocarbon_saturation = max(0, 1.0 - avg_sw)
    ooip = (
        7758.0 * area_acres * net_pay_ft * avg_porosity * hydrocarbon_saturation / boi
    )
    return {
        "ooip_stb": round(ooip, 0),
        "recoverable_stb": round(ooip * rf, 0),
        "inputs": {
            "area_acres": area_acres,
            "net_pay_ft": net_pay_ft,
            "avg_porosity": round(avg_porosity, 4),
            "avg_sw": round(avg_sw, 4),
            "boi": boi,
            "rf": rf,
        },
    }


def run_log_qc(
    depth: np.ndarray, curves_dict: dict[str, np.ndarray], spike_threshold: float = 5.0
) -> dict[str, Any]:
    depth = np.asarray(depth, dtype=float)
    sample_count = len(depth)
    results: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for name, values in curves_dict.items():
        array = np.asarray(values, dtype=float)
        null_count = int(np.sum(np.isnan(array)))
        null_pct = round(100.0 * null_count / sample_count, 1) if sample_count else 0.0
        valid = array[~np.isnan(array)]
        spike_count = 0
        if len(valid) > 10:
            mean = np.mean(valid)
            standard_deviation = np.std(valid)
            if standard_deviation > 1e-10:
                spike_count = int(
                    np.sum(np.abs(valid - mean) > spike_threshold * standard_deviation)
                )
        gap_count = 0
        run_length = 0
        for is_null in np.isnan(array):
            if is_null:
                run_length += 1
            else:
                if run_length > 3:
                    gap_count += 1
                run_length = 0
        if run_length > 3:
            gap_count += 1
        results[name] = {
            "null_count": null_count,
            "null_pct": null_pct,
            "spike_count": spike_count,
            "gap_count": gap_count,
            "min": round(float(np.min(valid)), 4) if len(valid) else None,
            "max": round(float(np.max(valid)), 4) if len(valid) else None,
            "mean": round(float(np.mean(valid)), 4) if len(valid) else None,
            "std": round(float(np.std(valid)), 4) if len(valid) else None,
        }
        if null_pct > 20:
            warnings.append(f"{name}: {null_pct}% null values")
        if spike_count > 5:
            warnings.append(f"{name}: {spike_count} spikes detected")
        if gap_count > 0:
            warnings.append(f"{name}: {gap_count} data gap(s)")
    max_null_pct = max((item["null_pct"] for item in results.values()), default=0)
    total_spikes = sum(item["spike_count"] for item in results.values())
    total_gaps = sum(item["gap_count"] for item in results.values())
    if max_null_pct > 30 or total_gaps > 5:
        quality = "poor"
    elif max_null_pct > 10 or total_spikes > 10 or total_gaps > 2:
        quality = "fair"
    else:
        quality = "good"
    return {
        "total_samples": sample_count,
        "curves": results,
        "overall_quality": quality,
        "warnings": warnings,
    }


def run_full_evaluation(
    data_arrays: dict[str, np.ndarray],
    depth: np.ndarray,
    area_acres: float = DEFAULT_AREA_ACRES,
    matrix_density: float = DEFAULT_MATRIX_DENSITY,
    fluid_density: float = DEFAULT_FLUID_DENSITY,
    a: float = DEFAULT_A,
    m: float = DEFAULT_M,
    n: float = DEFAULT_N,
    rw: float = DEFAULT_RW,
    phie_min: float = DEFAULT_PHIE_MIN,
    sw_max: float = DEFAULT_SW_MAX,
    vsh_max: float = DEFAULT_VSH_MAX,
    boi: float = DEFAULT_BOI,
    rf: float = DEFAULT_RF,
) -> dict[str, Any]:
    results: dict[str, Any] = {"status": "started", "warnings": []}
    results["qc"] = run_log_qc(depth, data_arrays)
    if "GR" not in data_arrays:
        results["status"] = "failed"
        results["warnings"].append("GR curve required but not found")
        return results
    baselines = pick_gr_baselines(data_arrays["GR"])
    results["baselines"] = baselines
    vshale = calc_vshale(
        data_arrays["GR"], baselines["clean_gr"], baselines["shaley_gr"]
    )
    data_arrays["V_SHALE"] = vshale
    if "RHOB" in data_arrays:
        phid = calc_porosity_density(data_arrays["RHOB"], matrix_density, fluid_density)
        data_arrays["PHID"] = phid
    else:
        results["warnings"].append("RHOB not found; density porosity skipped")
        phid = np.full(len(depth), np.nan)
        data_arrays["PHID"] = phid
    if "RT" in data_arrays:
        sw = calc_archie_sw(phid, data_arrays["RT"], a, m, n, rw)
        data_arrays["SW_ARCHIE"] = sw
    else:
        results["warnings"].append("RT not found; water saturation skipped")
        sw = np.full(len(depth), np.nan)
        data_arrays["SW_ARCHIE"] = sw
    phie = calc_effective_porosity(phid, vshale)
    data_arrays["PHIE"] = phie
    net_pay = calc_net_pay(depth, phie, sw, vshale, phie_min, sw_max, vsh_max)
    data_arrays["NET_PAY_FLAG"] = net_pay["net_pay_flag"]
    results["net_pay"] = {
        key: value for key, value in net_pay.items() if key != "net_pay_flag"
    }
    rt_for_zones = data_arrays.get("RT", np.full(len(depth), np.nan))
    results["zones"] = identify_pay_zones(
        depth, phie, sw, rt_for_zones, net_pay["net_pay_flag"]
    )
    results["ooip"] = calc_ooip(
        area_acres,
        net_pay["net_pay_ft"],
        net_pay["avg_phie_pay"],
        net_pay["avg_sw_pay"],
        boi,
        rf,
    )
    results["status"] = "success"
    results["data_arrays"] = data_arrays
    return results


class EvaluationWriter:
    """Persist JSON-safe evaluation output."""

    def __init__(self, output_path: Path, payload: dict[str, Any]) -> None:
        self._output_path = output_path
        self._payload = payload

    def write(self) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text(
            json.dumps(self._payload, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )


def _array(values: list[float | None]) -> np.ndarray:
    return np.array([np.nan if value is None else float(value) for value in values])


def _json_values(values: np.ndarray) -> list[float | int | None]:
    result: list[float | int | None] = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            result.append(None)
        elif np.issubdtype(values.dtype, np.integer):
            result.append(int(number))
        else:
            result.append(number)
    return result


def _number(request: dict[str, Any], name: str, default: float) -> float:
    value = request.get(name, default)
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one parsed LAS JSON file from an already-parsed request object."""
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
        parsed_path = WorkspacePathResolver(
            workspace_dir, parsed_relative, "parsed_path"
        ).resolve()
        parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
        raw_arrays = parsed.get("data_arrays")
        if not isinstance(raw_arrays, dict):
            raise ValueError("parsed JSON must contain data_arrays")
        arrays = {
            str(name): _array(values)
            for name, values in raw_arrays.items()
            if isinstance(values, list)
        }
        depth = arrays.get("DEPTH")
        if depth is None:
            raise ValueError("DEPTH curve required but not found")
        parameters = {
            "area_acres": _number(request, "area_acres", DEFAULT_AREA_ACRES),
            "matrix_density": _number(
                request, "matrix_density", DEFAULT_MATRIX_DENSITY
            ),
            "fluid_density": _number(request, "fluid_density", DEFAULT_FLUID_DENSITY),
            "a": _number(request, "a", DEFAULT_A),
            "m": _number(request, "m", DEFAULT_M),
            "n": _number(request, "n", DEFAULT_N),
            "rw": _number(request, "rw", DEFAULT_RW),
            "phie_min": _number(request, "phie_min", DEFAULT_PHIE_MIN),
            "sw_max": _number(request, "sw_max", DEFAULT_SW_MAX),
            "vsh_max": _number(request, "vsh_max", DEFAULT_VSH_MAX),
            "boi": _number(request, "boi", DEFAULT_BOI),
            "rf": _number(request, "rf", DEFAULT_RF),
        }
        result = run_full_evaluation(arrays, depth, **parameters)
        if result["status"] != "success":
            return {
                "status": "error",
                "error": "; ".join(result["warnings"]),
                "warnings": result["warnings"],
            }
        output_path = output_root / f"{well_id}_evaluation.json"
        sample_columns = {
            "DEPTH": _json_values(depth),
            "GR": _json_values(arrays.get("GR", np.full(len(depth), np.nan))),
            "RHOB": _json_values(arrays.get("RHOB", np.full(len(depth), np.nan))),
            "NPHI": _json_values(arrays.get("NPHI", np.full(len(depth), np.nan))),
            "RT": _json_values(arrays.get("RT", np.full(len(depth), np.nan))),
            "PHIE": _json_values(arrays["PHIE"]),
            "SW": _json_values(arrays["SW_ARCHIE"]),
            "NET_PAY_FLAG": _json_values(arrays["NET_PAY_FLAG"]),
        }
        payload = {
            "status": "success",
            "well_id": well_id,
            "source_path": str(parsed_path),
            "output_path": str(output_path),
            "parameters": parameters,
            "qc_summary": result["qc"],
            "gr_baselines": result["baselines"],
            "net_pay_summary": result["net_pay"],
            "zones": result["zones"],
            "ooip": result["ooip"],
            "warnings": result["warnings"],
            "sample_columns": sample_columns,
        }
        EvaluationWriter(output_path, payload).write()
        return payload
    except (ValueError, OSError, json.JSONDecodeError, TypeError) as error:
        return {"status": "error", "error": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run petrophysical evaluation.")
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
