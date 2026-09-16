---
description: "Exact contract for the four bundled scripts: the run(request) sandbox entry point, the read-only environment rule, and for every operation the argument names and the response keys. Read before any run_python call so no name is guessed."
last_updated: 2026-09-16
origin: original
---

# Script interface

## Executing a script in Amazon Quick

The sandbox process environment is read-only: `os.environ` cannot be changed, so `WORKSPACE_DIR` cannot be set by the agent, and scripts are never run as a subprocess. Every script exposes `run(request: dict) -> dict`. Execute a script like this:

1. Read the complete script source with `file_read`.
2. In `run_python` (or `run_python_with_write` when a file is written), import the script by its file stem, which Amazon Quick places on the sandbox import path, and call its `run(request)`: `import run_las_reader as script; result = script.run(request)`. Do not read or assign `__file__`, `__dict__`, or any other dunder attribute; the sandbox attribute checker blocks those and the import already registers the module in `sys.modules`, which the dataclass postponed annotations need. Do not compile or `exec` the source yourself.
3. Never mutate `os.environ`, modify `sys.path`, import one bundled script from another, or spawn a subprocess.

The command-line form `python scripts/<name>.py --request-json '<json>'` (plus `--fixture` for the fixture script) remains available outside the sandbox and behaves identically.

## Request and response envelope

Request: `{"operation": "<name>", "arguments": {...}}` plus script-specific top-level keys noted below. Responses carry `"status": "success"` with the keys listed, or `"status": "error"` with `code` and `message`. Treat any error as `UNKNOWN` for the dependent conclusion; never recompute by hand. Exception: `field_summary` returns the raw fixture snapshot without a `status` key.

## run_tiger_fixture.py

Top-level request key: `fixture` (path to `references/tiger-data-sample-response.json`, required).

| Operation | Arguments | Response keys |
| --- | --- | --- |
| `field_summary` | none | `field{name, operator, location, total_wells, active_wells, shut_in_wells}`, `summary{total_gas_production_mmscfd, total_water_production_bwpd, average_wellhead_pressure_psi, field_water_cut_pct, wells_with_active_alarms}`, `manifolds[]`, `wells[]`, `timestamp` |
| `well_deviations` | `threshold_pct` (default 10) | `deviation_count`, `evaluated_wells`, `deviations[]{well_id, parameter, current_value, rolling_average_24hr, deviation_pct, trend}` |
| `manifold_pressures` | none | `pressure_basis`, `manifolds[]{manifold_id, pressure_psi, min_wellhead_pressure_psi, max_wellhead_pressure_psi, wells_connected, producing_wells, flow_rate_mmscfd, status}` |
| `well_readings` | `well_ids` (array), `minutes` (default 30) | `interval_minutes`, `window_minutes`, `wells[]{well_id, readings[]}` |
| `well_history` | `well_id`, `days` (default 7, max 3650) | `history[]{date, avg_pressure_psi, avg_rate_mmscfd, avg_temp_degc, cumulative_gas_mmscf, uptime_pct}` |
| `completion_data` | `well_id` | `manifold`, `water_depth_m`, `total_depth_m`, `completion{type, lateral_length_m, frac_stages, perforation_intervals, casing_sizes, tubing_size_in, packer_depth_m, reservoir}` |
| `alarms` | `severity` (`all`, `RED`, `AMBER`), optional `well_id` | `precedent_basis` (`active_alarm_set`), `total_alarms`, `alarms[]{alarm_id, severity, type, message, triggered_at, well_id, acknowledgement_available, execution_status}` |
| `reservoir_constraints` | `well_id`, optional `proposed_rate_mmscfd` | `verdict`, `binding_constraint`, `drawdown{reservoir_pressure_psi, fbhp_psi, fbhp_basis, current_drawdown_psi, evaluated_drawdown_psi, critical_drawdown_psi, utilisation_pct}`, `sand{rate_pptb, limit_pptb, utilisation_pct}`, `water{...}`, `decline_diagnosis{diagnosis, pressure_trend, rate_trend, reservoir_driven}` |
| `safety_compliance` | `well_id`, `proposed_action`, optional `action_class` (`chemical`, `choke`, `thermal`, `mechanical`, `other`) | `verdict`, `blocking`, `checks[]{check, value_psi, limit_psi, utilisation_pct, verdict}`, `precedent{precedent_basis, matched_alarms, historical_outcome_available}`, `permit_posture`, `threshold_basis`, `execution_status` |

Golden checks for SK-14: `reservoir_constraints` returns `decline_diagnosis.diagnosis: DOWNSTREAM_RESTRICTION`, `drawdown.fbhp_basis: estimated_static_column`, `verdict: CAUTION`, `binding_constraint: sand_rate`; `safety_compliance` for the MEG evaluation returns `verdict: PASS`, `blocking: false`, `execution_status: not_executed`; `alarms` returns one RED `HYDRATE_RISK` and two AMBER alarms, all on SK-14.

## run_petrophysics.py

| Operation | Arguments | Response keys |
| --- | --- | --- |
| `hydrate_equilibrium` | `pressure_psi`, `current_temp_degc`, `meg_weight_pct` | `uninhibited_equilibrium_degc`, `depression_degc`, `inhibited_equilibrium_degc`, `signed_scenario_margin_degc`, `risk_band`, `method`, `assumptions` |
| `density_porosity` | `bulk_density_gcc` (array), `matrix_density_gcc`, `fluid_density_gcc` | `total_porosity_fraction` (array) plus summary fields |
| `shale_volume` | `gamma_ray_gapi` (array), `clean_gr_gapi`, `shale_gr_gapi` | `shale_volume_fraction` (array) plus summary fields |
| `effective_porosity` | `total_porosity_fraction` (array), `shale_volume_fraction` (array) | `effective_porosity_fraction` (array) |
| `archie_water_saturation` | `true_resistivity_ohm_m` (array), `total_porosity_fraction` (array), `water_resistivity_ohm_m`, `a`, `m`, `n` | `water_saturation_fraction` (array) |
| `net_pay` | `depth_ft` (array), `effective_porosity_fraction`, `water_saturation_fraction`, `shale_volume_fraction` (arrays), `porosity_min`, `sw_max`, `vshale_max` | net pay thickness and interval summary |

Feed arrays from `read_curves` `canonical_curves`: `RHOB` to `bulk_density_gcc`, `GR` to `gamma_ray_gapi`, `RT` to `true_resistivity_ohm_m`, and `DEPTH` (converted from metres to feet when the unit is `M`) to `depth_ft`.

Golden check: `hydrate_equilibrium` with `pressure_psi: 4560`, `current_temp_degc: 15.7`, `meg_weight_pct: 21.5` returns `inhibited_equilibrium_degc: 14.22`, `signed_scenario_margin_degc: 1.48`, `risk_band: HIGH`; `pressure_psi: 0` returns `code: NON_POSITIVE_PRESSURE`.

## run_economics.py

| Operation | Arguments | Response keys |
| --- | --- | --- |
| `daily_revenue` | `gas_rate_mmscfd`, `gas_price_per_mmbtu`, `btu_per_scf`, optional `condensate_bpd`, `condensate_price_per_bbl`, `ngl_bpd`, `ngl_price_per_bbl` | `revenue_breakdown{gas_revenue_usd, condensate_revenue_usd, ngl_revenue_usd, total_daily_revenue_usd}`, `unit_economics{revenue_per_mcf, revenue_per_boe, total_production_boepd}`, `assumptions` |
| `deferred_production` | `gas_price_per_mmbtu`, `btu_per_scf`, `constrained_wells[]{well_id, current_rate_mmscfd, potential_rate_mmscfd, reason}`, `shut_in_wells[]{well_id, potential_rate_mmscfd, reason}` | `total_deferred_mmscfd`, `total_deferred_value_usd_per_day`, `total_deferred_value_usd_per_month`, `annualised_deferred_usd`, `by_well[]{well_id, category, deferred_mmscfd, deferred_usd_per_day, reason}`, `assumptions` |
| `opex_per_boe` | `total_opex_daily_usd`, `total_production_boepd`, optional `cost_categories`, `benchmark_usd_per_boe` | `opex_per_boe`, variance fields |
| `remaining_reserves` | `eur`, `cumulative_production` | remaining reserves fields |
| `rank_acreage` | `areas` | ranked areas |
| `well_economics` | `afe_cost_usd`, `discount_rate`, `eur_mboe`, `forecast_months`, `ip_boe_d` | NPV and payout fields |

Golden checks with `gas_price_per_mmbtu: 3.5`, `btu_per_scf: 1050`: `constrained_wells` SK-14 at 22 of 38 MMscf/d returns `total_deferred_value_usd_per_day: 58800.0` (current deferral); `shut_in_wells` SK-14 at 38 MMscf/d returns `139650.0` (full-well exposure). Report the two separately and never as avoided savings.

## run_las_reader.py

Top-level request key: `workspace_dir` (required in Amazon Quick; the skill directory or a confirmed local folder). Paths in `arguments.path` must stay inside it; absolute paths outside it and parent traversal return `PARENT_TRAVERSAL` or `PATH_OUTSIDE_WORKSPACE` errors.

| Operation | Arguments | Response keys |
| --- | --- | --- |
| `read_metadata` | `path` | `source_path`, `version`, `wrap`, `null_value`, `well{STRT, STOP, STEP, NULL, COMP, WELL, FLD, ...}` (each `{unit, value, description}`), `curve_count`, `curves[]{mnemonic, unit, description, null_value}` |
| `read_curves` | `path`, optional depth window | `sample_count`, `depth_mnemonic`, `depth_window{minimum, maximum, unit}`, `null_value`, `curves{<mnemonic>: array}`, `units{<mnemonic>: unit}`, `canonical_curves{DEPTH, GR, NPHI, RHOB, DT, CALI, RT}`, `canonical_units`, `canonical_sources` |
| `resolve_aliases` | `mnemonics` (array of strings) | `aliases[]{mnemonic, normalized_mnemonic, canonical_name, recognized}`, `mapping{<mnemonic>: canonical_name}` |

Error codes: `WRAPPED_LAS_UNSUPPORTED`, `MISSING_ASCII_SECTION`, `UNSUPPORTED_VERSION`, `PARENT_TRAVERSAL`, `WORKSPACE_DIR_MISSING`, `UNKNOWN_OPERATION`, `INVALID_INPUT`.

Golden check on `evals/files/SK-14.las`: LAS 2.0, `wrap: NO`, `null_value: -999.25`, 200 samples, 7 curves `DEPT, GR, NPHI, RHOB, DT, CALI, ILD`; aliases resolve `DEPT` to `DEPTH`, `ILD` to `RT`, and `CALI` to `CALI` (caliper is never resistivity).
