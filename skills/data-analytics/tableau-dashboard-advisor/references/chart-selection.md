---
description: "Default chart types by analytical task, with conditions, alternatives and guardrails."
last_updated: 2026-11-22
---
# Chart selection

Choose by analytical task, data shape, audience, and available space—not by novelty.

| Task | Strong default | Conditions and alternatives |
| --- | --- | --- |
| Trend over ordered time | line | use bars for few discrete periods; use small multiples for many series |
| Category comparison/rank | sorted horizontal bar | aggregate or filter when labels become unreadable |
| Part-to-whole | 100% stacked bar | simple pie only for a few clearly different parts when angle judgment is acceptable |
| Distribution | histogram, box plot, strip/dot plot | simplify annotation for nontechnical audiences without hiding spread |
| Relationship | scatter plot | add reference/fit only when meaningful; avoid implying causation |
| Variance from target | diverging bar or bullet chart | define target and favorable direction explicitly |
| Current KPI | KPI card with comparison | include period, unit, benchmark, and favorable direction |
| Geography | symbol/filled map | prefer bars when precise comparison matters or geography is incidental |
| Status/exception | table, dot plot, bullet, or labeled indicator | pair color with text/icon/shape |

## Guardrails

- Avoid 3D encodings, decorative distortion, and unlabeled dual axes.
- Avoid many overlapping lines; select/highlight, facet, or summarize.
- Do not use a gauge when a bullet chart or KPI card communicates status more compactly.
- Limit categorical color to a legible, consistent set; use position for comparison.
- Use a dual axis only when the relationship warrants shared visual space, scales are disclosed, and marks are distinguishable.
- Use log scales, truncated axes, or normalized values only with clear labels and a reason.
- Avoid chart-count absolutes. Use audience attention, viewport, and question priority to determine capacity.

For each recommended view specify question, mark/chart, fields and aggregation, sort/order, benchmark, encodings, key labels, and the caveat that would invalidate the choice.

