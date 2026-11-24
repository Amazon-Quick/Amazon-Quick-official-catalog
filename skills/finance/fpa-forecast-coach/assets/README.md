---
description: "Overview, pre-requisites, installation, and getting started for the Forecast Coach skill."
last_updated: 2026-11-24
origin: original
---
# Forecast Coach

## Overview
Produces a baseline forecast for any numeric series over time with P10/P50/P90 bands from classical statistics: exponential smoothing (ETS, chosen per series by the corrected Akaike information criterion, AICc) averaged with the Theta method, with analytic 80% intervals. A series with many zero periods uses Croston's method with the Syntetos-Boylan approximation (SBA) instead. Alongside the baseline sit the methods finance already uses (trailing run-rates, prior year x trailing year-on-year growth, seasonal naive, and last actual held flat) and ETS and Theta on their own. Every method is backtested on the same held-out windows, and the skill writes one Microsoft Excel workbook with a Method picker and overlay columns, the backtest scoreboard, target phasing, and commentary. Every method extrapolates history, and none of them sees drivers.

## Pre-requisites

| Name | Type | Required | Setup |
| --- | --- | --- | --- |
| Code execution (run_python, run_python_with_write) | SYSTEM_TOOL | Y | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |

The scripts use only NumPy, pandas, openpyxl, and XlsxWriter from the AWS Quick code sandbox. They need Python 3.10 or later, which matters only if you run them outside AWS Quick.

## Methods and sources
The statistical methods in `scripts/` are written from their published descriptions:
- ETS in the additive-error state-space form of Hyndman, Koehler, Ord, and Snyder, [Forecasting with Exponential Smoothing](https://doi.org/10.1007/978-3-540-71918-2) (2008)
- Theta as simple exponential smoothing with drift, from Hyndman and Billah, [Unmasking the Theta method](https://doi.org/10.1016/S0169-2070(01)00143-1) (2003)
- Croston, [Forecasting and Stock Control for Intermittent Demands](https://doi.org/10.1057/jors.1972.50) (1972), with the correction in Syntetos and Boylan, [The accuracy of intermittent demand estimates](https://doi.org/10.1016/j.ijforecast.2004.10.001) (2005)

## Installation

On the **Skills** page in AWS Quick, choose **Browse all**, open the **Official** tab, search for Forecast Coach, and add the skill.

To install from a copy of this folder instead, choose **Create** on the **Skills** page, then **From folder**, and select the `fpa-forecast-coach` folder, which has `SKILL.md` at its root. You can also choose **From file** and upload a .zip of the folder. See [Teach agents with skills](https://docs.aws.amazon.com/quick/latest/userguide/working-with-skills.html).

## Getting started
Say "fpa-fc help", or attach a history and say "forecast this for the next 12 months".

## Disclaimer
Outputs are informational and are not accounting or financial advice. Validate with a qualified accountant or finance controller before relying on them.
