# Agency Submission Differences and Controlled Terminology Rules

Use for agency-specific submission format questions and controlled terminology (CT)
version policy. Confirm the target agency before applying.

## FDA versus PMDA submission differences

| Aspect          | FDA                              | PMDA                                |
|-----------------|----------------------------------|-------------------------------------|
| SDTM required   | Yes (NDA/BLA)                    | Yes (since 2020 for new drugs)      |
| ADaM required   | Yes                              | Recommended, not mandatory          |
| define.xml      | 2.0+ required                    | 2.0+ required                       |
| CT version policy | Latest at time of submission   | Pin at study start                  |
| Dataset size limit | 5 GB per dataset (eCTD)       | No explicit limit                   |
| Blanking rules  | Permissible null                 | Prefer explicit "NOT DONE"          |
| Reviewer's Guide | Required (cSDRG, aSDRG)         | Required                            |

Key gotcha: FDA accepts null for "not done" assessments; PMDA expects --STAT set to
"NOT DONE" with --REASND populated. Plan for PMDA requirements upfront if a dual
submission is intended.

## Controlled terminology rules

| Rule                            | Description                                              |
|---------------------------------|---------------------------------------------------------|
| Pin CT version at study start   | One CT version for the entire study                     |
| Document in define.xml          | Specify package version (for example 2024-03-29)        |
| Never mix versions              | Mixing CT within a study triggers P21 Warning CT2003    |
| Non-extensible codelists        | Use only CDISC-defined values (for example SEX, AEOUT)  |
| Extensible codelists            | Sponsor values allowed but must be documented           |
| Map legacy terms on upgrade     | Create a mapping table; never silently change coded values |
