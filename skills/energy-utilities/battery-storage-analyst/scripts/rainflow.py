"""ASTM E1049-85 four-point rainflow cycle counting for state-of-charge series.

Extracts charge and discharge cycles from an irregular state-of-charge (SOC)
time series so cycle-aging damage can be computed per depth-of-discharge (DoD).
Uses only the Python standard library so it runs inside the Amazon Quick
sandbox, which does not provide the third-party `rainflow` package.

Usage:
    from rainflow import count_cycles
    cycles = count_cycles(soc_series)  # list of (range, mean, count) tuples

Each returned range is a DoD magnitude on the same scale as the input SOC. Feed
the ranges to scripts/degradation.py cycle_damage(). Full cycles carry count
1.0, residual half-cycles carry 0.5.
"""

from __future__ import annotations


def _dedupe(series: list[float]) -> list[float]:
    """Collapse consecutive equal values so plateaus do not create zero ranges."""
    out: list[float] = []
    for value in series:
        if not out or out[-1] != value:
            out.append(value)
    return out


def _turning_points(series: list[float]) -> list[float]:
    """Reduce a series to its reversal points (local minima and maxima)."""
    if len(series) < 3:
        return list(series)
    points = [series[0]]
    for i in range(1, len(series) - 1):
        prev, cur, nxt = series[i - 1], series[i], series[i + 1]
        if (cur - prev) * (nxt - cur) < 0:
            points.append(cur)
    points.append(series[-1])
    return points


def count_cycles(series: list[float]) -> list[tuple[float, float, float]]:
    """Return rainflow cycles as (range, mean, count) using the 4-point method."""
    points = _turning_points(_dedupe(list(series)))
    cycles: list[tuple[float, float, float]] = []
    stack: list[float] = []
    for point in points:
        stack.append(point)
        while len(stack) >= 4:
            s0, s1, s2, s3 = stack[-4], stack[-3], stack[-2], stack[-1]
            range_inner = abs(s2 - s1)
            range_left = abs(s1 - s0)
            range_right = abs(s3 - s2)
            if range_inner <= range_left and range_inner <= range_right:
                cycles.append((range_inner, (s1 + s2) / 2.0, 1.0))
                del stack[-3:-1]
            else:
                break
    for k in range(len(stack) - 1):
        rng = abs(stack[k + 1] - stack[k])
        cycles.append((rng, (stack[k] + stack[k + 1]) / 2.0, 0.5))
    return cycles
