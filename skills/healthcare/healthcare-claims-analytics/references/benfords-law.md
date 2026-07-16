# Benford's Law Analysis

Test whether the first-digit distribution of charge amounts follows Benford's Law, using a
manually computed chi-square statistic. scipy is not available in the Amazon Quick sandbox,
so this uses numpy and the standard-library `math` module only.

## Inputs

A pandas Series of charge amounts. Optionally a `provider_id` label for the result.

## Code

```python
import math
import pandas as pd
import numpy as np

BENFORD = {1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
           5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046}


def _chi2_sf(x: float, df: int = 8) -> float:
    """Upper-tail p-value of the chi-square distribution for even df. Exact, no scipy."""
    if x <= 0:
        return 1.0
    k = df // 2
    half = x / 2.0
    term = math.exp(-half)
    total = term
    for i in range(1, k):
        term *= half / i
        total += term
    return min(1.0, total)


def benfords_test(charges: pd.Series, provider_id: str = "") -> dict:
    """Test charge first-digit distribution against Benford's Law (df = 8)."""
    first = charges[charges >= 10].apply(lambda x: int(str(x).lstrip("0").lstrip(".")[0]))
    first = first[first.between(1, 9)]
    counts = first.value_counts().sort_index()
    n = counts.sum()
    obs = np.array([counts.get(d, 0) for d in range(1, 10)], dtype=float)
    exp = np.array([BENFORD[d] * n for d in range(1, 10)])
    chi2 = float(((obs - exp) ** 2 / exp).sum())
    p = _chi2_sf(chi2, df=8)
    return {"provider_id": provider_id, "chi2": round(chi2, 2),
            "p_value": round(p, 4), "flag": p < 0.01}
```

## Key parameters

- p-value threshold: default 0.01. Use 0.05 for initial screening.
- Charge floor: only charges of $10 or more are analyzed (see pitfalls).

## Pitfalls

- Do not run the first-digit test on charges below $10. Filter to charges of $10 or more
  first; Benford's Law applies to data spanning multiple orders of magnitude, and low-value
  charges are constrained by fee schedules, so they naturally violate Benford's and produce
  false positives.
- The p-value helper is exact only for even degrees of freedom. With nine first-digit buckets
  the test has 8 degrees of freedom, which is even, so the closed form applies.
