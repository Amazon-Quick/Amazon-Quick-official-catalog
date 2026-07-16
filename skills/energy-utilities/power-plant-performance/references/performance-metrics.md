# Performance Metrics: NERC GADS and Heat Rate

Formula reference for the availability and heat rate workflows. All NERC GADS
metrics follow IEEE Standard 762 definitions exactly. Do not improvise
alternative definitions.

## NERC GADS Performance Metrics (IEEE Standard 762)

### Equivalent Forced Outage Rate (EFOR)
```
EFOR = (FOH + EFDH) / (SH + FOH + EFDH) * 100%
```
- FOH = Forced Outage Hours (unit completely unavailable, unplanned)
- EFDH = Equivalent Forced Derated Hours = sum(Derated_MW / Max_Capacity_MW * Derated_Hours)
- SH = Service Hours (hours the unit was generating)

### Equivalent Forced Outage Rate - demand (EFORd)
```
EFORd = (fp * Td + (1 - fp) * fd * Td) / (fp * Td + (1 - fp) * fd * Td + SH)
```
- fp = probability of full forced outage = FOH / (FOH + SH + RSH)
- fd = probability of forced derated state
- Td = demand period hours
- RSH = Reserve Shutdown Hours

EFOR is time-based (all hours weighted equally). EFORd is demand-weighted (only
hours the unit would have been needed). EFORd is the standard for capacity
adequacy assessments. They are not interchangeable.

### Equivalent Availability Factor (EAF)
```
EAF = (AH - EUDH - EPDH) / PH * 100%
```
- AH = Available Hours = PH - (FOH + MOH + POH + UOH)
- EUDH = Equivalent Unplanned Derated Hours
- EPDH = Equivalent Planned Derated Hours
- PH = Period Hours
- FOH, MOH, POH, UOH = Forced, Maintenance, Planned, Unplanned Outage Hours

### Net Capacity Factor (NCF)
```
NCF = Net_Generation_MWh / (Net_Max_Capacity_MW * Period_Hours) * 100%
```

### Gross Capacity Factor (GCF)
```
GCF = Gross_Generation_MWh / (Gross_Max_Capacity_MW * Period_Hours) * 100%
```

### Service Factor (SF)
```
SF = SH / PH * 100%
```

### Starting Reliability (SR)
```
SR = Successful_Starts / Attempted_Starts * 100%
```

### NERC GADS event classification
Forced outage hours include ONLY unplanned events. Planned maintenance is not a
forced outage. Typical cause-code groups:
- U1, U2, U3: Forced Outages (immediate, delayed, postponed)
- SF: Starting Failure
- ME: Maintenance extension of a planned outage
- PE: Planned extension
- MO: Maintenance Outage (scheduled, deferrable)
- PO: Planned Outage

### NERC GADS fleet averages (typical, by technology)
These vary by unit vintage, size, fuel, and region and change over time. Treat
them as fallback ranges only. Verify current values from the NERC GADS source
before benchmarking (see the skill Rules and Resources).

| Metric        | Coal          | Gas CT        | Combined Cycle | Nuclear     |
|---------------|---------------|---------------|----------------|-------------|
| EAF           | 82-86%        | 90-94%        | 87-91%         | 88-92%      |
| EFOR          | 6-10%         | 3-6%          | 3-5%           | 2-4%        |
| NCF           | 40-55%        | 10-25%        | 50-65%         | 90-93%      |
| HR (BTU/kWh)  | 9,500-10,500  | 9,500-11,000  | 6,400-7,200    | 10,400      |

## Heat Rate Analysis

### Gross and net heat rate
```
HR_gross = Fuel_Input_MMBTU / Gross_Generation_MWh * 1000    [BTU/kWh]
HR_net   = Fuel_Input_MMBTU / Net_Generation_MWh   * 1000    [BTU/kWh]
```
Net = Gross - Auxiliary Power. Heat rate comparisons must use a consistent
basis. Always state gross vs net.

### Incremental heat rate (at operating point P)
```
HR_inc = dH/dP = d(Fuel_Input)/d(Power_Output)    [BTU/kWh]
```

### Heat rate deviation from design
```
dHR  = HR_actual_corrected - HR_design            [BTU/kWh]
dHR% = dHR / HR_design * 100
```
Categorize: within tolerance (< 2%), moderate degradation (2-5%), significant
degradation (> 5%).

### Controllable loss decomposition (sums to total deviation)
```
dHR = dHR_compressor + dHR_turbine + dHR_combustion + dHR_HRSG + dHR_condenser + dHR_auxiliary
```

### Heat rate from cycle efficiency
```
HR = 3412.14 / eta_overall    [BTU/kWh]
```
3412.14 BTU = 1 kWh (exact conversion).

## HHV vs LHV

US utilities report on a Higher Heating Value (HHV) basis. OEM guarantees are
often on a Lower Heating Value (LHV) basis. Approximate HHV/LHV ratios: ~1.11
for natural gas, ~1.05 for coal. A "7,000 BTU/kWh LHV" combined cycle is about
7,763 BTU/kWh HHV. Confirm the basis before any comparison.
