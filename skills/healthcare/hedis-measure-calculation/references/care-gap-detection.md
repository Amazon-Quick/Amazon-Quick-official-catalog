# Care Gap Detection

Detect open care gaps across a population and rank them by a priority score that blends star weight and member risk.

## Python

```python
"""Detect and prioritize open care gaps across members."""
import pandas as pd
from datetime import date


def detect_care_gaps(
    members: pd.DataFrame,
    measures: list[dict],
    claims: pd.DataFrame,
    measurement_year: int = 2025,
) -> pd.DataFrame:
    """Detect open care gaps for a population.

    Args:
        members: DataFrame [member_id, date_of_birth, gender, risk_score].
        measures: List of dicts with keys: measure_id, age_min, age_max,
            gender (str|None), diagnosis_codes (list), numerator_codes (list),
            star_weight (1 or 3).
        claims: DataFrame [member_id, service_date, diagnosis_code, procedure_code].
        measurement_year: Calendar year for measurement.

    Returns:
        DataFrame: [member_id, measure_id, star_weight, risk_score, priority_score].
    """
    anchor = date(measurement_year, 12, 31)
    year_start = date(measurement_year, 1, 1)
    gaps = []
    for measure in measures:
        eligible = members.copy()
        eligible["age"] = eligible["date_of_birth"].apply(lambda d: (anchor - d).days // 365)
        eligible = eligible[eligible["age"].between(measure["age_min"], measure["age_max"])]
        if measure.get("gender"):
            eligible = eligible[eligible["gender"] == measure["gender"]]
        if measure.get("diagnosis_codes"):
            dx_members = claims[
                claims["diagnosis_code"].str.startswith(tuple(measure["diagnosis_codes"]))
            ]["member_id"].unique()
            eligible = eligible[eligible["member_id"].isin(dx_members)]
        year_claims = claims[claims["service_date"].between(str(year_start), str(anchor))]
        closed = year_claims[
            year_claims["procedure_code"].isin(measure["numerator_codes"])
        ]["member_id"].unique()
        for _, row in eligible[~eligible["member_id"].isin(closed)].iterrows():
            sw = measure.get("star_weight", 1)
            gaps.append({
                "member_id": row["member_id"], "measure_id": measure["measure_id"],
                "star_weight": sw, "risk_score": row.get("risk_score", 0),
                "priority_score": round(sw * 30 + min(row.get("risk_score", 0) * 25, 25) + 20, 1),
            })
    return pd.DataFrame(gaps).sort_values("priority_score", ascending=False).reset_index(drop=True)
```

Key parameters: `measurement_year` sets the anchor date (December 31) used for age; `star_weight` and `risk_score` drive `priority_score` so triple-weighted measures and higher-risk members surface first. Age is computed as of the anchor date, not the run date.
