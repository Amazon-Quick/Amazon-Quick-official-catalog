# NERC GADS / IEEE 762 Performance Index Formulas

Use these formulas exactly. Never approximate or substitute simplified versions.
Round every index to one decimal place (do not truncate).

## Base Time Components (hours)

- **PH** = Period Hours (total calendar hours in reporting period)
- **SH** = Service Hours (hours unit was synchronized to grid)
- **RSH** = Reserve Shutdown Hours
- **POH** = Planned Outage Hours
- **MOH** = Maintenance Outage Hours
- **FOH** = Forced Outage Hours (U1 + U2 + U3 outage hours)
- **EPDH** = Equivalent Planned Derated Hours = Sum of (PD MW loss / NDC * hours)
- **EMDH** = Equivalent Maintenance Derated Hours = Sum of (D4 MW loss / NDC * hours)
- **EFDH** = Equivalent Forced Derated Hours = Sum of (D1+D2+D3 MW loss / NDC * hours)
- **EUDH** = Equivalent Unplanned Derated Hours = EFDH + EMDH
- **AH** = Available Hours = SH + RSH + Synchronous Condensing Hours + Pumping Hours
- **NDC** = Net Dependable Capacity (MW)
- **NMC** = Net Maximum Capacity (MW)
- **AG** = Actual Generation (MWh net)

## Indexes

**Equivalent Availability Factor (EAF)**
```
EAF = [(AH - EPDH - EUDH) / PH] x 100%
```
Percentage of time the unit was available at full capacity, counting partial
derates as equivalent full outage hours.

**Equivalent Forced Outage Rate (EFOR)**
```
EFOR = [(FOH + EFDH) / (FOH + EFDH + SH)] x 100%
```
Probability the unit is unavailable due to forced outages or forced derates when
needed. Verify the current industry average and top-quartile figures at runtime
from the NERC GADS statistical brochures (see thresholds-and-deadlines.md).

**Equivalent Forced Outage Rate - demand (EFORd)**
```
EFORd = [f * FOHd + fp * EFDHd] / [f * (FOHd + SHd) + fp * (EFDHd + SHd_active)]
```
Where f = frequency of forced outage occurrences, fp = frequency of forced
derate occurrences, FOHd = forced outage hours during demand periods, EFDHd =
equivalent forced derated hours during demand periods, SHd = service hours
during demand periods. Weighted by demand periods; used in capacity market
calculations.

**Net Capacity Factor (NCF)**
```
NCF = [AG / (PH x NMC)] x 100%
```

**Gross Capacity Factor (GCF)**
```
GCF = [Gross Generation / (PH x Gross Maximum Capacity)] x 100%
```

**Service Factor (SF)**
```
SF = [SH / PH] x 100%
```

**Forced Outage Factor (FOF)**
```
FOF = [FOH / PH] x 100%
```

**Gross Output Factor (GOF)**
```
GOF = [Actual Gross Generation / (SH x Gross Maximum Capacity)] x 100%
```

**Availability Factor (AF)**
```
AF = [AH / PH] x 100%
```

**Planned Outage Factor (POF)**
```
POF = [(POH + EPDH) / PH] x 100%
```

**Maintenance Outage Factor (MOF)**
```
MOF = [(MOH + EMDH) / PH] x 100%
```

**Forced Outage Rate (FOR)**
```
FOR = [FOH / (FOH + SH)] x 100%
```

**Mean Time Between Failures (MTBF)**
```
MTBF = SH / Number of forced outage occurrences
```

**Mean Time To Repair (MTTR)**
```
MTTR = FOH / Number of forced outage occurrences
```
