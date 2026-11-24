---
description: "Tableau build guidance for a handoff: layout containers, filters and actions, calculations, performance, and build checks."
last_updated: 2026-11-22
---
# Tableau implementation guidance

Provide this depth only when the user wants a build handoff.

## Layout

- Prefer tiled containers for stable structure and shared alignment.
- Use floating objects selectively for overlays or exact placements whose behavior is understood.
- Specify outer padding, gutters, and relative proportions rather than false pixel precision when the final embed is unknown.
- Name worksheets, dashboards, containers, parameters, sets, and calculations descriptively.

## Filters and actions

Map each design control to an appropriate Tableau filter, parameter, set, or action based on current capabilities. State targets and clearing behavior. Use context filters only when order-of-operations or dependent-value behavior requires them; do not use them as a generic performance fix.

## Calculations

Provide formulas only when field names, grain, business definition, null/zero behavior, and aggregation semantics are sufficiently known. Label schematic formulas as pseudocode. For table calculations, state partitioning/addressing expectations. For LOD expressions, state the intended grain and relevant filter-order implication.

## Performance

Recommend measurement before architecture changes. Identify plausible risks—mark count, sheet count, filter fan-out, custom SQL, high-cost calculations, maps, extensions, or viz-in-tooltip—but do not diagnose load time from metadata alone. Suggest Performance Recording or equivalent observation when available. Live versus extract is an architecture decision involving latency, freshness, concurrency, source capacity, and governance—not a row-count rule.

## Build verification

Ask the builder to verify:

- KPI totals and comparison periods against an authoritative source;
- filters/actions, reset, and empty states;
- tooltips, sorting, legends, and number formats;
- desktop/device layouts at target dimensions;
- color contrast, non-color cues, keyboard/focus behavior where applicable;
- load and interaction performance with realistic data and permissions.

