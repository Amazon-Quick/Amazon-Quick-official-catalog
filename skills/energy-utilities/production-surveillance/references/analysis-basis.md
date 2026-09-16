---
description: "Assumptions, synthetic thresholds, golden outputs, and evidence limits used by the production-surveillance workflows."
last_updated: 2026-09-15
origin: original
---

# Production Surveillance Analysis Basis

All values in this reference are synthetic and intended for skill evaluation only. They are not operating limits, certified models, or evidence about a real asset.

## Golden scenario values

| Item | Expected value |
| --- | ---: |
| Fixture wells | 27 |
| Fixture gas rate | 1,004 MMscf/d |
| SK-14 current gas rate | 22 MMscf/d |
| SK-14 potential gas rate | 38 MMscf/d |
| SK-14 current temperature | 15.7 degC |
| Uninhibited hydrate equilibrium | 19.94 degC |
| Inhibited hydrate equilibrium at 21.5 wt% aqueous MEG | 14.22 degC |
| Signed scenario margin | +1.48 degC |
| Hydrate risk band | `HIGH` |
| Current 16 MMscf/d deferral at $3.50/MMBtu and 1,050 BTU/scf | $58,800/day |
| Full 38 MMscf/d well exposure at the same assumptions | $139,650/day |
| Proposed external handoff | Evaluate MEG injection from 2.1 to 3.5 m3/hr through the operating team's approved process |
| Field actions executed by this skill | 0 |

Current deferral and full-well exposure are separate scenarios. Neither is an avoided-loss claim.

## Hydrate method

`run_petrophysics.py` uses a fixture-calibrated lean-gas correlation:

```text
T_uninhibited_degC = -74.78 + 11.243 * ln(pressure_psi)
```

It applies Hammerschmidt monoethylene glycol (MEG) depression using aqueous-phase MEG weight percent. A volumetric injection rate in m3/hr cannot be converted to aqueous-phase weight percent without a water-condensation and mixing model. The skill must not calculate a post-change hydrate margin from a proposed volumetric rate.

The script defines the signed scenario margin as current temperature minus inhibited equilibrium temperature. Positive means the fixture temperature is above the inhibited curve. The script-owned bands are `FORMING` below 0 degC, `HIGH` from 0 to less than 3 degC, `MODERATE` from 3 to less than 6 degC, and `LOW` at 6 degC or more.

## Reservoir screening basis

The fixture analyzer estimates flowing bottomhole pressure from tubing pressure with a static gas-column approximation. It reports `fbhp_basis: estimated_static_column`; it is not a downhole gauge value or nodal model.

Synthetic thresholds:

- critical drawdown: 3,000 psi;
- sand advisory: 1.0 pounds per trillion Btu (pptb);
- water-cut screening limit: 15 percent;
- average gas compressibility factor: 0.90;
- drawdown utilisation below 80 percent is `PASS`, 80 to 100 percent is `CAUTION`, above 100 percent is `BLOCK`;
- a proposed increase is `BLOCK` when sand utilisation is 80 percent or greater.

Water-cut and sand history are not present in the daily history operation. Their trend basis is limited to the one-minute reading window.

## Safety screening basis

Synthetic thresholds:

- maximum allowable annulus surface pressure (MAASP): 2,500 psi;
- high-integrity pressure protection system (HIPPS) trip pressure: 6,000 psi;
- utilisation below 80 percent is `PASS`, 80 to 100 percent is `CAUTION`, above 100 percent is `BLOCK`.

Missing barrier inputs produce `UNKNOWN` or `CAUTION`, never an inferred safe result. Active alarms are the only precedent source. There is no incident archive, closed-event history, approval history, or measured outcome history.

## Economics basis

Every price and heating-value assumption must be supplied in the request and repeated in the output. The golden scenario uses $3.50/MMBtu and 1,050 BTU/scf. The script does not fetch market prices.

## Well-log calculation basis

The bundled SK-14 and SK-22 LAS 2.0 files under `evals/files/` are synthetic. They use `WRAP.NO`, `NULL.-999.25`, metre depth, GAPI gamma ray, V/V neutron porosity, G/CC bulk density, US/FT sonic, inch caliper, and OHMM deep induction resistivity. The reader maps ILD to canonical RT and converts depth from metres to feet for `net_pay`.

Use these synthetic reservoir intervals with inclusive reader bounds that preserve the original upper-exclusive formation selection:

- SK-14: 3980 through 4099 m MD, 120 source rows.
- SK-22: 3850 through 3974 m MD, 125 source rows.

The committed calculation sequence and constants are:

- `density_porosity`: matrix density 2.65 G/CC and fluid density 1.0 G/CC.
- `shale_volume`: clean gamma ray 20 GAPI and shale gamma ray 120 GAPI.
- `effective_porosity`: density porosity and shale volume from the prior steps.
- `archie_water_saturation`: canonical RT, the calculated effective porosity supplied as `total_porosity_fraction`, water resistivity 0.04 OHMM for SK-14 or 0.05 OHMM for SK-22, and Archie `a=1.0`, `m=2.0`, `n=2.0`.
- `net_pay`: porosity minimum 0.06, water saturation maximum 0.60, and shale volume maximum 0.40.

Rows with JSON null in any curve required by a calculation are excluded as an aligned set and counted. Do not interpolate them. These constants reproduce a synthetic demonstration sequence and are not field-calibrated interpretation parameters.

## Professional review

Outputs are informational scenario analysis only. A qualified production, reservoir, flow-assurance, process-safety, and regulatory professional must validate source data, models, limits, and procedures before any real-world action.
