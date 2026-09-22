---
description: "Why this skill derives sales velocity from the synchronous Selling Partner API order-metrics operation instead of an asynchronous sales-and-traffic report, plus the sku/asin exclusivity, interval, and required-parameter rules for the call."
last_updated: 2026-09-15
origin: original
---

# Velocity source: the synchronous order-metrics operation (not an async report)

A natural first design assumes sales velocity would come from an asynchronous
sales-and-traffic report (create report, poll until done, download). That adds
minutes of latency and polling complexity, and the built-in Amazon Selling Partner
connector does not expose a reports operation.

The connector does expose a synchronous order-metrics operation that returns
aggregated units, orders, and sales for an interval, broken down by a granularity
and filterable by `sku` or `asin`. This skill uses it for velocity.

- Synchronous, so it meets a sub-30-second latency target with no polling.
- Returns `unitCount` per interval, so daily velocity is trivial to derive.

## Usage notes
- `interval` is an ISO-8601 range like `2026-05-12T00:00:00-07:00--2026-06-11T00:00:00-07:00`.
- `granularity: Total` for a single 30-day number; `Day` for a daily series.
- `sku` and `asin` are mutually exclusive. Pass only one.
- `marketplaceIds` and the merchant account context are required.

daily velocity = `unitCount / days_in_interval`; days_of_cover = `fulfillableQuantity / daily velocity`.
