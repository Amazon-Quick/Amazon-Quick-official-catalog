---
name: tableau-about
display_name: "About the Tableau Plugin"
author: "Salesforce, Inc."
icon: assets/icon.svg
created_date: "2026-11-21"
last_updated: "2026-11-22"
description: Explain what the Tableau plugin is for and how it helps users work with existing or new Tableau content. Use when someone asks about the plugin, its purpose, suitable use cases, or why they should use it.
id: "4e3493c3-15fd-4238-a9a3-40871bf843e7"
checksum: "sha256:f438b6bae83143a3dee7290eebd40f7a356366f822f4dbb97442637407d73668"
---

# Tableau Plugin Overview

The Tableau plugin connects Amazon Quick to Tableau so users can explore existing analytics content, understand dashboard data, plan new dashboards, evaluate datasource metadata, review visualization design, and create or modify workbooks.

## Core capabilities

### Explore existing Tableau content

Find and open Tableau views, dashboards, workbooks, datasources, and metrics by name or keyword. Use the appropriate focused Tableau skill when the user wants to inspect or work with a specific item.

### Analyze dashboard data

Answer questions using the summary data exposed by a Tableau view. This can include identifying trends, comparing categories, applying supported filters, and finding marks that meet a condition.

Do not imply unrestricted access to underlying row-level data. Analysis is limited to the data and metadata Tableau makes available through the connected capabilities and the user’s permissions.

### Create or modify workbooks

Build a new Tableau workbook or update an existing one from a natural-language request. This can include creating sheets, calculations, charts, dashboards, filters, and layouts. The result is validated and handed to the user as a `.twbx` file to upload to Tableau.

The model constructs the workbook definition programmatically. Users do not need to understand or edit workbook XML themselves.

### Build a live data app

Scaffold, wire to a datasource, author, and package a Tableau data app — a custom viz-extension web app hosted on a worksheet that queries a datasource live, instead of using marks, Show Me, or the chart catalog. The app is handed to the user as a `.twbx` file to upload to Tableau.

The model authors the app's query and visualization code directly from the user's stated criteria and vibe; users do not need to write that code themselves. Use this workflow instead of standard workbook authoring when the request is for a live-querying custom viz extension rather than a native chart.

## Planning and review capabilities



### Advise on dashboard design

Provide advice that turns business questions, audience needs, and available datasource metadata into an implementation-ready Tableau dashboard plan.

A blueprint can specify:

- KPIs and analytical questions
- Recommended charts
- Dashboard hierarchy and layout
- Filters, actions, and tooltips
- Desktop and tablet behavior
- Accessible colors and typography
- Tableau implementation guidance
- A deterministic HTML wireframe when useful

This is an advisory workflow. It does not create, edit, or publish a Tableau dashboard or workbook. A wireframe is a nonfunctional planning mockup, not a working dashboard. Use the separate workbook-authoring workflow when the user requests implementation.

### Review datasource metadata quality

Evaluate published Tableau datasource metadata for:

- Schema hygiene
- Field naming
- Likely type or role mismatches
- Calculation complexity
- Documentation gaps
- Available freshness signals

The review can produce full scans, priority-only reports, datasource comparisons, changed-only results, or comparisons with a prior baseline.

This is a metadata-only assessment. It does not claim to detect row-level nulls, duplicates, distributions, PII, or underlying-data freshness when those facts are not exposed by the available metadata.

### Critique visualization design

Review and score Tableau dashboards or views using rendered-image evidence, available Tableau metadata, and a seven-domain design rubric.

The critique can assess:

- Audience adaptation
- Message alignment
- Chart selection
- Layout and storytelling
- Color
- Textual elements
- Typography and readability

Recommendations should be prioritized and tied to visible or explicitly supplied evidence. The critique is read-only: it does not modify workbooks, validate source-data accuracy, assess business performance, or infer interactions and accessibility behavior that cannot be observed.

## Routing guidance

Use the focused Tableau skill that best matches the requested outcome:

- Use `tableau-content-viewer` to find, open, or show existing Tableau content.
- Use `tableau-dashboard-advisor` for advice on how to design and build a dashboard, including a nonfunctional planning wireframe. It does not create the Tableau dashboard.
- Use `tableau-data-app-authoring` to scaffold, wire, author, and package a live-querying data app (viz extension) for the user to upload.
- Use `tableau-data-quality-sentinel` to review published datasource metadata.
- Use `tableau-viz-critique` to evaluate an existing dashboard or view.
- Use `tableau-workbook-authoring` to create, edit, or copy a workbook and package it for the user to upload.

For requests spanning multiple workflows, sequence them explicitly. For example, critique an existing dashboard before handing approved recommendations to workbook authoring.

## Representative requests

- `Find and open the regional sales dashboard.`
- `Explain the largest trends in this view.`
- `Which products shown here meet this condition?`
- `Advise me on how to design an executive dashboard for regional sales performance.`
- `Show me a nonfunctional desktop and tablet wireframe for this dashboard plan.`
- `Run a metadata quality scan on the Sales datasource.`
- `Compare metadata quality for Orders and Orders v2.`
- `Review this dashboard and prioritize its three highest-impact improvements.`
- `Add a monthly trend chart to this workbook.`
- `Build a data app that shows profit ratio by category as a live chart.`
