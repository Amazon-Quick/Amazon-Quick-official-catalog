---
description: "Overview, installation, and getting started for the Scenario Analysis skill."
last_updated: 2026-11-24
---
# Scenario Analysis

## Overview
A general-purpose financial scenario-modeling skill for AWS Quick. Point it at any financial time series (revenue, bookings, backlog, cash, inventory, headcount, operating expenses) and it produces a Bull, Base, and Bear estimate from your own data, using one Monte Carlo simulation, delivered as a single presentation-ready HTML report.

Given a history of actuals (and, optionally, a plan or budget, driver or pipeline data, a seasonality profile, and qualitative context), it:

1. Loads and validates the data, deriving the current period from the data itself, not from the clock.
2. Fits a trend (linear and polynomial) with seasonality detection and reports fit quality.
3. Models forward drivers (order book, project pipeline, sales pipeline, renewals) as probability-weighted conversions.
4. Expresses every component as a distribution and runs one Monte Carlo simulation over all of them.
5. Reads Bear, Base, and Bull directly off the simulated percentiles, so the three scenarios are points on one distribution.
6. Leads with P(hit target), the probability of making plan.
7. Produces a variance bridge, a sensitivity tornado, and "What has to be true" conditions for Bull and Bear.
8. Writes one standalone HTML report with inline SVG charts and Areas to Probe.

**Core idea:** hand-picked optimistic and pessimistic cases are replaced by percentiles of one simulation.

```
Components as distributions          Monte Carlo              Scenarios read off percentiles
Trend (regression + error)   \
Driver conversion (p, timing) ) -->  10,000 runs  -->  Bear = P10   Base = P50   Bull = P90
Seasonality                  /                          (configurable percentiles)
Judgment (ranged)           /
```

It is not a causal model and does not replace the user's judgment: drivers and judgment enter only as the user states them.

## Pre-requisites

| Name | Type | Required | Link |
| --- | --- | --- | --- |
| Code execution (run_python, run_python_with_write) | `SYSTEM_TOOL` | Y | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |

The skill needs no connector, space, or web search. The scripts use NumPy, pandas, and openpyxl, which are in the AWS Quick sandbox. Save `.xls` files as `.xlsx` or CSV first. The report uses no chart library, no external files, and no network request.

## Installation

On the **Skills** page in AWS Quick, choose **Browse all**, open the **Official** tab, search for Scenario Analysis, and add the skill.

To install from a copy of this folder instead, choose **Create** on the **Skills** page, then **From folder**, and select the `fpa-scenario-analysis` folder, which has `SKILL.md` at its root. You can also choose **From file** and upload a .zip of the folder. See [Teach agents with skills](https://docs.aws.amazon.com/quick/latest/userguide/working-with-skills.html).

## Getting started
Say "fpa-sa help", or share a history file and say "run scenario analysis on this against plan".

## Disclaimer
Outputs are informational and are not accounting or financial advice. Validate with a qualified accountant or finance controller before distributing or acting on them.
