---
description: "Module 1 coding checks: GL account, cost center, project, and capex, opex, or prepaid classification. Read when the coding module runs."
last_updated: 2026-11-24
---
# Module 1: Coding

Goal: every line lands on the right account, cost center, and project, and in the right bucket (opex, capex, prepaid), with a one-line reason.

Arguments (pass them as a list to `pir_run`, for example `pir_run(["coding", ...])`; add `--input <saved message>` to use a pasted message): `coding --lines L.csv [--prior P.csv] [--capex-threshold <profile>] [--life-months 12] [--project-required] [--materiality <profile>]`

If `--capex-threshold` is omitted, CODE-1 and CODE-2 report NOT RUN. If `--materiality` is omitted, CODE-3 reports NOT RUN. CODE-4 (balance-sheet account), CODE-5 (project missing), and CODE-6 (prior-coding mismatch) always run.

## Script rules
| Rule | Hit when | Severity |
|---|---|---|
| CODE-1 capex on expense account | unit price >= capex threshold and useful life > life months, on an expense account | SEND_BACK |
| CODE-2 expense item on asset account | below threshold, or a service, on an asset account | SEND_BACK |
| CODE-3 prepaid candidate | expense line whose service period exceeds 12 months, at or above materiality | CONDITION |
| CODE-4 expense on balance-sheet account | expensed line on a balance-sheet (non-asset) account | SEND_BACK |
| CODE-5 project missing | profile requires projects and the expensed line has none / 0000 | CONDITION |
| CODE-6 differs from prior buys | same vendor + item was coded to a different account before | CONDITION |

## Judgment rules
- Read what is bought from the quote or description, not the category label. A service with "life > 1 year" ticked is still a service.
- Capex test per unit, not per order: ten items are not one asset, unless the profile pools them (for example a network build).
- Prepaid: a 12-month subscription paid up front is expensed over the service months. Name the months.
- Stock / inventory lines in systems that default them to an inventory clearing account are expected, not a finding. Check `references/systems/<kind>.md`.
- Cost center use: if the justification says "test only", "pilot", or "for team X" and the cost center belongs elsewhere, ask.
- One effort split across cost centers or projects on separate lines: ask whether that is an intended allocation.
- Prior-coding precedent (CODE-6): quote the prior account as the suggested fix, and ask which is right. The older coding may be the wrong one.

## Output line per finding
`<rule> | <line> | coded <account> (<type>), suggest <account> (<type>) because <reason> | <source> | $<amount>`

## Not checked when
No capex_threshold in profile: CODE-1 and CODE-2 report NOT RUN; ask at what unit cost and useful life an item is capitalized.
No materiality in profile: CODE-3 reports NOT RUN; ask below what $ a finding should be noted only.
No account type and no coa_style in the profile: list "Coding: account type unknown" under Not checked and ask for the account ranges.
