---
description: "The chat layouts for presenting the audit, the comparison and the applied changes. Read before reporting results in chat."
last_updated: 2026-11-24
---
# Chat layouts

Adapt the length to the model: a clean model gets a few lines, a messy one the full layout. Lead with what's open; keep verified problems and questions apart.

## Audit

```markdown
**<Model name>: <one line on what's open, for example "3 errors and 12 issues that could give wrong numbers">**
<N> critical and <N> warnings verified · <N> questions for the owner · <N> suggestions (<N> more reviewed and judged OK)

**What it is:** <one or two sentences: purpose, horizon, how the tabs flow>.

**Fix first** (verified)
| # | Where | Problem | Impact | Fix |
|---|---|---|---|---|
| 1 | Total opex · Jan–Dec (Monthly Forecast!B8:M8) | Adds the subtotal and its lines | Opex is roughly double | Sum the lines or the subtotal, not both |
| ... (up to 8; group repeats) |

**Questions for the owner** (judgment, not errors)
- Headcount rises 22% in March (Monthly Forecast!D2) against a typical 2% a month. Is that planned?
- <2-6 more, each with the cell and the question>

**Formatting** (against this model's own conventions)
- <2-4 bullets>

**Not checked:** <only if relevant: charts, macros, value checks skipped because the file had no saved results>

Full report: [<model>_review.html](<the Report path the runner printed>). It has a filterable Issues list, the Changes with before/after numbers, a Map, and an Excel checklist with a sign-off sheet. This audit doesn't certify the numbers; the owner and reviewer sign off.

**Recommended changes** <numbered list from the plan, confirm marks and "Needs you" kept as printed>

<the approval question from SKILL.md <Workflow - Audit Workbook> step 7>
```

## Comparison

```markdown
**<old> → <new>: <N> changes look unintended** (or "No unintended-looking changes")

**What changed:** <inputs that moved and how many formulas use them; formula logic changes; rows, columns, and tabs added or removed>.

**Check these first**
| Flag | Where | What happened | Why it matters |
|---|---|---|---|
| K-01 | Salaries · Jan–Mar | The uplift was applied to Q1 only | FY salaries are understated if it was meant for the year |

**Key results:** <Total opex 17,854 → 18,900 (+5.9%); ...>

**Issues:** <N> new, <N> resolved since the old version.

Full comparison: [<new>_vs_<old>_comparison.html](<the Report path the runner printed>), with an Excel change log.
```

## Style
- **Impact in business terms:** what number is wrong and roughly by how much, when the values show it. The Changes tab's before/after values are a good source.
- **Name cells in plain words:** use the "In plain words" names from the plan ("Total cost · Q3"), with the reference in brackets.
- **Questions stay questions:** "Is that planned?", never "this is wrong".
- **Group repeats:** one row per pattern, not one per cell.
- **Clean model:** "No errors, tie-out breaks, or hardcodes found" plus any suggestions. Don't pad.
- **No scores, grades, or ready/not-ready labels;** the opening line and the counts say it.
- **One question per message:** the approval question ends the message.

## Report tabs

The report is one self-contained HTML file with light and dark styling and no scripts or external libraries; it prints cleanly.

| Tab | Shows |
|---|---|
| **Summary** | What's open and the next step; a tile per area (open verified issues, questions, fixed); "Fix first" (verified only); questions for the model owner; how the key results move; conventions; scope; disclaimer |
| **Issues** | Every finding, filterable by area, severity, basis (verified / question), status, and tab; plain-language cell names and a cell preview |
| **Changes** | One card per change: formula comparison, values before and after, risk, and status; then "Needs you" |
| **Map** | Purpose, tab-flow diagram with issue badges, key inputs and results, tab roles |
| **Performance** | Performance limits checked and any exceeded, with their issues |

The footer has an Excel checklist (status, owner, due, basis, the owner's question, links to each cell, and a **Sign-off** sheet) and a CSV.

## Output files

Saved to the location the user confirmed (Rule 11).

- `<model>_review.html`: the audit report, opened in a session tab and linked in chat; its Excel checklist (with sign-off sheet) and CSV are embedded downloads.
- `<model>_fixed.xlsx`: only after approval; opened and linked. Excel recalculates it on open.
- `<new>_vs_<old>_comparison.html`: only when comparing versions; its Excel change log is an embedded download.
- A chat summary in the layouts above.

`<model>` is the file name with spaces and symbols replaced by `_`.
