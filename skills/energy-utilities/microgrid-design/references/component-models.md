# Component Models: Solar PV, Battery, Diesel Genset

Implement these in `run_python` with numpy and pandas. The formulas below are
stable engineering physics and may be used directly. Any numeric coefficient
that drifts with hardware selection or market conditions (temperature
coefficients for the chosen module, actual round-trip efficiency, fuel curve
constants, current fuel price) must come from the datasheet, the user, or a
source verified this session, per Rule 2 in SKILL.md. The typical ranges shown
are for sanity checks, not values to plug in unverified.

## Solar PV Production Model

pvlib is not available in the sandbox. Either implement the geometry below with
numpy, or fetch a production profile from an authoritative solar-resource
service (see `references/data-sources.md`). When full pvlib fidelity is required,
use a coding agent such as Kiro via ACP in Quick on desktop to install pvlib and
execute the code outside the sandbox.

```
For each hour t:
  1. Solar position: zenith, azimuth = solar_position(latitude, longitude, t)

  2. Plane-of-array irradiance:
     POA = beam * cos(AOI) + diffuse_sky + diffuse_ground
     where AOI = angle of incidence on the tilted surface

  3. Cell temperature (Sandia model):
     T_cell = T_ambient + POA * exp(a + b * wind_speed) + POA/1000 * delta_T
     Open-rack glass/cell/glass: a = -3.56, b = -0.075

  4. DC power:
     P_dc = P_stc * (POA/1000) * (1 + gamma * (T_cell - 25))
       P_stc = nameplate DC capacity [kW]
       gamma = module temperature coefficient [%/C], verify from datasheet
               (crystalline silicon is typically -0.35 to -0.45)

  5. AC power:
     P_ac = P_dc * inverter_efficiency(P_dc / P_inverter_rated)
     Inverter efficiency is typically 96 to 98% at 20 to 100% loading

  6. Annual degradation:
     P_ac(year_y) = P_ac(year_1) * (1 - degradation_rate)^(y-1)
     Typical: 0.5%/year (mono-Si), 0.7%/year (poly-Si)
```

Apply year-1 soiling, shading, and wiring losses (typically 14 to 18% total
system losses). Capacity factor = annual_kWh / (kW_installed * 8760).

## Battery Dispatch Model

```
SOC(t+1) = SOC(t) + P_charge(t) * eta_charge * dt / E_rated
                  - P_discharge(t) * dt / (E_rated * eta_discharge)

Constraints:
  SOC_min <= SOC(t) <= SOC_max
  0 <= P_charge(t)    <= P_max_charge
  0 <= P_discharge(t) <= P_max_discharge
  P_charge(t) * P_discharge(t) = 0     (no simultaneous charge/discharge)

Resilience reserve (grid-connected mode, if islanding is required):
  SOC(t) >= SOC_resilience_reserve at all times
  SOC_resilience_reserve = critical_load_kW * hours_of_autonomy_required / E_rated

Round-trip efficiency:
  eta_roundtrip = eta_charge * eta_discharge
  Typical: LFP 86 to 90%, NMC 88 to 92%
  Split: eta_charge = sqrt(eta_roundtrip), eta_discharge = sqrt(eta_roundtrip)
```

Battery replacement timing is driven by throughput and calendar aging. For
20-year projects, budget one replacement around year 10 to 12.

## Diesel Genset Model

```
Fuel consumption (linear approximation):
  F(t) = F0 * P_rated + F1 * P_output(t)   [liters/hour]
    F0 = no-load coefficient (typically 0.08 L/hr per kW_rated)
    F1 = marginal coefficient (typically 0.25 L/hr per kW_output)

  Efficiency at partial load:
    eta_genset = P_output / (F(t) * LHV_diesel / 3600)
    LHV_diesel = 35.8 MJ/liter = 9.94 kWh/liter
    Typical: 33% at full load, 25% at 50% load, under 20% at 25% load

Operational constraints:
  P_output(t) >= P_min_loading * P_rated   (minimum loading, typically 30%)
  P_output(t) <= P_rated
  If P_output(t) < P_min_loading while running: raise load (charge battery) or shut down.

  Startup cost: 10 to 50 USD per start (wear, fuel preheat)
  Minimum runtime: 30 to 60 minutes once started (thermal cycling)

Maintenance:
  Oil change every 250 to 500 operating hours
  Major overhaul every 10,000 to 15,000 hours
  Budget 0.02 to 0.05 USD/kWh generated
```
