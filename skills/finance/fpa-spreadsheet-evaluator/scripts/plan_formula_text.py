"""
description: Formula text helpers for planned changes: pattern sources, literal numbers, argument splitting and lookup rewrites.
last_updated: 2026-11-24
"""

from __future__ import annotations

import re

import scan_workbook as S
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter
from plan_common import a1


def pattern_source(s: S.Sheet, r, c):
    """The neighbor whose formula pattern this cell should follow."""
    cells = s.cells
    L, R, L2 = cells.get((r, c - 1)), cells.get((r, c + 1)), cells.get((r, c - 2))
    if (
        L
        and L.formula
        and (
            (R and R.formula and L.norm == R.norm)
            or (not R and L2 and L2.formula and L2.norm == L.norm)
        )
    ):
        return L
    U, D, U2 = cells.get((r - 1, c)), cells.get((r + 1, c)), cells.get((r - 2, c))
    if (
        U
        and D
        and U2
        and U.formula
        and D.formula
        and U2.formula
        and U.norm == D.norm == U2.norm
    ):
        return U
    return None


def translate(src: S.C, r, c):
    return Translator(src.formula, origin=src.coord).translate_formula(a1(r, c))


def literal_spans(formula):
    """(start, end, text) of business-looking numbers - mirrors scan_workbook.literal_numbers."""
    masked = S.mask_strings(formula)
    chars = list(masked)
    for _sh, _box, s0, e0, _ref in S.refs_in(formula):
        chars[s0:e0] = ["\x00"] * (e0 - s0)
    m2 = "".join(chars)
    ctx = S.function_context(m2)
    out = []
    for m in S.NUM_RE.finditer(m2):
        text, pct = m.group(1), m.group(2)
        val = float(text) / (100 if pct else 1)
        func, arg = ctx[m.start()]
        if func in S.POSITIONAL and arg in S.POSITIONAL[func]:
            continue
        if not pct and val in S.OK_NUMBERS:
            continue
        out.append((m.start(), m.end(), text + pct))
    return out


def split_top(text, sep):
    """Split on sep outside parentheses and strings."""
    m = S.mask_strings(text)
    out, depth, last = [], 0, 0
    for i, ch in enumerate(m):
        if ch in "({":
            depth += 1
        elif ch in ")}":
            depth -= 1
        elif ch == sep and depth == 0:
            out.append(text[last:i])
            last = i + 1
    out.append(text[last:])
    return [p.strip() for p in out]


def strip_parens(t):
    t = t.strip()
    while (
        t.startswith("(")
        and t.endswith(")")
        and split_top(t[1:-1], ")") == [t[1:-1].strip()]
    ):
        depth, ok = 0, True
        for i, ch in enumerate(S.mask_strings(t)):
            depth += ch == "("
            depth -= ch == ")"
            if depth == 0 and i < len(t) - 1:
                ok = False
                break
        if not ok:
            break
        t = t[1:-1].strip()
    return t


def range_text(prefix, c1, r1, c2, r2, absolute, whole):
    d = "$" if absolute else ""
    if whole:
        return f"{prefix}{d}{get_column_letter(c1)}:{d}{get_column_letter(c2)}"
    return (
        f"{prefix}{d}{get_column_letter(c1)}{d}{r1}:{d}{get_column_letter(c2)}{d}{r2}"
    )


def split_ref(ref_text):
    """'Prices!$A$2:$D$21' -> ('Prices!', box, absolute, whole_columns)."""
    m = re.match(r"^((?:'[^']+'|[A-Za-z_][\w.]*)!)?(.+)$", ref_text.strip())
    prefix, body = (m.group(1) or ""), m.group(2)
    box = S.parse_box(body)
    return prefix, box, "$" in body, box[3] - box[1] + 1 >= S.MAX_ROW - 1


def vlookup_parts(args):
    if (
        len(args) != 4
        or args[3].strip().upper() not in ("FALSE", "0")
        or not re.fullmatch(r"\d+", args[2].strip())
    ):
        return None
    try:
        prefix, (c1, r1, c2, r2), ab, whole = split_ref(args[1])
    except (
        ValueError,
        AttributeError,
    ):  # not a plain range (a name, say); leave it to the user
        return None
    col = c1 + int(args[2]) - 1
    if col > c2:
        return None
    first = range_text(prefix, c1, r1, c1, r2, ab, whole)
    ret = range_text(prefix, col, r1, col, r2, ab, whole)
    return args[0], first, ret


def to_style(name, args, style):
    """Rewrite one lookup call into the given style. Returns text or None."""
    if name == "VLOOKUP":
        p = vlookup_parts(args)
        if not p:
            return None
        key, look, ret = p
        nf = None
    elif name == "XLOOKUP" and len(args) in (3, 4):
        key, look, ret = args[:3]
        nf = args[3] if len(args) == 4 else None
    elif name == "INDEX" and len(args) == 2:
        mm = re.fullmatch(r"(?:_xlfn\.)?MATCH\((.*)\)", args[1].strip(), re.S | re.I)
        if not mm:
            return None
        margs = split_top(mm.group(1), ",")
        if len(margs) != 3 or margs[2].strip() != "0":
            return None
        key, look, ret, nf = margs[0], margs[1], args[0], None
    else:
        return None
    if style == "XLOOKUP":
        options = f",{nf}" if nf else ""
        if name != "XLOOKUP":
            options = f",{nf or ''},2"
        return f"_xlfn.XLOOKUP({key},{look},{ret}{options})"
    if name == "XLOOKUP":
        # MATCH interprets wildcards; preserve XLOOKUP's literal exact-match key.
        key = (
            f"IF(ISTEXT({key}),SUBSTITUTE(SUBSTITUTE(SUBSTITUTE("
            f'{key},"~","~~"),"*","~*"),"?","~?"),{key})'
        )
    core = f"INDEX({ret},MATCH({key},{look},0))"
    return f"_xlfn.IFNA({core},{nf})" if nf else core


def rewrite_calls(formula, wanted, fn):
    """Apply fn(name, args) -> new text to every call named in `wanted` (outermost first, right to left)."""
    calls = [c for c in S.func_calls(formula) if c[0] in wanted]
    calls = [
        c
        for c in calls
        if not any(o is not c and o[2] < c[2] and c[3] <= o[3] for o in calls)
    ]
    new, changed = formula, False
    for name, args, a, b in sorted(calls, key=lambda c: -c[2]):
        t = fn(name, args)
        if t:
            new, changed = new[:a] + t + new[b:], True
    return new if changed else None
