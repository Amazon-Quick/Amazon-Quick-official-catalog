---
description: "The sheets in the optional Excel workbook and what each holds, and which cells are live formulas. Read in Workflow - Review Series step 9 when the user asks for the workbook."
last_updated: 2026-11-24
---
# The Excel workbook

The Excel workbook is written only when the user asks for it (Rule 12): for tracing figures,
notes, and sign-off. Sheets for an analysis that was not run are left out. Gaps, gap %, materiality, and the
trend comparisons are live formulas on the Data sheet. Expected values and scores are stored results of the
scripts, so editing the data does not re-run detection. Say so if the user asks to audit it.

| Sheet | What it holds |
|---|---|
| Summary | What was read, live counts, the largest events and the largest movers, and what to keep in mind |
| Anomalies | One row per event: actual, expected, gap, gap %, total gap over the event, type, outlier test, **Material?** against the thresholds in the blue cells, what it looks like, what to check, and blank columns for explanation, recurring or not, owner, reviewer, and date |
| Trends | One row per line: period on period, year on year, recent periods, year to date, last twelve months, compound growth, trend, direction, change in trend, level shifts, seasonal pattern, what was set aside |
| Data checks | Missing periods, zeros that look like blanks, reversed signs, unit slips, repeated values, duplicate lines |
| Charts | Actual against expected with unusual periods marked, as Excel charts. The dashboard is the interactive view |
| Data, Expected, Scores | The history as read, the expected value for every period, and a heat map of how unusual each period is |
| Method | How to read it, the settings, each line's source and treatment, the limits |
