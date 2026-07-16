# E&M Provider Profiling

Compare each provider's Evaluation and Management (E&M) code distribution to same-specialty
peers using z-scores, and flag statistical upcoding toward 99214 and 99215.

## Inputs

A claims DataFrame with columns: `provider_id`, `specialty`, `proc_code`. For the SQL
version, a `claims` table with the same columns.

## Python

```python
import pandas as pd
import numpy as np

EM_CODES = ["99202", "99203", "99204", "99205", "99211", "99212", "99213", "99214", "99215"]


def profile_em_distribution(claims_df: pd.DataFrame) -> pd.DataFrame:
    """Compare each provider's E&M distribution to specialty peers via z-scores."""
    em = claims_df[claims_df["proc_code"].isin(EM_CODES)].copy()

    prov_dist = em.groupby(["provider_id", "specialty", "proc_code"]).size().unstack(fill_value=0)
    prov_pct = prov_dist.div(prov_dist.sum(axis=1), axis=0)

    spec_mean = prov_pct.groupby("specialty").mean()
    spec_std = prov_pct.groupby("specialty").std()

    results = []
    for (prov, spec), row in prov_pct.iterrows():
        if spec not in spec_mean.index:
            continue
        z = (row - spec_mean.loc[spec]) / spec_std.loc[spec].replace(0, np.nan)
        results.append(
            {
                "provider_id": prov,
                "specialty": spec,
                "total_em": int(prov_dist.loc[(prov, spec)].sum()),
                "pct_99214_99215": row.get("99214", 0) + row.get("99215", 0),
                "z_99214": z.get("99214", np.nan),
                "z_99215": z.get("99215", np.nan),
                "flag_upcoding": z.get("99214", 0) > 2.0 or z.get("99215", 0) > 2.0,
            }
        )
    return pd.DataFrame(results).sort_values("z_99215", ascending=False)
```

## SQL

```sql
WITH provider_em AS (
    SELECT provider_id, specialty, proc_code, COUNT(*) AS cnt
    FROM claims
    WHERE proc_code IN ('99202','99203','99204','99205','99211','99212','99213','99214','99215')
    GROUP BY provider_id, specialty, proc_code
),
provider_total AS (
    SELECT provider_id, specialty, SUM(cnt) AS total FROM provider_em GROUP BY provider_id, specialty
),
provider_pct AS (
    SELECT e.provider_id, e.specialty, e.proc_code, t.total,
           ROUND(e.cnt * 100.0 / t.total, 2) AS pct
    FROM provider_em e JOIN provider_total t ON e.provider_id = t.provider_id
),
benchmark AS (
    SELECT specialty, proc_code, AVG(pct) AS avg_pct, STDDEV(pct) AS std_pct
    FROM provider_pct GROUP BY specialty, proc_code
)
SELECT p.provider_id, p.specialty, p.proc_code, p.pct, b.avg_pct,
       ROUND((p.pct - b.avg_pct) / NULLIF(b.std_pct, 0), 2) AS z_score
FROM provider_pct p
JOIN benchmark b ON p.specialty = b.specialty AND p.proc_code = b.proc_code
WHERE ABS((p.pct - b.avg_pct) / NULLIF(b.std_pct, 0)) > 2.0
ORDER BY z_score DESC;
```

## Key parameters

- z-score threshold: default 2.0. Lower to 1.5 for more sensitive screening.

## Pitfalls

- Do not benchmark against a single national average. Compare against same-specialty,
  same-region, same-payer-mix peers; specialty and geography drive legitimate variation, so
  a cardiologist's 99214 rate is naturally higher than a pediatrician's.
