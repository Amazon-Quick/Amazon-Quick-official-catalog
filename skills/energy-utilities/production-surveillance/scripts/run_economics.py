"""
description: Calculate deterministic synthetic production revenue, deferred production, operating cost, field value, reserves, acreage ranking, and Arps well economics from JSON inputs.
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

DAYS_PER_MONTH = 30.44
MONTHS_PER_YEAR = 12.0
SCF_PER_BOE = 6000.0
MAX_ROR_ITERATIONS = 100
ROR_TOLERANCE_USD = 100.0
MIN_ECONOMIC_RATE_BOEPD = 0.1
DEFAULT_ARPS_B = 1.2


@dataclass(frozen=True)
class EconomicsRequest:
    """Validated request for one economics operation."""

    operation: str
    arguments: dict[str, Any]


class RequestParser:
    """Parse a JSON request from inline text or a file."""

    def __init__(self, request_json: str | None, input_path: Path | None) -> None:
        self._request_json = request_json
        self._input_path = input_path

    def parse(self) -> EconomicsRequest:
        if (self._request_json is None) == (self._input_path is None):
            raise ValueError("provide exactly one of --request-json or --input")
        text = (
            self._input_path.read_text(encoding="utf-8")
            if self._input_path is not None
            else self._request_json or ""
        )
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
        return EconomicsRequest(operation=operation, arguments=arguments)


class EconomicsCalculator:
    """Perform one pure, deterministic economics calculation."""

    def __init__(self, request: EconomicsRequest) -> None:
        self._request = request

    def calculate(self) -> dict[str, Any]:
        operations = {
            "daily_revenue": self._daily_revenue,
            "deferred_production": self._deferred_production,
            "opex_per_boe": self._opex_per_boe,
            "field_value_metrics": self._field_value_metrics,
            "remaining_reserves": self._remaining_reserves,
            "rank_acreage": self._rank_acreage,
            "well_economics": self._well_economics,
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

    def _daily_revenue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        gas_rate = self._non_negative(arguments["gas_rate_mmscfd"], "gas_rate_mmscfd")
        gas_price = self._non_negative(
            arguments["gas_price_per_mmbtu"], "gas_price_per_mmbtu"
        )
        heating_value = self._non_negative(arguments["btu_per_scf"], "btu_per_scf")
        condensate_rate = self._non_negative(
            arguments.get("condensate_bpd", 0.0), "condensate_bpd"
        )
        condensate_price = self._non_negative(
            arguments.get("condensate_price_per_bbl", 0.0),
            "condensate_price_per_bbl",
        )
        ngl_rate = self._non_negative(arguments.get("ngl_bpd", 0.0), "ngl_bpd")
        ngl_price = self._non_negative(
            arguments.get("ngl_price_per_bbl", 0.0), "ngl_price_per_bbl"
        )
        gas_energy_mmbtu = gas_rate * heating_value
        gas_revenue = gas_energy_mmbtu * gas_price
        condensate_revenue = condensate_rate * condensate_price
        ngl_revenue = ngl_rate * ngl_price
        total_revenue = gas_revenue + condensate_revenue + ngl_revenue
        gas_volume_mcf = gas_rate * 1000.0
        total_boepd = gas_rate * 1_000_000.0 / SCF_PER_BOE + condensate_rate + ngl_rate
        return self._success(
            "daily_revenue",
            revenue_breakdown={
                "gas_revenue_usd": round(gas_revenue, 2),
                "condensate_revenue_usd": round(condensate_revenue, 2),
                "ngl_revenue_usd": round(ngl_revenue, 2),
                "total_daily_revenue_usd": round(total_revenue, 2),
            },
            unit_economics={
                "revenue_per_mcf": round(gas_revenue / gas_volume_mcf, 4)
                if gas_volume_mcf
                else 0.0,
                "revenue_per_boe": round(total_revenue / total_boepd, 2)
                if total_boepd
                else 0.0,
                "total_production_boepd": round(total_boepd, 2),
            },
            assumptions={
                "gas_price_per_mmbtu": gas_price,
                "btu_per_scf": heating_value,
                "condensate_price_per_bbl": condensate_price,
                "ngl_price_per_bbl": ngl_price,
            },
        )

    def _deferred_production(self, arguments: dict[str, Any]) -> dict[str, Any]:
        shut_in_wells = arguments.get("shut_in_wells", [])
        constrained_wells = arguments.get("constrained_wells", [])
        if not isinstance(shut_in_wells, list) or not isinstance(
            constrained_wells, list
        ):
            raise ValueError("shut_in_wells and constrained_wells must be arrays")
        gas_price = self._non_negative(
            arguments["gas_price_per_mmbtu"], "gas_price_per_mmbtu"
        )
        heating_value = self._non_negative(arguments["btu_per_scf"], "btu_per_scf")
        by_well: list[dict[str, Any]] = []
        for item in shut_in_wells:
            well = self._well_object(item, "shut_in_wells")
            by_well.append(
                {
                    "well_id": str(well["well_id"]),
                    "category": "shut_in",
                    "deferred_mmscfd": self._non_negative(
                        well.get("potential_rate_mmscfd", 0.0),
                        "potential_rate_mmscfd",
                    ),
                    "reason": str(well.get("reason", "")),
                }
            )
        for item in constrained_wells:
            well = self._well_object(item, "constrained_wells")
            current_rate = self._non_negative(
                well.get("current_rate_mmscfd", 0.0), "current_rate_mmscfd"
            )
            potential_rate = self._non_negative(
                well.get("potential_rate_mmscfd", 0.0), "potential_rate_mmscfd"
            )
            by_well.append(
                {
                    "well_id": str(well["well_id"]),
                    "category": "constrained",
                    "deferred_mmscfd": max(0.0, potential_rate - current_rate),
                    "reason": str(well.get("reason", "")),
                }
            )
        value_per_mmscfd = heating_value * gas_price
        for well in by_well:
            well["deferred_mmscfd"] = round(float(well["deferred_mmscfd"]), 5)
            well["deferred_usd_per_day"] = round(
                float(well["deferred_mmscfd"]) * value_per_mmscfd, 2
            )
        total_rate = sum(float(well["deferred_mmscfd"]) for well in by_well)
        total_value = sum(float(well["deferred_usd_per_day"]) for well in by_well)
        return self._success(
            "deferred_production",
            total_deferred_mmscfd=round(total_rate, 5),
            total_deferred_value_usd_per_day=round(total_value, 2),
            total_deferred_value_usd_per_month=round(total_value * 30.0, 2),
            annualised_deferred_usd=round(total_value * 365.0, 2),
            by_well=by_well,
            assumptions={
                "gas_price_per_mmbtu": gas_price,
                "btu_per_scf": heating_value,
            },
        )

    def _opex_per_boe(self, arguments: dict[str, Any]) -> dict[str, Any]:
        total_opex = self._non_negative(
            arguments["total_opex_daily_usd"], "total_opex_daily_usd"
        )
        production = self._non_negative(
            arguments["total_production_boepd"], "total_production_boepd"
        )
        benchmark = self._non_negative(
            arguments["benchmark_usd_per_boe"], "benchmark_usd_per_boe"
        )
        categories = arguments.get("cost_categories", {})
        if production == 0.0:
            raise ValueError("total_production_boepd must be greater than zero")
        if not isinstance(categories, dict):
            raise ValueError("cost_categories must be a JSON object")
        parsed_categories = {
            str(name): self._non_negative(value, f"cost_categories.{name}")
            for name, value in categories.items()
        }
        opex_per_boe = total_opex / production
        variance = opex_per_boe - benchmark
        return self._success(
            "opex_per_boe",
            opex_per_boe=round(opex_per_boe, 2),
            opex_per_mcfe=round(opex_per_boe / 6.0, 2),
            breakdown_per_boe={
                name: round(cost / production, 2)
                for name, cost in parsed_categories.items()
            },
            unallocated_opex_daily_usd=round(
                total_opex - sum(parsed_categories.values()), 2
            ),
            benchmark={
                "benchmark_usd_per_boe": benchmark,
                "variance_usd_per_boe": round(variance, 2),
                "variance_pct": round(variance / benchmark * 100.0, 2)
                if benchmark
                else None,
            },
        )

    def _field_value_metrics(self, arguments: dict[str, Any]) -> dict[str, Any]:
        production = self._object(arguments, "production_data")
        prices = self._object(arguments, "price_assumptions")
        targets = self._object(arguments, "targets")
        budget = self._object(arguments, "budget")
        elapsed_days = self._non_negative(production["days_in_month"], "days_in_month")
        remaining_days = self._non_negative(
            production["days_remaining"], "days_remaining"
        )
        if elapsed_days <= 0.0:
            raise ValueError("days_in_month must be greater than zero")
        revenue = self._daily_revenue(
            {
                "gas_rate_mmscfd": production["gas_rate_mmscfd"],
                "gas_price_per_mmbtu": prices["gas_price_per_mmbtu"],
                "btu_per_scf": prices["btu_per_scf"],
                "condensate_bpd": production.get("condensate_bpd", 0.0),
                "condensate_price_per_bbl": prices.get("condensate_price_per_bbl", 0.0),
            }
        )
        daily_revenue = float(revenue["revenue_breakdown"]["total_daily_revenue_usd"])
        total_days = elapsed_days + remaining_days
        monthly_revenue_target = self._non_negative(
            targets["monthly_revenue_target_usd"], "monthly_revenue_target_usd"
        )
        monthly_production_target = self._non_negative(
            targets["monthly_production_target_mmscf"],
            "monthly_production_target_mmscf",
        )
        monthly_afe = self._non_negative(budget["monthly_afe_usd"], "monthly_afe_usd")
        mtd_spend = self._non_negative(
            budget["mtd_actual_spend_usd"], "mtd_actual_spend_usd"
        )
        projected_spend = mtd_spend / elapsed_days * total_days
        prorated_target = monthly_revenue_target * elapsed_days / total_days
        gas_rate = self._non_negative(production["gas_rate_mmscfd"], "gas_rate_mmscfd")
        return self._success(
            "field_value_metrics",
            mtd_revenue_usd=round(daily_revenue * elapsed_days, 2),
            projected_month_revenue_usd=round(daily_revenue * total_days, 2),
            monthly_target_usd=round(monthly_revenue_target, 2),
            mtd_vs_plan_pct=round(
                (daily_revenue * elapsed_days - prorated_target)
                / prorated_target
                * 100.0,
                2,
            )
            if prorated_target
            else None,
            projected_month_production_mmscf=round(gas_rate * total_days, 3),
            monthly_production_target_mmscf=round(monthly_production_target, 3),
            budget_variance={
                "projected_spend_usd": round(projected_spend, 2),
                "variance_usd": round(projected_spend - monthly_afe, 2),
            },
        )

    def _remaining_reserves(self, arguments: dict[str, Any]) -> dict[str, Any]:
        eur = self._non_negative(arguments["eur"], "eur")
        cumulative = self._non_negative(
            arguments["cumulative_production"], "cumulative_production"
        )
        return self._success(
            "remaining_reserves",
            remaining_reserves=max(0.0, eur - cumulative),
            eur=eur,
            cumulative_production=cumulative,
        )

    def _rank_acreage(self, arguments: dict[str, Any]) -> dict[str, Any]:
        areas = arguments.get("areas")
        if not isinstance(areas, list) or not areas:
            raise ValueError("areas must be a non-empty array")
        ranked: list[dict[str, Any]] = []
        for index, item in enumerate(areas):
            if not isinstance(item, dict):
                raise ValueError(f"areas[{index}] must be an object")
            npv = self._finite_number(item["npv_usd"], f"areas[{index}].npv_usd")
            acres = self._non_negative(item["area_acres"], f"areas[{index}].area_acres")
            if acres == 0.0:
                raise ValueError(f"areas[{index}].area_acres must be greater than zero")
            ranked.append({**item, "npv_per_acre": round(npv / acres, 2)})
        ranked.sort(key=lambda item: float(item["npv_per_acre"]), reverse=True)
        for rank, item in enumerate(ranked, start=1):
            item["rank"] = rank
        return self._success("rank_acreage", count=len(ranked), ranked_areas=ranked)

    def _well_economics(self, arguments: dict[str, Any]) -> dict[str, Any]:
        eur_mboe = self._non_negative(arguments["eur_mboe"], "eur_mboe")
        ip_boe_d = self._non_negative(arguments["ip_boe_d"], "ip_boe_d")
        afe_cost = self._non_negative(arguments["afe_cost_usd"], "afe_cost_usd")
        lease = self._object(arguments, "lease_params")
        prices = self._object(arguments, "price_deck")
        discount_rate = self._finite_number(arguments["discount_rate"], "discount_rate")
        forecast_months = arguments.get("forecast_months")
        if eur_mboe <= 0.0 or ip_boe_d <= 0.0:
            raise ValueError("eur_mboe and ip_boe_d must be greater than zero")
        if not isinstance(forecast_months, int) or isinstance(forecast_months, bool):
            raise ValueError("forecast_months must be an integer")
        if not 1 <= forecast_months <= 1200:
            raise ValueError("forecast_months must be between 1 and 1200")
        if discount_rate <= -1.0:
            raise ValueError("discount_rate must be greater than -1")
        area_acres = self._non_negative(lease["area_acres"], "area_acres")
        if area_acres <= 0.0:
            raise ValueError("area_acres must be greater than zero")
        royalty = self._finite_number(lease["royalty_fraction"], "royalty_fraction")
        if not 0.0 <= royalty < 1.0:
            raise ValueError("royalty_fraction must be in [0, 1)")
        lease_cost = (
            self._non_negative(
                lease["mineral_acre_price_usd"], "mineral_acre_price_usd"
            )
            * area_acres
        )
        oil_price = self._non_negative(prices["oil_usd_bbl"], "oil_usd_bbl")
        gas_price = self._non_negative(prices["gas_usd_mcf"], "gas_usd_mcf")
        gor = self._non_negative(prices["gor_scf_per_bbl"], "gor_scf_per_bbl")
        qi = ip_boe_d * DAYS_PER_MONTH
        nominal_decline = 2.0 * qi / (eur_mboe * 1000.0)
        npv, cumulative_oil, cumulative_gas, cashflows = self._monthly_npv(
            qi,
            nominal_decline,
            DEFAULT_ARPS_B,
            oil_price,
            gas_price,
            gor,
            royalty,
            afe_cost,
            lease_cost,
            discount_rate,
            forecast_months,
        )
        ror = self._find_ror(
            qi,
            nominal_decline,
            DEFAULT_ARPS_B,
            oil_price,
            gas_price,
            gor,
            royalty,
            afe_cost,
            lease_cost,
            forecast_months,
        )
        return self._success(
            "well_economics",
            npv_usd=round(npv, 2),
            ror=None if ror is None else round(ror, 4),
            npv_per_acre=round(npv / area_acres, 2),
            cumulative_oil_bbl=round(cumulative_oil, 2),
            cumulative_gas_scf=round(cumulative_gas, 2),
            decline_params={
                "qi_boe_month": round(qi, 2),
                "di_per_month": round(nominal_decline, 6),
                "b": DEFAULT_ARPS_B,
            },
            monthly_cashflows_sample=cashflows[:12],
            assumptions={
                "oil_usd_bbl": oil_price,
                "gas_usd_mcf": gas_price,
                "gor_scf_per_bbl": gor,
                "royalty_fraction": royalty,
                "discount_rate": discount_rate,
                "forecast_months": forecast_months,
            },
        )

    def _monthly_npv(
        self,
        qi: float,
        decline: float,
        b_factor: float,
        oil_price: float,
        gas_price: float,
        gor: float,
        royalty: float,
        afe_cost: float,
        lease_cost: float,
        discount_rate: float,
        forecast_months: int,
    ) -> tuple[float, float, float, list[dict[str, Any]]]:
        monthly_discount = (1.0 + discount_rate) ** (1.0 / MONTHS_PER_YEAR) - 1.0
        cumulative_oil = 0.0
        cumulative_gas = 0.0
        npv = -afe_cost - lease_cost
        cashflows: list[dict[str, Any]] = []
        for month in range(1, forecast_months + 1):
            daily_rate = self._arps_rate(month - 0.5, qi, decline, b_factor)
            if daily_rate < MIN_ECONOMIC_RATE_BOEPD:
                break
            monthly_boe = daily_rate * DAYS_PER_MONTH
            oil_fraction = 1.0 / (1.0 + gor / SCF_PER_BOE) if gor > 0.0 else 1.0
            monthly_oil = monthly_boe * oil_fraction
            monthly_gas = monthly_oil * gor
            gross_revenue = monthly_oil * oil_price + monthly_gas / 1000.0 * gas_price
            net_revenue = gross_revenue * (1.0 - royalty)
            discounted_cashflow = net_revenue / (1.0 + monthly_discount) ** month
            npv += discounted_cashflow
            cumulative_oil += monthly_oil
            cumulative_gas += monthly_gas
            cashflows.append(
                {
                    "month": month,
                    "daily_rate_boe": round(daily_rate, 2),
                    "net_revenue_usd": round(net_revenue, 2),
                    "discounted_cashflow_usd": round(discounted_cashflow, 2),
                }
            )
        return npv, cumulative_oil, cumulative_gas, cashflows

    def _find_ror(
        self,
        qi: float,
        decline: float,
        b_factor: float,
        oil_price: float,
        gas_price: float,
        gor: float,
        royalty: float,
        afe_cost: float,
        lease_cost: float,
        forecast_months: int,
    ) -> float | None:
        low = -0.05
        high = 5.0
        low_npv = self._monthly_npv(
            qi,
            decline,
            b_factor,
            oil_price,
            gas_price,
            gor,
            royalty,
            afe_cost,
            lease_cost,
            low,
            forecast_months,
        )[0]
        high_npv = self._monthly_npv(
            qi,
            decline,
            b_factor,
            oil_price,
            gas_price,
            gor,
            royalty,
            afe_cost,
            lease_cost,
            high,
            forecast_months,
        )[0]
        if low_npv < 0.0 or high_npv > 0.0:
            return None
        for _ in range(MAX_ROR_ITERATIONS):
            midpoint = (low + high) / 2.0
            midpoint_npv = self._monthly_npv(
                qi,
                decline,
                b_factor,
                oil_price,
                gas_price,
                gor,
                royalty,
                afe_cost,
                lease_cost,
                midpoint,
                forecast_months,
            )[0]
            if abs(midpoint_npv) < ROR_TOLERANCE_USD:
                return midpoint
            if midpoint_npv > 0.0:
                low = midpoint
            else:
                high = midpoint
        return (low + high) / 2.0

    def _arps_rate(
        self, time_months: float, qi: float, decline: float, b_factor: float
    ) -> float:
        if b_factor <= 0.0:
            return qi * math.exp(-decline * time_months)
        return qi / (1.0 + b_factor * decline * time_months) ** (1.0 / b_factor)

    def _object(self, arguments: dict[str, Any], name: str) -> dict[str, Any]:
        value = arguments.get(name)
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a JSON object")
        return value

    def _well_object(self, value: Any, name: str) -> dict[str, Any]:
        if not isinstance(value, dict) or not value.get("well_id"):
            raise ValueError(f"each {name} entry must include well_id")
        return value

    def _non_negative(self, value: Any, name: str) -> float:
        parsed = self._finite_number(value, name)
        if parsed < 0.0:
            raise ValueError(f"{name} must be non-negative")
        return parsed

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

    def _success(self, operation: str, **values: Any) -> dict[str, Any]:
        return {"status": "success", "operation": operation, **values}

    def _error(self, code: str, message: str, **values: Any) -> dict[str, Any]:
        return {"status": "error", "code": code, "message": message, **values}


class JsonOutput:
    """Serialize one economics result as JSON on stdout."""

    def __init__(self, value: dict[str, Any]) -> None:
        self._value = value

    def write(self) -> None:
        print(json.dumps(self._value, indent=2, sort_keys=True))


class EconomicsCommand:
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
        return EconomicsCalculator(request).calculate()
    except (OSError, ValueError) as error:
        return {"status": "error", "code": "INPUT_ERROR", "message": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic production economics calculations from JSON."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--request-json", help="Inline JSON request object.")
    input_group.add_argument("--input", type=Path, help="Path to a JSON request file.")
    arguments = parser.parse_args()
    return EconomicsCommand(arguments.request_json, arguments.input).run()


if __name__ == "__main__":
    raise SystemExit(main())
