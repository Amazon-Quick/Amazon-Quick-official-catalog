---
description: "The required layout and design intent of the single HTML report, section by section (data limitations, hero P(hit target), Monte Carlo distribution, Bull and Bear trend, waterfall, tornado, percentile stack-rank and What has to be true, Areas to Probe, and supporting tables). Read when the user asks what a section shows."
last_updated: 2026-11-24
---
# Report layout

`sa.write_report(res, path)` (references/engine-api.md) writes one standalone HTML file: embedded CSS and inline SVG charts, no chart library, no external files, and no network request. Save it where the user chose (Rule 11) and open it in a session tab. No Excel.

**Design intent:** a finance leader grasps the story on the first screen (what the data can't support, the estimated chance of hitting plan, the shape of the risk, and which assumptions move it most) without reading a table. Charts come first; tables are backup detail.

Sections, top to bottom:

1. **Data limitations.** Stated first (short history, gaps, negative actuals, roll-forward breaks), before any result, never as a footnote.
2. **Hero band.** P(hit target) as the largest number on the page, with the target and where it came from. Beneath it a key performance indicator (KPI) strip: Base, Bull, and Bear values, the benchmark ("No full-year benchmark" when there is none), and "In X% of simulated runs the outcome is between Bear and Bull." The hero says the probability is a share of simulated runs, an estimate from the user's data, not a prediction. For a cap (`at_most`) the labels are Low case, Median, and High case.
3. **Monte Carlo distribution (the centerpiece, largest visual).** Histogram of the simulated outcomes with vertical markers for Bear, Base, and Bull, the target line, and the Bear-to-Bull band shaded. Caption states the band.
4. **Trend: Bull and Bear.** Actuals (solid), then one simulated run each for Bear, Base, and Bull, chosen so its periods add up to that scenario, forming a shaded band across the forecast periods, with the benchmark overlaid as a reference line when provided. The caption says each line is a single coherent path, not a per-period percentile.
5. **Variance waterfall.** Benchmark -> Trend delta -> Driver conversion -> Seasonality -> Judgment -> Base scenario, each step a labeled up or down bar. When the P50 differs from the expected value (the simulation's distribution is skewed), one extra step shows that difference so the bars add up exactly.
6. **Sensitivity tornado.** Each major assumption's low-to-high swing on the expected outcome, largest at the top: what moves the number most.
7. **Percentile stack-rank and What has to be true.** P10, P25, P50, P75, and P90, each with its difference from the benchmark; beside it, the conditions behind Bull and Bear (context-informed where context exists).
8. **Areas to Probe (always included).** A list ranked P1, P2, and P3: open questions, unverified context claims, conflicts between data and context, low-confidence fits, and default assumptions that need the user's own numbers.
9. **Supporting detail.** Scenario build-up (year-to-date actual or opening balance + trend and seasonality + drivers + judgment = expected, + distribution deviation = scenario, so each column sums), the assumptions table with DATA-BACKED, CONTEXT-INFORMED, USER-SET, or DEFAULT labels, external context (only when provided, each claim attributed), the basis of review (source file name and sheet, rows included and excluded, column map, date order, units, and number format), and a period-by-period appendix.

The footer carries the disclaimer that the outputs are informational, not accounting or financial advice. Deliver the file through a session tab; never print the HTML into chat.
