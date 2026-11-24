---
description: "The required sections of the dashboard blueprint and the final validation before returning it."
last_updated: 2026-11-22
---
# Blueprint output contract

Lead with the design decision, not a long methodology recap.

## Required sections

1. **Brief:** title, audience/use context, decisions, target viewport, assumptions.
2. **Question map:** priority, question, fields/aggregation, evidence status, recommended view.
3. **KPI hierarchy:** metric, definition, comparison, format, placement, favorable direction.
4. **Layout:** named zones with relative width/height and page assignments.
5. **Controls and actions:** filters, defaults, scope, reset; source-trigger-target-clearing for actions.
6. **Visual system:** semantic roles, assigned colors, typography/number-format roles, accessibility checks.
7. **Responsive behavior:** preserve, reflow, simplify, or remove by target viewport.
8. **Implementation notes:** worksheets, containers, calculations/parameters with assumptions, and tests.
9. **Risks/open decisions:** blocked questions, unknown data properties, and validation steps.

Omit sections that truly do not apply; do not fill them with ceremony. Mock values must be labeled placeholders.

## Final validation

- Every KPI/chart traces to a supported or explicitly assumed field.
- Every first-view element supports a priority question or essential context.
- Aggregations, grains, periods, targets, and favorable directions are explicit.
- Color is not the only status/selection signal.
- Critical information is visible without hover.
- Actions define target and clearing behavior.
- Missing data and unverifiable claims are labeled.
- Every material unverified requested field has a conditional use and an observed-field fallback or explicit omission.
- The recommendation does not claim a guaranteed quality score.
