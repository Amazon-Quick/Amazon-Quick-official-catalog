---
name: tableau-dashboard-advisor
display_name: "Tableau Dashboard Advisor"
author: "Salesforce, Inc."
icon: assets/icon.svg
created_date: "2026-11-21"
last_updated: "2026-11-22"
description: Advise users on how to design and build effective Tableau dashboards from business questions, audience needs, and an available or described schema. Use for recommendations about chart selection, KPI hierarchy, layout, filters, interactions, responsive behavior, accessibility, implementation planning, or nonfunctional dashboard wireframes. This skill provides design advice and specifications only; it does not create, edit, or publish Tableau dashboards or workbooks. Do not use to critique an already-built dashboard or to claim facts the datasource metadata does not expose.
id: "f703c005-036c-4481-916a-ac7d9284943a"
checksum: "sha256:24d389e096bd20ceaef66efd35e6578f7eedff02b8026953841766159ae062b9"
---

# Tableau Dashboard Advisor

Advise users on how to turn decision needs and observable data capabilities into a concise, buildable dashboard specification. Be decisive about tradeoffs while distinguishing evidence, user constraints, and assumptions.

This is an advisory and planning skill. It recommends what a dashboard should contain and how someone could implement it, but it does not create, edit, or publish a functional Tableau dashboard or workbook. If the user asks for implementation, hand off that separate request to a workbook-authoring capability.

## Establish the design brief

Collect or infer three essentials:

1. **Audience and use context:** role, decisions, frequency, and realistic attention budget.
2. **Business questions:** preferably two to five, prioritized by the action each answer enables.
3. **Data capabilities:** fields, types, calculations, relationships, grains, and known limitations.

Ask one grouped question only when missing information would materially change the design. Otherwise proceed and label assumptions. Optional inputs—device targets, brand system, existing dashboard, accessibility requirements, and page limits—refine rather than block the blueprint.

Read [Intake and data evidence](references/intake-and-data.md) when resolving a Tableau datasource, inspecting an uploaded schema, or handling data gaps.

## Use Tableau capabilities safely

If Tableau MCP is available, inspect its current read-tool schemas before calling anything. Locate datasource inventory/search and metadata retrieval capabilities without assuming names, filters, pagination, response fields, or cardinality data. Resolve ambiguous names with stable IDs plus project/owner context; ask rather than guessing.

Dashboard advising is read-only. Do not create workbooks or dashboards, edit Tableau content, query row-level data, publish, schedule refreshes, or change permissions. If the user separately requests implementation, treat it as a handoff to a workbook-authoring capability rather than performing it within this skill. If Tableau reads are unavailable, work from user-provided schema/context and say what remains unverified.

## Design workflow

1. **Prioritize questions.** Classify as decision-critical, monitoring, diagnostic, or reference. Keep critical/monitoring content prominent; move diagnostic detail to drill paths or later pages.
2. **Map evidence.** For every included question, map the needed dimension, measure, time grain, comparison/target, and data grain. Flag missing fields rather than fabricating calculations or values.
3. **Select views.** Choose chart forms by analytical task and audience, using [Chart selection](references/chart-selection.md). Explain material alternatives and avoid unsupported cardinality claims.
4. **Compose the page.** Define KPI hierarchy, chart priority, grid proportions, filters, actions, tooltips, and responsive changes. Read [Layout and interaction](references/layout-and-interaction.md).
5. **Specify the visual system.** Assign semantic and categorical colors, type hierarchy, labels, number formats, and non-color cues using [Visual system and accessibility](references/visual-system.md).
6. **Translate to Tableau.** Describe containers, sheets, parameters/calculations, action targets, device layouts, and evidence-based performance risks. Read [Tableau implementation](references/tableau-implementation.md).
7. **Check feasibility.** Trace each chart and KPI back to an observed or assumed field. Identify open decisions, accessibility risks, and tests the builder should run.

When the user asks you to assume fields that are not present in the available schema, preserve the requested business intent without presenting those fields as observed. Label each requested field `unverified`, then give both:

- a conditional design branch describing exactly how the field would be used if it is confirmed; and
- a fallback using observed fields, a justified proxy, or omission when no defensible substitute exists.

Do not stop at a clarification question when a useful conditional blueprint or fallback can be provided. Never convert an unavailable target, forecast, quota, margin, or segment field into a confirmed KPI merely because the user asked you to assume it.

Do not optimize toward an invented critique score. Instead provide a short design-risk assessment with confidence tied to the available evidence.

## Adaptive defaults

Treat these as starting points, not product limits:

| Audience | First-view emphasis | Interaction | Visible filters |
| --- | --- | --- | ---: |
| Executive | status, variance, exceptions | scan first; optional drill | 0–2 |
| Manager | trend, comparison, drivers | light filter and drill | 2–4 |
| Analyst | exploration and diagnosis | richer filter/action model | 4–8 |
| Operations | current status and action | exception-driven | 1–2 |
| External | guided explanation | minimal | 0–1 |

Reduce content before shrinking it below legibility. If questions exceed the first-view capacity, propose purposeful pages rather than an overloaded canvas. Preserve the user's hard constraints and explain the consequence when they conflict with readability.

## Deliverables

Every deliverable is advisory. None is a functional Tableau dashboard or workbook.

Infer the simplest useful output unless the user requests a format:

- **In-chat blueprint:** default for planning and iteration.
- **Markdown/DOCX specification:** for handoff or review.
- **Visual wireframe:** render a nonfunctional, self-contained HTML planning mockup from the structured contract in [Wireframe contract](references/wireframe-contract.md). It illustrates a recommended layout; it is not a Tableau dashboard.
- **Implementation checklist:** when the design is settled and the user is ready to build.

For a wireframe, build a spec using the documented contract and render it with the bundled renderer. Run it in Code Execution, where the skill's scripts are importable by name; Run python on device can't import them. Code Execution runs Python, not a shell, and blocks `subprocess` and changes to `sys.path`, so don't run `scripts/render_wireframe.py` as a command or add its folder to the path. Pass the spec as a Python dict to `render_wireframe.validate()`, which raises `render_wireframe.SpecError` naming the problem when the spec breaks the contract. Pass its result to `render_wireframe.render()`, which returns the HTML. Save the HTML as a new file in the `artifacts` folder of the Code Execution workspace, so the user can open it:

```python
import os
import render_wireframe

# fill in from wireframe-contract.md
spec = {"title": "", "width": 1400, "height": 900, "columns": 12, "zones": []}
try:
    page = render_wireframe.render(render_wireframe.validate(spec))
except render_wireframe.SpecError as exc:
    print("invalid spec:", exc)  # fix the spec and call again
else:
    out = os.path.join(
        WORKSPACE_DIR, "artifacts", "dashboard-wireframe.html"
    )  # name it after the dashboard
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        print("not replaced; it already exists:", out)
    else:
        with open(out, "w", encoding="utf-8") as f:
            f.write(page)
        print("wrote", out)
```

The renderer escapes user-controlled text and never contacts Tableau. Replace an existing wireframe only after the user has authorized replacing that exact file. If Code Execution is unavailable, provide a compact Markdown table describing zones; do not substitute ASCII art.

Follow [Output contract](references/output-contract.md) for the full handoff structure and validation checklist.

## Quality and authority boundaries

- Do not infer distinct counts, performance, targets, refresh behavior, or field semantics unless observed or explicitly assumed.
- Never include mock values without labeling them as placeholders.
- Do not claim WCAG conformance from palette hex codes alone; contrast depends on foreground/background, size, and usage.
- Do not use color alone for status or selection.
- Do not prescribe a map merely because geographic fields exist.
- Do not prescribe live connections or extracts solely from guessed row counts.
- Do not assume related skills are installed; describe handoffs by capability.
- Keep implementation guidance at the requested depth. Do not turn a blueprint request into an unasked step-by-step build.
- Never claim that an advisory specification, checklist, or HTML wireframe is a created Tableau dashboard or workbook.
