"""
description: The workbook scan's check catalog: group, severity and standard fix per check, report areas, and Excel function versions.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

# The checks: group, severity, and the standard fix.
CHECKS = {
    "error_value": (
        "Errors",
        "critical",
        "Trace to the first cell in the chain showing the error and fix that one; the rest clear with it.",
    ),
    "ref_in_formula": (
        "Errors",
        "critical",
        "Re-point the reference to the intended cell (look at the same formula in neighboring cells), or delete the line if retired.",
    ),
    "circular_reference": (
        "Errors",
        "critical",
        "Break the loop: one of these cells should use an input or a prior-period value instead of the other.",
    ),
    "external_link": (
        "Errors",
        "critical",
        "Paste the linked number in as a labeled input, or confirm the other file is always available at that path.",
    ),
    "broken_named_range": (
        "Errors",
        "critical",
        "Delete the name (Formulas > Name Manager) or point it at the intended range.",
    ),
    "hardcoded_number_in_formula": (
        "Hardcodes & consistency",
        "warning",
        "Move the number to a labeled input cell and reference it.",
    ),
    "value_in_formula_row": (
        "Hardcodes & consistency",
        "warning",
        "Restore the formula its neighbors use; a typed number won't update when inputs change.",
    ),
    "inconsistent_formula": (
        "Hardcodes & consistency",
        "warning",
        "Make it match its neighbors, or label why this period is different.",
    ),
    "sum_range_gap": (
        "Hardcodes & consistency",
        "warning",
        "Extend the SUM to cover every line in the block.",
    ),
    "ref_to_empty_cell": (
        "Hardcodes & consistency",
        "warning",
        "Fill in the referenced cell or point the formula elsewhere; blanks count as zero silently.",
    ),
    "volatile_function": (
        "Risk",
        "warning",
        "Replace with a direct reference or INDEX/XLOOKUP; OFFSET and INDIRECT hide what they point at.",
    ),
    "long_formula": (
        "Risk",
        "info",
        "Split into helper rows or use a lookup table so each step can be checked.",
    ),
    "hidden_sheet": (
        "Risk",
        "warning",
        "Unhide and label it, or move what it feeds into a visible inputs tab.",
    ),
    "hidden_rows_in_block": (
        "Risk",
        "info",
        "Unhide, or group (Data > Group) so the hiding is visible.",
    ),
    "data_past_table_edge": (
        "Tables",
        "warning",
        "Resize the Table (Table Design > Resize) to include these rows.",
    ),
    "generic_table_header": ("Tables", "info", "Give the column a real name."),
    "fixed_range_over_table": (
        "Tables",
        "warning",
        "Use the Table column by name, for example Orders[Amount], so it grows with the data.",
    ),
    "number_as_text": (
        "Cell formatting",
        "warning",
        "Convert to a number (Data > Text to Columns, or multiply by 1); SUM skips text.",
    ),
    "date_as_text": (
        "Cell formatting",
        "warning",
        "Convert to a real date so sorting and date math work.",
    ),
    "percent_general_format": ("Cell formatting", "info", "Apply a percent format."),
    "mixed_decimals": (
        "Cell formatting",
        "info",
        "Use the same number of decimal places as the rest of the column/row.",
    ),
    "mixed_units": (
        "Cell formatting",
        "warning",
        "Use the same unit scale as the rest of the tab, or label the exception clearly.",
    ),
    "input_style_break": (
        "Cell formatting",
        "warning",
        "Style it like the model's other inputs so people can see it is typed in.",
    ),
    "formula_styled_as_input": (
        "Cell formatting",
        "warning",
        "Restyle as a formula; right now it looks like a number someone can overwrite.",
    ),
    "link_style_break": (
        "Cell formatting",
        "info",
        "Style it like the model's other cross-tab formulas.",
    ),
    "total_style_break": (
        "Cell formatting",
        "info",
        "Style it like the model's other total rows.",
    ),
    "merged_cells_in_calc": (
        "Cell formatting",
        "info",
        "Unmerge; use Center Across Selection if the look matters. Merges break copy-across and sorting.",
    ),
    "no_freeze_panes": (
        "Cell formatting",
        "info",
        "Freeze the header row and label column (View > Freeze Panes).",
    ),
    "column_too_narrow": (
        "Cell formatting",
        "info",
        "Widen the column; the number shows as ####.",
    ),
    "cf_fragmented": (
        "Conditional formatting & dropdowns",
        "warning",
        "Delete the copies and apply one rule to the whole range (Home > Conditional Formatting > Manage Rules).",
    ),
    "cf_broken_ref": (
        "Conditional formatting & dropdowns",
        "warning",
        "Fix or delete the rule; it points at a deleted cell.",
    ),
    "cf_whole_column": (
        "Conditional formatting & dropdowns",
        "info",
        "Limit the rule to the rows in use; whole-column rules slow the file.",
    ),
    "dv_broken_source": (
        "Conditional formatting & dropdowns",
        "warning",
        "Point the dropdown at a valid list.",
    ),
    "dv_violation": (
        "Conditional formatting & dropdowns",
        "warning",
        "Change the value to an allowed choice, or add it to the list.",
    ),
    "pivot_source_short": (
        "Pivots",
        "warning",
        "Change Data Source to cover all rows, ideally a Table so it grows.",
    ),
    "pivot_fixed_range": (
        "Pivots",
        "info",
        "Base the pivot on a Table instead of a typed range.",
    ),
    "pivot_stale_cache": (
        "Pivots",
        "warning",
        "Refresh the pivot (PivotTable Analyze > Refresh), and consider 'Refresh data when opening the file'.",
    ),
    "formula_reads_pivot_by_position": (
        "Pivots",
        "warning",
        "Use GETPIVOTDATA, or SUMIFS on the source data; pivot cells move when the pivot reshapes.",
    ),
    "pivot_missing_source": (
        "Pivots",
        "critical",
        "Re-point the pivot to existing data.",
    ),
    "vlookup_approx": (
        "Formula patterns",
        "warning",
        "Add FALSE as the fourth argument for an exact match, unless the lookup list is sorted and a range match is intended.",
    ),
    "lookup_hardcoded_col": (
        "Formula patterns",
        "info",
        "Use a lookup that names the return column (XLOOKUP or INDEX/MATCH) so inserting a column can't shift the result.",
    ),
    "lookup_style_inconsistent": (
        "Formula patterns",
        "info",
        "Write it the way the rest of the model does its lookups.",
    ),
    "iferror_masking": (
        "Formula patterns",
        "info",
        "Guard only the expected error, such as a zero denominator, so real errors still show.",
    ),
    "redundant_formula": (
        "Formula patterns",
        "info",
        "Simplify the formula; the result is the same.",
    ),
    "compat_function": (
        "Formula patterns",
        "warning",
        "Rewrite with functions every reader's Excel has, or confirm everyone is on a newer version.",
    ),
    "calc_manual": (
        "Performance",
        "warning",
        "Set calculation to Automatic (Formulas > Calculation Options), unless the model is deliberately manual for speed.",
    ),
    "iterative_calc_on": (
        "Performance",
        "warning",
        "Turn off iterative calculation unless a loop is intended; with it on, accidental circular references go unnoticed.",
    ),
    "inflated_used_range": (
        "Performance",
        "warning",
        "Delete the empty formatted rows/columns past the data and save; the file shrinks and opens faster.",
    ),
    "excess_cell_styles": (
        "Performance",
        "info",
        "Remove unused cell styles; thousands of formats bloat the file and eventually trigger 'too many formats'.",
    ),
    "whole_column_array": (
        "Performance",
        "warning",
        "Limit the ranges to the rows in use, or use a Table column; array math over whole columns is slow.",
    ),
    "sumproduct_conditional": (
        "Performance",
        "info",
        "Use SUMIFS/COUNTIFS, which are usually much faster; criteria with wildcards or comparison operators match differently, so check them.",
    ),
    "volatile_load": (
        "Performance",
        "warning",
        "Put TODAY()/NOW() in one cell and reference it; every volatile cell recalculates on every edit.",
    ),
    "unused_named_range": (
        "Performance",
        "info",
        "Delete names nothing uses (Formulas > Name Manager).",
    ),
    "blank_rows_in_data": (
        "Data hygiene",
        "info",
        "Delete the blank rows; they break filters, sorting, pivots and Ctrl+arrow selection.",
    ),
    "empty_cell_gap": (
        "Data hygiene",
        "info",
        "Fill in the missing value, or enter 0 if it is truly zero.",
    ),
    "lookup_key_spaces": (
        "Data hygiene",
        "warning",
        "Remove the extra spaces (TRIM); 'East ' does not match 'East' in lookups and SUMIFS.",
    ),
    # reconciliation
    "period_total_mismatch": (
        "Reconciliation",
        "critical",
        "Make the total a SUM of its periods, or correct the typed figure and note where it came from.",
    ),
    "crossfoot_mismatch": (
        "Reconciliation",
        "critical",
        "Find the line whose total isn't the sum of its periods (or the SUM whose range differs) and fix it so both directions agree.",
    ),
    "tie_out_mismatch": (
        "Reconciliation",
        "warning",
        "Link the cell to the calculated value instead of typing it, or explain the difference in a note.",
    ),
    "same_metric_differs": (
        "Reconciliation",
        "info",
        "Link one to the other if they're the same measure; otherwise rename one so the difference is clear.",
    ),
    "header_formula_mismatch": (
        "Reconciliation",
        "critical",
        "Correct the header so it names the period its formulas actually read, or repoint the formulas if the header is right; check the totals that use this column.",
    ),
    "text_in_sum_range": (
        "Reconciliation",
        "critical",
        "Convert the text to numbers (Data > Text to Columns, or multiply by 1); the total is short by the amount shown.",
    ),
    "period_misaligned_link": (
        "Reconciliation",
        "warning",
        "Point each period at the matching period on the source tab (check the first column of the row).",
    ),
    # data integrity
    "period_header_gap": (
        "Data hygiene",
        "warning",
        "Fix the headers so every period appears once, in order; check the formulas under the bad header too.",
    ),
    "mixed_currency": (
        "Data hygiene",
        "warning",
        "Convert to one reporting currency with a labeled FX rate, or keep the currencies in separate, labeled blocks.",
    ),
    "duplicate_rows": (
        "Data hygiene",
        "warning",
        "Remove the duplicate rows, or add a column that explains why the same record appears twice.",
    ),
    "duplicate_key": (
        "Data hygiene",
        "warning",
        "Remove or merge the duplicate entries; totals and lookups count them twice or pick the first.",
    ),
    "outlier_value": (
        "Data hygiene",
        "info",
        "Check the value against the source; correct it if it's a typo or a unit slip.",
    ),
    # financial logic
    "double_counting": (
        "Financial logic",
        "critical",
        "Sum either the subtotals or the lines inside them, not both.",
    ),
    "growth_wrong_base": (
        "Financial logic",
        "warning",
        "Divide the change by the earlier period: =(new - old) / old.",
    ),
    "mixed_units_in_formula": (
        "Financial logic",
        "warning",
        "Convert to one unit (for example, divide by 1,000 for thousands) before adding, and label the result's unit.",
    ),
    "inconsistent_assumption": (
        "Financial logic",
        "warning",
        "Keep one copy of the assumption on the inputs tab and link every other place to it.",
    ),
    "unusual_movement": (
        "Financial logic",
        "warning",
        "Confirm the movement with the model owner and document the driver next to the assumption.",
    ),
    "sign_flip": (
        "Financial logic",
        "info",
        "Confirm the sign; if it's a reversal or true-up, label it.",
    ),
    "unexpected_zero": (
        "Financial logic",
        "info",
        "Fill in the missing value or link, or note why the period is zero.",
    ),
    "margin_out_of_range": (
        "Financial logic",
        "warning",
        "Check the margin's numerator and denominator.",
    ),
    # structure
    "default_sheet_name": (
        "Structure",
        "info",
        "Rename the tab to say what it holds; delete it if it's a leftover.",
    ),
    "inputs_outside_inputs_tab": (
        "Structure",
        "info",
        "Move the typed assumptions to the inputs tab and link to them, so every driver is in one place.",
    ),
    "no_inputs_tab": (
        "Structure",
        "info",
        "Collect the assumptions on one labeled inputs tab and link the model to it.",
    ),
}

# Function -> first Excel version that has it. "365" = Microsoft 365 only.
# Found by rule, but only a person can say whether they're wrong: worded as questions,
# never critical, never fixed automatically.
JUDGMENT_CHECKS = {
    "same_metric_differs",
    "outlier_value",
    "unusual_movement",
    "sign_flip",
    "unexpected_zero",
    "margin_out_of_range",
}
AREAS = {
    "formula": "Formula integrity",
    "data": "Data integrity",
    "logic": "Financial logic",
    "structure": "Structure & formatting",
}
AREA_OF_GROUP = {
    "Errors": "formula",
    "Hardcodes & consistency": "formula",
    "Formula patterns": "formula",
    "Risk": "formula",
    "Tables": "data",
    "Pivots": "data",
    "Data hygiene": "data",
    "Reconciliation": "data",
    "Financial logic": "logic",
    "Cell formatting": "structure",
    "Conditional formatting & dropdowns": "structure",
    "Performance": "structure",
    "Structure": "structure",
}
AREA_OF_CHECK = {
    "hidden_sheet": "structure",
    "hidden_rows_in_block": "structure",
    "long_formula": "structure",
    "number_as_text": "data",
    "date_as_text": "data",
    "text_in_sum_range": "data",
    "dv_violation": "data",
    "dv_broken_source": "data",
}


def area_of(check, group):
    return AREA_OF_CHECK.get(check) or AREA_OF_GROUP.get(group, "formula")


FUNCTION_VERSION = {
    **dict.fromkeys(
        ("IFS", "MAXIFS", "MINIFS", "SWITCH", "CONCAT", "TEXTJOIN"), "2019"
    ),
    **dict.fromkeys(
        (
            "XLOOKUP",
            "XMATCH",
            "LET",
            "FILTER",
            "SORT",
            "SORTBY",
            "UNIQUE",
            "SEQUENCE",
            "RANDARRAY",
        ),
        "2021",
    ),
    **dict.fromkeys(
        (
            "LAMBDA",
            "TEXTSPLIT",
            "TEXTBEFORE",
            "TEXTAFTER",
            "VSTACK",
            "HSTACK",
            "TAKE",
            "DROP",
            "CHOOSECOLS",
            "CHOOSEROWS",
            "TOCOL",
            "TOROW",
            "WRAPROWS",
            "WRAPCOLS",
            "EXPAND",
            "MAP",
            "REDUCE",
            "SCAN",
            "BYROW",
            "BYCOL",
            "MAKEARRAY",
            "GROUPBY",
            "PIVOTBY",
            "REGEXTEST",
            "REGEXEXTRACT",
            "REGEXREPLACE",
            "IMAGE",
        ),
        "365",
    ),
}
VERSION_ORDER = ["2016", "2019", "2021", "365"]
TARGETS = {
    "auto": None,
    "365": "365",
    "2021": "2021",
    "2019": "2019",
    "2016": "2016",
    "compatible": "2016",
}
SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}
