"""
description: The data one Forecast Coach run carries from the forecast step to the sheet writers: series, forecasts, backtests, methods per series, balances, period labels, and run settings.
last_updated: 2026-11-24
origin: original
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunContext:
    """Everything the sheet writers read. Built once by coach.build; never changed afterward."""

    names: list
    clean: dict  # {series: {"values": array, "dates": list or None}}
    fc: dict  # {series: baseline dict from stat_methods.baseline}
    bt: dict  # {series: backtest_all result}
    methods: dict  # {series: {label: array}} for every method with enough history
    missing: dict  # {series: [labels without enough history]}
    default: dict  # {series: label the Method picker starts on}
    stocks: frozenset
    labels: list
    horizon: int
    freq: str
    season: int
    units: str
    title: str
    run_id: str
