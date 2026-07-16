# Petroleum Engineering Methods

Formulas and reference Python implementations for the Drilling Operations Analyst.
All formulas use field units (ft, psi, ppg, bbl, scf, lbf, ft-lbf) unless a metric
variant is noted. These are stable engineering relationships (physical constants and
standard industry equations); they do not change over time. Time varying values
(formation strengths, offset benchmarks, rig rates, prices, regulatory limits) are
NOT stored here and must be verified per Rule 0 in SKILL.md.

## Minimum Curvature Method

The industry standard method (SPE 84246) for computing wellbore position between two
survey stations. It models the path as a circular arc between the stations.

Given station 1 (MD1, I1, A1) and station 2 (MD2, I2, A2), where I is inclination and
A is azimuth in degrees:

```
DeltaMD = MD2 - MD1

Dogleg angle beta:
  cos(beta) = cos(I2 - I1) - sin(I1) * sin(I2) * (1 - cos(A2 - A1))
  beta = arccos(cos(beta))

Ratio factor RF:
  RF = (2 / beta) * tan(beta / 2)
  Use RF = 1.0 when beta < 0.25 degrees (arc approaches a straight line).

Position increments:
  Delta_TVD   = (DeltaMD / 2) * (cos(I1) + cos(I2)) * RF
  Delta_North = (DeltaMD / 2) * (sin(I1)*cos(A1) + sin(I2)*cos(A2)) * RF
  Delta_East  = (DeltaMD / 2) * (sin(I1)*sin(A1) + sin(I2)*sin(A2)) * RF

Dogleg severity DLS:
  DLS = beta * (100 / DeltaMD)   degrees per 100 ft
  DLS = beta * (30 / DeltaMD)    degrees per 30 m  (metric)

Vertical section along azimuth AZvs:
  VS = Delta_North * cos(AZvs) + Delta_East * sin(AZvs)

Closure distance:  HD = sqrt(North^2 + East^2)
Closure azimuth:   AZ_closure = atan2(East, North), converted to the 0 to 360 range
```

Reference implementation:

```python
import numpy as np
import pandas as pd


def minimum_curvature(surveys):
    """Calculate 3D wellbore position from survey stations.

    surveys: DataFrame with columns [MD, INC, AZ] in ft and degrees.
    Returns: DataFrame with [MD, TVD, NS, EW, DLS].
    """
    results = []
    tvd, ns, ew = 0.0, 0.0, 0.0
    for i in range(len(surveys)):
        if i == 0:
            results.append({"MD": surveys.iloc[i]["MD"], "TVD": 0, "NS": 0, "EW": 0, "DLS": 0})
            continue
        md1, i1, a1 = surveys.iloc[i - 1][["MD", "INC", "AZ"]]
        md2, i2, a2 = surveys.iloc[i][["MD", "INC", "AZ"]]
        i1r, i2r = np.radians(i1), np.radians(i2)
        a1r, a2r = np.radians(a1), np.radians(a2)
        dmd = md2 - md1
        cos_beta = np.cos(i2r - i1r) - np.sin(i1r) * np.sin(i2r) * (1 - np.cos(a2r - a1r))
        beta = np.arccos(np.clip(cos_beta, -1, 1))
        rf = 1.0 if beta < np.radians(0.25) else (2.0 / beta) * np.tan(beta / 2.0)
        tvd += (dmd / 2.0) * (np.cos(i1r) + np.cos(i2r)) * rf
        ns += (dmd / 2.0) * (np.sin(i1r) * np.cos(a1r) + np.sin(i2r) * np.cos(a2r)) * rf
        ew += (dmd / 2.0) * (np.sin(i1r) * np.sin(a1r) + np.sin(i2r) * np.sin(a2r)) * rf
        dls = np.degrees(beta) * (100.0 / dmd) if dmd > 0 else 0
        results.append({"MD": md2, "TVD": tvd, "NS": ns, "EW": ew, "DLS": dls})
    return pd.DataFrame(results)
```

## Mechanical Specific Energy (MSE)

The energy required to destroy a unit volume of rock (Teale, 1965). Used to detect
drilling dysfunction and optimize parameters.

```
Rotary drilling MSE (downhole torque available):
  MSE = (WOB / A_bit) + (120 * pi * RPM * T) / (A_bit * ROP)

  A_bit = pi * d_bit^2 / 4        bit cross-sectional area (in^2)
  WOB   = weight on bit (lbf)
  RPM   = rotary speed (rev/min)
  T     = torque at bit (ft-lbf)
  ROP   = rate of penetration (ft/hr)
  MSE   = mechanical specific energy (psi)

Simplified surface MSE (downhole torque unavailable):
  MSE = (WOB / A_bit) + (480 * RPM * T_surface) / (d_bit^2 * ROP)

Minimum (theoretical) MSE approximates the confined compressive strength (CCS):
  CCS = UCS + (sigma_c * tan^2(45 + phi/2))   from Mohr-Coulomb
```

Efficiency interpretation:

- MSE close to CCS: efficient drilling.
- MSE = 2 to 3x CCS: mild dysfunction (bit balling, poor hole cleaning).
- MSE > 3x CCS: severe dysfunction (stick-slip, whirl, vibration).

Reference implementation:

```python
import numpy as np


def calc_mse(wob_lbf, rpm, torque_ftlbf, rop_fthr, bit_dia_in):
    """Calculate downhole MSE in psi."""
    area = np.pi * bit_dia_in**2 / 4.0
    if rop_fthr <= 0:
        return np.nan
    return (wob_lbf / area) + (120 * np.pi * rpm * torque_ftlbf) / (area * rop_fthr)
```

Dysfunction signatures:

- High MSE, low ROP, normal torque: bit balling or poor hole cleaning.
- High MSE, erratic torque: stick-slip.
- High MSE, poor WOB transfer: buckling or friction (common in deviated wells).

## Cost Per Foot (CPF)

```
Per bit run:
  CPF = (Bit_Cost + Rig_Rate * (Trip_Time + Drilling_Time)) / Footage_Drilled

Full well:
  CPF_total = Total_AFE / Total_MD

Normalized (benchmarking), by hole section (surface, intermediate, production):
  CPF_normalized = Section_Cost / Section_Length
```

Separate tangible costs (bits, casing, cement) from intangible costs (rig rate,
services, fuel). AFE means Authorization For Expenditure.

## Mud Weight Window

The safe operating envelope between pore pressure (lower bound) and fracture gradient
(upper bound), in equivalent mud weight (ppg).

```
Pore pressure emw:     PP_emw = P_pore / (0.052 * TVD)
Fracture gradient emw: FG_emw = P_frac / (0.052 * TVD)
Overburden emw:        OBG_emw = P_overburden / (0.052 * TVD)

Eaton fracture gradient:
  FG = (v / (1 - v)) * (OBG - PP) + PP     v = Poisson's ratio

Kick tolerance:
  KT = FG_at_shoe - (PP_at_interest + Delta_P_annular) * (TVD_shoe / TVD_interest)

Minimum mud weight = PP_emw + 0.5 ppg   (trip margin)
Maximum mud weight = FG_emw - 0.5 ppg   (surge margin)
Operating window   = Max_MW - Min_MW
```

Reference implementation:

```python
def mud_weight_window(pp_ppg, fg_ppg, trip_margin=0.5, surge_margin=0.5):
    """Return (min_mw, max_mw, window) in ppg."""
    min_mw = pp_ppg + trip_margin
    max_mw = fg_ppg - surge_margin
    return min_mw, max_mw, max_mw - min_mw
```

Set casing where the window narrows below about 0.5 ppg before reaching the next
section total depth. The trip and surge margins (0.5 ppg) are conventional defaults;
confirm the operator's drilling program values before use.

## Non-Productive Time (NPT)

Time during operations that does not advance well construction.

IADC standard categories:

1. Equipment failure (rig, BOP, pumps, top drive)
1. Stuck pipe / fishing
1. Lost circulation
1. Well control (kicks, BOP tests beyond scheduled)
1. Wellbore instability (packoffs, wiper trips, reaming)
1. Weather / waiting on weather
1. Waiting on orders / decisions
1. Cement / remedial cementing
1. Directional drilling problems (motor failures, survey issues)
1. Other

```
NPT ratio:  NPT% = NPT_hours / Total_hours * 100

Invisible lost time (ILT) for a repeated operation:
  ILT = Actual_time - Best_demonstrated_time
Measured against P10 performance from offset wells.
```

## Rate of Penetration (ROP) Models

```
Bourgoyne-Young (8 parameter):
  ln(ROP) = a1 + a2*(10000 - TVD) + a3*(TVD^0.69)*(gp - 9.0)
            + a4*(TVD*(gp - rho_c)) + a5*ln(WOB/d_bit - (WOB/d_bit)_threshold)
            + a6*ln(RPM) + a7*(-a8*Ah)
  a1 to a8 are empirically fit coefficients; gp is pore pressure gradient (ppg);
  rho_c is equivalent circulating density (ppg); Ah is a tooth wear function.

Bingham (simpler):
  ROP = K * (WOB/d_bit)^a * RPM^b     K, a, b are formation-dependent constants.
```

## Portfolio Benchmarking Statistics

- Days-vs-depth curves normalized to spud date (day 0) and compared section by section
  (surface, intermediate, curve, lateral), with NPT excluded for a clean curve.
- P10, P50, P90 performance curves (days to depth by section).
- Learning curve fit: Time_n = Time_1 * n^(-b), where b is the learning rate and n is
  the well sequence number.

## Reference Standards

- SPE 84246: Directional calculations based on the minimum curvature method
  (Sawaryn and Thorogood, 2005).
- SPE 208777: Standardization of mechanical specific energy equations and nomenclature
  (2023).
- Teale, R. (1965): The concept of specific energy in rock drilling. Int. J. Rock Mech.
  Mining Sci.
- Bourgoyne, A.T. et al.: Applied Drilling Engineering, SPE Textbook Series Vol. 2.
- Mitchell, R.F. and Miska, S.Z.: Fundamentals of Drilling Engineering, SPE Textbook
  Series Vol. 12.
- IADC Drilling Manual, 12th Edition: NPT classification and reporting standards.
