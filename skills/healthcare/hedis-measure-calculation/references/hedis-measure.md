# HEDIS Measure Rate Calculation

Compute a measure rate as numerator over eligible denominator, after removing exclusions. The Python calculator is generic across measures; the SQL example shows a full measure (Comprehensive Diabetes Care HbA1c testing).

## Python (generic measure calculator)

```python
"""Generic HEDIS measure rate calculator."""
import pandas as pd
from dataclasses import dataclass


@dataclass
class MeasureResult:
    measure_id: str
    denominator_count: int
    exclusion_count: int
    numerator_count: int
    rate: float
    gap_members: list[str]


def calculate_measure(
    eligible: pd.DataFrame,
    exclusions: pd.DataFrame,
    numerator_events: pd.DataFrame,
    measure_id: str,
) -> MeasureResult:
    """Calculate a HEDIS measure rate.

    Args:
        eligible: Denominator members. Columns: [member_id].
        exclusions: Excluded members. Columns: [member_id, exclusion_reason].
        numerator_events: Members meeting numerator. Columns: [member_id, event_date].
        measure_id: Measure identifier (e.g., 'CDC-HbA1c-Testing').

    Returns:
        MeasureResult with rate and gap member list.
    """
    denom_ids = set(eligible["member_id"])
    excl_ids = set(exclusions["member_id"])
    eligible_denom = denom_ids - excl_ids
    numer_ids = set(numerator_events["member_id"]) & eligible_denom
    gap_ids = eligible_denom - numer_ids
    denom_count = len(eligible_denom)
    rate = len(numer_ids) / denom_count if denom_count > 0 else 0.0
    return MeasureResult(
        measure_id=measure_id,
        denominator_count=denom_count,
        exclusion_count=len(excl_ids & denom_ids),
        numerator_count=len(numer_ids),
        rate=round(rate, 4),
        gap_members=sorted(gap_ids),
    )
```

The `set` intersection deduplicates numerator members automatically, so a member with multiple qualifying events counts once.

## SQL (full measure: Comprehensive Diabetes Care, HbA1c testing)

```sql
-- CDC: Comprehensive Diabetes Care, HbA1c Testing
WITH denominator AS (
    SELECT DISTINCT m.member_id
    FROM members m
    JOIN claims c ON m.member_id = c.member_id
    JOIN continuously_enrolled ce ON m.member_id = ce.member_id
    WHERE DATEDIFF(year, m.date_of_birth, '2025-12-31') BETWEEN 18 AND 75
      AND c.diagnosis_code LIKE 'E11%'
      AND c.service_date BETWEEN '2024-01-01' AND '2025-12-31'
      AND ce.is_continuously_enrolled = 1
),
exclusions AS (
    SELECT DISTINCT member_id FROM claims
    WHERE diagnosis_code IN ('Z51.5', 'N18.6')
       OR revenue_code IN ('0115','0125','0135','0145','0155','0235')
),
numerator AS (
    SELECT DISTINCT member_id FROM claims
    WHERE procedure_code IN ('83036','83037')
      AND service_date BETWEEN '2025-01-01' AND '2025-12-31'
)
SELECT COUNT(*) AS denom,
       SUM(CASE WHEN e.member_id IS NOT NULL THEN 1 ELSE 0 END) AS excluded,
       SUM(CASE WHEN e.member_id IS NULL AND n.member_id IS NOT NULL THEN 1 ELSE 0 END) AS numer,
       ROUND(SUM(CASE WHEN e.member_id IS NULL AND n.member_id IS NOT NULL THEN 1 ELSE 0 END) * 1.0
             / NULLIF(COUNT(*) - SUM(CASE WHEN e.member_id IS NOT NULL THEN 1 ELSE 0 END), 0), 4) AS rate
FROM denominator d
LEFT JOIN exclusions e ON d.member_id = e.member_id
LEFT JOIN numerator n ON d.member_id = n.member_id;
```

The diagnosis window spans two years (`2024-01-01` to `2025-12-31`) to honor the qualifying-condition lookback; the numerator window is the measurement year only. Confirm the value sets against current NCQA specifications for your measurement year.
