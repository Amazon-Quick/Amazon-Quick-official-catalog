---
description: "How to present findings as a Markdown report, scorecard, alert-only summary, JSON, or XLSX or DOCX file."
last_updated: 2026-11-22
---
# Output formats

## Markdown report

State scan time and coverage first. For each finding include severity, datasource, rule, concise evidence, why it matters, and a concrete fix. Distinguish observations from scored findings. Cap quick wins at five and avoid unsupported effort estimates.

End with:

> Metadata-only scan. Null rates, duplicate counts, distributions, row counts, referential integrity, PII presence, and underlying-data freshness were not assessed unless a separately authorized data-query workflow supplied that evidence.

## Scorecard

Use one row per datasource with overall grade, six domain grades, finding count, and status. Use `N/A` for an unassessed domain and `Failed` for inaccessible sources. Do not turn missing fields into passing grades.

## Alert-only

Show HIGH and CRITICAL findings, or changes requested by the user. If none qualify, say none were observed within completed metadata coverage—not that the data is clean.

## JSON

Return helper output plus `scan_timestamp`, `scope`, `unassessed_checks`, and sanitized `failures`. Do not include credentials, connection strings, or raw tool errors.

## XLSX/DOCX

Create only when requested. Include findings, scorecard, coverage, and methodology note. Validate with the appropriate artifact workflow before delivery.

