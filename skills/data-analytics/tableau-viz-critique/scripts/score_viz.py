#!/usr/bin/env python3
"""
description: Validate an assessment JSON and calculate its Viz Critique Pro score.
last_updated: 2026-11-22

Validate and calculate a Viz Critique Pro score from JSON."""

from __future__ import annotations

import argparse
import json
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

WEIGHTS = {
    "D1": Decimal("0.15"),
    "D2": Decimal("0.10"),
    "D3": Decimal("0.20"),
    "D4": Decimal("0.25"),
    "D5": Decimal("0.15"),
    "D6": Decimal("0.10"),
    "D7": Decimal("0.05"),
}

TIERS = [
    (Decimal("8.6"), "Iron Viz Ready"),
    (Decimal("7.5"), "Would Publish to Public"),
    (Decimal("6.5"), "Data With Its Shirt Tucked In"),
    (Decimal("5.0"), "Can You See It on Your End?"),
    (Decimal("3.0"), "Drag It Back to the Shelf"),
    (Decimal("0.0"), "Tableau Public…ly Concerning"),
]

BONUS_RULES = {
    "aesthetic-excellence": ({"D4"}, Decimal("0.5")),
    "accessible-redundancy": ({"D5", "D6"}, Decimal("0.3")),
    "innovative-clarity": ({"D3"}, Decimal("0.3")),
    "exceptional-annotations": ({"D6"}, Decimal("0.2")),
}


def decimal_value(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{label} must be numeric")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{label} must be finite")
    return result


def tier_for(score: Decimal) -> str:
    for minimum, label in TIERS:
        if score >= minimum:
            return label
    raise AssertionError("tier table must include zero")


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    domains = payload.get("domains")
    if not isinstance(domains, dict) or set(domains) != set(WEIGHTS):
        raise ValueError("domains must contain exactly D1 through D7")

    caps = payload.get("caps", {})
    if not isinstance(caps, dict):
        raise ValueError("caps must be an object")
    domain_caps = caps.get("domains", {})
    overall_caps = caps.get("overall", [])
    if not isinstance(domain_caps, dict) or not isinstance(overall_caps, list):
        raise ValueError(
            "caps.domains must be an object and caps.overall must be a list"
        )
    if not set(domain_caps).issubset(WEIGHTS):
        raise ValueError("domain caps may contain only D1 through D7")

    positive_bonus = Decimal("0")
    used_bonus_ids: set[str] = set()
    output_domains: dict[str, Any] = {}
    weighted_total = Decimal("0")

    for domain_id, weight in WEIGHTS.items():
        entry = domains[domain_id]
        if not isinstance(entry, dict):
            raise ValueError(f"{domain_id} must be an object")
        base = decimal_value(entry.get("base"), f"{domain_id}.base")
        if not Decimal("0") <= base <= Decimal("10"):
            raise ValueError(f"{domain_id}.base must be between 0 and 10")
        adjustments = entry.get("adjustments", [])
        if not isinstance(adjustments, list):
            raise ValueError(f"{domain_id}.adjustments must be a list")

        adjustment_total = Decimal("0")
        normalized_adjustments = []
        interactivity_total = Decimal("0")
        anti_pattern_total = Decimal("0")
        for index, adjustment in enumerate(adjustments):
            if not isinstance(adjustment, dict) or not isinstance(
                adjustment.get("label"), str
            ):
                raise ValueError(
                    f"{domain_id}.adjustments[{index}] needs a string label"
                )
            value = decimal_value(
                adjustment.get("value"), f"{domain_id}.adjustments[{index}].value"
            )
            kind = adjustment.get("kind", "other")
            if kind not in {"bonus", "interactivity", "anti-pattern", "other"}:
                raise ValueError(f"unsupported adjustment kind: {kind}")
            if value > 0 and kind not in {"bonus", "interactivity"}:
                raise ValueError("positive adjustments must be bonus or interactivity")
            if kind == "bonus":
                bonus_id = adjustment.get("id")
                if not isinstance(bonus_id, str) or bonus_id not in BONUS_RULES:
                    raise ValueError("bonus adjustments require a supported id")
                if bonus_id in used_bonus_ids:
                    raise ValueError(f"bonus may appear only once: {bonus_id}")
                allowed_domains, maximum = BONUS_RULES[bonus_id]
                if domain_id not in allowed_domains:
                    raise ValueError(f"bonus {bonus_id} is not allowed in {domain_id}")
                if value <= 0 or value > maximum:
                    raise ValueError(
                        f"bonus {bonus_id} must be greater than 0 and no more than {maximum}"
                    )
                used_bonus_ids.add(bonus_id)
            adjustment_total += value
            if kind == "bonus" and value > 0:
                positive_bonus += value
            if kind == "interactivity":
                if domain_id not in {"D1", "D4"}:
                    raise ValueError(
                        "interactivity adjustments are allowed only in D1 and D4"
                    )
                interactivity_total += value
            if kind == "anti-pattern":
                if domain_id != "D3" or value > 0:
                    raise ValueError(
                        "anti-pattern adjustments must be non-positive and applied to D3"
                    )
                anti_pattern_total += value
            normalized = {
                "label": adjustment["label"],
                "value": float(value),
                "kind": kind,
            }
            if kind == "bonus":
                normalized["id"] = adjustment["id"]
            normalized_adjustments.append(normalized)

        if abs(interactivity_total) > Decimal("0.5"):
            raise ValueError(f"{domain_id} interactivity adjustment exceeds ±0.5")
        if anti_pattern_total < Decimal("-2.0"):
            raise ValueError("D3 anti-pattern adjustment exceeds -2.0")

        score = min(Decimal("10"), max(Decimal("0"), base + adjustment_total))
        if domain_id in domain_caps:
            cap = decimal_value(domain_caps[domain_id], f"caps.domains.{domain_id}")
            if not Decimal("0") <= cap <= Decimal("10"):
                raise ValueError(f"caps.domains.{domain_id} must be between 0 and 10")
            score = min(score, cap)
        contribution = score * weight
        weighted_total += contribution
        output_domains[domain_id] = {
            "base": float(base),
            "adjustments": normalized_adjustments,
            "score": float(score),
            "weight": float(weight),
            "contribution": float(contribution),
        }

    if positive_bonus > Decimal("0.8"):
        raise ValueError("cumulative positive bonuses exceed +0.8")

    applied_cap: dict[str, Any] | None = None
    safety_blockers: list[dict[str, Any]] = []
    for index, cap_entry in enumerate(overall_caps):
        if not isinstance(cap_entry, dict) or not isinstance(
            cap_entry.get("label"), str
        ):
            raise ValueError(f"caps.overall[{index}] needs a string label")
        value = decimal_value(cap_entry.get("value"), f"caps.overall[{index}].value")
        if not Decimal("0") <= value <= Decimal("10"):
            raise ValueError(f"caps.overall[{index}].value must be between 0 and 10")
        kind = cap_entry.get("kind")
        if kind not in {"quality", "safety"}:
            raise ValueError(f"caps.overall[{index}].kind must be quality or safety")
        normalized_cap = {
            "label": cap_entry["label"],
            "value": float(value),
            "kind": kind,
        }
        if kind == "safety":
            safety_blockers.append(normalized_cap)
        if applied_cap is None or value < Decimal(str(applied_cap["value"])):
            applied_cap = normalized_cap

    if applied_cap is not None:
        weighted_total = min(weighted_total, Decimal(str(applied_cap["value"])))

    rounded = weighted_total.quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)
    safety_blocked = bool(safety_blockers)
    return {
        "domains": output_domains,
        "unrounded_score": float(weighted_total),
        "score": float(rounded),
        "tier": "Safety remediation required" if safety_blocked else tier_for(rounded),
        "safety_status": "blocked" if safety_blocked else "no declared safety cap",
        "safety_blockers": safety_blockers,
        "applied_overall_cap": applied_cap,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessment", help="path to assessment JSON")
    parser.add_argument("--output", help="optional output JSON path")
    args = parser.parse_args()

    try:
        payload = json.loads(Path(args.assessment).read_text(encoding="utf-8"))
        result = calculate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
