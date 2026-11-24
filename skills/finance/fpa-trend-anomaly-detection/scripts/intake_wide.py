"""
description: Read a wide sheet (periods across columns) into series, or return the questions that block it.
last_updated: 2026-11-24
"""

from __future__ import annotations

import datetime as _dt
import re

import numpy as np
from intake_bands import _find_band, _row_band, _scenario_columns
from intake_blocked import _blocked, _date_question
from intake_cells import (
    _RATIO_WORDS,
    _TOTAL_WORDS,
    ERRORS,
    NOTE_MIN_CHARS,
    ROW_CAP,
    _coerce,
    _col,
    _is_missing,
    _is_num,
    _matrix,
    _text,
    _untrusted,
)
from intake_periods import (
    _as_date,
    _cells_as_periods,
    _freq,
    _last_full_period,
    parse_period,
)


def extract(
    path: str,
    sheet: str | None = None,
    rows: list | None = None,
    labels: list | None = None,
    last_actual=None,
    include_totals: bool = False,
    today: _dt.date | None = None,
    period_row: int | None = None,
    date_order=None,
) -> dict:
    """Read lines from a wide-layout sheet (one line per row, periods across columns).

    rows         1-based row numbers to take, exactly as given; or
    labels       text to look for in the row labels (every row containing any of them); or
                 neither: every numeric row under the period header.
    last_actual  the last period that is an actual ('2026-07', 'Jul-26' or a date). Later columns are
                 plan and are not read. If omitted: a row of Actual/Plan markers by the header decides;
                 failing that, everything up to the last period that had fully ended before today.
    Rows that are totals of other rows are left out unless asked for by row number or include_totals=True.
    """
    mat, truncated, name = _matrix(path, sheet)
    band = None
    if period_row:
        band = _row_band(mat, period_row - 1, date_order)
        if band and band.get("no_actuals"):
            raise ValueError(
                f"Row {period_row} of {name!r} has period columns, but all are marked {' / '.join(band['no_actuals'][:4])} and none Actuals."
            )
        if band:
            band["freq"] = _freq(band["dates"])
    band = band or _find_band(mat, date_order=date_order)
    if not band or band["orientation"] != "columns":
        why = _scenario_columns(mat)
        return _blocked(
            name,
            [
                "Which row contains the period headings on {!r}{}? "
                "If periods run down a column, use extract_long instead.".format(
                    name, (" (" + why + ")") if why else ""
                )
            ],
        )
    pos, dates, freq = band["positions"], band["dates"], band["freq"]
    issues, skipped = [], []

    #      ended before today (a future month cannot be an actual, whatever the column is labeled)
    if band.get("tagged"):
        issues.append(
            "Read only the columns the sheet marks as Actuals%s."
            % (
                " (it also holds: {})".format(", ".join(band["other_scenarios"][:4]))
                if band.get("other_scenarios")
                else ""
            )
        )
    if band.get("repeats"):
        return _blocked(
            name,
            [
                f"Row {band['index'] + 1} repeats the same periods without scenario labels. Which columns are actuals? I have not selected the first copy or combined them."
            ],
            header_row=band["index"] + 1,
        )
    header = mat[band["index"]]
    ambiguous = [
        (_col(c), v)
        for c, v in enumerate(header)
        if isinstance(v, str)
        and re.fullmatch(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", v.strip())
        and parse_period(v, date_order) is None
    ]
    if ambiguous:
        return _blocked(
            name,
            [_date_question(v, f"{name}!{c}{band['index'] + 1}") for c, v in ambiguous],
            header_row=band["index"] + 1,
        )
    recognized = _cells_as_periods(list(enumerate(header)), date_order)
    if recognized:
        first, last = min(c for c, _ in recognized), max(c for c, _ in recognized)
        unknown = [
            (c, header[c])
            for c in range(first, last + 1)
            if parse_period(header[c], date_order) is None
            and any(
                c < len(row) and _is_num(row[c]) for row in mat[band["index"] + 1 :]
            )
        ]
        if unknown:
            return _blocked(
                name,
                [
                    f"{name}!{_col(c)}{band['index'] + 1} has period heading "
                    f"{_untrusted(v)} above numeric values. What period is this, "
                    "or is the column a subtotal to exclude?"
                    for c, v in unknown
                ],
                header_row=band["index"] + 1,
            )
    cut_at = len(dates) - 1
    la = _as_date(last_actual)
    if la is not None:
        cut_at = max((i for i, d in enumerate(dates) if d <= la), default=-1)
        why = f"you said the last actual is {la.isoformat()[:7]}"
    else:
        full = _last_full_period(dates, freq, today or _dt.date.today())
        why = "later periods had not finished by today, so they cannot be actuals"
        cut_at = min(cut_at, full)
    if cut_at < 0:
        raise ValueError(
            f"No actual periods on {name!r}: every period is after the cut-off."
        )
    if cut_at < len(dates) - 1:
        n_later = len(dates) - 1 - cut_at
        issues.append(
            f"History stops at {dates[cut_at].isoformat()[:7]} ({why}); {n_later} later column{'s' if n_later != 1 else ''} not read. Confirm that is the last closed period."
        )
    pos, dates = pos[: cut_at + 1], dates[: cut_at + 1]

    first_col = min(pos)
    cand = {}
    for r in range(band["index"] + 1, len(mat)):
        row = mat[r]
        vals, errs = [], 0
        for c in pos:
            v = row[c] if c < len(row) else None
            if isinstance(v, str) and v.strip() in ERRORS:
                errs += 1
                v = None
            elif isinstance(v, str):
                v = _coerce(v)
            vals.append(float(v) if _is_num(v) else np.nan)
        if not np.isfinite(vals).sum():
            continue
        parts = [_text(v) for v in row[:first_col]]
        label = " | ".join(t for t in parts if t)
        cand[r] = {
            "label": label or f"row {r + 1}",
            "parts": parts,
            "values": np.array(vals),
            "errors": errs,
        }

    explicit = bool(rows)
    if rows:
        want = [int(x) - 1 for x in rows]
        missing = [x + 1 for x in want if x not in cand]
        if missing:
            return _blocked(
                name,
                [
                    "No readable numbers in the period columns on selected row{} {}. "
                    "Which values should be analyzed?".format(
                        "s" if len(missing) > 1 else "", ", ".join(map(str, missing))
                    )
                ],
                header_row=band["index"] + 1,
            )
        chosen = [x for x in want if x in cand]
    elif labels:
        ql = [q.lower() for q in labels]
        chosen = [
            r for r, c in cand.items() if any(q in c["label"].lower() for q in ql)
        ]
        if not chosen:
            raise ValueError(
                f"No row label on {name!r} contains {labels}. Use find() to see the exact labels."
            )
    else:
        chosen = list(cand)
    value_questions, value_audit = [], {}
    for r in chosen:
        for c in pos:
            v = mat[r][c] if c < len(mat[r]) else None
            if isinstance(v, str) and not _is_missing(v) and not _is_num(_coerce(v)):
                entry = value_audit.setdefault(
                    r,
                    {
                        "row": r + 1,
                        "source": f"{name}!{r + 1}",
                        "status": "unresolved",
                        "reason": "nonnumeric history value",
                        "values": {},
                        "unresolved_cells": 0,
                    },
                )
                entry["unresolved_cells"] += 1
                if len(entry["values"]) < 10:
                    entry["values"][f"{_col(c)}{r + 1}"] = _untrusted(v)
                value_questions.append(
                    f"{name}!{_col(c)}{r + 1} contains {_untrusted(v)} in the history. "
                    "What value belongs here, or should this cell be treated as "
                    "explicitly missing? I have not analyzed it as a missing period."
                )
    if value_questions:
        return _blocked(
            name,
            value_questions,
            row_audit=list(value_audit.values()),
            header_row=band["index"] + 1,
        )

    #      row; only the label columns that differ between the chosen rows tell the lines apart
    #      (and of those, only as many as it takes to make every name different).
    width = max((len(cand[r]["parts"]) for r in chosen), default=0)

    def part(r, k):
        return cand[r]["parts"][k] if k < len(cand[r]["parts"]) else ""

    varying = [k for k in range(width) if len({part(r, k) for r in chosen}) > 1]
    use = varying[:1]
    while len({tuple(part(r, k) for k in use) for r in chosen}) < len(chosen) and len(
        use
    ) < len(varying):
        rest = [k for k in varying if k not in use]
        use.append(
            max(
                rest,
                key=lambda k: len(
                    {tuple(part(r, j) for j in use + [k]) for r in chosen}
                ),
            )
        )
    use.sort()
    for r in chosen:
        keep = [part(r, k)[:48] for k in use if part(r, k)] or [
            t for t in cand[r]["parts"] if t
        ][:1]
        cand[r]["name"] = " | ".join(keep) or cand[r]["label"]

    # Totals: by the line's own name, or because the row equals the sum of the rows directly above it.
    #      A word like "Total" that appears on most rows is a dimension member, not a totals row.
    totals = set()
    by_word = [r for r in chosen if _TOTAL_WORDS.search(cand[r]["name"])]
    if len(by_word) <= 0.4 * len(chosen) or len(chosen) < 3:
        totals.update(by_word)
    order = sorted(chosen)
    for i, r in enumerate(order):
        if r in totals or i < 2:
            continue
        v = cand[r]["values"]
        for k in range(2, min(i, 12) + 1):
            parts = [cand[x]["values"] for x in order[i - k : i] if x not in totals]
            if len(parts) < 2:
                continue
            s = np.nansum(parts, axis=0)
            ok = np.isfinite(v) & (np.abs(s) > 0)
            if ok.sum() >= 3 and np.allclose(v[ok], s[ok], rtol=0.005):
                totals.add(r)
                break
    series, prov = {}, {}
    for r in order:
        c = cand[r]
        nm = c["name"]
        if r in totals and not (explicit or include_totals):
            skipped.append(f"{nm} (row {r + 1}): a total of other rows")
            continue
        k = 2
        while nm in series:
            nm = f"{c['name']} ({k})"
            k += 1
        v = c["values"].copy()
        nz = np.where(np.isfinite(v) & (v != 0))[0]
        if (
            len(nz) >= 6
            and nz[-1] < len(v) - 1
            and np.all(np.nan_to_num(v[nz[-1] + 1 :]) == 0)
            and np.isfinite(v[nz[-1] + 1 :]).any()
        ):
            issues.append(
                f"{nm}: zero from {dates[nz[-1] + 1].isoformat()[:7]} on. Kept as recorded; confirm whether these are real zeros "
                "or values not yet posted before interpreting the change."
            )
        last = np.where(np.isfinite(v))[0]
        if len(last) and last[-1] < len(v) - 1:
            issues.append(
                f"{nm}: blank after {dates[last[-1]].isoformat()[:7]}, so its history ends there."
            )
        first = last[0] if len(last) else 0
        end = (last[-1] + 1) if len(last) else 0
        if end - first < 8:
            skipped.append(f"{nm} (row {r + 1}): only {end - first} periods of history")
            continue
        series[nm] = {
            "dates": [d.isoformat() for d in dates[first:end]],
            "values": v[first:end].tolist(),
        }
        contiguous = all(
            b - a == 1
            for a, b in zip(pos[first:end], pos[first + 1 : end], strict=False)
        )
        prov[nm] = (
            f"{name}!{_col(pos[first])}{r + 1}:{_col(pos[end - 1])}{r + 1}"
            if contiguous
            else f"{name} row {r + 1}, {end - first} period columns between {_col(min(pos[first:end]))} and {_col(max(pos[first:end]))}"
        )
        if c["errors"]:
            issues.append(
                f"{nm}: {c['errors']} error value{'s' if c['errors'] > 1 else ''} (#REF!, #DIV/0! ...) read as missing."
            )
        if r in totals:
            issues.append(
                f"{nm} is a total of other rows; do not also include its components in a Total."
            )
        elif _RATIO_WORDS.search(c["name"]) or float(np.nanmax(np.abs(v))) <= 1.5:
            issues.append(
                f"{nm} looks like a ratio or a rate. It is averaged over a window, never totaled."
            )
    #      both are legitimate lines to analyse; the components can explain a movement in the total
    overlaps = []
    groups: dict = {}
    for nm in series:
        groups.setdefault(nm.split(" | ")[0].lower(), []).append(nm)
    for members in groups.values():
        if not 3 <= len(members) <= 9:
            continue
        arrs = {m: np.array(series[m]["values"], dtype=float) for m in members}
        n = min(len(a) for a in arrs.values())
        for m in members:
            others = [x for x in members if x != m]
            combos = [others] + [
                [a, b] for i, a in enumerate(others) for b in others[i + 1 :]
            ]
            for combo in combos:
                tot = np.nansum([arrs[x][-n:] for x in combo], axis=0)
                ok = np.isfinite(arrs[m][-n:]) & (np.abs(tot) > 0)
                if ok.sum() >= 6 and np.allclose(arrs[m][-n:][ok], tot[ok], rtol=0.002):
                    overlaps.append({"total": m, "components": combo})
                    issues.append("{} is the sum of {}.".format(m, " + ".join(combo)))
                    break
    if truncated:
        return _blocked(
            name,
            [
                f"The file exceeds the {ROW_CAP}-row scan limit. Which subset should be reviewed? The partial scan is not a complete review."
            ],
            header_row=band["index"] + 1,
        )
    notes = []
    for r, row in enumerate(mat[:400]):
        for c, v in enumerate(row[:40]):
            if (
                isinstance(v, str)
                and len(v.strip()) >= NOTE_MIN_CHARS
                and len(notes) < 8
            ):
                notes.append(f"{name}!{_col(c)}{r + 1}: {_untrusted(v.strip())}")
    return {
        "status": "ready",
        "questions": [],
        "series": series,
        "provenance": prov,
        "freq": freq,
        "sheet": name,
        "last_actual": max(v["dates"][-1] for v in series.values())
        if series
        else dates[-1].isoformat(),
        "first_period": min(v["dates"][0] for v in series.values())
        if series
        else dates[0].isoformat(),
        "skipped": skipped,
        "issues": issues,
        "notes": notes,
        "overlaps": overlaps,
    }
