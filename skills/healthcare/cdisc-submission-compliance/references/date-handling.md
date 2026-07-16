# Date Handling Gotchas

Use for study day calculation and ADaM date imputation questions.

## Study day calculation

- --DY = date minus RFSTDTC plus 1, when date is on or after RFSTDTC.
- --DY = date minus RFSTDTC, when date is before RFSTDTC.

There is no Day 0. Day -1 is the day before RFSTDTC; Day 1 is RFSTDTC itself. This
off-by-one is the number one date calculation error in submissions.

## Date imputation rules for ADaM

| Scenario                      | Imputation rule                          | Flag guidance                        |
|-------------------------------|------------------------------------------|--------------------------------------|
| Missing day, AE start         | Impute to 1st of month                   | Set ASTDT, document imputation       |
| Missing month and day         | Impute to January 1st                    | Document in define.xml               |
| Missing end date, ongoing AE  | Use data cutoff date                     | Flag as ongoing (AENDY missing)      |
| Partial date comparison       | Conservative: earliest for start, latest for end | Document the algorithm       |

Rule: every imputed date requires a corresponding imputation flag variable (for
example ASTDTF, AENDTF) with values Y (imputed) or blank (not imputed).
