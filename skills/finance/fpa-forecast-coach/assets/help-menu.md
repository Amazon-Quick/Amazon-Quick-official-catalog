---
description: "Command menu shown by the Help workflow (fpa-fc help)."
last_updated: 2026-11-24
origin: original
---
**Forecast Coach commands**

| Command | What it does |
| --- | --- |
| `fpa-fc help` | Show this menu. |
| `fpa-fc forecast` | Forecast a history with P10/P50/P90 bands, backtest every method, optionally phase a target, and write a Microsoft Excel coach workbook. |

**What you get**
- A P10/P50/P90 baseline from classical statistics: exponential smoothing (ETS) averaged with the Theta method
- Finance methods side by side: trailing 3-, 6-, and 12-month (T3M, T6M, T12M) run-rates, prior year x trailing year-on-year growth, seasonal naive, last actual held flat, ETS, and Theta
- A backtest that says which method was most accurate on your own history
- Target phasing: spread a full-year number across periods by your seasonality
- A workbook with a Method picker and overlay columns you can change without re-running

**What you provide**
- source: a spreadsheet or CSV, an open tab, or numbers pasted in chat
- horizon: how many periods to forecast (default 12)

**Try saying**
- "Forecast revenue for the next 12 months from this file."
- "Backtest my forecast against what history implies."
- "Phase this full-year target by seasonality."

Say a command to start, or describe what you want in your own words.

Every method extrapolates history and uses no drivers. Outputs are informational and are not accounting or financial advice. Validate with a qualified accountant or finance controller before relying on them.
