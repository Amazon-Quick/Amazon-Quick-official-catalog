---
description: "How the workflow calls the bundled scripts: the input columns, each function's arguments, what to print, and the result keys the steps read. Read in Workflow - Write Commentary steps 5, 8, 9 and 11 instead of opening scripts/."
last_updated: 2026-11-24
---
# Script interface

Import `variance_check` in run_python and call these functions. It re-exports everything the workflow needs from the other modules in `scripts/`, so no other import is needed. Every function takes table text, not a path, and none of them reads or writes files.

## Input columns

Column names are matched case-insensitively, and common aliases work (for example `budget`, `plan`, or `forecast` for `comparison`).

| Column | Required | Meaning |
| --- | --- | --- |
| `line` | Y | Line name, unique per table |
| `actual` | Y | Actual value |
| `comparison` | Y | Value compared against |
| `variance` | N | Stated variance, checked against actual - comparison |
| `type` | N | `revenue`, `cost`, `profit`, `ratio` (a %, shown in bps), `per_unit` (an amount per unit), or `metric`. Inferred from the name when blank |
| `parent` | N | The line this row rolls up into. Without it, footing is not checked |
| `rollup` | N | `+` or `-`: how the row adds into its parent. Default: `-` for a cost under a profit or revenue parent, else `+` |
| `favorable_when` | N | `higher`, `lower`, or `neutral` (reported, never labeled F or U) |
| `formula` | N | For ratio and per-unit lines: `<numerator line> / <denominator line>`, recomputed from the table |

Money cells may use `$`, `€`, `£`, thousands separators, parentheses for negatives, and a `K`, `M`, or `B` suffix. Blank, `n/a`, `nan`, and `inf` cells count as missing.

## check(text, unit="", materiality_pct=2.0, materiality_abs=None, rounding=None, costs_negative=False)

Footing, variance, direction, and materiality for the table.

- `unit`: a label for the report only.
- `materiality_pct`, `materiality_abs`: the user's threshold, if given (references/methods.md, Materiality).
- `rounding`: an explicit footing tolerance. Leave it out: by default the tolerance is half the last digit shown, and it grows with the number of lines summed into each total.
- `costs_negative`: set to `True` only after the user confirms costs are stored as negatives.

Print `summarize(report)`, never the full report. The summary holds:

- `status`: `PASS`, `PASS with warnings`, or a string that starts with `FAIL`.
- `tolerance`: the rounding tolerance used, in the table's unit.
- `faults`: why the table does not foot. Any fault makes the status FAIL.
- `warnings`: questions for the user, such as negative costs, an unknown direction, a rounding difference, or a zero comparison base.
- `rows`: per line, `line`, `type`, `parent`, `actual`, `comparison`, `variance`, `variance_pct`, `variance_bps` (ratio lines), `direction` (`F`, `U`, `flat`, `neutral`, `ask`, or `n/a`), and `material`.

## check_ledger(ledger_text, report)

Checks the cause ledger against a `check` report from the same input, and totals it for the proof block. The ledger has the columns `line, piece, amount, tag, evidence, outlook, owner, due`. A row whose `line` is `Other lines` holds the non-material lines rolled up within the tolerance.

```python
from pathlib import Path

import variance_check

UNIT = "M"  # the unit the user confirmed in step 2
artifacts = Path(WORKSPACE_DIR) / "artifacts"
report = variance_check.check(
    (artifacts / "variance_input.csv").read_text(encoding="utf-8-sig"), unit=UNIT
)
print(
    variance_check.check_ledger(
        (artifacts / "variance_ledger.csv").read_text(encoding="utf-8-sig"), report
    )
)
```

Pass the same `unit`, `costs_negative`, and materiality arguments as in step 5. The result holds:

- `status`: `PASS` or `FAIL`.
- `faults`: pieces that do not add up to a line's variance, unknown tags or outlooks, a Rounding piece over the tolerance, an Unexplained piece over the tolerance with no named owner or due date, and component lines over the tolerance with no ledger rows.
- `gross_by_tag`: absolute amounts per tag on material component lines (not subtotals).
- `gross_total`: the sum of `gross_by_tag`.
- `unexplained_share_pct`: the Gross Unexplained Share, in percent.

## rvm(text)

Rate, volume, and mix for a segment table with the columns `segment`, `actual_units`, `comparison_units`, `actual_rate`, and `comparison_rate` (aliases such as `budget_units` and `plan_rate` work). Print the result. Its `segments` list has one entry per segment.

- `status`: `PASS` when volume + mix + rate equals the total variance, else `FAIL` with `faults`.
- `segments`: per segment, `volume`, `mix`, `rate`, `total`, and `mix_vs_avg` (references/methods.md, Rate, volume, and mix).
- `totals`: the same effects summed over the segments.
