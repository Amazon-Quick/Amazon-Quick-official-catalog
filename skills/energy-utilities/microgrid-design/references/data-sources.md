# Authoritative Data Sources

Fetch time-sensitive values from these sources at runtime with `web_search` and
`url_fetch`, per Rule 2 in SKILL.md. Model knowledge is not a valid source for
any of these. Some services require a free API key that the user supplies; do
not hardcode keys in this skill or its scripts, and do not ask the user for
secrets that belong to a configured connector.

## Solar resource and system modeling
- NREL PVWatts API: https://developer.nrel.gov/docs/solar/pvwatts/v8/
- NREL ReOpt API: https://developer.nrel.gov/docs/energy-optimization/reopt/
- NREL System Advisor Model (SAM): https://sam.nrel.gov/
- Sandia PV Performance Modeling Collaborative: https://pvpmc.sandia.gov/

## Rates, prices, and market data
- OpenEI Utility Rate Database (URDB): https://apps.openei.org/USURDB/
- U.S. Energy Information Administration open data: https://www.eia.gov/opendata/
- Lazard Levelized Cost of Energy report (annual): generation and storage benchmarks

## Standards and program guidance
- IEEE 1547-2018: Interconnection of distributed energy resources with electric power systems
- IEEE C57.91: Guide for loading mineral-oil-immersed transformers
- U.S. DOE Office of Electricity, Microgrid Program: https://www.energy.gov/oe/

## What to verify from these sources (never assume as current)
- Diesel and fuel prices, and fuel escalation assumptions.
- Utility tariffs: energy rates, demand charges, standby/backup charges, and
  export compensation (net metering, net billing, or wholesale).
- Tax credits, standalone-storage credits, and depreciation schedules.
- LCOE benchmarks for grid electricity, solar, storage, and diesel generation.
- Interconnection and air-quality permitting requirements for the jurisdiction.
