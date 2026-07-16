# Charging and Electrical Specifications

Engineering reference for sizing chargers, modeling coincident demand, and assessing
distribution transformer capacity. Values marked "verify" change over time or by
vendor and must be confirmed against a live source per Rule 1 before use in a
calculation. Physical constants, code-defined multipliers, and standard formulas
below are stable and do not require runtime lookup.

## EV charging specifications (SAE J1772 / CCS)

```
Level 1 (AC): 120V, 12-16A, 1.4-1.9 kW
  Use case: emergency/trickle only; NOT suitable for fleet operations
  Charge rate: ~4-5 miles of range per hour

Level 2 (AC): 208-240V, up to 80A, 7.2-19.2 kW (per SAE J1772)
  Typical fleet installation: 7.7 kW (32A@240V) or 11.5 kW (48A@240V)
  High-power L2: 19.2 kW (80A@240V)
  Charge rate: 15-65 miles of range per hour
  Connector: SAE J1772 (Type 1) or NACS
  Circuit requirement: 40A-100A breaker (125% continuous load, NEC 625.41)

DCFC (DC Fast Charge): 200-1000V DC, 50-350 kW
  50 kW: 150-200 miles per hour of charge
  150 kW: 400-600 miles per hour of charge
  350 kW: 800+ miles per hour of charge (limited by vehicle acceptance rate)
  Connector: CCS1 (Combined Charging System) or NACS
  Circuit requirement: dedicated 480V 3-phase service
```

## Coincident demand model

Fleet charging demand is NOT (number_of_vehicles * charger_kW). The coincident
demand factor accounts for staggered arrivals, varying state of charge (SOC) on
arrival, and charge completion.

```
P_coincident(t) = sum over v of [P_charger(v) * active(v, t)]

  active(v, t) = 1 if vehicle v is plugged in AND SOC(v, t) < SOC_target at time t
  SOC(v, t)    = SOC_arrival(v) + (P_charger(v) * hours_charging(v, t)) / E_battery(v)
  SOC_arrival(v) = 1 - (daily_miles(v) / range_at_full_charge(v))

Coincidence factor (CF):
  CF = P_coincident_peak / (N_vehicles * P_charger_rated)

  Typical values (verify against a current load-shape source such as the EPRI EV
  Load Shape Library before treating as authoritative):
    Overnight depot (8hr dwell, L2):    CF = 0.3-0.5
    Daytime opportunity (1-2hr, DCFC):  CF = 0.6-0.8
    Staggered shifts:                   CF = 0.2-0.4
```

## Stochastic arrival/departure model

Monte Carlo simulation of fleet charging load profiles. numpy is available in the
sandbox; no third-party solver is needed.

```
For each vehicle:
  arrival_time ~ Normal(mu=shift_end, sigma=15min)
  daily_miles  ~ LogNormal(mu=avg_daily, sigma=0.2*avg_daily)
  SOC_arrival  = max(0.1, 1 - daily_miles / rated_range)
  energy_needed  = (1 - SOC_arrival) * battery_capacity_kWh
  charge_duration = energy_needed / charger_power_kW

Aggregate: sum active chargers at each 15-min interval across n_simulations
Output: P10, P50, P90 demand profiles
```

## Charger sizing algorithm

```
For each vehicle class in fleet:
  1. energy_per_day = daily_miles / efficiency_mi_per_kWh
  2. available_charge_hours = dwell_time * 0.9 (10% buffer for connection/queue)
  3. min_charger_power = energy_per_day / available_charge_hours
  4. Select charger level:
       min_charger_power <= 7.7 kW  -> Level 2 (32A)
       min_charger_power <= 11.5 kW -> Level 2 (48A)
       min_charger_power <= 19.2 kW -> Level 2 (80A)
       min_charger_power >  19.2 kW -> DCFC required

Number of shared chargers:
  N_chargers = ceil(N_vehicles * energy_per_day_total
               / (charger_kW * available_hours * utilization_target))
  utilization_target = 0.65-0.75 (balances cost vs queuing)

Charger-to-vehicle ratio guidelines:
  Overnight depot (L2):            1:1 to 1:1.5
  Opportunity charging (DCFC):     1:4 to 1:8
```

## Distribution transformer loading model (IEEE C57.91)

```
Load_existing(t) = existing facility demand profile [kW]
Load_EV(t)       = coincident EV charging demand [kW]
Load_total(t)    = Load_existing(t) + Load_EV(t)
U(t)             = Load_total(t) / Transformer_kVA_rating

Thermal limits (IEEE C57.91-2011):
  Normal loading:            U <= 1.0 continuous
  Short-term emergency:      U <= 1.3 for up to 4 hours (with reduced life)

Hottest-spot temperature rise:
  theta_H = theta_ambient + delta_theta_oil_rise * (U^2)^n + delta_theta_winding * U^(2*m)
  n = 0.8 (ONAN), m = 0.8
  Critical threshold: theta_H = 110C (normal life expectancy point)

Accelerated aging factor:
  F_AA = exp((15000/383) - (15000/(theta_H + 273)))
  F_AA = 1.0 at rated hottest-spot (110C)
  F_AA > 1.0 means accelerated aging
  F_AA ~ 2.0 at ~117C (life consumed at 2x rate)

Available headroom for EV:
  P_available = Transformer_kVA - max(Load_existing) - safety_margin (10-20%)
  If P_available < P_EV_coincident_peak:
    Upgrade required, OR managed charging to stay within limits
```
