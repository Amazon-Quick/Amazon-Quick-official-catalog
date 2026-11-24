---
description: "Module 5 approval and policy checks: approval tiers, split-PO detection, freight and tax add-ons, after-the-fact purchases. Read when the approval module runs."
last_updated: 2026-11-24
---
# Module 5: Approval and policy

Goal: the right person approves the full commitment, the spend is not split to dodge a limit, and the purchase came before the work.

Arguments (pass them as a list to `pir_run`, for example `pir_run(["approval", ...])`; add `--input <saved message>` to use a pasted message): `approval --requests R.csv [--tiers <profile approval_matrix>] --split-window-days 30 --split-margin 0.15 --addon-warn 0.15`

`--tiers` takes plain numbers, lowest first (convert a profile value such as `10k/50k/unlimited` to `10000,50000`). If `--tiers` is omitted, APR-1 and APR-3 report NOT RUN. APR-2 (large add-on) and APR-4 (after-the-fact) always run. A PO supplied with no requisition and no invoice is checked as its own item, at the PO total.

## Script rules
| Rule | Hit when | Severity |
|---|---|---|
| APR-1 tier crossed after add-ons | base amount sits in one tier, base + freight + tax + contingency in a higher one | SEND_BACK |
| APR-2 large add-on | add-ons > addon-warn (15%) of the base, tier unchanged | CONDITION |
| APR-3 possible split | same vendor + requester within the window; each request under a tier and at least one within split-margin below it; together above it (a finding names the first 20 request IDs) | SEND_BACK |
| APR-4 receipt/service before PO | service start or receipt date before the request date (after-the-fact) | CONDITION |

## Judgment rules
- Freight and tax are often added at invoice time by design. Their absence from the PO is not a finding; state the expected invoice total (PO + freight + tax) and test it against the tiers.
- Split detection is a pattern, not proof. Write "possible split" and ask whether the requests are one need. Also look for the same scope on different requesters or cost centers when the user supplies a wider list.
- Change orders: re-test the revised total, not just the increment, against the tiers.
- After-the-fact purchases: ask why the PO came late and whether the work was authorized; recommend the business's after-the-fact process if it has one.
- Approval routing: if the user supplies the approver chain, check the final approver's limit covers the full commitment.
- Quote policy cross-check: if the total crosses the quote threshold, module 4 must run.
- Never infer approval authority from a job title; use the profile's matrix or ask.

## Not checked when
No approval_matrix in profile: APR-1 and APR-3 report NOT RUN; list under Not checked and ask the user for the $ tiers.
