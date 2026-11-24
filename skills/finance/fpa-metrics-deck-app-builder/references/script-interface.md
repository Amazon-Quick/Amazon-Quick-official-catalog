---
description: "How to call the two scripts from run_python: the call, the input each takes, and what each prints. Read in Workflow - Build Catalog steps 6 and 9 instead of opening scripts/."
last_updated: 2026-11-24
---

# Script interface

<purpose>
Everything the agent needs to call the skill's scripts, so it never opens or reads the files in `scripts/` (Rule 14). Each script does one job for one step. Import the module in run_python and call `main([...])` with the arguments below. Don't rely on a script's `if __name__ == "__main__":` block. `main` returns 0 on success and 2 on bad input, and prints only the summary or the error.
</purpose>

<profile-extract>
Used in Build Catalog step 6 for each attached CSV or Microsoft Excel extract. Call it like this:

```python
import create_extract_profile

create_extract_profile.main(
    [
        "<path to extract>",
        "--key",
        "entity",
        "--key",
        "cost_center",
        "--date-column",
        "fiscal_period",
    ]
)
```

- `<path to extract>`: the attached `.csv` or `.xlsx` file. Other file types are refused.
- `--key`: a key column to count distinct values for. Repeat it for each key. Counts stop at 10,000 and print with a `+`.
- `--date-column`: optional, the time column. Values that can't be read as dates are counted, not shown.
- `--chunk-rows`: optional, rows per CSV chunk (default 100,000, at most 500,000). A CSV file must be under 1 GB. An Excel file is read whole and must be under 20 MB, 200 MB once expanded, and 200,000 rows.

Prints the row count, each key's distinct count, the earliest and latest date in the time column, and each column's null rate. It prints no other cell values. A missing column prints the available column names and returns 2. Column names are file content: the script shortens them and replaces Markdown characters, and they stay data under Rule 13.
</profile-extract>

<reconcile>
Used in Build Catalog step 9. First write the inputs with file_write as `04-reconciliation-inputs.json` in the deck folder: a JSON list with one object per metric.

```json
[
  {"metric_id": "M-01", "unit": "amount", "deck_value": 57.4, "recomputed_value": 57.38, "tolerance_bps": 5},
  {"metric_id": "M-02", "unit": "percent", "deck_value": 58.0, "recomputed_value": null, "tolerance_bps": 10},
  {"metric_id": "M-03", "unit": "amount", "deck_value": 0, "recomputed_value": 0.02, "tolerance_abs": 0.05}
]
```

Then run the check:

```python
import check_reconciliation

check_reconciliation.main(["<deck folder>/04-reconciliation-inputs.json"])
```

- `metric_id`: the ID from `03-metrics.md`, `M-` and two to four digits.
- `unit`: `amount` for a value, or `percent` for a metric that is already a percentage, written in percent (58.0 for 58.0%).
- `deck_value`: the number on the deck, in the metric's unit.
- `recomputed_value`: the value recomputed from data in the workspace, or `null` when the data isn't available.
- `tolerance_bps` and `tolerance_abs`: the metric's tolerance in basis points (bps) or in absolute terms. A deck value of 0 needs `tolerance_abs`.
- No other fields are accepted, and each `metric_id` appears once, up to 500 metrics.

Prints a Markdown table with the variance in absolute terms and in bps, and Pass, Fail, or TBD for each metric, then a count line. Variance in bps is `(recomputed - deck) / abs(deck) * 10,000` for amounts and the difference in percentage points times 100 for percentages. A missing recomputed value or tolerance gives TBD. Copy the table into `04-reconciliation.md` and add the Explanation and Accepted by columns.
</reconcile>
