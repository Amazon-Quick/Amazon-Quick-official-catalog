# Parameter Reference and Domain Pitfalls

Consolidated tuning guidance and false-signal traps across all tasks. Each task's own
reference file repeats the parameters and pitfalls specific to it; this file is the
cross-task overview.

## Parameter reference

| Function | Key parameter | Default | Guidance |
|---|---|---|---|
| `profile_em_distribution` | z-score threshold | 2.0 | Lower to 1.5 for sensitive screening |
| `validate_ncci` | NCCI edit file | CMS quarterly | Update quarterly from CMS |
| `detect_duplicates` | `fuzzy_window_days` | 3 | Increase to 7 for post-acute care |
| `benfords_test` | p-value threshold | 0.01 | Use 0.05 for initial screening |
| `detect_impossible_days` | `max_min` | 1440 | Reduce to 960 for a stricter threshold |

## Domain pitfalls

- **X12 segment terminator.** Do not parse 837 files using the newline character as the
  segment terminator. Read the terminator from position 105 of the ISA segment (the character
  after the last ISA element); terminators can be `~`, `\n`, or any character, and assuming
  `~` breaks on files that use another.

- **Single-benchmark profiling.** Do not compare provider E&M distributions to a single
  national benchmark. Benchmark against same-specialty, same-region, same-payer-mix peers;
  specialty and geography drive legitimate variation.

- **Duplicate over-flagging.** Do not flag all exact duplicate claims as fraud. Distinguish
  true duplicates (the same claim resubmitted) from legitimate corrections (different claim
  IDs with adjustment reason codes). Only same-claim-ID resubmissions without adjustment
  reason codes are suspect.

- **Benford's on small charges.** Do not run first-digit analysis on charges below $10.
  Filter to charges of $10 or more; low-value charges cluster around fee-schedule amounts and
  naturally violate Benford's Law.

- **Stale NCCI edits.** Do not use NCCI edit tables without checking effective and deletion
  dates. Filter edits to those active on the claim's date of service. NCCI edits are versioned
  quarterly, so applying current edits to historical claims produces false violations.

- **Concurrent services.** Do not detect impossible days from CPT time estimates without
  accounting for concurrent services. Some services legitimately overlap (monitoring during
  infusion, teaching-physician attestation); only sum non-overlapping service minutes.
