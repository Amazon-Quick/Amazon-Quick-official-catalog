# Authoritative sources for time-sensitive values

Rule 0 requires that any value which changes over time be verified live with
web_search or url_fetch before use. Fetch from these sources during the session;
do not rely on values embedded in this skill or in model memory. If a source is
unreachable, ask the user to provide or confirm the value.

## Cost and performance benchmarks (CAPEX, O&M, technology assumptions)

- National Renewable Energy Laboratory (NREL) Annual Technology Baseline (ATB):
  https://atb.nrel.gov/
- Lazard Levelized Cost of Energy Analysis (annual update):
  https://www.lazard.com/research-insights/
- International Renewable Energy Agency (IRENA) Renewable Power Generation Costs:
  https://www.irena.org/
- International Energy Agency (IEA) Renewable Energy Market Update:
  https://www.iea.org/

## Solar resource data

- NREL PVWatts methodology and calculator: https://pvwatts.nrel.gov/
- NREL National Solar Radiation Database (NSRDB): https://nsrdb.nrel.gov/

## Wind resource data

- Global Wind Atlas: https://globalwindatlas.info/

## What to verify at runtime

Technology CAPEX ($/kW), fixed and variable O&M, current incentive levels
(investment tax credit, production tax credit) and their eligibility rules,
prevailing power purchase agreement (PPA) prices, and any grid or interconnection
limits for the project location. Physical model constants (transposition geometry,
temperature coefficients, air density formula, Weibull and power-curve math) do not
change and are embedded in the methodology reference files.
