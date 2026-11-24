---
description: "Help text shown by the Help workflow (fpa-se help)."
last_updated: 2026-11-24
---
# Spreadsheet Evaluator: help

Audits a finance workbook before it is shared, and applies the fixes you approve to a copy. The skill works on a copy and does not write to your original.

**Commands**
- `fpa-se audit`: check a workbook and get a report with a numbered change list
- `fpa-se compare`: compare two versions of a workbook and flag changes that look unintended
- `fpa-se help`: show this menu

**What it checks**
- Formula integrity: errors, broken references, inconsistent or pasted-over formulas, SUMs that stop short
- Data integrity: totals that don't tie, duplicates, numbers stored as text, mixed currencies
- Financial logic: double counting, wrong growth bases, mixed units, unusual movements raised as questions
- Structure and formatting: inputs on calculation tabs, hidden tabs, formatting against the model's own convention

**What you get**
- An HTML audit report with an Excel sign-off checklist
- A numbered change list; approved changes go into a fixed copy that is re-checked
- Optionally, a comparison of two versions that flags changes that look unintended

**What you provide**
- model: the workbook (.xlsx or .xlsm)
- excel_target (optional): the oldest Excel version your readers use
- prior_version (optional): an earlier version to compare against
- A folder to save the report and the fixed copy in

**Try saying**
- "Check this forecast before I send it."
- "Does this budget tie out?"
- "What changed between these two versions?"

Outputs are informational and are not accounting or financial advice. Validate with a qualified accountant or finance controller before sharing or relying on the model.
