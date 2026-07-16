# Load Growth Forecasting Methods

Reference math for <Workflow - Load Growth Forecasting>. All models are fit with
numpy and pandas in run_python (no scipy or statsmodels in the sandbox; use
`numpy.linalg.lstsq` for regression and closed-form curve fits).

## Econometric method

Correlates load with economic drivers via log-linear regression:

```
ln(D_t) = b0 + b1*ln(GDP_t) + b2*ln(Price_t) + b3*ln(Pop_t) + b4*CDD_t + b5*HDD_t + e_t
```

- `D_t`   electricity demand in year t
- `GDP_t` real gross domestic product
- `Price_t` average retail electricity price
- `Pop_t` population or customer count
- `CDD_t`, `HDD_t` cooling / heating degree days (weather normalization)
- `bi` elasticity coefficients, estimated by ordinary or generalized least squares

Typical elasticities: income elasticity `b1` about 0.3 to 0.7; price elasticity
`b2` about -0.1 to -0.5. Confirm current elasticities against an authoritative
source per Rule 1 before treating them as inputs; do not hardcode them as facts.

## End-use method

Bottom-up aggregation by appliance or process:

```
D_t = sum_j ( N_j_t * Sat_j_t * UEC_j_t * LF_j )
```

- `j` end-use category (HVAC, lighting, industrial motors, EV charging, etc.)
- `N_j_t` number of customers or units in category j at time t
- `Sat_j_t` saturation rate (fraction of customers with this end-use)
- `UEC_j_t` unit energy consumption (kWh/year per unit)
- `LF_j` load factor (peak contribution)

## Trending method

Extrapolation of historical growth:

```
D_t = D0 * (1 + g)^t                 exponential
D_t = D0 + m*t                       linear
D_t = K / (1 + exp(-r*(t - t0)))     logistic / saturation
```

Compound annual growth rate from history:

```
g = (D_recent / D_base)^(1/n) - 1
```

Fit exponential, linear, and logistic curves; select the best by adjusted R^2.

## Weather normalization

Compute CDD and HDD (base 65 F) for each year, regress peak demand against
CDD/HDD to isolate weather effects, then normalize historical peaks to
50th-percentile weather (or 90/10 design weather).

## Scenario construction

- Base: best-fit model with central assumptions.
- High: base plus incremental load from electrification (EVs, heat pumps), data
  centers, or known large loads.
- Low: base minus energy efficiency gains, distributed generation
  self-consumption, and demand response.

If a scenario driver is unavailable, fall back to plus/minus one standard error
of the regression as the high/low bounds. Forecast uncertainty grows roughly as
sqrt(t); treat 10-year and 20-year values as scenario ranges, not predictions.
