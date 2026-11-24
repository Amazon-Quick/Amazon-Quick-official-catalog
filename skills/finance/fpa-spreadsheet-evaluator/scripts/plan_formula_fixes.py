"""
description: Planned formula changes: restore a row's pattern, extend a SUM, move a typed number to an input, and rewrite lookups and ranges.
last_updated: 2026-11-24
"""

from __future__ import annotations

import re
from collections import Counter

import scan_workbook as S
from openpyxl.utils import get_column_letter
from plan_common import (
    a1,
    cells_of,
    display,
    fill_template,
    money,
    nearest,
    quote_sheetname,
    row_label,
    short,
)
from plan_formula_text import (
    literal_spans,
    pattern_source,
    rewrite_calls,
    to_style,
    translate,
)


def restore_pattern(p, f, risk):
    s = p.wb.sheets[f["sheet"]]
    pts = cells_of(f["cell"])
    if pts is None:
        return p.needs_you(f)
    edits, parts = [], []
    for r, c in pts:
        if (s.name, r, c) in p.claimed:
            continue
        x, src = s.cells.get((r, c)), pattern_source(s, r, c)
        if not x or not src:
            continue
        new = translate(src, r, c)
        if p.points_at_blank(s.name, new):
            return p.needs_you(
                f,
                "The row's pattern would point this cell at an empty cell (the row may be shifted); "
                "set the formula by hand.",
            )
        edits.append(
            {
                "op": "cell",
                "sheet": s.name,
                "cell": a1(r, c),
                "formula": new,
                "style_from": src.coord,
            }
        )
        parts.append((a1(r, c), x, new))
    if not edits:
        return p.needs_you(f)
    cell, x, new = parts[0]
    if f["check"] == "value_in_formula_row":
        summary = (
            f"Use formula {new} instead of typed {money(x.raw)} (confirm the typed value is not an intentional override)"
            if len(parts) == 1
            else f"Use the row's formula in {len(parts)} cells (confirm the typed values are not intentional overrides)"
        )
        action = "formula"
    else:
        summary = (
            f"{short(x.formula)} → {short(new)} (match the formulas around it)"
            if len(parts) == 1
            else f"Make {len(parts)} cells match the formulas around them"
        )
        action = "formula"
    p.add([f["id"]], s.name, f["cell"], action, risk, summary, edits)


def extend_sum(p, f):
    s = p.wb.sheets[f["sheet"]]
    for r, c in cells_of(f["cell"]) or []:
        x = s.cells.get((r, c))
        if not x or not x.formula or (s.name, r, c) in p.claimed:
            continue
        m = re.search(
            r"(?<![\w.])SUM\(\s*(\$?[A-Z]{1,3}\$?\d+):(\$?[A-Z]{1,3}\$?\d+)\s*\)",
            x.formula,
            re.I,
        )
        if not m:
            continue
        c1, r1, c2, r2 = S.parse_box(f"{m.group(1)}:{m.group(2)}")
        if c1 == c2 == c and r2 < r:
            end = a1(r - 1, c)
            missed = [s.cells.get((rr, c)) for rr in range(r2 + 1, r)]
        elif r1 == r2 == r and c2 < c:
            end = a1(r, c - 1)
            missed = [s.cells.get((r, cc)) for cc in range(c2 + 1, c)]
        else:
            continue
        keep_abs = "$" in m.group(2)
        end_txt = re.sub(r"([A-Z]+)(\d+)", r"$\1$\2", end) if keep_abs else end
        new = x.formula[: m.start(2)] + end_txt + x.formula[m.end(2) :]
        add = sum(v.cached for v in missed if v is not None and S.is_num(v.cached))
        p.add(
            [f["id"]],
            s.name,
            a1(r, c),
            "formula",
            "safe",
            f"{short(x.formula)} → {short(new)} (adds the missing line{'s' if len(missed) > 1 else ''}, {'+' if add >= 0 else ''}{money(add)})",
            [{"op": "cell", "sheet": s.name, "cell": a1(r, c), "formula": new}],
        )
        return
    p.needs_you(f)


def inputs_tab(p, from_sheet):
    reads = p.sheet_roles.get(from_sheet, {}).get("reads_from", [])
    tabs = [
        x["sheet"]
        for x in p.scan.get("sheets", [])
        if x["role"] == "inputs" and x["state"] == "visible"
    ]
    for t in tabs:
        if t in reads:
            return t
    return tabs[0] if tabs else None


def extract_input(p, f):
    s = p.wb.sheets[f["sheet"]]
    pts = cells_of(f["cell"])
    if pts is None or p.is_claimed(s.name, pts):
        return p.needs_you(f) if pts is None else None
    lits = set()
    for r, c in pts:
        x = s.cells.get((r, c))
        if x and x.formula:
            lits |= {t for _, _, t in literal_spans(x.formula)}
    tab = inputs_tab(p, s.name)
    if len(lits) != 1 or not tab:
        why = (
            "Move each typed number to a labeled input cell"
            if len(lits) != 1
            else "Add an inputs area, then move the number there"
        )
        return p.needs_you(f, why)
    lit = lits.pop()
    val = float(lit.rstrip("%")) / (100 if lit.endswith("%") else 1)
    t = p.wb.sheets[tab]
    role = p.conv.get("input", {})
    inputs = [
        x
        for x in t.cells.values()
        if not x.formula
        and S.is_num(x.raw)
        and all(getattr(x, a) == v for a, v in role.items())
    ]
    vcol = Counter(x.c for x in inputs).most_common(1)[0][0] if inputs else 2
    lcol = min((x.c for x in t.cells.values()), default=1)
    if lcol >= vcol:
        lcol = max(1, vcol - 1)
    row = p.new_inputs.get(tab) or max((x.r for x in t.cells.values()), default=0) + 2
    p.new_inputs[tab] = row + 1
    style_v = max(inputs, key=lambda x: x.r) if inputs else None
    style_l = t.cells.get((style_v.r, lcol)) if style_v else None
    label = f"{row_label(s, *pts[0]) or 'Assumption'} - moved from {s.name}!{f['cell']}"
    ref = f"{quote_sheetname(tab)}!${get_column_letter(vcol)}${row}"
    edits = [
        {
            "op": "new_cell",
            "sheet": tab,
            "cell": a1(row, lcol),
            "value": label,
            **({"style_from": f"{tab}!{style_l.coord}"} if style_l else {}),
        },
        {
            "op": "new_cell",
            "sheet": tab,
            "cell": a1(row, vcol),
            "value": val,
            **({"style_from": f"{tab}!{style_v.coord}"} if style_v else {}),
        },
    ]
    for r, c in pts:
        x = s.cells.get((r, c))
        if not x or not x.formula:
            continue
        new, last = [], 0
        for a, b, txt in literal_spans(x.formula):
            if txt == lit:
                new.append(x.formula[last:a] + ref)
                last = b
        new.append(x.formula[last:])
        e = {
            "op": "cell",
            "sheet": s.name,
            "cell": a1(r, c),
            "formula": "".join(new),
        }
        # the formula now pulls from another tab: follow the model's cross-tab style if it has one
        link_conv = p.conv.get("link")
        if (
            link_conv
            and not (x.links - {"[external]"})
            and any(getattr(x, a) != v for a, v in link_conv.items())
        ):
            like = nearest(
                s,
                r,
                c,
                lambda y, x=x, link_conv=link_conv: (
                    bool(y.formula and (y.links - {"[external]"}))
                    and y.fmt == x.fmt
                    and all(getattr(y, a) == v for a, v in link_conv.items())
                ),
            )
            if like:
                e["style_from"] = like.coord
        edits.append(e)
    p.add(
        [f["id"]],
        s.name,
        f["cell"],
        "formula + new input",
        "confirm",
        f"Move {lit} to a new input {tab}!{a1(row, vcol)} (labeled) and point "
        f"{'the formula' if len(edits) == 3 else f'{len(edits) - 2} formulas'} at it",
        edits,
    )


def lookup_target(p):
    xl = p.scan.get("excel", {})
    dom = xl.get("lookup_style", {}).get("dominant")
    modern = xl.get("effective_target") in ("2021", "365")
    if dom == "XLOOKUP" and not modern:
        return "INDEX/MATCH"
    return dom or ("XLOOKUP" if modern else "INDEX/MATCH")


def formula_rewrite(p, f, risk, wanted, fn, summary, declined=None):
    s = p.wb.sheets.get(f["sheet"])
    pts = cells_of(f["cell"]) if s else None
    if not pts:
        return p.needs_you(f)
    edits, sample = [], None
    for r, c in pts:
        x = s.cells.get((r, c))
        if not x or not x.formula or (s.name, r, c) in p.claimed:
            continue
        new = rewrite_calls(x.formula, wanted, fn) if wanted else fn(x)
        if new and new != x.formula:
            edits.append(
                {"op": "cell", "sheet": s.name, "cell": a1(r, c), "formula": new}
            )
            sample = sample or (x.formula, new)
    if not edits:
        return p.needs_you(f, declined)
    n = len(edits)
    p.add(
        [f["id"]],
        s.name,
        f["cell"],
        "formula",
        risk,
        fill_template(
            summary,
            old=short(display(sample[0])),
            new=short(display(sample[1])),
            n=str(n),
            cells=f" ({n} cells)" if n > 1 else "",
        ),
        edits,
    )


def fix_lookup_style(p, f, style=None):
    style = style or lookup_target(p)
    return formula_rewrite(
        p,
        f,
        "confirm",
        {"VLOOKUP", "XLOOKUP", "INDEX"},
        lambda n, a: (
            to_style(n, a, style)
            if (n != "INDEX" or style != "INDEX/MATCH")
            and not (n == "XLOOKUP" and style == "XLOOKUP")
            else None
        ),
        "{old} → {new}{cells} (written the way the model does its lookups)"
        if f["check"] == "lookup_style_inconsistent"
        else "{old} → {new}{cells} (works in every Excel version the readers use)",
    )


def fix_compat(p, f):
    fns = set(re.findall(r"^(\w+) needs", f["description"]))
    if fns & {"XLOOKUP"}:
        return fix_lookup_style(p, f, "INDEX/MATCH")
    return p.needs_you(
        f, "Rewrite with older functions, or confirm every reader has a newer Excel"
    )


def fix_vlookup_approx(p, f):
    return formula_rewrite(
        p,
        f,
        "confirm",
        {"VLOOKUP", "HLOOKUP"},
        lambda n, a: f"{n}({','.join(a)},FALSE)" if len(a) == 3 else None,
        "{old} → {new}{cells} (exact match; the result can change if it was relying on a range match)",
    )


def fix_sumproduct(p, f):
    return p.needs_you(
        f,
        "Review any SUMIFS rewrite with the owner: SUMPRODUCT equality and "
        "SUMIFS criteria differ for wildcards, operators, text numbers, blanks "
        "and errors. Equivalent results have not been established.",
    )


def fix_whole_column(p, f):
    def bound(x):
        out, last = [], 0
        for sh, box, _s0, e0, ref in S.refs_in(x.formula):
            if box[3] - box[1] + 1 < S.MAX_ROW - 1:
                continue
            tgt = p.wb.resolve(sh) if sh else x.sheet
            t = p.wb.sheets.get(tgt)
            if not t or not t.rows:
                return None
            r1, r2 = t.header_row + 1, max(t.rows)
            d = "$" if "$" in ref else ""
            new_ref = f"{d}{get_column_letter(box[0])}{d}{r1}:{d}{get_column_letter(box[2])}{d}{r2}"
            out.append(x.formula[last : e0 - len(ref)] + new_ref)
            last = e0
        out.append(x.formula[last:])
        return "".join(out)

    return formula_rewrite(
        p,
        f,
        "confirm",
        None,
        bound,
        "{old} → {new}{cells} (only the rows in use; widen if the data grows, or use a Table)",
    )


def fix_redundant(p, f):
    def simp(x):
        body = x.formula[1:].strip()
        if body.startswith("+"):
            return "=" + body[1:]
        m = re.fullmatch(r"SUM\((.*)\)", body, re.I | re.S)
        if not m:
            return None
        ref = m.group(1).strip()
        refs = list(S.refs_in("=" + ref))
        if len(refs) != 1:
            return None
        sh, box, start, end, _text = refs[0]
        if start != 1 or end != len(ref) + 1 or box[:2] != box[2:]:
            return None
        target = p.wb.resolve(sh) if sh else x.sheet
        cell = p.wb.cell(target, box[1], box[0]) if target else None
        # SUM ignores text and booleans in references; a direct reference does not.
        if cell is None or not S.is_num(cell.cached if cell.formula else cell.raw):
            return None
        return "=" + ref

    return formula_rewrite(
        p,
        f,
        "safe",
        None,
        simp,
        "{old} → {new}{cells} (same result)",
        declined=(
            "Check whether the SUM can go: around named ranges, table columns or "
            "multi-cell math it adds up the whole array, so removing it can change the result."
        ),
    )
