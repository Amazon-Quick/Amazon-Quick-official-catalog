---
description: "Overview, pre-requisites, installation, and getting started for the Metrics Deck App Builder skill."
last_updated: 2026-11-24
---
# Metrics Deck App Builder

## Overview
Walks a finance analyst and their team from "we have a deck" to "we have an AWS Quick App whose numbers are checked against the system of record." It builds a catalog first (data sources, datasets, metric definitions) as Markdown files and checks every number on the deck against the system of record within a stated tolerance. Only then does it design and build the app. Each metric's definition and source, and the data's freshness, are visible in the app.

## Pre-requisites
| Dependency | Type | Required | Link |
|---|---|---|---|
| app_building | SKILL | Y | [Skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html) |
| Code execution | SYSTEM_TOOL | Y | [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) |
| canvas_pptx | SKILL | N | [Skills](https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html) |

app_building builds the app. Code execution profiles data extracts and reconciles the numbers; without it those values stay `TBD`. canvas_pptx is needed only for a Microsoft PowerPoint version.

No external connectors are needed. Dashboards, datasets, and connectors you already have in AWS Quick can be cataloged as sources, and the skill asks you to confirm each one before it registers it in the app.

## Installation

On the **Skills** page in AWS Quick, choose **Browse all**, open the **Official** tab, search for Metrics Deck App Builder, and add the skill.

To install from a copy of this folder instead, choose **Create** on the **Skills** page, then **From folder**, and select the `fpa-metrics-deck-app-builder` folder, which has `SKILL.md` at its root. You can also choose **From file** and upload a .zip of the folder. See [Teach agents with skills](https://docs.aws.amazon.com/quick/latest/userguide/working-with-skills.html).

## Getting started
Say "fpa-mdab help", or attach your current deck and say "build an app for this deck".

## Disclaimer
Outputs are informational and are not accounting or financial advice. Validate the metrics with a qualified accountant or finance controller before the app is relied on.

## Test data

`evals/files/synthetic_mbr_deck_outline.md` is an invented monthly business review outline, and `evals/files/synthetic_mbr_actuals.csv` is an invented ledger extract for it.
Their figures are not from a real business.
