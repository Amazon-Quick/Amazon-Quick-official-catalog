---
description: "Shortcut map from a seller's question to the right Selling Partner API analytics metric ID, the three analytics domains, and the key metrics per domain. Live metric metadata is the source of truth for availability."
last_updated: "2026-09-15"
origin: original
---

# Metrics catalog

A shortcut for mapping a seller's question to the right metric ID. The live metric-metadata operation response is the source of truth: always confirm the ID and its business definition there. If a metric below is not in the metadata for the seller's marketplace, pick the closest one that is, and tell the seller which you used.

## Domains
- `Threep_Inventory`: FBA inventory health, days of supply, restock, inbound.
- `Threep_Traffic`: sessions, page views, glance views, featured-offer share.
- `Threep_Sales`: ordered units, ordered items, revenue.

The domain names carry the `Threep_` prefix in the metric-data operation. Use these names as returned by the metadata; do not assume an unprefixed alias.

## Intent to metric map

| Seller question | Metric ID | Domain |
|---|---|---|
| How much inventory do I have? | `FBA_AVAILABLE_QTY` | Threep_Inventory |
| Am I at risk of stockout? | `FBA_INV_VIS_ONHAND_PMEAN_DOS` (days of supply) | Threep_Inventory |
| What is my demand forecast? | `FBA_FORECAST_N7_P80`, `FBA_FORECAST_N30_P80` | Threep_Inventory |
| When should I restock? | `FBA_INV_VIS_RESTOCK_ORDER_DATE` | Threep_Inventory |
| How much should I restock? | `FBA_INV_RESTOCK_QTY` | Threep_Inventory |
| What is my sales velocity? | `FBA_UNITS_SHIPPED_T30` | Threep_Inventory |
| What is reserved / bound? | `FBA_INV_VIS_BOUND_QTY` | Threep_Inventory |
| What is inbound? | `FBA_INV_INBOUND_TOTAL` | Threep_Inventory |
| How is my traffic? | `SESSION_CNT` | Threep_Traffic |
| What are my page views? | `PAGE_VIEW_CNT` | Threep_Traffic |
| Page views by device? | `DESKTOP_PAGE_VIEW_CNT`, `MOBILE_APPLICATIONS_PAGE_VIEW_CNT`, `MOBILE_BROWSER_PAGE_VIEW_CNT` | Threep_Traffic |
| Am I winning the featured offer? | `FEATURED_OFFER_CNT` | Threep_Traffic |
| How many units did I sell? | `TOTAL_ORDERED_UNITS` | Threep_Sales |
| What is my revenue? | `TOTAL_ORDERED_PROD_SALES_AMT` | Threep_Sales |

## Key metrics by domain

### Threep_Inventory
- Days of supply / stockout risk: `FBA_INV_VIS_ONHAND_PMEAN_DOS`, `FBA_INV_VIS_ONHAND_P90_DOS`, `FBA_INV_VIS_TOTAL_PMEAN_DOS`, `FBA_INV_VIS_TOTAL_P90_DOS`. Analysis rule: days of supply under 14 is at risk of stockout.
- Restock: `FBA_INV_VIS_RESTOCK_ORDER_DATE` (a string/date dimension), `FBA_INV_RESTOCK_QTY`, `FBA_INV_VIS_RECOMMENDED_MIL_PMEAN_DOS`, `FBA_INV_VIS_RECOMMENDED_MIL_P90_DOS`.
- On-hand / reserved: `FBA_AVAILABLE_QTY`, `FBA_INV_VIS_BOUND_QTY`, `FBA_INV_VIS_CUSTOMER_ORDERS_QTY`, `FBA_INV_VIS_CUSTOMER_SHIP_DISABLED_QTY`.
- Inbound / transfers: `FBA_INV_INBOUND_TOTAL`, `FBA_INV_VIS_TRANS_SHIPMENTS_TOTAL_QUANTITY`.
- Inventory health: `FBA_INV_HIL_ZONE`.
- Sales velocity: `FBA_UNITS_SHIPPED_T30`.
- Demand forecast: `FBA_FORECAST_N7_P80`, `FBA_FORECAST_N30_P80`, `FBA_FORECAST_N60_P80`.

### Threep_Traffic
- Sessions: `SESSION_CNT` and device splits `DESKTOP_SESSION_CNT`, `MOBILE_APPLICATIONS_SESSION_CNT`, `MOBILE_BROWSER_SESSION_CNT`.
- Page views: `PAGE_VIEW_CNT` (plus `DESKTOP_` / `MOBILE_APPLICATIONS_` / `MOBILE_BROWSER_`).
- Glance views: `GLANCE_VIEW_CNT` (plus device splits).
- Featured offer: `FEATURED_OFFER_CNT` (plus device splits).

### Threep_Sales
- `TOTAL_ORDERED_UNITS`, `TOTAL_ORDERED_ITEMS`, `TOTAL_ORDERED_PROD_SALES_AMT` (revenue; pass currency for financial metrics).

## Readiness caveats
- Metadata is the source of truth for availability. Not every metric in this catalog is exposed to every seller. Use only metrics that appear in the metric-metadata response; if one is not returned, do not use it, pick an available alternative and say so.
- Use the metric-metadata operation to discover metrics and groupable columns beyond this list; this catalog is a curated starting point, not the full set.
