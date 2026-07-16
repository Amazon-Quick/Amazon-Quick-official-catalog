# Authoritative Data Sources and Standards

Fetch time-sensitive values from these sources at runtime with url_fetch or
web_search (Rule 1). Access to the listed APIs requires an action connector or an
API key supplied by the user; the skill does not embed keys. If a source is
unreachable, ask the user to provide or confirm the value rather than guessing.

## Live data (time-sensitive; fetch each session)

- OpenEI Utility Rate Database (URDB): https://api.openei.org/utility_rates?version=7
  Utility tariffs, time-of-use (TOU) rate schedules, demand charges.
- EIA Open Data API: https://api.eia.gov/v2/
  Electricity retail prices and fuel (gasoline/diesel) prices by region.
- NREL Alternative Fuels Station Locator:
  https://developer.nrel.gov/docs/transportation/alt-fuel-stations-v1/
  Existing public charging infrastructure.
- EPRI EV Load Shape Library: https://loadshape.epri.com/
  Empirical fleet charging load shapes and coincidence factors.
- Atlas Public Policy EV Hub: https://www.atlasevhub.com/
  State incentives, registrations, and policy tracking.

## Incentives (verify current eligibility each session; rules change annually)

- Federal Commercial Clean Vehicle Credit (Internal Revenue Code section 45W):
  no MSRP cap; applies to fleet/commercial vehicles.
- Federal Clean Vehicle Credit (section 30D): consumer credit with MSRP limits,
  manufacturer caps, and domestic-content requirements.
  Confirm current amounts and eligibility at the IRS and U.S. Department of Energy
  sites before use.

## Stable standards (reference documents, not runtime values)

- SAE J1772-201710: EV Conductive Charge Coupler.
- SAE J3068: Electric Vehicle Power Transfer, 3-phase AC for medium/heavy-duty.
- IEEE C57.91-2011: Guide for Loading Mineral-Oil-Immersed Transformers.
- NEC Article 625: Electric Vehicle Charging Systems (625.41: 125% continuous load).
- OCPP 2.0.1 (Open Charge Point Protocol): https://openchargealliance.org/
  Communication standard for managed/smart charging.
