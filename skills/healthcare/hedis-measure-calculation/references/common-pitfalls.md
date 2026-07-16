# Common Pitfalls

The calculation mistakes that most often produce wrong HEDIS rates. Check each against the code before delivering it.

- **Enrollment gap off-by-one.**
  Wrong: including segment end dates when calculating enrollment gap days.
  Right: calculate gaps as the calendar days between segments (the day after the end of segment A to the day before the start of segment B).
  Why: off-by-one errors incorrectly exclude continuously enrolled members or include ineligible ones.

- **Segments not clipped to the measurement year.**
  Wrong: using enrollment segments as-is without clipping to the measurement year boundaries.
  Right: clip all enrollment segments to the measurement year start and end dates before calculating gaps.
  Why: segments extending beyond the year inflate coverage and produce incorrect enrollment determinations.

- **Wrong date field for inpatient utilization.**
  Wrong: using service date for inpatient utilization metrics.
  Right: use admit date and discharge date for inpatient claims; service date is for professional and outpatient claims.
  Why: inpatient utilization (admissions, readmissions, length of stay) is defined by admission events, not individual service lines.

- **Numerator not deduplicated.**
  Wrong: counting a member multiple times in the numerator when they have multiple qualifying events.
  Right: deduplicate numerator events by member ID; each member counts once regardless of how many services they received.
  Why: multiple events for the same member inflate the numerator and produce artificially high rates.

- **Age computed on the wrong date.**
  Wrong: calculating member age as of the run date or an arbitrary date.
  Right: calculate age as of the measure-specific anchor date (typically December 31 of the measurement year).
  Why: the wrong anchor date shifts age-based eligibility and includes or excludes members incorrectly.

- **Diagnosis lookback too short.**
  Wrong: only looking at the measurement year for qualifying diagnoses.
  Right: apply the measure-specified lookback period (typically 2 years) for identifying members with qualifying conditions.
  Why: many HEDIS measures require a diagnosis in the measurement year OR the year prior; using only one year misses eligible members.
