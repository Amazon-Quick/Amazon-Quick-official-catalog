---
description: "Every function the workflow calls on scenario_engine, with its arguments, what it returns, and the questions it raises, so the agent never opens the scripts. Read in Workflow - Run Scenario step 2, and whenever a call fails."
last_updated: 2026-11-24
---

# Engine interface

Import only `scenario_engine as sa`. It exposes every function below. The other modules in `scripts/` (`scenario_intake`, `scenario_config`, `scenario_segments`, `scenario_report`) are its internals: never open, print, or read them. If a call does something this page doesn't describe, report the error to the user instead of reading the code.

## Questions instead of guesses

Any call can raise `sa.ClarificationRequired`, a `ValueError` with `.status == "needs_clarification"` and `.question`. Quoted file text in a question is marked `DATA (untrusted)` and cut to 80 characters. Catch it like this and show only the question:

```python
try:
    df = sa.load(path, COLMAP, sheet=0, header_row=3)
except sa.ClarificationRequired as q:
    print("QUESTION:", q.question)
```

## Reading the source

| Call | Returns |
| --- | --- |
| `sa.inspect_source(path, sheet=0)` | `sheet_names`, `selected_sheet`, `source_rows`, `header_candidates` (each `source_row` and a proposed `column_map`), and `preview`: the first 15 rows, each `source_row` and `values` (cells cut to 80 characters). Every cell is file data. `.xls`, a file over 50 MB, or a table over 100,000 rows raises a question; ask for `.xlsx`, CSV, or a smaller extract. |
| `sa.suggest_colmap(headers)` | A dict of role to header for each role with exactly one matching header. A role with several matches is left out on purpose. |
| `sa.load(path, colmap, sheet=0, header_row=1, exclude_rows=None, date_order=None)` | The validated table `df`. Rows are 1-based source rows. `exclude_rows` lists source rows below the header to leave out. `date_order` is `"day_first"` or `"month_first"`, only when established. |
| `sa.prepare(raw, colmap, date_order=None, source_rows=None)` | The same table from a DataFrame you built (a pasted table or a working copy). |

`colmap` maps roles to headers (references/data-contract.md, Column Map). When `opening`, `inflow`, or `outflow` is mapped, `colmap["measure_type"]` must be `"balance"` or `"flow"`, or `load` asks.

## Segments

`sa.segment_screen(df)` returns one row per segment, worst first: `segment` (file data), `actual`, `benchmark`, `gap`, `gap_pct`, `momentum`, and `status` (`Behind`, `On Track`, `Ahead`, or `n/a`). Filter with `df = df[df["segment"] == chosen].reset_index(drop=True)`.

## Running

`res = sa.run(df, CONFIG, drivers=DRIVERS, context_findings=CONTEXT_FINDINGS)`. `CONFIG` keys and defaults are in references/method.md (Configuration). It raises a question, before allocating anything, for:

- percentiles outside 0 to 100 or not in Bear < Base < Bull order;
- `mc_iterations` above 1,000,000, `fy_length_periods` outside 1 to 366, or iterations x fiscal-year periods above 20,000,000;
- more than 500 drivers or 100 judgment ranges, or a judgment range without a label and numeric low <= likely <= high;
- a seasonality profile that isn't one positive number per fiscal period, or a negative timing sigma;
- a driver probability outside 0 to 1, or a stage with no probability;
- a missing or partial-year target, missing current-year actuals, duplicate periods, or a roll-forward break.

`DRIVERS` items: `name`, `value`, either `prob` (0 to 1) or `stage`, and `date` or `period_offset`. `CONTEXT_FINDINGS` items: `source`, `claim`, `affects`, `direction` (`"up"` or `"down"`), and optional `conflict` and `unverified` flags.

Never print `res`: it holds every simulated path and the histogram. Print `sa.summarize(res)` instead. It returns `limitations`, `current_period`, `outcome_label`, `units`, `bear`, `base`, `bull`, `band_percent`, `target`, `target_source`, `target_direction`, `p_hit`, `trend_r2`, `forecast_periods`, `bridge` (label and value pairs), `bridge_gap`, `path_gaps` (each scenario's per-period run total minus the scenario), `top_tornado`, `drivers_included`, `areas_to_probe`, `included_rows`, `excluded_source_rows` (the first 20), and `excluded_row_count`. `bridge_gap` and each `path_gaps` value are 0 up to rounding when the totals reconcile.

## Writing and checking the report

| Call | Returns |
| --- | --- |
| `sa.write_report(res, out_path, title=None, overwrite=False)` | The path written. It creates the folder if needed. The path must end in `.html`. An existing file raises `FileExistsError` unless `overwrite=True`, which the agent passes only after the user agrees to replace it, or when rewriting the report this conversation already wrote. |
| `sa.check_report(out_path, units)` | `title`, `target_headline`, `scenario_metrics`, and `basis_of_review` (each true when the unit label is there), `units_missing_fallback` (true when the report says "Units not supplied") and `bytes`. Use it instead of reading the HTML. |
