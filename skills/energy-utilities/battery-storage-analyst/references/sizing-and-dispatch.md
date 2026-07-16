# Capacity Sizing and Dispatch

Guidance for sizing a battery energy storage system (BESS) and scheduling its
charge and discharge. Read this during sizing (workflow step BESS.3) and dispatch
(step BESS.5).

## Sandbox note: no linear-programming solver

The Amazon Quick Python sandbox provides numpy and pandas but no linear-programming
or mixed-integer solver (no scipy.optimize, pulp, cvxpy, or ortools) and `pip
install` is blocked. Do not claim to run a linear program. Size and dispatch with
the numpy-based deterministic methods below, which give the same answer for the
threshold-and-schedule structure of these problems. State this method choice in
the deliverable so results are reproducible. When a true linear or mixed-integer
program is warranted (for example complex multi-stream revenue stacking), use a
coding agent such as Kiro via ACP in Quick on desktop to install pulp, cvxpy, or
ortools and run the optimization outside the sandbox.

## Peak shaving sizing

The optimal power rating for demand-charge reduction is the gap between the
historical peak and the target peak the customer holds:

```
P_bess = P_peak_historical - P_target
P_peak_historical = max(load) over the billing period at the true meter interval
E_bess = sum over t of max(load(t) - P_target, 0) * dt   (energy above the target line)
```

Sizing uses the critical month approach:

1. For each month, find the peak event: the contiguous intervals above P_target.
2. Required energy is the area above P_target during the deepest and longest event.
3. Adjust for round-trip efficiency and usable state-of-charge (SOC) range:
   `E_rated = E_bess / (round_trip_efficiency * usable_soc_range)`.
4. Choose P_target that maximizes (demand-charge savings minus annualized BESS cost).

Because the objective is one-dimensional and monotonic in structure, sweep or
binary-search P_target over the feasible range with numpy rather than a solver.
Evaluate each candidate against the whole load series, keep the best net-benefit
target. Demand charges use the single highest true-interval reading in the billing
period, never the monthly average.

## Duration by application

- Peak shaving: duration set by the critical peak event, often 2 to 4 hours.
- Time-of-use (TOU) arbitrage: duration matched to the priced spread window.
- Frequency regulation: symmetric power capacity, typically 15 to 30 minutes.
- Combined: size to the binding constraint across enabled streams, then verify
  each stream is still served.

## Dispatch and revenue stacking

Revenue stacking is not additive. The battery cannot serve two streams with the
same power in the same interval, so co-optimize: for each interval assign power to
its highest-value use given the opportunity cost of the alternatives, subject to:

```
sum of stream power(t) <= P_bess                       (power limit)
SOC(t+1) = SOC(t) + charge(t)*eta - discharge(t)/eta   (energy balance)
SOC_min <= SOC(t) <= SOC_max                            (SOC bounds)
sum of |delta_SOC(t)| over the year <= throughput_budget(year)  (degradation budget)
reg_reservation(t) <= min(SOC(t)-SOC_min, SOC_max-SOC(t)) * E_rated / dt
```

Implement as a greedy per-interval allocation with a forward SOC pass in numpy,
then a check that the annual throughput stays within the degradation budget from
references/degradation-model.md. If infeasible, drop the lowest-value stream and
re-run. Sequential single-stream optimization overstates total revenue by roughly
15 to 40 percent, so never sum independently optimized streams.

## Solar plus storage

For paired photovoltaic (PV) plus BESS systems the sizing is interdependent. pvlib
is not in the sandbox, so build the PV profile from first principles or from a
user-supplied production series:

```
P_pv(t) = capacity * GHI(t)/1000 * temperature_derating * inverter_efficiency
P_net(t) = load(t) - P_pv(t)
```

Size the BESS against the net load profile, not the raw load. The battery absorbs
solar clipping, shifts generation to the evening peak, and cuts the net demand
peak that sets demand charges. Investment tax credit (ITC) qualification for
paired charging is covered in references/financial-model.md.
