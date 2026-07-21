# Emission Factors, GWP Values, and Calculation Formulas

Rule 0 governs this file: **do not treat any numeric value below as current without
verifying it against its cited authoritative source during the session.** The values
here are reference defaults with provenance. Factors that change over time (grid
rates, annually updated hub factors, market prices) MUST be fetched at runtime with
`url_fetch` or `web_search` from the sources named below. Stable values derived from
fuel chemistry change rarely but still require citing the source year.

As of July 2026, the current editions are: **eGRID 2023** (released January 2025, Rev 2 June 2025) and **EPA GHG Emission Factors Hub 2025** (January 2025).

## Global Warming Potentials (IPCC AR5, 100-year)

Use these unless the user specifies a different assessment report.

| Gas | GWP |
|---|---|
| CO2 | 1 |
| CH4 | 28 |
| N2O | 265 |

Source: IPCC AR5, Chapter 8, Table 8.A.1.

## Stationary combustion (kg per unit)

Source: EPA 40 CFR Part 98 Table C-1 and the EPA GHG Emission Factors Hub.
Verify the current year at https://www.epa.gov/climateleadership/ghg-emission-factors-hub

| Fuel | Unit | CO2 | CH4 | N2O |
|---|---|---|---|---|
| Natural gas | MMBtu | 53.06 | 0.001 | 0.0001 |
| Diesel / No. 2 fuel oil | gallon | 10.21 | 0.00043 | 0.00008 |
| Propane (LPG) | gallon | 5.72 | 0.00024 | 0.00005 |
| Coal (bituminous) | short ton | 2310 | 0.011 | 0.016 |
| Wood / biomass | short ton | 1640* | 0.032 | 0.019 |

*Biogenic: report separately, exclude from scope totals.

## Mobile combustion

Source: EPA Emission Factors Hub Table 2-5 (updated annually). Verify before use.

| Fuel | CO2 (kg/gallon) | CH4 (g/mile) | N2O (g/mile) |
|---|---|---|---|
| Motor gasoline | 8.89 | 0.0217 (passenger car) | 0.0062 |
| Diesel | 10.21 | 0.0010 (light truck) | 0.0015 |
| Jet fuel (kerosene) | 9.75 | n/a | n/a |

## Purchased electricity (EPA eGRID)

Do NOT hardcode grid factors. eGRID factors change annually as the grid decarbonizes.
Fetch current values at runtime:

1. `web_search("EPA eGRID summary data current year subregional emission rates")` to
   find the latest eGRID release.
2. `url_fetch("https://www.epa.gov/egrid/summary-data")` to read the summary page.
3. Identify the current eGRID data year. As of July 2026, the latest is eGRID 2023
   (data year 2023, released January 2025, Revision 2 June 12, 2025).
4. The summary table now includes a **CO2e column** (lb CO2e/MWh) that combines
   CO2, CH4, and N2O using AR5 GWPs. Use the CO2e column directly rather than
   computing from individual gas columns.
5. Map the facility zip code to an eGRID subregion (EPA Power Profiler at
   https://www.epa.gov/egrid/power-profiler) or ask the user for the subregion code.
6. Apply the subregional total output emission rate (lb CO2e per MWh) for that year.
7. Convert: `tCO2e_per_MWh = lb_CO2e_per_MWh * 0.000453592`

Subregion codes (reference only, NOT for calculation — from eGRID 2023):
AKGD, AKMS, AZNM, CAMX, ERCT, FRCC, HIMS, HIOA, MROE, MROW, NEWE, NWPP,
NYCW, NYLI, NYUP, PRMS, RFCE, RFCM, RFCW, RMPA, SPNO, SPSO, SRMV, SRMW,
SRSO, SRTV, SRVC.

Note: eGRID 2023 added AZNM, HIMS, HIOA, PRMS, and SRMW subregions compared
to earlier editions. If a previously used subregion code is not in the current
release, consult the eGRID technical documentation for mapping changes.

Programmatic access: EPA Envirofacts RESTful service at
https://www.epa.gov/enviro/greenhouse-gas-restful-data-service

## Refrigerants (GWP, AR5 100-year)

| Refrigerant | Chemical | GWP |
|---|---|---|
| R-22 (HCFC-22) | CHClF2 | 1760 |
| R-134a (HFC-134a) | CH2FCF3 | 1300 |
| R-404A | Blend | 3922 |
| R-410A | Blend | 1924 |
| R-32 | CH2F2 | 675 |
| R-744 (CO2) | CO2 | 1 |
| SF6 | SF6 | 23500 |

## Business travel: air (kg CO2e per passenger-mile)

| Class | Short-haul (<300mi) | Medium (300-2300mi) | Long-haul (>2300mi) |
|---|---|---|---|
| Economy | 0.257 | 0.166 | 0.150 |
| Business | n/a | 0.481 | 0.434 |
| First | n/a | 0.663 | 0.599 |

Hotel nights contribute roughly 20 to 30 kg CO2e per night and are often forgotten.

## Waste disposal (tCO2e per short ton)

| Waste type | Landfill | Recycled | Composted | Incinerated |
|---|---|---|---|---|
| Mixed MSW | 0.52 | n/a | n/a | 0.04 |
| Paper (mixed) | 1.17 | -3.55 | n/a | -0.05 |
| Plastics (mixed) | 0.04 | -1.38 | n/a | 0.89 |
| Food waste | 0.56 | n/a | -0.18 | -0.09 |
| Metal (mixed) | 0.04 | -4.49 | n/a | n/a |

## Employee commuting mode factors (kg CO2e per mile)

Car alone 0.404, carpool 0.202, bus 0.064, rail 0.041, bike or walk 0.
Default working days: 235 per year (excludes weekends, holidays, remote days).

## Calculation formulas

Stationary combustion (result in tonnes):
```
co2_t  = fuel_consumed * EF_co2  / 1000
ch4_t  = fuel_consumed * EF_ch4  * GWP_ch4 / 1000
n2o_t  = fuel_consumed * EF_n2o  * GWP_n2o / 1000
total_co2e_t = co2_t + ch4_t + n2o_t
```

Mobile combustion:
```
co2_t = fuel_consumed_gallons * EF_co2_per_gallon / 1000
ch4_t = miles_driven * EF_ch4_g_per_mile * GWP_ch4 / 1e6
n2o_t = miles_driven * EF_n2o_g_per_mile * GWP_n2o / 1e6
```

Refrigerant leakage:
```
co2e_t = refrigerant_charge_kg * annual_leak_rate * GWP / 1000
# or mass-balance:
co2e_t = (begin_inv + purchases - end_inv - recovered) * GWP / 1000
# Default leak rates: commercial refrigeration 15-25%, AC systems 2-10%.
```

Purchased electricity, location-based:
```
co2e_t = electricity_mwh * grid_emission_factor_tco2e_per_mwh
```

Scope 3, Category 3, Activity C (Transmission & Distribution Losses):
```
loss_mwh = electricity_mwh * grid_gross_loss_pct
co2e_t = loss_mwh * grid_emission_factor_tco2e_per_mwh
```
The 2025 EPA GHG Emission Factors Hub (Table 6) now provides grid gross loss
percentages for each eGRID subregion. Fetch at runtime alongside grid factors.

Purchased electricity, market-based (in priority order): supplier-specific factor,
then residual mix factor, then grid average as fallback. RECs, GOs, I-RECs, or a
contractual PPA are the only valid market instruments. Being on a "green" utility
rate does not qualify.

Employee commuting:
```
annual_miles = employees * one_way_distance * 2 * working_days
co2e_t = annual_miles * EF_per_mile / 1000
```

## Unit conversions

- 1 therm = 0.1 MMBtu
- 1 CCF (hundred cubic feet) = 1.036 therms
- 1 MCF (thousand cubic feet) = 10.36 therms
- 1 lb = 0.4536 kg
- lb CO2 per MWh to tCO2 per MWh: multiply by 0.000453592
