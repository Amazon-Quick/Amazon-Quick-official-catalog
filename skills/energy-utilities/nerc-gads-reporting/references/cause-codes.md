# NERC GADS Cause Code System

Cause codes are organized in a three-level hierarchy. Confirm exact numeric
ranges and component codes against the current NERC GADS DRI at runtime; the
ranges below are for structural orientation, not a substitute for the DRI.

## Level 1 - System (major equipment group)

- Boiler (codes 0100-0899)
- Turbine/Generator (codes 1000-1899)
- Reactor (codes 2000-2899)
- Balance of Plant (codes 3000-3899)
- External (codes 4000-4899)
- Non-Equipment (codes 5000-5899)
- Wind-specific (codes 6000-6899)
- Solar-specific (codes 7000-7899)

## Level 2 - Component (specific equipment within a system)

Example within Boiler: Furnace, Superheater, Reheater, Economizer, Air Heater,
Fans, Pulverizers.

## Level 3 - Amplification Code (root cause detail)

- 80 = Personnel Error
- 81 = Design/Engineering Problem
- 82 = Manufacturing/Processing Problem
- 83 = Construction/Installation/Commissioning Problem
- 84 = Operational Procedure/Practice Problem
- 85 = External Influence (non-weather)
- 86 = Unknown
- 87 = Other
- 88 = Lightning
- 89 = Cold Weather
- 90 = Hot Weather
- 91 = Flood
- 92 = Ice/Snow
- 93 = Tornado/Straight-line Wind
- T1 = Testing (regulatory required)
- T2 = Testing (non-regulatory)

## Contributing Operating Condition (COC) codes

Mandatory field for events starting on or after January 1, 2024. Valid values:
Normal Operating Condition, Cold Weather, Hot Weather, Wet Bulb Above Design,
Wildfire/Smoke, Flooding, Other Extreme Weather. A missing COC on a post-2024
event causes eGADS rejection.
