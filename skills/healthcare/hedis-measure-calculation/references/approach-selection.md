# Approach Selection

Scenario-to-approach guidance. Use it to pick the language and shape of the code before reading the task reference.

| Scenario | Approach | Key consideration |
|----------|----------|-------------------|
| Single measure, ad-hoc | Python `calculate_measure()` | Fast iteration, easy debugging |
| Enterprise batch (all measures) | SQL common table expressions per measure | Scales to millions of members |
| Data source: claims only | Use procedure/revenue codes for numerator | No clinical data available |
| Data source: claims + EHR | Supplement with lab values, vitals | Higher capture rate |
| Enrollment check: single payer | `max_gap_days=45` (HEDIS default) | One enrollment table |
| Enrollment check: multi-payer | Merge enrollment spans first, then check | Avoid double-counting gaps |
