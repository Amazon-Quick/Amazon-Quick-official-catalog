"""
description: Reconciliation checks: period totals, tie-outs between tabs, misaligned period links, text inside SUM ranges and header mismatches.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import bisect
import re
from collections import Counter, defaultdict

from openpyxl.utils import get_column_letter
from scan_finance_base import (
    ASSUMPTION_WORDS,
    GROWTH_WORDS,
    KIND_WORD,
    LABEL_STOP,
    NON_ADDITIVE,
    _close,
    _direct_refs,
    _find,
    _fmtn,
    _label_left,
    _norm_label,
    _numv,
    _v,
    additive_cells,
    period_key,
    period_text,
)
from scan_findings import data_text
from scan_formats import fmt_section, numeric_text, plural
from scan_formula_text import refs_in


def check_reconciliation(wb, fs, cached_ok):
    if not cached_ok:
        return
    n = 0
    for s in wb.sheets.values():
        P = s.periods
        if not P or not P["totals"] or s.is_data:
            continue
        kind_word = KIND_WORD[P["kind"]] + "s"
        for T, comps in P["totals"].items():
            hdr = P["text"].get(T) or "total"
            for r in sorted(s.rows):
                if r <= P["row"] or n >= 60:
                    continue
                t = s.cells.get((r, T))
                tv = _numv(t)
                if tv is None or "%" in fmt_section(t.fmt):
                    continue
                lab = _label_left(s, r, P["order"][0])
                if not lab or NON_ADDITIVE.search(lab) or GROWTH_WORDS.search(lab):
                    continue
                if t.formula and re.search(
                    r"\b(AVERAGE|MAX|MIN|INDEX|LOOKUP|VLOOKUP|XLOOKUP|HLOOKUP|MATCH|OFFSET|INDIRECT|MEDIAN)\s*\(",
                    t.formula,
                    re.I,
                ):
                    continue
                nums = [_numv(s.cells.get((r, c))) for c in comps]
                nums = [v for v in nums if v is not None]
                if len(nums) < 2 or len(nums) < 0.5 * len(comps):
                    continue
                across = sum(nums)
                # a total row: its period cells add up a block of lines in the same column
                down, block = None, None
                first = s.cells.get((r, comps[0]))
                if first is not None and first.formula:
                    cells = additive_cells(wb, first)
                    if (
                        cells
                        and all(sh == s.name and cc == comps[0] for sh, _, cc in cells)
                        and len(cells) >= 2
                    ):
                        rows_in = sorted(rr for _, rr, _ in cells if rr != r)
                        vals = [_numv(s.cells.get((rr, T))) for rr in rows_in]
                        if all(v is not None for v in vals) and not any(
                            _find(
                                fs,
                                "period_total_mismatch",
                                s.name,
                                f"{get_column_letter(T)}{rr}",
                            )
                            for rr in rows_in
                        ):
                            down, block = sum(vals), (rows_in[0], rows_in[-1])
                        elif any(
                            _find(
                                fs,
                                "period_total_mismatch",
                                s.name,
                                f"{get_column_letter(T)}{rr}",
                            )
                            for rr in rows_in
                        ):
                            continue  # follows from a line already flagged above
                ok_across = _close(tv, across, t.fmt)
                ok_down = down is None or _close(tv, down, t.fmt)
                if ok_across and ok_down:
                    continue
                if (
                    not ok_across
                    and down is None
                    and any(
                        _close(tv, k, t.fmt)
                        for k in (
                            nums[-1],
                            nums[0],
                            max(nums),
                            min(nums),
                            across / len(nums),
                        )
                    )
                ):
                    continue  # an average / ending value, not a sum
                if _find(fs, "sum_range_gap", s.name, t.coord):
                    continue
                if down is not None:
                    fs.add(
                        "crossfoot_mismatch",
                        s.name,
                        t.coord,
                        f"Totals don't cross-foot: across, the {kind_word} of {data_text(lab)} add to {_fmtn(across)}; down the {data_text(hdr)} column, "
                        f"rows {block[0]}-{block[1]} add to {_fmtn(down)}; the cell shows {_fmtn(tv)}.",
                    )
                elif t.formula:
                    fs.add(
                        "period_total_mismatch",
                        s.name,
                        t.coord,
                        f"The {data_text(hdr)} total for {data_text(lab)} shows {_fmtn(tv)}, but its {kind_word} add up to {_fmtn(across)} "
                        f"(off by {_fmtn(abs(tv - across))}).",
                        severity="warning",
                    )
                else:
                    fs.add(
                        "period_total_mismatch",
                        s.name,
                        t.coord,
                        f"The {data_text(hdr)} total for {data_text(lab)} is typed as {_fmtn(tv)}, but its {kind_word} add up to {_fmtn(across)} "
                        f"(off by {_fmtn(abs(tv - across))}).",
                    )
                n += 1


def check_tie_outs(wb, fs, roles, cached_ok):
    """The same line item on two tabs (or twice on one) with different numbers."""
    if not cached_ok:
        return
    groups = defaultdict(list)
    seen = 0
    for s in wb.sheets.values():
        if s.is_data:
            continue
        P = s.periods
        for r, xs in s.rows.items():
            if r <= max(s.header_row, P["row"] if P else 0):
                continue
            nums = [x for x in xs if _numv(x) is not None]
            if not nums:
                continue
            for x in nums:
                if len(nums) == 1:
                    pk = ("single",)
                elif P and x.c in P["cols"]:
                    pk = ("p", P["kind"], P["cols"][x.c])
                elif P and x.c in P["totals"]:
                    pk = ("total",)
                else:
                    continue
                lab = _norm_label(_label_left(s, r, x.c))
                if len(lab) < 4 or lab in LABEL_STOP or not re.search(r"[a-z]", lab):
                    continue
                groups[(lab, pk)].append(x)
                seen += 1
                if seen > 200_000:
                    break
    found = {}
    for (lab, _pk), xs in groups.items():
        rows = {(x.sheet, x.r) for x in xs}
        if len(rows) < 2:
            continue
        refs = {}
        for x in xs:
            if x.formula:
                refs[(x.sheet, x.r, x.c)] = set(_direct_refs(wb, x, 50))

        def linked(a, b, refs=refs):
            ra, rb = (
                refs.get((a.sheet, a.r, a.c), ()),
                refs.get((b.sheet, b.r, b.c), ()),
            )
            return any(t[0] == b.sheet and t[1] == b.r for t in ra) or any(
                t[0] == a.sheet and t[1] == a.r for t in rb
            )

        typed_inputs = [
            x for x in xs if not x.formula and roles.get(x.sheet) == "inputs"
        ]
        ref = (
            typed_inputs[0]
            if typed_inputs
            else next((x for x in xs if x.formula), xs[0])
        )
        for x in xs:
            if x is ref or (x.sheet, x.r) == (ref.sheet, ref.r) or linked(x, ref):
                continue
            a, b = float(_numv(x)), float(_numv(ref))
            if _close(a, b, x.fmt) or (
                b
                and a
                and round(abs(a / b), 6) in (1000.0, 0.001, 1e6, 1e-6, 100.0, 0.01)
            ):
                continue
            if not x.formula and not ref.formula:
                if x.sheet == ref.sheet and roles.get(x.sheet) != "inputs":
                    continue
                if not (
                    roles.get(x.sheet) == "inputs"
                    or roles.get(ref.sheet) == "inputs"
                    or ASSUMPTION_WORDS.search(lab)
                ):
                    continue
                check = "inconsistent_assumption"
            elif not x.formula or not ref.formula:
                if x.formula:  # flag the typed one
                    x, ref = ref, x
                    a, b = b, a
                check = "tie_out_mismatch"
            else:
                if x.sheet == ref.sheet:
                    continue
                check = "same_metric_differs"
            key = (check, x.sheet, x.r, ref.sheet)
            if key in found:
                found[key]["cols"].append(x.c)
                continue
            found[key] = {
                "x": x,
                "ref": ref,
                "a": a,
                "b": b,
                "cols": [x.c],
                "label": _label_left(wb.sheets[x.sheet], x.r, x.c),
            }
    n_j = 0
    for (check, sh, r, _rsh), g in sorted(
        found.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])
    ):
        x, ref = g["x"], g["ref"]
        c1, c2 = min(g["cols"]), max(g["cols"])
        cell = f"{get_column_letter(c1)}{r}" + (
            f":{get_column_letter(c2)}{r}" if c2 > c1 else ""
        )
        where_ref = f"{ref.sheet}!{ref.coord}"
        more = (
            f" ({plural(len(g['cols']), 'period')} differ)"
            if len(g["cols"]) > 1
            else ""
        )
        if check == "inconsistent_assumption":
            fs.add(
                check,
                sh,
                cell,
                f"{data_text(g['label'])} is {_fmtn(g['a'], x.fmt)} here but {_fmtn(g['b'], ref.fmt)} on {data_text(where_ref)}{more}. "
                "Two values for one assumption usually means one copy wasn't updated.",
            )
        elif check == "tie_out_mismatch":
            fs.add(
                check,
                sh,
                cell,
                f"Typed as {_fmtn(g['a'], x.fmt)} here, but {data_text(where_ref)} calculates {data_text(g['label'])} as "
                f"{_fmtn(g['b'], ref.fmt)}{more}. A typed copy won't follow the model when it changes.",
            )
        elif n_j < 10:
            n_j += 1
            fs.add(
                check,
                sh,
                cell,
                f"{data_text(g['label'])} is {_fmtn(g['a'], x.fmt)} here and {_fmtn(g['b'], ref.fmt)} on {data_text(where_ref)}{more}; "
                "both are calculated.",
                question="Are these meant to be the same number? If they're different measures, give them different labels.",
            )


def check_period_alignment(wb, fs):
    """A row that pulls each period from another tab, but from the wrong column."""
    for s in wb.sheets.values():
        P = s.periods
        if not P or s.is_data:
            continue
        for r in sorted(s.rows):
            if r <= P["row"]:
                continue
            lab = _label_left(s, r, P["order"][0])
            if re.search(
                r"prior|previous|opening|beginning|\blag\b|last|\bpy\b|\bly\b|shift|offset|lead",
                lab,
                re.I,
            ):
                continue
            pairs = []
            for c in P["order"]:
                x = s.cells.get((r, c))
                if x is None or not x.formula:
                    continue
                cross = [
                    (sh, box)
                    for sh, box, *_ in refs_in(x.formula)
                    if sh
                    and wb.resolve(sh)
                    and wb.resolve(sh) != s.name
                    and box[0] == box[2]
                    and box[1] == box[3]
                ]
                if len(cross) != 1:
                    continue
                tgt = wb.sheets[wb.resolve(cross[0][0])]
                TP = tgt.periods
                if (
                    not TP
                    or TP["kind"] != P["kind"]
                    or cross[0][1][0] not in TP["cols"]
                ):
                    continue
                pairs.append(
                    (c, P["cols"][c], TP["cols"][cross[0][1][0]], tgt.name, cross[0][1])
                )
            if len(pairs) < 2:
                continue
            offs = Counter(p[2] - p[1] for p in pairs)
            off, cnt = offs.most_common(1)[0]
            if off == 0 or cnt < 0.6 * len(pairs):
                continue
            c, own, src, tname, box = next(p for p in pairs if p[2] - p[1] == off)
            k = P["kind"]
            cells = [p[0] for p in pairs if p[2] - p[1] == off]
            rng = (
                f"{get_column_letter(min(cells))}{r}:{get_column_letter(max(cells))}{r}"
            )
            fs.add(
                "period_misaligned_link",
                s.name,
                rng,
                f"{data_text(lab) if lab else 'This row'} pulls the wrong period from {data_text(tname)}: the {period_text(k, own)} column reads "
                f"{data_text(tname)}'s {period_text(k, src)} ({get_column_letter(box[0])}{box[1]}), and the rest of the row is shifted the same way.",
            )


SUM_FUNC_RE = re.compile(
    r"\b(SUM|SUMIFS?|SUMPRODUCT|SUBTOTAL|AGGREGATE|AVERAGE|AVERAGEIFS?)\s*\(", re.I
)


def check_text_in_sums(wb, fs):
    """Numbers typed as text inside a range a SUM-style function reads. SUM skips text, so the total is short.
    Reads typed values, so it works whether or not the file was calculated."""
    text_numbers = {}
    for s in wb.sheets.values():
        columns = defaultdict(list)
        for (r, c), y in s.cells.items():
            if not y.formula and isinstance(y.raw, str) and numeric_text(y.raw):
                columns[c].append((r, y))
        text_numbers[s.name] = {
            c: sorted(entries, key=lambda entry: entry[0])
            for c, entries in columns.items()
        }
    for s in wb.sheets.values():
        if s.hidden:
            continue
        hits = {}
        for x in s.cells.values():
            if not x.formula or not SUM_FUNC_RE.search(x.formula):
                continue
            for sh, box, *_ in refs_in(x.formula):
                tgt = wb.sheets.get(wb.resolve(sh)) if sh else s
                if tgt is None:
                    continue
                c1, r1, c2, r2 = box
                if (r2 - r1 + 1) * (c2 - c1 + 1) > 20000:
                    continue
                bad = []
                for c, entries in text_numbers[tgt.name].items():
                    if c1 <= c <= c2:
                        start = bisect.bisect_left(entries, r1, key=lambda e: e[0])
                        end = bisect.bisect_right(entries, r2, key=lambda e: e[0])
                        bad.extend(y for _, y in entries[start:end])
                bad.sort(key=lambda y: (y.r, y.c))
                if bad:
                    key = (x.sheet, x.coord)
                    hits.setdefault(key, (x, tgt, []))[2].extend(bad)
        for (_sh, coord), (x, tgt, bad) in hits.items():
            seen, missing = set(), 0.0
            for y in bad:
                if (y.r, y.c) in seen:
                    continue
                seen.add((y.r, y.c))
                core = re.sub(r"[^\d.]", "", y.raw)
                try:
                    v = float(core)
                except ValueError:
                    continue
                neg = y.raw.strip().startswith(("-", "("))
                missing += -v if neg else v
            cells = sorted(seen)
            where = ", ".join(f"{get_column_letter(c)}{r}" for r, c in cells[:6]) + (
                " ..." if len(cells) > 6 else ""
            )
            lab = _label_left(s, x.r, x.c) or "This total"
            on = "" if tgt is s else f" on {data_text(tgt.name)}"
            fs.add(
                "text_in_sum_range",
                s.name,
                coord,
                f"{data_text(lab)} ({coord}) skips {plural(len(cells), 'number')} stored as text{on} ({where}); "
                f"the total is short by about {missing:,.0f}.",
            )
            fs.items[-1]["_cells"] = {(r, c) for r, c in cells} if tgt is s else set()
            fs.items[-1]["text_cells"] = [
                {"sheet": tgt.name, "cell": f"{get_column_letter(c)}{r}"}
                for r, c in cells
            ]


def check_header_formulas(wb, fs):
    """A period header that disagrees with the period its own column's formulas read from another tab."""
    for s in wb.sheets.values():
        P = s.periods
        if not P or s.is_data:
            continue
        for c in P["order"]:
            own = P["cols"][c]
            reads = Counter()
            example = None
            for r in sorted(s.rows):
                if r <= P["row"]:
                    continue
                x = s.cells.get((r, c))
                if x is None or not x.formula:
                    continue
                for sh, box, *_ in refs_in(x.formula):
                    if box[0] != box[2] or box[1] != box[3]:
                        continue
                    tgt = wb.sheets.get(wb.resolve(sh)) if sh else s
                    if tgt is None or tgt is s and box[0] == c:
                        continue
                    k = None
                    TP = tgt.periods
                    if TP and TP["kind"] == P["kind"] and box[0] in TP["cols"]:
                        k = TP["cols"][box[0]]  # the source column's period header
                    else:
                        lab = tgt.cells.get(
                            (box[1], 1)
                        )  # a long layout: the period sits in the row label
                        pk = period_key(_v(lab)) if lab is not None else None
                        if pk and pk[0] == P["kind"]:
                            k = pk[1]
                    if k is not None:
                        reads[k] += 1
                        example = example or (x, tgt, box, k)
            if not reads:
                continue
            k, n = reads.most_common(1)[0]
            if k == own or n < 2 or n < 0.6 * sum(reads.values()):
                continue
            x, tgt, box, _ = (
                example if example[3] == k else next(e for e in [example] if e)
            )
            hdr = f"{get_column_letter(c)}{P['row']}"
            fs.add(
                "header_formula_mismatch",
                s.name,
                hdr,
                f"Header {data_text(hdr)} says {period_text(P['kind'], own)}, but {plural(n, 'formula')} below it read "
                f"{period_text(P['kind'], k)} from {data_text(tgt.name)} (for example {x.coord} = {data_text(x.formula, 60)}). "
                "Either the header or the formulas are wrong.",
            )
