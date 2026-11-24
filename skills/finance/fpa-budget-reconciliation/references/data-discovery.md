---
description: "The discovery interview: how to find where a user's plan, actuals, purchase orders, invoices, exchange rates, and headcount live in any company's systems, the questions that decide how dollars are counted once, and how to confirm the data with a control total before reconciling."
last_updated: 2026-11-24
---

# Data discovery

<purpose>
Every company stores budget and spend differently. The skill cannot assume an enterprise resource planning (ERP) system, a chart of accounts, or a file layout, so it learns them from the user before it reconciles anything. This file is the interview: what to ask, in what order, what each answer changes in the spec, and how to prove the data is read correctly. Ask in plain business words, never in spec field names.
</purpose>

<sources>
The skill needs two sources and can use four more. Ask only for what the user has.

| Source | Required | What it is in most systems | What it adds |
|---|---|---|---|
| Plan | yes | Budget, forecast, operating plan, or outlook export; often one column per month | The yardstick and the grain |
| Actuals | yes | GL detail, journal lines, or a trial balance by month and line | What has been spent |
| Purchase orders | no | Open PO report, commitments report, PO lines with ordered and received amounts | Money promised but not yet spent |
| Invoices | no | Accounts payable (AP) invoice register, AP aging, invoices awaiting approval or posting | Bills received but not yet in the GL |
| Exchange rates | when more than one currency | Monthly average or month-end rate table from treasury or the ERP | Conversion to one reporting currency |
| Headcount | no | Planned and actual heads by month and team, with open requisitions | People, which are a count and never a sum |

Where the data can come from, in order of preference:
1. Files the user attaches (.xlsx, .xlsm, .csv). Ask for .xlsb and .xls to be saved as .xlsx.
2. A system the user exports from (an ERP, a planning tool, a web-based ledger). Ask the user to export the report and attach it, and tell them which report to look for (for example "the open PO report, filtered to your departments, with ordered, received, and invoiced amounts").
</sources>

<interview>
Run find_data_profile.py on every file first. It finds header rows, types every column, guesses each sheet's role, and drafts a spec. Then confirm in at most two messages, using its findings as the defaults. Group the questions; do not ask one at a time.

**Message 1: shape and scope**
1. Which file is the plan, and which version or scenario in it is the one to reconcile against? (The profiler flags a version or scenario column; filter to one, or numbers double.)
2. What identifies a plan line? Offer the dimension columns the profiler found, and recommend the lowest level the plan is actually set at (see <grain>).
3. What is the last closed month? Actuals after it are shown separately and never counted as year to date.
4. When does the fiscal year start, and how are fiscal periods labeled (for example FY27 P03)?
5. Which currency should the report be in? If more than one currency appears, ask for monthly rates and whether they are units of the reporting currency per one foreign unit or the other way round.
6. If the profiler asks about numeric dates: are dates written day/month/year or month/day/year? Offer its suggested default when it gives one. A date such as 07/06/2026 reads either way, so never guess; if files use different orders, ask for ISO dates (2026-06-07).

**Message 2: counting each dollar once** (only if purchase orders or invoices were supplied)
7. When an invoice is posted to the GL, does the GL line carry the PO number, the invoice number, or neither? This decides the linkage method (see <double_counting>).
8. Does the PO report have its own open or remaining column, and is it net of invoices or net of posted spend?
9. Are goods-received accruals booked to the GL before the invoice arrives? If yes, do those accrual lines carry the PO number?
10. Which PO statuses mean the PO is finished (closed, cancelled, complete)? Their unspent balance is released, not open.
11. Which invoice statuses mean the invoice is already in the GL (posted, paid)?

**Always confirm the sign.** Ask whether a positive amount is an expense in each file. GL exports differ: some show debits positive, some show credits positive, some show parentheses or trailing minus signs. The profiler reports the share of negative values per amount column; a cost GL that is mostly negative is a sign flip (`sign: -1`).
</interview>

<grain>
The grain is the lowest level of detail that can be attributed back to the plan. Pick it from the plan, never from the actuals: if the plan is set by department and account, the grain is department and account even when the GL has project and vendor too.

When actuals are more detailed than the plan on a dimension (plan on a summary account, actuals on its sub-accounts), ask for the hierarchy that rolls the detail up: a child-to-parent table, or a mapping the user states. The engine walks each value up the tree until it reaches a value the plan uses. Anything that never reaches a plan value is unplanned: it stays in every total and is listed, never dropped.

Signs the grain is wrong: most actual dollars land as unplanned (grain too fine, or a missing hierarchy); or one plan line absorbs very different spend (grain too coarse, ask whether a finer plan exists).
</grain>

<double_counting>
A dollar of spend can appear three times: on a PO, on an invoice, and as a GL line. The engine places every ordered dollar in one bucket: posted, pending, open, or released. How it can prove that depends on what links the files.

| What links them | Linkage | How open is computed | Confidence |
|---|---|---|---|
| GL lines carry the PO number, or the invoice number and the invoice carries the PO | `by_reference` | ordered minus GL posted against the PO minus invoices not yet in the GL | high |
| The PO report has a trusted open or remaining column | `open_column` | taken from the report (state `open_basis`) | medium |
| Nothing links them | `ordered_less_invoiced` | ordered minus invoiced | low; say so in the report |

`auto` picks by_reference when at least a fifth of POs match GL references, else open_column when the PO file has an open column, else ordered_less_invoiced.

Rules that keep the count honest:
- An invoice whose posting state cannot be told (no status, no GL reference) is not added as pending. Adding it might count it twice; leaving it out is reported as a finding.
- Accruals without a PO reference are flagged: if they accrue receipts on open POs, the PO is counted again as open. Ask the user to confirm.
- Consumption beyond the order is an overrun: shown and flagged, never subtracted from another PO.
- Pending invoices and open POs are cost commitments. They do not apply to revenue lines.
</double_counting>

<control_total>
Before presenting results, tie one number to something the user already trusts. Ask: "What is the total spend for the last closed month in your own system?" (a trial balance, a profit and loss (P&L) statement, a dashboard). Compare it with the actual for that month on the Trend sheet. If they differ, the usual causes, in order: a version filter missing (plan doubled), the sign, an account range that should be excluded (balance sheet, revenue, intercompany, allocations), a currency without a rate, or GL dated after the last closed month. Fix the spec and re-run; do not explain a gap away.
</control_total>

<spec_notes>
- Column mapping is `canonical: "Source header"`. Canonical names: the grain names, `period`, `amount` (or `debit` and `credit`), `currency`, `reference` (PO on a GL line), `invoice_ref`, `vendor`, `description`, `entry_type`; for POs `po_number`, `po_line`, `ordered`, `received`, `invoiced`, `open_amount`, `status`, `need_by`, `period` (order date); for invoices `invoice_number`, `po_number`, `amount`, `status`, `invoice_date`, `posted`; for rates `currency`, `period`, `rate`; for headcount `period`, `plan_heads`, `actual_heads`, `open_reqs`.
- A wide plan (one column per month) uses `layout: "wide"` and lists the month headers in `period_columns`.
- Exclusions (balance-sheet accounts, intercompany, allocations, statistical accounts) are `filters` with `action: "exclude"`. Ask before excluding anything; list every exclusion in the report's Method sheet.
- Revenue lines (if any) are named in `rules.revenue` so their favorable direction flips and commitments do not apply to them.
</spec_notes>
