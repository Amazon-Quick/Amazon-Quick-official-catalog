---
description: "Default layout for the metrics app and for an optional Microsoft PowerPoint version. Read in Workflow - Build App step 1 and Workflow - Build Deck step 1. Every default can be overridden by the user."
last_updated: 2026-11-24
---
# Default layout

These are defaults. Follow them unless the user asks for something else.

## App layout

- **Headline metrics on the first tab.** The first tab is a summary that leads with the headline key performance indicator (KPI) tiles, so a reader gets the main answer without clicking.
- **Dropdown lists on summary pages.** Summary tabs get dropdown lists to filter by period, entity or segment, and scenario, so viewers can filter the headline numbers in place.
- **Every chart has a table.** Put each chart next to or directly under a table of the numbers it plots. The chart shows the shape; the table gives the exact values reviewers quote.
- **Bold totals.** Every table ends with a bold total row (or a subtotal and total). Totals follow the metric's aggregation rule in `03-metrics.md`.
- **Variance before trend.** Put the variance-to-budget view ahead of trend views, so reviewers see first whether the numbers are on budget.
- **Mirror the existing deck** where you can, so reviewers know where to look and side-by-side testing takes less work.
- **Neutral theme,** with colors and fonts kept in one place (a theme file or CSS variables) so the look changes in one place.
- **Tabs:** usually one per deck section.

## PowerPoint version (only when asked)

- Each slide leads with its key highlight: a large chart or graphic plus one callout number. Keep the table that goes with each chart, with a bold total row.
- No company branding (logo, template, brand colors) unless the user asks. If they do, ask for a template or brand example and apply it.
- The first slide is a title slide only: the deck title, the owner's name if there is one, and a date if it applies. No metrics.
