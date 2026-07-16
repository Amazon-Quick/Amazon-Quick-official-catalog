# Fracture Treatment Diagnostics

Reference detail for the Nolte-Smith and G-function workflows. Read the relevant
section before running the corresponding analysis.

## Nolte-Smith Pressure Analysis

Log-log plot of net fracturing pressure vs time to identify fracture propagation
modes (Nolte and Smith, 1981).

Net pressure:

```
P_net = BHP_treating - P_closure
BHP   = surface_pressure + hydrostatic - friction_losses
```

Propagation modes by log-log slope (e = d[log(P_net)] / d[log(t)]):

- **Mode I, Normal Fracture Extension (confined height):** slope e between 0.125
  and 0.25 (about 1/4 for PKN, 1/5 for KGD). Net pressure rises slowly as the
  fracture extends in length. Stable propagation within the target interval.
- **Mode II, Height Growth or Pressure Stabilization:** slope e near 0 (flat net
  pressure). The fracture met a barrier and grows laterally at constant width, or
  height growth into a lower-stress zone relieves pressure. Equilibrium between
  extension and leak-off.
- **Mode III, Restricted Extension or Screen-out approaching:** slope e between
  0.5 and 1.0 (steepening). Tip resistance rising, fracture widening faster than
  extending. Rising proppant concentration at the tip. Action: reduce proppant
  concentration or increase rate.
- **Mode IV, Uncontrolled Height Growth:** slope e negative (net pressure
  falling). Fracture breaking into a low-stress zone above or below target, poor
  containment. Action: reduce rate, consider a diverter, evaluate zone isolation.

Pressure derivative technique (Ayoub et al., 1992): plot `t * (dP_net/dt)` vs
time on log-log. It shares the net-pressure slope but amplifies changes, so it is
more sensitive to mode transitions than pressure alone.

Practical implementation:

1. Convert surface pressure to bottomhole pressure (BHP):
   `BHP = Ps + 0.052*MW*TVD - Pf_pipe - Pf_perf - Pf_NWB`.
2. Estimate closure stress from a Diagnostic Fracture Injection Test (DFIT), a
   Leak-Off Test (LOT), or offset data.
3. `P_net = BHP - P_closure`.
4. Plot log(P_net) vs log(t_pump) during treatment.
5. Compute the running slope e.
6. Classify propagation mode from the slope value.

Reference slope-to-mode bands used by scripts and workflow steps:

- `0.125 <= e <= 0.33` -> Mode I: Normal Extension
- `-0.1 <= e < 0.125` -> Mode II: Height Growth / Stabilization
- `e > 0.5` -> Mode III: Restricted / Screen-out Risk
- `e < -0.1` -> Mode IV: Uncontrolled Height Growth
- otherwise -> Transitional

## G-Function Analysis for DFIT

The G-function (Nolte, 1979) is a time transform for analyzing pressure decline
after fracture shut-in.

G-function (PKN geometry, constant injection rate):

```
delta_tD = delta_t / tp          (dimensionless shut-in time, tp = pumping time)
g(delta_tD) = (1 + delta_tD)^1.5 - delta_tD^1.5      (low leak-off)
G(delta_tD) = (4/pi) * [ g(delta_tD) - g(0) ]
```

At large shut-in times, G is approximately proportional to sqrt(shut-in time).
Cumulative leak-off volume after shut-in is proportional to G, so P vs G is a
straight line when fracture compliance and leak-off rate are constant.

Closure pressure identification:

- Plot P vs G (Castillo plot). Departure from the straight line marks closure.
- Plot the superposition derivative `G * dP/dG` vs G. During ideal leak-off it is
  constant (horizontal); a downward bend marks closure.
- Closure pressure (Pc) is the pressure at the departure point.

Non-ideal signatures:

- **Pressure-dependent leak-off (PDL):** `G*dP/dG` shows a hump above the straight
  line at early G. Natural fractures opening near the wellbore raise leak-off.
- **Fracture tip extension:** `G*dP/dG` concave upward at very early time. The
  fracture is still growing after shut-in from stored energy.
- **Multiple closure events:** multiple inflection points, complex networks
  closing in sequence.

Instantaneous Shut-In Pressure (ISIP):

- ISIP is the pressure immediately after pumps stop, extrapolated to zero shut-in
  time (not the first recorded shut-in reading).
- `Net ISIP = ISIP - Pc` indicates fracture width and net pressure at end of
  treatment. High ISIP relative to Pc indicates good fracture geometry.
- Stress shadow across stages: `Delta_sigma = ISIP_stage_n - ISIP_stage_1`.
  Rising ISIP across stages suggests stress-shadow buildup, typically 50 to 200
  psi between adjacent stages in unconventionals.

Interpretation frameworks (Castillo, Barree, McClure) can yield different closure
pressures on the same dataset. Always state which method was used.
