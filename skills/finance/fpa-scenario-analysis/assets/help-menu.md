---
description: "Command menu and help text shown by the Help workflow (fpa-sa help)."
last_updated: 2026-11-24
---
# Scenario Analysis: help

Builds a Bull, Base, and Bear forecast from one Monte Carlo simulation and leads with the probability of hitting your target, in one HTML report. Every figure is an estimate from your own data, not a prediction.

**Scenario Analysis commands**

| Command | What it does |
| --- | --- |
| `fpa-sa help` | Show this menu. |
| `fpa-sa run` | Map and validate a financial time series, run one Monte Carlo simulation, and deliver Bear, Base, and Bull with P(hit target) in one HTML report. |

Say a command to start, or describe what you want in your own words.

**What you provide**
- source: a CSV or Excel (.xlsx) file, or a pasted table
- measure_type: flow (revenue, expense) or balance (cash, backlog). Default: flow
- target: the number to test against. Default: the benchmark's full-year total
- Optional: drivers (pipeline, order book), judgment ranges, and context such as notes or decks

**What you get**
- P(hit target), the Bear, Base, and Bull values, and the probability band between them
- Monte Carlo distribution, Bull and Bear trend, variance bridge, sensitivity tornado
- What has to be true for Bull and Bear, and Areas to Probe ranked P1 to P3

**Try saying**
- "Run a bull and bear case with Monte Carlo on revenue_actuals.csv against plan."
- "Model our order backlog roll-forward and give me the P50 closing backlog with an 80% band."
- "Screen all plants for who is behind budget, then deep-dive the worst one."
- "Run the scenario on sales.csv, and read QBR_deck.pptx as context."

Outputs are informational and are not accounting or financial advice. Validate with a qualified accountant or finance controller before distributing or acting on them.
