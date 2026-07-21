# Solar PV Methodology (PVWatts-equivalent)

All numeric coefficients below are physical model constants (transposition geometry,
temperature physics) that do not change over time. Any market or regulatory value
(costs, incentives, grid limits) must instead be verified live per Rule 0.

## Plane of Array (POA) irradiance

- POA = beam_POA + diffuse_POA + ground_reflected_POA
- beam_POA = DNI * cos(angle_of_incidence)
- angle_of_incidence = f(solar_zenith, solar_azimuth, tilt, surface_azimuth)
- Isotropic diffuse: diffuse_POA = DHI * (1 + cos(tilt)) / 2
- Ground reflection: reflected_POA = GHI * albedo * (1 - cos(tilt)) / 2
- Default albedo: 0.2 (grass), 0.6 (snow), 0.12 (urban)
- Simplified monthly approximation for latitude tilt:
  POA ~ GHI * (1 + 0.034 * cos(2*pi*(month-1)/12))

## Cell temperature and temperature derate

- T_cell = T_ambient + (POA / 800) * (T_NOCT - 20)
- T_NOCT (Nominal Operating Cell Temperature) = 45 C for standard modules
- Temperature coefficient gamma = -0.004 /C (typical crystalline silicon)
- Temperature derate factor = 1 + gamma * (T_cell - 25)
- Temperature derate is significant above 25 C average; do not skip in hot climates.

## Power output

- P_dc = POA/1000 * capacity_kW * temperature_derate * soiling * mismatch * shading
- P_ac = P_dc * inverter_efficiency * wiring_losses * transformer_losses
- Clipping: if P_dc > inverter_rating, P_ac = inverter_rating (DC/AC ratio > 1.0 clips)

## Net annual energy and lifetime forecast

- E_year1 = sum(P_ac * hours) over all time steps
- E_yearN = E_year1 * (1 - degradation_rate)^(N-1)
- Capacity_factor_AC = E_year1 / (capacity_kW * 8760)
- Report capacity factor as AC (net) unless the user asks for DC.

## System loss stack (defaults; adjust to site-measured values when available)

| Loss factor | Default | Notes |
|---|---|---|
| Soiling | 2% | Arid 3-5%, humid 1-2% |
| Shading | 3% | 0% if unshaded |
| Module mismatch | 2% | Manufacturing tolerance |
| DC wiring | 2% | Function of string length |
| Connections | 0.5% | - |
| Inverter efficiency | 96% (4% loss) | Weighted CEC efficiency, modeled separately |
| AC wiring | 1% | - |
| Transformer | 1% | Utility-scale |
| Light-induced degradation (LID) | 1.5% | First-year effect |
| Nameplate rating | 1% | - |
| Availability | 3% | Curtailment plus maintenance |

Losses are multiplicative, not additive. Total derate is typically 14-16%.
Annual degradation (default 0.5%/year, crystalline silicon) is applied to the
lifetime forecast, not inside the year-1 loss stack.

## Reference implementation (numpy + stdlib only; no scipy)

```python
import numpy as np

losses = {
    "soiling": 0.02, "shading": 0.03, "mismatch": 0.02, "dc_wiring": 0.02,
    "connections": 0.005, "inverter": 0.04, "ac_wiring": 0.01,
    "transformer": 0.01, "lid": 0.015, "nameplate": 0.01, "availability": 0.03,
}
temp_derate = 1 + (-0.004) * (avg_cell_temp - 25)
total_derate = temp_derate
for pct in losses.values():
    total_derate *= (1 - pct)

net_energy_year1 = gross_energy_kwh * total_derate
capacity_factor_ac = net_energy_year1 / (capacity_kw * 8760)

degradation_rate = 0.005
annual_production = [
    {"year": n, "energy_mwh": net_energy_year1 * (1 - degradation_rate) ** (n - 1) / 1000}
    for n in range(1, project_life + 1)
]
```

## Fixed tilt vs tracking

- Default: latitude tilt, south-facing in the northern hemisphere, fixed mount.
- Single-axis tracking increases yield roughly 15-25% versus fixed tilt. Always
  ask the user about mounting type.
