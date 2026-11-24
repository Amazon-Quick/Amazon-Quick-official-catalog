---
description: "Human-facing overview, pre-requisites, installation, and getting started for the fpa-budget-reconciliation skill."
last_updated: 2026-11-24
---

# Budget Reconciliation

Reconciles actual spend to the plan or budget for an active close, using whatever data you have: general ledger (GL) actuals, open purchase orders, invoices awaiting posting, exchange rates, and headcount. It shows what is spent, what is still outstanding, and which lines and documents need a closer look.

## Overview

Share your plan and actuals, in any layout from any system. The skill profiles the files, then asks a few questions to learn how your data works: which plan version to use, what a plan line is, the last closed month, the reporting currency, and how your purchase orders, invoices, and GL link to each other. With that it reconciles at the lowest level of detail your plan supports, rolling detailed accounts up to plan lines where needed.

Each ordered or invoiced dollar is placed in one bucket (posted, pending, open, or released), and a tie-out checks that the buckets add back to the source totals. When your files don't link purchase orders to GL lines, the report says the overlap can't be proven. Currencies convert at each month's own rate. A statistical screen flags lines and documents that need inspection: material variances, spikes against a line's own history, lines unusual against their peers, spend with no plan, commitments past the full-year budget, likely timing reversals, stale or overrun purchase orders, aged unposted invoices, and possible duplicate billing. Headcount is compared at the last closed month, never summed across months.

You get a one-page HTML report for leadership and an Excel workbook with every number behind it, live formulas, and Owner, Status, and Notes columns for following up each item. The skill flags where to look and says why in numbers; it does not write the business explanation.

## Pre-requisites

| Name | Type | Required | Link |
| --- | --- | --- | --- |
| Code execution | SYSTEM_TOOL | Y | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |

Code execution runs the bundled Python scripts with pandas, NumPy, openpyxl, XlsxWriter, and Pydantic from the AWS Quick code sandbox, and file operations save the results. The scripts make no network calls. The skill works from files you attach: export your plan, GL and other reports from your own systems first. Outside AWS Quick, the scripts need Python 3.11 or later.

Files it can read: .xlsx, .xlsm, and .csv. Save .xlsb and .xls files as .xlsx first.

## Installation

On the **Skills** page in AWS Quick, choose **Browse all**, open the **Official** tab, search for Budget Reconciliation, and add the skill.

To install from a copy of this folder instead, choose **Create** on the **Skills** page, then **From folder**, and select the `fpa-budget-reconciliation` folder, which has `SKILL.md` at its root. You can also choose **From file** and upload a .zip of the folder. See [Teach agents with skills](https://docs.aws.amazon.com/quick/latest/userguide/working-with-skills.html).

## Getting started

Attach your plan and actuals and say "reconcile my budget". Enter `fpa-br help` for every command.

Good to know:
- The skill asks before it excludes anything (for example balance-sheet or intercompany accounts) and lists every exclusion in the workbook.
- It asks you for one total you already trust, such as last month's spend in your own system, and ties to it before showing results.
- Results are for information, not accounting or financial advice. Check them with a qualified accountant or finance controller before you act on them.
- Thresholds are adjustable: say "only flag variances over $50,000" or "use 15%".

## Test data

The files under `evals/files/` are synthetic: a clinic budget with its GL export, and a
robotics plan with GL detail, purchase orders, invoices, exchange rates, headcount, and an account
hierarchy. No real company, vendor or person appears in them.
