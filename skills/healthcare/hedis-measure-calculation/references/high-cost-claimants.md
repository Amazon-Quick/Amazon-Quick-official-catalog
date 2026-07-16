# High-Cost Claimant Identification

Identify members whose total paid amount exceeds a percentile threshold and report their share of total spend.

## Python

```python
"""Identify high-cost claimants and analyze cost drivers."""
import pandas as pd
import numpy as np


def identify_high_cost_claimants(
    claims: pd.DataFrame,
    threshold_percentile: float = 95,
    measurement_year: int = 2025,
) -> dict:
    """Identify high-cost claimants above a percentile threshold.

    Args:
        claims: DataFrame [member_id, service_date, paid_amount, claim_type, diagnosis_code].
        threshold_percentile: Percentile cutoff (default 95th).
        measurement_year: Calendar year to analyze.

    Returns:
        Dict with threshold, count, pct of total spend, and member DataFrame.
    """
    year_claims = claims[
        pd.to_datetime(claims["service_date"]).dt.year == measurement_year
    ]
    member_costs = (
        year_claims.groupby("member_id")
        .agg(total_paid=("paid_amount", "sum"), claim_count=("paid_amount", "count"))
        .reset_index()
    )
    threshold = np.percentile(member_costs["total_paid"], threshold_percentile)
    high_cost = member_costs[member_costs["total_paid"] >= threshold].sort_values(
        "total_paid", ascending=False
    )
    return {
        "threshold_amount": round(threshold, 2),
        "high_cost_count": len(high_cost),
        "high_cost_pct_of_total": round(
            high_cost["total_paid"].sum() / member_costs["total_paid"].sum() * 100, 1
        ),
        "high_cost_members": high_cost,
    }
```

Key parameters: `threshold_percentile` (95th default) sets the cutoff; `measurement_year` scopes the claims. Costs are aggregated per member before the percentile is applied, so a member is ranked on total annual spend rather than individual claims.
