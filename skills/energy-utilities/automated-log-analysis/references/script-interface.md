---
description: "Exact Amazon Quick sandbox invocation contract for automated LAS generation, parsing, petrophysics, plotting, and reporting."
last_updated: 2026-09-16
origin: original
---

# Script interface

Every bundled script exposes `run(request: dict) -> dict`. Amazon Quick Desktop executes the scripts inside `run_python_with_write`:

1. Read the complete script source with `file_read`.
2. Import the script by its file stem and call `run(request)`. Example: `import run_evaluation as script; result = script.run(request)`.
3. Use a unique `script_name` for each execution and treat script-returned numbers as authoritative.

Each script is self-contained. The scripts do not call each other. Use the output path returned by one step as the relative input path for the next step.

## Common input

- `workspace_dir` (string, required): absolute sandbox workspace directory supplied by Amazon Quick.
- `well_id` (string, optional): must match `^[A-Za-z0-9._-]+$`; default `SYN-LAS-1`.
- `data_root` (string, optional): relative directory beneath `workspace_dir`; default `automated-log-analysis-data`.

Absolute input paths and paths containing parent traversal return `status: "error"`. Successful mutations return `status: "created"`; parsing and evaluation return `status: "success"`. Failures return `status: "error"` and an `error` string.

## Script contracts

| Script | Operation and extra request fields | Success response keys | Writes |
| --- | --- | --- | --- |
| `create_synthetic_las.py` | Create deterministic LAS 2.0. Optional `mode`: `create` or `no_resistivity`. | `status`, `well_id`, `path`, `relative_path`, `sample_count`, `curves`, `mode` | `<data_root>/<well_id>.las` |
| `run_las_parse.py` | Parse LAS. Required `las_path` relative to `workspace_dir`; optional `aliases` flat or category-nested object. | `status`, `well_id`, `source_path`, `version`, `wrap`, `well_info`, `curves`, `alias_mapping`, `sample_count`, `depth_range`, `required_curves`, `warnings`, `data_arrays`, `output_path` | `<data_root>/<well_id>_parsed.json` |
| `run_evaluation.py` | Evaluate parsed JSON. Optional `parsed_path`, `area_acres`, `matrix_density`, `fluid_density`, `a`, `m`, `n`, `rw`, `phie_min`, `sw_max`, `vsh_max`, `boi`, `rf`. | `status`, `well_id`, `source_path`, `output_path`, `parameters`, `qc_summary`, `gr_baselines`, `net_pay_summary`, `zones`, `ooip`, `warnings`, `sample_columns` | `<data_root>/<well_id>_evaluation.json` |
| `create_log_plot.py` | Render five-track log. Optional `parsed_path`, `evaluation_path`, `downsample` (integer, default `1`). | `status`, `well_id`, `path`, `bytes`, `dpi` | `<data_root>/<well_id>_log_plot.png` |
| `create_report.py` | Create reports. Optional `parsed_path`, `evaluation_path`, `plot_path`, `recommendations` (array of caller-supplied strings). | `status`, `well_id`, `docx_path`, `markdown_path`, `warnings` | `<data_root>/<well_id>_report.docx` when `python-docx` is available; `<data_root>/<well_id>_report.md` always |

## Exact default requests

Create the synthetic LAS:

```json
{"workspace_dir":"<Quick workspace directory>","well_id":"SYN-LAS-1","data_root":"automated-log-analysis-data","mode":"create"}
```

Parse the synthetic LAS. Read `references/curve_aliases.json` with `file_read`, parse it as JSON, and pass it as `aliases`; the embedded defaults make this field optional.

```json
{"workspace_dir":"<Quick workspace directory>","well_id":"SYN-LAS-1","data_root":"automated-log-analysis-data","las_path":"automated-log-analysis-data/SYN-LAS-1.las","aliases":{}}
```

Evaluate with the locked defaults:

```json
{"workspace_dir":"<Quick workspace directory>","well_id":"SYN-LAS-1","data_root":"automated-log-analysis-data","parsed_path":"automated-log-analysis-data/SYN-LAS-1_parsed.json","area_acres":500.0,"matrix_density":2.65,"fluid_density":0.9,"a":1.0,"m":1.87,"n":2.45,"rw":0.017,"phie_min":0.06,"sw_max":0.5,"vsh_max":0.5,"boi":1.3,"rf":0.35}
```

Create the composite log:

```json
{"workspace_dir":"<Quick workspace directory>","well_id":"SYN-LAS-1","data_root":"automated-log-analysis-data","parsed_path":"automated-log-analysis-data/SYN-LAS-1_parsed.json","evaluation_path":"automated-log-analysis-data/SYN-LAS-1_evaluation.json","downsample":1}
```

Create both reports. Replace the example recommendation with only recommendations supplied or approved by the user.

```json
{"workspace_dir":"<Quick workspace directory>","well_id":"SYN-LAS-1","data_root":"automated-log-analysis-data","parsed_path":"automated-log-analysis-data/SYN-LAS-1_parsed.json","evaluation_path":"automated-log-analysis-data/SYN-LAS-1_evaluation.json","plot_path":"automated-log-analysis-data/SYN-LAS-1_log_plot.png","recommendations":[]}
```

## Documented failures

- Missing common input: `workspace_dir is required`.
- Unsafe identifier: `well_id must match ^[A-Za-z0-9._-]+$`.
- Absolute input path: `<field> must be relative to workspace_dir`.
- Parent traversal: `<field> must not contain parent traversal`.
- Missing LAS: `LAS file not found: <relative path>`.
- Missing depth: `DEPTH curve required but not found`.
- Missing resistivity is not fatal. Evaluation returns `status: "success"`, null `SW` samples, warning `RT not found; water saturation skipped`, `net_pay_summary.sw_cutoff_applied: false`, `net_pay_summary.accuracy` beginning `limited`, null `avg_sw_pay` and zone `avg_sw`, and null `ooip_stb` and `recoverable_stb` with a `note`. Net pay is then screened on porosity and shale volume only; report it as limited accuracy.
- Missing Word dependency is not fatal. Markdown is written and the response warning is `python-docx unavailable; Word report skipped`.
- Degraded evaluations render honestly in both reports: `Net pay basis` names the cutoffs applied and the accuracy string, null Sw appears as `n/a (no resistivity)`, null OOIP appears as `not estimated (<ooip.note>)`, and null zone RT appears as `n/a`.

## Golden values

The default synthetic LAS has 1,501 samples at 0.5 ft from 8,000.0 to 8,750.0 ft. Its locked evaluation values are:

- GR baselines: 35.0 API clean and 120.0 API shaley.
- Net pay: 325.0 ft; gross 750.5 ft; net-to-gross 0.4330.
- Pay zones: 8,100.0–8,199.5 ft, 8,300.0–8,424.5 ft, and 8,550.0–8,649.5 ft.
- Average pay PHIE: 0.2286; average pay Sw: 0.1184.
- OOIP: 195,437,364 STB; recoverable: 68,403,077 STB.
- QC grade: `good`.
