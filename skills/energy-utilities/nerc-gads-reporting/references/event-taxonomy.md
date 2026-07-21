# NERC GADS Event Type Taxonomy

Classify every event record against the codes below, following the NERC GADS
Data Reporting Instructions (DRI). When a record is ambiguous, flag it for user
review rather than guessing.

## Outage Events (unit at zero output)

| Code | Name | Definition | Urgency |
|------|------|-----------|---------|
| U1 | Unplanned (Forced) Outage - Immediate | Requires immediate removal from service. No time for startup or load pickup. | Within same minute of occurrence |
| U2 | Unplanned (Forced) Outage - Delayed | Permits postponement beyond 6 hours but requires removal within the same weekend | 6 hours to end of next weekend |
| U3 | Unplanned (Forced) Outage - Postponed | Can be postponed beyond the end of the next weekend but requires unit removal before the next planned outage | Beyond weekend, before next PO |
| MO | Maintenance Outage | Outage deferrable beyond the next planned outage but requiring removal within the current operating period (operating quarter/season) | Within current operating period |
| PO | Planned Outage | Outage scheduled well in advance (typically 4+ weeks) for maintenance, overhaul, or modification | Scheduled well in advance |
| ME | Maintenance Outage Extension | Extension of a maintenance outage beyond original scope | Related event only |
| PE | Planned Outage Extension | Extension of a planned outage beyond original scope | Related event only |
| SF | Startup Failure | Unit fails to synchronize within a specified period after startup is initiated | Related event only |

## Derate Events (unit at reduced capacity)

| Code | Name | Definition |
|------|------|-----------|
| D1 | Unplanned (Forced) Derating - Immediate | Requires immediate reduction in capacity |
| D2 | Unplanned (Forced) Derating - Delayed | Derate can be delayed 6 hours to end of next weekend |
| D3 | Unplanned (Forced) Derating - Postponed | Derate can be postponed beyond next weekend |
| D4 | Maintenance Derating | Derate within current operating period |
| DM | Maintenance Derating Extension | Related event extension |
| PD | Planned Derating | Scheduled well in advance |
| DP | Planned Derating Extension | Related event extension |

## Other Active Events

| Code | Name | Definition |
|------|------|-----------|
| RS | Reserve Shutdown | Unit available but not generating due to lack of demand |
| NC | Non-Curtailing Event | Equipment removed but unit capacity not reduced |

## Inactive State Events

| Code | Name | Definition |
|------|------|-----------|
| IR | Inactive Reserve | Unit unavailable, can return after repairs (>60 days, related to RS) |
| MB | Mothballed | Unit unavailable, can return with appropriate notice (>60 days) |
| RU | Retired | Unit permanently removed from service |
