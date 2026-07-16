# Impossible Day Detection

Flag providers who bill more than 24 hours of time-based services in a single day, using CPT
time estimates.

## Inputs

A claims DataFrame with columns: `provider_id`, `service_date`, `proc_code`, `units`,
`claim_id`.

## Code

```python
import pandas as pd

CPT_MINUTES = {
    "99213": 15, "99214": 25, "99215": 40, "99203": 30, "99204": 45, "99205": 60,
    "90837": 53, "90834": 38, "97110": 15, "97140": 15, "99291": 74, "99292": 30,
}


def detect_impossible_days(claims_df: pd.DataFrame, max_min: int = 1440) -> pd.DataFrame:
    """Flag providers billing more than 24 hours of services in a single day."""
    df = claims_df.copy()
    df["est_min"] = df["proc_code"].map(CPT_MINUTES).fillna(0) * df["units"].fillna(1)
    daily = (
        df.groupby(["provider_id", "service_date"])
        .agg(total_min=("est_min", "sum"), claims=("claim_id", "nunique"))
        .reset_index()
    )
    return daily[daily["total_min"] > max_min].sort_values("total_min", ascending=False)
```

## Key parameters

- `max_min`: default 1440 (24 hours). Reduce to 960 (16 hours) for a stricter threshold.
- `CPT_MINUTES`: extend this map with the time-based codes relevant to your data.

## Pitfalls

- Do not sum CPT time estimates without accounting for concurrent services. Distinguish
  sequential time-based services from ones that legitimately overlap (for example infusion
  supervision during an E&M visit, or teaching-physician attestation). Only sum
  non-overlapping service minutes; naive summation inflates minutes and produces false flags.
