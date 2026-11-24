"""
description: Data integrity and model structure checks: period header gaps, currencies, duplicates, outliers, tab names and where inputs live.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re
from collections import Counter

from openpyxl.utils import get_column_letter
from scan_finance_base import (
    DEFAULT_TAB_RE,
    KEY_HEADER,
    NOT_MEASURE,
    _cells_in,
    _fmtn,
    _label_left,
    _median,
    _numv,
    _v,
    cell_currency,
    period_text,
)
from scan_findings import data_text
from scan_formats import is_num, plural
from scan_formula_text import refs_in


def check_data_integrity(wb, fs, cached_ok):
    for s in wb.sheets.values():
        if not s.rows:
            continue
        # period headers that skip, repeat or go backwards
        P = s.periods
        if P and len(P["order"]) >= 3:
            k = P["kind"]
            seq = [(c, P["cols"][c]) for c in P["order"]]
            for (c0, o0), (c1, o1) in zip(seq, seq[1:], strict=False):
                step = (
                    (o1 - o0) % (12 if k == "mo" else 4)
                    if k in ("mo", "qo")
                    else o1 - o0
                )
                if step == 1:
                    continue
                a, b = period_text(k, o0), period_text(k, o1)
                if step == 0:
                    text = f"{b} appears twice in the period headers ({get_column_letter(c0)}{P['row']} and {get_column_letter(c1)}{P['row']})."
                elif step < 0:
                    text = f"Period headers go backwards, from {a} to {b}."
                else:
                    missing = [period_text(k, o0 + i) for i in range(1, min(step, 4))]
                    text = f"Period headers jump from {a} to {b} ({', '.join(missing)}{' ...' if step > 4 else ''} missing)."
                fs.add(
                    "period_header_gap",
                    s.name,
                    f"{get_column_letter(c1)}{P['row']}",
                    text,
                )
                break
        # mixed currencies on one tab
        cur = Counter()
        first = {}
        for x in s.cells.values():
            if _numv(x) is None or x.r <= s.header_row:
                continue
            cc = cell_currency(wb, s.name, x.r, x.c)
            if cc:
                cur[cc] += 1
                first.setdefault(cc, x.coord)
        if len(cur) >= 2:
            (c_a, n_a), (c_b, n_b) = cur.most_common(2)
            if n_b >= 3:
                fs.add(
                    "mixed_currency",
                    s.name,
                    first[c_b],
                    f"Two currencies on this tab: {plural(n_a, 'cell')} in {c_a} and {n_b} in {c_b} (for example {first[c_b]}). "
                    "Check they're converted before they're added together.",
                )
        if not s.is_data:
            continue
        rows = {r: xs for r, xs in s.rows.items() if r > s.header_row}
        # exact duplicate records
        seen, dups = {}, []
        for r in sorted(rows):
            vals = tuple(
                sorted(
                    (x.c, str(_v(x)).strip())
                    for x in rows[r]
                    if _v(x) not in (None, "")
                )
            )
            if len(vals) < 3:
                continue
            if vals in seen:
                dups.append((r, seen[vals]))
            else:
                seen[vals] = r
        maxc = max(x.c for x in s.cells.values())
        if dups:
            r, r0 = dups[0]
            fs.add(
                "duplicate_rows",
                s.name,
                f"A{r}:{get_column_letter(maxc)}{r}",
                f"{plural(len(dups), 'row')} {'is an exact copy' if len(dups) == 1 else 'are exact copies'} of another row "
                f"(for example, row {r} repeats row {r0}).",
            )
        # duplicate IDs in the first column
        c0 = min(x.c for x in s.cells.values())
        head = s.cells.get((s.header_row, c0))
        keys = [
            (r, _v(s.cells.get((r, c0))))
            for r in sorted(rows)
            if s.cells.get((r, c0)) is not None
        ]
        keys = [(r, k) for r, k in keys if k not in (None, "")]
        dup_rows = {r for r, _ in dups}
        if len(keys) >= 10:
            cnt = Counter(str(k).strip() for _, k in keys)
            looks_id = (
                head is not None and KEY_HEADER.search(str(_v(head) or ""))
            ) or sum(
                1 for _, k in keys if isinstance(k, str) and re.search(r"\d", k)
            ) >= 0.8 * len(keys)
            if looks_id and len(cnt) >= 0.9 * len(keys):
                rep = [
                    (k, [r for r, kk in keys if str(kk).strip() == k])
                    for k, n in cnt.items()
                    if n > 1
                ]
                rep = [(k, rs) for k, rs in rep if not set(rs[1:]) <= dup_rows]
                if rep:
                    k, rs = rep[0]
                    fname = (
                        str(_v(head)) if head is not None and _v(head) else "The key"
                    )
                    fs.add(
                        "duplicate_key",
                        s.name,
                        f"{get_column_letter(c0)}{rs[1]}",
                        f"{data_text(fname)} {data_text(k)} appears {len(rs)} times (rows {', '.join(map(str, rs[:4]))})"
                        + (
                            f"; {plural(len(rep) - 1, 'other ID')} repeat too"
                            if len(rep) > 1
                            else ""
                        )
                        + ". The rest of the column is unique, so these are probably double entries.",
                    )
        if not cached_ok:
            continue
        # values far outside the column's normal range
        n_out = 0
        for c in sorted({x.c for x in s.cells.values()}):
            h = s.cells.get((s.header_row, c))
            hname = (
                str(_v(h)).strip()
                if h is not None and _v(h) is not None
                else get_column_letter(c)
            )
            if NOT_MEASURE.search(hname):
                continue
            col = [
                (r, _numv(s.cells.get((r, c))))
                for r in rows
                if s.cells.get((r, c)) is not None
            ]
            col = [(r, v) for r, v in col if v is not None]
            if len(col) < 20:
                continue
            vals = [v for _, v in col]
            med = _median(vals)
            mad = _median([abs(v - med) for v in vals])
            if mad <= 0:
                continue
            hits = sorted(
                ((abs(v - med) / (1.4826 * mad), r, v) for r, v in col), reverse=True
            )
            for z, r, v in hits[:2]:
                if z < 8 or n_out >= 15:
                    break
                kcell = s.cells.get((r, c0))
                kname = (
                    f" ({data_text(_v(kcell))})"
                    if kcell is not None and c != c0 and _v(kcell) not in (None, "")
                    else ""
                )
                fs.add(
                    "outlier_value",
                    s.name,
                    f"{get_column_letter(c)}{r}",
                    f"{data_text(hname)} in row {r}{kname} is {_fmtn(v)}; the column's typical value is about {_fmtn(med)}.",
                    question="Is this value right, or a typo or unit slip?",
                )
                n_out += 1


def check_structure(wb, fs, roles):
    visible = [s for s in wb.sheets.values() if not s.hidden]
    # tab names
    for s in wb.sheets.values():
        if DEFAULT_TAB_RE.search(s.name.strip()):
            fs.add(
                "default_sheet_name",
                s.name,
                None,
                f"The tab name {data_text(s.name)} looks like a default or working name.",
            )
    referenced = Counter()
    for x in wb.formulas:
        for sh, box, *_ in refs_in(x.formula):
            tgt = wb.resolve(sh) if sh else x.sheet
            cells = _cells_in(wb, tgt, box, 400) if tgt else None
            for t in cells or ():
                referenced[t] += 1
    has_inputs = [s for s in visible if roles.get(s.name) == "inputs"]
    pasted = {
        (i["sheet"], i.get("cell"))
        for i in fs.items
        if i["check"] == "value_in_formula_row"
    }
    spread = Counter()
    for s in wb.sheets.values():
        if s.is_data or roles.get(s.name) not in ("calculation", "output"):
            continue
        P = s.periods
        typed = [
            x
            for x in s.cells.values()
            if not x.formula
            and is_num(x.raw)
            and x.r > max(s.header_row, P["row"] if P else 0)
            and referenced.get((s.name, x.r, x.c))
            and (s.name, x.coord) not in pasted
            and x.raw not in (0, 1)
        ]
        spread[s.name] = len(typed)
        if has_inputs and len(typed) >= 3:
            ex = sorted(typed, key=lambda y: (y.r, y.c))[0]
            rws = sorted({y.r for y in typed})
            labs = [
                litem
                for litem in (
                    _label_left(s, rr, ex.c + 1) or _label_left(s, rr, 99) for rr in rws
                )
                if litem
            ]
            what = (
                f"in {plural(len(rws), 'row')} ({', '.join(data_text(lab) for lab in labs[:4])}{', ...' if len(labs) > 4 else ''})"
                if labs
                else f"(for example {ex.coord})"
            )
            fs.add(
                "inputs_outside_inputs_tab",
                s.name,
                ex.coord,
                f"{plural(len(typed), 'typed number')} that formulas depend on {'sits' if len(typed) == 1 else 'sit'} on this "
                f"{roles.get(s.name)} tab {what} rather than on {data_text(has_inputs[0].name)}.",
            )
    if (
        not has_inputs
        and sum(1 for n in spread.values() if n) >= 2
        and sum(spread.values()) >= 5
    ):
        fs.add(
            "no_inputs_tab",
            None,
            None,
            f"Assumptions are typed into {plural(sum(1 for n in spread.values() if n), 'tab')} "
            "and there's no dedicated inputs tab, so it's hard to see what drives the model.",
        )
