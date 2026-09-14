"""
description: ASTM E1049-85 four-point rainflow cycle counting for state-of-charge series implemented with only the Python standard library.
last_updated: 2026-09-13
origin: original

ASTM E1049-85 four-point rainflow cycle counting for state-of-charge series.

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

import argparse
import logging
import sys
from dataclasses import dataclass


class _PrintStream:
    """Adapter that lets logging emit timestamped lines to the real stdout."""

    def write(self, message: str) -> None:
        text = message.rstrip("\n")
        if text:
            sys.__stdout__.write(text + "\n")

    def flush(self) -> None:
        sys.__stdout__.flush()


logging.basicConfig(
    stream=_PrintStream(),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    force=True,
)
_LOGGER = logging.getLogger(__name__)

# The four-point method compares an inner range against its two neighbours, so a
# reduction requires at least four retained turning points on the stack.
MIN_POINTS_FOR_TURNING = 3
MIN_STACK_FOR_REDUCTION = 4

# Cycle weights per ASTM E1049-85: closed cycles count once, residuals count half.
FULL_CYCLE_COUNT = 1.0
HALF_CYCLE_COUNT = 0.5


@dataclass(frozen=True)
class Cycle:
    """A single rainflow-extracted cycle as a structured carrier.

    cycle_range is the DoD magnitude, mean the cycle midpoint, and count the
    ASTM weight (1.0 for a closed cycle, 0.5 for a residual half-cycle).
    """

    cycle_range: float
    mean: float
    count: float

    def as_tuple(self) -> tuple[float, float, float]:
        """Legacy (range, mean, count) tuple form consumed by degradation.py."""
        return (self.cycle_range, self.mean, self.count)


class RainflowCounter:
    """Pure four-point rainflow cycle counter over a state-of-charge series."""

    def count(self, series: list[float]) -> list[Cycle]:
        """Extract rainflow cycles from `series` using the 4-point method."""
        points = self._turning_points(self._dedupe(list(series)))
        cycles: list[Cycle] = []
        stack: list[float] = []
        for point in points:
            stack.append(point)
            self._reduce_stack(stack, cycles)
        self._append_residuals(stack, cycles)
        return cycles

    def _dedupe(self, series: list[float]) -> list[float]:
        """Collapse consecutive equal values so plateaus do not create zero ranges."""
        out: list[float] = []
        for value in series:
            if not out or out[-1] != value:
                out.append(value)
        return out

    def _turning_points(self, series: list[float]) -> list[float]:
        """Reduce a series to its reversal points (local minima and maxima)."""
        if len(series) < MIN_POINTS_FOR_TURNING:
            return list(series)
        points = [series[0]]
        for i in range(1, len(series) - 1):
            prev, cur, nxt = series[i - 1], series[i], series[i + 1]
            if (cur - prev) * (nxt - cur) < 0:
                points.append(cur)
        points.append(series[-1])
        return points

    def _reduce_stack(self, stack: list[float], cycles: list[Cycle]) -> None:
        """Close every full cycle currently resolvable on the top of the stack."""
        while len(stack) >= MIN_STACK_FOR_REDUCTION:
            s0, s1, s2, s3 = stack[-4], stack[-3], stack[-2], stack[-1]
            range_inner = abs(s2 - s1)
            range_left = abs(s1 - s0)
            range_right = abs(s3 - s2)
            if range_inner <= range_left and range_inner <= range_right:
                cycles.append(Cycle(range_inner, (s1 + s2) / 2.0, FULL_CYCLE_COUNT))
                del stack[-3:-1]
            else:
                break

    def _append_residuals(self, stack: list[float], cycles: list[Cycle]) -> None:
        """Record the remaining open ranges as half-cycles."""
        for k in range(len(stack) - 1):
            rng = abs(stack[k + 1] - stack[k])
            cycles.append(Cycle(rng, (stack[k] + stack[k + 1]) / 2.0, HALF_CYCLE_COUNT))


def count_cycles(series: list[float]) -> list[tuple[float, float, float]]:
    """Return rainflow cycles as (range, mean, count) using the 4-point method."""
    return [cycle.as_tuple() for cycle in RainflowCounter().count(series)]


def _build_parser() -> argparse.ArgumentParser:
    """Construct the command-line parser for the rainflow demonstration."""
    parser = argparse.ArgumentParser(
        description="ASTM E1049-85 four-point rainflow cycle counting on an SOC series.",
    )
    parser.add_argument(
        "--series",
        type=float,
        nargs="+",
        required=True,
        help="State-of-charge values in time order.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Count cycles for the supplied SOC series and log each result."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    cycles = count_cycles(args.series)
    for cycle_range, mean, count in cycles:
        _LOGGER.info("range=%s mean=%s count=%s", cycle_range, mean, count)
    _LOGGER.info("total_cycles=%d", len(cycles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
