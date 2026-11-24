"""
description: Read a long table or CSV (one row per period) into series, or return the questions that block it.
last_updated: 2026-11-24
"""

from __future__ import annotations

import datetime as _dt
import re

import numpy as np
from intake_blocked import _blocked, _date_question, _row_counts
from intake_cells import (
    _PLAN_WORDS,
    ROW_CAP,
    _coerce,
    _col,
    _is_missing,
    _is_num,
    _matrix,
    _text,
    _untrusted,
    _untrusted_values,
)
from intake_periods import _as_date, _freq, _last_full_period, parse_period


def extract_long(
    path: str,
    sheet: str | None = None,
    date_col: str | None = None,
    value_col: str | None = None,
    key_cols: list | None = None,
    filters: dict | None = None,
    last_actual=None,
    today: _dt.date | None = None,
    header_row: int | None = None,
    date_order=None,
    aggregate_duplicates: bool = False,
    skip_rows: list | None = None,
    unit_col: str | None = None,
) -> dict:
    """Read lines from a long-layout sheet or CSV (one row per period per entity).

    date_col     header of the period column (found automatically if omitted)
    value_col    header of the numbers, or a list of headers, one line each; omitted = every numeric column
    key_cols     headers whose values name the line, e.g. ["Marketplace", "Channel"]; none = one line per value column
    filters      {header: value or [values]} rows to keep, e.g. {"Scenario": "Actual"}
    header_row   optional 1-based header row, after the user identifies it
    date_order   'DMY' or 'MDY', only after the user resolves ambiguous numeric dates
    aggregate_duplicates  True only after the user confirms repeated rows are additive
    skip_rows    explicit 1-based rows the user approved excluding; the audit retains them
    unit_col     units/currency column; common names are detected automatically

    Returns status='needs_clarification' and an empty series when a row cannot be interpreted.
    Read questions and row_audit, get the answer, and call again. Invalid rows never become missing
    periods. A plain "date, line A, line B" CSV needs no arguments when its contents are unambiguous.
    """
    mat, truncated, name = _matrix(path, sheet)
    if not mat:
        return _blocked(
            name, ["This file has no rows. Which file contains the history?"]
        )
    wanted = [
        str(h).lower()
        for h in [
            date_col,
            *(value_col if isinstance(value_col, (list, tuple)) else [value_col]),
            *(key_cols or []),
        ]
        if h
    ]

    def header_score(r):
        texts = [_text(v).lower() for v in mat[r] if _text(v)]
        named = sum(any(h == t or h in t for t in texts) for h in wanted)
        date_named = any(
            re.search(r"\b(date|period|month|quarter)\b", t) for t in texts
        )
        # A title/footer cannot win just because it contains more words than the actual header.
        followers = mat[r + 1 : r + 8]
        data_below = sum(
            any(parse_period(v, date_order) for v in row) for row in followers
        )
        return (named, date_named, bool(data_below), len(texts))

    if header_row is not None and not 1 <= header_row <= len(mat):
        return _blocked(
            name,
            [
                f"Header row {header_row!r} is outside this file. Which row holds the column names?"
            ],
        )
    hr = (
        header_row - 1
        if header_row
        else max(range(min(len(mat), 40)), key=header_score)
    )
    headers = [_text(v) for v in mat[hr]]
    audit, questions, issues = [], [], []
    skip = set(skip_rows or [])

    def col(h):
        if h is None:
            return None
        exact = [i for i, x in enumerate(headers) if x.lower() == str(h).lower()]
        part = exact or [
            i for i, x in enumerate(headers) if str(h).lower() in x.lower()
        ]
        if len(part) != 1:
            raise ValueError(
                f"Which column means {_untrusted(h)}? It matches {len(part)} "
                f"columns on {name!r}, row {hr + 1}. Available headers: "
                f"{_untrusted_values([x for x in headers if x])}."
            )
        return part[0]

    body = mat[hr + 1 :]
    try:
        dc = col(date_col) if date_col else None
        if dc is None:
            candidates = [
                i
                for i, h in enumerate(headers)
                if re.search(r"\b(date|period|month|quarter)\b", h, re.I)
            ]
            if not candidates:
                candidates = [
                    i
                    for i in range(len(headers))
                    if sum(
                        1
                        for row in body[:30]
                        if i < len(row) and parse_period(row[i], date_order)
                    )
                    >= 5
                ]
            if len(candidates) != 1:
                raise ValueError(
                    "Which column is the period to analyze? Date candidates: "
                    f"{_untrusted_values([headers[i] for i in candidates])}. "
                    f"Headers: {_untrusted_values([h for h in headers if h])}."
                )
            dc = candidates[0]
        kc = [col(k) for k in (key_cols or [])]
        fl = {
            col(k): {
                str(x).strip().lower()
                for x in (v if isinstance(v, (list, tuple, set)) else [v])
            }
            for k, v in (filters or {}).items()
        }
        ucs = (
            [col(unit_col)]
            if unit_col
            else [
                i
                for i, h in enumerate(headers)
                if h.lower()
                in ("unit", "units", "currency", "currency code", "uom", "scale")
            ]
        )
        if value_col:
            vcs = [
                col(h)
                for h in (
                    value_col if isinstance(value_col, (list, tuple)) else [value_col]
                )
            ]
        else:
            vcs = [
                i
                for i, h in enumerate(headers)
                if h
                and i != dc
                and i not in kc
                and i not in fl
                and i not in ucs
                and sum(1 for row in body[:200] if i < len(row) and _is_num(row[i]))
                >= 0.5
                * max(1, sum(any(v is not None for v in row) for row in body[:200]))
            ]
            if not vcs:
                raise ValueError(
                    "Which column holds the values to analyze? Headers: "
                    f"{_untrusted_values([h for h in headers if h])}."
                )
            if any(_PLAN_WORDS.search(headers[i]) for i in vcs):
                raise ValueError(
                    "These value columns include plan or forecast: "
                    f"{_untrusted_values([headers[i] for i in vcs])}. Which are actuals?"
                )
    except ValueError as err:
        return _blocked(name, [str(err)], header_row=hr + 1)

    records, seen, unit_values = [], {}, {c: set() for c in ucs}
    for rowno, row in enumerate(body, hr + 2):

        def get(c, row=row):
            return row[c] if c < len(row) else None

        entry = {
            "row": rowno,
            "source": f"{name}!{rowno}",
            "status": "loaded",
            "reason": "validated data row",
        }
        audit.append(entry)
        if not any(v is not None for v in row):
            entry.update(status="excluded", reason="blank row")
            continue
        if rowno in skip:
            entry.update(status="excluded", reason="user-confirmed exclusion")
            continue
        if all(get(i) == h for i, h in enumerate(headers) if h):
            entry.update(status="excluded", reason="repeated header")
            continue
        date_value = get(dc)
        if isinstance(date_value, str) and re.fullmatch(
            r"(grand\s+)?(sub[- ]?)?total", date_value.strip(), re.I
        ):
            entry.update(status="excluded", reason="summary row")
            continue
        if (
            isinstance(date_value, str)
            and re.match(
                r"^(end of report|generated (on|at)|report generated)\b",
                date_value.strip(),
                re.I,
            )
            and not any(get(c) is not None for c in vcs)
        ):
            entry.update(status="excluded", reason="footer row")
            continue
        if any(str(get(c) or "").strip().lower() not in ok for c, ok in fl.items()):
            entry.update(status="excluded", reason="outside confirmed filter")
            continue
        d = parse_period(date_value, date_order)
        if d is None:
            entry.update(
                status="unresolved",
                reason="unreadable or ambiguous date",
                value=_untrusted(date_value),
                cell=f"{_col(dc)}{rowno}",
            )
            questions.append(_date_question(date_value, f"{name}!{_col(dc)}{rowno}"))
            continue
        values = {
            vc: _coerce(get(vc)) if isinstance(get(vc), str) else get(vc) for vc in vcs
        }
        bad = [
            vc
            for vc, value in values.items()
            if not _is_missing(value)
            and (not _is_num(value) or not np.isfinite(float(value)))
        ]
        if bad:
            entry.update(
                status="unresolved",
                reason="nonnumeric or nonfinite value",
                values={f"{_col(c)}{rowno}": _untrusted(get(c)) for c in bad[:10]},
                unresolved_cells=len(bad),
            )
            bad_desc = ", ".join(
                f"{_col(c)} ({_untrusted(headers[c])})={_untrusted(get(c))}"
                for c in bad[:10]
            )
            if len(bad) > 10:
                bad_desc += f", and {len(bad) - 10} more cells (see row_audit)"
            questions.append(
                f"{name} row {rowno} has {bad_desc}. What should these values be, or "
                f"should this specific row be excluded? I have not treated them as "
                f"zero or missing periods."
            )
            continue
        if any(get(c) in (None, "") for c in kc):
            entry.update(status="unresolved", reason="missing line identifier")
            questions.append(
                f"{name} row {rowno} is missing a line identifier. Which line does it belong to?"
            )
            continue
        ent = " | ".join(str(get(c)).strip() for c in kc)
        for c in ucs:
            unit_values[c].add(str(get(c) or "").strip())
        for vc in vcs:
            key = (
                (ent + " | " + headers[vc])
                if (ent and len(vcs) > 1)
                else (ent or headers[vc])
            )
            marker = (key, d)
            if marker in seen and not aggregate_duplicates:
                entry.update(status="unresolved", reason="duplicate line and date")
                questions.append(
                    f"{name} rows {seen[marker]} and {rowno} duplicate "
                    f"{_untrusted(key)} on {d.isoformat()}. Are these separate "
                    "amounts to add, different lines to group separately, "
                    "or a repeated export row?"
                )
            seen.setdefault(marker, rowno)
            value = np.nan if _is_missing(values[vc]) else float(values[vc])
            records.append((key, d, value, headers[vc], rowno))
    for c, units in unit_values.items():
        if len(units) > 1 or units == {""}:
            questions.append(
                f"The {_col(c)} column ({_untrusted(headers[c])}) contains units "
                f"{_untrusted_values(sorted(units))}. Which unit should be used, and how should "
                "the other rows be converted or separated? I have not combined them."
            )
    if truncated:
        questions.append(
            f"The file exceeds the {ROW_CAP}-row scan limit. Provide a smaller export or confirm a specific subset; the partial scan is not a complete review."
        )
    if questions:
        return _blocked(name, questions, audit, hr + 1, issues)
    acc: dict = {}
    for key, d, value, column, _rowno in records:
        acc.setdefault(key, {"_col": column})
        previous = acc[key].get(d, np.nan)
        acc[key][d] = (
            previous + value
            if np.isfinite(previous) and np.isfinite(value)
            else previous
            if np.isfinite(previous)
            else value
        )
    if not acc:
        return _blocked(
            name,
            ["No data rows remain. Are the selected sheet and filters correct?"],
            audit,
            hr + 1,
        )
    cols_of = {k: v.pop("_col") for k, v in acc.items()}
    all_dates = sorted({d for s in acc.values() for d in s})
    freq = _freq(all_dates)
    skipped = []
    if hr:
        issues.append(
            f"Header is row {hr + 1}; {hr} title/blank rows above it were not data."
        )
    if aggregate_duplicates:
        issues.append(
            "Repeated line/date rows were summed because the user confirmed they are additive."
        )
    la = _as_date(last_actual)
    if la is None:
        full = _last_full_period(all_dates, freq, today or _dt.date.today())
        if full < 0:
            return _blocked(
                name,
                [
                    "No complete actual period remains: every period is after "
                    "the cut-off. Which source contains completed actual history?"
                ],
                audit,
                hr + 1,
                issues,
            )
        if 0 <= full < len(all_dates) - 1:
            la = all_dates[full]
            issues.append(
                f"History stops at {la.isoformat()[:7]}: later periods had not finished by today, so they cannot be actuals. "
                "Confirm that is the last closed period."
            )
    series, prov = {}, {}
    for key, s in acc.items():
        ds = [d for d in sorted(s) if la is None or d <= la]
        if not ds:
            skipped.append(f"{key}: no periods before the confirmed cut-off")
            continue
        grid = [d for d in all_dates if ds[0] <= d <= ds[-1]]
        vals = [s.get(d, float("nan")) for d in grid]
        gaps = sum(1 for x in vals if x != x)
        if gaps:
            issues.append(
                f"{key}: {gaps} period{'s' if gaps > 1 else ''} with no row, read as missing rather than zero."
            )
        series[key] = {"dates": [d.isoformat() for d in grid], "values": vals}
        prov[key] = "{}, column {!r}{}".format(
            name,
            cols_of[key],
            (
                " where "
                + ", ".join(
                    "{} = {}".format(headers[c], "/".join(sorted(v)))
                    for c, v in fl.items()
                )
            )
            if fl
            else "",
        )
    if not series:
        return _blocked(
            name,
            ["No actual periods remain before the confirmed cut-off."],
            audit,
            hr + 1,
            issues,
        )
    if la is not None:
        excluded_late = {r for _, d, _, _, r in records if d > la}
        for entry in audit:
            if entry["row"] in excluded_late:
                entry.update(status="excluded", reason="after last actual period")
    counts = _row_counts(audit)
    issues.append(
        f"Rows below header: {counts['loaded']} loaded, {counts['excluded']} excluded, {counts['unresolved']} unresolved. row_audit gives the reason for each row that was not loaded."
    )
    return {
        "status": "ready",
        "questions": [],
        "row_audit": audit,
        "row_counts": counts,
        "header_row": hr + 1,
        "series": series,
        "provenance": prov,
        "freq": freq,
        "sheet": name,
        "last_actual": max(s["dates"][-1] for s in series.values()) if series else None,
        "first_period": min(s["dates"][0] for s in series.values()) if series else None,
        "skipped": skipped,
        "issues": issues,
        "notes": [],
        "overlaps": [],
    }
