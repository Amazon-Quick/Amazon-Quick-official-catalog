---
description: "The canonical, system-neutral fields every pasted table is mapped onto. Read when mapping columns or running a single module."
last_updated: 2026-11-24
---
# Canonical fields (system-neutral)

These are the names the checks use. With `--input` (and always with `all`) the user's column names are mapped to them automatically, so don't reshape a pasted table; check `mapped_columns` instead. Column names are matched case-insensitively with spaces and punctuation turned into `_`, and the engine reports every header it mapped in `mapped_columns`. Unknown extra columns are kept but ignored. If two columns could fill one field, ask.

| Object | Required | Optional |
|---|---|---|
| Requisition / request | id, vendor, amount, date | requester, cost_center, account, project, period (YYYY-MM), freight, tax, contingency, service_start, item, qty, unit_price, sole_source_reason, justification |
| PO / PO line | po, amount (or qty x unit_price) | line, contract_id, po_date, start, end (period of performance), end_date, item, qty, unit_price, payment_terms_days, account_type |
| Receipt (goods or service entry) | po, line, qty_received | receipt_date |
| Invoice line | invoice_no, po, line, qty, unit_price, amount | vendor (needed for the duplicate check across suppliers), invoice_date, service_start, service_end, stated_total |
| Contract / rate card | contract_id, ceiling, start, end | vendor, payment_terms_days, auto_renew, notice_days; rate card rows: contract_id, item (or role), rate |
| Change order | contract_id, amount | date, reason |
| Budget line | grain columns (for example cost_center, account), period, amount | source (budget / forecast / allocation), pooled (Y/N). One table with budget, actuals, and open commitments columns side by side is also accepted and read as all three. |
| Actuals | grain columns, period, amount | |
| Open commitment | po, grain columns, period, po_amount, invoiced | received, need_by, status |
| Price history | item, unit_price, date | vendor |
| Quote | quote_id (or request_id), vendor, amount | valid_until |
| Coding line | id, account, account_type (expense / asset / prepaid / balance_sheet), amount | unit_price, useful_life_months, category, service_start, service_end, project, vendor, item |

## Conventions
- Dates: YYYY-MM-DD preferred; MM/DD/YYYY and DD-Mon-YYYY accepted. Periods: YYYY-MM preferred; Mon-YYYY, MM/DD/YYYY, and quarter labels (2026-Q4) accepted.
- Amounts in one currency (the profile's). If a table mixes currencies, stop and ask for rates.
- Grain key: the budget, actuals, commitment, and request tables must share the grain columns named in `--grain`.
- `account_type` is supplied by the user or derived from the profile's `coa_style`; say which.
- Source citation: the script reports `file:line` (inside the parsed table). In the report, cite the original document and row ID instead.

## `all` arguments and outputs

Arguments: `all --input FILE [--grain cost_center,account] [--fiscal-start-month 1-12] [--tiers 10000,50000] [--period-start D --period-end D] [--price-tol 0.02] [--qty-tol 0] [--capex-threshold N] [--materiality N] [--quote-threshold N --quotes-required N] [--price-history-tol 0.20] [--template-fields CSV] [--as-of D]`. Every threshold is optional; a missing one is reported in `not_run`, never assumed.

Outputs used by the report: `bottom_line`, `totals_line`, `groups` (verdict, display, count, amount), `totals`, `check_sum_ok`, `overall_verdict`, `findings` (rule, item, severity, what, number, source, at_stake), `not_run`, `items` (item, type, supplier, amount, cost_center, project, account, category), `justification_rows` (item, text, read_from), `match_rows` (item, po_line, ordered_qty, received_qty, invoiced_qty, invoiced_qty_cumulative, po_price, invoice_price, qty_match, price_match, duplicate_check), `po_burn`, `inputs`, `mapped_columns`, `excluded_rows`, `ignored_tables`, `unreadable_periods`, `over_invoiced_commitments`, `notes`, `policy_candidates`. The keys after `mapped_columns` are present only when they apply, so read them with `.get()`. `items[].type` is `request`, `invoice`, or `po` for a PO reviewed as its own item. Amounts in the JSON are plain decimals (`12500.00`); the two sentences are already formatted for the report (`$12,500.00`).

## Arguments to `all`

Pass every profile value you have as an argument; leave out the ones you don't (the check reports not run instead):

```
"--grain", "cost_center,account"   budget grain columns from the profile (default is labeled ASSUMPTION)
"--fiscal-start-month", "2"        first month of the fiscal year, 1-12 (default 1, labeled ASSUMPTION)
"--tiers", "10000,50000"            approval tier upper limits, comma-separated, lowest first
"--period-start", "2026-10-01", "--period-end", "2026-10-31"     invoice review period
"--price-tol", "0.02"               invoice unit price against PO price
"--capex-threshold", "5000", "--materiality", "1000"
"--quote-threshold", "25000", "--quotes-required", "2", "--price-history-tol", "0.20"
"--template-fields", template_csv   CSV file in WORK with one column "element" (justification template)
"--as-of", "2026-11-12"             today's date
```

## Tables for values stated in prose

**When the message has no table.** The script reads tables only (Markdown pipe tables or CSV), never prose. If `parser_tables` is empty or misses an item the user described (for example a PO written as an email sentence), write the values the message states as a small table, append it to the saved file under a line `Model-extracted from the message:`, and run `all` again. Use these headers so each table is recognized, and leave a cell blank rather than infer a value the message doesn't state:
- requisition: `id, vendor, amount, date, cost_center, account, justification`
- PO: `po, line, item, qty, unit_price, amount, vendor, cost_center, account, contract_id, justification` (a one-line PO may leave `line`, `qty` and `unit_price` blank)
- contract: `contract_id, ceiling` (add `start, end` when stated); a contract mentioned in prose ("an MSA with a $15,000 annual ceiling") becomes this table plus the `contract_id` on the PO or requisition row
- invoice: `invoice_no, vendor, invoice_date, po, line, qty, unit_price, amount`

Say in Basis of review which values were model-extracted.

## Running one module

**Single modules.** The subcommands `profile`, `coding`, `budget`, `contract`, `price`, `approval`, `invoice`, `justification`, `combine`, and `summary` remain for running one check on its own (see the module reference files for their arguments). If you run modules one by one for 2+ items, run `combine --results a.json,b.json` and then `summary --verdicts combined.json --items items.csv` (columns `id, amount[, status]`) to get `bottom_line`, `totals_line`, `groups` and `check_sum_ok`.
