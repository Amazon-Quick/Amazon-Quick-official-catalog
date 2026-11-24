---
description: "Default configuration and what the engine's run() does step by step (trend and seasonality, drivers, Monte Carlo, scenarios, bridge, tornado, provenance). Read in Workflow - Run Scenario steps 7 and 8."
last_updated: 2026-11-24
---
# Method

## Configuration

Start from these defaults and change only what the user states. The engine checks every value before it simulates and asks when one is out of range (references/engine-api.md, Running).

```python
CONFIG = {
    "bear_percentile": 10,
    "base_percentile": 50,
    "bull_percentile": 90,  # scenario percentiles
    "mc_iterations": 10000,  # 1 to 1,000,000; iterations x fy_length_periods at most 20,000,000
    "poly_degree": 2,
    "detect_seasonality": True,
    "seasonality_profile": None,  # or one positive index per fiscal period, averaging about 1.0
    "driver_stage_prob": {
        "stage_1": 0.10,
        "stage_2": 0.30,
        "stage_3": 0.60,
        "stage_4": 0.90,
    },  # replace with the user's stages
    "driver_timing_sigma": 1.0,  # periods of timing uncertainty
    "target": None,  # None requires complete benchmark full-year total
    "target_direction": "at_least",  # at_most for a confirmed cap
    "units": None,  # set confirmed label, for example "USD thousands"; never guessed
    "judgment_adjustments": [],  # {"label": "Price increase Q3", "low": 0, "likely": 500000, "high": 900000, "source": "..."}
    "fy_start_period": None,  # for example "2026-04"; None aligns fiscal years to the data's first period
    "fy_length_periods": 12,  # 1 to 366
}
DRIVERS = []  # {"name", "value", "prob" or "stage", "date"}; see references/data-contract.md
```

## What run() does, in order

- **Trend and seasonality.** Linear and polynomial (degree `poly_degree`) least-squares fits; multiplicative seasonal indices estimated when there is at least one full year of history. Fit quality gate: R2 > 0.70 trend is the primary anchor; 0.50 to 0.70 lean on drivers and judgment; below 0.50 low confidence. The residual standard error becomes the trend component's distribution.
- **Drivers.** Each converts with its probability (from its stage when blank) and lands at a period drawn from a normal distribution around its date.
- **Monte Carlo.** 10,000 runs by default, drawing trend error, driver conversion and timing, seasonality, and triangular judgment ranges together. Flow: outcome = year-to-date actual + simulated remaining periods. Balance: inflows and outflows are simulated and compounded from the latest balance to a closing-balance distribution.
- **Scenarios and headline.** Bear, Base, and Bull at the configured percentiles; P(hit target) = share of runs at or above a floor (`at_least`) or at or below a cap (`at_most`), as confirmed by the user or explicit source labels. CONFIG target takes precedence; otherwise the benchmark must cover the full fiscal year. A partial benchmark is not annualized, and Base is never substituted for a target.
- **Bridge.** Benchmark (or the year-to-date actual, then "Trend projection (remaining periods)", when there is no full-year benchmark) -> Trend delta -> Driver conversion -> Seasonality -> Judgment -> Base, with a final "distribution shape" step when the P50 differs from the expected value, so the bars add up exactly.
- **Tornado.** Each assumption moved across its range on its own (trend level +/- one residual sigma over the remaining periods, seasonality off or on, each driver not converting or converting, each judgment item from low to high), ranked by swing.
- **What has to be true, provenance, areas to probe.** Conditions from the largest swings plus confirmed context; every assumption labeled DATA-BACKED, CONTEXT-INFORMED, USER-SET, or DEFAULT; open questions, unverified claims, conflicts, and default assumptions ranked P1, P2, or P3.

## Coherence rules

- **Calendar first.** Dated history is laid on a complete calendar before anything else. A missing prior-year period stays a gap: it is listed as a data limitation, excluded from the trend fit at its true position, and never interpolated. A gap in current-year actuals blocks a full-year result until the value is supplied or the user confirms zero activity for that specific period. Duplicate periods also block pending a decision about corrections, aggregation, or segment selection. The fiscal-year window and the remaining forecast periods are set by date, so a gap never pulls a period from the next fiscal year into the forecast.
- **Scenario paths.** The per-period Bear, Base, and Bull lines are each one simulated run: the run whose outcome is closest to that percentile, with the judgment draw and the last fraction of a unit placed in the final period so the run equals the scenario exactly. Per-period percentiles are not shown as paths because they do not add up to the period-total percentile.
- **Build-up.** Each scenario column shows year-to-date actual (or opening balance), trend and seasonality, drivers and judgment at their expected values, the expected total, and a distribution deviation (scenario minus expected). The columns sum to their scenarios by construction; this is not an independent reconciliation. The engine rejects non-finite build-up amounts.
- **Provenance.** Configuration (percentiles, iterations, seed, fiscal year, timing sigma, a target the user gave) is USER-SET when its value differs from the shipped default and DEFAULT otherwise, whether or not it was passed explicitly, so a stated value equal to the default shows as DEFAULT. A seasonality profile the user supplies, and the target (stated or taken from the user's own plan), are USER-SET. Seasonality that was not estimated is DEFAULT. Only estimates from the history are DATA-BACKED, and only confirmed context is CONTEXT-INFORMED.


## Input decisions before simulation

`ClarificationRequired` carries `status="needs_clarification"` and a `question`. Show the question and wait; do not convert an input failure into a forecast result. Invalid dates and nonblank numeric values never become missing values. Mixed unambiguous dates and comma thousands and parentheses negatives are parsed independently. For a selected header and explicit exclusions, source row counts are retained in `df.attrs["input_audit"]` and the report.

A complete full-year benchmark contains one finite plan value for every fiscal period (or the exact fiscal-year closing balance). An explicit target permits a run with incomplete benchmark data, but the partial benchmark is left out of the full-year bridge and the limitation is stated.
