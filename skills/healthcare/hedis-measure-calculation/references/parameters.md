---
description: "Reference table of default parameter values such as measurement year, gap days, lookback, and percentile used across the skill's HEDIS calculation examples."
last_updated: 2026-09-13
origin: original
---

# Parameter Reference

Default parameter values used across the calculation examples and what they mean.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `measurement_year` | Current calendar year | HEDIS reporting year |
| `max_gap_days` | 45 | Maximum allowable enrollment gap |
| `anchor_date` | Dec 31 of measurement year | Date member must be enrolled through |
| `dx_lookback_years` | 2 | Years to look back for qualifying diagnoses |
| `threshold_percentile` | 95 | Percentile cutoff for high-cost identification |
| `readmission_window` | 30 | Days after discharge for readmission flag |

Resolve `measurement_year` to a concrete four-digit year with get_current_time before writing date logic; do not leave it relative.
