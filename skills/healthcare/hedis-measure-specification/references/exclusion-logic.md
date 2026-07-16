# Exclusion Logic

| Category | Applies to | Condition |
|----------|-----------|-----------|
| Hospice | All measures | Hospice benefit or encounter |
| Deceased | All measures | Death during measurement year |
| End-stage renal disease | Diabetes, kidney | N18.6, dialysis codes |
| Organ transplant | Diabetes, kidney | Z94.x |
| Pregnancy | Blood pressure, diabetes | O00 to O9A |
| Frailty plus advanced illness | Age 66 and older, multiple | BOTH conditions required |

## Evaluation rules

1. Apply exclusions AFTER building the full denominator.
2. Check the full measurement year for exclusion events.
3. Frailty plus advanced illness is compound. Both must be present.
4. Hospice overrides all other logic.
5. Document which optional exclusions are applied.

## Watch out

- Never apply exclusions before the full eligible population is built. Build the
  complete denominator first, then subtract.
- A frailty diagnosis alone does not exclude a member without a co-occurring
  advanced-illness condition.
