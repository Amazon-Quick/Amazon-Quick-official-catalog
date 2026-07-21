# Financial Methodology (LCOE and project economics)

Levelized cost of energy (LCOE) is the discounted lifetime cost per unit of
discounted lifetime energy. Cost benchmarks change every year and MUST be verified
live per Rule 0 against the sources in references/authoritative-sources.md. The
formulas below are stable; the input values are not.

## Capital Recovery Factor (CRF)

- CRF = r * (1 + r)^n / ((1 + r)^n - 1)
- r = real weighted average cost of capital (WACC), typically 5-8% for renewables
- n = project lifetime (25-35 years solar, 20-30 years wind)

## LCOE

Full net present value (NPV) method (preferred):

```
LCOE = SUM_t[ C_t / (1+r)^t ] / SUM_t[ E_t / (1+r)^t ]
  C_t = annual costs in year t (CAPEX in year 0, O&M in years 1..n)
  E_t = E_year1 * (1 - degradation)^(t-1)
  r   = real discount rate,  t = 0..n
```

Report LCOE in $/MWh (or the local currency equivalent). Present it as a P25-P75
range reflecting resource uncertainty, not a single point, unless site-measured data
supports high confidence.

Plausible ranges to sanity-check results against (verify current values live before
quoting them): utility solar roughly $25-60/MWh, onshore wind roughly $30-70/MWh,
offshore wind roughly $70-150/MWh. If a result falls outside its band, check units:
the most common error is mixing $/kW-DC with $/kW-AC or nominal with real WACC.

## Uncertainty and P-values

- P50: median (expected case)
- P75: 75% exceedance (conservative, common for debt sizing)
- P90: 90% exceedance (stress case)
- combined_sigma = sqrt(resource_unc^2 + model_unc^2 + measurement_unc^2)
- P75 = P50 * (1 - 0.674 * combined_sigma)
- P90 = P50 * (1 - 1.282 * combined_sigma)
- Inter-annual variability: 2-5% solar, 5-10% wind.
- Never present a generation estimate without stating its P-value.

## Reference implementation (numpy + stdlib only; no scipy, no numpy_financial)

```python
import numpy as np

def npv(rate, cashflows):
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))

def irr(cashflows, lo=-0.9, hi=2.0, tol=1e-7, iters=200):
    """Solve IRR by bisection. numpy.irr was removed and numpy_financial is not
    available in the Quick sandbox, so bracket the root manually."""
    f_lo = npv(lo, cashflows)
    if f_lo * npv(hi, cashflows) > 0:
        return None  # no sign change in the bracket
    for _ in range(iters):
        mid = (lo + hi) / 2
        f_mid = npv(mid, cashflows)
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2

# LCOE (full NPV)
capex_total = capex_per_kw * capacity_kw
fixed_om_annual = fixed_om_per_kw * capacity_kw
r, n, d = discount_rate, project_life, degradation_rate

npv_costs = capex_total + sum(fixed_om_annual / (1 + r) ** t for t in range(1, n + 1))
npv_energy_mwh = sum(
    (net_energy_year1 / 1000) * (1 - d) ** (t - 1) / (1 + r) ** t for t in range(1, n + 1)
)
lcoe = npv_costs / npv_energy_mwh  # $/MWh

# CRF cross-check (should be within ~5% of the NPV LCOE)
crf = r * (1 + r) ** n / ((1 + r) ** n - 1)
lcoe_crf = (capex_total * crf + fixed_om_annual) / avg_annual_energy_mwh

# Project cashflows at a PPA price
cashflows = [-capex_total] + [
    (net_energy_year1 / 1000) * (1 - d) ** (t - 1) * ppa_price - fixed_om_annual
    for t in range(1, n + 1)
]
project_irr = irr(cashflows)
project_npv = npv(r, cashflows)
simple_payback = capex_total / ((net_energy_year1 / 1000) * ppa_price - fixed_om_annual)
```

## Required financial assumptions to state in every report

Discount rate (WACC), project life, debt/equity split, and tax treatment
(investment tax credit percentage, production tax credit $/MWh, or none). LCOE does
not capture the time-value of energy: a project at $40/MWh producing mostly during
low-price hours can be worth less than one at $45/MWh.
