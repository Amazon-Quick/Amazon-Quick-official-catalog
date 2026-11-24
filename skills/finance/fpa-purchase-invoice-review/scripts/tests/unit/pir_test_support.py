"""
description: Shared helpers for the fpa-purchase-invoice-review unit tests: reset engine state, inject tables in memory, and run a pasted message through stdin, so no test reads or writes a file.
last_updated: 2026-11-24

Run from the skill folder: PYTHONPATH=scripts python -m pytest scripts/tests/unit -q
"""

import io
import sys
from contextlib import contextmanager

import pir_check
from pir_state import (
    _EXCLUDED_ROWS,
    _IGNORED_TABLES,
    _MAPPED_COLS,
    _STATE,
    _TABLE_CACHE,
    INPUTS,
)


class NS:
    """Argument namespace for calling one cmd_* function directly; unset names are None."""

    def __init__(self, **kwargs: object) -> None:
        self.__dict__.update(kwargs)

    def __getattr__(self, name: str) -> None:
        return None


def reset_state() -> None:
    """Clear the per-call state the engine shares between modules."""
    for shared in (INPUTS, _EXCLUDED_ROWS, _IGNORED_TABLES):
        shared.clear()
    _TABLE_CACHE.clear()
    _MAPPED_COLS.clear()
    _STATE.clear()
    _STATE.update({"result": None, "quiet": True, "column_map": {}})


def table(name: str, rows: list[dict]) -> str:
    """Put rows in the table cache under a pseudo path and return that path."""
    path = f"<test>:{name}"
    _TABLE_CACHE[path] = [dict(r, _src=f"{name}:{i + 2}") for i, r in enumerate(rows)]
    return path


def result() -> dict:
    """The result the last cmd_* call emitted."""
    return _STATE["result"]


@contextmanager
def stdin_text(text: str):
    """Serve text as standard input, the engine's `--input -` source."""
    saved = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(text.encode("utf-8")), encoding="utf-8")
    try:
        yield
    finally:
        sys.stdin = saved


def run_message(text: str, *args: str) -> dict:
    """Run `all --input -` on a pasted message held in memory."""
    with stdin_text(text):
        return pir_check.run(["all", "--input", "-", *args])
