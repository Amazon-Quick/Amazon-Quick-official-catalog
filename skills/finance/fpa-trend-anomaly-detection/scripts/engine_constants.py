"""
description: Constants shared by the engine modules: cycles, windows, thresholds.
last_updated: 2026-11-24
"""

from __future__ import annotations

SEASON = {"D": 7, "W": 52, "MS": 12, "QS": 4, "YS": 1}  # periods in one seasonal cycle
PER_YEAR = {"D": 365.25, "W": 52.18, "MS": 12, "QS": 4, "YS": 1}
MIN_AFTER = {
    "D": 7,
    "W": 4,
    "MS": 3,
    "QS": 3,
    "YS": 3,
}  # periods a step must hold before it is a new level
W_AFTER = {
    "D": 14,
    "W": 8,
    "MS": 6,
    "QS": 4,
    "YS": 3,
}  # periods after a candidate step that are compared
W_BEFORE = {"D": 28, "W": 13, "MS": 12, "QS": 8, "YS": 6}  # periods before it
MIN_BEFORE = (
    3  # periods needed before a candidate step (the rank test then needs more to pass)
)
MIN_POINTS = 8  # below this nothing is judged
NEIGHBOURS = 6  # periods around a point that set its expected level
SLOPE_SPAN = 12  # periods around a point that set the local slope
SCALE_FLOOR = 0.005  # smallest scatter assumed: 0.5% of level
SEASONAL_GAIN = 0.85  # scatter with seasonal adjustment / without, below which adjusting clearly helps
SHIFT_T = 4.0  # how many standard errors a step must clear
