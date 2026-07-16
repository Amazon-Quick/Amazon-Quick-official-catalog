# SDTM Domain Mapping Decision Tree

Use for the non-obvious mappings where teams make mistakes. Apply the branch that
matches the collected data, then confirm against the current SDTM Implementation
Guide for the domain.

## Oncology tumor data

- Identifying tumor location or characteristics: TU (one record per identified lesion).
- Measuring a lesion (diameter, volume): TR (one record per measurement per visit).
- Evaluating overall response (CR, PR, SD, PD): RS (one record per assessment per visit).

Rule of thumb: TU identifies it, TR measures it, RS evaluates the patient.

## Medication data

- Study drug or protocol-mandated therapy: EX (Exposure).
- Non-study medication taken during the study: CM.
- Ambiguous, for example rescue medication specified in the protocol:
  - Protocol-required with dosing rules: EX.
  - Taken at investigator or subject discretion: CM.

## Pre-existing condition that worsens on study

- Record in MH (with MHENDTC blank or ongoing).
- ALSO record in AE (with AEPRESP set to "Y" to flag pre-existing).
- Link via RELREC if needed for traceability.

## Questionnaire, patient-reported outcome, or scale data

- Published validated instrument (for example EQ-5D, PHQ-9): QS.
- Sponsor-designed assessment with scoring: QS (with sponsor-defined TESTCDs).
- Single ad-hoc question not part of a scale: FA (Findings About).
