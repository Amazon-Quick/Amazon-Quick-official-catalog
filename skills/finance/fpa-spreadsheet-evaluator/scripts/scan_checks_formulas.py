"""
description: Formula integrity checks: errors, circular references, broken names and links, typed numbers, pattern breaks and SUM gaps.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import bisect
import re
from collections import Counter, defaultdict

from openpyxl.utils import get_column_letter
from scan_findings import Findings, add_grouped, data_text, rectangles
from scan_formats import is_num, plural
from scan_formula_text import (
    EXT_RE,
    NUM_RE,
    XL_PREFIX,
    if_depth,
    literal_numbers,
    mask_strings,
    parse_box,
    refs_in,
)
from scan_limits import (
    CIRCULAR_EDGE_CAP,
    COL_CAP,
    ERRORS,
    LONG_FORMULA_CHARS,
    MAX_IF_NESTING,
    NUMBER_HINTS,
    ROW_CAP,
    VOLATILE,
    WORKDAYS,
)
from scan_load import Workbook


def check_errors(wb: Workbook, fs: Findings, cached_ok: bool):
    errs = {}
    for s in wb.sheets.values():
        for x in s.cells.values():
            if (
                isinstance(x.cached, str)
                and x.cached.strip() in ERRORS
                and (x.formula or cached_ok or True)
            ):
                errs[(x.sheet, x.r, x.c)] = x.cached.strip()
    error_index = defaultdict(lambda: defaultdict(list))
    for order, (sheet, r, c) in enumerate(errs):
        error_index[sheet][c].append((r, order))
    minima = {}
    absent = (len(errs), 0)
    for sheet, columns in error_index.items():
        for col, rows in columns.items():
            rows.sort()
            size = len(rows)
            tree = [absent] * size + [(order, r) for r, order in rows]
            for pos in range(size - 1, 0, -1):
                tree[pos] = min(tree[2 * pos], tree[2 * pos + 1])
            minima[(sheet, col)] = tree

    def first_error(tree, lo, hi):
        """Earliest source-order error in a row interval, in logarithmic time."""
        lo, hi = lo + len(tree) // 2, hi + len(tree) // 2
        result = absent
        while lo < hi:
            if lo % 2:
                result = min(result, tree[lo])
                lo += 1
            if hi % 2:
                hi -= 1
                result = min(result, tree[hi])
            lo, hi = lo // 2, hi // 2
        return result

    ref_pts, err_pts = defaultdict(dict), defaultdict(dict)
    for x in wb.formulas:
        if "#REF!" in mask_strings(x.formula):
            ref_pts[x.sheet][(x.r, x.c)] = "ref"
    for (sheet, r, c), e in errs.items():
        if (r, c) in ref_pts[sheet]:
            continue
        x = wb.cell(sheet, r, c)
        cause = None
        if x and x.formula:
            for sh, box, *_ in refs_in(x.formula):
                tgt = wb.resolve(sh) if sh else sheet
                candidates = []
                for ec, rows in error_index.get(tgt, {}).items():
                    if not box[0] <= ec <= box[2]:
                        continue
                    lo = bisect.bisect_left(rows, (box[1], -1))
                    hi = bisect.bisect_right(rows, (box[3], len(errs)))
                    tree = minima[(tgt, ec)]
                    order, er = first_error(tree, lo, hi)
                    if (tgt, er, ec) == (sheet, r, c):
                        pos = bisect.bisect_left(rows, (r, -1))
                        order, er = min(
                            first_error(tree, lo, pos),
                            first_error(tree, pos + 1, hi),
                        )
                    if order != absent[0]:
                        candidates.append((order, er, ec))
                if candidates:
                    _order, er, ec = min(candidates)
                    cause = (
                        f"{tgt}!{get_column_letter(ec)}{er}"
                        if tgt != sheet
                        else f"{get_column_letter(ec)}{er}"
                    )
                if cause:
                    break
        err_pts[sheet][(r, c)] = (e, cause)
    for sheet, pts in ref_pts.items():
        add_grouped(
            fs,
            "ref_in_formula",
            sheet,
            pts,
            lambda k, rng: (
                "Formula points at a cell, row, column or tab that was deleted (#REF!)."
            ),
        )
    for sheet, pts in err_pts.items():
        add_grouped(
            fs,
            "error_value",
            sheet,
            pts,
            lambda k, rng: (
                f"Shows {k[0]}"
                + (
                    f" because of the error in {data_text(k[1])}. Fix that first."
                    if k[1]
                    else "."
                )
            ),
        )


def check_circular(wb: Workbook, fs: Findings):
    fidx = defaultdict(lambda: defaultdict(list))
    for x in wb.formulas:
        fidx[x.sheet][x.c].append(x.r)
    for s in fidx.values():
        for rows in s.values():
            rows.sort()
    n_real = len(wb.formulas)
    node = {(x.sheet, x.r, x.c): i for i, x in enumerate(wb.formulas)}
    edges = [[] for _ in wb.formulas]
    # A range reference points at a few segment-tree nodes per column instead of at
    # every formula cell in it, so whole-column and running-total references cost
    # O(log n) edges each, not O(n). Tree node t of a column with m formula rows is a
    # leaf (the formula at rows[t - m]) when t >= m, else a virtual node with edges to
    # 2t and 2t + 1. Virtual edges only point down the tree, so every cycle found
    # runs through real formula cells.
    trees = {}

    def tree_node(key, t):
        rows, base = trees[key]
        m = len(rows)
        return node[(key[0], rows[t - m], key[1])] if t >= m else base + t

    for sheet, columns in fidx.items():
        for col, rows in columns.items():
            m = len(rows)
            if m < 2:
                continue
            trees[(sheet, col)] = (rows, len(edges))
            edges.extend([] for _ in range(m))  # ids base+0 .. base+m-1; 0 unused
            for t in range(1, m):
                edges[trees[(sheet, col)][1] + t] = [
                    tree_node((sheet, col), 2 * t),
                    tree_node((sheet, col), 2 * t + 1),
                ]
    edge_count = 0
    capped = False
    for i, x in enumerate(wb.formulas):
        for sh, box, *_ in refs_in(x.formula):
            tgt = wb.resolve(sh) if sh else x.sheet
            if not tgt or tgt not in fidx:
                continue
            for col, rows in fidx[tgt].items():
                if not box[0] <= col <= box[2]:
                    continue
                lo = bisect.bisect_left(rows, box[1])
                hi = bisect.bisect_right(rows, box[3])
                if lo >= hi:
                    continue
                if len(rows) < 2:
                    targets = [node[(tgt, rows[0], col)]]
                else:
                    targets = []
                    a, b = lo + len(rows), hi + len(rows)
                    while a < b:
                        if a % 2:
                            targets.append(tree_node((tgt, col), a))
                            a += 1
                        if b % 2:
                            b -= 1
                            targets.append(tree_node((tgt, col), b))
                        a, b = a // 2, b // 2
                edges[i].extend(targets)
                edge_count += len(targets)
                if edge_count >= CIRCULAR_EDGE_CAP:
                    capped = True
                    break
            if capped:
                break
        if capped:
            wb.notes.append(
                {
                    "note": "scan_capped",
                    "detail": "Circular-reference check is incomplete: dependency "
                    f"expansion reached {CIRCULAR_EDGE_CAP:,} edges. "
                    "Unscanned dependencies may contain additional cycles.",
                }
            )
            break
    # iterative Tarjan
    index, low, on, stack, comps, counter = {}, {}, set(), [], [], [0]
    for start in range(len(edges)):
        if start in index:
            continue
        work = [(start, 0)]
        while work:
            v, pi = work.pop()
            if pi == 0:
                index[v] = low[v] = counter[0]
                counter[0] += 1
                stack.append(v)
                on.add(v)
            recurse = False
            for j in range(pi, len(edges[v])):
                w = edges[v][j]
                if w not in index:
                    work.append((v, j + 1))
                    work.append((w, 0))
                    recurse = True
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            if recurse:
                continue
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                real = sorted(w for w in comp if w < n_real)
                if real and (len(comp) > 1 or v in edges[v]):
                    comps.append(real)
            if work:
                u = work[-1][0]
                low[u] = min(low[u], low[v])
    for comp in comps:
        cells = [wb.formulas[i] for i in comp]
        by_sheet = defaultdict(list)
        for x in cells:
            by_sheet[x.sheet].append((x.r, x.c))
        names = ", ".join(
            f"{sh}!{r}" for sh, pts in by_sheet.items() for r in rectangles(pts)
        )
        for sh, pts in by_sheet.items():
            r1, c1 = min(p[0] for p in pts), min(p[1] for p in pts)
            r2, c2 = max(p[0] for p in pts), max(p[1] for p in pts)
            rng = f"{get_column_letter(c1)}{r1}" + (
                "" if (r1, c1) == (r2, c2) else f":{get_column_letter(c2)}{r2}"
            )
            fs.add(
                "circular_reference",
                sh,
                rng,
                f"These cells depend on each other in a loop: {data_text(names)}.",
            )


def check_names_and_links(wb: Workbook, fs: Findings):
    try:
        names = list(wb.wf.defined_names.items())
    except AttributeError:
        names = [(d.name, d) for d in wb.wf.defined_names.definedName]
    for ws in wb.wf.worksheets:
        names += [
            (f"{ws.title}!{n}", d) for n, d in getattr(ws, "defined_names", {}).items()
        ]
    for n, d in names:
        if "#REF!" in (d.attr_text or ""):
            fs.add(
                "broken_named_range",
                None,
                None,
                f"The name {data_text(n)} points at #REF! (a deleted range).",
            )
    ext_pts = defaultdict(dict)
    for x in wb.formulas:
        m = EXT_RE.search(mask_strings(x.formula))
        if m:
            ext_pts[x.sheet][(x.r, x.c)] = m.group(0).strip("[]!'")
    for sheet, pts in ext_pts.items():
        add_grouped(
            fs,
            "external_link",
            sheet,
            pts,
            lambda k, rng: f"Pulls a number from another file ({data_text(k)}).",
        )
    # Private openpyxl 3.1 attribute with no public equivalent; the guard keeps the
    # scan working if a later release renames it.
    if getattr(wb.wf, "_external_links", None) and not ext_pts:
        fs.add(
            "external_link",
            None,
            None,
            f"The workbook keeps {plural(len(wb.wf._external_links), 'link')} to other files (Data > Edit Links).",
        )


def check_formulas(wb: Workbook, fs: Findings):
    hard, vol, long_ = defaultdict(dict), defaultdict(dict), defaultdict(dict)
    for x in wb.formulas:
        nums = literal_numbers(x.formula)
        if nums:
            hard[x.sheet][(x.r, x.c)] = ", ".join(dict.fromkeys(nums))
        up = XL_PREFIX.sub("", mask_strings(x.formula).upper())
        v = [f for f in VOLATILE if re.search(rf"(?<![\w.]){f}\s*\(", up)]
        if v:
            vol[x.sheet][(x.r, x.c)] = "/".join(v)
        depth = if_depth(mask_strings(x.formula))
        if len(x.formula) > LONG_FORMULA_CHARS or depth > MAX_IF_NESTING:
            long_[x.sheet][(x.r, x.c)] = (
                f"{depth} nested IFs"
                if depth > MAX_IF_NESTING
                else f"{len(x.formula)} characters"
            )
    # the same number typed into 3+ formulas is almost always a real assumption
    freq = Counter(
        n for pts in hard.values() for k in pts.values() for n in k.split(", ")
    )
    # working-days constants only matter when the model mixes them
    wd = defaultdict(dict)
    for x in wb.formulas:
        for m in NUM_RE.finditer(mask_strings(x.formula)):
            try:
                v = float(m.group(1))
            except ValueError:
                continue
            if v in WORKDAYS:
                wd[int(v)][(x.sheet, x.r, x.c)] = 0
    if len(wd) >= 2:
        mixed = ", ".join(str(v) for v in sorted(wd))
        for v, cells in wd.items():
            for sheet, r, c in cells:
                hard[sheet][(r, c)] = str(v)
        wb.notes.append(
            {
                "note": "mixed_working_days",
                "detail": f"formulas use different working-days-per-year numbers: {mixed}",
            }
        )

    def describe(k, rng):
        nums = k.split(", ")
        base = (
            f"The numbers {k} are" if len(nums) > 1 else f"The number {k} is"
        ) + " typed into the formula instead of coming from an input cell"
        hints = [
            f"{n} is often {NUMBER_HINTS[float(n)]}"
            for n in nums
            if n.replace(".", "", 1).isdigit() and float(n) in NUMBER_HINTS
        ]
        many = [n for n in nums if freq[n] >= 3]
        return (
            base
            + "."
            + (f" ({'; '.join(hints)})" if hints else "")
            + (
                f" {', '.join(many)} appears in {max(freq[n] for n in many)}+ places, so it is likely a key assumption."
                if many
                else ""
            )
        )

    for sheet, pts in hard.items():
        add_grouped(fs, "hardcoded_number_in_formula", sheet, pts, describe)
    for sheet, pts in vol.items():
        add_grouped(
            fs,
            "volatile_function",
            sheet,
            pts,
            lambda k, rng: (
                f"Uses {k}: recalculates constantly and hides what it refers to; breaks silently when tabs or rows move."
            ),
        )
    for sheet, pts in long_.items():
        add_grouped(
            fs,
            "long_formula",
            sheet,
            pts,
            lambda k, rng: f"Formula is hard to check by eye ({k}).",
        )


def check_patterns(wb: Workbook, fs: Findings):
    """Typed values and odd formulas sitting inside a run of identical formulas."""
    skip = {
        (i["sheet"], r, c)
        for i in fs.items
        if i["check"] in ("ref_in_formula",)
        for (r, c) in i.get("_cells", ())
    }
    vals, incon = defaultdict(dict), defaultdict(dict)
    for s in wb.sheets.values():
        if s.is_data:
            continue
        cells = s.cells
        for (r, c), x in cells.items():
            if r <= s.header_row or (x.sheet, r, c) in skip:
                continue
            for d in ((0, 1), (1, 0)):  # along the row, then down the column
                a = cells.get((r - d[0], c - d[1]))
                b = cells.get((r + d[0], c + d[1]))
                pair = None
                # Down a column, models often alternate line types (revenue, cost, profit...) whose
                # relative formulas can coincide, so a column break needs three matching neighbors.
                a2 = cells.get((r - 2 * d[0], c - 2 * d[1])) if d == (1, 0) else a
                if (
                    a
                    and b
                    and a2
                    and a.formula
                    and b.formula
                    and a2.formula
                    and a.norm == b.norm == a2.norm
                ):
                    pair = a.norm
                elif d == (0, 1) and a and a.formula and not b:
                    a2 = cells.get((r, c - 2))
                    if a2 and a2.formula and a2.norm == a.norm:
                        pair = a.norm  # last cell in a row
                if not pair:
                    continue
                if x.formula and x.norm != pair:
                    incon[s.name][(r, c)] = "row" if d == (0, 1) else "column"
                elif not x.formula and is_num(x.raw):
                    vals[s.name][(r, c)] = "row" if d == (0, 1) else "column"
                break
    for sheet, pts in vals.items():
        add_grouped(
            fs,
            "value_in_formula_row",
            sheet,
            pts,
            lambda k, rng: (
                f"A typed number sits in a {k} of matching formulas. It was likely pasted over and won't update."
            ),
        )
    for sheet, pts in incon.items():
        add_grouped(
            fs,
            "inconsistent_formula",
            sheet,
            pts,
            lambda k, rng: (
                f"Formula differs from the matching formulas around it in its {k}."
            ),
        )


def check_sums_and_blanks(wb: Workbook, fs: Findings):
    gap, empty = defaultdict(dict), defaultdict(dict)
    for x in wb.formulas:
        s = wb.sheets[x.sheet]
        up = mask_strings(x.formula).upper()
        for m in re.finditer(
            r"(?<![\w.])SUM\(\s*(\$?[A-Z]{1,3}\$?\d+):(\$?[A-Z]{1,3}\$?\d+)\s*\)", up
        ):
            c1, r1, c2, r2 = parse_box(f"{m.group(1)}:{m.group(2)}")
            if c1 == c2 == x.c and r2 < x.r:  # vertical total below its block
                between = [s.cells.get((r, x.c)) for r in range(r2 + 1, x.r)]
                if any(
                    b is not None and (is_num(b.cached) or b.formula) for b in between
                ):
                    gap[x.sheet][(x.r, x.c)] = (
                        f"{get_column_letter(x.c)}{r2 + 1}:{get_column_letter(x.c)}{x.r - 1}"
                    )
            elif r1 == r2 == x.r and c2 < x.c:  # horizontal total right of its block
                between = [s.cells.get((x.r, c)) for c in range(c2 + 1, x.c)]
                if any(
                    b is not None and (is_num(b.cached) or b.formula) for b in between
                ):
                    gap[x.sheet][(x.r, x.c)] = (
                        f"{get_column_letter(c2 + 1)}{x.r}:{get_column_letter(x.c - 1)}{x.r}"
                    )
        for sh, box, _s0, _e0, ref in refs_in(x.formula):
            if ":" in ref:
                continue
            tgt = wb.resolve(sh) if sh else x.sheet
            if not tgt:
                continue
            ts = wb.sheets[tgt]
            if box[1] > ROW_CAP or box[0] > COL_CAP:
                continue
            t = ts.cells.get((box[1], box[0]))
            label = (
                f"{tgt}!{get_column_letter(box[0])}{box[1]}"
                if tgt != x.sheet
                else f"{get_column_letter(box[0])}{box[1]}"
            )
            if t is None and not any(
                box[0] <= mc.max_col
                and box[0] >= mc.min_col
                and mc.min_row <= box[1] <= mc.max_row
                for mc in ts.ws.merged_cells.ranges
            ):
                empty[x.sheet][(x.r, x.c)] = label
    for sheet, pts in gap.items():
        add_grouped(
            fs,
            "sum_range_gap",
            sheet,
            pts,
            lambda k, rng: (
                f"The SUM stops short; it misses {k.split(':')[0] if len(set(k.split(':'))) == 1 else k}."
            ),
        )
    for sheet, pts in empty.items():
        add_grouped(
            fs,
            "ref_to_empty_cell",
            sheet,
            pts,
            lambda k, rng: (
                f"Refers to {data_text(k)}, which is blank (counts as zero)."
            ),
        )
