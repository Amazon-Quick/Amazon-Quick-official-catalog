---
description: "The finance profile fields (ERP, coding style, budget grain, approval tiers, thresholds, tolerances, justification template), their defaults, and the first-run rules for asking. Read at step 7 of the Review Items workflow."
last_updated: 2026-11-24
---
# Finance profile

Kept in one JSON file per business, at a path the user chooses (for example `pir_profile.json` in their output folder). Read at step 7 of the Review Items workflow, and written back only to that file when the user confirms new values. Only these fields are saved; never item data, amounts, or people.

Fields marked **none, ask** have no built-in assumption. The check that needs them will report NOT RUN until the user provides a value. This is intentional: approval tiers, quote policy, capex thresholds, materiality, and invoice tolerance vary enough between organizations that a wrong default is worse than no default.

| Field | What it holds | Needed by | Default if unknown |
|---|---|---|---|
| erp | System holding the GL (kind is enough: large ERP, mid-market ERP, small-business accounting package) | system mapping | ASSUMPTION: unknown - generic field names |
| purchasing_tool | Tool that raises requisitions/POs | system mapping | ASSUMPTION: same as erp |
| coa_style | How expense, asset (capex), and prepaid accounts are told apart | coding | ASSUMPTION: account type column supplied with the data |
| grain | Budget grain: dimensions and period (cost center x account x month; project x quarter) | budget | ASSUMPTION: cost_center,account; monthly |
| budget_source | Every planning source to check and which is of record | budget | ASSUMPTION: the budget file supplied |
| approval_matrix | $ tiers and who approves each | approval | **none, ask** |
| quote_policy | $ above which competitive quotes are needed, how many; sole-source rule | price, approval | **none, ask** |
| capex_threshold | Unit cost and useful life that make an item capital | coding | **none, ask** |
| fiscal_calendar | First month of the fiscal year; closed periods | budget, invoice | ASSUMPTION: January; none closed |
| currency | Reporting currency | all | ASSUMPTION: USD |
| materiality | $ below which a finding is noted under INFO, not raised | all | **none, ask** |
| invoice_tolerance | 3-way match tolerance for price (qty tolerance is assumed exact) | invoice | **none, ask** |
| justification_template | The org's required justification elements (for example WHAT,HOW,WHY,WHO,WHERE,CADENCE,BUDGET); see `references/justification-template.md` for guidance | justification | **none, ask on first run** |
| evidence_locations | Where line items, coding, budget, quotes, contracts, receipts, and prior POs live | justification, all | **none, ask on first gap** |

## System kinds
The `erp` and `purchasing_tool` values pick a mapping file in `references/systems/`: a large ERP with a segmented account string (`large-erp-segmented-account.md`), a large ERP with account assignment categories (`large-erp-account-assignment.md`), a cloud procure-to-pay suite (`cloud-procurement-suite.md`), or a small-business accounting package (`small-business-accounting.md`). Ask which fits when the profile names none of them.

## First-run rules
- Ask only for fields the requested modules need (`pir_run(["profile", "--modules", ...])` lists them), at most 3 questions in one message grouped in a `To finish this review I need` block.
- For threshold fields (approval_matrix, quote_policy, capex_threshold, materiality, invoice_tolerance): do NOT proceed on a default. Report the check as NOT RUN and ask the question.
- For justification_template: offer the WHAT/HOW/WHY/WHO/WHERE/CADENCE/BUDGET starter (see `references/justification-template.md`). Save it to the profile file only after the user confirms.
- For non-threshold fields: offer to proceed on the ASSUMPTION default and proceed if the user does not answer.
- When the user corrects a value later, update the profile file and say so in one line.
- Write the `Profile:` line in Basis of review on every review; mark NOT PROVIDED fields so a missing value is visible.

## Example profile file
```json
{
 "erp": "large ERP",
 "purchasing_tool": "cloud procurement suite",
 "coa_style": "1xxxx asset, 5-6xxxx expense, 14xx prepaid",
 "grain": "cost_center,account,month",
 "budget_source": "annual plan (record) + Q3 forecast",
 "approval_matrix": "10k/50k/unlimited (pass as --tiers 10000,50000)",
 "quote_policy": "2 quotes over 25k, sole-source memo",
 "capex_threshold": "5000 and life > 12 months",
 "fiscal_calendar": "Feb start, closed through Sep",
 "currency": "USD",
 "materiality": "500",
 "invoice_tolerance": "price 2%",
 "justification_template": "WHAT,HOW,WHY,WHO,WHERE,CADENCE,BUDGET",
 "evidence_locations": "quotes on PO attachment; contracts in shared folder /contracts"
}
```
