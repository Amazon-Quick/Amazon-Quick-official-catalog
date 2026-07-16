# Duplicate Claim Detection

Detect exact and near-duplicate claim submissions for the same member, provider, procedure,
and date window.

## Inputs

A claims DataFrame with columns: `claim_id`, `member_id`, `provider_id`, `proc_code`,
`service_date` (as datetime). For the SQL version, a `claims` table with the same columns.

## Python

```python
import pandas as pd


def detect_duplicates(claims_df: pd.DataFrame, fuzzy_window_days: int = 3) -> pd.DataFrame:
    """Detect exact and near-duplicate claims."""
    key_cols = ["member_id", "provider_id", "proc_code", "service_date"]
    exact = claims_df[claims_df.duplicated(subset=key_cols, keep=False)].copy()
    exact["dup_type"] = "exact"

    s = claims_df.sort_values(key_cols)
    s["prev_date"] = s.groupby(key_cols[:3])["service_date"].shift(1)
    s["gap"] = (s["service_date"] - s["prev_date"]).dt.days
    near = s[(s["gap"] > 0) & (s["gap"] <= fuzzy_window_days)].copy()
    near["dup_type"] = "near"

    cols = ["claim_id", "member_id", "provider_id", "proc_code", "service_date", "dup_type"]
    return pd.concat([exact[cols], near[cols]])
```

## SQL

```sql
-- Exact duplicates
SELECT a.claim_id AS id_1, b.claim_id AS id_2, a.member_id, a.proc_code, a.service_date
FROM claims a JOIN claims b
  ON a.member_id = b.member_id AND a.provider_id = b.provider_id
  AND a.proc_code = b.proc_code AND a.service_date = b.service_date
  AND a.claim_id < b.claim_id;

-- Near-duplicates (within 3 days)
SELECT a.claim_id AS id_1, b.claim_id AS id_2, a.member_id, a.proc_code,
       a.service_date AS date_1, b.service_date AS date_2
FROM claims a JOIN claims b
  ON a.member_id = b.member_id AND a.provider_id = b.provider_id
  AND a.proc_code = b.proc_code AND a.claim_id < b.claim_id
  AND ABS(DATEDIFF(a.service_date, b.service_date)) BETWEEN 1 AND 3;
```

## Key parameters

- `fuzzy_window_days`: default 3. Increase to 7 for post-acute care.

## Pitfalls

- Do not flag all exact duplicates as fraud. Distinguish true duplicates (the same claim
  resubmitted) from legitimate corrections (different claim IDs with adjustment reason codes).
  Payers routinely reprocess claims with new claim IDs after corrections; only same-claim-ID
  resubmissions without adjustment reason codes are suspect.
