# NCCI Edit Validation

Validate claims against National Correct Coding Initiative (NCCI) code-pair edits and return
violations, honoring modifier indicators and the edit's active date range.

## Inputs

- `claims_df`: columns `claim_id`, `provider_id`, `member_id`, `service_date`, `proc_code`, `modifier_1`.
- `ncci_edits`: columns `column1_cpt`, `column2_cpt`, `modifier_indicator`, `effective_date`, `deletion_date`.

Source the current NCCI edit table quarterly from the Centers for Medicare and Medicaid
Services (CMS).

## Code

```python
import pandas as pd


def validate_ncci(claims_df: pd.DataFrame, ncci_edits: pd.DataFrame) -> pd.DataFrame:
    """Validate claims against NCCI edits. Returns violations."""
    violations = []
    for (prov, mem, dt), grp in claims_df.groupby(["provider_id", "member_id", "service_date"]):
        codes = grp["proc_code"].tolist()
        mods = grp["modifier_1"].fillna("").tolist()

        for i, c1 in enumerate(codes):
            for j, c2 in enumerate(codes):
                if i >= j:
                    continue
                for col1, col2, mi in [(c1, c2, j), (c2, c1, i)]:
                    match = ncci_edits[
                        (ncci_edits["column1_cpt"] == col1)
                        & (ncci_edits["column2_cpt"] == col2)
                        & (ncci_edits["effective_date"] <= dt)
                        & (ncci_edits["deletion_date"].isna() | (ncci_edits["deletion_date"] > dt))
                    ]
                    if match.empty:
                        continue
                    ind = match.iloc[0]["modifier_indicator"]
                    has_mod = mods[mi] in ("59", "XE", "XS", "XP", "XU")
                    if ind == "0" or (ind == "1" and not has_mod):
                        violations.append(
                            {
                                "provider_id": prov,
                                "member_id": mem,
                                "service_date": dt,
                                "column1_cpt": col1,
                                "column2_cpt": col2,
                                "modifier_indicator": ind,
                                "status": "DENIED" if ind == "0" else "DENIED - modifier required",
                            }
                        )
    return pd.DataFrame(violations)
```

## Key parameters

- NCCI edit file: update quarterly from CMS.
- Modifier indicator: `0` means the pair can never be unbundled; `1` means a valid modifier
  (59, XE, XS, XP, XU) allows separate payment.

## Pitfalls

- Do not apply edits without checking effective and deletion dates. Filter to edits active on
  the claim's date of service with `effective_date <= service_date` and
  `(deletion_date IS NULL OR deletion_date > service_date)`. NCCI edits are versioned
  quarterly, so applying current edits to historical claims produces false violations.
