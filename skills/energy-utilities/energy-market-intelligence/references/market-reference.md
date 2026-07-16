# Energy Market Reference Catalog

Lookup data for energy market research. This catalog does not change between runs.
Time-sensitive values (prices, emission factors, regulatory limits, forecasts) are
never listed here as current: fetch them at runtime from the authoritative sources
below, per Rule 1 in SKILL.md.

## Market Segments

- Upstream: exploration, production, reserves (crude oil, natural gas, natural gas liquids).
- Midstream: transportation, processing, storage (pipelines, liquefied natural gas, gas processing).
- Downstream: refining, marketing, retail (gasoline, diesel, jet fuel, petrochemicals).
- Power generation: utility-scale and distributed (thermal, renewable, nuclear, storage).
- Carbon markets: compliance (European Union Emissions Trading System, Regional Greenhouse Gas Initiative, Western Climate Initiative) and voluntary (voluntary carbon market).

## Key Pricing Points

- Crude oil: West Texas Intermediate (Cushing, Oklahoma), Brent (North Sea), Dubai/Oman (Asia benchmark).
- Natural gas: Henry Hub (United States), Title Transfer Facility (Europe), Japan/Korea Marker (Asia liquefied natural gas).
- Electricity: varies by Independent System Operator or Regional Transmission Organization (PJM, ERCOT, CAISO, MISO, SPP, NYISO, ISO-NE).
- Carbon: European Union Allowance, Regional Greenhouse Gas Initiative allowance, California Carbon Allowance.
- Renewable Energy Credits: Class I credit prices vary by state and market.

## Regulatory Bodies

- Federal Energy Regulatory Commission (FERC): interstate gas and electricity, wholesale markets.
- Environmental Protection Agency (EPA): emissions rules, Renewable Fuel Standard, methane regulations.
- Department of Energy (DOE): liquefied natural gas export authorizations, Strategic Petroleum Reserve, loan programs.
- State Public Utility Commissions: retail rates, integrated resource plans, renewable mandates.
- California Air Resources Board (CARB): cap-and-trade, Low Carbon Fuel Standard.
- European Commission: REPowerEU, Fit for 55, Carbon Border Adjustment Mechanism.

## Analytical Frameworks

- Supply-demand balance: production plus imports versus consumption plus exports plus storage change.
- Crack spread: (product revenue minus crude cost) divided by crude cost. Proxy for refining margin.
- Spark spread: power price minus (gas price times heat rate). Proxy for gas-fired generation margin.
- Dark spread: power price minus (coal price times heat rate) minus carbon cost. Coal generation margin.
- Net-back pricing: end-market price minus transportation and processing costs equals wellhead value.
- Forward curve analysis: contango (future price above spot) versus backwardation (spot above future).
- Seasonal patterns: heating degree days, cooling degree days, shoulder months.

## Authoritative Data Sources

Tier 1 (primary data and official filings):
- Energy Information Administration (EIA): https://www.eia.gov/ (Short-Term Energy Outlook, Annual Energy Outlook, natural gas weekly, petroleum status report).
- International Energy Agency (IEA): https://www.iea.org/ (Oil Market Report, Gas Market Report, World Energy Outlook).
- Federal Energy Regulatory Commission (FERC): https://www.ferc.gov/ (orders, notices of proposed rulemaking, market oversight).
- Independent System Operator and Regional Transmission Organization market reports: PJM, ERCOT, CAISO, MISO, SPP, NYISO, ISO-NE.
- Baker Hughes rig count: https://rigcount.bakerhughes.com/ (leading indicator for United States oil and gas activity).
- Commodity Futures Trading Commission (CFTC): Commitments of Traders positioning data for energy futures.

Tier 2 (industry analysis, often paywalled):
- S&P Global Commodity Insights: https://www.spglobal.com/commodityinsights/ (commodity price assessments, market analysis).
- BloombergNEF: https://about.bnef.com/ (energy transition, clean energy investment data).

## Source Credibility Tiers

- Tier 1: EIA, IEA, FERC, and other primary agencies and market operators.
- Tier 2: established industry publications and analyst firms.
- Tier 3: general media and blogs. Corroborate before relying on tier 3.
