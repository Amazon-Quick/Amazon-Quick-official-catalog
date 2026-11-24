#!/usr/bin/env python3
"""
description: Validate and score normalized Tableau metadata-quality findings.
last_updated: 2026-11-22

Validate and score normalized Tableau metadata-quality findings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VERSION = "1.0"
DOMAINS = ("schema", "naming", "types", "calcs", "metadata", "freshness")
SEVERITIES = ("low", "medium", "high", "critical")
PENALTIES = {"critical": 10, "high": 5, "medium": 2, "low": 0.5}
STATUSES = {"profiled", "reused", "failed"}
TOP_KEYS = {"scan_id", "methodology_version", "sources", "findings"}
REQUIRED = {"source_id", "domain", "rule_id", "severity", "evidence_key", "summary"}
OPTIONAL = {"additional_domains", "systemic", "combined_critical", "observation"}


class InputError(ValueError):
    """Raised for invalid input documents."""


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{label} must be a non-empty string")
    return value.strip()


def grade(score: float) -> str:
    bands = (
        (97, "A+"),
        (93, "A"),
        (90, "A-"),
        (87, "B+"),
        (83, "B"),
        (80, "B-"),
        (77, "C+"),
        (73, "C"),
        (70, "C-"),
        (67, "D+"),
        (63, "D"),
        (60, "D-"),
    )
    return next((label for minimum, label in bands if score >= minimum), "F")


def escalate(severity: str, finding: dict[str, Any]) -> str:
    if finding.get("combined_critical"):
        return "critical"
    if finding.get("systemic") or finding.get("additional_domains"):
        return SEVERITIES[min(SEVERITIES.index(severity) + 1, 3)]
    return severity


def parse(payload: Any) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise InputError("input must be a JSON object")
    unknown = set(payload) - TOP_KEYS
    if unknown:
        raise InputError(f"unknown top-level keys: {sorted(unknown)}")
    sources_raw, findings_raw = payload.get("sources"), payload.get("findings")
    if not isinstance(sources_raw, list) or not isinstance(findings_raw, list):
        raise InputError("sources and findings must be arrays")

    sources: list[dict[str, str]] = []
    ids: set[str] = set()
    for index, source in enumerate(sources_raw):
        if not isinstance(source, dict):
            raise InputError(f"sources[{index}] must be an object")
        extra = set(source) - {"id", "name", "status", "assessed_domains"}
        if extra:
            raise InputError(f"sources[{index}] has unknown keys: {sorted(extra)}")
        source_id = require_text(source.get("id"), f"sources[{index}].id")
        if source_id in ids:
            raise InputError(f"duplicate source id: {source_id}")
        status = source.get("status", "profiled")
        if status not in STATUSES:
            raise InputError(
                f"sources[{index}].status must be one of {sorted(STATUSES)}"
            )
        assessed = source.get(
            "assessed_domains", [] if status == "failed" else list(DOMAINS)
        )
        if not isinstance(assessed, list) or any(
            value not in DOMAINS for value in assessed
        ):
            raise InputError(
                f"sources[{index}].assessed_domains contains an invalid domain"
            )
        if len(set(assessed)) != len(assessed):
            raise InputError(
                f"sources[{index}].assessed_domains must not contain duplicates"
            )
        if status == "failed" and assessed:
            raise InputError(
                f"sources[{index}] cannot assess domains when status is failed"
            )
        ids.add(source_id)
        sources.append(
            {
                "id": source_id,
                "name": require_text(source.get("name"), f"sources[{index}].name"),
                "status": status,
                "assessed_domains": assessed,
            }
        )

    if (
        any(source["status"] == "reused" for source in sources)
        and payload.get("methodology_version") != VERSION
    ):
        raise InputError(f"reused sources require methodology_version {VERSION}")

    findings: list[dict[str, Any]] = []
    for index, item in enumerate(findings_raw):
        if not isinstance(item, dict):
            raise InputError(f"findings[{index}] must be an object")
        missing, extra = REQUIRED - set(item), set(item) - REQUIRED - OPTIONAL
        if missing:
            raise InputError(f"findings[{index}] missing keys: {sorted(missing)}")
        if extra:
            raise InputError(f"findings[{index}] has unknown keys: {sorted(extra)}")
        source_id = require_text(item["source_id"], f"findings[{index}].source_id")
        if source_id not in ids:
            raise InputError(
                f"findings[{index}] references unknown source: {source_id}"
            )
        source = next(value for value in sources if value["id"] == source_id)
        if source["status"] == "failed":
            raise InputError(f"findings[{index}] cannot reference a failed source")
        domain = require_text(item["domain"], f"findings[{index}].domain").lower()
        severity = require_text(item["severity"], f"findings[{index}].severity").lower()
        if domain not in DOMAINS:
            raise InputError(f"findings[{index}].domain must be one of {list(DOMAINS)}")
        if domain not in source["assessed_domains"]:
            raise InputError(
                f"findings[{index}].domain was not assessed for source {source_id}"
            )
        if severity not in SEVERITIES:
            raise InputError(
                f"findings[{index}].severity must be one of {list(SEVERITIES)}"
            )
        additional = item.get("additional_domains", [])
        if not isinstance(additional, list) or any(
            value not in DOMAINS for value in additional
        ):
            raise InputError(
                f"findings[{index}].additional_domains contains an invalid domain"
            )
        if domain in additional or len(set(additional)) != len(additional):
            raise InputError(
                f"findings[{index}].additional_domains must be distinct from primary domain"
            )
        for key in ("systemic", "combined_critical", "observation"):
            if key in item and not isinstance(item[key], bool):
                raise InputError(f"findings[{index}].{key} must be boolean")
        normalized = {
            "source_id": source_id,
            "domain": domain,
            "rule_id": require_text(item["rule_id"], f"findings[{index}].rule_id"),
            "severity": severity,
            "evidence_key": require_text(
                item["evidence_key"], f"findings[{index}].evidence_key"
            ),
            "summary": require_text(item["summary"], f"findings[{index}].summary"),
            "additional_domains": sorted(set(additional)),
            "systemic": item.get("systemic", False),
            "combined_critical": item.get("combined_critical", False),
            "observation": item.get("observation", False),
        }
        normalized["effective_severity"] = escalate(severity, normalized)
        findings.append(normalized)
    return sources, findings


def score(payload: Any) -> dict[str, Any]:
    sources, findings = parse(payload)
    observations = [item for item in findings if item["observation"]]
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in (item for item in findings if not item["observation"]):
        key = (item["source_id"], item["rule_id"], item["evidence_key"])
        current = deduped.get(key)
        if current is None or SEVERITIES.index(
            item["effective_severity"]
        ) > SEVERITIES.index(current["effective_severity"]):
            deduped[key] = item
    scored = list(deduped.values())

    source_results, included_scores = [], []
    domain_scores: dict[str, list[float]] = {domain: [] for domain in DOMAINS}
    for source in sources:
        if source["status"] == "failed":
            source_results.append(
                {**source, "score": None, "grade": None, "finding_count": 0}
            )
            continue
        own = [item for item in scored if item["source_id"] == source["id"]]
        value = max(
            0.0, 100.0 - sum(PENALTIES[item["effective_severity"]] for item in own)
        )
        included_scores.append(value)
        domains = {}
        for domain in DOMAINS:
            if domain not in source["assessed_domains"]:
                domains[domain] = {
                    "score": None,
                    "grade": None,
                    "finding_count": None,
                    "status": "not_assessed",
                }
                continue
            matches = [item for item in own if item["domain"] == domain]
            domain_value = max(
                0.0,
                100.0 - sum(PENALTIES[item["effective_severity"]] for item in matches),
            )
            domains[domain] = {
                "score": domain_value,
                "grade": grade(domain_value),
                "finding_count": len(matches),
                "status": "assessed",
            }
            domain_scores[domain].append(domain_value)
        source_results.append(
            {
                **source,
                "score": value,
                "grade": grade(value),
                "finding_count": len(own),
                "domains": domains,
            }
        )

    overall = (
        round(sum(included_scores) / len(included_scores), 2)
        if included_scores
        else None
    )
    domain_results = {}
    for domain, values in domain_scores.items():
        value = round(sum(values) / len(values), 2) if values else None
        domain_results[domain] = {
            "score": value,
            "grade": grade(value) if value is not None else None,
            "assessed_source_count": len(values),
        }
    return {
        "methodology_version": VERSION,
        "coverage": {
            status: sum(source["status"] == status for source in sources)
            for status in sorted(STATUSES)
        },
        "overall_score": overall,
        "overall_grade": grade(overall) if overall is not None else None,
        "sources": source_results,
        "domains": domain_results,
        "findings": scored,
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON findings file")
    parser.add_argument("--pretty", action="store_true", help="indent JSON output")
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as handle:
            result = score(json.load(handle))
    except (OSError, json.JSONDecodeError, InputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
