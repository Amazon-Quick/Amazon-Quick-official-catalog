---
description: "Color roles, typography and labels, and branding rules for a dashboard, with accessibility in mind."
last_updated: 2026-11-22
---
# Visual system and accessibility

## Color

Define roles before hex values:

- primary/highlight;
- neutral/context;
- categorical series where needed;
- favorable, unfavorable, and warning states;
- background, text, gridlines, and focus/selection states.

Semantic direction depends on the metric: an increase may be unfavorable for cost, incidents, or latency. Pair status color with text, icon, shape, position, or pattern. Keep category assignments consistent across views.

Do not claim accessibility from a palette list. State intended foreground/background pairs and verify contrast in the rendered implementation. As design targets, use at least 4.5:1 for normal text, 3:1 for large text, and 3:1 for essential graphical objects and UI boundaries where the applicable standard requires it. Account for focus, hover, disabled, and selected states.

## Typography and labels

Specify roles—dashboard title, context/subtitle, KPI value/label, chart title, axis, annotation, tooltip—then choose sizes and weights suited to the target viewport and available fonts. Avoid naming a font that is not known to be installed or permitted.

Use plain-language display names, units, period context, and consistent number formats. Prefer direct labels when practical. Never put required information only in a tooltip.

## Branding

Use brand colors for identity and emphasis, not automatically for semantic status. Preserve accessibility even when brand colors require tints, darker variants, outlines, or non-color cues. Include logo placement only if the user requests or supplies branding.

