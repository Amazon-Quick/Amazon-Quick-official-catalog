# Optimization Methodology and Dispatch Strategies

This file holds the three-stage optimization method and the two dispatch strategies referenced by the main workflow. Implement all math in `run_python` using numpy and pandas. There is no HOMER, SAM, or pvlib package in the Amazon Quick sandbox; these names describe methodology, not tools you can import.

## Three-Stage Optimization: Enumerate, Simulate, Rank

### Stage 1: Enumerate feasible configurations

```
For PV_capacity in [0, 50, 100, 200, 500, 1000, ...] kW:
  For Battery_kWh in [0, 100, 200, 500, 1000, 2000, ...] kWh:
    For Genset_kW in [0, 50, 100, 200, 500, ...] kW:
      For Grid_connection in [True, False]:
        If configuration meets the minimum reliability threshold:
          Add to feasible set
```

Search-space reduction (prune before simulating):
- PV upper bound: 2 * annual_load / (capacity_factor * 8760)
- Battery upper bound: 3 days of autonomy * daily_load_kWh
- Genset upper bound: peak_load * 1.2 (allows starting transients)
- Drop configurations that obviously violate constraints before simulating.

Target 50 to 200 candidate configurations for full simulation. If the space is larger, screen coarsely, then refine increments around the optimum.

### Stage 2: Simulate 8,760-hour dispatch for each candidate

```
For each hour t = 1 to 8760:
  Apply dispatch strategy (load-following or cycle-charging)
  Record: energy served, unserved energy, fuel consumed, battery SOC, grid flows

Annual metrics:
  total energy served, unserved energy
  fuel consumption (liters diesel)
  battery throughput (kWh cycled)
  grid import/export (kWh)
  renewable fraction achieved
  hours of unserved energy
```

### Stage 3: Rank by net present cost

```
For each feasible configuration that passes constraints:
  NPC  = Capital + NPV(fuel + O&M + replacements) - NPV(salvage) - NPV(grid_export_revenue)
  LCOE = NPC / NPV(total_energy_served)

Sort by NPC ascending. Report the top 3 to 5 with a trade-off analysis.
```

The full NPC and LCOE formulas are in `references/metrics.md`.

## Dispatch Strategies

### Load-Following (LF)

```
Priority order when serving load:
  1. Solar PV (use all available, zero marginal cost)
  2. Battery discharge (if SOC > SOC_min_operating)
  3. Grid import (if grid-connected and cheaper than genset)
  4. Diesel genset (last resort, highest marginal cost)

Battery charging priority:
  1. Excess solar (free energy)
  2. Grid during off-peak time-of-use periods (if grid-connected)
  3. Genset does NOT charge battery in load-following mode

When solar > load:
  1. Charge battery (up to max charge rate and SOC_max)
  2. Export to grid (if allowed and compensated)
  3. Curtail the remainder
```

### Cycle-Charging (CC)

Same as load-following, except when the genset runs it operates at full rated
capacity: it serves load and charges the battery with excess capacity, because
genset efficiency is highest at full load.

```
Genset activation threshold:
  Start when SOC < SOC_genset_start (for example 30%)
  Stop  when SOC > SOC_genset_stop  (for example 80%)
```

This reduces genset runtime (fewer starts) but raises fuel per start event.
Prefer it for remote sites with expensive fuel delivery, where genset starts
carry high wear cost.
