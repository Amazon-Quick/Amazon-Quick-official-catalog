# Risk Stratification Scoring

Two independent scores: the Charlson Comorbidity Index from diagnosis codes, and the LACE index for 30-day readmission risk.

## Charlson Comorbidity Index (Python)

```python
"""Calculate Charlson Comorbidity Index from diagnosis codes."""

# ICD-10 prefix -> (condition, weight). Subset of key mappings.
CHARLSON_MAP = {
    "I21": ("mi", 1), "I22": ("mi", 1), "I50": ("chf", 1),
    "I70": ("pvd", 1), "I71": ("pvd", 1), "I6": ("cvd", 1),
    "F01": ("dementia", 1), "F03": ("dementia", 1), "G30": ("dementia", 1),
    "J4": ("copd", 1), "M05": ("ctd", 1), "M06": ("ctd", 1),
    "K25": ("pud", 1), "K26": ("pud", 1),
    "K70": ("mild_liver", 1), "K73": ("mild_liver", 1), "K74": ("mild_liver", 1),
    "E109": ("dm_uncomp", 1), "E119": ("dm_uncomp", 1),
    "E102": ("dm_comp", 2), "E112": ("dm_comp", 2),
    "G81": ("hemiplegia", 2), "N18": ("renal", 2),
    "C": ("cancer", 2),
    "C77": ("metastatic", 6), "C78": ("metastatic", 6), "C79": ("metastatic", 6),
    "B20": ("hiv", 6),
}


def charlson_score(diagnosis_codes: list[str]) -> dict:
    """Calculate Charlson Comorbidity Index. Returns {score, conditions}."""
    matched: dict[str, int] = {}
    for code in [c.replace(".", "") for c in diagnosis_codes]:
        for prefix, (cond, wt) in CHARLSON_MAP.items():
            if code.startswith(prefix):
                if cond == "cancer" and "metastatic" in matched:
                    continue
                if cond == "metastatic":
                    matched.pop("cancer", None)
                if cond == "dm_uncomp" and "dm_comp" in matched:
                    continue
                if cond == "dm_comp":
                    matched.pop("dm_uncomp", None)
                if cond not in matched or wt > matched[cond]:
                    matched[cond] = wt
                break
    return {"score": sum(matched.values()), "conditions": matched}
```

The hierarchy logic keeps only the more severe of paired conditions (metastatic over cancer, complicated over uncomplicated diabetes).

## LACE Readmission Risk Score (Python)

```python
"""Calculate LACE readmission risk score."""


def lace_score(length_of_stay: int, acuity: str, charlson: int, ed_visits_6mo: int) -> dict:
    """Calculate LACE index for 30-day readmission risk.

    Returns dict with total score, component scores, and risk tier.
    """
    l = 7 if length_of_stay >= 14 else (5 if length_of_stay >= 7 else (4 if length_of_stay >= 4 else min(length_of_stay, 3)))
    a = {"emergent": 3, "urgent": 2, "elective": 0}.get(acuity.lower(), 0)
    c = 5 if charlson >= 4 else min(charlson, 3)
    e = min(ed_visits_6mo, 4)
    total = l + a + c + e
    tier = "high" if total >= 10 else ("moderate" if total >= 5 else "low")
    return {"total": total, "components": {"L": l, "A": a, "C": c, "E": e}, "risk_tier": tier}
```

LACE combines Length of stay, Acuity of admission, Charlson comorbidity, and Emergency visits in the prior six months. Feed the Charlson score above in as the `charlson` argument.
