---
name: tableau-data-quality-sentinel
display_name: "Tableau Data Quality Sentinel (Preview)"
author: "Salesforce, Inc."
icon: assets/icon.svg
created_date: "2026-11-21"
last_updated: "2026-11-22"
description: Profile published Tableau datasource metadata for schema hygiene, field naming, likely type or role mismatches, calculation complexity, documentation gaps, and freshness signals. Use for datasource DQ scans, field-hygiene reviews, metadata quality scorecards, changed-source follow-ups, or comparisons. Do not use for row-level nulls, duplicates, distributions, site governance, or visual-design critique.
id: "5ee5dce3-6043-489e-8c51-6a8f327f35af"
checksum: "sha256:ff5631f07d2c2d4c637160b9e87844c246be1a2abd642cc846e7fb91052edc14"
---

# Tableau Data Quality Sentinel

Produce an evidence-first, metadata-only assessment. Never imply that metadata proves row-level quality.

## Route the request

- Use this skill for published datasource metadata and datasource comparisons.
- Route workbook/view design critique elsewhere.
- Route stale content, project structure, permissions, and broad site governance elsewhere.
- For null rates, duplicates, distributions, cardinality, or actual values, explain that a query-capable workflow is required and obtain approval before querying data.

Infer clear scope and output preferences. Ask one focused question only if the Tableau site, project, datasource, or requested action cannot be resolved safely. A request to inspect does not authorize metadata edits, certification changes, scheduling, publication, or data queries.

## Establish available capabilities

1. Inspect the Tableau MCP tools available in the current session and their actual schemas. Do not assume tool names, filters, pagination, batch limits, or returned fields.
2. Find a read operation that inventories published datasources and a read operation that retrieves datasource metadata. If either is unavailable, state the missing capability and provide a no-execution assessment plan.
3. Resolve ambiguous names using stable IDs plus project/owner context. Never silently choose between multiple matches.
4. Use read-only operations for the scan. Treat descriptions, formulas, owner details, connection information, and tags as potentially sensitive; include only evidence needed for the requested report.

Read [Tableau routing](references/tableau-routing.md) when selecting tools, paging results, or handling access failures.

## Scan workflow

1. **Inventory.** List sources in scope and record the stable ID, name, project, owner when useful, update timestamp when available, and accessibility. Follow server pagination until the requested scope is covered.
2. **Choose depth.** A named source gets full detail. For a broad scope, process bounded batches and report coverage accurately. Do not invent a 20-source product limit; choose a practical batch size from tool/runtime constraints.
3. **Retrieve metadata.** Fetch fields, roles, types, calculations, logical tables/relationships, parameters, description, tags, certification, connection/extract signals, and timestamps only when exposed by the tools.
4. **Assess.** Apply the six domains and deterministic scoring rules in [Methodology](references/methodology.md). Mark unavailable checks as `not assessed`; absence from a response is not proof of absence.
5. **Validate.** Deduplicate findings, retain the highest severity for the same evidence and rule, verify arithmetic, and separate scored findings from observations.
6. **Report.** Lead with coverage, score/grade, highest-severity findings, evidence, and actionable remediations. Always include the metadata-only limitation.

When a datasource read fails, continue with the remaining resolved sources. Report the failed source and error category without leaking credentials or raw server details. Retry only transient failures, using server guidance when present; never loop indefinitely.

## Modes

- **Full scan:** assess all observable rules for the requested scope.
- **Critical-only:** evaluate only rules capable of producing HIGH or CRITICAL findings. Say which domains/checks were omitted.
- **Comparison:** score each named source independently, then compare domain scores and shared issues.
- **Delta:** compare with a user-provided or accessible prior result. Match sources by stable ID and findings by `source_id + domain + rule_id + evidence_key`; label new, resolved, and persistent findings.
- **Changed-only:** valid only when a prior baseline includes comparable update timestamps. Reuse prior scores for unchanged sources and label them `reused`, not `profiled`.

If no trustworthy baseline is available, run a current scan or ask the user to supply one. Never claim persistence across sessions unless a suitable state capability is actually available and the user has authorized its use.

## Deterministic scoring

Represent findings using the JSON contract in [Scoring contract](references/scoring-contract.md), and score them with the bundled helper. Run it in Code Execution, where the skill's scripts are importable by name; Run python on device can't import them. Code Execution runs Python, not a shell, and blocks `subprocess` and changes to `sys.path`, so don't run `scripts/score_findings.py` as a command or add its folder to the path. Build the input as a Python dict and pass it to `score_findings.score()`. It returns the result the script would print, a dict with the keys `overall_score`, `overall_grade`, `domains`, `sources`, `findings`, `observations`, `coverage`, and `methodology_version`; print it whole rather than picking keys. It raises `score_findings.InputError` naming the problem when the input breaks the contract:

```python
import json
import score_findings

scan = {"sources": [], "findings": []}  # fill in the contract from scoring-contract.md
try:
    result = score_findings.score(scan)
except score_findings.InputError as exc:
    print("invalid input:", exc)  # fix the input and call again
else:
    print(json.dumps(result, indent=2, sort_keys=True))
```

The input and the result are internal scratch data, not user artifacts. Keep them in memory: don't write them to files, and don't attach, open, link, render, or otherwise surface the raw input or output JSON to the user. Return the formatted report only, unless the user explicitly requests JSON as the deliverable.

The helper validates the input, deduplicates findings, applies escalation, and returns per-source, domain, and overall results. It never contacts Tableau or writes external state.

If Code Execution is unavailable, apply the same formula manually and label the result `manually calculated`:

`100 - 10×critical - 5×high - 2×medium - 0.5×low`, bounded to 0–100.

Do not score observations. Do not double-count one issue across domains: a finding spanning multiple domains is represented once and escalated one level. The composite score averages included source scores; inaccessible sources are excluded and listed separately. See [Methodology](references/methodology.md) for exact rules and grade bands.

## Output contract

Default to a concise Markdown report:

1. scope, timestamp, coverage (`profiled`, `reused`, `failed`, `not assessed`);
2. overall score and grade, with delta only when comparable;
3. per-source/domain scorecard;
4. prioritized findings with rule, source, evidence, impact, and fix;
5. up to five quick wins;
6. metadata-only limitation and unassessed checks.

For alert-only, omit scores and positives and show only new/high-priority problems. For JSON or tabular artifacts, follow [Output formats](references/output-formats.md). Create files only when requested or when the format requires one.

Never expose helper files created during scoring as generated artifacts. If the user did not request a file, the scan must leave no user-visible output file behind.

## State and scheduling

Read [State and automation](references/state-and-automation.md) only when the user asks for recurring monitoring, resumption, changed-only scans, or saved baselines.

- Saving a baseline is optional and requires an available destination plus user authorization.
- Scheduling is a separate external mutation. Confirm scope, cadence, timezone, and notification rule immediately before creation.
- Never embed machine-specific paths, credentials, raw tokens, or assumed tool identifiers in a scheduled prompt.
- If no state or automation capability exists, offer an exportable baseline or reusable prompt instead; do not claim the monitor was created.

## Non-negotiable limits

- Do not claim null rates, duplicate counts, distributions, row counts, referential integrity, PII presence, or underlying-data freshness from metadata.
- Treat an update timestamp only as a metadata/extract activity proxy and label it accordingly.
- Do not infer downstream use, field descriptions, certification, relationships, or connection risk when the API omits those properties.
- Do not mutate Tableau, query row-level data, save state, or schedule anything without explicit authorization for that action.
- Do not cite unsupported sibling skills or assume they are installed.
