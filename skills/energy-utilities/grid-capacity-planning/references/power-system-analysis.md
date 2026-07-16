# Power System Analysis: Sensitivity Factors, Contingencies, Hosting Capacity

Reference math for the hosting capacity, N-1 contingency, and transfer
capability workflows. All linear algebra runs in run_python with numpy.

## Sandbox reality for power flow

There is no dedicated power-system solver in the Quick sandbox. `pandapower`,
`PyPSA`, and `scipy` are NOT available, and `pip install` is blocked. Build the
DC network matrices and sensitivity factors directly with numpy:

- Bus susceptance matrix `Bbus` from branch reactances and the incidence matrix.
- Invert with `numpy.linalg.inv` (dense) after removing the slack row and column,
  or solve with `numpy.linalg.solve` for a single injection pattern.

Full AC power flow is not provided as a library. To validate DC results with AC,
either implement a Newton-Raphson solver in numpy for the specific case, or have
the user supply AC power-flow results exported from their planning tool
(PSS/E, PowerWorld, pandapower run outside Quick, etc.). Do not claim AC results
that were not actually computed (Rule 1). When a full solver is required, use a
coding agent such as Kiro via ACP in Quick on desktop to install pandapower,
PyPSA, or scipy and run the analysis outside the sandbox.

## Power Transfer Distribution Factors (PTDF)

Fraction of a transfer (inject at bus i, withdraw at bus j) that flows on branch k:

```
PTDF(k, i->j) = (X_im - X_in - X_jm + X_jn) / x_k
```

- `X` = bus reactance matrix = inv(B) with slack row/col removed
- `m, n` = from-bus and to-bus of branch k
- `x_k` = series reactance of branch k

Matrix form:

```
PTDF = diag(1/x) @ A.T @ inv(B)
```

- `A` branch-bus incidence matrix (branches x buses)
- `B` nodal susceptance matrix (slack row/col removed)

For a transfer of dP MW from bus i to bus j: `dFlow_k = PTDF(k, i->j) * dP`.

The slack bus PTDF is zero by definition. Removing the slack row/column before
inversion is mandatory; skipping it produces a singular matrix.

## Line Outage Distribution Factors (LODF)

Fraction of pre-outage flow on branch l that shifts to branch k when l trips:

```
LODF(k, l) = PTDF(k, m->n) / (1 - PTDF(l, m->n))
```

where m, n are the from/to buses of the outaged branch l.

Post-contingency flow: `Flow_k_post = Flow_k_pre + LODF(k, l) * Flow_l_pre`.

LODF is undefined when `1 - PTDF(l, m->n)` approaches 0 (the outage islands the
branch). Detect this and flag the contingency as islanding rather than dividing.

## N-1 contingency screening

```
for l in contingency_list:
    for k in monitored_branches (k != l):
        flow_post = flow_base[k] + LODF[k, l] * flow_base[l]
        loading_pct = abs(flow_post) / emergency_rating[k] * 100
        if loading_pct > 100: flag violation
```

N-0 (intact system) uses the normal rating; N-1 (post-contingency) uses the
emergency rating, typically 10 to 15 percent above normal for limited duration.

Performance Index for ranking contingencies:

```
PI_l = sum_k (Flow_k_post / Rating_k)^(2n)     n = 1 or 2
```

Higher n emphasizes severe overloads. Rank by PI to focus detailed AC study on
the worst cases. DC screening carries 5 to 10 percent error versus AC; validate
binding constraints before investment decisions.

Definitions: N-1 = loss of any single element. N-1-1 = two sequential losses
(NERC TPL Category C). N-2 = simultaneous double contingency. Do not conflate them.

## Available Transfer Capability (ATC)

Per NERC MOD standards:

```
ATC = TTC - TRM - ETC - CBM
```

- `TTC` Total Transfer Capability: max transfer without violating reliability
  criteria under N-1.
- `TRM` Transmission Reliability Margin: uncertainty allowance, typically 2 to 5
  percent of TTC.
- `ETC` Existing Transmission Commitments: firm and non-firm committed uses.
- `CBM` Capacity Benefit Margin: reserved for generation reliability (LOLE-based),
  often 0 on many paths.

Never omit TRM or CBM. If ATC < 0 the path is fully committed or constrained.

TTC via sensitivity factors:

```
TTC = min over branches k of (Rating_k - Flow_k_base) / PTDF(k, source->sink)   [N-0]
TTC = min over k, l of (Emergency_Rating_k - Flow_k_post_l) / PTDF_post_k       [N-1]
TTC = min(N-0 limit, N-1 limit)
```

Distribute injection pro-rata among source buses and withdrawal pro-rata among
sink buses. ATC is a snapshot; always state the study conditions (peak/off-peak,
season, year).

## Hosting capacity for distributed energy resources (DER)

Hosting capacity (HC) is the maximum DER penetration a feeder can accommodate
without violating operating limits:

```
HC = min(HC_thermal, HC_voltage, HC_protection, HC_power_quality)
```

Voltage limits follow ANSI C84.1: plus/minus 5 percent on a 120 V base
(0.95 to 1.05 pu).

Voltage-limited HC (from the power-flow Jacobian sensitivity dV/dP):

```
HC_voltage = (V_max - V_no_DER) / (dV/dP)     [MW]
```

Thermal-limited HC:

```
HC_thermal = Rating_MVA - Existing_Flow_MVA               [MVA, forward]
HC_thermal = Rating_MVA + Existing_Load_MVA               [MVA, reverse flow]
```

Iterative method used in practice:

```
p_der = 0
step  = feeder_peak / 50          # ~2% of peak load
while True:
    p_der += step
    # add DER at bus, run power flow
    # check: 0.95 <= V <= 1.05 pu, all branch loading <= 100%, protection ok
    if any_violation:
        HC = p_der - step; break
    if p_der > 2 * feeder_peak:
        HC = p_der; break          # practical upper bound
```

Classify the limiting factor per bus: thermal, voltage, protection, or reverse
flow (backfeed at the substation exceeds protection settings).

HC depends heavily on DER power factor: unity power factor is most conservative;
smart inverters at 0.9 leading raise voltage-limited HC. Do not assume all DER
runs at nameplate simultaneously; apply coincidence factors (solar about 0.7 to
0.85 of nameplate at the peak production hour).

## Substation loading

```
Loading% = S_actual / S_rated * 100          S_actual = sqrt(P^2 + Q^2)  [MVA]
Loading%_N-1 = S_total / ((N_transformers - 1) * S_rated_each) * 100
```

IEEE C57.91 thermal aging acceleration:

```
Aging_Factor = exp( (15000/383) - (15000/(Theta_HS + 273)) )
```

`Theta_HS` = hottest-spot temperature (C). Aging factor = 1.0 at the rated
hottest-spot of 110 C.
