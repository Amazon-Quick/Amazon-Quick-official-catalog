---
description: "The sheets in the Forecast Coach workbook and what each holds. Read when the user asks what a sheet shows or how to use the Method picker and overlays."
last_updated: 2026-11-24
origin: original
---
# The coach workbook

| Sheet | What it holds |
|---|---|
| Forecast | Baseline P50 per series per period, with a comment in every cell that names the baseline method and explains that number; inputs per series: Method (dropdown), Overlay %, Overlay abs; and a formula-driven Final block = selected method x (1 + Overlay %) + Overlay abs, with a Total row for flows. On a re-run with a prior workbook, the prior P50 and the change on the periods both runs share |
| Methods | Every method with enough history for each series, period by period, with its total (or end-of-horizon value for a balance) and its backtest weighted absolute percentage error (WAPE); the backtest winner is marked |
| Bands | P10/P50/P90 for the baseline, with band width as a share of P50 |
| Backtest | Per series: the best method, the baseline method used, the WAPE of the baseline and each finance method on the same held-out windows, baseline bias, and band coverage |
| Target_Phasing | Only when targets are passed: baseline P50, P50 scaled to the target, the target phased by historical shares, and whether each phased period sits inside the P10 to P90 band |
| Your_Forecast | Only when the user's own forecast is passed: their number against the baseline P50 and band, period by period |
| Commentary | What the run says, then the risks, in prose |
| Actuals | The input history, with a line chart per series for up to eight series (actual, P50, P10/P90 dashed) |
| Run_Info | Run ID, the baseline method used, horizon, frequency, season, source file, prior workbook, and the methods' limits |

Changing the Method cell or the overlay columns recalculates Final without a re-run. Stocks are read at the end of the horizon and never summed.
