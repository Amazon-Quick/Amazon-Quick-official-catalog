---
description: "How growth rates (period on period, YoY, YTD, LTM, CAGR), the underlying trend, trend changes and seasonality are measured and worded. Read when running or explaining the trend analysis."
last_updated: 2026-11-24
---
# Trend analysis: what it computes and how to report it

Trend analysis says **where this line is heading, how fast, and whether that has changed.**
It is not about single periods. If the user asks which months look wrong, that is anomaly detection.

## What is in `res["trends"]` (one dict per line) and on the Trends sheet

| Field | Meaning |
|---|---|
| `last_period`, `last_value` | The latest complete period and its value |
| `prior_pct` | Latest period against the one before (month on month, quarter on quarter, week on week). Raw, so it carries seasonality: do not lead with it on a seasonal line |
| `yoy_pct` | Latest period against the same period a year earlier. The standard seasonality-free comparison |
| `recent_yoy_pct` | The most recent few periods (3 months, 2 quarters, 13 weeks, 28 days) against the same periods a year earlier. Steadier than one period |
| `ytd_pct`, `ytd_periods` | Fiscal year to date against the same periods of the prior year |
| `ltm`, `ltm_prior`, `ltm_pct`, `ltm_change` | The last twelve months (or 4 quarters, 52 weeks) against the twelve before |
| `cagr_pct`, `cagr_years` | Compound annual growth between the latest twelve months and the twelve months that many whole years earlier. Only with three years or more |
| `trend_pct`, `direction` | The annual rate at which the level has moved over the trend window (two years for monthly data), on the seasonally adjusted line with unusual periods set aside. `direction` is Rising or Falling only when a rank test finds a clear trend of at least 1% a year; otherwise Flat |
| `underlying_pct` | The same rate with level shifts taken out. Present only when the level stepped inside the window. A step and steady growth are different news: report both |
| `trend_change` | Where the underlying trend picked up, slowed or reversed, with the rate before and after. Present only when the evidence is strong |
| `level_shifts` | Sustained steps in the level, with the period and size |
| `seasonal_label`, `peak`, `trough` | How strong the seasonal pattern is, and the highest and lowest point in the year with their usual size |
| `noise_pct` | The line's typical unexplained movement from period to period. A change smaller than this is not worth a sentence |
| `yoy_streak` | Consecutive latest periods of year-on-year growth (positive) or decline (negative) |
| `set_aside` | Periods left out of the trend because they are unusual. Always name them if you quote the trend |
| `read` | One sentence with the main facts, ready to adapt |

`basis` is "Total" for amounts for the period (revenue, spend, units sold) and "Average" for balances
and rates (inventory, headcount, a margin). Windows are added up for the first and averaged for the
second, because twelve month-end balances added together mean nothing. The percentages are the same either
way; the amounts are not. If the user corrects a line's type, re-run with `line_types`.

## How to report

1. **Answer what was asked.** "How is revenue trending?" gets the direction and the rate first, not a table.
2. **Lead with the comparison finance uses for that question.** Direction over time: the trend rate and the
   last twelve months. "How did we do this month?": year on year, then the recent periods year on year.
   Year so far: year to date.
3. **Pair the percentage with the amount** for the lines that matter: "+8.1% over the last twelve months, +9,540".
4. **Say when the trend changed**, if `trend_change` or `level_shifts` is present: "growth slowed from about
   12% to 8% a year around March 2021", "a step up of about 20% in April 2020, steady growth since".
5. **Rank several lines by amount of change**, not by percentage. A 40% rise on a tiny line is not the headline.
6. **Mention seasonality when it matters to the reading**: "December usually runs about 23% above the
   year's level, so the December jump is the normal pattern".
7. **Name what was set aside.** "Excluding March 2020, which is flagged as unusual" tells the user what the trend leaves out.

## Pitfalls to avoid

- **Period on period on a seasonal line.** "Up 12% on last month" in December is the season, not growth.
  Use year on year or the trend rate.
- **Small bases.** A line that went from 3 to 9 is "+200%". Give the amount and leave the percentage out,
  or say it is from a small base.
- **Flat is an answer.** If `direction` is Flat, say the line is broadly flat. Do not turn +0.8% a year into "growing".
- **Short history.** Under about two years the seasonal pattern cannot be separated and compound growth is
  not computed. The fields come back as `None`; say what is missing instead of estimating it.
- **A level shift is not growth.** A line that stepped up 20% once and has been flat since is flat with a
  step, not "growing 10% a year".
- **Calendar effects.** Months differ in working days, and some calendars have 4-week and 5-week periods.
  These repeat every year and are absorbed by the seasonal pattern; a year-specific effect (a leap day, an
  event that moved to a different month) is not adjusted for. Say so if the user asks about a small move.
- **Currency.** Nothing is restated at constant rates. If the lines are in different currencies or include
  translation effects, say that the trend includes them.
- **No causes.** The trend says what the line did. Why it did so needs drivers this analysis has not seen.

## Vocabulary

Use the terms finance teams use: month on month (MoM), quarter on quarter (QoQ), year on year (YoY),
year to date (YTD), last twelve months (LTM, also TTM), compound annual growth rate (CAGR), run-rate,
seasonally adjusted. Spell a term out the first time unless the user used the abbreviation themselves.

## Handing off to a forecast

If the user goes on to forecast the same lines, `res["one_offs"]` is the per-line list of one-off periods a forecast would usually leave out.
