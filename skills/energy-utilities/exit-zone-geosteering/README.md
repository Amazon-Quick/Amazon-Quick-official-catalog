---
description: "Human-facing overview, built-in prerequisites, workflows, installation, data handling, and scheduling caveat for Exit Zone Geosteering."
last_updated: 2026-09-15
origin: original
---

# Exit Zone Geosteering

Verifies live synthetic logging-while-drilling data, prices the measured gap, warns before a projected zone exit, runs a parallel decision review, replays the stream, generates a provenance-checked handover, and renders a local dashboard.

## Overview

The skill is self-contained and runs deterministic Python in the Amazon Quick workspace. It ships a synthetic `SYN1` dataset, three reference datasets, six calculation and projection scripts, a plain-HTML fallback, and unit tests. Every observation contains confidence, reasoning, and source citations. Dollar figures come only from code and reference data, never generated narrative.

New workflows add:

- **Decision Review:** Verify gates the run, then isolated Price Impact and Zone-Exit Warning tasks run in parallel, Shift Handover checks provenance, and one decision card presents exact cited results. A failed child feature is `UNKNOWN`; a rejected Verify stops before dispatch.
- **Dashboard:** `create_dashboard.py` projects chart-ready JSON. The `highcharts` and `html_design` built-in skills create a self-contained interactive dashboard with LWD, curtain-section, confidence, and alert views. The bundled plain HTML opens when either built-in is unavailable.
- **Replay:** appends one deterministic SYN1 tick, reruns Verify and Zone-Exit Warning within the session, and stops at the first Warn or Escalate.
- **Scheduled watch:** after an interactive decision review or warning, offers once to create an opt-in recurring check that surfaces each new Warn or Escalate crossing once.

## Pre-requisites

No external connector, local service, network access, or credentials are required.

- Amazon Quick built-in tools (cloud runtime, required): `run_python`, `run_python_with_write`, `file_read`, `open_in_session_tab`, and `get_current_time` must be available.
- Amazon Quick parallel task tools (cloud runtime, required for Decision Review): `start_task`, `create_task_group`, and `get_task_group_result` must be available.
- Amazon Quick Python sandbox (cloud runtime, required): Python standard-library support is required. The scripts do not install packages or call a network.

This skill also uses built-in Amazon Quick system skills and tools. They are pre-installed; make sure they are enabled in Customize > Skills or Customize > Connectors:

- `highcharts`: builds interactive charts and data visualizations (built-in system skill, optional because a plain-HTML fallback is included).
- `html_design`: builds formatted self-contained HTML views and artifacts (built-in system skill, optional because a plain-HTML fallback is included).
- `agent_management`: lists and creates the optional recurring exit-zone watch (built-in system tool, required only for scheduled watch).
- `memory_management`: recalls and records the accept-or-decline scheduling decision so the offer appears once (built-in system tool, required only for scheduled watch).

If a required built-in tool is unavailable, stop the affected workflow. If `highcharts` or `html_design` is unavailable, open the plain-HTML fallback and state that interactive charts are unavailable. If agent or memory management is unavailable, skip the scheduling offer rather than risk asking repeatedly.

## Installation

1. Add this skill in Amazon Quick: https://docs.aws.amazon.com/quick/latest/userguide/skills-desktop.html
2. In Customize > Skills, confirm `highcharts` and `html_design` are enabled; they carry a System badge and are on by default.
3. In Customize > Connectors, confirm the built-in system tools are available if you want Decision Review fan-out or the scheduled watch: https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html
4. No external connector setup is needed.

## Getting started

Ask `run the geosteering decision review for SYN1` for the full gated review. You can also ask `verify well SYN1`, `price impact for SYN1`, `check zone exit`, `replay SYN1`, `generate handover`, or `show geosteering dashboard`.

The first Verify run creates the default 19-record SYN1 stream when needed. Replay preserves an existing stream; when no stream exists, it creates a 14-record starting point so the next tick demonstrates the first Warn crossing.

## Scheduled watch behavior

The watch is opt-in and offered once only when no matching scheduled agent and no recorded decision exist. It runs Zone-Exit Warning, compares the result with persisted `exit_alert` crossing keys, stays silent for repeated or non-qualifying results, and surfaces one card for each new Warn or Escalate threshold crossing. The scheduled task has no condition because its own prompt performs the dedupe decision.

Scheduled watches fire only while the machine is on and Quick is running. They do not run while the laptop is closed. Change or cancel them under Settings, Scheduled tasks.

## Safety and data handling

All data remains under the skill data root inside `WORKSPACE_DIR`. Wellbore identifiers must match `^[A-Za-z0-9._-]+$`. The scheduled watch reads source inputs and writes only this skill's derived alert observations. Quick does not interpret geology or generate a steer. The skill provides informational engineering and financial analysis only; qualified professionals must review field actions and economic commitments.

## Runtime notes

- The Amazon Quick sandbox environment is read-only, so every script request carries `workspace_dir` explicitly; see `references/script-interface.md` for the exec-and-`run(request)` recipe.
- The default 19-record `SYN1` seed already sits in Escalate range. Ask to `replay SYN1 from the start` to reseed with 12 ticks and watch the Watch, Warn, Escalate progression over seven appended ticks.
