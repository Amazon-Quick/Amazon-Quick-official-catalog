---
description: "Overview, prerequisites, installation, and getting started for the Spreadsheet Evaluator skill."
last_updated: 2026-11-24
---
# Spreadsheet Evaluator

## Overview
Reviews a finance workbook before it is shared, using checks a finance analyst would run. The bundled scripts check formula integrity, cross-tab reconciliation, data integrity, financial logic, and structure; the agent adds business judgment. Problems found by exact checks are kept apart from questions for the owner. It produces one HTML audit report with an Excel sign-off checklist and a numbered change list. It applies approved fixes to a copy (not the original) and re-checks the copy. It can also compare two versions of a workbook to flag changes that look unintended.

## Pre-requisites

| Name | Type | Required | Link |
| --- | --- | --- | --- |
| Code execution (run_python_with_write) | SYSTEM_TOOL | Y | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |

The scripts use the Python standard library and openpyxl, which the AWS Quick code sandbox provides. They run on Python 3.10 or later if you run them outside AWS Quick. No formula recalculation is bundled: value checks read the results Excel last saved in the file, and the fixed copy recalculates when it is opened in Excel. The report loads no scripts or external files.

Period detection reads English month names. Currency detection reads the symbols and codes for US dollars, euros, pounds sterling, yen, and rupees ($, €, £, ¥, ₹, USD, EUR, GBP, JPY, INR).

## Where files are written
The report and the fixed copy are written to the folder you choose when the skill asks where to save them. The runner also keeps working files, including a snapshot copy of your workbook, under `artifacts/.metadata/` in the AWS Quick workspace. Treat both as confidential as the workbook.

## Installation

On the **Skills** page in AWS Quick, choose **Browse all**, open the **Official** tab, search for Spreadsheet Evaluator, and add the skill.

To install from a copy of this folder instead, choose **Create** on the **Skills** page, then **From folder**, and select the `fpa-spreadsheet-evaluator` folder, which has `SKILL.md` at its root. You can also choose **From file** and upload a .zip of the folder. See [Teach agents with skills](https://docs.aws.amazon.com/quick/latest/userguide/working-with-skills.html).

## Getting started
Say "fpa-se help", "fpa-se audit", or "fpa-se compare", or attach a workbook and say "check this model before I share it".

## Disclaimer
Outputs are informational and are not accounting or financial advice. The audit does not certify the numbers, and it is not a financial statement audit or an internal-control attestation. Validate with a qualified accountant or finance controller before sharing or relying on the model.

## Test data

The three workbooks under `evals/files/` are invented review models (clean, messy, ambiguous),
built to trip the checks. They are not based on any real model.
