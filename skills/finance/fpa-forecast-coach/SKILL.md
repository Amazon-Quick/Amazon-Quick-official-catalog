---
name: fpa-forecast-coach
display_name: Forecast Coach (Preview)
icon: assets/trending-up.svg
description: "Produce a baseline forecast for any time series with P10/P50/P90 bands from classical statistics (exponential smoothing and the Theta method), finance methods side by side (trailing run-rates, prior year x growth), a backtest that says which method history favors, target phasing by seasonality, and a Microsoft Excel coach workbook. Use when asked to 'forecast this', 'project these out', 'what is the baseline', 'backtest my forecast', 'phase this target', or 'fpa-fc help'."
created_date: "2026-11-11"
last_updated: "2026-11-24"
origin: original
license: "MIT-0"
preferred_model: smart
preferred_thinking: medium
tools: [run_python, run_python_with_write, file_read, list_session_tabs, open_in_session_tab]
readme: "Read assets/README.md, and stop if a required dependency is missing."
inputs:
  - name: source
    description: "Where the history lives: a spreadsheet or CSV in the session, an open session tab, or numbers pasted in chat."
    type: string
    required: true
  - name: horizon
    description: "How many periods to forecast."
    type: number
    required: false
    default: 12
checksum: "sha256:af7278d4e17c70b38ade38fd4b610fe0df4c75f78fa03340a278ff20b1394e74"
id: "4595dd5d-6b33-4f0e-b30f-cffb66ca9a02"
---

## Overview

Forecasts time series with a statistical baseline: exponential smoothing (ETS, chosen per series by the corrected Akaike information criterion, AICc) averaged with the Theta method, or Croston's method for a series with many zero periods, with analytic P10/P90 bands. Next to the baseline, the scripts compute the methods finance already uses (trailing run-rates, prior year x trailing year-on-year growth, seasonal naive, and last actual held flat) and ETS and Theta on their own. They backtest all of them on the same held-out windows. They then write one Microsoft Excel workbook the user can adjust: a P50 baseline, P10/P90 bands, a Method picker and overlay columns that drive a Final row, the backtest scoreboard, target phasing, and commentary with the risks stated first. Every method extrapolates history, and none of them sees drivers.

## Workflow

<Goal>
A coach workbook for {{source}} over {{horizon}} periods, built by the bundled scripts, where every series has a P50 baseline with P10/P90 bands, every available finance method side by side, and a backtest verdict; and a chat answer that leads with the number asked for, states the backtest verdict and band coverage in one line, and reads out every flag that bears on the answer, including when a simpler method beat the baseline.
</Goal>

<Definitions>

<Definition - Methods>
The baseline ("Baseline P50", with P10/P90 bands) and the comparison methods: trailing 3-, 6-, and 12-month (T3M, T6M, T12M) run-rates, prior year x trailing year-on-year growth, seasonal naive, last actual held flat, ETS, and Theta. The baseline is the average of ETS and Theta, except for a series with 40% or more zero values, where it is Croston's method with the Syntetos-Boylan approximation (Croston/SBA), because smoothing a series with many zeros mixes how often a value occurs with how large it is, and Croston's method estimates the two separately. `res["methods"][series]["baseline_method"]` names which one a series used. Only the baseline has bands; the others are point estimates. A method that needs more history than a series has is not offered for that series.
</Definition - Methods>

<Definition - Stock and Flow>
A flow (sales, spend, units) sums across periods. A stock or balance (inventory, headcount, cash) is read at a point in time and is never summed across periods.
</Definition - Stock and Flow>

<Definition - Backtest Verdict>
For each series, the method with the lowest weighted absolute percentage error (WAPE) on the same two held-out windows, plus the baseline's bias and band coverage. Two windows are enough to prefer a method, not enough to promise it keeps winning.
</Definition - Backtest Verdict>

</Definitions>

<Rules>
1. Coach, not oracle. Every method extrapolates history alone and uses no drivers, price, promotions, or plan scenarios. Say what it does not know, and never present a forecast as certain.
2. Never hide a bad backtest. When a simpler method beat the baseline on a series, say so and name the method; do not present the baseline's number as the answer there.
3. Compute every forecast with the bundled scripts (`coach.build`). Never hand-write a forecast, the per-cell explanations, or the commentary.
4. Do not install packages, download a model, or call the internet. Everything runs on the bundled scripts.
5. Pad missing history with NaN, never zeros, and never sum a stock across periods (<Definition - Stock and Flow>).
6. Never forecast a series the user described as a plan, budget, or target. A target goes into `targets=`, never into `series=`.
7. Name the method behind every number, including the baseline method from `baseline_method`. Do not call a run-rate or prior-year number the baseline forecast, and do not quote the P10 to P90 band as a planning range when backtest coverage is above 90%, because a band that holds more than 90% of actuals is too wide to plan with.
8. Never write into the user's source file. The coach workbook is always a new file.
9. Ask the user once where to save the workbook.
10. Never send, publish, or share the workbook without the user's explicit approval.
11. Outputs are informational and are not accounting or financial advice. The user must validate the forecast with a qualified accountant or finance controller before relying on it.
12. Never open, read, or print any `scripts/{module}.py` file. Import the module a step names and call its function; print only what the step's Validate line needs.
</Rules>

<Agent Annotations>
- [Agent] = Execute using tools. Do not involve the user.
- [Ask user] = Present to the user and wait for a response. When a decision is needed, offer numbered options with the recommended one first, marked "(recommended)", and "Other" last.
- [Decide] = Evaluate conditions and follow the matching branch.
- [Think] = Reason internally with no tools or output: weigh at least three approaches against <Goal> and <Rules>, pick one, and check what could go wrong.
</Agent Annotations>

<Gotchas>
1. When the skill loads, its scripts/ folder is on the Python import path, so the scripts import by name. AWS Quick does not run a script's `__main__` block.
2. Variables do not survive between separate run_python calls, so a later step cannot reuse `series` or an import from an earlier call.
3. Three things silently corrupt a forecast: a totals row read as a series, a plan or forecast column read as actuals, and a partial last period, which every method reads as a collapse.
4. With under three seasonal cycles, seasonal peaks come out flattened; P90 is the better guide for a peak period.
5. A date such as 03/04/2025 reads as March 4 or April 3. `coach.prepare` skips a series whose dates can be read both ways and says so in `issues`.
</Gotchas>

<Instructions>

<Workflow - Router
description="Check the dependency, then send the request to the matching workflow."
tools=[file_read]
triggers=["User asks for a forecast, projection, run-rate, baseline, backtest, or target phasing", "fpa-fc help, fpa-fc forecast, or a bare fpa-fc"]
>

1. [Agent] Read the `## Pre-requisites` table in assets/README.md and check that run_python and run_python_with_write are available in this session.
   Validate: both tools are available.
   If fails: stop, tell the user that code execution is turned off, and link [System tools](https://docs.aws.amazon.com/quick/latest/userguide/system-tools-desktop.html) from the README.

2. [Decide] Which workflow?
   Validate: exactly one workflow is chosen.
   - `fpa-fc help`, a bare `fpa-fc`, or "what can the forecast coach do" → <Workflow - Help>
   - `fpa-fc forecast`, or a request to forecast, backtest, or phase a target → <Workflow - Forecast>
   If fails: render <Workflow - Help>.

</Workflow - Router>

<Workflow - Forecast
description="Read a history, confirm its shape, forecast and backtest every method with the bundled scripts, and report the verdict and every flag with a Microsoft Excel coach workbook."
tools=[run_python, run_python_with_write, file_read, list_session_tabs, open_in_session_tab]
triggers=["fpa-fc forecast", "User asks for a forecast, projection, run-rate or baseline", "User asks to backtest a forecast or phase a target by seasonality"]
>

1. [Agent] With run_python, import the scripts by name (Gotcha 1) and run a sanity forecast.
   ```python
   import coach
   import stat_methods as sm

   chk = sm.baseline([100.0] * 24, 6, "MS")["p50"]
   print("sanity ok:", bool(abs(max(chk) - 100) < 1e-6 and abs(min(chk) - 100) < 1e-6))
   ```
   Validate: the sanity check prints `True` (a flat history forecasts flat).
   If fails: an ImportError means the skill's scripts are missing; tell the user and stop. For any other error, print it unedited and stop. Never hand-write a forecast (Rule 3).

2. [Agent] With run_python, read {{source}} with pandas (for an open tab, get its path from list_session_tabs) and build `series = {name: {"dates": [...], "values": [...]}}`, with the frequency and units. Leave out totals rows and plan or forecast columns, and drop a partial last period (Gotcha 3). Then call `coach.prepare(series, freq)` in the same call and print its `issues`.
   Validate: every series has at least 8 points (fewer leaves no room to fit and backtest), dates ascending, one value per period, and no totals rows.
   If fails: ask only for what is missing, such as which column holds the dates, which rows are actuals, or whether the last period is complete.

3. [Ask user] Show a compact table: each series, its number of points, first and last period, and last value, plus the `issues` from step 2. In the same message confirm {{horizon}}, the units, whether each series is a stock or a flow (<Definition - Stock and Flow>), any target to phase and its window, and where to save the workbook (Rule 9). When an issue says the dates can be read two ways (Gotcha 5), ask whether they are day-first or month-first.
   Validate: the user recognizes the last actual value for at least one series and confirms the save location.
   If fails: re-read with a different header row or sheet and show the table again. If no save location is given, offer the artifacts folder and say it lasts only for this conversation.

4. [Agent] With run_python_with_write (it writes the workbook) and `timeout=300` (a run with many series can pass the 60-second default), in one call (Gotcha 2): import coach, rebuild `series` from {{source}} exactly as in step 2, then run `res = coach.build(series=series, horizon=<horizon>, freq=<freq>, season=<season>, units=<units>, title=<title>, out_path="<confirmed path>/Forecast_Coach.xlsx", method="best", targets=<targets or None>, stock=<names of the stock series or None>, user_forecast=<their numbers or None>, prior_path=<previous workbook or None>, source_file=<name>, date_order=<"DMY" or "MDY" when confirmed, else None>)`. For a target in a later window, set `"start"` to the window's first period and a horizon that reaches its last; to phase a full-year number with some periods closed, forecast only the open periods and pass the remainder. Print `res["summary"]`, `res["flags"]`, and `res["methods"]`, and nothing else from `res`.
   Validate: `res["path"]` exists, and the summary, flags, and methods are printed.
   If fails: read the error message, fix the input it names (Gotcha 3), and re-run. Never compute the forecast by hand (Rule 3).

5. [Agent] Report in chat: lead with the number the user asked for, naming its method (Rule 7). Then the backtest verdict in one line per <Definition - Backtest Verdict> with band coverage, then every flag in `res["flags"]` that bears on the answer, including any method that beat the baseline (Rule 2). Repeat the disclaimer in Rule 11. Open the workbook with open_in_session_tab. Do not list the sheets or narrate the build.
   Validate: every number stated is in the printed output, and every flag is stated or deliberately skipped as irrelevant.
   If fails: correct the message from the printed output.

6. [Ask user] Offer one next move: change the Method cell or set Overlay % on rows they disagree with (no re-run needed); phase a target; re-run at another horizon or grain; or re-run next period with `prior_path` to show what moved. When the user asks what a sheet shows or how the Method picker works, read <Resource key="workbook-sheets"> and answer from it.
   Validate: the user picks a move or ends.
   If fails: end the workflow.
   - A re-run or target: go to step 4.
   - Done: end. Do not share the workbook without approval (Rule 10).

</Workflow - Forecast>

<Workflow - Help
description="Show the forecast coach's commands, what it needs, and how to start."
tools=[file_read]
triggers=["fpa-fc help", "fpa-fc", "User asks what the forecast coach can do"]
>

1. [Agent] Read <Resource key="help-menu"> and show it to the user.
   Validate: the menu lists `fpa-fc help` and `fpa-fc forecast`, each with a one-line description.
   If fails: summarize the <Goal>, the inputs ({{source}}, {{horizon}}), and the trigger phrases from the description.

2. [Ask user] Ask whether to start a forecast now, and if so, which data to use.
   Validate: the user picks start or done.
   If fails: end the workflow.
   - Start: go to <Workflow - Forecast> step 1.

</Workflow - Help>

</Instructions>

<Resources>
<Resource key="workbook-sheets">references/workbook.md</Resource>
<Resource key="help-menu">assets/help-menu.md</Resource>
</Resources>
