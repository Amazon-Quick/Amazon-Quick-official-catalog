---
description: "Overview, installation, and getting started for the Trend Analysis and Anomaly Detection skill."
last_updated: 2026-11-24
---
# Trend Analysis and Anomaly Detection

## Overview
Two analyses of a line's own history, sharing one reading of the data and one interactive dashboard:

- **Trend analysis** answers where a line is heading, how fast, and whether that changed: period on period, year on year, year to date, last twelve months, compound annual growth, the underlying trend, changes in trend, steps in level, and seasonality.
- **Anomaly detection** answers which periods do not fit, by how much, and what kind of event each looks like, such as one-off, temporary, new level, or too early to tell, plus data checks such as blanks loaded as zero, reversed signs, and unit slips.

The dashboard shows headline counts, actual against expected for each line with its events marked, a heat map of how unusual each period is, trend rate against the last twelve months, actual against budget when budget lines are added, and tables of every event and data check. An Excel workbook with live formulas, notes, and owner and sign-off columns is written when the user asks.

It knows only each line's own history. It has not seen a budget, a forecast, or any drivers, so it says what moved, not why.

## Pre-requisites

| Name | Type | Required | Link |
| --- | --- | --- | --- |
| Code execution (`run_python`, `run_python_with_write`) | SYSTEM_TOOL | Y | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |

Code execution runs the bundled Python scripts with NumPy, openpyxl, and XlsxWriter from the AWS Quick code sandbox, and writes the dashboard (and the workbook, when you ask for it). The skill needs no connectors. The scripts make no network calls, and the dashboard loads no external files.

## Installation

On the **Skills** page in AWS Quick, choose **Browse all**, open the **Official** tab, search for Trend Analysis and Anomaly Detection, and add the skill.

To install from a copy of this folder instead, choose **Create** on the **Skills** page, then **From folder**, and select the `fpa-trend-anomaly-detection` folder, which has `SKILL.md` at its root. You can also choose **From file** and upload a .zip of the folder. See [Teach agents with skills](https://docs.aws.amazon.com/quick/latest/userguide/working-with-skills.html).

## Getting started
Say "fpa-tad help", or share a file of monthly lines and say "how is this trending, and is anything unusual?".

## Security risks

| Risk | Where | What it does | Why it is kept |
| --- | --- | --- | --- |
| Script in the dashboard page | `assets/dashboard-template.html` | The page's one inline script draws the charts as SVG from the review's figures, which are embedded in the page as JSON with `<`, `>` and `&` escaped. It loads no file and makes no network request. | Without it the dashboard has no charts or line tabs. Open the dashboard only from your own session. |

## Disclaimer
Outputs are informational and are not accounting or financial advice. Validate with a qualified accountant or finance controller before distributing or acting on them.
