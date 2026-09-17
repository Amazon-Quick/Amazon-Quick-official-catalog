---
description: Pre-requisites, installation, and getting started for automated-log-analysis.
last_updated: 2026-09-16
origin: original
---

# Automated Log Analysis

Deterministic petrophysical evaluation of LAS 2.0 well logs inside Amazon Quick. Bundled scripts parse the file with vendor curve-alias resolution, compute Vshale, density porosity, Archie water saturation, effective porosity, net pay, pay zones, and OOIP, render a five-track composite log, and write a Word report with a Markdown twin. The email workflow reads a vendor delivery from Outlook and drafts, never sends, the results reply. A synthetic well (`SYN-LAS-1`) with locked golden values exercises the entire pipeline without any email.

## Pre-requisites

| Dependency | Type | Runtime | Required |
|---|---|---|---|
| `file_read`, `run_python_with_write` | Built-in tools | Amazon Quick sandbox | Required |
| `open_in_session_tab`, `get_current_time` | Built-in tools | Amazon Quick sandbox | Optional; plot and report still save without them |
| Outlook | Cloud connector | Amazon Quick | Optional; needed only for the email pipeline |
| `numpy`, `pandas` | Sandbox Python libraries | Amazon Quick sandbox | Required by parser and evaluator |
| `matplotlib` | Sandbox Python library | Amazon Quick sandbox | Required by the plotter |
| `python-docx` | Sandbox Python library | Amazon Quick sandbox | Optional; Markdown report is written when absent |

No local MCP servers, package installation, or network access. Each script exposes `run(request)` and is executed by importing it by file stem inside `run_python_with_write` with `workspace_dir` passed explicitly; see `references/script-interface.md`. The sandbox blocks `__file__`, `__dict__`, `exec`, and `compile`, so the scripts never rely on them.

DLIS attachments are not supported (`dlisio` is not in the sandbox); ask the vendor for LAS.

## Installation

1. Install the `automated-log-analysis/` directory into Amazon Quick as a local skill folder.
2. Optionally enable the Outlook connector in Settings > Capabilities > Connections for the email pipeline.
3. Trigger it with any of the phrases below.

## Getting started

- "Run the log analysis on the synthetic well" creates `SYN-LAS-1` and runs the whole pipeline; expect 325.0 ft net pay, three zones, OOIP 195,437,364 STB.
- "Analyze this LAS file at automated-log-analysis-data/my-well.las" runs the standalone workflow on a file already in the workspace.
- "Process daily drilling logs from my Demo folder" runs the email pipeline and drafts the results reply.
- "Run the degraded case with no resistivity" demonstrates the limited-accuracy path: net pay screened on porosity and shale only, Sw and OOIP reported as unavailable.

All outputs are written under `<workspace>/automated-log-analysis-data/`: the LAS, `<well>_parsed.json`, `<well>_evaluation.json`, `<well>_log_plot.png`, `<well>_report.docx`, and `<well>_report.md`.

## What the scripts do and do not do

The scripts are deterministic and self-contained. They replace the model-written matplotlib and Node `docx` steps of the original prototype, so figures and layout no longer vary between runs. Narrative (QC interpretation, recommendations, email wording) stays with the model and is supplied to the report script explicitly; the scripts never invent recommendations.

## Directory structure

```
automated-log-analysis/
  SKILL.md
  README.md
  references/
    script-interface.md
    curve_aliases.json
  scripts/
    create_synthetic_las.py
    run_las_parse.py
    run_evaluation.py
    create_log_plot.py
    create_report.py
    tests/
  evals/
    evals.json
```
