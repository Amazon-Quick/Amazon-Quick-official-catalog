# Financial Model

How to assemble the pro-forma and compute returns. Read this during the financial
build (workflow step BESS.6). The metrics (net present value, internal rate of
return, payback, levelized cost of stored energy) are implemented in
scripts/financial.py. Every price, rate, tax parameter, and benchmark used here is
time-sensitive: confirm it against a live source per Rule 0 before use.

## Acronyms

- NPV: net present value. IRR: internal rate of return.
- LCOS: levelized cost of stored energy.
- WACC: weighted average cost of capital (the discount rate; not cost of equity alone).
- ITC: investment tax credit. MACRS: modified accelerated cost recovery system (depreciation).
- LMP: locational marginal price. TOU: time-of-use.

## Cash flow series

All outputs use nominal dollars unless stated otherwise.

```
Year 0: capital = P_bess * cost_per_kW + E_bess * cost_per_kWh + balance_of_system
        + interconnection    (entered as a negative cash flow)

Year y in 1..N:
    revenue(y) = stacked_revenue(y) * (1 - revenue_fade_from_degradation(y))
    opex(y)    = fixed_O&M + variable_O&M * throughput(y) + augmentation_cost(y)
    tax(y)     = ITC(y) + MACRS_depreciation(y) * tax_rate
    cash_flow(y) = revenue(y) - opex(y) + tax(y)
```

Feed [year0_capital, cash_flow(1), ... cash_flow(N)] to scripts/financial.py:
npv(WACC, flows), irr(flows), payback_year(flows). Compute LCOS with lcos(capital,
opex_by_year, discharged_by_year, WACC).

## Revenue streams

Energy arbitrage:
```
revenue_arb = sum over t of (discharge(t)*LMP_high(t) - charge(t)*LMP_low(t))
```

Demand-charge reduction (uses the single highest true-interval peak, not average):
```
monthly_savings = (peak_original - peak_with_BESS) * demand_charge_rate [$/kW]
annual_savings  = sum of monthly_savings over 12 months
```
Demand-charge ratchets mean one month's failure to shave can set a floor for up to
11 following months; model ratchet provisions explicitly.

Capacity market:
```
revenue_capacity = enrolled_MW * clearing_price [$/MW-day] * availability * 365
```

Frequency regulation:
```
revenue_reg = capacity_MW * reg_clearing_price * hours_available * performance_score
```
Performance reflects response speed, accuracy, and mileage. Mileage varies widely
by independent system operator; fast-response products cycle the battery harder and
accelerate degradation, so charge the degradation cost back against the revenue.

## Incentives

- Standalone storage and paired solar plus storage can qualify for the ITC.
- Apply MACRS depreciation over its statutory schedule against the tax basis.
- The ITC percentage, eligibility rules, and depreciation schedule change with
  legislation and IRS guidance. Confirm the current values from an authoritative
  source (see references/data-sources.md) before applying them. Do not rely on a
  remembered percentage.

## ITC qualification for paired systems

Charge accounting matters. Grid-charged energy above the disqualifying share of
annual throughput can void ITC eligibility, so optimize the charge schedule to keep
solar-charged energy above the required threshold. Confirm the current threshold
from a live source rather than assuming a fixed percentage.

## Sensitivity

Run at least plus or minus 20 percent on capital cost, electricity price, and
degradation rate, and report the swing in NPV, IRR, and payback. Transformer and
interconnection costs can add 10 to 25 percent to project cost and are often omitted
from screening; include them.

## Benchmarking

Compare LCOS against the current-year Lazard levelized cost of storage report
(see references/data-sources.md). Do not quote a remembered figure.
