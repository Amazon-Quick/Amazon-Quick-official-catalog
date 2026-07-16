# Completion Economics and Spacing

Reference detail for the completion economics, spacing optimization, and fleet
workflows.

## Completion Economics

Estimated Ultimate Recovery (EUR) per dollar invested:

```
EUR/$  = EUR [bbl or mcf] / Total_Completion_Cost [$]
NPV/$  = NPV_production_revenue / Total_Completion_Cost   (preferred)
```

Total completion cost breakdown:

```
C_total = C_perf + C_plug + C_pump + C_proppant + C_chemical
        + C_water + C_drillout + C_flowback
```

- `C_perf`: perforation charges plus wireline runs
- `C_plug`: composite or dissolvable plug costs
- `C_pump`: pumping horsepower charges (typically $/hhp/hr)
- `C_proppant`: sand or ceramic cost ($/ton) times total mass
- `C_chemical`: friction reducer, gel, surfactant, biocide
- `C_water`: source water plus hauling plus disposal
- `C_drillout`: coiled tubing or drill-out operations
- `C_flowback`: equipment rental plus hauling during flowback

Incremental value of a design change:

```
Delta_NPV  = NPV(design_B) - NPV(design_A)
Delta_Cost = Cost(design_B) - Cost(design_A)
ROI        = Delta_NPV / Delta_Cost
```

The change is economic when `Delta_NPV > Delta_Cost`.

Net Present Value (NPV) at the specified discount rate is the primary economic
metric. Cost comparisons must account for both capital (completion cost) and
production value (EUR times price).

Proppant and fluid intensity normalization (required for cross-field comparison):

```
Proppant_lbs_per_ft = Total_proppant_lbs / Lateral_length_ft
Fluid_bbl_per_ft    = Total_fluid_bbl / Lateral_length_ft
Stages_per_1000ft   = Stage_count / (Lateral_length_ft / 1000)
Clusters_per_stage  = Total_clusters / Stage_count
```

Marginal economics of intensification: the EUR-to-proppant relationship is
typically logarithmic, not linear. The optimum loading is where marginal EUR
value equals marginal cost. Do not linearly extrapolate beyond the data range.

## Stage and Cluster Spacing Optimization

Stress-based stage spacing: rule of thumb `spacing = 2 * x_f` (half-length) for no
interference. Practical optimum: the spacing where incremental EUR from tighter
spacing falls below incremental cost.

Fracture half-length estimation (PKN model):

```
x_f = [ (qi * E' * tp) / (2 * pi * h_f * C_L^2 * (1 - v^2)) ]^(1/4) * correction
```

Where qi = injection rate per stage (bbl/min), E' = plane strain modulus =
E/(1-v^2), tp = pump time per stage (min), h_f = fracture height (ft),
C_L = leak-off coefficient (ft/sqrt(min)).

Cluster spacing:

- Minimum spacing for stress shadow to dissipate: about 3x fracture height /
  Poisson ratio.
- Typical cluster spacing in unconventionals: 20 to 60 ft.
- Cluster efficiency (producing clusters / total clusters) is typically 40 to 70
  percent. Do not assume 100 percent cluster contribution in spacing math.
- If cluster efficiency is below 50 percent, consider tighter spacing with fewer
  clusters per stage.

Limited entry perforation design:

```
Q_cluster    = Cd * n_perfs * A_perf * sqrt(2 * Delta_P_perf / rho_slurry)
Delta_P_perf = 0.2369 * rho_slurry * Q^2 / (n_perfs^2 * d_perf^4 * Cd^2)
```

Where Cd = discharge coefficient (0.56 to 0.90), A_perf = pi * d_perf^2 / 4,
Q in bpm, d_perf in inches, rho in ppg. Design for more than 500 psi perforation
friction differential for uniform distribution. Maximum entry holes per cluster:
typically 2 to 6 for limited entry.

## Frac Fleet Scheduling

Fleet efficiency metrics:

```
Pump_time_%      = actual_pump_hours / (total_hours - planned_maintenance)
Stage_per_day    = stages_completed / calendar_days_on_location
Zipper_efficiency = stages_pumped / (stages_pumped + transitions)
```

Time components per stage: pump time (1.5 to 3 hr), wireline plug and perf (0.5 to
2 hr), well-to-well transition for zipper (0.5 to 1 hr), non-productive time (NPT:
equipment, wellbore, weather), and idle time (waiting on water, sand, decisions).

Per-stage cost model:

```
C_stage = HP_rate * pump_hours + wireline_rate + plug_cost + perf_cost
        + proppant_tons * $/ton + fluid_bbl * $/bbl + chemical_cost
```

Zipper frac advantage: eliminates rig-up and rig-down between wells, enables
offset pressure monitoring while pumping, and typically yields 20 to 40 percent
more stages per day than conventional. It requires a multi-well pad with
simultaneous access, and simultaneous operations (SIMOPS) on tight spacing require
pressure monitoring of offset wells during treatment.
