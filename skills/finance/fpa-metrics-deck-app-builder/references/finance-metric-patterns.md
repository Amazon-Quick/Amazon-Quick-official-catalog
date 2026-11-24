---
description: "Finance-specific checks for defining metrics (fiscal calendar, foreign exchange, ratios, sign conventions, tie-out tolerance) and for explaining reconciliation misses. Read in Workflow - Build Catalog steps 7 and 9."
last_updated: 2026-11-24
---
# Finance metric patterns and checks

Use these while defining metrics (Build Catalog step 7) and when explaining reconciliation misses (Build Catalog step 9).

## Checks for every metric

1. **Scenario alignment.** Name the scenario the metric is compared against (budget, the latest forecast, or prior year) and the column that selects it. When a new forecast is loaded, decide whether the deck switches to it.
2. **Fiscal calendar.** State whether periods are fiscal or calendar, the pattern (calendar months, 4-4-5, 4-5-4, or 5-4-4), the week start day, and how a 53-week year is handled.
3. **Foreign exchange (FX) and currency.** State the reporting currency, the rate source, and the rate date (daily, month-end, or budget rate). If the deck shows constant currency, define it: current-period amounts converted at the comparison period's rates, or at budget rates.
4. **Sign convention.** Say whether a positive variance is favorable. For costs it's usually the reverse of revenue. Use one convention per deck and show it in the app's legend.
5. **Aggregation.** Sums roll up, but ratios and averages don't. Define a ratio as a ratio of sums at the level shown, and never average percentages across segments or periods.
6. **Time basis.** Define month, quarter to date (QTD), year to date (YTD), or trailing 12 months, and the close cut-off. Say whether the current period is shown before it closes and, if so, label it preliminary.
7. **Exclusions.** List what is filtered out (intercompany, one-time items, specific entities or cost centers), each with its reason and owner.
8. **Source of truth.** Name the system of record and the tolerance the metric must tie to, in absolute terms or in basis points (bps).
9. **Denominators.** When a denominator can be zero or negative (a budget line, a prior-year loss), divide by its absolute value, and say what the metric shows when the denominator is 0.

## Common finance deck metrics and how to define them

| Pattern | Definition shape | Watch out for |
|---------|------------------|---------------|
| Actuals compared to budget | `actual - budget`, and `(actual - budget) / abs(budget)` | The scenario version, and how budget is phased by month |
| Variance in bps | `(metric_a - metric_b) * 10,000` for ratios | Mixing percentage points and percent change |
| Year-over-year (YoY) growth | `(this period - same period last year) / abs(same period last year)` | Fiscal or calendar alignment, and the 53-week year |
| Run rate | the period amount times the periods per year | Seasonality. Label it as run rate, not forecast |
| Attainment | `actual / target` | The target's timing (full-year or to-date phased) |
| Mix | the segment amount over the total amount | The total must use the same filters as the segments |
| Bridge (walk) | a start value, plus driver deltas, equals the end value | The drivers must sum exactly to the total change. Add an "other" line and keep it small |
| Margin % | `SUM(gross profit) / SUM(revenue)` | A ratio of sums, not an average of margins |
| Unit economics | the amount divided by units | Units and amounts must come from the same grain |
| Operating expenses (opex) per employee | `SUM(opex) / average headcount` | Average headcount over the period, not the period-end count |

## When a number doesn't reconcile

Check every cause below, and record each one that contributes to the gap.

1. The calendar: fiscal or calendar, the period pattern, and the cut-off date.
2. The grain: duplicate rows from a join. Check the row counts at the dataset's grain.
3. The filters: an exclusion applied in the deck but not in the dataset, or the reverse.
4. The scenario version, or the FX rate date.
5. Timing: a late close adjustment, or a refresh that ran before the final load.
6. Rounding: the deck shows rounded components that don't add up to the rounded total.

Record each cause in `04-reconciliation.md`. Repeated causes belong in the metric's definition, so the next refresh doesn't hit them again.
