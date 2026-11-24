"""
description: Financial logic checks: double counting, growth on the wrong base, mixed units, and owner questions about unusual values.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import bisect
import re
from collections import Counter, defaultdict

from openpyxl.utils import get_column_letter
from scan_finance_base import (
    GROWTH_WORDS,
    KEY_WORDS,
    KIND_WORD,
    MARGIN_WORDS,
    MAX_JUDGMENT,
    SIGNED_POSITIVE,
    _direct_refs,
    _fmtn,
    _grouped_add,
    _label_left,
    _median,
    _numv,
    additive_cells,
    cell_currency,
    stored_scale,
)
from scan_findings import data_text
from scan_formats import fmt_section, plural
from scan_formula_text import mask_strings, parse_box, refs_in
from scan_limits import FINANCIAL_WORK_CAP


def check_financial_logic(wb, fs, cached_ok):
    budget = {"n": 0}
    additive_cache = {}
    bounds_cache = {}
    work = 0
    capped = False

    def spend(amount):
        nonlocal work, capped
        work += amount
        if work <= FINANCIAL_WORK_CAP and not capped:
            return True
        if not capped:
            wb.notes.append(
                {
                    "note": "scan_capped",
                    "detail": "Double-counting check is incomplete: additive formula "
                    f"analysis reached its {FINANCIAL_WORK_CAP:,} work limit. "
                    "Additional double counting may remain.",
                }
            )
        capped = True
        return False

    def additive(x):
        # additive_cells reads only the formula text and its tab, so copies share one set.
        key = (x.sheet, x.formula)
        if key not in additive_cache:
            additive_cache[key] = (
                additive_cells(wb, x, spend=spend) if spend(len(x.formula)) else None
            )
        return additive_cache[key]

    def bounds(y):
        """Sheets and row/column span of the ranges y reads, cached per formula cell.
        For an additive formula this is the span of additive_cells(y), found without
        building the cell set."""
        key = (y.sheet, y.formula)
        if key not in bounds_cache:
            sheets, boxes = set(), []
            for sh, box, *_ in refs_in(y.formula):
                sheets.add(wb.resolve(sh) if sh else y.sheet)
                boxes.append(box)
            bounds_cache[key] = (
                (
                    sheets,
                    min(b[1] for b in boxes),
                    max(b[3] for b in boxes),
                    min(b[0] for b in boxes),
                    max(b[2] for b in boxes),
                )
                if boxes and None not in sheets
                else None
            )
        return bounds_cache[key]

    formula_rows = defaultdict(lambda: defaultdict(list))
    for y in wb.formulas:
        formula_rows[y.sheet][y.c].append(y.r)
    for columns in formula_rows.values():
        for rows in columns.values():
            rows.sort()

    def reads_a_formula(x):
        """True when a range x reads holds a formula cell: only then can x double count."""
        for sh, box, *_ in refs_in(x.formula):
            tgt = wb.resolve(sh) if sh else x.sheet
            for col, rows in formula_rows.get(tgt, {}).items():
                if box[0] <= col <= box[2] and bisect.bisect_left(
                    rows, box[1]
                ) < bisect.bisect_right(rows, box[3]):
                    return True
        return False

    def may_contain(outer, inner):
        """False when inner cannot be a subset of outer: a cheap test before the set one."""
        return (
            inner[0] <= outer[0]
            and outer[1] <= inner[1]
            and inner[2] <= outer[2]
            and outer[3] <= inner[3]
            and inner[4] <= outer[4]
        )

    def find_double_count(s, x, cells):
        """Description of the first subtotal x adds together with its own lines, or None."""
        outer = bounds(x)
        for sh, r, c in sorted(cells):
            if not spend(1):
                return None
            y = wb.cell(sh, r, c)
            if y is None or not y.formula or y is x:
                continue
            inner_span = bounds(y)
            if inner_span is None or not may_contain(outer, inner_span):
                continue
            inner = additive(y)
            if not inner or len(inner) < 2:
                continue
            if spend(len(inner)) and inner <= cells and (sh, r, c) not in inner:
                lab = _label_left(wb.sheets[sh], r, c) or f"{sh}!{y.coord}"
                rows_in = sorted({rr for _, rr, _ in inner})
                return (
                    f"Adds {data_text(lab)} ({y.coord if sh == s.name else data_text(sh + '!' + y.coord)}) and the lines it already sums "
                    f"({'rows ' + str(rows_in[0]) + '-' + str(rows_in[-1]) if len({cc for _, _, cc in inner}) == 1 else plural(len(inner), 'cell')}), "
                    "so those lines are counted twice."
                )
        return None

    def add_q(check, sheet, cell, text, question, weight=1.0, severity=None):
        budget.setdefault("items", []).append(
            (weight, check, sheet, cell, text, question, severity)
        )

    for s in wb.sheets.values():
        if s.is_data:
            continue
        dbl, grw, unt = [], [], []
        double_cache = {}
        # double counting: a total that adds a subtotal and the lines inside it
        for x in [y for y in s.cells.values() if y.formula]:
            if capped:
                break
            if not reads_a_formula(x):
                continue
            cells = additive(x)
            if not cells or len(cells) < 3:
                continue
            own = (x.sheet, x.r, x.c)
            # The same formula text on one tab adds the same cells, so it gets the same answer.
            search_key = (x.formula, own if own in cells else None)
            if search_key not in double_cache:
                found = find_double_count(s, x, cells)
                if capped:
                    break
                double_cache[search_key] = found
            if double_cache[search_key]:
                dbl.append((x.r, x.c, x.norm, double_cache[search_key]))
        # growth rates divided by the wrong period
        for x in [y for y in s.cells.values() if y.formula]:
            f = re.sub(r"\s+", "", mask_strings(x.formula)).replace("$", "")
            m = re.fullmatch(
                r"=\(?([A-Z]{1,3}\d+)-([A-Z]{1,3}\d+)\)?/\(?([A-Z]{1,3}\d+)\)?", f
            )
            m2 = re.fullmatch(r"=\(?([A-Z]{1,3}\d+)/([A-Z]{1,3}\d+)\)?-1", f)
            if not (m or m2):
                continue
            lab = _label_left(s, x.r, x.c)
            if not (
                GROWTH_WORDS.search(lab)
                or ("%" in fmt_section(x.fmt) and not MARGIN_WORDS.search(lab))
            ):
                continue
            Pg = s.periods

            def pos(ref):
                c, r = parse_box(ref)[0], parse_box(ref)[1]
                return r, c

            def later(a, b, Pg=Pg, lab=lab):
                """a is a later period than b: same row, both period columns (or adjacent when no headers)."""
                (ra, ca), (rb, cb) = pos(a), pos(b)
                if ra != rb or ca <= cb:
                    return False
                if Pg:
                    return ca in Pg["cols"] and cb in Pg["cols"]
                return bool(GROWTH_WORDS.search(lab))

            if m and m.group(3) == m.group(1) and later(m.group(1), m.group(2)):
                grw.append(
                    (
                        x.r,
                        x.c,
                        x.norm,
                        f"{data_text(lab) if lab else 'This rate'} divides the change by the later period ({m.group(1)}), not the earlier one "
                        f"({m.group(2)}). Growth is usually (new - old) / old.",
                    )
                )
            elif m2 and later(m2.group(2), m2.group(1)):
                grw.append(
                    (
                        x.r,
                        x.c,
                        x.norm,
                        f"{data_text(lab) if lab else 'This rate'} divides the earlier period ({m2.group(1)}) by the later one "
                        f"({m2.group(2)}), so the sign and size of the growth are inverted.",
                    )
                )
        # adding amounts in different units or currencies
        for x in [y for y in s.cells.values() if y.formula]:
            body = mask_strings(x.formula)
            if (
                "*" in body
                or "/" in body
                or re.search(r"\b(?!SUM\b)[A-Z][A-Z0-9.]*\s*\(", body)
            ):
                continue
            refs = _direct_refs(wb, x, 200)
            if not refs:
                continue
            scales = {sc: ref for ref in refs for sc in [stored_scale(wb, *ref)] if sc}
            curs = {cc: ref for ref in refs for cc in [cell_currency(wb, *ref)] if cc}
            own_sc, _own_cur = (
                stored_scale(wb, s.name, x.r, x.c),
                cell_currency(wb, s.name, x.r, x.c),
            )
            lab = _label_left(s, x.r, x.c)
            if len(scales) >= 2:
                (a, ra), (b, rb) = list(scales.items())[:2]
                unt.append(
                    (
                        x.r,
                        x.c,
                        x.norm,
                        f"{data_text(lab) if lab else 'This formula'} adds numbers stored in {a} ({data_text(ra[0])}!{get_column_letter(ra[2])}{ra[1]}) and in {b} "
                        f"({data_text(rb[0])}!{get_column_letter(rb[2])}{rb[1]}) without converting.",
                    )
                )
            elif len(curs) >= 2:
                (a, ra), (b, rb) = list(curs.items())[:2]
                unt.append(
                    (
                        x.r,
                        x.c,
                        x.norm,
                        f"{data_text(lab) if lab else 'This formula'} adds amounts in {a} ({data_text(ra[0])}!{get_column_letter(ra[2])}{ra[1]}) and {b} "
                        f"({data_text(rb[0])}!{get_column_letter(rb[2])}{rb[1]}) with no exchange rate.",
                    )
                )
            elif len(scales) == 1 and own_sc and own_sc not in scales:
                src, ref = next(iter(scales.items()))
                unt.append(
                    (
                        x.r,
                        x.c,
                        x.norm,
                        f"{data_text(lab) if lab else 'This cell'} is labeled in {own_sc} but takes a number stored in {src} from "
                        f"{data_text(ref[0])}!{get_column_letter(ref[2])}{ref[1]} without converting.",
                    )
                )
        _grouped_add(fs, "double_counting", s.name, dbl)
        _grouped_add(fs, "growth_wrong_base", s.name, grw)
        _grouped_add(fs, "mixed_units_in_formula", s.name, unt[:200])
        if not cached_ok:
            continue
        P = s.periods
        if not P:
            continue
        cols = P["order"]
        k = P["kind"]
        unit = KIND_WORD[k]
        for r in sorted(s.rows):
            if r <= P["row"]:
                continue
            lab = _label_left(s, r, cols[0])
            if not lab:
                continue
            series = [(c, s.cells.get((r, c))) for c in cols]
            vals = [(c, x, _numv(x)) for c, x in series]
            nums = [(c, x, v) for c, x, v in vals if v is not None]
            if len(nums) < 4:
                continue
            is_pct = (
                sum(1 for _, x, _ in nums if "%" in fmt_section(x.fmt)) > len(nums) / 2
            )
            weight = 2.0 if KEY_WORDS.search(lab) else 1.0
            # margins outside -100%..100%
            if MARGIN_WORDS.search(lab) and is_pct:
                bad = [(c, v) for c, _, v in nums if abs(v) > 1]
                if bad:
                    c, v = bad[0]
                    add_q(
                        "margin_out_of_range",
                        s.name,
                        f"{get_column_letter(c)}{r}",
                        f"{data_text(lab)} is {v * 100:,.0f}% in {data_text(P['text'].get(c, ''))}"
                        + (
                            f" ({plural(len(bad), 'period')} outside -100% to 100%)"
                            if len(bad) > 1
                            else ""
                        )
                        + ".",
                        "Is the denominator right? A margin outside -100% to 100% usually means the wrong base.",
                        2.0,
                        "warning",
                    )
            # isolated sign flips and negatives where they shouldn't be
            nz = [(c, v) for c, _, v in nums if v != 0]
            if len(nz) >= 5 and not is_pct and not GROWTH_WORDS.search(lab):
                pos_n = sum(1 for _, v in nz if v > 0)
                minority = [(c, v) for c, v in nz if (v > 0) != (pos_n >= len(nz) / 2)]
                if 0 < len(minority) <= 2 and len(minority) <= 0.2 * len(nz):
                    c, v = minority[0]
                    neg = v < 0
                    sev = "warning" if neg and SIGNED_POSITIVE.search(lab) else None
                    add_q(
                        "sign_flip",
                        s.name,
                        f"{get_column_letter(c)}{r}",
                        f"{data_text(lab)} is {'negative' if neg else 'positive'} in {data_text(P['text'].get(c, ''))} ({_fmtn(v)}) while the rest of the row is "
                        f"{'positive' if neg else 'negative'}.",
                        "Is the sign intended (a credit, reversal or true-up), or a sign-convention slip?",
                        weight,
                        sev,
                    )
            # an isolated zero inside a run of real values
            if len(nums) >= 5 and not is_pct:
                for i in range(1, len(vals) - 1):
                    c, x, v = vals[i]
                    pv, nv = vals[i - 1][2], vals[i + 1][2]
                    if (
                        v == 0
                        and pv
                        and nv
                        and sum(1 for _, _, w in nums if w) >= 0.8 * len(nums)
                    ):
                        add_q(
                            "unexpected_zero",
                            s.name,
                            f"{get_column_letter(c)}{r}",
                            f"{data_text(lab)} is 0 in {data_text(P['text'].get(c, ''))}, between {_fmtn(pv)} and {_fmtn(nv)}.",
                            "Is the zero real, or is a value or link missing?",
                            weight * 0.8,
                        )
                        break
            # unusual movements against the row's own history
            if GROWTH_WORDS.search(lab) or any(
                i["check"] == "period_misaligned_link"
                and i["sheet"] == s.name
                and parse_box(i["cell"])[1] <= r <= parse_box(i["cell"])[3]
                for i in fs.items
            ):
                continue
            ch = []
            for (_c0, _x0, v0), (c1, x1, v1) in zip(vals, vals[1:], strict=False):
                if v0 is None or v1 is None or c1 not in P["cols"]:
                    continue
                if is_pct:
                    ch.append((c1, x1, v1 - v0, v0, v1))
                elif v0 != 0 and (v0 > 0) == (v1 > 0):
                    ch.append((c1, x1, (v1 - v0) / abs(v0), v0, v1))
            if len(ch) < 3:
                continue
            ds = [d for _, _, d, _, _ in ch]
            med = _median(ds)
            mad = _median([abs(d - med) for d in ds])
            floor = 0.05 if is_pct else (0.10 if len(ch) >= 5 else 0.25)
            thr = max(4 * 1.4826 * mad, floor)
            mean_abs = sum(abs(v) for _, _, v in nums) / len(nums)
            cands = sorted(
                (
                    (abs(d - med), c, x, d, v0, v1)
                    for c, x, d, v0, v1 in ch
                    if abs(d - med) > thr
                    and abs(d) >= floor
                    and (is_pct or abs(v1 - v0) >= 0.01 * mean_abs)
                ),
                reverse=True,
            )
            flagged = {cc for _, cc, *_ in cands}
            for dev, c, x, d, v0, v1 in cands[:1]:
                # a one-period spike or dip shows as two opposite moves: report the point itself
                i = cols.index(c)
                prev_c = cols[i - 1] if i else None
                spike = (
                    prev_c in flagged
                    and next((dd for cc, _, dd, _, _ in ch if cc == prev_c), 0) * d < 0
                )
                if spike:
                    c, x = prev_c, s.cells.get((r, prev_c))
                    pv = vals[i - 2][2] if i >= 2 else None
                    ptxt = P["text"].get(c, "")
                    if is_pct:
                        text = f"{data_text(lab)} {'dips' if d > 0 else 'spikes'} to {_fmtn(v0, x.fmt)} in {data_text(ptxt)}, between {_fmtn(pv, x.fmt)} and {_fmtn(v1, x.fmt)}."
                    else:
                        text = f"{data_text(lab)} {'drops' if d > 0 else 'jumps'} to {_fmtn(v0)} in {data_text(ptxt)}, between {_fmtn(pv)} and {_fmtn(v1)}."
                else:
                    ptxt = P["text"].get(c, "")
                    if is_pct:
                        text = f"{data_text(lab)} moves {d * 100:+.1f} points in {data_text(ptxt)}, against a typical {med * 100:+.1f} points a {unit} in this row."
                    else:
                        text = (
                            f"{data_text(lab)} {'rises' if d > 0 else 'falls'} {abs(d):.0%} in {data_text(ptxt)} ({_fmtn(v0)} to {_fmtn(v1)}), "
                            f"against a typical {med:+.1%} a {unit} in this row."
                        )
                moved = budget.setdefault("moved", set())
                if (
                    x is not None
                    and x.formula
                    and any(
                        (t[0], t[2]) == (s.name, c)
                        and (t[0], t[1], t[2]) in moved
                        or (t[0], t[1], t[2]) in moved
                        for t in _direct_refs(wb, x, 50)
                    )
                ):
                    moved.add(
                        (s.name, r, c)
                    )  # explained by a move already flagged upstream
                    continue
                moved.add((s.name, r, c))
                nbr = [s.cells.get((r, cc)) for cc in cols if cc != c]
                norms = Counter(y.norm for y in nbr if y is not None and y.formula)
                if not x.formula:
                    text += f" The {data_text(ptxt)} value is typed in."
                elif norms and x.norm != norms.most_common(1)[0][0]:
                    text += f" Its formula differs from the {unit}s around it."
                else:
                    text += " Its formula matches its neighbors, so the move comes from what feeds it."
                add_q(
                    "unusual_movement",
                    s.name,
                    f"{get_column_letter(c)}{r}",
                    text,
                    "Is that planned? If so, note the driver, for example on the inputs tab, so readers aren't surprised.",
                    weight * (1 + min(dev / max(thr, 1e-9), 5) / 5),
                    "warning",
                )
            # year over year, on long monthly series
            if k == "m" and len(cols) >= 24 and not is_pct:
                by_o = {P["cols"][c]: (c, x, v) for c, x, v in vals if v is not None}
                yy = [
                    (
                        by_o[o][0],
                        by_o[o][1],
                        (by_o[o][2] - by_o[o - 12][2]) / abs(by_o[o - 12][2]),
                        by_o[o - 12][2],
                        by_o[o][2],
                    )
                    for o in sorted(by_o)
                    if o - 12 in by_o and by_o[o - 12][2]
                ]
                if len(yy) >= 6:
                    ds = [d for _, _, d, _, _ in yy]
                    med = _median(ds)
                    mad = _median([abs(d - med) for d in ds])
                    thr = max(4 * 1.4826 * mad, 0.15)
                    worst = max(yy, key=lambda t: abs(t[2] - med))
                    c, x, d, v0, v1 = worst
                    if abs(d - med) > thr:
                        add_q(
                            "unusual_movement",
                            s.name,
                            f"{get_column_letter(c)}{r}",
                            f"{data_text(lab)} in {data_text(P['text'].get(c, ''))} is {d:+.0%} on the same month last year ({_fmtn(v0)} to {_fmtn(v1)}), "
                            f"against a typical {med:+.0%} year over year.",
                            "Is that planned? If so, note the driver so readers aren't surprised.",
                            weight,
                            "warning",
                        )
    items = sorted(budget.get("items", []), key=lambda t: -t[0])
    per_row = Counter()
    verified = [
        (i["sheet"], parse_box(i["cell"]))
        for i in fs.items
        if i.get("basis") == "verified" and i.get("sheet") and i.get("cell")
    ]

    def explained(sheet, cell):
        c, r = parse_box(cell)[0], parse_box(cell)[1]
        return any(
            sh == sheet and b[0] <= c <= b[2] and b[1] <= r <= b[3]
            for sh, b in verified
        )

    for _weight, check, sheet, cell, text, question, sev in items:
        rk = (sheet, re.sub(r"[A-Z]+", "", cell or ""))
        if per_row[rk] >= 2 or budget["n"] >= MAX_JUDGMENT:
            continue
        if explained(
            sheet, cell
        ):  # a verified finding on the same cell already says why; the question adds the size of it
            question = "This follows from the issue flagged on the same cell; once that's fixed, does the movement still make sense?"
        per_row[rk] += 1
        budget["n"] += 1
        fs.add(check, sheet, cell, text, severity=sev, question=question)
