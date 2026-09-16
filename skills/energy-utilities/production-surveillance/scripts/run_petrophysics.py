"""
description: Run deterministic density porosity, shale volume, effective porosity, Archie water saturation, net-pay, and MEG-inhibited hydrate calculations from JSON inputs.
last_updated: 2026-09-14
origin: original
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_MATRIX_DENSITY_GCC = 2.65
DEFAULT_FLUID_DENSITY_GCC = 1.0
DEFAULT_ARCHIE_A = 1.0
DEFAULT_ARCHIE_M = 2.0
DEFAULT_ARCHIE_N = 2.0
DEFAULT_POROSITY_MIN = 0.06
DEFAULT_SW_MAX = 0.60
DEFAULT_VSHALE_MAX = 0.40
HYDRATE_LOG_INTERCEPT = -74.78
HYDRATE_LOG_SLOPE = 11.243
HAMMERSCHMIDT_CONSTANT = 2335.0
MEG_MOLECULAR_WEIGHT = 62.07
FAHRENHEIT_TO_CELSIUS_SCALE = 5.0 / 9.0


@dataclass(frozen=True)
class PetrophysicsRequest:
    """Validated request for one calculation."""

    operation: str
    arguments: dict[str, Any]


class RequestParser:
    """Parse a JSON request from inline text or a file."""

    def __init__(self, request_json: str | None, input_path: Path | None) -> None:
        self._request_json = request_json
        self._input_path = input_path

    def parse(self) -> PetrophysicsRequest:
        if (self._request_json is None) == (self._input_path is None):
            raise ValueError("provide exactly one of --request-json or --input")
        if self._input_path is not None:
            text = self._input_path.read_text(encoding="utf-8")
        else:
            text = self._request_json or ""
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"request is not valid JSON: {error.msg}") from error
        if not isinstance(value, dict):
            raise ValueError("request root must be a JSON object")
        operation = value.get("operation")
        arguments = value.get("arguments", {})
        if not isinstance(operation, str) or not operation:
            raise ValueError("request.operation must be a non-empty string")
        if not isinstance(arguments, dict):
            raise ValueError("request.arguments must be a JSON object")
        return PetrophysicsRequest(operation=operation, arguments=arguments)


class PetrophysicsCalculator:
    """Perform one pure, deterministic petrophysics calculation."""

    def __init__(self, request: PetrophysicsRequest) -> None:
        self._request = request

    def calculate(self) -> dict[str, Any]:
        operations = {
            "density_porosity": self._density_porosity,
            "shale_volume": self._shale_volume,
            "effective_porosity": self._effective_porosity,
            "archie_water_saturation": self._archie_water_saturation,
            "net_pay": self._net_pay,
            "hydrate_equilibrium": self._hydrate_equilibrium,
        }
        operation = operations.get(self._request.operation)
        if operation is None:
            return self._error(
                "UNKNOWN_OPERATION",
                f"unsupported operation: {self._request.operation}",
                supported_operations=sorted(operations),
            )
        try:
            return operation(self._request.arguments)
        except (KeyError, TypeError, ValueError) as error:
            return self._error("INVALID_INPUT", str(error))

    def _density_porosity(self, arguments: dict[str, Any]) -> dict[str, Any]:
        bulk_density = self._array(arguments, "bulk_density_gcc")
        matrix_density = self._finite_number(
            arguments.get("matrix_density_gcc", DEFAULT_MATRIX_DENSITY_GCC),
            "matrix_density_gcc",
        )
        fluid_density = self._finite_number(
            arguments.get("fluid_density_gcc", DEFAULT_FLUID_DENSITY_GCC),
            "fluid_density_gcc",
        )
        if matrix_density == fluid_density:
            raise ValueError("matrix_density_gcc and fluid_density_gcc cannot be equal")
        porosity = np.clip(
            (matrix_density - bulk_density) / (matrix_density - fluid_density),
            0.0,
            1.0,
        )
        return self._success(
            "density_porosity",
            density_porosity_fraction=self._rounded_list(porosity),
            basis={
                "matrix_density_gcc": matrix_density,
                "fluid_density_gcc": fluid_density,
            },
        )

    def _shale_volume(self, arguments: dict[str, Any]) -> dict[str, Any]:
        gamma_ray = self._array(arguments, "gamma_ray_gapi")
        clean_gr = self._finite_number(arguments["clean_gr_gapi"], "clean_gr_gapi")
        shale_gr = self._finite_number(arguments["shale_gr_gapi"], "shale_gr_gapi")
        if clean_gr >= shale_gr:
            raise ValueError("clean_gr_gapi must be less than shale_gr_gapi")
        shale_volume = np.clip((gamma_ray - clean_gr) / (shale_gr - clean_gr), 0.0, 1.0)
        return self._success(
            "shale_volume",
            shale_volume_fraction=self._rounded_list(shale_volume),
            basis={"clean_gr_gapi": clean_gr, "shale_gr_gapi": shale_gr},
        )

    def _effective_porosity(self, arguments: dict[str, Any]) -> dict[str, Any]:
        total_porosity = self._array(arguments, "total_porosity_fraction")
        shale_volume = self._array(arguments, "shale_volume_fraction")
        self._same_length(total_porosity, shale_volume)
        effective = np.clip(total_porosity * (1.0 - shale_volume), 0.0, 1.0)
        return self._success(
            "effective_porosity",
            effective_porosity_fraction=self._rounded_list(effective),
        )

    def _archie_water_saturation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        resistivity = self._array(arguments, "true_resistivity_ohm_m")
        porosity = self._array(arguments, "total_porosity_fraction")
        self._same_length(resistivity, porosity)
        if np.any(resistivity <= 0.0) or np.any(porosity <= 0.0):
            raise ValueError("resistivity and total porosity values must be positive")
        rw = self._finite_number(
            arguments["water_resistivity_ohm_m"], "water_resistivity_ohm_m"
        )
        a = self._finite_number(arguments.get("a", DEFAULT_ARCHIE_A), "a")
        m = self._finite_number(arguments.get("m", DEFAULT_ARCHIE_M), "m")
        n = self._finite_number(arguments.get("n", DEFAULT_ARCHIE_N), "n")
        if rw <= 0.0 or a <= 0.0 or m <= 0.0 or n <= 0.0:
            raise ValueError("Archie parameters must be positive")
        saturation = np.clip(
            ((a * rw) / (resistivity * porosity**m)) ** (1.0 / n), 0.0, 1.0
        )
        return self._success(
            "archie_water_saturation",
            water_saturation_fraction=self._rounded_list(saturation),
            basis={"water_resistivity_ohm_m": rw, "a": a, "m": m, "n": n},
        )

    def _net_pay(self, arguments: dict[str, Any]) -> dict[str, Any]:
        depth = self._array(arguments, "depth_ft")
        effective_porosity = self._array(arguments, "effective_porosity_fraction")
        water_saturation = self._array(arguments, "water_saturation_fraction")
        shale_volume = self._array(arguments, "shale_volume_fraction")
        self._same_length(depth, effective_porosity, water_saturation, shale_volume)
        if depth.size < 2:
            raise ValueError("net_pay requires at least two depth samples")
        differences = np.diff(depth)
        if np.any(differences == 0.0):
            raise ValueError("depth_ft values must not repeat")
        depth_step = float(np.median(np.abs(differences)))
        porosity_min = self._finite_number(
            arguments.get("porosity_min", DEFAULT_POROSITY_MIN), "porosity_min"
        )
        sw_max = self._finite_number(arguments.get("sw_max", DEFAULT_SW_MAX), "sw_max")
        vshale_max = self._finite_number(
            arguments.get("vshale_max", DEFAULT_VSHALE_MAX), "vshale_max"
        )
        pay = (
            (effective_porosity >= porosity_min)
            & (water_saturation <= sw_max)
            & (shale_volume <= vshale_max)
        )
        net_pay_ft = float(np.count_nonzero(pay) * depth_step)
        gross_ft = float(depth.size * depth_step)
        average_porosity = (
            float(np.mean(effective_porosity[pay])) if np.any(pay) else 0.0
        )
        average_sw = float(np.mean(water_saturation[pay])) if np.any(pay) else 0.0
        return self._success(
            "net_pay",
            net_pay_ft=round(net_pay_ft, 2),
            gross_ft=round(gross_ft, 2),
            net_to_gross=round(net_pay_ft / gross_ft if gross_ft else 0.0, 4),
            average_porosity_in_pay=round(average_porosity, 4),
            average_water_saturation_in_pay=round(average_sw, 4),
            net_pay_flag=[int(value) for value in pay],
            cutoffs={
                "porosity_min": porosity_min,
                "sw_max": sw_max,
                "vshale_max": vshale_max,
            },
        )

    def _hydrate_equilibrium(self, arguments: dict[str, Any]) -> dict[str, Any]:
        pressure = self._finite_number(arguments["pressure_psi"], "pressure_psi")
        meg_weight_pct = self._finite_number(
            arguments.get("meg_weight_pct", 0.0), "meg_weight_pct"
        )
        current_temp_raw = arguments.get("current_temp_degc")
        if pressure <= 0.0:
            return self._error(
                "NON_POSITIVE_PRESSURE", "pressure_psi must be greater than zero"
            )
        if not 0.0 <= meg_weight_pct < 100.0:
            return self._error(
                "MEG_FRACTION_OUT_OF_RANGE", "meg_weight_pct must be in [0, 100)"
            )
        uninhibited = HYDRATE_LOG_INTERCEPT + HYDRATE_LOG_SLOPE * math.log(pressure)
        depression_degf = 0.0
        if meg_weight_pct > 0.0:
            depression_degf = (
                HAMMERSCHMIDT_CONSTANT
                * meg_weight_pct
                / (MEG_MOLECULAR_WEIGHT * (100.0 - meg_weight_pct))
            )
        depression_degc = depression_degf * FAHRENHEIT_TO_CELSIUS_SCALE
        inhibited = uninhibited - depression_degc
        result = self._success(
            "hydrate_equilibrium",
            pressure_psi=round(pressure, 1),
            uninhibited_equilibrium_degc=round(uninhibited, 2),
            meg_weight_pct=round(meg_weight_pct, 2),
            depression_degc=round(depression_degc, 2),
            inhibited_equilibrium_degc=round(inhibited, 2),
            method="log-linear lean-gas fit with Hammerschmidt MEG depression",
            assumptions=[
                "fixture-calibrated lean-gas correlation",
                "MEG value is aqueous-phase weight percent",
                "not a compositional flash or field-certified operating envelope",
            ],
        )
        if current_temp_raw is not None:
            current_temp = self._finite_number(current_temp_raw, "current_temp_degc")
            margin = current_temp - inhibited
            if margin < 0.0:
                risk_band = "FORMING"
            elif margin < 3.0:
                risk_band = "HIGH"
            elif margin < 6.0:
                risk_band = "MODERATE"
            else:
                risk_band = "LOW"
            result.update(
                {
                    "current_temp_degc": round(current_temp, 2),
                    "signed_scenario_margin_degc": round(margin, 2),
                    "risk_band": risk_band,
                }
            )
        return result

    def _array(self, arguments: dict[str, Any], name: str) -> np.ndarray:
        value = arguments.get(name)
        if not isinstance(value, list) or not value:
            raise ValueError(f"{name} must be a non-empty JSON array")
        try:
            array = np.asarray(value, dtype=float)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must contain only numbers") from error
        if array.ndim != 1 or not np.all(np.isfinite(array)):
            raise ValueError(
                f"{name} must be a one-dimensional array of finite numbers"
            )
        return array

    def _same_length(self, *arrays: np.ndarray) -> None:
        lengths = {array.size for array in arrays}
        if len(lengths) != 1:
            raise ValueError("input arrays must have the same length")

    def _finite_number(self, value: Any, name: str) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be numeric, not boolean")
        try:
            parsed = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must be numeric") from error
        if not math.isfinite(parsed):
            raise ValueError(f"{name} must be finite")
        return parsed

    def _rounded_list(self, values: np.ndarray) -> list[float]:
        return [round(float(value), 6) for value in values]

    def _success(self, operation: str, **values: Any) -> dict[str, Any]:
        return {"status": "success", "operation": operation, **values}

    def _error(self, code: str, message: str, **values: Any) -> dict[str, Any]:
        return {"status": "error", "code": code, "message": message, **values}


class JsonOutput:
    """Serialize one calculation result as JSON on stdout."""

    def __init__(self, value: dict[str, Any]) -> None:
        self._value = value

    def write(self) -> None:
        print(json.dumps(self._value, indent=2, sort_keys=True))


class PetrophysicsCommand:
    """Facade that parses a request, runs a calculation, and emits JSON."""

    def __init__(self, request_json: str | None, input_path: Path | None) -> None:
        self._request_json = request_json
        self._input_path = input_path

    def run(self) -> int:
        if self._request_json is None:
            payload = json.loads(
                Path(str(self._input_path)).read_text(encoding="utf-8")
            )
        else:
            payload = json.loads(self._request_json)
        result = run(payload)
        JsonOutput(result).write()
        return 0 if result.get("status") == "success" else 2


def run(request_object: dict[str, Any]) -> dict[str, Any]:
    """Execute one request object and return the result dict (sandbox entry point)."""
    try:
        request = RequestParser(json.dumps(request_object), None).parse()
        return PetrophysicsCalculator(request).calculate()
    except (OSError, ValueError) as error:
        return {"status": "error", "code": "INPUT_ERROR", "message": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic petrophysics calculations from JSON."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--request-json", help="Inline JSON request object.")
    input_group.add_argument("--input", type=Path, help="Path to a JSON request file.")
    arguments = parser.parse_args()
    return PetrophysicsCommand(arguments.request_json, arguments.input).run()


if __name__ == "__main__":
    raise SystemExit(main())
