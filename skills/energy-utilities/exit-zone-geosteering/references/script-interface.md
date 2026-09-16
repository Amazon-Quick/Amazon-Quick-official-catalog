---
description: "Exact invocation contract for the six bundled scripts, including isolated decision-review task shapes, replay append mode, and dashboard projection outputs."
last_updated: 2026-09-16
origin: original
---

# Script interface

Every script exposes `run(request: dict) -> dict`. The Amazon Quick sandbox environment is read-only, so agents MUST pass `workspace_dir` explicitly in the request and MUST NOT assign `WORKSPACE_DIR`. The environment variable is a compatibility fallback only when `workspace_dir` is absent.

Amazon Quick Desktop MUST execute a bundled script inside `run_python_with_write`, not as a subprocess:

1. Read the complete script source with `file_read`.
2. In `run_python_with_write`, import the script by its file stem, which Amazon Quick places on the sandbox import path, and call its `run(request)`: `import run_verification as script; result = script.run(request)`. Do not read or assign `__file__`, `__dict__`, or any other dunder attribute; the sandbox attribute checker blocks those and the import already registers the module in `sys.modules`, which the dataclass postponed annotations need. Do not compile or `exec` the source yourself.

Use a unique `script_name` for each execution. Do not invoke a subprocess, modify `os.environ`, import another bundled script, or modify `sys.path`. The callable entry is `run` in each of `create_synthetic_well.py`, `run_verification.py`, `run_price_impact.py`, `run_zone_exit.py`, `create_handover.py`, and `create_dashboard.py`. The CLI form `python scripts/<name>.py --input '<json object>'` remains available outside the read-only sandbox.

## Common input

- `workspace_dir` (string, required in Amazon Quick Desktop; absolute path supplied by the sandbox workspace context)
- `wellbore_id` (string, must match `^[A-Za-z0-9._-]+$`; default `SYN1`)
- `data_root` (string, relative below `workspace_dir`; default `exit-zone-geosteering-data`). Absolute paths and paths escaping the resolved workspace directory are rejected.

The common request shape for `SYN1` is:

```json
{"workspace_dir":"<Quick workspace directory>","wellbore_id":"SYN1","data_root":"exit-zone-geosteering-data"}
```

Replace `<Quick workspace directory>` with the workspace directory supplied by Amazon Quick and replace only the validated `wellbore_id` when another well is requested. Isolated Decision Review tasks receive this exact request object in their prompt because they cannot see conversation history.

Responses are JSON objects with a `status` field when the operation is not an observation. `created`, `appended`, `projected`, and `no_alert` are documented results; `error` carries an `error` message. A persisted observation is returned as the complete observation object. Treat an error as the documented failure path and never recompute a value by hand.

| Script | Extra input keys | Success result | Writes |
| --- | --- | --- | --- |
| `create_synthetic_well.py` | create mode: `references` with parsed `offsets`, `price_deck`, `zone_tops`; optional `ticks`; replay mode: `mode: "append_tick"` | create: `status: "created"`; replay: `status: "appended"` with one new `record` | create rewrites stream, state, observation sink, and references; append mode adds one stream line only |
| `run_verification.py` | none | complete `payzone_delta` observation | appends `payzone_delta` |
| `run_price_impact.py` | none | complete `impact_estimate` observation | appends `impact_estimate` |
| `run_zone_exit.py` | none | complete `exit_alert` observation, or `status: "no_alert"` with `projection` | appends `exit_alert` only when tiered |
| `create_handover.py` | none | complete `handover_note`, or `status: "provenance_failure"` with exact orphans | appends `handover_note` only after integrity passes |
| `create_dashboard.py` | `template`, the full text of `assets/dashboard.html` | `status: "projected"`, `data_output`, `fallback_output`, counts, and `chart_series` | chart-ready JSON and plain-HTML fallback under `outputs/` |

## Decision Review isolated-task outputs

The Price Impact task must return exactly one of these envelopes:

```json
{"feature":"price_impact","status":"ok","observation":{"id":"...","type":"impact_estimate","value":{"scenarios":[{"scenario":"correct_now","usd":0,"unit":"USD"},{"scenario":"hold_3_stands","usd":0,"unit":"USD"}],"basis":{}},"confidence":0,"reasoning":"...","source":[]}}
```

```json
{"feature":"price_impact","status":"unknown","error":"exact failure or timeout"}
```

The Zone-Exit Warning task must return exactly one of these envelopes:

```json
{"feature":"zone_exit_warning","status":"ok","observation":{"id":"...","type":"exit_alert","value":{"severity":"Watch|Warn|Escalate","eta_minutes":0,"margin_ft":0,"boundary_zone":"...","boundary_md":0,"rate_ft_per_hr":0,"steer":null,"steer_status":"..."},"confidence":0,"reasoning":"...","source":[]}}
```

```json
{"feature":"zone_exit_warning","status":"no_alert","projection":{"severity":null,"eta_minutes":0,"margin_ft":0,"boundary_zone":"...","boundary_md":0,"rate_ft_per_hr":0}}
```

```json
{"feature":"zone_exit_warning","status":"unknown","error":"exact failure or timeout"}
```

The task wrapper may add only `feature` and normalized `status`; it must not alter script-owned numbers, reasoning, confidence, or sources.

## Dashboard chart-ready data

`data_output` contains:

- `lwd_curves`: every numeric stream channel as `[measured_depth, value]` points.
- `trajectory`: deterministic section footage and measured depth from `stream.jsonl`.
- `zone_bands`: top and base measured depths from `references/zone_tops.json`.
- `confidence_trend`: every `payzone_delta` confidence with depth, timestamp, and observation id.
- `alert_feed`: every persisted `exit_alert` with tier, ETA, margin, boundary, reasoning, and source.

The Highcharts artifact is generated by the built-in `highcharts` and `html_design` skills from this JSON. The bundled `assets/dashboard.html` is the no-chart fallback.

## Golden values

For the bundled 19-record `SYN1` seed, reproduced by scripts on 2026-09-14:

- Verify: `p50_delta_ft: 14.5`, `confidence: 0.917`, `threshold: 0.65`, `accepted: true`
- Price Impact: `correct_now` `363825.0` USD; `hold_3_stands` `320650.0` USD
- Zone-Exit Warning: `eta_minutes: 9.5`, `margin_ft: 9.5`, tier `Escalate`; no steer is generated
- Shift Handover: `integrity.status: pass`, `orphan_count: 0`

For a 12-record replay-from-start stream, the seed ends at `10055.5` ft, `44.5` ft below the `10100.0` ft TargetZone base, and is already `Watch`. Appended replay tick 1 remains `Watch` at `39.5` minutes, the first `Warn` is appended tick 3 at `29.5` minutes, and the first `Escalate` is appended tick 7 at `9.5` minutes. This is the required Watch -> Warn -> Escalate progression.

For a 14-record replay stream, one `append_tick` adds `stream:SYN1:14` at `10070.5` ft and `2026-09-01T15:14:00.000Z`; the resulting zone-exit projection first enters `Warn` at `29.5` minutes.

A `wellbore_id` such as `../x` returns `error: wellbore_id must match ^[A-Za-z0-9._-]+$`.
