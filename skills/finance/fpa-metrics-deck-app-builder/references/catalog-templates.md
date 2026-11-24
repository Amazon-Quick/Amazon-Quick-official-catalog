---
description: "Markdown table templates for the deck catalog (data sources, datasets, metrics, reconciliation log) and the ID scheme. Read in Workflow - Build Catalog steps 4, 6, 7, and 9."
last_updated: 2026-11-24
---
# Catalog templates

Copy these tables into the deck folder files. Use one row per item. Write `TBD` rather than leaving a cell blank, and list each `TBD` as an open question in `00-deck-brief.md`.

Example rows use US dollars (USD). Replace the currency, the column names, and the formats with the deck's reporting currency.

IDs are stable and short, so later files can cite them: `SRC-01`, `DS-01`, `M-01`.

## 01-data-sources.md

| ID | Source | System | System of record? | Owner (team) | Refresh cadence | Data lands (compared to close) | Access path | Classification | Deck sections | Notes |
|----|--------|--------|-------------------|--------------|-----------------|--------------------------------|-------------|----------------|---------------|-------|
| SRC-01 | Actuals | General ledger (enterprise resource planning, ERP) | Yes | | Daily | Business day 3 | | | | |
| SRC-02 | Budget and forecast | Planning system | Yes (plan) | | Per planning cycle | | | | | |
| SRC-03 | Finance mart | Amazon Redshift `schema` | No (derived) | | Daily | | | | | |

## 02-datasets.md

| ID | Dataset | Source ID | Type (table, view, Quick Sight dataset, sheet) | Grain (one row per ...) | Time column and calendar | Key dimensions | Measures (raw) | Scenario column | Currency and FX column | Row-level security | Refresh | Notes |
|----|---------|-----------|------------------------------------------------|-------------------------|--------------------------|----------------|----------------|-----------------|------------------------|--------------------|---------|-------|
| DS-01 | | SRC-01 | | | `fiscal_period` (fiscal, 4-4-5) | entity, cost center, account | amount_usd | actual / budget / forecast | USD; month-end rate | | | |

## 03-metrics.md

Abbreviations in the example rows: quarter to date (QTD), year to date (YTD), month over month (MoM), year over year (YoY), and basis points (bps).

| ID | Metric | Business definition (one sentence) | Formula | Unit and format | Aggregation | Time basis | Comparisons | Filters and exclusions | Dataset and columns | Owner | Tolerance | Status |
|----|--------|------------------------------------|---------|-----------------|-------------|------------|-------------|------------------------|---------------------|-------|-----------|--------|
| M-01 | Net revenue | | `SUM(revenue_usd)` | $M, 1 decimal place | Sum | Month, QTD, YTD | MoM, YoY, compared to budget | Exclude intercompany | DS-01.revenue_usd | | 5 bps | Draft |
| M-02 | Gross margin % | | `SUM(gross_profit) / SUM(revenue)` | %, 1 decimal place | Ratio of sums | Month, QTD | Compared to budget (bps) | | DS-01 | | 10 bps | Draft |

The Status column moves `Draft` -> `Owner approved` -> `Reconciled` -> `In app`.

## 04-reconciliation.md

Reconciled period: `<fiscal period>`. System of record: `<SRC-ID>`.

Paste the table `check_reconciliation` prints (references/script-interface.md), then add the Explanation and Accepted by columns for each metric that fails or is `TBD`:

| Metric ID | Explanation | Accepted by |
|-----------|-------------|-------------|
| M-01 | | |

references/script-interface.md gives the variance formula. A metric whose deck value is 0 needs an absolute tolerance agreed with the finance owner, recorded in its Tolerance column.
