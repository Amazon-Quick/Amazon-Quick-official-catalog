# Continuous Enrollment Rules

| Rule | Definition |
|------|-----------|
| Measurement year | January 1 to December 31 of the reporting year |
| Anchor date | Date the member must be enrolled through (usually December 31) |
| Allowable gap | 45 days or fewer of total gap permitted |
| Gap counting | Calendar days without coverage; multiple gaps are summed |
| Enrollment source | Medical benefit, pharmacy benefit, or both, depending on the measure |

## Enrollment evaluation decision tree

```
Is the member enrolled on the anchor date?
  NO  -> Exclude from denominator
  YES
    Total gap days during measurement year?
      45 or fewer -> Continuously enrolled
      more than 45 -> Exclude from denominator
    Measure requires pharmacy benefit?
      YES -> Verify pharmacy enrollment separately
      NO  -> Medical enrollment is sufficient
```

## Watch out

- Do not exclude members whose total gap is 45 days or fewer. HEDIS permits an
  allowable gap at or under that threshold.
- Sum every gap across the measurement year before comparing to the threshold.
