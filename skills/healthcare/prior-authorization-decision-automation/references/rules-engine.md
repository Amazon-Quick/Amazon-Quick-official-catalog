# Rules-Based Adjudication Engine

A deterministic rules engine is the audit-defensible core of PA automation. It runs on
the Python standard library, so it works in the Amazon Quick `run_python` sandbox and
in an external environment. Use it for clear-cut policy criteria (step therapy, age,
lab thresholds) and route only ambiguous cases to a machine learning model (see
`references/ml-classifier.md`).

```python
"""Rules-based PA adjudication engine."""
from dataclasses import dataclass
from enum import Enum


class Decision(Enum):
    APPROVE = "approve"
    DENY = "deny"
    PEND = "pend"


@dataclass
class AdjudicationResult:
    decision: Decision
    reason_code: str
    reason_text: str


def adjudicate(features: dict, policy: dict) -> AdjudicationResult:
    """Apply rules-based adjudication logic.

    Args:
        features: Feature dict from extract_features().
        policy: Policy config with keys:
            - require_step_therapy (bool)
            - min_dx_specificity (int)
            - min_documentation_score (float)
            - require_lab_in_range (bool)
    """
    # Rule 1: Documentation completeness
    if features["documentation_score"] < policy.get("min_documentation_score", 0.75):
        return AdjudicationResult(
            Decision.PEND, "PEND-001", "Insufficient documentation; request additional clinical records"
        )
    # Rule 2: Diagnosis specificity
    if features["dx_specificity"] < policy.get("min_dx_specificity", 4):
        return AdjudicationResult(
            Decision.DENY, "DENY-DX", "Diagnosis code lacks required specificity"
        )
    # Rule 3: Step therapy
    if policy.get("require_step_therapy", True) and not features["step_therapy_complete"]:
        return AdjudicationResult(
            Decision.DENY, "DENY-STEP", "Step therapy requirements not met"
        )
    # Rule 4: Lab value threshold
    if policy.get("require_lab_in_range", False) and not features["lab_value_in_range"]:
        return AdjudicationResult(
            Decision.DENY, "DENY-LAB", "Required lab value not within criteria range"
        )
    # All rules passed
    return AdjudicationResult(Decision.APPROVE, "APPROVE-001", "All clinical criteria met")
```

Key design points:

- Order matters. Documentation completeness is checked first because an incomplete
  request should pend for more records rather than deny on the merits.
- `policy` is passed in per payer. Each payer has independent clinical policies, so keep
  one policy config per payer rather than a shared default.
- Reason codes are standardized enums, not free text. See the reason code reference in
  `references/denial-analysis.md`. Map them to CARC/RARC codes for downstream systems
  rather than matching free-text strings.
- A PEND outcome is not a denial. It signals a recoverable documentation gap and should
  route to a work queue, not to the denial pipeline.
