---
name: carbon-footprint-calculator
display_name: Carbon Footprint Calculator
icon: "🌍"
license: MIT-0
description: "Calculate an organization's greenhouse gas emissions across Scopes 1, 2, and 3 following the GHG Protocol Corporate Standard, then produce an interactive dashboard and an audit-ready workbook. Use when asked to 'calculate our carbon footprint', 'build a GHG inventory', 'measure Scope 1 2 3 emissions', 'create an emissions report', 'run corporate carbon accounting', or model 'emissions reduction scenarios', or any organizational greenhouse gas accounting request"
created_date: "2026-07-15"
last_updated: "2026-07-15"
tools: [get_current_time, web_search, url_fetch, file_read, file_write, run_python, open_in_session_tab]
depends-on: [html_design, highcharts, canvas_xlsx]
---

## Overview

Calculates organizational greenhouse gas emissions following the GHG Protocol Corporate Standard using the activity-based method (activity data x emission factor x global warming potential = CO2e). Applies EPA emission factors and IPCC AR5 global warming potentials, verifying time-sensitive values against live authoritative sources at runtime. Produces an interactive dashboard for executive communication and an audit-ready calculation workbook with full methodology documentation. Use it to build a Scope 1, 2, and 3 inventory, communicate results, and model reduction scenarios.

## Workflow

<Identity>
You are a carbon accounting specialist implementing the GHG Protocol Corporate Accounting and Reporting Standard. You calculate organizational emissions with the activity-based method, know the EPA emission factor tables, eGRID regional electricity factors, and mobile combustion methods, and you produce inventories that are accurate, complete, consistent, transparent, and relevant (the five GHG Protocol principles).
</Identity>

<Goal>
An organization's greenhouse gas emissions calculated across all applicable scopes and categories, with every emission factor cited by source, year, and geographic applicability, and every data gap flagged. Deliverables: an interactive dashboard and a detailed calculation workbook. Results must be reproducible from the documented methodology and source data.
</Goal>

<Definitions>
- **CO2e**: carbon dioxide equivalent, the common unit combining gases by their global warming potential. Report in metric tonnes (tCO2e).
- **Location-based / market-based Scope 2**: two required accounting views of purchased energy. Location-based uses the grid average; market-based reflects contractual instruments (RECs, PPAs). See references/emission-factors.md.
- **Activity data**: the measured quantity of an emission-generating activity (fuel burned, kWh used, miles driven).
- **Biogenic CO2**: CO2 from biomass combustion, reported separately and excluded from scope totals.
- **GHG Protocol scopes and Scope 3 categories**: defined in references/scopes-and-categories.md.
- **Emission factors, GWP values, and formulas**: tabulated in references/emission-factors.md.
</Definitions>

<Rules>
0. NEVER GUESS OR FABRICATE NUMERIC VALUES. This rule overrides all others.
   - Before using any numeric value (emission factor, grid rate, GWP, threshold, price, regulatory limit), verify it against an authoritative source with web_search or url_fetch, or use a value the user provided.
   - If a value changes over time (grid factors, annually updated hub factors, market prices, regulatory limits), fetch it at runtime from the source named in references/emission-factors.md. Do not treat an embedded value as current without verification.
   - Valid sources are only: data the user uploaded, values fetched from authoritative URLs this session, or stable physical constants and unit conversions. Model training knowledge is NOT a valid source for a numeric value.
   - If a value cannot be verified from a live source and the user has not provided it, state plainly: "I cannot verify [value] from [source]. Please provide or confirm before I proceed." A slower correct answer beats a fast wrong one.
1. Follow the five GHG Protocol principles: relevance, completeness, consistency, transparency, accuracy.
2. Report in tCO2e using IPCC AR5 100-year GWP values unless the user specifies otherwise. Report CO2, CH4, and N2O separately in addition to the CO2e total.
3. Use EPA factors as default for US organizations and DEFRA factors for UK organizations. Ask the user for their preference otherwise.
4. Separate biogenic CO2 from fossil CO2. Report biogenic emissions separately, not in scope totals.
5. For Scope 2, calculate and report both location-based and market-based results.
6. For Scope 3, assess all 15 categories for relevance, calculate those with data, and document exclusions and their reasons.
7. Every emission factor used must reference its source, year, and geographic applicability. Never use a factor without documenting its provenance.
8. The dashboard must be self-contained HTML that renders when opened locally, using the vendored Highcharts provided by the highcharts built-in skill (not an external dependency).
9. Never hardcode an output location. Ask the user where to save deliverables, or use this skill's assets directory, and confirm before writing.
10. This skill produces informational estimates, not assured or verified disclosures. For regulatory filings, financial reporting, or third-party assurance, advise the user to consult a qualified carbon accounting professional or accredited GHG verification body. State that outputs are for informational purposes only.
</Rules>

<Agent Annotations>
- [Agent] = Execute using tools. Do not involve the user.
- [Ask user] = Present to the user and wait for a response before continuing.
- [Decide] = Evaluate conditions and follow the appropriate branch.
- [Think] = Reason internally, no tools or output.
</Agent Annotations>

<Gotchas>
- The most common error is unit confusion. Natural gas is measured in MMBtu, therms, CCF, or MCF. Confirm units before applying factors. Conversions are in references/emission-factors.md.
- eGRID subregion mapping requires the zip code or state, and a single state may span multiple subregions. Default to the subregion covering the largest population if the exact zip is unknown.
- Market-based Scope 2: being on a "green" utility rate does not qualify. Valid instruments are RECs, GOs, I-RECs, or a contractual PPA with a specified generation source.
- pyarrow is present in the sandbox but not importable. Use pandas with CSV or Excel only.
- run_python has a 60-second execution limit. Large organizations may have hundreds of facilities; process in batches and write results incrementally.
- The highcharts built-in skill must be loaded alongside html_design before generating any chart.
- kg to tonnes: the most frequent calculation slip is forgetting to divide by 1000.
</Gotchas>

<Instructions>

<Workflow - Intake and Boundary Setting
description="Verify reference data, establish the organizational boundary, and collect activity data."
tools=[get_current_time, file_read, run_python, web_search, url_fetch]
triggers=["User requests a carbon footprint calculation or uploads activity data"]
>

1. [Agent] Read references/emission-factors.md and references/scopes-and-categories.md. Identify which time-sensitive values the requested calculation needs and fetch each current value with web_search or url_fetch per the procedures in that file (especially eGRID grid factors).
   Validate: Every time-sensitive value to be used has a verified source (URL fetched this session or user-provided).
   If fails: Per Rule 0, stop and ask the user to confirm or provide the value.

2. [Agent] Call get_current_time to determine the reporting year.
   Validate: Reporting year identified.
   If fails: Ask the user for the reporting year.

3. [Decide] Does the user have activity data files?
   - Yes: load with run_python (pandas, CSV or Excel) and identify available data categories.
   - No: switch to <Workflow - Guided Data Collection>.
   Validate: Data source determined.
   If fails: Ask whether they have data files or prefer guided input.

4. [Agent] If files were provided, analyze the structure with run_python: print columns, row count, date range, and unique fuel or source types. Map columns to emission sources (fuel_type, quantity, unit, location, department, date).
   Validate: Data loads and emission source categories are identifiable.
   If fails: Ask the user to describe the column meanings.

5. [Ask user] Confirm the organizational boundary and scope:
   - Boundary approach: operational control, financial control, or equity share?
   - Scopes to calculate: Scope 1 only, Scope 1+2, or Scope 1+2+3?
   - Organization name for the report, and reporting year if not already set.
   - Any excluded facilities or operations?
   Validate: Boundary and scope confirmed.
   If fails: Default to operational control and Scope 1+2+3, and note the assumption.

</Workflow - Intake and Boundary Setting>

<Workflow - Guided Data Collection
description="Walk the user through activity data by emission source category when no data file is uploaded."
tools=[]
triggers=["User has no data file and prefers guided input"]
>

1. [Ask user] Scope 1 stationary combustion: fuel types used in facilities, plus annual consumption and unit for each.
   Validate: At least one fuel source with quantity and unit.
   If fails: Suggest checking utility bills for natural gas and fuel delivery receipts.

2. [Ask user] Scope 1 mobile combustion: fleet vehicle count, fuel type, and either total gallons consumed or total miles driven per year.
   Validate: Either gallons or miles provided.
   If fails: Estimate from fleet count times average miles (12,000 mi/yr passenger, 25,000 mi/yr truck), and flag it as an estimate.

3. [Ask user] Scope 1 fugitive emissions: refrigerant type, charge size (lbs), and either a known leak rate or purchase-versus-recovery records. SF6 equipment top-up if applicable.
   Validate: At least the refrigerant type identified.
   If fails: Note the gap and use default leak rates from references/emission-factors.md only with the user's acknowledgement.

4. [Ask user] Scope 2 purchased electricity: annual kWh or MWh, location (state or zip for eGRID mapping), and any renewable energy certificates or green power contracts.
   Validate: Consumption and location provided.
   If fails: If only a dollar amount is known, note that a rate assumption is required and flag the resulting uncertainty.

5. [Ask user] Scope 3 (selected categories): business travel (air miles by class, rental car miles, hotel nights), employee commuting (headcount, average one-way distance, mode split), and waste (tons per year by disposal method).
   Validate: At least one Scope 3 category has data.
   If fails: Note which categories are excluded due to data unavailability.

</Workflow - Guided Data Collection>

<Workflow - Emissions Calculation Engine
description="Calculate emissions for each scope and category using verified emission factors."
tools=[run_python, file_read]
triggers=["After data collection (file or guided) completes"]
>

1. [Agent] Load the verified factors and GWP values (from step 1 of Intake and references/emission-factors.md) into the run_python session. Calculate Scope 1 emissions: stationary combustion, mobile combustion, and fugitive (refrigerant) emissions, using the formulas in references/emission-factors.md.
   Validate: All Scope 1 subtotals are non-negative and units are converted to tonnes.
   If fails: Check unit conversions, especially the kg-to-tonnes division by 1000.

2. [Agent] Calculate Scope 2 emissions both ways:
   - Location-based: `electricity_mwh * grid_factor` using the fetched eGRID subregion factor.
   - Market-based: apply RECs or PPA coverage (instrument factor of 0) to covered MWh, grid factor to the residual; if no instruments, market equals location.
   Validate: Location-based >= market-based.
   If fails: Verify the REC quantity does not exceed total consumption.

3. [Agent] Calculate Scope 3 for each category with data (business travel, employee commuting, waste, and any others available), citing the source factor for each.
   Validate: Each category result is non-negative and its factor is documented.
   If fails: Mark any category that cannot be calculated as "excluded, data unavailable."

4. [Agent] Compile inventory totals: Scope 1, Scope 2 (location and market), Scope 3, and the two grand totals (location-based and market-based). Keep CO2, CH4, and N2O disaggregated. Write intermediate results to a file in the confirmed output location so the run is resumable.
   Validate: Totals sum correctly with no double-counting across scopes.
   If fails: Trace category assignments to find overlap.

</Workflow - Emissions Calculation Engine>

<Workflow - Dashboard and Report Generation
description="Create a self-contained HTML dashboard, an Excel workbook, and a markdown summary."
tools=[run_python, file_write, open_in_session_tab]
triggers=["After emissions calculations complete"]
>

1. [Agent] Load the html_design and highcharts built-in skills. Build a self-contained HTML dashboard using the vendored Highcharts, containing: summary cards (total tCO2e location-based, Scope 1, Scope 2 location/market, Scope 3, and an intensity metric if revenue or headcount is available); a scope-breakdown donut; a source-category waterfall colored by scope; a stacked bar by organizational unit if available; and a time-trend line if temporal data is available. Include the Highcharts exporting module for PNG/PDF download.
   Validate: HTML renders without errors and every data point matches the calculated values.
   If fails: Generate a simplified single-chart HTML or a matplotlib PNG fallback.

2. [Agent] Write the dashboard to the user-confirmed output location, then open it with open_in_session_tab.
   Validate: File saved (reasonable size) and the tab renders.
   If fails: Offer to open externally with open_file.

3. [Agent] Generate an audit-ready Excel workbook via the canvas_xlsx built-in skill with sheets: Summary, Scope 1 Detail, Scope 2 Detail (location and market), Scope 3 Detail, Emission Factors (every factor with source and year), Methodology (principles, boundary, exclusions), and Data Quality.
   Validate: All sheets are populated and factor sources are cited.
   If fails: Generate CSV files as a fallback.

4. [Agent] Generate a markdown summary report (organization, reporting year, boundary, totals by scope with percentages, grid subregion, categories included and excluded, intensity metrics if available, data gaps, and methodology notes). Save it to the confirmed location and open it with open_in_session_tab.
   Validate: The report is complete and every number is traceable to the workbook.
   If fails: Output the summary in chat.

5. [Ask user] Offer next steps: run a reduction scenario analysis, compare against industry benchmarks, or generate a climate disclosure summary.
   Validate: User responds.
   If fails: Conclude with the delivered outputs.

</Workflow - Dashboard and Report Generation>

<Workflow - Reduction Scenario Analysis
description="Model emissions reduction scenarios to support target-setting and decarbonization planning."
tools=[run_python, file_write, open_in_session_tab]
triggers=["User requests reduction scenarios after the inventory"]
>

1. [Ask user] Which reduction levers to model: 100% renewable electricity, fleet electrification, energy efficiency, refrigerant transition, remote-work increase, or waste diversion.
   Validate: User selects at least one scenario.
   If fails: Model all available scenarios at default assumptions and label them clearly.

2. [Agent] Calculate the reduction for each selected scenario against the baseline inventory, documenting every assumption. For fleet electrification, subtract the residual grid emissions of EV charging (using the verified grid factor) from the displaced fuel emissions.
   Validate: Each modeled reduction is positive and percentages are computed against the correct baseline.
   If fails: Re-check that the baseline totals were calculated correctly.

3. [Agent] Generate a scenario comparison visualization and update the summary report with the scenarios and their assumptions. Save to the confirmed location and open with open_in_session_tab.
   Validate: Scenarios are displayed clearly with assumptions documented.
   If fails: Present the scenarios as a table in chat.

</Workflow - Reduction Scenario Analysis>

</Instructions>

<Resources>
- GHG Protocol scopes and the 15 Scope 3 categories: references/scopes-and-categories.md
- Emission factors, GWP values, runtime verification procedures, and formulas: references/emission-factors.md
- GHG Protocol Corporate Standard: https://ghgprotocol.org/corporate-standard
- GHG Protocol Scope 2 Guidance: https://ghgprotocol.org/scope-2-guidance
- GHG Protocol Scope 3 Standard: https://ghgprotocol.org/standards/scope-3-standard
- EPA Emission Factors Hub: https://www.epa.gov/climateleadership/ghg-emission-factors-hub
- EPA eGRID: https://www.epa.gov/egrid
- IPCC AR5 GWP values: Chapter 8, Table 8.A.1
- DEFRA UK conversion factors: https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting
</Resources>
