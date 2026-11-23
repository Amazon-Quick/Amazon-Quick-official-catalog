---
description: "Human-facing overview of the Informatica Catalog and Data Discovery skill: what it does, how it works, its files, sample prompts, and connector requirements."
last_updated: 2026-11-13
origin: original
---
# informatica-catalog-data-discovery

Intent-driven, catalog-grounded data discovery for Informatica IDMC's Cloud Data Governance and Catalog (CDGC).

## What This Skill Does

Discovers, validates, assesses, and reports on data assets using CDGC catalog metadata. Covers:

- **Discovery** — find tables, columns, glossary terms, domains, policies by keyword or natural language
- **Trust assessment** — score datasets on certification, ownership, documentation, freshness, glossary coverage
- **Field reliability** — verify whether a specific field has a governed meaning (glossary term) or is undocumented/ambiguous
- **Sensitivity & PII** — surface data classification labels and detect hidden sensitivity (e.g., REGION encoding Religion)
- **Policy lookup** — find applicable governance policies and compliance constraints
- **Safe usage** — synthesize findings into FORBIDDEN / CAUTION / PERMISSIBLE guidance
- **Compliance flags** — check for RTBF, consent, opt-out mechanisms before outreach campaigns
- **Gap detection** — structured reporting of missing metadata (undocumented, unowned, unclassified, uncertified)

This skill is **read-only** — it never writes to the catalog. Gaps are reported with the steward as the next action.

## How It Works

The skill classifies user intent (15 intent types), routes to the matching strategy, issues MCP tool calls against CDGC (`search_assets`, `get_asset_details`), and returns a verdict-first response with evidence, gaps, and next actions.

When the user needs actual data (row values, counts, aggregates), the skill hands off to the `informatica-data-exploration` MCP after resolving the trusted asset.

## File Structure

```
informatica-catalog-data-discovery/
├── SKILL.md                          # Core playbook (13 sections)
├── assets/
│   └── README.md                     # This file
└── references/
    ├── asset-types.md                # Technical vs business asset families, classType search
    ├── tools-and-execution.md        # Tool parameters, segments, parallel execution, data-exploration hand-off
    ├── strategies.md                 # Full step-by-step procedures for each intent strategy
    ├── search-rules.md               # Mode selection, filters, ambiguity handling
    └── business-delivery.md          # Business-user response format and delivery contract
```

SKILL.md is self-sufficient for simple turns. Reference files are loaded on demand for complex scenarios.

## Sample Prompts

- Where's the customer data with the highest quality?
- Can I rely on the RATING field in FCT_ORDERS?
- Is this data safe to use for a marketing campaign?
- Who owns the SALES_FACT table, and is it certified?
- What policy applies to this PII column?
- Is there a right-to-be-forgotten flag on this dataset before I run outreach?

## MCP Dependency

Requires the `informatica-catalog-discovery` MCP server (CDGC). For data-exploration hand-off, also requires `informatica-data-exploration` (Claire). MCP server configuration is added when real endpoints are available.
