# System Architecture and Islanding

Use this when producing the single-line diagram, the equipment schedule, and
the islanding procedure. Render diagrams as SVG or with the `highcharts` and
`html_design` built-in skills; there is no diagramming package in the sandbox.

## Single-Line Diagram Components

```
- PCC (Point of Common Coupling): connection to the utility grid
- Main breaker / automatic transfer switch (ATS)
- Microgrid controller / energy management system (EMS)
- AC bus (typically 480V 3-phase)
- DC bus (if DC-coupled solar + storage)
- Solar PV array -> DC/AC inverter -> AC bus
- Battery system -> bidirectional inverter -> AC bus
- Diesel genset -> AC bus (direct, synchronous generator)
- Critical load panel (fed during islanding)
- Non-critical load panel (shed during islanding if needed)
- Grid interconnection with protective relaying (per IEEE 1547)
```

## Islanding Transition

```
1. Grid fault detected (voltage/frequency deviation)
2. PCC breaker opens (anti-islanding trips first, then an intentional island forms)
3. Microgrid controller assumes frequency/voltage regulation
4. Genset starts if needed for capacity
5. Non-critical loads shed if generation is insufficient
6. Critical loads maintained by PV + battery + genset
7. Grid returns: synchronize, close PCC breaker, resume grid-connected mode
```

Islanding is not instantaneous. Sub-second transfer needs a battery inverter in
virtual synchronous machine mode. Gensets take 5 to 15 seconds to start and
synchronize. PV inverter anti-islanding protection (IEEE 1547) trips during grid
faults unless the microgrid controller explicitly overrides it for intentional
islanding, which requires microgrid-certified inverters.

## Deliverable Set

- Single-line diagram (SVG or described for drawing).
- Equipment schedule: PV modules, inverters, batteries, genset, switchgear,
  controller. A spreadsheet suits this well (`canvas_xlsx`).
- Dispatch profile charts: a sunny sample week, a cloudy sample week, and an
  outage event.
- Annual energy-flow Sankey diagram: sources -> storage -> loads -> exports/curtailment.
- Monthly generation breakdown: stacked bar chart by source.

If chart rendering is unavailable, deliver a text-based architecture description
with key specifications rather than fabricating an image.
