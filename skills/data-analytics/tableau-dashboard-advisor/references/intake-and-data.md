---
description: "The minimum brief to collect, how to use Tableau metadata and other inputs, and how to map each question to fields."
last_updated: 2026-11-22
---
# Intake and data evidence

## Minimum brief

Resolve audience/context, decisions/questions, and data capabilities. Useful optional details are primary device, embedding dimensions, brand/accessibility constraints, existing design, and page count.

When several essentials are missing, ask them together. Example: “Who will use this, what decisions should it support, and what fields or Tableau datasource are available?” Do not ask again for context already present.

## Tableau metadata

Discover the available Tableau read tools and their schemas. Inventory or search sources, follow pagination for the requested scope, and retrieve metadata by stable identifier when possible. Exact name, project, and owner can disambiguate candidates. Do not expose stable IDs unless useful to the user.

Classify only what the response supports:

- DATE/DATETIME can support time views, subject to grain and completeness.
- Numeric types may be measures, identifiers, codes, or quantities; verify semantic role.
- Strings may be categories, labels, IDs, or encoded dates/numbers; names alone are weak evidence.
- Geographic roles support a map only when location is central to the question and coverage is suitable.
- Formulas may enable KPIs or filters; inspect semantics before recommending them.
- Relationships and logical tables help identify grain and duplication risks but do not prove row-level behavior.

Metadata commonly omits distinct counts, distributions, row counts, target values, data latency, and actual query performance. Mark these `unknown` unless another authorized source provides them.

## Other inputs

- For a CSV or spreadsheet, inspect headers, inferred types, and only the samples necessary for design. State whether cardinality/grain was measured or inferred.
- For a verbal schema, distinguish supplied facts from design assumptions.
- For a conceptual dashboard with no data, define a required-field checklist and make the design conditional on it.

## Question-to-field map

For every question record:

| Item | Required evidence |
| --- | --- |
| Decision | action the answer enables |
| Measure | field/calculation and aggregation |
| Dimension | grouping or comparison field |
| Time | field and grain, if applicable |
| Benchmark | prior period, target, baseline, or none |
| Data grain | row/entity level and duplication caveat |
| Status | supported, assumed, or blocked |

If a question is blocked, offer options: add a field, define a transparent calculation, use a justified proxy, or reframe the question. Never silently invent a target or business definition.

## Unverified requested fields

If the user names a field or business concept that the available schema does not confirm, do not treat the name as evidence that the field exists. Record it as `unverified` and keep the response useful with a two-part alternative:

1. **If confirmed:** specify the KPI, chart, filter, comparison, or calculation that would use the field, including its required type and grain.
2. **Current fallback:** use an observed field or transparent proxy when one is defensible; otherwise omit the element and state what decision remains unsupported.

Apply this separately to each material missing concept. For example, an unverified quota may conditionally support attainment while the current design uses prior-period comparison; an unverified customer segment may conditionally support a breakdown while the current design uses an observed region or product dimension. Do not invent values, thresholds, or business definitions for either branch.
