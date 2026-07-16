# Clinical Feature Extraction

Feature extraction turns a parsed PA request plus claims, formulary, and lab data into
a single feature vector for adjudication. It uses pandas, which is available in the
Amazon Quick `run_python` sandbox.

## Feature Set for PA Adjudication

| Feature | Source | Type | Description |
|---------|--------|------|-------------|
| `dx_specificity` | Diagnosis codes | int | ICD-10 code length (3 is category, 4 to 7 is specific) |
| `drug_class` | Service code (NDC/HCPCS) | categorical | Therapeutic class (for example biologic, opioid) |
| `prior_treatment_count` | Claims history | int | Number of prior drugs tried in same class |
| `step_therapy_complete` | Claims and formulary | bool | All required prior steps documented |
| `days_since_last_treatment` | Claims history | int | Gap since last related treatment |
| `lab_value_in_range` | Lab results | bool | Key lab (for example HbA1c) meets threshold |
| `provider_specialty` | Provider data | categorical | Specialty of ordering provider |
| `place_of_service` | Claim | categorical | Office, outpatient, inpatient, home |
| `prior_pa_denials` | PA history | int | Count of prior denials for same service |
| `documentation_score` | Supporting info | float | Completeness score (0 to 1) based on required docs |

## Feature Extraction Code

```python
"""Extract clinical features from parsed PA request + claims history."""
import pandas as pd
from datetime import datetime


def extract_features(
    pa_request: dict,
    claims_history: pd.DataFrame,
    formulary: pd.DataFrame,
    lab_results: pd.DataFrame,
) -> dict:
    """Build feature vector for PA adjudication model.

    Args:
        pa_request: Parsed PA request (from parse_278 or parse_pas_bundle).
        claims_history: Member's prior claims with columns:
            [member_id, service_date, drug_class, ndc, diagnosis_code].
        formulary: Formulary table with columns:
            [ndc, tier, step_therapy_required, prior_drugs_required, drug_class].
        lab_results: Lab results with columns:
            [member_id, test_code, result_value, result_date].
    """
    member_id = pa_request.get("member_id", "")
    dx_codes = pa_request.get("diagnosis_codes", [])
    svc_codes = pa_request.get("service_codes", [])

    # Diagnosis specificity: max ICD-10 code length
    dx_specificity = max((len(c.replace(".", "")) for c in dx_codes), default=3)

    # Prior treatment count in same drug class
    requested_drug = svc_codes[0] if svc_codes else ""
    drug_info = formulary[formulary["ndc"] == requested_drug]
    drug_class = drug_info["drug_class"].iloc[0] if len(drug_info) > 0 else "unknown"
    member_claims = claims_history[claims_history["member_id"] == member_id]
    prior_treatments = member_claims[member_claims["drug_class"] == drug_class]
    prior_treatment_count = prior_treatments["ndc"].nunique()

    # Step therapy completion
    required_steps = int(drug_info["prior_drugs_required"].iloc[0]) if len(drug_info) > 0 else 0
    step_therapy_complete = prior_treatment_count >= required_steps

    # Days since last treatment in class
    if len(prior_treatments) > 0:
        last_date = pd.to_datetime(prior_treatments["service_date"]).max()
        days_since = (datetime.now() - last_date).days
    else:
        days_since = -1  # no prior treatment

    # Lab value check (example: HbA1c for diabetes drugs)
    member_labs = lab_results[lab_results["member_id"] == member_id]
    recent_lab = member_labs.sort_values("result_date", ascending=False).head(1)
    lab_in_range = bool(recent_lab["result_value"].iloc[0] >= 7.0) if len(recent_lab) > 0 else False

    # Documentation completeness score
    supporting_info = pa_request.get("supporting_info_types", [])
    required_docs = {"clinical-note", "lab-result", "treatment-history", "diagnosis"}
    doc_score = len(set(supporting_info) & required_docs) / len(required_docs)

    return {
        "dx_specificity": dx_specificity,
        "drug_class": drug_class,
        "prior_treatment_count": prior_treatment_count,
        "step_therapy_complete": step_therapy_complete,
        "days_since_last_treatment": days_since,
        "lab_value_in_range": lab_in_range,
        "documentation_score": doc_score,
    }
```

Gotcha: every feature must use only data available at or before the moment of PA
submission. Deriving a feature from the eventual outcome or from post-submission claims
leaks future data and inflates training performance while failing in production. See
`references/reference-tables.md` for the documentation completeness weighting.
