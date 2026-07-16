# National Committee for Quality Assurance (NCQA) Audit Requirements

## Data source hierarchy

| Source | Priority | Use for |
|--------|----------|---------|
| Administrative claims | Primary | Denominator, exclusions, process numerators |
| Electronic clinical data (ECDS) | Primary for ECDS measures | Lab results, vitals |
| Supplemental data | Secondary | Fills claims gaps (health information exchange lab results) |
| Medical record review | Tertiary | Validation, hybrid measures |

## Common audit findings

| Finding | Severity | Remediation |
|---------|----------|-------------|
| Supplemental data without source verification | High | Implement source validation |
| Enrollment gap calculation error | High | Revalidate against NCQA specifications |
| Incorrect age calculation | Medium | Use age as of the anchor date |
| Duplicate member counting | High | Deduplicate on member identifier |
| Stale value sets | Medium | Update code sets annually |

## Watch out

- Validate supplemental data with date, value, and provider before submission.
- Deduplicate on member identifier across enrollment segments so no member is
  counted more than once.
- Update ICD-10, CPT, and HCPCS value sets every measurement year.
