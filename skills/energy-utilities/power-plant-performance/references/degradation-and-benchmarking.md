# Degradation Trending and Benchmarking

Reference for the degradation trending and benchmarking workflows.

## Degradation signatures

Recoverable, short-term (compressor fouling, recovered by online/offline wash):
```
dP_output ~= -2% to -5% between washes (6-12 month cycle)
dHR       ~= +50-150 BTU/kWh
```
Signature: reduced mass flow, reduced pressure ratio, increased exhaust
temperature at the same firing temperature.

Recoverable at major maintenance (hot gas path wear, seal clearance growth,
steam path deposits):
```
dP_output ~= -2% to -4% over a 24,000-48,000 EOH interval
dHR       ~= +50-100 BTU/kWh
```
Signature: increased exhaust temperature spread, reduced turbine efficiency.

Non-recoverable (permanent material degradation, coating loss, profile change):
```
dP_output ~= -0.5% to -1% per major inspection interval
dHR       ~= +20-40 BTU/kWh (cumulative)
```
Addressed by component replacement or uprate.

"Equivalent Operating Hours" (EOH) is not calendar hours. EOH counts starts
(each start adds N equivalent hours) and load cycling. Use EOH, not calendar
hours, for GT and combined-cycle degradation trending.

## Degradation trending method

1. Correct all performance data to ISO conditions (see thermodynamic-models.md).
2. Remove non-steady-state periods (starts, shutdowns, load ramps, trips).
3. Filter to baseload operation only (> 85-90% of rated output).
4. Remove outliers (> 3 sigma from a rolling mean).
5. Plot corrected heat rate vs time (or equivalent operating hours).
6. Fit a linear regression and read the slope as the degradation rate.
7. Compare to the expected rate for the technology and vintage.

Regression without scipy (scipy is not in the Quick sandbox; use numpy):
```python
import numpy as np
months = np.arange(len(hr_corrected_monthly))
y = np.asarray(hr_corrected_monthly, dtype=float)
slope, intercept = np.polyfit(months, y, 1)          # BTU/kWh per month
fit = np.polyval([slope, intercept], months)
ss_res = float(np.sum((y - fit) ** 2))
ss_tot = float(np.sum((y - y.mean()) ** 2))
r_squared = 1 - ss_res / ss_tot if ss_tot else float("nan")
degradation_rate_per_year = slope * 12
```
Trending requires a minimum of 6 months of corrected data; 2+ years is
preferred. Do not draw conclusions from uncorrected short-term fluctuations.
Correct for ambient first, then trend the corrected values: trending
uncorrected data in a seasonal climate produces a sawtooth that hides the real
degradation signal.

## Cost of degradation
```
annual_cost = dHR * generation_MWh * fuel_cost_per_MMBTU / 1000
```
Verify the fuel price from a live source or user input before using it.

## Benchmarking scoring

For each KPI, percentile rank = (fleet units worse than this plant) / total
fleet units. Composite score is a weighted average of percentile ranks:
heat rate 40%, EFOR 30%, capacity factor 20%, starting reliability 10%.

Traffic-light rating: Green above the 75th percentile, Yellow 25th-75th, Red
below the 25th percentile.

Improvement ranking: for each KPI, compute the annual dollar value of closing
the gap to the fleet median, rank by dollars per year, and map each to a
concrete physical action (maintenance, upgrade, or operational change).

Always note the comparison population. Comparing a 1970s subcritical coal unit
to a "coal fleet average" that includes modern supercritical units is
misleading.
