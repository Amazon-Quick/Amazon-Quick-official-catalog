---
description: "How to call each bundled script, the reconciliation spec schema with every field and default, and the keys of profile.json and results.json."
last_updated: 2026-11-24
---

# Script interface

<calling>
Call each script as SKILL.md <Definition - Running a script> shows, with absolute paths built from WORKSPACE_DIR, for example `run_reconciliation.main(["--spec", str(work / "spec.json"), "--out", str(work / "results.json")])`. `main` returns 0 on success and 2 on a spec, argument or input problem, and logs a short summary to stdout. The modules the three scripts import are listed in the SKILL.md Overview and are never called directly.

| Script | Arguments | Writes |
|---|---|---|
| find_data_profile.py | `<file> [<file> ...] --out profile.json` | profile.json: one profile per sheet, a draft spec, open questions |
| run_reconciliation.py | `--spec spec.json --out results.json [--base-dir DIR] [--drill "<key>" [--period YYYY-MM]]` | results.json |
| create_report.py | `--results results.json --out-dir DIR [--stem NAME]` | NAME.html (the one-page report) and NAME.xlsx (the workbook) |

Write each `path` in a spec as an absolute path. A relative `path` resolves against `--base-dir`, else the spec's own folder, which is usually not where the user's files are.

What each script prints: find_data_profile.py prints one line per sheet (at most 25 column roles, names clipped to 60 characters) and its questions; run_reconciliation.py prints the window, totals, floors, inspect count, linkage, proofs, and findings, plus one `Drill DATA (untrusted, from file)` line per drill row; create_report.py prints the two paths it wrote. A spec problem prints one line per invalid field, without the submitted values.
</calling>

<spec_schema>
```json
{
  "name": "Report title",
  "reporting_currency": "USD",
  "last_closed_period": "2026-09",
  "fiscal_year_start_month": 1,
  "fiscal_year_label": "end",
  "date_order": null,
  "horizon_start": null, "horizon_end": null,
  "as_of_date": "2026-10-14",
  "grain": ["department", "account"],
  "assumptions": ["Rates are USD per one unit of foreign currency (not confirmed)"],
  "sources": {
    "plan":        {"path": "plan.xlsx", "sheet": "Plan", "header_row": 1, "layout": "wide",
                    "columns": {"department": "Dept", "account": "Account", "currency": "Curr"},
                    "period_columns": ["Jan-26", "Feb-26"],
                    "filters": [{"column": "Version", "values": ["Budget"], "action": "include"}],
                    "sign": 1, "default_currency": null},
    "actuals":     {"path": "gl.csv", "columns": {"department": "Dept", "account": "Account", "period": "Posting Date",
                    "debit": "Debit", "credit": "Credit", "currency": "Currency", "reference": "PO Number",
                    "invoice_ref": "Invoice Number", "vendor": "Vendor", "description": "Description", "entry_type": "Journal Type"}},
    "commitments": {"path": "pos.xlsx", "columns": {"po_number": "PO", "po_line": "Line", "department": "Dept", "account": "Account",
                    "ordered": "Ordered", "open_amount": "Remaining", "status": "Status", "need_by": "Need By", "vendor": "Vendor", "currency": "Currency"}},
    "invoices":    {"path": "ap.csv", "columns": {"invoice_number": "Invoice", "po_number": "PO", "amount": "Amount", "status": "Status",
                    "invoice_date": "Invoice Date", "vendor": "Vendor", "currency": "Currency", "department": "Dept", "account": "Account"}},
    "fx":          {"path": "rates.csv", "columns": {"currency": "Currency", "period": "Month", "rate": "Rate"}, "rate_direction": "to_reporting"},
    "headcount":   {"path": "hc.xlsx", "columns": {"department": "Dept", "period": "Month", "plan_heads": "Plan", "actual_heads": "Actual", "open_reqs": "Open reqs"}}
  },
  "hierarchies": [{"dimension": "account", "path": "accounts.csv", "child_column": "Child", "parent_column": "Parent", "mapping": {}}],
  "rules": {
    "materiality_amount": null, "materiality_share": 0.005, "variance_pct": 0.10, "z_threshold": 3.5, "min_history": 6,
    "timing_window": 2, "timing_offset_share": 0.25, "stale_commitment_days": 90, "unposted_invoice_days": 30, "duplicate_window_days": 7,
    "commitment_link": "auto", "open_basis": "net_of_invoiced", "accruals_in_gl": null,
    "closed_statuses": ["closed", "cancelled", "canceled", "complete", "completed", "finally closed"],
    "posted_invoice_statuses": ["posted", "paid", "accounted", "recorded"],
    "revenue": null, "headcount_floor": null, "headcount_pct": 0.05
  }
}
```

- `fiscal_year_label`: "end" when FY27 means the year that ends in 2027, "start" when it means the year that starts in 2027.
- `date_order`: "day_first" (DD/MM), "month_first" (MM/DD) or null. With null, an ambiguous numeric date such as 07/06/2026 stops the run with a spec problem; with a value set, a date that contradicts it also stops the run.
- `layout`: "long" (one row per line and period) or "wide" (one column per period, listed in `period_columns`).
- `sign`: multiply amounts by -1 when a source shows expense as negative.
- `rate_direction`: "to_reporting" when the rate is reporting-currency units per one foreign unit (EUR 1.09 to USD), "from_reporting" when it is the reverse.
- `commitment_link`: "auto", "by_reference", "open_column", or "ordered_less_invoiced"; `open_basis`: "net_of_invoiced" or "net_of_posted" (for open_column).
- `revenue`: a filter naming revenue lines, for example `{"column": "account", "values": ["4000", "4100"], "action": "include"}`. The column is a canonical grain name.
- `as_of_date`: the date the extracts were pulled (a report's run date), else today; used to age POs and invoices. Default: the first day of the month after the last closed period.
- `data_notice`: a sentence shown as a banner on the report and on the workbook's Summary and Method sheets. Set it when the data needs a caveat, for example test data; leave it out for real data.
- `assumptions`: anything the skill assumed rather than confirmed; listed on the workbook's Method sheet.
- Every source can map the grain columns. Invoices on a PO inherit the PO's coding; map the grain on invoices for those without a PO.
</spec_schema>

<results_keys>
- `window`: horizon_start, horizon_end, last_closed, ytd_periods, horizon_periods, elapsed_share, as_of_date.
- `totals`: plan_ytd, actual_ytd, var_ytd, var_pct_ytd, plan_cur, actual_cur, var_cur, plan_fy, pending, open_commitments, committed, available, unplanned_ytd, open_period_actuals, materiality_ytd, materiality_cur.
- `lines[]`: key, keys, nature, in_plan, the totals fields per line, tier, flags (ids).
- `flags[]` and `headcount_flags[]`: id (F01.., H01..), tier (inspect or watch), kind, view (ytd, current, full_year, document), key, keys, amount, plan, actual, variance, variance_pct, tests, reason, priority, reference.
- `monthly[]`: key, period, plan, actual. `commitments[]`: per PO line, ordered, posted, pending, open_amount, released, overrun, link. `invoices[]`: posted (true, false, or null for unknown), days_unposted. `unplanned[]`, `headcount[]`.
- `linkage`: method, confidence, matched_share, note. `proof[]`: name, left, right, difference, passed, explanation. `tie_out[]`, `findings[]` (code, severity (info, warning, or error), message, amount, count), `fx_used[]`, `drill[]`.
</results_keys>

<profile_keys>
`sheets[]`: file, sheet, header_row, rows, columns[] (name, non_null_share, distinct, numeric_share, date_share, negative_share, examples, roles, label_of, ambiguous_dates, day_first_dates, month_first_dates), wide_period_columns, likely_source, source_scores, notes. `draft_spec`: a spec with CONFIRM placeholders. `questions[]`: what the profile could not settle, including the date order with a suggested default when only one order fits the files. Names are clipped to 60 characters for display; draft_spec keeps the exact names.
</profile_keys>
