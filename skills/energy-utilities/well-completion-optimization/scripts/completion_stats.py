"""Completion design statistics using only numpy and the standard library.

The Amazon Quick Python sandbox provides numpy and pandas but not scipy or
statsmodels, so the tests a completion comparison needs are implemented here from
first principles. Student's t tail probabilities come from the regularized
incomplete beta function (Numerical Recipes formulation), the Wilcoxon
signed-rank test uses the normal approximation with tie and continuity
correction, and the regression is ordinary least squares by the normal equations.

Functions:
    paired_t_test(group_a, group_b) -> dict
    wilcoxon_signed_rank(differences) -> dict
    ols_regression(design_matrix, response, feature_names) -> dict

All p-values are two-sided. Call these instead of importing scipy or statsmodels.
"""

from __future__ import annotations

import math

import numpy as np


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function."""
    max_iter = 200
    eps = 3.0e-12
    fpmin = 1.0e-30
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_beta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(ln_beta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _t_two_sided_p(t_stat: float, df: float) -> float:
    """Two-sided p-value for a Student's t statistic with df degrees of freedom."""
    if df <= 0:
        return float("nan")
    x = df / (df + t_stat * t_stat)
    return _betai(0.5 * df, 0.5, x)


def _normal_two_sided_p(z: float) -> float:
    """Two-sided p-value for a standard normal z-score."""
    return math.erfc(abs(z) / math.sqrt(2.0))


def paired_t_test(group_a, group_b) -> dict:
    """Paired t-test comparing matched completion designs.

    group_a and group_b are equal-length sequences of the response variable for
    matched wells (for example EUR per foot). Returns the mean difference, its
    standard deviation, the t statistic, the two-sided p-value, Cohen's d for
    paired data, the pair count, and a significance flag at alpha = 0.05.
    """
    a = np.asarray(group_a, dtype=float)
    b = np.asarray(group_b, dtype=float)
    if a.shape != b.shape:
        raise ValueError("group_a and group_b must have the same length")
    diff = b - a
    n = diff.size
    if n < 2:
        raise ValueError("need at least two matched pairs")
    mean_diff = float(np.mean(diff))
    sd_diff = float(np.std(diff, ddof=1))
    if sd_diff == 0.0:
        raise ValueError("differences have zero variance; test is undefined")
    t_stat = mean_diff / (sd_diff / math.sqrt(n))
    p_value = _t_two_sided_p(t_stat, n - 1)
    return {
        "mean_difference": mean_diff,
        "std_difference": sd_diff,
        "t_statistic": t_stat,
        "p_value": p_value,
        "cohens_d": mean_diff / sd_diff,
        "n_pairs": int(n),
        "significant_at_005": bool(p_value < 0.05),
    }


def wilcoxon_signed_rank(differences) -> dict:
    """Wilcoxon signed-rank test on paired differences (normal approximation).

    Use when the difference distribution is non-normal or the sample is small.
    Zero differences are dropped. Ties share averaged ranks and the variance is
    tie-corrected. A continuity correction is applied. Returns the W statistic,
    the two-sided p-value, the effective sample size, and a significance flag.
    """
    diff = np.asarray(differences, dtype=float)
    diff = diff[diff != 0.0]
    n = diff.size
    if n < 1:
        raise ValueError("no non-zero differences to test")
    order = np.argsort(np.abs(diff))
    abs_sorted = np.abs(diff)[order]
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs_sorted[j + 1] == abs_sorted[i]:
            j += 1
        ranks[i : j + 1] = 0.5 * (i + 1 + j + 1)
        i = j + 1
    signs = np.sign(diff)[order]
    w_plus = float(np.sum(ranks[signs > 0]))
    w_minus = float(np.sum(ranks[signs < 0]))
    w_stat = min(w_plus, w_minus)
    mean_w = n * (n + 1) / 4.0
    _, counts = np.unique(abs_sorted, return_counts=True)
    tie_term = float(np.sum(counts**3 - counts))
    var_w = (n * (n + 1) * (2 * n + 1) - 0.5 * tie_term) / 24.0
    if var_w <= 0.0:
        raise ValueError("variance is non-positive; test is undefined")
    z = (w_stat - mean_w + 0.5) / math.sqrt(var_w)
    p_value = _normal_two_sided_p(z)
    return {
        "w_statistic": w_stat,
        "z_score": z,
        "p_value": p_value,
        "n_effective": int(n),
        "significant_at_005": bool(p_value < 0.05),
    }


def ols_regression(design_matrix, response, feature_names=None) -> dict:
    """Ordinary least squares regression by the normal equations.

    design_matrix is an (n_samples, n_features) array WITHOUT an intercept column;
    an intercept is added automatically. response is length n_samples. Returns per
    term (intercept first) the coefficient, standard error, t statistic, and
    two-sided p-value, plus R-squared, adjusted R-squared, and residual degrees of
    freedom.
    """
    x = np.asarray(design_matrix, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(response, dtype=float).reshape(-1)
    n, k = x.shape
    if y.shape[0] != n:
        raise ValueError("design_matrix and response length mismatch")
    x_design = np.column_stack([np.ones(n), x])
    p = x_design.shape[1]
    df_resid = n - p
    if df_resid <= 0:
        raise ValueError("not enough samples for the number of features")
    xtx = x_design.T @ x_design
    xtx_inv = np.linalg.inv(xtx)
    beta = xtx_inv @ x_design.T @ y
    resid = y - x_design @ beta
    ss_resid = float(resid @ resid)
    ss_total = float(((y - y.mean()) ** 2).sum())
    sigma2 = ss_resid / df_resid
    se = np.sqrt(np.diag(xtx_inv) * sigma2)
    t_stats = beta / se
    p_values = [_t_two_sided_p(t, df_resid) for t in t_stats]
    r_squared = 1.0 - ss_resid / ss_total if ss_total > 0 else float("nan")
    adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / df_resid

    if feature_names is None:
        names = ["const"] + [f"x{i + 1}" for i in range(k)]
    else:
        names = ["const"] + list(feature_names)

    terms = []
    for i, name in enumerate(names):
        terms.append(
            {
                "term": name,
                "coefficient": float(beta[i]),
                "std_error": float(se[i]),
                "t_statistic": float(t_stats[i]),
                "p_value": float(p_values[i]),
                "significant_at_005": bool(p_values[i] < 0.05),
            }
        )
    return {
        "terms": terms,
        "r_squared": r_squared,
        "adj_r_squared": adj_r_squared,
        "df_residual": int(df_resid),
        "n_samples": int(n),
    }
