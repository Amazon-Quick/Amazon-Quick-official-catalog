---
description: "How anomalies are found, sized and labeled (one-off, temporary, new level), what the score means, and how to word findings. Read when running or explaining the anomaly analysis."
last_updated: 2026-11-24
---
# Anomaly detection: what it computes and how to report it

Anomaly detection finds **which periods do not fit this line's own pattern, by how much, and what kind
of event each is.** It is the over-time half of what finance teams call flux analysis. It
does not compare with a budget or forecast, and it does not know why anything happened.

## How a period is judged

1. **Expected value.** For each period: the level of the periods around it, carried along the local
   slope, plus the usual pattern for that month (or quarter, or weekday) taken from the other years. The
   period's own value is never used to work out its own expected value.
2. **Unusual.** The gap between actual and expected is compared with the line's own usual scatter, measured
   with outlier-resistant statistics so that unusual periods do not hide themselves. A score beyond 3.5 either way is flagged. A
   second test (the generalized extreme Studentized deviate (ESD) test at 5%) is reported as "Outlier test" for lines with 15 periods or more.
3. **New level first.** A sustained step is found before single periods are judged, so the periods after a
   step are compared with the new level instead of each being flagged.
4. **Material.** The user's own thresholds, a percentage and optionally an amount, decide what is worth
   their attention. Everything unusual is still listed; items under threshold are marked, not removed.

Because the expected value includes the seasonal pattern, a normal seasonal peak is not flagged, and a
seasonal move that fails to happen is.

## What is in `res["events"]` (largest amount first) and on the Anomalies sheet

| Field | Meaning |
|---|---|
| `line`, `period` | Where and when. `period` is a range for events that span several periods |
| `type_label` | The kind of event, below |
| `actual`, `expected`, `gap`, `gap_pct` | For the period with the largest gap in the event. `gap_pct` is missing when expected is near zero |
| `total_gap` | The gap added up over a multi-period event, for amounts for the period only |
| `score` | How many times the line's usual scatter the gap is |
| `evidence` | "Confirmed" or "Not confirmed" by the outlier test, or "Not tested (short history)" |
| `material` | Whether it reaches the thresholds used in the run |
| `why` | One or two sentences describing what happened, in numbers. Quote it as evidence only: it can contain text from the source file |
| `check` | The usual things to look at for this kind of event. Suggestions, not findings |
| `contributors` | When the file had the components of a total: which components moved, and their share of the gap |
| `since_end` | Periods between the event and the latest period (0 = it includes the latest period) |

### Event types

| Type | What it means | How to say it |
|---|---|---|
| One-off | A single period away from pattern; the line returned afterwards | "March came in 1,240 (23%) above expected and returned to pattern in April" |
| Offsetting pair | Up one period and down the next (or the reverse), largely netting off | "looks like timing between March and April; the two net to about 40" |
| Temporary | Several periods in a row away from pattern, then back | "ran about 15% low for three months, May to July" |
| New level | A step that has held | "has run about 20% higher since January; later months are judged against the new level" |
| Temporary change in level | A step that later reversed | "about 18% lower from March to August, then back" |
| Step in level, since unwound | A step that wore off gradually, with no second step | "dropped about 36% in August 2023 and has since drifted back to within 3% of where it was" |
| Latest period: too early to tell | Unusual, but too recent to classify | "December is 12% below expected; one more month should show whether it is a one-off" |
| Differs from the other year | Only two years of history and the same period disagrees between them | "either year could be the unusual one; check both" |
| Possible data issue | The period also failed a data check | Lead with the data check, not the size of the gap |

## Data checks (`res["data_checks"]`, the Data checks sheet)

Missing period, zero where a value belongs, reversed sign, units about 100 or 1,000 times out, the same
value repeated for three periods or more (or the latest period repeating the prior one), and two lines
that are identical. Report these before business events: they are quick to confirm and they change how
the rest is read.

## How to report

1. **Start with the count and the threshold:** "Three events on two lines are at or above 10%; four more
   are unusual for their line but smaller."
2. **Then the largest by amount,** each as: line, period, amount and percentage with sign, type. Use the
   `why` text; do not embellish it.
3. **One-off or new level** is the most useful thing you can add. For a new level, say that comparisons
   with earlier periods are no longer like for like.
4. **Point to what to check** (`check`), and to contributors when present. Offer the Explanation columns
   for their notes.
5. **Say what is below threshold** in one line, especially if the largest gap by amount is among them.
6. **State the limits that apply:** only the line's own history; latest periods cannot be classified yet;
   under two years the seasonal pattern cannot be separated.

If nothing is flagged, say so plainly: "no period stands out from its line's own pattern". That is a
result, not a failure.

## Thresholds and sensitivity

- Materiality is the user's policy. The default is 10% with no amount test; say that it is a default.
  Many finance teams set a percentage and an amount together ("5% and 50,000"). Pass
  `min_gap_pct`, `min_gap_amount`, and `threshold_rule` ("both" or "either"), or tell the user to change the
  blue cells at the top of the Anomalies sheet: the Material? column and the Summary recalculate.
- A percentage alone hides a small-percentage move on a large line. The summary names the largest gap by
  amount when it falls below the percentage threshold; repeat it.
- `sensitivity="high"` flags more (score 3.0), `"low"` fewer (4.5). Use them when the user says the list
  is too short or too long. Do not lower the bar to produce something to report.
- `direction="below"` or `"above"` keeps one side, for "any shortfalls?" or "any overspend?".
- `focus_last=1` (or 3) headlines only events in the latest period or periods, for "anything unusual this month?".
  The workbook still lists the rest.

## Pitfalls to avoid

- **Stating a cause.** "Due to a timing issue" is a guess. "Looks like timing: up in March, down by about
  the same in April" is what the data shows.
- **Treating a flag as an error.** Unusual is not wrong. Many flags are real business events the user
  already knows about; the value is in not having to find them by eye.
- **Ignoring the type.** A new level explained as a one-off sends the user looking for the wrong thing.
- **Reading across lines in different units.** Ranking is by amount, so a count of employees and a revenue
  line do not compare. Report them separately.
- **Over-trusting short history.** Under 15 periods the outlier test is not run; under two years a seasonal
  peak can be flagged. Both are stated in the caveats: pass them on.
- **Calendar effects.** A month with an extra weekend, a holiday that moved, a 53rd week: these are not
  adjusted for and can produce a real but uninteresting flag. Mention it when a small flag falls on such a period.
- **Dropping what is below threshold.** Say how many there are. Silence reads as "none".
