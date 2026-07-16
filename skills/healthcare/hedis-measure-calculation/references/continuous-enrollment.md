# Continuous Enrollment Check

Determine whether a member is continuously enrolled through the measurement period, allowing a total gap up to `max_gap_days` (HEDIS default 45).

## Python

```python
"""Check continuous enrollment with allowable gap."""
import pandas as pd


def check_continuous_enrollment(
    enrollment: pd.DataFrame, member_id: str,
    start_date: str, end_date: str, max_gap_days: int = 45,
) -> dict:
    """Check if a member is continuously enrolled with allowable gap.

    Args:
        enrollment: DataFrame [member_id, enroll_start, enroll_end].
        member_id: Member to check.
        start_date: Measurement period start (e.g., '2025-01-01').
        end_date: Measurement period end / anchor date (e.g., '2025-12-31').
        max_gap_days: Maximum allowable gap in days (HEDIS default: 45).

    Returns:
        Dict with is_enrolled (bool), total_gap_days (int), gap_periods (list).
    """
    start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    me = enrollment[enrollment["member_id"] == member_id].copy()
    me["enroll_start"] = pd.to_datetime(me["enroll_start"]).clip(lower=start)
    me["enroll_end"] = pd.to_datetime(me["enroll_end"]).clip(upper=end)
    me = me[me["enroll_start"] <= me["enroll_end"]].sort_values("enroll_start").reset_index(drop=True)
    if me.empty:
        return {"is_enrolled": False, "total_gap_days": (end - start).days, "gap_periods": []}
    if not (me["enroll_end"] >= end).any():
        return {"is_enrolled": False, "total_gap_days": -1, "gap_periods": []}
    gap_periods, total_gap = [], 0
    if me.iloc[0]["enroll_start"] > start:
        g = (me.iloc[0]["enroll_start"] - start).days
        total_gap += g
        gap_periods.append({"from": str(start.date()), "to": str(me.iloc[0]["enroll_start"].date()), "days": g})
    for i in range(1, len(me)):
        if me.iloc[i]["enroll_start"] > me.iloc[i - 1]["enroll_end"] + pd.Timedelta(days=1):
            g = (me.iloc[i]["enroll_start"] - me.iloc[i - 1]["enroll_end"]).days - 1
            total_gap += g
            gap_periods.append({"from": str(me.iloc[i - 1]["enroll_end"].date()), "to": str(me.iloc[i]["enroll_start"].date()), "days": g})
    return {"is_enrolled": total_gap <= max_gap_days, "total_gap_days": total_gap, "gap_periods": gap_periods}
```

For multi-payer enrollment, merge overlapping enrollment spans into a single set of segments before calling this, so shared coverage is not counted as a gap.

## SQL

```sql
-- Continuous enrollment check with allowable gap (<= 45 days)
WITH enrollment_segments AS (
    SELECT member_id, enroll_start, enroll_end,
           LEAD(enroll_start) OVER (PARTITION BY member_id ORDER BY enroll_start) AS next_start
    FROM enrollment
    WHERE enroll_end >= '2025-01-01' AND enroll_start <= '2025-12-31'
),
gaps AS (
    SELECT member_id,
           DATEDIFF(day, enroll_end, next_start) - 1 AS gap_days
    FROM enrollment_segments
    WHERE next_start IS NOT NULL
      AND DATEDIFF(day, enroll_end, next_start) > 1
),
total_gaps AS (
    SELECT member_id, SUM(gap_days) AS total_gap_days
    FROM gaps
    GROUP BY member_id
),
anchor_check AS (
    SELECT DISTINCT member_id
    FROM enrollment
    WHERE enroll_end >= '2025-12-31'
)
SELECT a.member_id,
       COALESCE(g.total_gap_days, 0) AS total_gap_days,
       CASE WHEN COALESCE(g.total_gap_days, 0) <= 45 THEN 1 ELSE 0 END AS is_continuously_enrolled
FROM anchor_check a
LEFT JOIN total_gaps g ON a.member_id = g.member_id;
```

Key parameters: `max_gap_days` (45 default), measurement period bounds, and the anchor date the member must be enrolled through.
