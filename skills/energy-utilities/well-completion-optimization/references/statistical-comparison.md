# Statistical Design Comparison

Reference detail for the completion design comparison workflow. Method for
comparing completion designs while controlling for geologic and operational
confounders.

## Sandbox constraint (read first)

The Amazon Quick Python sandbox provides numpy and pandas but does NOT provide
scipy or statsmodels. Do not import them; they fail at runtime. All statistical
tests in this skill are implemented in pure numpy plus the standard library in
`scripts/completion_stats.py`. Call that script rather than reaching for scipy or
statsmodels.

## Matching criteria (control variables)

Match pairs on all of:

1. Formation and landing zone (same stratigraphic target).
2. Reservoir quality proxy (gas-oil ratio, initial pressure, IP/ft, porosity*h).
3. Lateral length (within +/- 500 ft).
4. Vintage (within +/- 6 months, controls for price-driven choke management).
5. Spacing (similar well density in the section, controls for depletion).

## Test variable (one at a time)

Stage spacing, cluster spacing, proppant loading (lbs/ft lateral), fluid volume
(bbl/ft), or cluster count per stage.

## Response variable

EUR (6-month, 12-month, or estimated ultimate via decline-curve analysis),
EUR/1000ft (normalized for lateral length), peak 30-day or 90-day IP, or NPV per
foot.

## Statistical tests (all in scripts/completion_stats.py)

- **Paired t-test** (matched pairs, roughly normal differences):
  `t = mean(diff) / (std(diff) / sqrt(n))`. Reject the null (no difference) if
  p < 0.05. The script returns t, two-sided p, Cohen's d, and n.
- **Wilcoxon signed-rank test** (non-parametric alternative): use when the
  difference distribution is non-normal or n < 30. The script uses the normal
  approximation with tie and continuity correction and returns W and p.
- **Multiple linear regression** (control for several factors at once):

  ```
  EUR/ft = b0 + b1*proppant_per_ft + b2*stages_per_1000ft + b3*cluster_spacing
         + b4*porosity_h + b5*lateral_length + error
  ```

  The script returns each coefficient with its standard error, t-statistic, and
  p-value, plus R-squared. A significant coefficient indicates that design
  parameter materially affects the outcome after controlling for geology.

## Minimum sample size

- To detect a 10 percent EUR difference at 80 percent power: about 30 matched
  pairs.
- To detect a 20 percent EUR difference: about 12 matched pairs.

## Interpretation guardrails

- Report the p-value for every comparison. Results with p > 0.05 are not
  statistically significant and must be flagged as inconclusive.
- Test group balance before concluding. If landing zone, reservoir quality, or
  spacing patterns differ between groups, the comparison is confounded.
- Use the same decline model and economic limit for EUR across all wells compared.
  Inconsistent EUR methods invalidate the comparison.
- Normalize completion costs to a common cost basis when comparing across
  different service-cost environments (for example a low-cost year vs a high-cost
  year).
