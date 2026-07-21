# GADS Classification Rules and Non-Obvious Traps

Apply these when parsing, classifying, and validating events. Each rule reflects
a NERC DRI requirement or a common eGADS rejection cause. When a case is
ambiguous, flag it for user review rather than guessing.

## Reportability

- Events shorter than 1 minute are not reportable unless they result in a unit trip.
- A derate is reportable only when net MW loss exceeds the greater of 10 MW or
  2% of Net Dependable Capacity (NDC).
- Reserve Shutdown (RS) hours are excluded from forced outage rate calculations.

## Overlapping derates

When two forced derates overlap, the combined MW loss cannot exceed NDC. Cap the
equivalent derated hours at the unit's maximum possible derate for any given
hour. Do not sum overlapping derates past 100% of NDC.

## Reserve Shutdown into forced outage

If a unit goes from RS directly into a forced outage (U1/U2/U3), the RS period is
NOT retroactively reclassified. The forced outage starts when the unit would have
been called to run.

## Startup Failures

An SF event can only exist as a Related Event to a U1 primary event. A standalone
SF is invalid.

## U1 amplification codes

The only valid amplification codes for a U1 event are 84, T1, and T2. A U1
lacking one of these is a classification error to flag.

## Seasonal derating vs. forced derating

Ambient temperature derates that reduce capacity below NDC are classified as D4
(Maintenance Derating) when expected seasonally, not D1. Only unexpected
temperature extremes beyond design basis warrant forced derate classification.

## Net vs. gross generation

GADS reports on a NET basis (station service subtracted). Ensure input data is
net, or subtract station service consumption before calculating NCF.

## Period Hours

- Use exact calendar hours (e.g., a non-leap Q1 = 31+28+31 = 90 days = 2,160 hours).
- Account for leap-year February (Q1 = 2,184 hours in leap years).
- Do NOT adjust for Daylight Saving Time; GADS uses clock hours as reported.

## Time accounting balance

PH must equal the sum of all state hours (SH + RSH + FOH + MOH + POH + inactive
hours) within a +/- 0.1 hour tolerance. A larger imbalance is a validation
failure to surface before submission.

## Wind and solar differences

Wind plants report at the plant level (not individual turbine). Solar reports at
the inverter-block or plant level per the GADS Solar DRI. Different event codes
apply (6000-series for wind, 7000-series for solar).

## Contributing Operating Condition (COC)

Mandatory for events starting Jan 1, 2024 or later. Missing COC causes eGADS
rejection. Valid codes are listed in references/cause-codes.md.
