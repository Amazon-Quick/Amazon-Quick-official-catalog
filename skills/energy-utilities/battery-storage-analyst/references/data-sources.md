# Authoritative Data Sources

Per Rule 0, every time-sensitive value must be verified against a live source in
the current session before use, using web_search or url_fetch. Model knowledge is
not a valid source. This file lists where each class of value comes from. If a
source is unreachable and the user has not supplied the value, stop and ask.

## Utility tariffs and rates

- OpenEI Utility Rate Database (URDB): https://openei.org/wiki/Utility_Rate_Database
  API endpoint https://api.openei.org/utility_rates?version=7 (requires an API key).
  Use for demand charges, TOU periods, and ratchet provisions by utility.
- If the API is not reachable via url_fetch, ask the user for the tariff sheet PDF
  or the utility name and service territory so the rate can be looked up.

## Wholesale energy and market prices

- U.S. Energy Information Administration (EIA) Open Data: https://www.eia.gov/opendata/
- Locational marginal prices, capacity, and regulation clearing prices come from the
  relevant independent system operator (for example the ISO or RTO serving the site).
  Ask the user which market applies and fetch its published price data.

## Technology cost and LCOS benchmarks

- Lazard Levelized Cost of Storage report (published annually): fetch the current
  edition for capital cost and LCOS benchmarks. Do not quote a remembered figure.
- NREL cost and performance databases and the NREL ReOpt documentation:
  https://developer.nrel.gov/docs/energy-optimization/reopt/

## Incentives and tax parameters

- ITC percentage, eligibility, and charge-share thresholds, and MACRS schedules:
  confirm from IRS guidance and current U.S. Department of Energy or NREL summaries.
  These change with legislation, so never apply a remembered percentage.

## Degradation model parameters

- Cell manufacturer datasheet for the specific cell, when available.
- Peer-reviewed literature listed in references/degradation-model.md.
- Measured test data supplied by the user.

## Solar resource (for paired systems)

- NREL National Solar Radiation Database (NSRDB) or a user-supplied production
  profile. pvlib is not available in the sandbox, so build the PV profile from the
  irradiance series and system parameters as shown in references/sizing-and-dispatch.md.
