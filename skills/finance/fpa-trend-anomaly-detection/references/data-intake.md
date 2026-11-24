---
description: "How intake reads an export before any analysis: the ready and needs-clarification states and what each requires."
last_updated: 2026-11-24
---
# Read the data before interpreting it

An unreadable row can change the trend or turn a normal period into a false anomaly. Intake therefore returns one of two states:

- `ready`: the selected rows are understood and `series` can be passed to `sr.prepare`.
- `needs_clarification`: `series` is empty. Read `questions` and the source locations, ask the user, and wait. A report is not ready.

Ask only what changes the answer. Inspect the file first and do not ask users to rename clear headers or reformat clear dates. Use short questions with examples: "Row 8 says `01/04/2025`. Is that 1 April or January 4?" A default is not a substitute for this answer.

## Long tables and CSV

`si.extract_long` accepts the existing sheet, column, and filter arguments and these resolution arguments:

| Argument | Use |
|---|---|
| `header_row=4` | The actual header is on row 4. One-based; identify it from the file or the user's reply. |
| `date_order="DMY"` or `"MDY"` | The user confirmed how ambiguous numeric dates should be read. Named months, ISO dates, Excel dates and numeric dates with only one valid interpretation do not need this answer. |
| `aggregate_duplicates=True` | The user confirmed repeated rows for the same line and date are separate amounts that should be added. Do not set this for balances or rates. Alternatively use more `key_cols` to separate the lines. |
| `skip_rows=[8, 19]` | The user explicitly approved excluding these source rows. Do not fill this automatically for rows that failed to parse. |
| `unit_col="Units"` | Identify a nonstandard units column. Common names such as Units, Currency, UOM, and Scale are found automatically. |

Mixed units or currencies block the combined analysis. If the user confirms a conversion, create a separate working copy with the confirmed factors and source-row mapping, then re-read it. Keep the original unchanged and disclose the conversion; do not invent an exchange rate.

For `extract_long`, `row_audit` names every row below the header as `loaded`, `excluded`, or `unresolved`, with its reason. `row_counts` totals those groups; rows above `header_row` are title and header context, not data. Clear repeated headers, blank rows, explicitly labeled summary rows, and clear empty footers are recorded as exclusions. Bad dates or values are unresolved. A scan that reaches the row cap blocks instead of claiming a complete review. `extract` (wide sheets) returns no row audit; check its `skipped` and `issues` instead. Print `row_counts` and only the entries that are not `loaded`, never the whole `row_audit`.

When ready, compare loaded counts with the input and report the exclusions. "Unresolved date at row 8" is not "missing April." Only after input validation may preparation identify periods with no source observation.

## Wide tables

`si.extract` also returns a status. Repeated period columns without Actual or Plan labels, unreadable period headings over values, and text errors in the selected history require clarification. Use `period_row=` and, if needed, `date_order=` after the meaning is known. Do not select the first repeated period or trim to the longest regular run.

Zeros remain zeros. If a trailing zero could mean "not posted," ask before interpreting that drop. Totals remain separately identified, and selected actual periods are distinguished from incomplete or future periods.

## Resume without another interview

Keep the selected path, sheet, header, columns, filters, date convention, units, and explicit exclusions in the current conversation's working notes. Apply the answer and run intake again. Ask another question only if that re-read reveals a different material conflict. If the source is clean, state the reading briefly and continue.

`sr.prepare` checks pasted and derived series too. An unreadable date, mismatched count of dates and values, or unresolved grain is a question; `sr.run` rejects unanswered preparation questions even when `freq` was supplied.
