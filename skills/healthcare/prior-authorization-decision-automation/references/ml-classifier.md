# Machine Learning Classifier for PA Decisions

Use a machine learning (ML) classifier only to augment the rules engine on ambiguous
cases with soft criteria, never to replace it. Auditable, explainable decisions require
deterministic rules for regulatory compliance; an ML model alone is not audit
defensible. Route clear-cut cases through the rules engine
(`references/rules-engine.md`) and ambiguous cases through the model.

## Sandbox availability

The training and explainability code below depends on `xgboost`, `scikit-learn`, and
`shap`. None of these are available in the Amazon Quick `run_python` sandbox, whose
package set is a closed allowlist (numpy, pandas, matplotlib, and similar). Do not try
to run this code inside Quick. Deliver it as code the user runs in their own training
environment, where they control the installed packages (for example a coding agent such
as Kiro via ACP in Quick on desktop, which can install xgboost, scikit-learn, and shap
and run the code outside the sandbox). The parsing, feature
extraction, and rules-engine code elsewhere in this skill uses only pandas and the
standard library, so that code does run in the Quick sandbox.

## Training Pipeline

```python
"""Train a gradient-boosted classifier on historical PA decisions."""
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import xgboost as xgb


def train_pa_classifier(
    data: pd.DataFrame,
    target_col: str = "decision",
    feature_cols: list[str] | None = None,
    n_folds: int = 5,
) -> tuple[xgb.XGBClassifier, pd.DataFrame]:
    """Train XGBoost on historical PA decisions (1=approved, 0=denied)."""
    if feature_cols is None:
        feature_cols = [c for c in data.columns if c != target_col]
    X, y = data[feature_cols].copy(), data[target_col].copy()
    cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    X[cat_cols] = X[cat_cols].astype("category")
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        enable_categorical=True,
        eval_metric="logloss",
        random_state=42,
    )
    cv_results = []
    splitter = StratifiedKFold(n_folds, shuffle=True, random_state=42)
    for fold, (ti, vi) in enumerate(splitter.split(X, y)):
        model.fit(X.iloc[ti], y.iloc[ti], eval_set=[(X.iloc[vi], y.iloc[vi])], verbose=False)
        y_prob = model.predict_proba(X.iloc[vi])[:, 1]
        cv_results.append({"fold": fold, "auc": roc_auc_score(y.iloc[vi], y_prob)})
    model.fit(X, y, verbose=False)
    return model, pd.DataFrame(cv_results)
```

Requires at least about 1000 historical decisions before ML is worth attempting; below
that, use the rules engine only. Train and validate a separate model per payer.
See `references/reference-tables.md` for the hyperparameter ranges and the
`scale_pos_weight` correction for the class imbalance typical of PA data (70 to 80
percent approvals).

## SHAP Explainability

```python
"""Generate SHAP explanations for PA decisions."""
import shap


def explain_pa_decision(model, X, instance_idx: int = 0) -> dict:
    """Generate SHAP values for a single PA decision."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    explanation = dict(
        sorted(
            zip(X.columns, shap_values[instance_idx]),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
    )
    return {
        "base_value": float(explainer.expected_value),
        "prediction": float(model.predict_proba(X.iloc[[instance_idx]])[:, 1][0]),
        "feature_contributions": explanation,
    }
```

Do not accept SHAP explanations at face value. Verify that the top contributing
features align with the payer's published clinical policy. Spurious correlations in
training data can produce plausible looking but clinically meaningless explanations.
