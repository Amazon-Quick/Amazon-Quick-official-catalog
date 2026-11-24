---
description: "Overview, installation, and getting started for the Purchase and Invoice Review skill."
last_updated: 2026-11-24
---
# Purchase and Invoice Review

## Overview
Does a finance reviewer's legwork on purchase requisitions, purchase orders (POs), and supplier invoices before approval or payment, for any enterprise resource planning (ERP) system or purchasing tool. It maps pasted tables onto a neutral schema and runs only the checks that apply: coding, budget fit, contract, price, approval and policy, and invoice match. It returns one verdict per item in a fixed four-section report: Verdict, Summary, 7 Justifications Summary, and 3-Way Match Summary. Every finding carries its rule, number, source, and amount at stake. It recommends a verdict and does not approve, reject, or pay anything.

Company specifics (approval tiers, tolerances, thresholds, and justification template) come from a finance profile JSON file the user keeps at a path they choose. The skill saves only profile fields there, not item data, amounts, or names. During a review, the skill copies the pasted input to a scratch folder in the AWS Quick workspace for the bundled engine and deletes that folder when the review ends. If the deletion fails, it gives the user the folder path to delete.

## Pre-requisites
| Name | Type | Required | Link |
| --- | --- | --- | --- |
| Code execution (`run_python`, `run_python_with_write`) | SYSTEM_TOOL | Y | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |

The bundled engine uses the Python standard library only and needs no connector.

## Installation

On the **Skills** page in AWS Quick, choose **Browse all**, open the **Official** tab, search for Purchase and Invoice Review, and add the skill.

To install from a copy of this folder instead, choose **Create** on the **Skills** page, then **From folder**, and select the `fpa-purchase-invoice-review` folder, which has `SKILL.md` at its root. You can also choose **From file** and upload a .zip of the folder. See [Teach agents with skills](https://docs.aws.amazon.com/quick/latest/userguide/working-with-skills.html).

## Getting started
Say "fpa-pir help", or paste a requisition, PO or invoice table and say "review this before I approve it".

## Disclaimer
Outputs are informational and are not accounting, audit, or financial advice. Validate each verdict with a qualified accountant, finance controller, or procurement lead before approving or paying.
