# Reference Tables and Common Mistakes

Lookup tables and hard-won guidance for tuning PA automation. Read alongside
`references/ml-classifier.md` and `references/feature-extraction.md`.

## XGBoost Hyperparameters for PA Classification

| Parameter | Default | Range |
|-----------|---------|-------|
| `n_estimators` | 300 | 100 to 1000 |
| `max_depth` | 6 | 3 to 10 |
| `learning_rate` | 0.05 | 0.01 to 0.3 |
| `subsample` | 0.8 | 0.5 to 1.0 |
| `colsample_bytree` | 0.8 | 0.5 to 1.0 |
| `scale_pos_weight` | 1.0 | Set to neg/pos ratio for imbalanced data |

## Documentation Completeness Scoring

| Document Type | Weight | Required For |
|---------------|--------|-------------|
| Clinical notes | 0.30 | All PA requests |
| Lab results | 0.25 | Drug PAs with lab criteria |
| Treatment history | 0.25 | Step therapy drugs |
| Diagnosis confirmation | 0.10 | All PA requests |
| Specialist referral | 0.10 | Specialty drugs |

## Common Mistakes

- **Wrong:** Training a PA classifier on imbalanced data without correction.
  **Right:** Set `scale_pos_weight` to the neg/pos ratio, or apply resampling to balance
  the training set.
  **Why:** PA datasets are often 70 to 80 percent approvals; without correction, the
  model learns to approve everything.

- **Wrong:** Including features derived from information not available at the time of the
  PA request.
  **Right:** Ensure all features use only data available before or at the moment of
  submission (claims history, not future outcomes).
  **Why:** Leaking future data inflates model performance in training but fails
  completely in production.

- **Wrong:** Deploying a model trained on one payer's decisions to adjudicate another
  payer's requests.
  **Right:** Train and validate separate models per payer, or include payer identity as
  a feature with sufficient per-payer training data.
  **Why:** Each payer has independent clinical policies; a model trained on Payer A's
  criteria will make wrong decisions for Payer B.

- **Wrong:** Accepting SHAP explanations at face value without clinical validation.
  **Right:** Verify that top SHAP features align with known clinical criteria from the
  payer's published policy.
  **Why:** Spurious correlations in training data can produce plausible looking but
  clinically meaningless explanations.

- **Wrong:** Hardcoding denial reason strings with free-text matching.
  **Right:** Use standardized reason codes (CARC/RARC) and map them to structured enums.
  **Why:** Free-text matching is brittle; minor wording changes break the logic and
  cause silent failures.

- **Wrong:** Replacing the rules engine entirely with an ML classifier.
  **Right:** Use ML to augment deterministic policy rules; route clear-cut cases through
  rules and ambiguous cases through ML.
  **Why:** Auditable, explainable decisions require deterministic rules for regulatory
  compliance; ML alone is not audit defensible.
