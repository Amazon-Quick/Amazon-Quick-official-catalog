---
description: "How to write a single-view or workbook-wide review, word the evidence, and produce a document when asked."
last_updated: 2026-11-22
---
# Review report guide

Use the smallest report that satisfies the request. Do not force a document choice when an inline review is sufficient.

## Single-view review

1. **Score and tier** — include genre and the primary question. When `safety_status` is `blocked`, replace the ordinary tier with **Safety remediation required**.
2. **Verdict** — two or three sentences balancing the most important strength and limitation.
3. **Scorecard** — D1–D7, final domain score, contribution, and one evidence-based explanation each.
4. **Score drivers** — two to four observations with the greatest weighted effect; name bonuses, penalties, or caps.
5. **Recommendations** — two to four prioritized actions with current issue, proposed fix, affected domain, and Low/Medium/High effort.
6. **Limits** — state what could not be assessed from the available render or metadata.

Within D1 and D4, summarize visible interactivity:

- visible filters and their placement;
- clear versus ambiguous affordances;
- static versus progressive disclosure;
- visible navigation and reset behavior;
- net scoring impact, if any.

Use this note when the review relies on a static render:

> Interactivity was assessed from visible cues only. Tooltip quality, action responsiveness, parameter behavior, keyboard access, and screen-reader structure were not tested.

## Workbook-wide review

Score each materially different dashboard or view separately. Then add a cross-view section for navigation, design-system consistency, terminology, filters, and repeated issues. Do not average unrelated view scores unless the user asks for a workbook-level rollup; if averaging, state the method.

## Evidence language

Use precise statements:

- “The red fill appears on the two metrics below target” is observed evidence.
- “The filter likely controls all charts” is an inference and must be labeled.
- “The tooltip explains the outlier” is unsupported unless a tooltip was supplied or exercised.

Avoid vague praise such as “looks clean” without naming alignment, spacing, hierarchy, or another observable property.

## Document output

For Word or Google Docs output, preserve the same score, evidence, caps, and recommendations as the inline review. Add accessible headings, concise alt text for any included render, and a score table that remains readable without color.

Do not create or share a document until the user requests that output or accepts an offered format.
