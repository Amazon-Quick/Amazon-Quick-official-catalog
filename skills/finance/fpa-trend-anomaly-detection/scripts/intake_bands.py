"""
description: Find the row or column of period headings in a sheet, and the Actual or plan tags over it.
last_updated: 2026-11-24
"""

from __future__ import annotations

from intake_cells import _ACTUAL_WORDS, _PLAN_WORDS, _col, _matrix, _text
from intake_periods import _cells_as_periods, _freq, _longest_run_loose, parse_period


def _tags_for(mat: list, r: int, positions: list) -> dict:
    """{column: scenario label} for the period columns of header row r, read from the rows around it.

    Two shapes are understood: a label under or over every period column ("Actuals", "Budget", "Forecast"),
    and a label written once at the start of a group of columns, which applies until the next label.
    A row only counts if it contains at least one word that names a scenario, so a units row is ignored.
    """

    def scen(t):
        return (
            bool(t)
            and len(t) <= 28
            and (_ACTUAL_WORDS.match(t) or _PLAN_WORDS.search(t))
            and not parse_period(t)
        )

    near = [x for x in (r + 1, r - 1, r + 2, r - 2, r + 3, r - 3) if 0 <= x < len(mat)]
    for x in near:  # a label on every column
        row = mat[x]
        got = {
            c: _text(row[c])
            for c in positions
            if c < len(row) and _text(row[c]) and len(_text(row[c])) <= 28
        }
        if len(got) >= 0.6 * len(positions) and any(scen(t) for t in got.values()):
            return got
    for x in (r - 1, r - 2, r - 3):  # a label once per group of columns
        if x < 0:
            continue
        row, cur, got = mat[x], None, {}
        for c in range(max(positions) + 1):
            t = _text(row[c]) if c < len(row) else ""
            if scen(t):
                cur = t
            if cur and c in positions:
                got[c] = cur
        if len(got) >= 0.6 * len(positions) and any(
            _ACTUAL_WORDS.match(t) for t in got.values()
        ):
            return got
    return {}


def _row_band(mat: list, r: int, date_order=None) -> dict | None:
    """The period columns of header row r, in date order, keeping only actuals when the sheet marks them."""
    cells = _cells_as_periods(
        [(c, v) for c, v in enumerate(mat[r]) if v is not None], date_order
    )
    if len(cells) < 4:
        return None
    tags = _tags_for(mat, r, [c for c, _ in cells])
    other = sorted({t for t in tags.values() if not _ACTUAL_WORDS.match(t)})
    if tags:
        cells = [(c, d) for c, d in cells if _ACTUAL_WORDS.match(tags.get(c, ""))]
        if not cells:
            return {"index": r, "no_actuals": other}
    by_date: dict = {}
    for c, d in cells:
        by_date.setdefault(d, c)
    dates = sorted(by_date)
    # Keep every recognizable period. Trimming to the longest regular run silently discards
    # valid history around a missing/bad header; prepare() can ask about irregular spacing.
    pos = [by_date[d] for d in dates]
    if len(dates) < 4:
        return None
    return {
        "orientation": "columns",
        "index": r,
        "positions": pos,
        "dates": dates,
        "tagged": bool(tags),
        "other_scenarios": other,
        "repeats": (len(cells) > len(by_date)) and not tags,
    }


def _find_band(
    mat: list, scan_rows: int = 40, scan_cols: int = 8, date_order=None
) -> dict | None:
    """Where the periods are: across a header row (wide layout) or down a column (long layout)."""
    best = None
    for r in range(min(scan_rows, len(mat))):
        b = _row_band(mat, r, date_order)
        if (
            b
            and "dates" in b
            and (best is None or len(b["dates"]) > len(best["dates"]))
        ):
            best = b
    for c in range(min(scan_cols, max((len(r) for r in mat[:50]), default=0))):
        col = _cells_as_periods(
            [
                (r, row[c])
                for r, row in enumerate(mat)
                if c < len(row) and row[c] is not None
            ],
            date_order,
        )
        pos, dates = _longest_run_loose(col)
        if len(dates) >= 8 and (best is None or len(dates) > 3 * len(best["dates"])):
            best = {"orientation": "rows", "index": c, "positions": pos, "dates": dates}
    if best:
        best["freq"] = _freq(best["dates"])
    return best


def _no_actuals(mat: list, scan_rows: int = 40) -> str:
    """Says so when a sheet has period columns but marks none of them as actuals."""
    for r in range(min(scan_rows, len(mat))):
        b = _row_band(mat, r)
        if b and b.get("no_actuals"):
            return f"row {r + 1} has period columns, but all are marked {' / '.join(b['no_actuals'][:4])} and none Actuals"
    return ""


def _scenario_columns(mat: list, scan_rows: int = 40) -> str:
    """Says so when a sheet's columns are scenarios (FY25 Actuals, FY26 Budget, FY26 Forecast ...), not a time series."""
    why = _no_actuals(mat, scan_rows)
    if why:
        return why
    for r, row in enumerate(mat[:scan_rows]):
        cells = [
            (c, parse_period(v))
            for c, v in enumerate(row)
            if v is not None and parse_period(v)
        ]
        if len(cells) >= 4 and len({d for _, d in cells}) < len(cells):
            return f"row {r + 1} repeats period labels across columns: these look like scenarios side by side (actuals, plans, forecasts), not a history over time"
    return ""


def periods(path: str, sheet: str | None = None) -> dict:
    """Where this sheet's period header is, what it covers and at what frequency. {} if none is found."""
    mat, _, name = _matrix(path, sheet)
    b = _find_band(mat)
    if not b:
        return {}
    where = (
        f"row {b['index'] + 1}, columns {_col(min(b['positions']))} to {_col(max(b['positions']))}{' (actual columns only)' if b.get('tagged') else ''}"
        if b["orientation"] == "columns"
        else f"column {_col(b['index'])}, rows {b['positions'][0] + 1} to {b['positions'][-1] + 1}"
    )
    return {
        "sheet": name,
        "layout": "wide (periods across columns)"
        if b["orientation"] == "columns"
        else "long (periods down a column)",
        "where": where,
        "first": b["dates"][0].isoformat(),
        "last": b["dates"][-1].isoformat(),
        "count": len(b["dates"]),
        "freq": b["freq"],
    }
