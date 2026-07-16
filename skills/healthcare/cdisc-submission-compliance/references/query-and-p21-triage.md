# Query Prioritization and Pinnacle 21 Triage

Use for data query prioritization and for triaging Pinnacle 21 (P21) findings before
database lock or submission.

## Query prioritization by clinical impact

| Priority     | Data category    | Examples                                  | Resolution SLA      |
|--------------|------------------|-------------------------------------------|---------------------|
| P1 Critical  | Safety data      | SAE dates, AE causality, death records    | 24 to 48 hours      |
| P2 High      | Efficacy endpoints | Primary/secondary endpoint values, visit dates | 3 to 5 business days |
| P3 Medium    | Key demographics | Randomization data, stratification factors | 5 to 7 business days |
| P4 Low       | Administrative   | Informed consent dates, site identifiers  | 10 business days    |

Escalation rules:

- Queries affecting multiple subjects: escalate one priority level.
- Systematic errors (wrong unit for all subjects at a site): P1 regardless of data type.
- Safety queries block database lock: resolve before anything else.

## Pinnacle 21 triage decision tree

- Severity Error: MUST fix before submission (no exceptions).
- Severity Warning:
  - Affects safety or efficacy data: fix.
  - Cosmetic or structural only: document justification in the Reviewer's Guide.
  - Systematic across all subjects: fix (the reviewer will notice).
- Severity Notice:
  - Easy fix (under 1 hour): fix.
  - Complex or low-impact: skip, document if asked.

## Top P21 rules by fix priority

| Rule ID | Description                          | Severity | Action                                        |
|---------|--------------------------------------|----------|-----------------------------------------------|
| SD0009  | USUBJID not consistent with DM       | Error    | Fix immediately, breaks traceability          |
| SD0083  | Missing required variable            | Error    | Fix, submission will be rejected              |
| SD1001  | Invalid date/time format             | Error    | Fix, ISO 8601 is non-negotiable               |
| CT2001  | CT mismatch (value not in codelist)  | Warning  | Fix if non-extensible codelist; document if sponsor extension |
| CT2003  | CT version inconsistency             | Warning  | Usually fix, indicates mixed CT versions      |
| SD1020  | Value not found in external codelist | Warning  | Fix if a standard term exists; extend if legitimate |
| AD0252  | ADSL missing required variables      | Error    | Fix, ADSL completeness is critical            |
| AD0322  | BDS record without PARAMCD           | Error    | Fix, BDS is unusable without PARAMCD          |
| SD0070  | Duplicate records                    | Warning  | Investigate, may be valid (bilateral findings) |
| SD1015  | Inconsistent values across datasets  | Warning  | Fix if traceability broken; document if by design |
