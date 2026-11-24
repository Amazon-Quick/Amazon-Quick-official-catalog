"""
description: Deterministic Nelder-Mead minimizer with the standard reflection, expansion, contraction, and shrink coefficients, used to fit the smoothing parameters.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np


def minimize(
    f: Callable[[np.ndarray], float], x0: np.ndarray, step: np.ndarray, iters: int = 400
) -> tuple[np.ndarray, float]:
    """(best point, best value) after at most `iters` Nelder-Mead iterations from `x0`."""
    n = x0.size
    simplex = [x0.astype(float)]
    for i in range(n):
        v = x0.astype(float).copy()
        v[i] += step[i]
        simplex.append(v)
    vals = [f(v) for v in simplex]
    for _ in range(iters):
        order = np.argsort(vals, kind="stable")
        simplex = [simplex[i] for i in order]
        vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) <= 1e-10 * (abs(vals[0]) + 1e-12):
            break
        centroid = np.mean(simplex[:-1], axis=0)
        xr = centroid + (centroid - simplex[-1])
        fr = f(xr)
        if fr < vals[0]:
            xe = centroid + 2.0 * (centroid - simplex[-1])
            fe = f(xe)
            simplex[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            simplex[-1], vals[-1] = xr, fr
        else:
            xc = centroid + 0.5 * (simplex[-1] - centroid)
            fc = f(xc)
            if fc < vals[-1]:
                simplex[-1], vals[-1] = xc, fc
            else:
                best = simplex[0]
                simplex = [best] + [best + 0.5 * (v - best) for v in simplex[1:]]
                vals = [vals[0]] + [f(v) for v in simplex[1:]]
    i = int(np.argmin(vals))
    return simplex[i], vals[i]
