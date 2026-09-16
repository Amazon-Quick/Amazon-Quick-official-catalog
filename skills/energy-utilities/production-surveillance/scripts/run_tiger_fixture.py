"""
description: Read a synthetic 27-well production fixture and run deterministic field, well, reservoir, and safety analyses without network or operational side effects.
last_updated: 2026-09-14
origin: original
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

MAX_READING_MINUTES = 10_080
MAX_HISTORY_DAYS = 3_650
ANOMALY_START = {
    "wellhead_pressure_psi": 4180.0,
    "gas_rate_mmscfd": 38.0,
    "wellhead_temp_degc": 19.8,
}
ROUNDING = {
    "wellhead_pressure_psi": 0,
    "tubing_pressure_psi": 0,
    "annulus_pressure_psi": 0,
    "gas_rate_mmscfd": 3,
    "water_rate_bwpd": 0,
    "water_cut_pct": 4,
    "wellhead_temp_degc": 3,
    "choke_position_pct": 3,
    "meg_injection_rate_m3hr": 4,
    "sand_rate_pptb": 5,
}
MAASP_LIMIT_PSI = 2500.0
HIPPS_TRIP_PSI = 6000.0
CRITICAL_DRAWDOWN_PSI = 3000.0
SAND_ADVISORY_LIMIT_PPTB = 1.0
WATER_CUT_LIMIT_PCT = 15.0
GAS_COMPRESSIBILITY = 0.90
METRES_TO_FEET = 3.28084
CELSIUS_TO_FAHRENHEIT_SCALE = 9.0 / 5.0
CELSIUS_TO_FAHRENHEIT_OFFSET = 32.0
RANKINE_OFFSET = 459.67


@dataclass(frozen=True)
class TigerRequest:
    """Validated request for one fixture operation."""

    operation: str
    arguments: dict[str, Any]


class FixtureReader:
    """Read one JSON fixture from disk."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> dict[str, Any]:
        with self._path.open(encoding="utf-8") as source:
            value = json.load(source)
        if not isinstance(value, dict):
            raise ValueError("fixture root must be a JSON object")
        return value


class RequestParser:
    """Parse and validate an inline JSON request."""

    def __init__(self, request_json: str) -> None:
        self._request_json = request_json

    def parse(self) -> TigerRequest:
        try:
            value = json.loads(self._request_json)
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
        return TigerRequest(operation=operation, arguments=arguments)


class TigerFixtureAnalyzer:
    """Run deterministic read-only analyses against an injected fixture."""

    def __init__(self, fixture: dict[str, Any]) -> None:
        self._fixture = fixture

    def execute(self, request: TigerRequest) -> dict[str, Any]:
        operations = {
            "field_summary": self._field_summary,
            "well_deviations": self._well_deviations,
            "manifold_pressures": self._manifold_pressures,
            "well_readings": self._well_readings,
            "well_history": self._well_history,
            "completion_data": self._completion_data,
            "alarms": self._alarms,
            "reservoir_constraints": self._reservoir_constraints,
            "safety_compliance": self._safety_compliance,
        }
        operation = operations.get(request.operation)
        if operation is None:
            return self._error(
                "UNKNOWN_OPERATION",
                f"unsupported operation: {request.operation}",
                supported_operations=sorted(operations),
            )
        try:
            return operation(request.arguments)
        except (KeyError, TypeError, ValueError) as error:
            return self._error("INVALID_INPUT", str(error))

    def _field_summary(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments:
            raise ValueError("field_summary accepts no arguments")
        return copy.deepcopy(self._fixture)

    def _well_deviations(self, arguments: dict[str, Any]) -> dict[str, Any]:
        threshold = self._finite_number(arguments.get("threshold_pct", 10.0))
        if threshold < 0:
            raise ValueError("threshold_pct must be non-negative")
        end_time = self._parse_timestamp(str(self._fixture["timestamp"]))
        deviations: list[dict[str, Any]] = []
        evaluated_wells = 0
        for well in self._fixture["wells"]:
            current_rate = float(well["measurements"]["gas_rate_mmscfd"])
            if well["status"] == "SHUT_IN" or current_rate <= 0:
                continue
            evaluated_wells += 1
            historical_rates: list[float] = []
            for age_minutes in range(1439, -1, -1):
                timestamp = end_time - timedelta(minutes=age_minutes)
                progress = max(0.0, min(1.0, 1.0 - age_minutes / 240.0))
                measurements = self._jitter_measurements(well, timestamp, progress)
                historical_rates.append(float(measurements["gas_rate_mmscfd"]))
            rolling_average = sum(historical_rates) / len(historical_rates)
            deviation_pct = (current_rate - rolling_average) / rolling_average * 100.0
            if abs(deviation_pct) >= threshold:
                deviations.append(
                    {
                        "well_id": well["well_id"],
                        "parameter": "gas_rate_mmscfd",
                        "current_value": round(current_rate, 5),
                        "rolling_average_24hr": round(rolling_average, 5),
                        "deviation_pct": round(deviation_pct, 2),
                        "trend": "declining" if deviation_pct < 0 else "increasing",
                    }
                )
        deviations.sort(key=lambda item: abs(item["deviation_pct"]), reverse=True)
        return {
            "status": "success",
            "operation": "well_deviations",
            "timestamp": self._fixture["timestamp"],
            "window_hours": 24,
            "threshold_pct": threshold,
            "evaluated_wells": evaluated_wells,
            "deviation_count": len(deviations),
            "deviations": deviations,
        }

    def _manifold_pressures(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if arguments:
            raise ValueError("manifold_pressures accepts no arguments")
        grouped: dict[str, list[dict[str, Any]]] = {}
        for well in self._fixture["wells"]:
            grouped.setdefault(str(well["manifold"]), []).append(well)
        metadata = {
            str(item["manifold_id"]): item for item in self._fixture["manifolds"]
        }
        manifolds: list[dict[str, Any]] = []
        for manifold_id, wells in grouped.items():
            pressures = [
                float(well["measurements"]["wellhead_pressure_psi"]) for well in wells
            ]
            manifolds.append(
                {
                    "manifold_id": manifold_id,
                    "pressure_psi": round(sum(pressures) / len(pressures)),
                    "min_wellhead_pressure_psi": round(min(pressures)),
                    "max_wellhead_pressure_psi": round(max(pressures)),
                    "wells_connected": len(wells),
                    "producing_wells": sum(
                        well["status"] != "SHUT_IN"
                        and float(well["measurements"]["gas_rate_mmscfd"]) > 0
                        for well in wells
                    ),
                    "flow_rate_mmscfd": round(
                        sum(
                            float(well["measurements"]["gas_rate_mmscfd"])
                            for well in wells
                        ),
                        3,
                    ),
                    "status": metadata.get(manifold_id, {}).get("status", "UNKNOWN"),
                }
            )
        manifolds.sort(key=lambda item: item["manifold_id"])
        return {
            "status": "success",
            "operation": "manifold_pressures",
            "timestamp": self._fixture["timestamp"],
            "pressure_basis": "average connected-well wellhead pressure",
            "manifolds": manifolds,
        }

    def _well_readings(self, arguments: dict[str, Any]) -> dict[str, Any]:
        well_ids = arguments.get("well_ids")
        minutes = arguments.get("minutes", 30)
        if not isinstance(well_ids, list) or not well_ids:
            raise ValueError("well_ids must be a non-empty list")
        if isinstance(minutes, bool) or not isinstance(minutes, int):
            raise ValueError("minutes must be an integer")
        if not 1 <= minutes <= MAX_READING_MINUTES:
            raise ValueError(f"minutes must be between 1 and {MAX_READING_MINUTES}")
        well_map = self._well_map()
        normalized_ids = [str(well_id).strip().upper() for well_id in well_ids]
        unknown = sorted(set(normalized_ids) - set(well_map))
        if unknown:
            return self._error(
                "UNKNOWN_WELL",
                "one or more well IDs are unknown",
                unknown_well_ids=unknown,
                valid_well_ids=sorted(well_map),
            )
        end_time = self._parse_timestamp(str(self._fixture["timestamp"]))
        start_time = end_time - timedelta(minutes=minutes - 1)
        result_wells: list[dict[str, Any]] = []
        for well_id in normalized_ids:
            well = well_map[well_id]
            readings: list[dict[str, Any]] = []
            for offset in range(minutes):
                timestamp = start_time + timedelta(minutes=offset)
                age_minutes = (end_time - timestamp).total_seconds() / 60.0
                progress = max(0.0, min(1.0, 1.0 - age_minutes / 240.0))
                readings.append(
                    {
                        "timestamp": self._format_timestamp(timestamp),
                        "measurements": self._jitter_measurements(
                            well, timestamp, progress
                        ),
                        "status": well["status"],
                    }
                )
            result_wells.append({"well_id": well_id, "readings": readings})
        return {
            "status": "success",
            "operation": "well_readings",
            "timestamp": self._fixture["timestamp"],
            "interval_minutes": 1,
            "window_minutes": minutes,
            "wells": result_wells,
        }

    def _well_history(self, arguments: dict[str, Any]) -> dict[str, Any]:
        well_id = str(arguments.get("well_id", "")).strip().upper()
        days = arguments.get("days", 7)
        if not well_id:
            raise ValueError("well_id is required")
        if isinstance(days, bool) or not isinstance(days, int):
            raise ValueError("days must be an integer")
        if not 1 <= days <= MAX_HISTORY_DAYS:
            raise ValueError(f"days must be between 1 and {MAX_HISTORY_DAYS}")
        well = self._well_map().get(well_id)
        if well is None:
            return self._error("UNKNOWN_WELL", "unknown well ID", well_id=well_id)
        end_date = self._parse_timestamp(str(self._fixture["timestamp"])).date()
        measurements = well["measurements"]
        cumulative_gas = 0.0
        history: list[dict[str, Any]] = []
        for index in range(days):
            date = end_date - timedelta(days=days - index - 1)
            rng = random.Random(  # nosec B311 - seeded synthetic jitter, not security randomness
                f"history:{well_id}:{date.isoformat()}"
            )
            recency = index / max(days - 1, 1)
            if well_id == "SK-14":
                pressure = (
                    ANOMALY_START["wellhead_pressure_psi"]
                    + (
                        measurements["wellhead_pressure_psi"]
                        - ANOMALY_START["wellhead_pressure_psi"]
                    )
                    * recency
                )
                rate = (
                    ANOMALY_START["gas_rate_mmscfd"]
                    + (
                        measurements["gas_rate_mmscfd"]
                        - ANOMALY_START["gas_rate_mmscfd"]
                    )
                    * recency
                )
                temperature = (
                    ANOMALY_START["wellhead_temp_degc"]
                    + (
                        measurements["wellhead_temp_degc"]
                        - ANOMALY_START["wellhead_temp_degc"]
                    )
                    * recency
                )
            else:
                pressure = float(measurements["wellhead_pressure_psi"]) * (
                    1.0 + rng.uniform(-0.029, 0.029)
                )
                rate = float(measurements["gas_rate_mmscfd"]) * (
                    1.0 + rng.uniform(-0.029, 0.029)
                )
                temperature = float(measurements["wellhead_temp_degc"]) * (
                    1.0 + rng.uniform(-0.029, 0.029)
                )
            if well["status"] == "SHUT_IN":
                rate = 0.0
                uptime = 0.0
            else:
                uptime = round(99.0 + rng.uniform(0.0, 1.0), 2)
            cumulative_gas += max(rate, 0.0)
            history.append(
                {
                    "date": date.isoformat(),
                    "avg_pressure_psi": round(pressure),
                    "avg_rate_mmscfd": round(rate, 3),
                    "avg_temp_degc": round(temperature, 2),
                    "cumulative_gas_mmscf": round(cumulative_gas, 3),
                    "uptime_pct": uptime,
                }
            )
        return {
            "status": "success",
            "operation": "well_history",
            "well_id": well_id,
            "days": days,
            "history": history,
        }

    def _completion_data(self, arguments: dict[str, Any]) -> dict[str, Any]:
        well_id = str(arguments.get("well_id", "")).strip().upper()
        if not well_id:
            raise ValueError("well_id is required")
        well = self._well_map().get(well_id)
        if well is None:
            return self._error("UNKNOWN_WELL", "unknown well ID", well_id=well_id)
        well_number = int(well_id.split("-")[1])
        completion_type = str(well["completion_type"])
        horizontal = completion_type.startswith("HORIZONTAL")
        fractured = completion_type == "HORIZONTAL_FRAC"
        lateral_length = 1200 + ((well_number % 5) - 2) * 50 if horizontal else 0
        frac_stages = 12 + (well_number % 3) - 1 if fractured else 0
        total_depth = int(well["total_depth_m"])
        interval_bottom = total_depth - 160
        completion: dict[str, Any] = {
            "type": completion_type,
            "lateral_length_m": lateral_length,
            "frac_stages": frac_stages,
            "perforation_intervals": [
                {
                    "top_md_m": interval_bottom - 110,
                    "bottom_md_m": interval_bottom - 70,
                },
                {"top_md_m": interval_bottom - 40, "bottom_md_m": interval_bottom},
            ],
            "casing_sizes": [
                "13 3/8 in surface",
                "9 5/8 in intermediate",
                "7 in production",
            ],
            "tubing_size_in": 4.5,
            "packer_depth_m": total_depth - 300,
            "reservoir": {
                "formation": "Synthetic Turbidite Reservoir",
                "porosity_pct": round(17.8 + (well_number % 5) * 0.35, 2),
                "permeability_md": 38 + (well_number % 7) * 3,
                "reservoir_pressure_psi": 8500 + well_number * 18,
                "reservoir_temp_degc": round(91.5 + well["water_depth_m"] / 600, 1),
                "gas_gravity": 0.65,
                "h2s_ppm": 100 + (well_number % 6) * 10,
                "co2_pct": round(1.8 + (well_number % 4) * 0.1, 1),
            },
        }
        if well_id == "SK-14":
            completion.update(
                {
                    "lateral_length_m": 1200,
                    "frac_stages": 12,
                    "perforation_intervals": [
                        {"top_md_m": 3980, "bottom_md_m": 4020},
                        {"top_md_m": 4050, "bottom_md_m": 4090},
                    ],
                    "packer_depth_m": 3950,
                }
            )
            completion["reservoir"].update(
                {
                    "porosity_pct": 18.5,
                    "permeability_md": 45,
                    "reservoir_pressure_psi": 8750,
                    "reservoir_temp_degc": 95,
                    "h2s_ppm": 120,
                    "co2_pct": 2.1,
                }
            )
        return {
            "status": "success",
            "operation": "completion_data",
            "well_id": well_id,
            "manifold": well["manifold"],
            "water_depth_m": well["water_depth_m"],
            "total_depth_m": total_depth,
            "completion": completion,
        }

    def _alarms(self, arguments: dict[str, Any]) -> dict[str, Any]:
        severity = str(arguments.get("severity", "all")).strip().upper()
        well_id = str(arguments.get("well_id", "")).strip().upper()
        if severity not in {"ALL", "AMBER", "RED"}:
            raise ValueError("severity must be one of: all, amber, red")
        alarms: list[dict[str, Any]] = []
        for well in self._fixture["wells"]:
            if well_id and well["well_id"] != well_id:
                continue
            for source_alarm in well.get("alarms", []):
                if severity != "ALL" and source_alarm["severity"].upper() != severity:
                    continue
                alarm = copy.deepcopy(source_alarm)
                alarm["well_id"] = well["well_id"]
                alarm["acknowledgement_available"] = False
                alarm["execution_status"] = "not_executed"
                alarms.append(alarm)
        return {
            "status": "success",
            "operation": "alarms",
            "timestamp": self._fixture["timestamp"],
            "severity_filter": severity.lower(),
            "well_id_filter": well_id or None,
            "precedent_basis": "active_alarm_set",
            "total_alarms": len(alarms),
            "alarms": alarms,
        }

    def _reservoir_constraints(self, arguments: dict[str, Any]) -> dict[str, Any]:
        well_id = str(arguments.get("well_id", "")).strip().upper()
        if not well_id:
            raise ValueError("well_id is required")
        proposed_rate_raw = arguments.get("proposed_rate_mmscfd")
        proposed_rate = (
            None
            if proposed_rate_raw is None
            else self._finite_number(proposed_rate_raw)
        )
        completion_result = self._completion_data({"well_id": well_id})
        if completion_result.get("status") != "success":
            return completion_result
        well = self._well_map()[well_id]
        measurements = well["measurements"]
        reservoir = completion_result["completion"]["reservoir"]
        required_fields = (
            "reservoir_pressure_psi",
            "reservoir_temp_degc",
            "gas_gravity",
        )
        missing = [field for field in required_fields if field not in reservoir]
        if missing:
            return {
                "status": "success",
                "operation": "reservoir_constraints",
                "well_id": well_id,
                "verdict": "UNKNOWN",
                "missing_fields": missing,
            }
        intervals = completion_result["completion"]["perforation_intervals"]
        mid_depth_m = sum(
            (float(item["top_md_m"]) + float(item["bottom_md_m"])) / 2.0
            for item in intervals
        ) / len(intervals)
        reservoir_temp_f = (
            float(reservoir["reservoir_temp_degc"]) * CELSIUS_TO_FAHRENHEIT_SCALE
            + CELSIUS_TO_FAHRENHEIT_OFFSET
        )
        wellhead_temp_f = (
            float(measurements["wellhead_temp_degc"]) * CELSIUS_TO_FAHRENHEIT_SCALE
            + CELSIUS_TO_FAHRENHEIT_OFFSET
        )
        average_temp_rankine = (
            reservoir_temp_f + wellhead_temp_f
        ) / 2.0 + RANKINE_OFFSET
        exponent = (
            0.01875
            * float(reservoir["gas_gravity"])
            * mid_depth_m
            * METRES_TO_FEET
            / (GAS_COMPRESSIBILITY * average_temp_rankine)
        )
        flowing_bottomhole_pressure = float(
            measurements["tubing_pressure_psi"]
        ) * math.exp(exponent)
        drawdown = (
            float(reservoir["reservoir_pressure_psi"]) - flowing_bottomhole_pressure
        )
        current_rate = float(measurements["gas_rate_mmscfd"])
        evaluated_drawdown = drawdown
        if proposed_rate is not None:
            if proposed_rate < 0:
                raise ValueError("proposed_rate_mmscfd must be non-negative")
            if current_rate <= 0:
                return self._error(
                    "UNAVAILABLE_RATE_BASIS",
                    "cannot scale proposed drawdown from a non-producing well",
                )
            evaluated_drawdown = drawdown * proposed_rate / current_rate
        drawdown_utilisation = 100.0 * evaluated_drawdown / CRITICAL_DRAWDOWN_PSI
        sand_utilisation = (
            100.0 * float(measurements["sand_rate_pptb"]) / SAND_ADVISORY_LIMIT_PPTB
        )
        water_utilisation = (
            100.0 * float(measurements["water_cut_pct"]) / WATER_CUT_LIMIT_PCT
        )
        history = self._well_history({"well_id": well_id, "days": 7})["history"]
        pressure_direction = self._direction(
            float(history[0]["avg_pressure_psi"]),
            float(history[-1]["avg_pressure_psi"]),
        )
        rate_direction = self._direction(
            float(history[0]["avg_rate_mmscfd"]),
            float(history[-1]["avg_rate_mmscfd"]),
        )
        diagnosis = self._decline_diagnosis(pressure_direction, rate_direction)
        proposed_increase = proposed_rate is not None and proposed_rate > current_rate
        if drawdown_utilisation > 100.0 or (
            proposed_increase and sand_utilisation >= 80.0
        ):
            verdict = "BLOCK"
        elif drawdown_utilisation >= 80.0 or sand_utilisation >= 80.0:
            verdict = "CAUTION"
        else:
            verdict = "PASS"
        return {
            "status": "success",
            "operation": "reservoir_constraints",
            "well_id": well_id,
            "verdict": verdict,
            "binding_constraint": (
                "sand_rate" if sand_utilisation >= drawdown_utilisation else "drawdown"
            ),
            "drawdown": {
                "reservoir_pressure_psi": reservoir["reservoir_pressure_psi"],
                "fbhp_psi": round(flowing_bottomhole_pressure),
                "fbhp_basis": "estimated_static_column",
                "current_drawdown_psi": round(drawdown),
                "evaluated_drawdown_psi": round(evaluated_drawdown),
                "critical_drawdown_psi": CRITICAL_DRAWDOWN_PSI,
                "utilisation_pct": round(drawdown_utilisation, 1),
            },
            "sand": {
                "rate_pptb": measurements["sand_rate_pptb"],
                "limit_pptb": SAND_ADVISORY_LIMIT_PPTB,
                "utilisation_pct": round(sand_utilisation, 1),
            },
            "water": {
                "cut_pct": measurements["water_cut_pct"],
                "limit_pct": WATER_CUT_LIMIT_PCT,
                "utilisation_pct": round(water_utilisation, 1),
                "water_trend_basis": "60_minute_window_only",
            },
            "decline_diagnosis": {
                "pressure_trend": pressure_direction,
                "rate_trend": rate_direction,
                "diagnosis": diagnosis,
                "reservoir_driven": diagnosis == "RESERVOIR_DRIVEN",
            },
            "threshold_basis": "synthetic_fixture",
        }

    def _safety_compliance(self, arguments: dict[str, Any]) -> dict[str, Any]:
        well_id = str(arguments.get("well_id", "")).strip().upper()
        proposed_action = str(arguments.get("proposed_action", "")).strip()
        if not well_id or not proposed_action:
            raise ValueError("well_id and proposed_action are required")
        completion_result = self._completion_data({"well_id": well_id})
        if completion_result.get("status") != "success":
            return completion_result
        well = self._well_map()[well_id]
        measurements = well["measurements"]
        reservoir = completion_result["completion"]["reservoir"]
        history_result = self._well_history({"well_id": well_id, "days": 7})
        history = history_result["history"]
        maasp_utilisation = (
            100.0 * float(measurements["annulus_pressure_psi"]) / MAASP_LIMIT_PSI
        )
        hipps_utilisation = (
            100.0 * float(measurements["tubing_pressure_psi"]) / HIPPS_TRIP_PSI
        )
        buildup = (
            float(history[-1]["avg_pressure_psi"])
            - float(history[0]["avg_pressure_psi"])
        ) / max(len(history) - 1, 1)
        days_to_trip = None
        if buildup > 0:
            days_to_trip = (
                HIPPS_TRIP_PSI - float(measurements["tubing_pressure_psi"])
            ) / buildup
        action_class = str(arguments.get("action_class", "")).strip().lower()
        if not action_class:
            action_class = self._classify_action(proposed_action)
        if action_class not in {"chemical", "choke", "thermal", "mechanical", "other"}:
            raise ValueError(
                "action_class must be chemical, choke, thermal, mechanical, or other"
            )
        if maasp_utilisation > 100.0 or hipps_utilisation > 100.0:
            verdict = "BLOCK"
        elif maasp_utilisation >= 80.0 or hipps_utilisation >= 80.0:
            verdict = "CAUTION"
        else:
            verdict = "PASS"
        alarms = self._alarms({"severity": "all", "well_id": well_id})
        return {
            "status": "success",
            "operation": "safety_compliance",
            "well_id": well_id,
            "proposed_action": proposed_action,
            "action_class": action_class,
            "verdict": verdict,
            "blocking": verdict == "BLOCK",
            "checks": [
                {
                    "check": "maasp",
                    "value_psi": measurements["annulus_pressure_psi"],
                    "limit_psi": MAASP_LIMIT_PSI,
                    "utilisation_pct": round(maasp_utilisation, 1),
                    "verdict": self._utilisation_verdict(maasp_utilisation),
                },
                {
                    "check": "hipps_proximity",
                    "value_psi": measurements["tubing_pressure_psi"],
                    "limit_psi": HIPPS_TRIP_PSI,
                    "utilisation_pct": round(hipps_utilisation, 1),
                    "verdict": self._utilisation_verdict(hipps_utilisation),
                    "days_to_trip": None
                    if days_to_trip is None
                    else round(days_to_trip, 1),
                    "basis": "synthetic seven-day pressure trend",
                },
                {
                    "check": "sour_service",
                    "h2s_ppm": reservoir.get("h2s_ppm"),
                    "verdict": "REVIEW_REQUIRED",
                    "note": "Synthetic sour-service scenario. Qualified review is required.",
                },
                {
                    "check": "co2_and_water",
                    "co2_pct": reservoir.get("co2_pct"),
                    "water_cut_pct": measurements["water_cut_pct"],
                    "verdict": "REVIEW_REQUIRED",
                },
            ],
            "precedent": {
                "precedent_basis": "active_alarm_set",
                "matched_alarms": [alarm["type"] for alarm in alarms["alarms"]],
                "historical_outcome_available": False,
            },
            "permit_posture": self._permit_posture(action_class),
            "threshold_basis": "synthetic_fixture",
            "execution_status": "not_executed",
        }

    def _well_map(self) -> dict[str, dict[str, Any]]:
        return {str(well["well_id"]): well for well in self._fixture["wells"]}

    def _jitter_measurements(
        self,
        well: dict[str, Any],
        timestamp: datetime,
        anomaly_progress: float | None,
    ) -> dict[str, Any]:
        baseline = well["measurements"]
        rng = random.Random(  # nosec B311 - seeded synthetic jitter, not security randomness
            f"{well['well_id']}:{timestamp.isoformat()}"
        )
        result: dict[str, Any] = {}
        for name, value in baseline.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                result[name] = value
                continue
            if well["well_id"] == "SK-14" and name in ANOMALY_START:
                progress = 1.0 if anomaly_progress is None else anomaly_progress
                generated = (
                    ANOMALY_START[name]
                    + (float(value) - ANOMALY_START[name]) * progress
                )
            elif value == 0:
                generated = 0.0
            else:
                generated = float(value) * (1.0 + rng.uniform(-0.029, 0.029))
            digits = ROUNDING.get(name, 3)
            rounded = round(generated, digits)
            result[name] = int(rounded) if digits == 0 else rounded
        return result

    def _classify_action(self, action: str) -> str:
        lowered = action.lower()
        if "meg" in lowered or "chemical" in lowered or "inhibitor" in lowered:
            return "chemical"
        if "choke" in lowered:
            return "choke"
        if "heat" in lowered or "thermal" in lowered:
            return "thermal"
        if any(word in lowered for word in ("intervention", "pig", "depressur")):
            return "mechanical"
        return "other"

    def _permit_posture(self, action_class: str) -> str:
        return {
            "chemical": "verify commissioned envelope and operating authority",
            "choke": "production-supervisor review required",
            "thermal": "permit and energy-isolation review required",
            "mechanical": "permit, isolation, and engineering review required",
            "other": "qualified review required before classification",
        }[action_class]

    def _decline_diagnosis(self, pressure: str, rate: str) -> str:
        if pressure == "FALLING" and rate == "FALLING":
            return "RESERVOIR_DRIVEN"
        if pressure == "RISING" and rate == "FALLING":
            return "DOWNSTREAM_RESTRICTION"
        if pressure == "RISING" and rate == "RISING":
            return "FACILITY_OR_CHOKE_CHANGE"
        if pressure == "STABLE" and rate == "FALLING":
            return "LIQUID_LOADING_OR_PARTIAL_RESTRICTION"
        return "INCONCLUSIVE"

    def _direction(self, first: float, last: float) -> str:
        tolerance = max(abs(first) * 0.01, 0.01)
        if last > first + tolerance:
            return "RISING"
        if last < first - tolerance:
            return "FALLING"
        return "STABLE"

    def _utilisation_verdict(self, utilisation: float) -> str:
        if utilisation > 100.0:
            return "BLOCK"
        if utilisation >= 80.0:
            return "CAUTION"
        return "PASS"

    def _finite_number(self, value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError("numeric values must not be booleans")
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("numeric values must be finite")
        return parsed

    def _parse_timestamp(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _format_timestamp(self, value: datetime) -> str:
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")

    def _error(self, code: str, message: str, **details: Any) -> dict[str, Any]:
        result: dict[str, Any] = {"status": "error", "code": code, "message": message}
        result.update(details)
        return result


class JsonOutput:
    """Serialize one result as JSON on stdout."""

    def __init__(self, value: dict[str, Any]) -> None:
        self._value = value

    def write(self) -> None:
        print(json.dumps(self._value, indent=2, sort_keys=True))


class TigerCommand:
    """Facade that parses input, reads the fixture, and emits one JSON result."""

    def __init__(self, fixture_path: Path, request_json: str) -> None:
        self._fixture_path = fixture_path
        self._request_json = request_json

    def run(self) -> int:
        request_object = json.loads(self._request_json)
        request_object["fixture"] = str(self._fixture_path)
        result = run(request_object)
        JsonOutput(result).write()
        return 0 if result.get("status") == "success" else 2


def run(request_object: dict[str, Any]) -> dict[str, Any]:
    """Execute one request object and return the result dict.

    ``request_object`` carries ``operation``, optional ``arguments``, and
    ``fixture`` (path to the fixture JSON). This is the entry point for the
    Amazon Quick sandbox, where the module is executed from source and this
    function is called directly.
    """
    try:
        fixture_path = request_object.get("fixture")
        if not fixture_path:
            raise ValueError("fixture path is required")
        payload = {k: v for k, v in request_object.items() if k != "fixture"}
        request = RequestParser(json.dumps(payload)).parse()
        fixture = FixtureReader(Path(str(fixture_path))).read()
        return TigerFixtureAnalyzer(fixture).execute(request)
    except (OSError, ValueError) as error:
        return {"status": "error", "code": "INPUT_ERROR", "message": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic analyses against a synthetic well fixture."
    )
    parser.add_argument("--fixture", required=True, help="Path to the fixture JSON.")
    parser.add_argument(
        "--request-json",
        required=True,
        help="JSON object with operation and optional arguments.",
    )
    arguments = parser.parse_args()
    return TigerCommand(Path(arguments.fixture), arguments.request_json).run()


if __name__ == "__main__":
    raise SystemExit(main())
