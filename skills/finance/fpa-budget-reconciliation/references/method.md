---
description: "How the reconciliation computes every figure and flag: the budget walk, period window, currency conversion, roll-up to the plan grain, the commitment split that places each dollar in one bucket, the outlier tests (materiality, relative, robust z against history and across lines, timing, committed past budget), headcount as a stock, and the tie-out proofs. Read it to explain a number or a flag to the user."
last_updated: 2026-11-24
---

# Method

<budget_walk>
For each line at the plan's grain:

- Plan YTD, Actual YTD: the closed months of the plan year (fiscal year start through the last closed period).
- Variance = actual minus plan. Variance % = variance divided by the absolute plan.
- Full-year plan: every month of the plan year.
- Pending: invoices approved but not yet in the GL.
- Open: purchase-order dollars not yet invoiced or posted.
- Committed = actual YTD + pending + open.
- Available = full-year plan minus committed. Negative means the line is committed beyond its budget.

Actuals dated after the last closed period are kept out of year to date and shown on their own (an open month reads as a collapse or a spike). Actuals before the plan year are used only as history for the spike test.
</budget_walk>

<sign_convention>
Variance is always actual minus plan. On a cost line a positive variance is over budget (unfavorable), shown warm; negative is under budget (favorable), shown cool. On a revenue line (named in `rules.revenue`) the colors flip, and pending and open commitments are not applied. Amounts are made expense-positive at load with each source's `sign`, so every downstream figure reads the same way.
</sign_convention>

<currency>
Every row converts at the rate for its own period. When a period has no rate, the latest earlier rate is used and listed as a fallback in the FX sheet and the findings; plan months after the last closed period use the latest available rate (a forecast rate is not invented). A currency with no rate at all is left out of the totals, listed in the tie-out, and raised as an error finding: the report must not be presented as complete until rates are supplied. Open purchase orders are valued at the last closed period's rate.
</currency>

<grain_and_rollup>
Each row's dimensions are walked up the supplied hierarchy until they reach a value the plan uses. A value that never reaches one is unplanned: the row keeps its own value, appears as a line with zero plan, is counted in every total, and is listed on the Unplanned sheet. A missing dimension column becomes "(not coded)". Nothing is dropped silently.
</grain_and_rollup>

<commitments>
See references/data-discovery.md `<double_counting>` for the linkage choice. Per purchase order: consumed = posted (GL lines carrying the PO directly or through its invoice) + pending (its invoices not in the GL). Open = max(ordered minus consumed, 0) while the PO is open; on a closed PO that balance is released instead. Overrun = max(consumed minus ordered, 0). A PO's dollars are split across its lines by ordered amount. The proof `ordered = posted + pending + open + released - overrun` holds for every PO.

Invoices without a PO, or whose PO is not in the file, add to pending on their own line when they are known not to be in the GL.
</commitments>

<materiality>
Two floors, one for year to date and one for the month. The user can set one amount for both (`materiality_amount`). Otherwise the year-to-date floor is 0.5% of the gross plan year to date and the month floor is 1% of the gross plan for the month, each rounded down to two significant figures so it reads as a round number. State both floors in every presentation; ask the user whether they suit the business.
</materiality>

<tests>
Each line is tested in three views, and documents in a fourth.

| Test | View | Fires when |
|---|---|---|
| material | year to date, month | absolute variance at or above the floor |
| relative | year to date, month | absolute variance % at or above 10% (`variance_pct`), or a variance on zero plan |
| cross_section | year to date | the line's size-scaled variance (variance divided by the square root of plan plus actual) has a robust z-score beyond 3.5 against all planned lines |
| history_spike | month | the month's actual has a robust z-score beyond 3.5 against the line's own last 12 closed months (needs 6 or more), unless the plan jumps the same way that month (a planned step) |
| timing | month | the month's variance reverses at least 75% of the prior two months' variance |
| committed | full year | committed exceeds the full-year plan by half the year-to-date floor or more |
| unplanned | year to date | actuals with no plan line, at or above the month floor |
| sign | year to date | a cost line carries a net credit year to date |
| document | purchase orders, invoices | PO overrun, a PO open more than 90 days past its need-by month, an invoice waiting more than 30 days to reach the GL, the same invoice number twice, or the same vendor and amount within 7 days |

The robust z-score is the Iglewicz-Hoaglin modified z: 0.6745 times (value minus median) divided by the median absolute deviation. It is used instead of mean and standard deviation because one large outlier inflates the standard deviation and hides itself. When the median absolute deviation is 0 (most values identical), the score uses the mean absolute deviation instead: (value minus median) divided by 1.2533 times the mean absolute deviation.

**Tiers.** Inspect: material and at least one more test, or unplanned at half the year-to-date floor, or a document issue at or above the month floor, or a duplicate invoice. Watch: material with a variance of at least half the relative threshold but no second test, statistically unusual but below the floor, a likely timing reversal, or a document issue below the floor. Everything else is not flagged. Items are ranked by size against the floor, weighted by the number of tests that fired.

The skill flags where to look and says why in numbers. It never explains the business cause; that is the owner's job, and the Inspect sheet has Owner, Status, and Notes columns for it.
</tests>

<headcount>
Heads are a count at a point in time, not a flow. They are compared at the last closed month only and never summed across months (three months of 100 heads is still 100 heads). A group is flagged when its variance is at least the floor (one head, or 1% of planned heads if larger) and at least 5%. Open requisitions are headcount commitments: a group below plan whose actual plus open requisitions exceeds plan is called out.
</headcount>

<proofs>
Three checks, each shown with both sides and the difference:
1. GL actuals are each counted once: the converted GL total equals year-to-date actuals on every line plus history before the plan year plus activity after the last closed period.
2. Plan is carried in full: converted plan rows inside the plan year equal the full-year plan summed across lines.
3. Every ordered dollar is posted, pending, open, or released (when purchase orders are supplied).

A failed proof is an error finding. Do not present totals until it is explained.
</proofs>

<drill>
`run_reconciliation.py --drill "<line key>" [--period YYYY-MM]` adds the 25 largest GL rows behind one line (the closed months, or one month) to the results, with vendor, description, references, and the source dimension values before roll-up. Use it to show the user what drove a flag; do not paste more than the top rows into chat.
</drill>
