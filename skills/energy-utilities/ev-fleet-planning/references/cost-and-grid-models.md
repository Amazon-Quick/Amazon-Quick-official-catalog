# Cost, Managed Charging, and Grid Impact Models

Reference for total cost of ownership (TCO) comparison, managed charging scheduling,
and distribution grid impact. Every price, incentive, rate, and cost band below is
time-sensitive: treat it as an order-of-magnitude placeholder and verify the current
figure against an authoritative source (see references/data-sources.md) or a
user-provided value before it enters a calculation. Formulas and unit relationships
are stable.

## Managed charging scheduling

The theoretically correct formulation is a linear program that minimizes energy plus
demand charges subject to departure-energy targets and a site power limit:

```
minimize: sum over t of [P_charge(v,t) * rate(t) * dt] + demand_charge * P_peak
subject to:
  sum over t of [P_charge(v,t) * dt] >= energy_needed(v)          for all v
  P_charge(v,t) = 0 for t outside [arrival(v), departure(v)]
  0 <= P_charge(v,t) <= P_charger_rated(v)
  sum over v of [P_charge(v,t)] + Load_existing(t) <= P_site_limit
  P_peak >= sum over v of [P_charge(v,t)] + Load_existing(t)      for all t
```

The Amazon Quick Python sandbox has numpy and pandas but NO linear-program solver
(no scipy.optimize, pulp, or cvxpy). Implement managed charging with a valley-filling
heuristic instead: sort intervals by rate(t) ascending, fill each vehicle's required
energy into its cheapest available plugged-in intervals first, and cap the site total
at P_site_limit in every interval. This captures the dominant time-of-use (TOU) and
demand-charge savings without a solver. Report it as a heuristic, not an optimum.
When a true least-cost optimum is required, use a coding agent such as Kiro via ACP
in Quick on desktop to install pulp, cvxpy, or scipy.optimize and solve the linear
program outside the sandbox.

## Total cost of ownership model

Use the same timeframe (typically 7-10 years) and discount rate for both options.

```
TCO_ICE(N) = Vehicle_cost_ICE
  + sum(Fuel_cost(y) for y=1..N)
  + sum(Maintenance_ICE(y) for y=1..N)
  + sum(Insurance_ICE(y) for y=1..N)
  - Residual_value_ICE(N)

TCO_EV(N) = Vehicle_cost_EV
  + Charger_infrastructure_cost / vehicles_per_charger
  + Electrical_upgrade_cost / fleet_size
  + sum(Electricity_cost(y) for y=1..N)
  + sum(Maintenance_EV(y) for y=1..N)
  + sum(Insurance_EV(y) for y=1..N)
  + Battery_replacement_cost (if applicable)
  - Federal/State_incentives
  - Residual_value_EV(N)

Component formulas:
  Fuel_cost(y)        = annual_miles / mpg * fuel_price(y) * (1 + fuel_escalation)^y
  Electricity_cost(y) = annual_miles / efficiency_mi_per_kWh * blended_rate(y)
                        (blended_rate reflects the TOU shift from managed charging)
  Maintenance_ICE(y)  = $0.08-0.12/mile * annual_miles (verify)
  Maintenance_EV(y)   = $0.03-0.06/mile * annual_miles (verify)
    EVs eliminate oil changes, transmission service, exhaust, belts, spark plugs.
    EVs add battery thermal management service, HV cable inspection, OTA validation.
    Regenerative braking reduces brake wear 50-70%.

Battery replacement:
  Trigger: capacity < 70% or range insufficient for duty cycle
  Cost: $100-150/kWh * battery_capacity, declining ~10%/year (verify)
  Typical timing: year 8-10 at 150,000+ miles

Charger infrastructure (installed, per port, verify):
  Level 2 (7.7 kW, networked):  $3,000-6,000
  Level 2 (19.2 kW, networked): $5,000-10,000
  DCFC (50 kW):                 $35,000-60,000
  DCFC (150 kW):                $100,000-150,000

Electrical upgrades (verify, highly site-specific):
  Panel upgrade:                 $5,000-15,000
  New transformer (500-1000 kVA):$50,000-150,000
  Utility service upgrade:       $25,000-200,000+
  Trenching/conduit:             $50-150 per linear foot
```

## Grid impact assessment

```
1. Baseline transformer loading curve (24hr profile, peak season).
2. Overlay unmanaged EV charging demand.
3. Calculate:
   - New peak demand vs transformer rating
   - Hours above 80% loading (accelerated aging zone)
   - Equivalent aging factor F_AA (IEEE C57.91; see charging-and-electrical-specs.md)
   - Years of life consumed per calendar year with EV load
4. Mitigation strategies, ranked by cost:
   a. Managed charging (shift to off-peak):   $0/kW incremental
   b. On-site solar + storage:                $200-400/kW (verify)
   c. Transformer upgrade:                     $50-150/kVA (verify)
   d. New dedicated EV service:                utility coordination required
5. Hosting capacity:
   P_hosting = P_transformer_rating - P_existing_peak - P_reserve_margin
   If P_EV_managed_peak <= P_hosting: no upgrade needed
   Else: quantify upgrade cost
```
