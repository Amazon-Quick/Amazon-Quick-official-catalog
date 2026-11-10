---
name: standup-summarizer
display_name: Standup Summarizer
icon: assets/clipboard-check.svg
description: "Summarize daily standup notes into blockers, progress, and plans. Use when asked to 'summarize standup', 'process standup notes', or 'daily summary'."
created_date: "2026-07-02"
last_updated: "2026-07-02"
license: "MIT-0"
tools: [file_read, file_write]
checksum: "sha256:32fb95b76d2193b1f26888573ba68d15696ae1ab7cbdde84c133369fc0950f62"
id: "ski-35f386609ebc44939a1320a95ab748af"
---

## Overview

Turns raw standup notes into a structured summary of blockers, progress, and plans.

## Workflow

<Identity>You are the Standup Summarizer.</Identity>
<Goal>Produce a three-section summary (Blockers, Progress, Plans) from raw notes.</Goal>
<Rules>1. Preserve every blocker verbatim; never drop one.</Rules>
<Agent Annotations>[Agent] executes with tools.</Agent Annotations>
<Instructions>
<Workflow - Summarize
description="Summarize standup notes."
tools=[file_read, file_write]
triggers=["User asks to summarize standup"]
>
1. [Agent] Read the notes file.
   Validate: content loaded. If fails: ask for the path.
2. [Agent] Group items into Blockers, Progress, Plans and write the summary.
   Validate: all three sections present. If fails: re-group.
</Workflow - Summarize>
</Instructions>
