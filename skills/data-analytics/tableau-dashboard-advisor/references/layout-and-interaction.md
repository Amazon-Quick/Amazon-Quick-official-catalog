---
description: "Page architecture, multi-page and responsive behavior, and filters and actions for a dashboard."
last_updated: 2026-11-22
---
# Layout and interaction

## Page architecture

Use a consistent grid. Put orientation and current context first, then decision-critical KPIs/views, then monitoring and diagnostic content. Give the primary view the most space. Use spacing and alignment rather than boxes around every object.

A typical desktop page may contain:

1. title, scope, data-through timestamp, and essential controls;
2. compact KPI row;
3. primary view plus one or two supporting views;
4. definitions, source note, and update context.

This is a pattern, not a mandatory template. The dashboard’s reading direction, locale, embed size, and task may require another flow.

## Pages and responsive behavior

Use distinct pages when the audience or analytical mode changes: overview, diagnosis, operational detail, or methodology. Name pages by purpose.

For each target viewport specify what reflows, simplifies, moves, or is removed. Preserve critical context and touch targets. Do not promise that one Tableau layout will automatically behave responsively; identify device-specific layouts or embedding constraints when relevant.

## Filters and actions

Every visible filter must support a likely decision. Define control type, default, scope, placement, and empty state. Use searchable controls only if the actual value set warrants them. When more than two controls/actions alter the view, provide a discoverable reset and visible active-filter context.

For each action state:

- source and trigger;
- action type (filter, highlight, navigate, parameter, set, or URL);
- target(s);
- behavior on clearing/no selection;
- visual affordance and keyboard/touch alternative where applicable.

Do not hide critical facts behind hover. Tooltips should add context rather than repeat labels; specify their field order, formatting, comparison, and action cue. Viz-in-tooltip is optional and must earn its rendering and comprehension cost.

