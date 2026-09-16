---
description: "Human-facing overview, prerequisites, installation, and data-boundary guidance for the Production Surveillance skill."
last_updated: 2026-09-15
origin: original
---

# Production Surveillance

Analyzes synthetic production, flow-assurance, reservoir, safety, petrophysics, and economics scenarios with deterministic offline scripts and a mandatory human approval boundary.

## Overview

This skill supports six operationally read-only analysis workflows: Well Log Ingestion, Morning Field Report, Anomaly Investigation, Flow Assurance Check, Reservoir Constraints, and Safety Compliance Check. It ships a synthetic 27-well fixture, two synthetic LAS 2.0 logs, pre-computed synthetic well-log summaries, and local calculation scripts. The Morning Field Report can render a self-contained Highcharts dashboard, Anomaly Investigation runs three isolated domain checks in parallel, and an opt-in recurring watch can scan for deviations and RED alarms. It never sends a field command, changes equipment, acknowledges an alarm, creates a work order, or represents a recommendation as executed.

## Pre-requisites

The bundled synthetic scenarios have no external connector dependency. Amazon Quick runs the included scripts with built-in Python tooling.

- Python sandbox (system tool, Amazon Quick cloud runtime, required): use `run_python` for the included read-only scripts and `run_python_with_write` only when the user explicitly asks to save an analysis artifact.
- LAS 2.0 parsing (included Python standard-library script, Amazon Quick sandbox): unwrapped LAS 2.0 text files are parsed directly within `WORKSPACE_DIR`; no lasio, pyarrow, package installation, or network access is required. Wrapped LAS and LAS 3.0 return documented errors.
- DLIS conversion (user-selected system tool or local preprocessing utility, user's local machine, optional): DLIS still requires external conversion to validated JSON arrays because the sandbox does not include dlisio.

This skill also uses built-in Amazon Quick system capabilities. They are available by default; ensure they are enabled in Customize:

- `agent_management`: Agent management (built-in system tool, optional) creates the opt-in recurring surveillance watch.
- `memory_management`: Knowledge and memory (built-in system tool, optional) recalls and records the user's scheduling decision so the offer appears only once.
- `html_design`: HTML design (built-in system skill, optional) builds the formatted dashboard artifact.
- `highcharts`: Highcharts (built-in system skill, optional) supplies vendored chart code for the self-contained dashboard.

If `html_design` or `highcharts` is unavailable, the complete Markdown report remains available. If `agent_management` or `memory_management` is unavailable, on-demand analysis still runs but the offer-once scheduled watch is unavailable.

If a DLIS converter is unavailable, continue with the bundled synthetic fixtures, supported LAS 2.0 files, or already-converted JSON. Do not attempt package installation or substitute unverified parsing logic.

## Installation

1. Add this skill in Customize > Skills.
1. Confirm the built-in Python capability is enabled.
1. Confirm the optional `html_design`, `highcharts`, `agent_management`, and `memory_management` capabilities are enabled for dashboards and scheduled surveillance.
1. For external LAS 2.0 data, keep the unwrapped text file within the confirmed workspace. For DLIS, preprocess it locally into JSON and validate units and curve names before upload.

Amazon Quick skill installation guidance: https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html

## Getting started

Try one of these requests:

- "What curves are in the bundled synthetic SK-14 LAS file?"
- "Generate a morning field report from the synthetic fixture and build the dashboard."
- "SK-14 pressure is spiking and rate is dropping, run a full investigation."
- "Investigate the RED alarm."
- "Check the SK-14 hydrate margin at 4,560 psi, 15.7 degC, and 21.5 wt% aqueous MEG."
- "Assess SK-14 reservoir constraints."
- "Run the safety compliance check for a proposed MEG-rate evaluation."

The Morning Field Report can create a self-contained local HTML dashboard and always retains a Markdown fallback. After a Morning Field Report or Anomaly Investigation, the skill offers the recurring read-only watch once when no watch or recorded decision exists. Scheduled scans fire only while the machine is on and Quick is running.

Every analysis workflow ends with `APPROVE`, `MODIFY`, or `REJECT`, except that a safety `BLOCK` or `UNKNOWN` removes APPROVE. Approval records an external handoff only. A qualified professional must review any real-world use.

## Extending this skill

Any extension must preserve the safety veto, isolated-task `UNKNOWN` failure paths, data provenance, no-CDN dashboard requirement, offer-once scheduling rule, `execution_status: not_executed`, and the human approval boundary.

## Runtime notes

- The Amazon Quick sandbox environment is read-only. Every script exposes `run(request)`; execute it with the recipe in `references/script-interface.md` and pass `workspace_dir` to the LAS reader explicitly.
- `references/script-interface.md` lists every operation's argument names and response keys. Read it before the first script call so no key is guessed.
