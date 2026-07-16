# Lithium-Ion Degradation Model

Equations and parameters for projecting capacity fade. Read this when configuring
degradation (workflow step BESS.4) and running the annual aging loop (step BESS.5).
The deterministic math is implemented in scripts/degradation.py and
scripts/rainflow.py. Parameters below are literature ranges for orientation only:
per Rule 0, confirm the values you use against a cell datasheet, published paper,
or measured test data and cite the source in the deliverable.

## Superposition

Total capacity loss is the sum of calendar and cycle aging:

```
Q_loss_total(t) = Q_loss_calendar(t) + Q_loss_cycle(t)
Q_remaining(t)  = 1.0 - Q_loss_total(t)
```

## Calendar aging (SEI growth, Arrhenius)

The solid-electrolyte interphase film grows with square-root-of-time kinetics
driven by temperature. Calendar aging accumulates whether or not the battery
cycles; it does not pause when the battery is idle.

```
Q_loss_calendar(t) = A_cal * exp(-Ea_cal / (R * T)) * exp(alpha * SOC) * sqrt(t)

A_cal   pre-exponential factor, fitted from accelerated aging tests
Ea_cal  SEI activation energy [J/mol]. Literature range: 24,000-30,000 for NMC,
        28,000-35,000 for LFP
R       universal gas constant = 8.314 J/(mol*K)
T       cell operating temperature [K] (self-heating plus ambient, not ambient alone)
alpha   SOC acceleration factor (roughly 0.5-1.5 for NMC, lower for LFP)
t       time [days]
```

NMC = nickel manganese cobalt oxide. LFP = lithium iron phosphate.

## Cycle aging (rainflow plus Wohler curve)

Cycle life versus depth-of-discharge (DoD) follows a Wohler (S-N) relationship:

```
N_failure(DoD) = a * DoD^(-b)
```

Literature ranges: NMC around a = 2000, b = 1.7 (chemistry and conditions move a
between 1000 and 3000); LFP around a = 5000, b = 1.5. Manufacturer cycle-life
claims assume controlled lab conditions, so real-world fade is commonly 20 to 40
percent faster; carry that as an explicit uncertainty band.

Extract cycles from the SOC time series with the four-point rainflow method
(ASTM E1049-85) in scripts/rainflow.py, then accumulate damage by Palmgren-Miner:

```
D_i = count_i / N_failure(DoD_i)
Q_loss_cycle = sum(D_i)          (failure at sum = 1.0)
```

## Annual projection loop

```
for year y in 1..project_life:
    cal = calendar_loss over y*365 days at the operating T and SOC
    cyc = cumulative Palmgren-Miner damage through year y
    Q_remaining(y) = 1.0 - cal - cyc
    usable_energy(y) = E_rated * Q_remaining(y) * usable_soc_range
    if Q_remaining(y) < 0.70:   # end of economic life
        trigger augmentation or project end
```

## Validation checks

- A 25 C, 50 percent SOC calendar-only run over 10 years should land near 15 to 20
  percent fade for NMC. If it does not, the parameters are wrong; do not proceed.
- High SOC at high temperature is punishing for NMC: 100 percent SOC at 35 C can
  fade 3 to 4 times faster than 50 percent SOC at 25 C.

## Augmentation

For projects beyond 10 years, model adding cells mid-life to restore capacity.
Augmentation cost depends on future cell prices: apply a learning-curve decline
(commonly 10 to 15 percent cost reduction per doubling of cumulative production),
and confirm the current cell-price basis against a live source per Rule 0.

## Source literature

- Schmalstieg et al. (2014), holistic aging model for Li(NiMnCo)O2 18650 cells,
  Journal of Power Sources.
- Wang et al. (2014), cycle-life model for graphite-LiFePO4 cells, Journal of
  Power Sources.
- Xu et al. (2018), modeling of lithium-ion battery degradation for cell life
  assessment, IEEE Transactions on Smart Grid.
- ASTM E1049-85, standard practices for cycle counting in fatigue analysis.
