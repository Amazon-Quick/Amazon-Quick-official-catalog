# Capital Investment Cost Reference

Reference math and planning-level cost data for <Workflow - Investment Planning>.

## Time value of money

Present Worth of Revenue Requirements:

```
PWRR = Capital_Cost * CRF + sum_t ( O&M_t / (1 + r)^t )
```

Capital Recovery Factor:

```
CRF = r*(1 + r)^n / ((1 + r)^n - 1)
```

- `r` weighted average cost of capital (WACC); default 7 percent if the utility
  value is unknown, and label it as an assumption.
- `n` asset life in years (30-year evaluation period is common).

## Planning-level unit costs

These are order-of-magnitude planning figures only. Transmission costs vary by a
factor of 2 to 3 across regions (coastal, urban, and environmentally sensitive
corridors are at the high end). Per Rule 1, verify current costs against an
authoritative source (utility cost catalog, recent regulatory filing, EPRI or
EIA cost data) or ask the user for their planning-cost basis before using these
as inputs. State the year-dollar basis in every estimate.

| Item                                   | Planning-level range |
|----------------------------------------|----------------------|
| 345 kV transmission line               | $3-6M per mile       |
| 138 kV transmission line               | $1.5-3M per mile     |
| 345/138 kV autotransformer             | $8-15M each          |
| 138/69 kV transformer                  | $3-6M each           |
| Substation expansion (new bay)         | $2-5M                |
| Distribution feeder reconductoring     | $0.5-1.5M per mile   |

## Estimating discipline

- Apply a 15 to 25 percent contingency factor for planning-level estimates
  (default 20 percent).
- Apply regional multipliers where known.
- Report 5-year projects with specific costs, 10-year projects with plus/minus
  30 percent ranges, and 20-year needs as programmatic spending levels.

## Solution alternatives to weigh per need

- Reconductoring: raise thermal rating in an existing corridor.
- New line construction: new corridor, possibly higher voltage.
- Transformer addition or replacement: raise substation capacity.
- Storage: defer traditional wires investment.
- Demand-side management: reduce load growth at the constrained location.

Rank investments by year of need (earliest first), then by severity (highest
overload first). Flag "least regret" investments that resolve multiple needs.
