---
description: "Help menu shown by the Help workflow (fpa-mdab help)."
last_updated: 2026-11-24
---
# Metrics Deck App Builder: help

Turns a recurring finance deck into an AWS Quick App whose numbers are checked against the system of record, by cataloging and reconciling every number first.

**Metrics Deck App Builder commands**

| Command | What it does |
| --- | --- |
| `fpa-mdab help` | Show this menu. |
| `fpa-mdab catalog` | Frame the deck, catalog its sources, datasets, and metrics, and reconcile every number to the system of record. |
| `fpa-mdab app` | Design the app from the reconciled catalog and build it with the app_building skill. |
| `fpa-mdab deck` | Build a Microsoft PowerPoint version from the reconciled catalog. |

**What you provide**
- deck_name: the deck the app replaces or supports
- deck_cadence: weekly, monthly, or quarterly (default: monthly)
- workspace_folder: where to save the catalog files (asked once)

**Try saying**
- "Build an app for our monthly business review deck."
- "Catalog the metrics behind this deck before we build anything."

Say a command to start, or describe what you want in your own words.

Outputs are informational and are not accounting or financial advice. Validate the metrics with a qualified accountant or finance controller before the app is relied on.
