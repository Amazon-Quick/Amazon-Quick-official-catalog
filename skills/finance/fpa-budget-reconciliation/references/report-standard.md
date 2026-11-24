---
description: "What the two deliverables contain and why: the one-page HTML report's layout and design rules, the workbook's sheets and live formulas, how to present results in chat, and the variance handoff contract for other skills."
last_updated: 2026-11-24
---

# Report standard

<one_page_report>
One landscape page a finance leader can read in a minute: the headline metrics first, then the detail. Top to bottom:

1. Title and a one-line context: through which month, reporting currency, plan year, as-of date.
2. Six key performance indicator (KPI) cards: full-year budget; spent to date (share of budget, plan to date, a meter with the year-closed marker); variance to plan to date (signed, colored); pending invoices; open purchase orders; remaining balance (share of budget left against share of year left, or "Over-committed" when negative). A source the user did not supply reads "Not supplied", never $0.
3. The full-year budget bar: spent, pending, open POs, and remaining in one bar, hatched past the budget when over-committed, with the year-closed marker and a one-line caption.
4. The headline: one sentence stating the variance, what is pending or on order, what is still available, and how many items need inspection. It is a finding, not a label.
5. Budget by the first grain dimension (for example department): one row per group with full-year budget, plan and actual to date, variance and variance %, pending, open POs, remaining, a budget-used bar (spent plus committed, with the year-closed marker), and the inspect flag ids. Each group expands to its lines ("Show every line" expands all, and printing expands all). A single-dimension grain shows the lines directly.
6. Needs inspection: the ranked items, one row per line (several tests on one line are merged), each with its id, the amount, the kinds of test that fired, and the first sentence of the reason. Beside it, variance to plan by month: bars above (over) and below (under) a zero line for each closed month; open months show their plan only.
7. Largest variances year to date (diverging bars), headcount at the last closed month (actual bar, open requisitions as a light extension, plan as a tick), and "Data checks" (tie-out, PO linkage confidence, currency, coverage, accruals without PO references, activity held out of the open month).
8. Footnote: the sign convention, the materiality floors, and the workbook's file name.

Design rules (they keep the page legible and honest):
- One accent pair carries meaning: warm for over plan or unfavorable, cool for under plan or favorable. Everything else is ink and grays. Never color for decoration.
- Numbers are tabular; amounts are compact ($1.2M, $48K) with the sign shown on variances.
- No gauges, no 3D, no gradients, no emoji, no card grids. Charts are inline SVG and the file has no external requests, so it opens offline and prints on one page.
- Say "not supplied" for a source the user did not give, never $0.
</one_page_report>

<workbook>
| Sheet | Contents |
|---|---|
| Summary | The headline, totals as formulas over the Lines total row, flag counts, the tie-out result, a sheet guide |
| Lines | One row per line: plan, actual, and variance year to date and for the month, full-year plan, pending, open, committed, available, tier, flag ids. Variance, committed, and available are live formulas |
| Inspect | Every flag with its reason, tests, and reference, plus blank Owner, Status (Open, Explained, Fix needed, Done), and Notes for the team |
| Monthly, Trend | Plan and actual per line and month; Trend totals them with SUMIFS |
| Commitments, Invoices | Where each ordered and invoiced dollar sits, with a per-PO check column that must read 0 |
| Unplanned | Actuals with no plan line |
| Headcount | Plan and actual heads per group and month, open requisitions |
| Tie-out | The proofs, the source walk, and every finding |
| FX rates | Every rate used and whether it was the period's own |
| Method | Grain, window, sign convention, thresholds, linkage, definitions |

Formulas carry cached values computed from the same rounded inputs, so the file reads correctly in previews and recalculates to the same figures in a spreadsheet app.
</workbook>

<chat_presentation>
Present the results once, after the files are written, in this order and keep it short:
1. The headline sentence (the same sentence and item count as the report).
2. The top inspect items as a table: id, line, amount, why (one line each), at most 8.
3. What limits or shapes the figures: an error finding, a failed proof, a fallback rate, low linkage confidence, unplanned dollars above the floor, activity held out after the last closed month, and whether the results tie to the user's control total.
4. The materiality floors used.
5. The two file paths, and one offer: drill into an item, change a threshold, or re-run with corrected data.
Use labels and aggregates only. Never paste rows of the user's data into chat beyond a short drill list they asked for.
</chat_presentation>

<handoff>
For a commentary or narrative skill, hand over the Lines sheet (or results.json `lines`) in the variance contract shape: one row per line and period with line, period, actual, plan, variance, and variance percent, plus the sign convention sentence and which columns were treated as actual and as plan. Do not draft explanations in this skill.
</handoff>
