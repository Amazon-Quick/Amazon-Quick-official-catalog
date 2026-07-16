# HEDIS Measure Structure

Every Healthcare Effectiveness Data and Information Set (HEDIS) measure resolves
to a rate built from an eligible population, exclusions, and a numerator.

```
Eligible Population (Denominator)
  minus Exclusions
  equals Eligible Denominator
  Numerator (members who met the quality criteria)
  Rate = Numerator / Eligible Denominator
```

## Components

| Component | Definition | Example (Comprehensive Diabetes Care, HbA1c) |
|-----------|-----------|----------------------------------------------|
| Denominator | Members eligible based on age, diagnosis, enrollment | Age 18 to 75, diabetes (E11.x), continuously enrolled |
| Exclusions | Members removed due to clinical exceptions | Hospice, end-stage renal disease, organ transplant |
| Numerator | Members who met the quality criteria | HbA1c test performed during measurement year |
| Rate | Numerator divided by (Denominator minus Exclusions) | Percentage with HbA1c testing |

## Five measure types

- Process: a service was delivered.
- Outcome: a clinical result was achieved.
- Structural: a system capability exists.
- Patient experience: survey-based (Consumer Assessment of Healthcare Providers and Systems, CAHPS).
- Utilization: resource consumption.

## Watch out

- Do not merge process and outcome sub-measures. HbA1c testing (process) and
  HbA1c control below 8 percent (outcome) are separate rates.
- Compute the rate only after exclusions are subtracted from the full denominator.
