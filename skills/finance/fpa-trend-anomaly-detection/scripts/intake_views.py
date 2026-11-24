"""
description: Small, capped text views of a workbook (menu, values, find, rows) so no sheet is dumped into context.
last_updated: 2026-11-24
"""

from __future__ import annotations

import datetime as _dt

from intake_bands import _find_band, _scenario_columns
from intake_cells import ROW_CAP, TEXT_CAP, _book, _col, _is_num, _matrix, _text
from intake_periods import parse_period


def _cap(lines: list, limit: int = TEXT_CAP) -> str:
    text = "\n".join(lines)
    return (
        text
        if len(text) <= limit
        else text[: limit - 70]
        + f"\n... (capped at {limit} characters; narrow the request)"
    )


def menu(path: str, sheet: str | None = None, max_labels: int = 25) -> str:
    """Every sheet: size, header text, row labels and where its periods are. No numbers.

    With many sheets the overview shortens each one so that all of them are always listed; pass
    sheet= for the full label list of one.
    """
    is_csv = str(path).lower().endswith((".csv", ".txt"))
    sheets = (
        [None]
        if is_csv
        else ([sheet] if sheet else [ws.title for ws in _book(path).worksheets])
    )
    per_sheet = TEXT_CAP // max(len(sheets), 1)
    n_labels = int(max(0, min(max_labels, (per_sheet - 160) // 45)))
    out = []
    for s_ in sheets:
        mat, _, name = _matrix(path, s_, max_rows=400, max_cols=160)
        state = ""
        if s_ is not None:
            st = getattr(_book(path)[s_], "sheet_state", "visible")
            state = "" if st == "visible" else f"  [{st}]"
        lines = [
            "=== {}  ({} rows read){}".format(
                name, len(mat) if len(mat) < 400 else "400+", state
            )
        ]
        b = _find_band(mat)
        if b:
            p = (
                (f"row {b['index'] + 1}")
                if b["orientation"] == "columns"
                else ("column {}".format(_col(b["index"])))
            )
            if b.get("other_scenarios"):
                others = ", ".join(b["other_scenarios"][:4])
                scenario_note = (
                    f" (columns marked Actuals; also on the sheet: {others})"
                )
            elif b.get("tagged"):
                scenario_note = " (columns marked Actuals)"
            else:
                scenario_note = ""
            first_period = b["dates"][0].isoformat()[:7]
            last_period = b["dates"][-1].isoformat()[:7]
            lines.append(
                f"  periods: {p}, {first_period} to {last_period}, "
                f"{len(b['dates'])} {b['freq']} periods{scenario_note}"
            )
        else:
            lines.append(
                "  periods: "
                + (_scenario_columns(mat) or "none found in the first rows")
            )
        seen, labels = set(), []
        for r, row in enumerate(mat):
            texts = [_text(v) for v in row[:6] if _text(v) and not parse_period(v)]
            if not texts:
                continue
            lab = " | ".join(texts)[:60]
            if lab not in seen:
                seen.add(lab)
                if len(labels) < n_labels:
                    labels.append(f"r{r + 1} {lab}")
        lines += ["  " + x for x in labels]
        if len(seen) > len(labels):
            lines.append(
                f"  ({len(labels)} of {len(seen)} distinct row labels shown; menu(path, sheet={name!r}) lists more, find() searches)"
            )
        out.append("\n".join(lines)[: max(per_sheet - 5, 150)])
    return _cap(out)


def values(
    path: str, sheet: str | None = None, header: str | None = None, limit: int = 40
) -> str:
    """Distinct values under a column header on a long-layout sheet or CSV, most frequent first.

    With no header: every column with how many distinct values it holds and a few examples, which is
    enough to pick the date column, the value column, the columns that name a line and any filter
    (for example Scenario = Actual). Header names match case-insensitively; a unique partial match is enough.
    """
    mat, truncated, name = _matrix(path, sheet)
    if not mat:
        return f"{name} is empty."
    hr = max(
        range(min(len(mat), 15)),
        key=lambda r: sum(1 for v in mat[r] if _text(v)),
        default=0,
    )
    headers = [_text(v) for v in mat[hr]]
    body = mat[hr + 1 :]

    def column(i):
        counts: dict = {}
        for row in body:
            v = row[i] if i < len(row) else None
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            key = v.strip() if isinstance(v, str) else v
            counts[key] = counts.get(key, 0) + 1
        return counts

    lines = []
    if header is None:
        lines.append(
            f"Columns on {name} (header row {hr + 1}, {len(body)} data rows{', scan capped' if truncated else ''}):"
        )
        for i, h in enumerate(headers):
            if not h:
                continue
            c = column(i)
            nums = sum(1 for k in c if _is_num(k))
            dates = sum(1 for k in list(c)[:50] if parse_period(k))
            kind = (
                "numbers"
                if nums >= 0.8 * max(1, len(c))
                and dates < 0.8 * min(50, max(1, len(c)))
                else "periods"
                if dates >= 0.8 * min(50, max(1, len(c)))
                else "text"
            )
            sample = ", ".join(_show(k) for k in list(c)[:4])
            lines.append(
                f"  {_col(i)} {h[:28]:<28} {kind:<8} {len(c):>5} distinct   e.g. {sample[:70]}"
            )
        return _cap(lines)
    hits = [i for i, x in enumerate(headers) if x.lower() == str(header).lower()] or [
        i for i, x in enumerate(headers) if str(header).lower() in x.lower()
    ]
    if len(hits) != 1:
        return f"Header {header!r} matches {len(hits)} columns on {name}. Headers: {[x for x in headers if x][:40]}"
    c = column(hits[0])
    lines.append(
        f"{headers[hits[0]]} on {name}: {len(c)} distinct values in {sum(c.values())} rows{' (scan capped)' if truncated else ''}"
    )
    for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:limit]:
        lines.append(f"  {_show(k)[:40]:<40} {v} rows")
    if len(c) > limit:
        lines.append(f"  ... and {len(c) - limit} more")
    return _cap(lines)


def find(path: str, text: str, limit: int = 40) -> str:
    """Every cell whose text contains `text` (case-insensitive), with sheet, cell and row number."""
    q = text.strip().lower()
    sheets = (
        [None]
        if str(path).lower().endswith((".csv", ".txt"))
        else [ws.title for ws in _book(path).worksheets]
    )
    hits = []
    for s in sheets:
        mat, _, name = _matrix(path, s)
        for r, row in enumerate(mat):
            for c, v in enumerate(row):
                if isinstance(v, str) and q in v.lower():
                    hits.append(
                        f"{name}!{_col(c)}{r + 1} (row {r + 1}): {v.strip()[:110]}"
                    )
                    if len(hits) >= limit:
                        return _cap(
                            hits
                            + [f"... (stopped at {limit} matches; add words to narrow)"]
                        )
    return _cap(hits) if hits else f"No cell text contains {text!r}."


def rows(
    path: str, sheet: str | None, first: int, last: int, max_cols: int = 30
) -> str:
    """Rows first..last (1-based) as values, at most 40 rows and `max_cols` columns."""
    mat, _, name = _matrix(path, sheet, max_rows=min(int(last), ROW_CAP))
    first, last = max(1, int(first)), min(int(last), int(first) + 39, len(mat))
    out = [f"=== {name} rows {first}-{last}"]
    for r in range(first - 1, last):
        parts = [
            f"{_col(c)}={_show(v)}"
            for c, v in enumerate(mat[r][:max_cols])
            if v is not None
        ]
        if parts:
            out.append(f"  r{r + 1}: {'  '.join(parts)}")
    return _cap(out)


def _show(v) -> str:
    if isinstance(v, float):
        return repr(round(v, 4))
    if isinstance(v, (_dt.date, _dt.datetime)):
        return v.isoformat()[:10]
    return repr(v)[:60]
