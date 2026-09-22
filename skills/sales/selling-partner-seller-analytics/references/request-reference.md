---
description: "Exact request and response shapes for the Selling Partner API analytics metric-metadata and metric-data operations: required parameters, the mandatory MARKETPLACE_ID filter, multi-metric and ASIN filtering, pagination, gotchas, and worked examples."
last_updated: "2026-09-15"
origin: original
---

# Analytics request and response reference

How to build the metric-metadata and metric-data calls correctly. The single most common failure is a malformed metric-data request, so read this before querying.

## Metric metadata operation

Discovers what metrics exist. Call it first.

Input
- `marketplaceIds` (required): array with one marketplace ID, e.g. `["ATVPDKIKX0DER"]`.
- `entityId` (required): the seller's Merchant Token / MCID.

Reading the response. The response returns domains, each with columns:

| Field | How to use |
|-------|-----------|
| `metricId` | Use in the metrics array of the data query |
| `metricName` | Human-readable name of the metric |
| `businessDefinition` | What the metric measures; use it to confirm intent |
| `dataType` | `DOUBLE`, `STRING`, or `ZONED_TIMESTAMP` |
| `aggregationType` | How values combine: `SUM`, `AVG`, `MAX` |
| `isGroupable` | true = dimension (use in groupBy / filter); false = measure (use in metrics) |

To find the right metric: browse the domain (`Threep_Inventory`, `Threep_Sales`, `Threep_Traffic`), look at columns where isGroupable is false for measures, and read the business definition to confirm.

## Metric data operation

Retrieves values. Build the request carefully, the API is strict.

Required parameters
- `marketplaceIds`: array with one marketplace ID, e.g. `["ATVPDKIKX0DER"]`.
- `entityId`: the seller's merchant customer ID.
- `metrics`: an array of objects with a name field, e.g. `[{"name": "SESSION_CNT"}]`. Not an array of strings.
- `startDate`: inclusive, `YYYY-MM-DD`.
- `endDate`: inclusive, `YYYY-MM-DD`.
- `groupableColumnFilter` (required): must contain a `MARKETPLACE_ID` leaf condition using `EQUALS` (single marketplace) or `IN` (multiple), with an actual value. Predicate operators (`IS_NULL`, `IS_NOT_NULL`, `LIKE`) and other columns (e.g. an ASIN-only filter) do not satisfy this; a request without a valued MARKETPLACE_ID condition is rejected with "missing marketplace ID filter". Required even though marketplaceIds is also passed. To also filter by another dimension, wrap both in an AND (see the ASIN example below).
  ```json
  { "operator": "EQUALS", "column": "MARKETPLACE_ID", "value": {"stringValue": "ATVPDKIKX0DER"} }
  ```
- `dateGranularity` (required): `DAY | WEEK | MONTH | QUARTER | YEAR` (splits results into time buckets). Omitting it fails or returns empty. Send it on every call.

Optional parameters
- `groupBy`: array of groupable column names, e.g. `["ASIN"]` for a per-product breakdown.
- `pageSize`: 1 to 1000 (default 50).
- `paginationToken`: from the previous response's `pagination.nextToken`.
- `currency`: ISO 4217 code (e.g. `USD`); required for financial metrics.

### Multiple metrics in one call
```json
{ "metrics": [
    {"name": "FBA_INV_VIS_ONHAND_PMEAN_DOS"},
    {"name": "FBA_UNITS_SHIPPED_T30"}
] }
```

### Filtering to a specific ASIN, combine with AND and children
```json
{ "groupableColumnFilter": {
    "operator": "AND",
    "children": [
      {"operator": "EQUALS", "column": "MARKETPLACE_ID", "value": {"stringValue": "ATVPDKIKX0DER"}},
      {"operator": "EQUALS", "column": "ASIN",           "value": {"stringValue": "B0FN71SQ8R"}}
    ]
} }
```

### Response structure
```json
{
  "results": [
    { "startDate": "2026-06-01", "endDate": "2026-06-07",
      "metrics": [
        { "groupByKey": [ {"name": "ASIN", "value": "B0FN71SQ8R"} ],
          "metrics":    [ {"name": "FBA_INV_VIS_ONHAND_PMEAN_DOS", "value": 45.2} ] } ] }
  ],
  "pagination": { "nextToken": "..." }
}
```

## Gotchas (these cause most failures)
- The MARKETPLACE_ID filter is mandatory and strict. groupableColumnFilter must contain a MARKETPLACE_ID leaf using EQUALS (single) or IN (multiple) with a real value, required even though marketplaceIds is a top-level param. IS_NULL / IS_NOT_NULL / LIKE or an ASIN-only filter are rejected ("missing marketplace ID filter").
  - Valid: `{"operator":"EQUALS","column":"MARKETPLACE_ID","value":{"stringValue":"ATVPDKIKX0DER"}}`
  - Valid (with ASIN): `{"operator":"AND","children":[{"operator":"EQUALS","column":"MARKETPLACE_ID","value":{"stringValue":"ATVPDKIKX0DER"}},{"operator":"EQUALS","column":"ASIN","value":{"stringValue":"B0C6X64277"}}]}`
  - Invalid: MARKETPLACE_ID with IS_NOT_NULL (no value); an ASIN-only filter.
- groupableColumnFilter and dateGranularity are required, not optional. Omit either and the request fails or returns empty.
- Combining metrics is grain-based. A single metric can be grouped by any column it is groupable on. To combine multiple metrics in one call, they must share a grain: read domains availability from the metric-metadata response and groupBy only a column in the commonGrains shared by all requested metrics. Metrics at different grains must be requested in separate calls.
- metrics must be objects (`{"name": "..."}`), not strings.
- entityId is not auto-populated by the gateway; always pass it explicitly.
- Pagination field names differ: the request field is paginationToken; read its value from the response's pagination.nextToken.
- Data is delayed roughly two days from the current date; do not expect today's or yesterday's numbers.
- Empty results? Widen the date range, or drop groupBy to get an aggregated total.
- Discover first. If unsure of a metric ID, call the metric-metadata operation; never guess.

## Worked examples

"What are my sessions this month by ASIN?"
```json
{ "marketplaceIds": ["ATVPDKIKX0DER"], "entityId": "<seller_merchant_id>",
  "metrics": [{"name": "SESSION_CNT"}],
  "startDate": "2026-07-01", "endDate": "2026-07-31",
  "dateGranularity": "WEEK", "groupBy": ["ASIN"],
  "groupableColumnFilter": {"operator": "EQUALS", "column": "MARKETPLACE_ID", "value": {"stringValue": "ATVPDKIKX0DER"}} }
```

"Am I at risk of any stockouts?" analysis rule: days of supply under 14 is at risk.
```json
{ "marketplaceIds": ["ATVPDKIKX0DER"], "entityId": "<seller_merchant_id>",
  "metrics": [{"name": "FBA_INV_VIS_ONHAND_PMEAN_DOS"}, {"name": "FBA_UNITS_SHIPPED_T30"}],
  "startDate": "2026-07-01", "endDate": "2026-07-10", "dateGranularity": "DAY", "groupBy": ["ASIN"],
  "groupableColumnFilter": {"operator": "EQUALS", "column": "MARKETPLACE_ID", "value": {"stringValue": "ATVPDKIKX0DER"}} }
```

"Show me inventory for a specific ASIN"
```json
{ "marketplaceIds": ["ATVPDKIKX0DER"], "entityId": "<seller_merchant_id>",
  "metrics": [{"name": "FBA_AVAILABLE_QTY"}, {"name": "FBA_INV_VIS_BOUND_QTY"}, {"name": "FBA_INV_INBOUND_TOTAL"}],
  "startDate": "2026-07-01", "endDate": "2026-07-10", "dateGranularity": "DAY", "groupBy": ["ASIN"],
  "groupableColumnFilter": {"operator": "AND", "children": [
    {"operator": "EQUALS", "column": "MARKETPLACE_ID", "value": {"stringValue": "ATVPDKIKX0DER"}},
    {"operator": "EQUALS", "column": "ASIN",           "value": {"stringValue": "B0FN71SQ8R"}}
  ]} }
```
