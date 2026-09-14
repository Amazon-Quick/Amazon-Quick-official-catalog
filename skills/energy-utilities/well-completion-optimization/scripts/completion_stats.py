"""
description: Completion design statistics implemented with only numpy and the standard library, providing paired t-test, Wilcoxon signed-rank, and OLS regression functions.
last_updated: 2026-09-13
origin: original

Completion design statistics using only numpy and the standard library.

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

The numeric primitives live in pure, dependency-injected classes (a Student's t
distribution, a normal distribution, and one calculator per test) so the logic is
unit-testable without a filesystem or network. The three module-level functions
are thin adapters that preserve the historical call signatures and dict return
shapes the skill depends on.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel


class _PrintStream:
    """Routes log records to stdout via print (the sandbox only returns stdout)."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=_PrintStream(),
    force=True,
)
logger = logging.getLogger(__name__)


ALPHA: float = 0.05
BETACF_MAX_ITERATIONS: int = 200
BETACF_EPSILON: float = 3.0e-12
BETACF_FLOATING_POINT_MIN: float = 1.0e-30
CONTINUITY_CORRECTION: float = 0.5
MINIMUM_PAIRED_SAMPLES: int = 2
MINIMUM_WILCOXON_SAMPLES: int = 1
INTERCEPT_TERM_NAME: str = "const"
DEFAULT_FEATURE_PREFIX: str = "x"


@dataclass(frozen=True)
class PairedSample:
    """Matched response values for two completion designs (pure input carrier)."""

    group_a: Sequence[float]
    group_b: Sequence[float]


@dataclass(frozen=True)
class RegressionRequest:
    """Inputs for an OLS fit: design matrix, response, and optional term names."""

    design_matrix: Sequence[Sequence[float]]
    response: Sequence[float]
    feature_names: Sequence[str] | None = None


class PairedTTestResult(BaseModel):
    """Paired t-test outcome; field order matches the historical dict."""

    mean_difference: float
    std_difference: float
    t_statistic: float
    p_value: float
    cohens_d: float
    n_pairs: int
    significant_at_005: bool


class WilcoxonResult(BaseModel):
    """Wilcoxon signed-rank outcome; field order matches the historical dict."""

    w_statistic: float
    z_score: float
    p_value: float
    n_effective: int
    significant_at_005: bool


class RegressionTerm(BaseModel):
    """One regression term; field order matches the historical dict."""

    term: str
    coefficient: float
    std_error: float
    t_statistic: float
    p_value: float
    significant_at_005: bool


class OlsResult(BaseModel):
    """OLS regression outcome; field order matches the historical dict."""

    terms: list[RegressionTerm]
    r_squared: float
    adj_r_squared: float
    df_residual: int
    n_samples: int


class StudentTDistribution:
    """Two-sided Student's t tail probability via the regularized incomplete beta
    function (pure). Tuning constants are injected, not read from the environment."""

    def __init__(
        self,
        max_iterations: int,
        epsilon: float,
        floating_point_min: float,
    ) -> None:
        self._max_iterations = max_iterations
        self._epsilon = epsilon
        self._floating_point_min = floating_point_min

    def two_sided_p_value(self, t_statistic: float, degrees_of_freedom: float) -> float:
        """Two-sided p-value for a t statistic with the given degrees of freedom."""
        if degrees_of_freedom <= 0:
            return float("nan")
        x = degrees_of_freedom / (degrees_of_freedom + t_statistic * t_statistic)
        return self._regularized_incomplete_beta(0.5 * degrees_of_freedom, 0.5, x)

    def _regularized_incomplete_beta(self, a: float, b: float, x: float) -> float:
        """Regularized incomplete beta function I_x(a, b)."""
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        ln_beta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        front = math.exp(ln_beta + a * math.log(x) + b * math.log(1.0 - x))
        if x < (a + 1.0) / (a + b + 2.0):
            return front * self._beta_continued_fraction(a, b, x) / a
        return 1.0 - front * self._beta_continued_fraction(b, a, 1.0 - x) / b

    def _beta_continued_fraction(self, a: float, b: float, x: float) -> float:
        """Continued fraction for the incomplete beta function."""
        qab = a + b
        qap = a + 1.0
        qam = a - 1.0
        c = 1.0
        d = 1.0 - qab * x / qap
        if abs(d) < self._floating_point_min:
            d = self._floating_point_min
        d = 1.0 / d
        h = d
        for m in range(1, self._max_iterations + 1):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < self._floating_point_min:
                d = self._floating_point_min
            c = 1.0 + aa / c
            if abs(c) < self._floating_point_min:
                c = self._floating_point_min
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < self._floating_point_min:
                d = self._floating_point_min
            c = 1.0 + aa / c
            if abs(c) < self._floating_point_min:
                c = self._floating_point_min
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < self._epsilon:
                break
        return h


class NormalDistribution:
    """Two-sided p-value for a standard normal z-score (pure)."""

    def two_sided_p_value(self, z_score: float) -> float:
        """Two-sided p-value for a standard normal z-score."""
        return math.erfc(abs(z_score) / math.sqrt(2.0))


class PairedTTestCalculator:
    """Paired t-test comparing matched completion designs (pure business logic)."""

    def __init__(self, t_distribution: StudentTDistribution) -> None:
        self._t_distribution = t_distribution

    def evaluate(self, sample: PairedSample) -> PairedTTestResult:
        """Compute the paired t-test for matched response values.

        group_a and group_b are equal-length sequences of the response variable for
        matched wells (for example EUR per foot). Returns the mean difference, its
        standard deviation, the t statistic, the two-sided p-value, Cohen's d for
        paired data, the pair count, and a significance flag at alpha = 0.05.
        """
        a = np.asarray(sample.group_a, dtype=float)
        b = np.asarray(sample.group_b, dtype=float)
        if a.shape != b.shape:
            raise ValueError("group_a and group_b must have the same length")
        diff = b - a
        n = diff.size
        if n < MINIMUM_PAIRED_SAMPLES:
            raise ValueError("need at least two matched pairs")
        mean_diff = float(np.mean(diff))
        sd_diff = float(np.std(diff, ddof=1))
        if sd_diff == 0.0:
            raise ValueError("differences have zero variance; test is undefined")
        t_stat = mean_diff / (sd_diff / math.sqrt(n))
        p_value = self._t_distribution.two_sided_p_value(t_stat, n - 1)
        return PairedTTestResult(
            mean_difference=mean_diff,
            std_difference=sd_diff,
            t_statistic=t_stat,
            p_value=p_value,
            cohens_d=mean_diff / sd_diff,
            n_pairs=int(n),
            significant_at_005=bool(p_value < ALPHA),
        )


class WilcoxonSignedRankCalculator:
    """Wilcoxon signed-rank test via the normal approximation (pure business logic)."""

    def __init__(self, normal_distribution: NormalDistribution) -> None:
        self._normal_distribution = normal_distribution

    def evaluate(self, differences: Sequence[float]) -> WilcoxonResult:
        """Compute the Wilcoxon signed-rank test on paired differences.

        Use when the difference distribution is non-normal or the sample is small.
        Zero differences are dropped. Ties share averaged ranks and the variance is
        tie-corrected. A continuity correction is applied. Returns the W statistic,
        the two-sided p-value, the effective sample size, and a significance flag.
        """
        diff = np.asarray(differences, dtype=float)
        diff = diff[diff != 0.0]
        n = diff.size
        if n < MINIMUM_WILCOXON_SAMPLES:
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
        z = (w_stat - mean_w + CONTINUITY_CORRECTION) / math.sqrt(var_w)
        p_value = self._normal_distribution.two_sided_p_value(z)
        return WilcoxonResult(
            w_statistic=w_stat,
            z_score=z,
            p_value=p_value,
            n_effective=int(n),
            significant_at_005=bool(p_value < ALPHA),
        )


class OlsRegressionCalculator:
    """Ordinary least squares by the normal equations (pure business logic)."""

    def __init__(self, t_distribution: StudentTDistribution) -> None:
        self._t_distribution = t_distribution

    def evaluate(self, request: RegressionRequest) -> OlsResult:
        """Fit ordinary least squares with an automatically added intercept.

        design_matrix is an (n_samples, n_features) array WITHOUT an intercept column;
        an intercept is added automatically. response is length n_samples. Returns per
        term (intercept first) the coefficient, standard error, t statistic, and
        two-sided p-value, plus R-squared, adjusted R-squared, and residual degrees of
        freedom.
        """
        x = np.asarray(request.design_matrix, dtype=float)
        if x.ndim == 1:
            x = x.reshape(-1, 1)
        y = np.asarray(request.response, dtype=float).reshape(-1)
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
        p_values = [
            self._t_distribution.two_sided_p_value(t, df_resid) for t in t_stats
        ]
        r_squared = 1.0 - ss_resid / ss_total if ss_total > 0 else float("nan")
        adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / df_resid

        names = self._term_names(request.feature_names, k)

        terms = [
            RegressionTerm(
                term=name,
                coefficient=float(beta[i]),
                std_error=float(se[i]),
                t_statistic=float(t_stats[i]),
                p_value=float(p_values[i]),
                significant_at_005=bool(p_values[i] < ALPHA),
            )
            for i, name in enumerate(names)
        ]
        return OlsResult(
            terms=terms,
            r_squared=r_squared,
            adj_r_squared=adj_r_squared,
            df_residual=int(df_resid),
            n_samples=int(n),
        )

    def _term_names(
        self, feature_names: Sequence[str] | None, feature_count: int
    ) -> list[str]:
        """Build the term-name list (intercept first) matching the historical order."""
        if feature_names is None:
            return [INTERCEPT_TERM_NAME] + [
                f"{DEFAULT_FEATURE_PREFIX}{i + 1}" for i in range(feature_count)
            ]
        return [INTERCEPT_TERM_NAME] + list(feature_names)


_STUDENT_T_DISTRIBUTION = StudentTDistribution(
    max_iterations=BETACF_MAX_ITERATIONS,
    epsilon=BETACF_EPSILON,
    floating_point_min=BETACF_FLOATING_POINT_MIN,
)
_NORMAL_DISTRIBUTION = NormalDistribution()


def paired_t_test(group_a: Sequence[float], group_b: Sequence[float]) -> dict:
    """Paired t-test comparing matched completion designs.

    group_a and group_b are equal-length sequences of the response variable for
    matched wells (for example EUR per foot). Returns the mean difference, its
    standard deviation, the t statistic, the two-sided p-value, Cohen's d for
    paired data, the pair count, and a significance flag at alpha = 0.05.
    """
    calculator = PairedTTestCalculator(_STUDENT_T_DISTRIBUTION)
    result = calculator.evaluate(PairedSample(group_a=group_a, group_b=group_b))
    return result.model_dump()


def wilcoxon_signed_rank(differences: Sequence[float]) -> dict:
    """Wilcoxon signed-rank test on paired differences (normal approximation).

    Use when the difference distribution is non-normal or the sample is small.
    Zero differences are dropped. Ties share averaged ranks and the variance is
    tie-corrected. A continuity correction is applied. Returns the W statistic,
    the two-sided p-value, the effective sample size, and a significance flag.
    """
    calculator = WilcoxonSignedRankCalculator(_NORMAL_DISTRIBUTION)
    result = calculator.evaluate(differences)
    return result.model_dump()


def ols_regression(
    design_matrix: Sequence[Sequence[float]],
    response: Sequence[float],
    feature_names: Sequence[str] | None = None,
) -> dict:
    """Ordinary least squares regression by the normal equations.

    design_matrix is an (n_samples, n_features) array WITHOUT an intercept column;
    an intercept is added automatically. response is length n_samples. Returns per
    term (intercept first) the coefficient, standard error, t statistic, and
    two-sided p-value, plus R-squared, adjusted R-squared, and residual degrees of
    freedom.
    """
    calculator = OlsRegressionCalculator(_STUDENT_T_DISTRIBUTION)
    result = calculator.evaluate(
        RegressionRequest(
            design_matrix=design_matrix,
            response=response,
            feature_names=feature_names,
        )
    )
    return result.model_dump()
