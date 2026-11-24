"""
description: Provide the statistics used by the trend and anomaly analyses, using numpy and the standard library only.
last_updated: 2026-11-24
sources:
  - https://dlmf.nist.gov/8.17
  - https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm
  - https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h3.htm
  - https://doi.org/10.1080/01621459.1993.10476408

Statistics used by the trend and anomaly analyses. numpy and the standard library only.

Everything here is a textbook method written out so the skill needs no scipy:

    mad_scale, modified_z      robust scatter and the Iglewicz-Hoaglin modified z-score (NIST 1.3.5.17)
    qn_scale                   the Rousseeuw-Croux Qn scatter: as robust as the MAD, far less variable in short samples
    robust_z                   the z-score built on Qn, which is what the analyses flag on
    screen_scale               a cruder, contamination-proof scatter used only for a first screening pass
    generalized_esd            Rosner's generalized ESD test for up to k outliers (NIST 1.3.5.17.3)
    mann_whitney               two-sample rank test: exact for small samples without ties, else normal
    mann_kendall               rank test for a monotonic trend
    theil_sen                  median-of-pairwise-slopes line
    t_ppf, t_cdf, norm_sf      distribution functions the tests need
"""

from __future__ import annotations

import math
import sys

import numpy as np

__all__ = [
    "mad_scale",
    "modified_z",
    "qn_scale",
    "screen_scale",
    "robust_z",
    "generalized_esd",
    "mann_whitney",
    "mann_kendall",
    "theil_sen",
    "t_ppf",
    "t_cdf",
    "norm_sf",
]

MAD_TO_SD = 1.4826  # MAD x this estimates a standard deviation for normal data
MODZ_CONST = 0.6745  # = 1 / MAD_TO_SD, the constant in the modified z-score


def norm_sf(z: float) -> float:
    """P(Z > z) for a standard normal."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


_CF_FLOOR = sys.float_info.min  # keeps a zero denominator from dividing by zero


def _beta_cf_coefficient(k: int, a: float, b: float, x: float) -> float:
    """Coefficient d_k of the incomplete beta continued fraction, DLMF 8.17.22.

    For k = 2m:      d_k =  m (b - m) x / ((a + 2m - 1)(a + 2m))
    For k = 2m + 1:  d_k = -(a + m)(a + b + m) x / ((a + 2m)(a + 2m + 1))
    """
    m = k // 2
    if k % 2 == 0:
        return m * (b - m) * x / ((a + 2 * m - 1.0) * (a + 2 * m))
    return -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1.0))


def _beta_cf_tail(a: float, b: float, x: float, terms: int) -> float:
    """The denominator 1 + d_1/(1 + d_2/(1 + ...)) truncated after `terms`."""
    tail = 1.0
    for k in range(terms, 0, -1):
        tail = 1.0 + _beta_cf_coefficient(k, a, b, x) / tail
        if abs(tail) < _CF_FLOOR:
            tail = _CF_FLOOR
    return tail


def _betacf(a: float, b: float, x: float) -> float:
    """Evaluate the DLMF 8.17.22 continued fraction for the incomplete beta.

    The fraction is 1 / (1 + d_1 / (1 + d_2 / (1 + ...))). Summing it from the
    far end inwards converges from below, so the depth is doubled until two
    successive depths agree, which keeps short and long series alike exact
    without a fixed iteration budget. The caller supplies the leading factor.
    """
    terms = 32
    previous = _beta_cf_tail(a, b, x, terms)
    for _ in range(6):
        terms *= 2
        tail = _beta_cf_tail(a, b, x, terms)
        if abs(tail - previous) <= 1e-16 * abs(tail):
            return 1.0 / tail
        previous = tail
    return 1.0 / previous


def _betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    """P(T <= t) for Student's t with df degrees of freedom."""
    if df <= 0:
        raise ValueError("df must be positive")
    tail = 0.5 * _betainc(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t >= 0 else tail


def t_ppf(p: float, df: float) -> float:
    """The value t with P(T <= t) = p. Bisection on t_cdf, good to about 1e-10."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be strictly between 0 and 1")
    if p == 0.5:
        return 0.0
    if p < 0.5:
        return -t_ppf(1.0 - p, df)
    lo, hi = 0.0, 2.0
    while t_cdf(hi, df) < p:
        lo, hi = hi, hi * 2.0
        if hi > 1e12:
            break
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12 * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


def mad_scale(x, floor: float = 0.0) -> float:
    """Median absolute deviation scaled to a standard deviation, never below `floor`."""
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return float("nan")
    return max(MAD_TO_SD * float(np.median(np.abs(a - np.median(a)))), float(floor))


def modified_z(x, floor: float = 0.0) -> np.ndarray:
    """Modified z-score 0.6745 (x - median) / MAD for every element; NaN stays NaN.

    `floor` is the smallest scatter (in standard-deviation units) the score may assume, so a line that
    is flat to the last digit does not turn a rounding difference into an extreme score.
    """
    a = np.asarray(x, dtype=float)
    ok = np.isfinite(a)
    out = np.full(a.shape, np.nan)
    if ok.sum() == 0:
        return out
    med = float(np.median(a[ok]))
    scale = mad_scale(a[ok], floor)
    if not scale > 0:
        out[ok] = 0.0
        return out
    out[ok] = (a[ok] - med) / scale
    return out


_QN_SMALL = {
    2: 0.399,
    3: 0.994,
    4: 0.512,
    5: 0.844,
    6: 0.611,
    7: 0.857,
    8: 0.669,
    9: 0.872,
}


MAX_QN_POINTS = 2000  # pairwise Qn and the level-shift search are quadratic; this keeps one line near 4 s and 64 MB


def qn_scale(x, floor: float = 0.0) -> float:
    """Rousseeuw and Croux's Qn estimate of scatter, scaled to a standard deviation, never below `floor`.

    Qn is the k-th smallest distance between pairs of observations (k about a quarter of the pairs). Like
    the MAD it ignores up to half the data being wild, but it uses the data far more efficiently (about
    82% against 37% for normal data), so in a line of 24 to 60 periods it is much less likely to come
    out too small by chance and turn ordinary periods into flags.
    """
    a = np.asarray(x, dtype=float)
    if a.size > MAX_QN_POINTS:
        raise ValueError(
            f"Qn supports at most {MAX_QN_POINTS} observations per analysis. "
            "Confirm a shorter window or a coarser grain; the estimator and "
            "history have not been changed."
        )
    a = np.sort(a[np.isfinite(a)])
    n = a.size
    if n == 0:
        return float("nan")
    if n == 1:
        return float(floor)
    i, j = np.triu_indices(n, 1)
    dist = np.sort(a[j] - a[i])
    h = n // 2 + 1
    k = h * (h - 1) // 2
    dn = _QN_SMALL.get(n, n / (n + 1.4) if n % 2 else n / (n + 3.8))
    return max(2.21914 * dn * float(dist[k - 1]), float(floor))


def screen_scale(x, floor: float = 0.0) -> float:
    """A deliberately contamination-proof scatter, for a first screening pass only.

    The 40th percentile of the absolute deviations from the median, scaled to a standard deviation for
    normal data. It stays put with up to about half the periods disturbed, which matters early on, when
    a run of unusual months has also bent the expected values of its neighbors and of the same months
    in other years. It is too variable to judge periods by; the final scores use qn_scale.
    """
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return float("nan")
    dev = np.sort(np.abs(a - np.median(a)))
    return max(float(dev[min(a.size - 1, int(0.4 * a.size))]) / 0.5244, float(floor))


def robust_z(x, floor: float = 0.0, screen: bool = False) -> np.ndarray:
    """(x - median) / Qn scatter for every element; NaN stays NaN. See modified_z for the `floor`.

    screen=True divides by screen_scale instead (first-pass screening).
    """
    a = np.asarray(x, dtype=float)
    ok = np.isfinite(a)
    out = np.full(a.shape, np.nan)
    if ok.sum() == 0:
        return out
    scale = screen_scale(a[ok], floor) if screen else qn_scale(a[ok], floor)
    if not scale > 0:
        out[ok] = 0.0
        return out
    out[ok] = (a[ok] - float(np.median(a[ok]))) / scale
    return out


def generalized_esd(x, max_outliers: int | None = None, alpha: float = 0.05) -> dict:
    """Rosner's generalized extreme studentized deviate test.

    Tests for up to `max_outliers` outliers in roughly normal data without having to say how many there
    are. Unlike a single Grubbs test it is not blinded when two outliers mask each other.
    Returns {'outliers': positions in x, most extreme first, 'R': [...], 'lambda': [...], 'tested': n}.
    NaN entries are ignored. NIST calls the critical values very accurate for n >= 25 and reasonably
    accurate for n >= 15; callers should not lean on the result below that.
    """
    a = np.asarray(x, dtype=float)
    idx = np.where(np.isfinite(a))[0]
    n = idx.size
    if n < 3:
        return {"outliers": [], "R": [], "lambda": [], "tested": int(n)}
    k = int(max_outliers) if max_outliers is not None else max(1, min(10, n // 7))
    k = max(1, min(k, n - 2))
    vals, pos = a[idx].copy(), idx.copy()
    R, lam, removed = [], [], []
    for i in range(1, k + 1):
        mean, sd = float(vals.mean()), float(vals.std(ddof=1))
        if not sd > 0:
            break
        dev = np.abs(vals - mean)
        j = int(np.argmax(dev))
        R.append(float(dev[j] / sd))
        p = 1.0 - alpha / (2.0 * (n - i + 1))
        t = t_ppf(p, n - i - 1)
        lam.append(float((n - i) * t / math.sqrt((n - i - 1 + t * t) * (n - i + 1))))
        removed.append(int(pos[j]))
        vals, pos = np.delete(vals, j), np.delete(pos, j)
    count = 0
    for i in range(len(R)):
        if R[i] > lam[i]:
            count = i + 1
    return {"outliers": removed[:count], "R": R, "lambda": lam, "tested": int(n)}


def _mw_exact_sf(n1: int, n2: int, u: int) -> float:
    """P(U >= u) under the null, no ties, by counting arrangements."""
    top = n1 * n2
    # ways[m][v] = number of ways for the first sample of size m (against the n seen so far) to score v
    prev = [[1] + [0] * top for _ in range(n1 + 1)]  # n = 0: U is always 0
    for n in range(1, n2 + 1):
        cur = [[1] + [0] * top]  # m = 0
        for m in range(1, n1 + 1):
            row = [0] * (top + 1)
            a, b = cur[m - 1], prev[m]
            for v in range(m * n + 1):
                row[v] = (a[v - n] if v >= n else 0) + b[v]
            cur.append(row)
        prev = cur
    counts = prev[n1][: top + 1]
    total = sum(counts)
    return sum(counts[u:]) / total


def mann_whitney(a, b) -> dict:
    """Two-sided Mann-Whitney U test that samples a and b come from the same distribution.

    Exact when there are no ties and the samples are small (n1 * n2 <= 400); otherwise the normal
    approximation with tie and continuity corrections. Returns {'U', 'p', 'method', 'n1', 'n2'}.
    """
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    x, y = x[np.isfinite(x)], y[np.isfinite(y)]
    n1, n2 = x.size, y.size
    if n1 == 0 or n2 == 0:
        return {
            "U": float("nan"),
            "p": float("nan"),
            "method": "none",
            "n1": int(n1),
            "n2": int(n2),
        }
    allv = np.concatenate([x, y])
    order = np.argsort(allv, kind="mergesort")
    ranks = np.empty(allv.size, dtype=float)
    sorted_v = allv[order]
    i, ties = 0, []
    while i < allv.size:
        j = i
        while j + 1 < allv.size and sorted_v[j + 1] == sorted_v[i]:
            j += 1
        ranks[order[i : j + 1]] = 0.5 * (i + j) + 1.0
        if j > i:
            ties.append(j - i + 1)
        i = j + 1
    u1 = float(
        ranks[:n1].sum() - n1 * (n1 + 1) / 2.0
    )  # number of (x, y) pairs with x > y
    u_big = max(u1, n1 * n2 - u1)
    if not ties and n1 * n2 <= 400:
        p = min(1.0, 2.0 * _mw_exact_sf(n1, n2, int(round(u_big))))
        return {"U": u1, "p": float(p), "method": "exact", "n1": int(n1), "n2": int(n2)}
    n = n1 + n2
    tie_term = sum(t**3 - t for t in ties) / (n * (n - 1.0)) if n > 1 else 0.0
    var = n1 * n2 / 12.0 * ((n + 1.0) - tie_term)
    if not var > 0:
        return {"U": u1, "p": 1.0, "method": "normal", "n1": int(n1), "n2": int(n2)}
    z = (u_big - n1 * n2 / 2.0 - 0.5) / math.sqrt(var)
    return {
        "U": u1,
        "p": float(min(1.0, 2.0 * norm_sf(z))),
        "method": "normal",
        "n1": int(n1),
        "n2": int(n2),
    }


def mann_kendall(x) -> dict:
    """Mann-Kendall test for a monotonic trend. Returns {'S', 'z', 'p', 'n'}; p is two-sided.

    Normal approximation with tie and continuity corrections, which is adequate from about 8 points.
    """
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    n = a.size
    if n < 4:
        return {"S": 0.0, "z": 0.0, "p": 1.0, "n": int(n)}
    diff = np.sign(a[None, :] - a[:, None])
    s = float(np.triu(diff, 1).sum())
    _, counts = np.unique(a, return_counts=True)
    tie = float(sum(c * (c - 1) * (2 * c + 5) for c in counts if c > 1))
    var = (n * (n - 1) * (2 * n + 5) - tie) / 18.0
    if not var > 0:
        return {"S": s, "z": 0.0, "p": 1.0, "n": int(n)}
    z = (
        (s - 1.0) / math.sqrt(var)
        if s > 0
        else ((s + 1.0) / math.sqrt(var) if s < 0 else 0.0)
    )
    return {
        "S": s,
        "z": float(z),
        "p": float(min(1.0, 2.0 * norm_sf(abs(z)))),
        "n": int(n),
    }


def theil_sen(t, y) -> tuple:
    """Robust line through (t, y): slope = median of pairwise slopes, intercept = median(y - slope t).

    Returns (slope, intercept). With fewer than two usable points the slope is 0.
    """
    tt = np.asarray(t, dtype=float)
    yy = np.asarray(y, dtype=float)
    ok = np.isfinite(tt) & np.isfinite(yy)
    tt, yy = tt[ok], yy[ok]
    if tt.size == 0:
        return 0.0, float("nan")
    if tt.size == 1:
        return 0.0, float(yy[0])
    i, j = np.triu_indices(tt.size, 1)
    dt = tt[j] - tt[i]
    keep = dt != 0
    if not keep.any():
        return 0.0, float(np.median(yy))
    slope = float(np.median((yy[j] - yy[i])[keep] / dt[keep]))
    return slope, float(np.median(yy - slope * tt))
