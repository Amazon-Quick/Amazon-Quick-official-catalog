# Resilience and Financial Metrics

Implement in `run_python`. Physics and accounting formulas below are stable.
Every price, incentive rate, tax credit, discount rate, fuel escalation rate,
and benchmark used in the financial model changes over time and MUST be verified
from a source this session or supplied by the user (Rule 2 in SKILL.md). Do not
plug in the illustrative ranges as if they were current.

## Resilience Metrics

### Hours of Autonomy

```
Given an outage starting at hour t_start lasting D hours:
  For each hour t in [t_start, t_start + D]:
    Available = P_pv(t) + P_battery_discharge(t) + P_genset(t)
    System survives if Available >= Critical_load(t) for all t in the outage.

Hours of autonomy = maximum D the system serves critical load, from worst case:
  Winter night (no solar, battery at minimum reserve SOC).
  Battery-only:     autonomy = E_battery * usable_SOC / Critical_load_avg
  Battery + genset: autonomy = fuel_tank_capacity / fuel_consumption_rate
```

### Loss of Load Expectation (LOLE)

```
LOLE = expected days per year where load exceeds available generation.

Monte Carlo:
  For n_simulations = 1000:
    For each hour t = 1 to 8760:
      Sample availability of each resource against its forced outage rate (FOR):
        PV_available     = PV_output(t)  if rand() > PV_FOR      else 0
        Genset_available = P_rated       if rand() > Genset_FOR  else 0
        Battery_available= P_battery     if rand() > Battery_FOR else 0
        Grid_available   = P_grid        if rand() > grid_outage_prob else 0
      If sum(available) < Load(t): loss_of_load_hours += 1
  LOLE = loss_of_load_hours / n_simulations / 24   [days/year]

Typical forced outage rates (verify against equipment data if available):
  PV 2 to 5%, Genset 5 to 15%, Battery 1 to 3%, Grid 0.1 to 2% (utility SAIDI/SAIFI).

Target LOLE:
  Grid-scale:                       0.1 days/year (1 day in 10 years)
  Commercial/campus:                0.5 to 2.0 days/year
  Critical infrastructure:          under 0.01 days/year
```

### Renewable Fraction

```
RF = (E_solar_consumed + E_battery_discharged_from_solar) / E_total_load_served
```

- E_solar_consumed: solar used directly by load (not exported or curtailed).
- E_battery_discharged_from_solar: battery energy originally charged by solar,
  tracked via solar-content accounting in the battery.
- Grid or genset energy reduces RF. The battery is a pass-through and inherits
  the source of its charge. Charging losses mean only 86 to 90% of stored solar
  reaches the load.

## Financial Model

### Net Present Cost (NPC)

```
NPC = C_capital
    + sum(C_annual(y)      / (1 + r)^y for y = 1..N)
    + sum(C_replacement(y) / (1 + r)^y for replacement years)
    - C_salvage / (1 + r)^N

C_capital = PV_kW * cost_per_watt_PV * 1000
          + Battery_kWh * cost_per_kWh_battery
          + Genset_kW * cost_per_kW_genset
          + balance_of_system + interconnection + engineering

C_annual(y) = Fuel_cost(y) + O&M_PV(y) + O&M_battery(y) + O&M_genset(y)
            + Grid_electricity_cost(y) - Grid_export_revenue(y)

Fuel_cost(y) = annual_fuel_liters * diesel_price(y) * (1 + fuel_escalation)^y

C_replacement:
  Battery around year 10 to 12
  Genset overhaul at operating-hour intervals
  Inverter around year 12 to 15

C_salvage = remaining component value at project end (linear depreciation):
  Salvage = C_original * (life_remaining / total_life)
```

### Levelized Cost of Energy (LCOE)

```
LCOE = NPC / sum(E_served(y) / (1 + r)^y for y = 1..N)   [USD/kWh]
  r = real discount rate (nominal minus inflation)
  N = project lifetime (typically 20 to 25 years)
```

Do not embed benchmark LCOE ranges as current. Fetch current generation and
storage benchmarks from an authoritative source (see `references/data-sources.md`)
before comparing a design against grid-only or diesel-only baselines.

Apply incentives only after verifying current eligibility and rates from an
authoritative source: investment tax credit, standalone-storage credit, and
accelerated depreciation schedules all change by jurisdiction and year.
