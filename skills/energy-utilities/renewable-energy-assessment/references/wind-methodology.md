# Wind Methodology (Weibull + power curve)

All coefficients here are physical model constants. Market and cost values must be
verified live per Rule 0.

## Weibull wind speed distribution

- f(v) = (k/c) * (v/c)^(k-1) * exp(-(v/c)^k)
- k = shape parameter (typically 1.5-3.0; k=2 is the Rayleigh distribution)
- c = scale parameter (m/s), related to mean speed: c = v_mean / Gamma(1 + 1/k)
- Mean wind speed from Weibull: v_mean = c * Gamma(1 + 1/k)

The Amazon Quick sandbox does not provide scipy, so fit the distribution with the
method of moments using numpy and the stdlib `math.gamma`, not `scipy.stats`.

## Wind shear correction (power law)

- v_hub = v_measured * (h_hub / h_measured)^alpha
- alpha = shear exponent: 0.14 open terrain, 0.20 suburban, 0.30 urban, 0.10 offshore
- Shear varies by time of day (stable nighttime air has higher shear). Use measured
  shear when available rather than the default.

## Air density and wind power density

- rho = 1.225 kg/m3 at sea level, 15 C
- Altitude correction: rho = 1.225 * (1 - 2.256e-5 * elevation)^5.256
- Wind power density: WPD = 0.5 * rho * v^3 (W/m2)

## Simplified power curve (cubic ramp region)

- P(v) = 0 for v < v_cutin (typically 3-4 m/s)
- P(v) = P_rated * (v^3 - v_cutin^3) / (v_rated^3 - v_cutin^3) for v_cutin <= v <= v_rated
- P(v) = P_rated for v_rated < v <= v_cutout (typically 25 m/s)
- P(v) = 0 for v > v_cutout

## Capacity factor

- CF = integral[ f(v) * P(v) dv ] / P_rated
- Typical ranges: onshore 25-45%, offshore 35-55%.
- Offshore has higher capacity factors but much higher CAPEX and O&M. Never apply
  onshore cost or loss assumptions to offshore projects.

## Reference implementation (numpy + stdlib only; no scipy)

```python
import numpy as np
import math

# Fit Weibull by method of moments (exclude calm periods, account for them separately)
speeds = wind_speeds[wind_speeds > 0]
mean, std = speeds.mean(), speeds.std()
k = (std / mean) ** -1.086          # empirical estimator, valid ~1 <= k <= 10
c = mean / math.gamma(1 + 1 / k)

# Wind shear to hub height
alpha, h_hub, h_meas = 0.14, 80.0, 10.0
v_hub_scale = (h_hub / h_meas) ** alpha  # multiply speeds or scale c

# Expected power via numerical integration over a speed grid
grid = np.linspace(0.001, 30, 3000)     # start above 0 to avoid div-by-zero when k<1

def power_curve(x, p_rated, v_cutin=3.5, v_rated=12.0, v_cutout=25.0):
    p = np.zeros_like(x)
    ramp = (x >= v_cutin) & (x < v_rated)
    p[ramp] = p_rated * (x[ramp] ** 3 - v_cutin ** 3) / (v_rated ** 3 - v_cutin ** 3)
    p[(x >= v_rated) & (x <= v_cutout)] = p_rated
    return p

pdf = (k / c) * (grid / c) ** (k - 1) * np.exp(-(grid / c) ** k)
trapz = np.trapezoid if hasattr(np, "trapezoid") else np.trapz  # numpy 2.x renamed trapz
expected_power_kw = trapz(power_curve(grid, capacity_kw) * pdf, grid)
gross_energy_kwh = expected_power_kw * 8760
capacity_factor = expected_power_kw / capacity_kw
```

Wind loss stack is typically 5-15% (wake losses, availability, electrical). Wind
degradation default is 1.6%/year per recent operating-fleet studies.
