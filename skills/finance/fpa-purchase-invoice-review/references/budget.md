---
description: "Module 2 budget fit: headroom after actuals and open commitments, grain matching, pooled lines, and period handling. Read when the budget module runs."
last_updated: 2026-11-24
---
# Module 2: Budget fit

Goal: say whether the request fits the plan at the grain and period the business controls, after money already spent and already committed.

Arguments (pass them as a list to `pir_run`, for example `pir_run(["budget", ...])`; add `--input <saved message>` to use a pasted message): `budget --budget B.csv --actuals A.csv --commitments C.csv --requests R.csv --grain <profile grain> --fiscal-start-month <m> --as-of <date> [--stale-days 90] [--commit-statuses open]`

## Formula
`headroom = budget - actuals - open commitments - earlier requests in this batch - request`
- Computed per fiscal quarter and per fiscal year the request touches, at the profile grain.
- Open commitment = PO amount - invoiced to date (the invoiced part is already in actuals), and never below 0: a PO invoiced above its value is listed under `over_invoiced_commitments`, so confirm the overage is in actuals. Only statuses named in `--commit-statuses` count; others are listed as excluded.
- Every planning source (budget, forecast, top-down allocation) goes in one file with a `source` column. Effective headroom = the LOWEST across sources. Never add sources together. A source with no row for the line counts as 0 for it. More than 10 distinct sources comes back as a question about the source column.
- Batch: requests on the same line are taken in ID order; a request that fits alone but breaks with earlier ones says so.

## Script rules
| Rule | Hit when | Severity |
|---|---|---|
| BUD-1 unbudgeted | no budget row at the grain in any source | CONDITION (question for the budget owner) |
| BUD-2 does not fit, specific line | lowest headroom < 0 and the line is not pooled | HOLD |
| BUD-2 does not fit, pooled line | lowest headroom < 0 and the budget row is marked pooled (catch-all / discretionary) | CONDITION |
| BUD-3 stale commitment | open PO on the same line, need-by older than stale days, nothing received | INFO - may be released, confirm with the buyer |

Not checked when: no budget table is supplied (BUD-1..3 report NOT RUN, never BUD-1), or a period cannot be read (for example `Q4` with no year): that row is listed under `unreadable_periods` and the affected request's BUD-1..2 report NOT RUN. Periods are read as `YYYY-MM`, `YYYY-MM-DD`, `MM/DD/YYYY`, `Mon-YYYY` or a quarter label such as `2026-Q4` (taken as a fiscal quarter).

## Judgment rules
- A year that fits never clears a quarter that breaks. Name the quarter and the $.
- Before calling a shortfall, confirm you have every planning source the user keeps (current plan, latest forecast, prior-phase project that funds this phase). Ask "Which plan line funds this?" when the answer is not in the data.
- Say plainly whether the shortfall sits in a pooled catch-all line or in the project's own line. A pooled shortfall means the owner must choose what gives way; a project shortfall means the project needs more budget.
- Phasing: phased amounts must sum to the request; a line phased into a closed period is a finding.
- Stale commitments can make room; list them with $ and which breaking request they could cover. Release is the buyer's and owner's call.
- Never write "approved" or "rejected"; write "fits", "does not fit by $X in FY-Qn".

## Show
Headroom table from `headroom_table`: source, key, bucket, budget, actuals, open commitments, earlier requests, request, headroom after.
