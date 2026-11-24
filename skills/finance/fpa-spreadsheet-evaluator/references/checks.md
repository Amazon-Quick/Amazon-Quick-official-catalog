---
description: "What each scan finding means, why it matters and when it is not a problem. Read when explaining a finding or deciding whether it is verified or a question."
last_updated: 2026-11-24
---
# Check reference: what each finding means and when it's not a problem

## Contents
- Errors
- Hardcodes and consistency
- Risk
- Tables
- Cell formatting
- Conditional formatting and dropdowns
- Pivots
- Formula patterns
- Performance
- Data hygiene
- Reconciliation
- Financial logic (verified)
- Questions for the owner (judgment)
- Structure

Each entry: **what it means**, then **dismiss or downgrade when...** for the judgment step. "Info" in the scan is shown as **Suggestion** in the report.

Every finding carries `area` (formula, data, logic, structure) and `basis`: `verified` (an exact check) or `judgment` (a question for the owner, with a `question` field). Judgment findings are never critical and never get an automatic fix.

## Errors (Critical)

**error_value**: the cell shows #REF!, #DIV/0!, #N/A, #VALUE!, #NAME?, #NUM!, or #NULL!. When an error causes others downstream, the scan names the cause; report the root cell first.
- **Downgrade when** an #N/A is a deliberate "no data yet" marker inside an IFERROR-protected chain, or a #DIV/0! sits in a future period with no data. Say which.

**ref_in_formula**: the formula text contains #REF!, meaning a row, column, or tab it used was deleted. Treat it as real.

**circular_reference**: cells depend on each other in a loop.
- **Downgrade when** the model intentionally iterates, for example interest on an average debt balance with iterative calculation turned on. Ask if unsure.

**external_link**: the formula pulls from another file. The number goes stale or breaks when that file moves.
- **Downgrade when** the user confirms the link is a maintained, intended feed.

**broken_named_range**: a defined name points at #REF!. Treat it as real; it is usually harmless unless a formula uses the name.

## Hardcodes and consistency (Warning)

**hardcoded_number_in_formula**: a number typed into a formula, for example `=B5*0.35`. The scan already ignores:
- unit conversions: 7, 12, 24, 52, 60, 100, 365, 1000
- 0 and 1
- positional arguments, such as the column number in VLOOKUP or the digits in ROUND

**Dismiss when** the number is a fixed fact: unit conversions, a legal constant, a number of days. **Keep when** it's a business assumption someone might want to change: a rate, price, growth, mix, or allocation share.

**value_in_formula_row**: a typed number sits where the matching formulas around it say a formula should be. It's usually pasted over. The number may look right today but won't update.
- **Dismiss when** a label or note says it's a manual override, for example "Actuals" or "Override". Even then, suggest marking it visibly.
- Replacing it requires explicit confirmation by change number: the pattern alone does not prove it was pasted over accidentally.

**inconsistent_formula**: a formula differs from the identical formulas on both sides of it.
- **Dismiss when** the cell is a labeled one-off, such as a stub period or a known one-time adjustment.

**sum_range_gap**: a total stops before the last line of its block, so the line is left out.
- **Dismiss when** the excluded line is a memo or sub-line the label says is excluded.

**ref_to_empty_cell**: a formula uses a blank cell, which Excel counts as zero.
- **Dismiss when** the blank is a deliberate "not applicable" input. Even then, suggest a 0 so the intent is visible.

## Risk

**volatile_function** (Warning): OFFSET or INDIRECT. These hide what they point at, recalculate constantly, and break silently when tabs or rows change.
- **Downgrade to Info when** used once over a tiny range in a clearly labeled helper.

**long_formula** (Info): over 250 characters, or more than four nested IFs. Suggest helper rows or a lookup table.

**hidden_sheet** (Warning if it feeds visible tabs, otherwise Info): hidden inputs are a classic source of surprise numbers.

**hidden_rows_in_block** (Info): rows or columns hidden inside the data, not grouped.
- **Dismiss when** they're clearly grouped and labeled; note that the scan can't see outline groups.

## Tables

**data_past_table_edge** (Warning): rows sit right below an Excel Table but outside it, so Table formulas, pivots, and charts miss them.

**generic_table_header** (Info): "Column1" or a blank header.

**fixed_range_over_table** (Warning): `SUM(Data!C2:C51)` instead of `Orders[Amount]`. It won't grow with the Table.

## Cell formatting

Style findings are always relative to the model's own conventions (from a legend, or from what 70 percent or more of cells do). If the user corrects the convention, dismiss the style findings that depended on it.

**input_style_break** (Warning): a typed number not styled like the model's other inputs. People won't know it's typed in.

**formula_styled_as_input** (Warning): a formula styled like an input. Someone may overwrite it.

**link_style_break** (Info): a cross-tab formula not styled like the others.

**total_style_break** (Info): a bold total row with different borders or fill than the tab's other total rows.

**mixed_units** (Warning): one cell in $M while the tab is in $K, or similar. Readers misread the scale.
- **Dismiss when** the exception is labeled, for example "($M)" in the row label.
- Ask whether the difference is intentional and which units are stored before quoting a monetary impact. This finding is Needs you; copying a neighbor's format is not a safe automatic fix.

**mixed_decimals** (Info): a different number of decimals than the rest of its row (models) or column (data tabs).

**number_as_text / date_as_text** (Warning): the value is stored as text. Sums skip it, and sorting and date math break. Typed text numbers are found in rows as well as columns (a line of months where a few were loaded as text), and on files with no saved formula results.

**percent_general_format** (Info): a rate like 0.15 shown in General format.

**merged_cells_in_calc** (Info): merges break copying across and sorting. Center Across Selection gives the same look.

**no_freeze_panes** (Info): a long tab (40 or more rows) with no frozen header.

**column_too_narrow** (Info): the number shows as ####.
- **Dismiss when** the user only reads the file in a tool that auto-fits columns.

## Conditional formatting and dropdowns

**cf_fragmented** (Warning): one highlight rule split into 20 or more copies, usually from copy-paste. Many copies of one rule can slow a file down and make it larger. The fix is to delete the copies and apply one rule to the whole range.

**cf_broken_ref** (Warning): a rule points at #REF!.

**cf_whole_column** (Info): a rule covers a million rows; it slows the file.

**dv_broken_source** (Warning): a dropdown's list points at #REF!.

**dv_violation** (Warning): a cell holds a value its dropdown doesn't allow; it was probably pasted in.

## Pivots

**pivot_source_short** (Warning): the pivot's source range stops before the data does, so totals miss recent rows.

**pivot_fixed_range** (Info): built on a typed range, not a Table, so it won't grow. Often appears alongside pivot_source_short.

**pivot_stale_cache** (Warning): the pivot was last refreshed with fewer rows than the source now has, so its numbers are out of date.

**formula_reads_pivot_by_position** (Warning): `=Pivot!B5` reads whatever lands in B5, which changes if the pivot is filtered or reshaped. Suggest GETPIVOTDATA or SUMIFS on the source.

**pivot_missing_source** (Critical): the source tab or table no longer exists.

## Formula patterns

**vlookup_approx** (Warning): VLOOKUP/HLOOKUP with no 4th argument does an approximate match. On an unsorted list it returns a wrong value without any error. The fix (adding FALSE) can change results, which is the point.
- **Dismiss when** the table is sorted ascending and a range lookup is intended, such as tax brackets, tiers, or commission bands.

**lookup_hardcoded_col** (Info): the return column is a typed number, such as `,4,`. Inserting a column in the table shifts the result.

**lookup_style_inconsistent** (Info): most lookups use one style (XLOOKUP, INDEX/MATCH, or VLOOKUP) and these use another. The fix rewrites them in the model's style. It never introduces XLOOKUP into a model whose readers might be on older Excel.

**iferror_masking** (Info): IFERROR(calculation, 0) hides every error, including real ones.
- **Dismiss when** it guards a known case, like a zero denominator in future periods. Even then, IF(denominator=0, 0, ...) is clearer.

**redundant_formula** (Info): `=+A1` or `=SUM(A1+B1)`. It's harmless, but noise when reviewing.

**compat_function** (Warning): the function needs a newer Excel than the readers have, so they see #NAME?. Only raised when an Excel target is set.

## Performance

**calc_manual** (Warning): numbers on screen may be stale.
- **Dismiss when** the owner keeps it manual on purpose for a very large model. Even then, note it in the file.

**iterative_calc_on** (Warning): circular references calculate silently.
- **Dismiss when** the model has an intended loop, such as interest on average debt.

**inflated_used_range** (Warning): formatting far past the data makes Excel treat the area as used. The fix removes only empty formatted cells.

**excess_cell_styles** (Info/Warning): thousands of stored formats, usually from copying between workbooks.

**whole_column_array** (Warning): SUMPRODUCT or array formulas over whole columns calculate a million rows. Whole columns in SUMIFS, COUNTIFS or lookups are fine and aren't flagged.

**sumproduct_conditional** (Info): SUMPRODUCT used as a conditional sum. SUMIFS is usually faster, but it reads wildcards (`*`, `?`, `~`), comparison operators, and text numbers in the criteria differently, so the rewrite is marked `confirm`.

**volatile_load** (Warning): 50 or more cells with TODAY, NOW, or RAND. Put the date in one cell and reference it.

**unused_named_range** (Info): names no formula, rule, or dropdown uses. The scan can't see names used by charts, macros, or other files.
- **Dismiss when** the owner says a macro or another file uses them.

## Data hygiene

**blank_rows_in_data** (Info): breaks filters, sorting, pivots, and Ctrl+arrow selection.

**empty_cell_gap** (Info): one blank in a column that is otherwise filled. It could be missing data.
- **Dismiss when** the blank means "not applicable" or "not yet".

**lookup_key_spaces** (Warning): 'East ' doesn't match 'East', so lookups miss these rows and SUMIFS leaves them out.

## Reconciliation (Data integrity)

**period_total_mismatch** (Critical if the total is typed, Warning if it's a formula): a Total / FY / YTD column doesn't equal the sum of its months or quarters. Rows labeled as rates, averages, headcount, balances, or other non-additive measures are skipped, and so are totals that equal the average, first, last, max, or min.
- **Dismiss when** the total is deliberately non-additive and the label doesn't say so (for example "Ending FTEs" written as "FTEs"). Suggest a clearer label.

**crossfoot_mismatch** (Critical): for a total row in a block, the periods added across and the lines added down give different grand totals. One of the SUMs covers a different range, or a line's total is typed.

**tie_out_mismatch** (Warning): a typed number with the same label (and period) as a calculated value elsewhere, but a different value, for example a summary typed as 9,000 when the forecast calculates 17,854.
- **Dismiss when** the typed figure is a deliberate snapshot (for example "Board-approved budget") and labeled as such.

**same_metric_differs** (Question): two calculated values with the same label differ. Often two definitions (gross and net) sharing a name.

**period_misaligned_link** (Warning): a row that pulls each period from another tab reads a consistently shifted column (Jan reads Feb). Rows labeled prior, opening, lag, and similar are skipped.

**header_formula_mismatch** (Critical): a period header disagrees with the period its own column's formulas read from another tab. The header says Apr 2025 while the formulas below read Apr 2026 from Data. The scan reads the period from the source column's header, or from the row label on a long-layout tab, and raises it when at least two formulas agree on a different period than the header. Either the header or the formulas are wrong; the owner decides which, so it goes to Needs you.
- **Downgrade when** the column is a deliberate comparison (prior year, lag, offset) and the header says so.

**text_in_sum_range** (Critical): a SUM, SUMIF(S), SUMPRODUCT, SUBTOTAL, AGGREGATE, or AVERAGE range contains numbers stored as text. SUM skips text, so the total is short; the finding names the cells and the amount missing. It reads typed values, so it works whether or not the file was calculated. Its fix is the same conversion as number_as_text, linked to that change.
- **Dismiss when** the text is a code that only looks numeric (an account or cost center number) and the range was never meant to add it.
- **Dismiss when** the shift is the point (for example a one-month lag) but the label doesn't say so; suggest labeling it.

## Data integrity additions

**period_header_gap** (Warning): period headers skip (Mar → May), repeat (Q2 twice), or go backwards. Check the formulas under the header too.

**mixed_currency** (Warning): one tab holds amounts in two currencies (from number formats or currency codes in labels).
- **Dismiss when** the currencies sit in clearly labeled separate blocks and are converted before any total.

**duplicate_rows** (Warning): exact copies of a record on a data tab.
- **Dismiss when** repeated identical records are real (two identical transactions on one day) and there's no unique ID to tell them apart.

**duplicate_key** (Warning): an ID that is otherwise unique appears more than once.

**outlier_value** (Question): a value far outside its column's normal range (robust z-score over 8). Usually a typo or a unit slip (1,400,000 among salaries near 116,000).

## Financial logic (verified)

**double_counting** (Critical): a total adds both a subtotal and the lines the subtotal already sums. Treat it as real unless the "subtotal" is actually a different measure with a misleading formula.

**growth_wrong_base** (Warning): a growth or change formula divides by the later period (`(new - old) / new`) or computes `old / new - 1`. Only flagged on growth/change rows or %-formatted cells comparing two period columns. Margins are excluded.
- **Dismiss when** the model deliberately uses the later period as base (rare; for example a "share of current" metric) and labels it.

**mixed_units_in_formula** (Warning): a formula adds numbers stored in different units ($K and $M, from labels or tab titles) or currencies, or a cell labeled in one unit takes a number stored in another without converting. Cells whose number format scales the display are left out, since their stored unit is ambiguous.

**inconsistent_assumption** (Warning): the same assumption typed with two values (for example tax rate 25 percent on Inputs, 24 percent on Summary). Only for typed numbers on an inputs tab or with assumption-like labels.

## Questions for the owner (judgment)

These are found by rule but only the owner can say whether they're wrong. Keep the good ones, dismiss the ones the file explains, and add a note when you can see the driver. Never restate them as errors.

**unusual_movement**: a period-over-period (or same-month-last-year) change far outside the row's own typical change, for example headcount up 22 percent in March in a row that otherwise grows 2 percent a month. One-period spikes and dips are reported as the point itself. The text says whether the value is typed, the formula differs from its neighbors, or the move comes from what feeds it; moves explained by a move already flagged upstream aren't repeated.
- **Dismiss when** a label, note or input explains it (a planned hiring wave, a price increase, a one-off).

**sign_flip**: one or two values in a row have the opposite sign to the rest. Growth and % rows are skipped. Warning-level for revenue, headcount, or volume rows.

**unexpected_zero**: an isolated zero between non-zero values.
- **Dismiss when** the period is genuinely zero (a shutdown month, a ramp).

**margin_out_of_range**: a margin outside -100 percent to 100 percent, usually the wrong denominator.

**reviewer_judgment**: your own entries from `judgments.json` - business sense and the variance story.

## Structure

**default_sheet_name** (Suggestion): Sheet1, Copy of..., (2), test, old.

**inputs_outside_inputs_tab** (Suggestion): typed numbers that formulas depend on sit on a calculation or output tab when the model has an inputs tab. Typed forecast lines are common in finance models; suggest moving the assumptions, not the data.

**no_inputs_tab** (Suggestion): assumptions are spread over several tabs with no inputs tab.

## Scan notes

| Note | What to do |
|---|---|
| `values_not_cached` | Saved results are unavailable, so value checks are skipped. Name the skipped checks; do not infer that the file was never calculated, and never say the workbook ties. |
| `scan_capped` | Check `intake.coverage`: if filled cells were not scanned, identify them as incomplete coverage and ask for smaller files. Do not assume that everything beyond the limit is empty formatting. |
| `needs_clarification` | Ask the concrete `intake.questions`, wait, and pass confirmed answers with `ev.scan(context=...)`. Share independent formula findings only as preliminary until resolved. |
| `pivot_unreadable` | Say pivot checks are incomplete for that tab. |
| `excel_version_detected` | Mention which Excel version the file needs. |
| `mixed_working_days` | Point out the different working-days-per-year numbers. |
| `template_scaffold` | Ask whether there's a populated version before auditing a template. |

## What the scan checks

| Area | Verified checks | Questions (judgment) |
|---|---|---|
| Formula integrity | error values (traced to the source), `#REF!`, circular references, links to other files, broken names, inconsistent formulas, typed numbers in formulas, values pasted over formulas, SUMs that stop short, references to blanks, risky lookups, IFERROR masking, functions too new for the readers | - |
| Data integrity | totals that don't equal their periods, totals that don't cross-foot, typed copies that don't tie to the calculation, rows pulling the wrong period from another tab, period headers that skip or repeat, mixed currencies, duplicate rows and IDs, numbers and dates stored as text, stray spaces in keys, blank rows and gaps, Table and pivot coverage, dropdown violations | the same line item calculated two ways; values far outside a column's range |
| Financial logic | double counting (a total that adds a subtotal and its lines), growth rates divided by the wrong period, adding different units or currencies, one assumption with two values | unusual period-over-period and year-over-year movements (judged against the row's own history), isolated sign flips, unexpected zeros, margins outside -100% to 100% |
| Structure and formatting | default or working tab names, inputs living on calculation tabs, no inputs tab, hidden tabs and rows, merged cells, long formulas, formatting against the model's convention (mixed units and decimals, rates in General format, #### columns), conditional-formatting bloat, performance limits | - |

**What it can't do** (say so if asked): no charts or screen layout, no VBA, no real calculation timing, and no recalculation: value checks read the results Excel last saved in the file.

## What gets fixed automatically

- **Formulas:** replace a typed value with the neighboring formula pattern (`confirm`, since it may be an intentional override); extend a SUM that stops short; make an odd formula match its neighbors (`confirm`); move a typed-in number to a labeled input (`confirm`); use a Table's column names (`confirm`). A fix that would point at an empty cell is sent to "Needs you" instead.
- **Values:** convert numbers or dates stored as text. Ambiguous slash dates require the user's date order first; invalid dates stay unresolved. Never label a guessed conversion safe.
- **Formatting and layout:** copy a neighbor's format that follows the model's convention; % format for rates; widen #### columns; freeze header rows; unmerge calculation cells.
- **Tables, highlighting, performance, and lookups:** as listed in each change, with `confirm` where the result can change.

Everything else is "Needs you": double counting, period misalignment, mixed units and currencies, tie-outs, duplicates, `#REF!`, circular references, external links, hidden tabs, pivots, and structural rework. Questions are never planned as changes.
