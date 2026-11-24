---
description: "How to keep a baseline, resume a scan and get approval for scheduling, used only when the user asks for persistence or monitoring."
last_updated: 2026-11-22
---
# State and automation

Use only when the user requests persistence, resumption, delta monitoring, or scheduling.

## Baseline

Prefer an accessible user-controlled file or supported persistent store. Confirm the destination before writing. Store only methodology version, scan timestamp/scope, stable source IDs, update timestamps when available, normalized finding keys, scores, and coverage. Do not store formulas, connection strings, tokens, owner details, or full payloads unless explicitly needed.

Validate a baseline before reuse. If methodology versions differ, report the incompatibility and rescan rather than presenting a false delta.

## Resume

Resume only from a baseline that identifies the requested scope and completed stable IDs. Re-inventory first. A prior permission failure is not permanent: avoid repeated retries within one run, but allow a later run to test current access once.

## Scheduling authorization

Before using an automation capability, confirm exact scope/site, cadence and timezone, alert condition, baseline destination, and that the user wants creation now. Use the automation tool's current schema; explain unsupported fields instead of inventing them.

The scheduled prompt must be portable: name the skill, scope, mode, comparison method, reporting threshold, and failure behavior. Never embed local paths. An unattended run must not prompt for choices; if authentication or required capabilities are unavailable, report failure without mutating Tableau.

