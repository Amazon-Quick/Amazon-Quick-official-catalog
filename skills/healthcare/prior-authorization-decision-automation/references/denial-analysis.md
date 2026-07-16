# Denial Reason Analysis

Denial pattern analysis identifies systemic documentation or policy gaps across a book
of PA decisions. It uses pandas, which is available in the Amazon Quick `run_python`
sandbox.

## Denial Pattern Analysis

```python
"""Analyze PA denial patterns to identify systemic issues."""
import pandas as pd


def analyze_denials(
    pa_decisions: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """Analyze denial patterns across dimensions.

    Args:
        pa_decisions: DataFrame with columns
            [pa_id, member_id, provider_npi, drug_class, denial_reason, decision, decision_date].
        group_cols: Columns to group by. Defaults to [denial_reason, drug_class, provider_npi].
    """
    denied = pa_decisions[pa_decisions["decision"] == "denied"].copy()
    if group_cols is None:
        group_cols = ["denial_reason", "drug_class", "provider_npi"]
    analyses = {}
    for col in group_cols:
        if col not in denied.columns:
            continue
        g = (
            denied.groupby(col)
            .agg(denial_count=("pa_id", "count"), unique_members=("member_id", "nunique"))
            .sort_values("denial_count", ascending=False)
            .reset_index()
        )
        g["pct_of_denials"] = (g["denial_count"] / len(denied) * 100).round(1)
        analyses[col] = g
    if "denial_reason" in denied.columns:
        doc_gaps = denied[
            denied["denial_reason"].str.contains("documentation|insufficient", case=False, na=False)
        ]
        analyses["documentation_gaps"] = (
            doc_gaps.groupby("drug_class")
            .agg(gap_count=("pa_id", "count"))
            .sort_values("gap_count", ascending=False)
            .reset_index()
        )
    return analyses
```

## Denial Reason Code Reference

| Reason Code | Description | Remediation |
|-------------|-------------|-------------|
| DENY-STEP | Step therapy not completed | Document prior treatments with dates |
| DENY-DX | Non-specific diagnosis | Use highest-specificity ICD-10 code |
| DENY-LAB | Lab criteria not met | Resubmit with current lab results |
| DENY-MN | Medical necessity not established | Submit letter of medical necessity |
| DENY-EXP | Experimental or investigational | Cite peer-reviewed evidence |
| PEND-001 | Incomplete documentation | Submit clinical notes, labs, history |

These codes are the same enums returned by the rules engine
(`references/rules-engine.md`). Map them to standardized CARC/RARC codes for downstream
remittance and appeals systems rather than matching on free text.
