---
description: "Overview, pre-requisites, installation, and getting started for the Variance Commentary skill."
last_updated: 2026-11-24
---
# Variance Commentary

## Overview
Turns a table of actuals compared with a budget, forecast, plan, or prior period into variance commentary a finance reviewer can act on. It checks that the table foots, labels each line favorable or unfavorable by line type, and splits revenue into rate, volume, and mix when units exist. It is built to state only causes the data or a named owner supports, and to list everything else as an open item with an owner and a due date.

## Pre-requisites

| Name | Type | Required | Link |
| --- | --- | --- | --- |
| Code execution (run_python) | SYSTEM_TOOL | Y | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |

The bundled scripts use the Python standard library only. Run outside AWS Quick, they need Python 3.10 or later.

## Installation

On the **Skills** page in AWS Quick, choose **Browse all**, open the **Official** tab, search for Variance Commentary, and add the skill.

To install from a copy of this folder instead, choose **Create** on the **Skills** page, then **From folder**, and select the `fpa-variance-commentary` folder, which has `SKILL.md` at its root. You can also choose **From file** and upload a .zip of the folder. See [Teach agents with skills](https://docs.aws.amazon.com/quick/latest/userguide/working-with-skills.html).

## Getting started
Say "fpa-vc help", or share a table of actuals compared with budget and say "write my variance commentary for <period>".

## Disclaimer
Outputs are informational and are not accounting or financial advice. Validate with a qualified accountant or finance controller before distributing or acting on them.
