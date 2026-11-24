"""
description: Formula text parsing for the workbook scan: cell references, relative form, function calls, typed numbers and IF nesting.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re

from openpyxl.utils import column_index_from_string, range_boundaries
from scan_limits import MAX_COL, MAX_ROW, OK_NUMBERS, POSITIONAL, WORKDAYS

STR_RE = re.compile(r'"(?:[^"]|"")*"')
REF_RE = re.compile(
    r"(?<![\w.\]\[!:$'])"
    r"(?:(?:'(?P<qs>(?:[^']|'')+)'|(?P<us>[A-Za-z_][\w.]*))!)?"
    r"(?P<ref>\$?[A-Z]{1,3}\$?\d{1,7}(?::\$?[A-Z]{1,3}\$?\d{1,7})?|\$?[A-Z]{1,3}:\$?[A-Z]{1,3}|\$?\d{1,7}:\$?\d{1,7})"
    r"(?![\w(\[!])"
)
EXT_RE = re.compile(r"\[[^\]]*\.(?:xls[xmb]?|csv)\]|(?<![\w\]])\[\d+\][^!]*!", re.I)
NUM_RE = re.compile(
    r"(?<![\w.$:\]\x00])(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\d+)(%?)(?![\w(\[:!.\x00])"
)
CELL_PART = re.compile(r"(\$?)([A-Z]{1,3})(\$?)(\d+)")


def mask_strings(f: str) -> str:
    return STR_RE.sub(lambda m: '"' + "\x00" * (len(m.group()) - 2) + '"', f)


def parse_box(ref: str):
    """'A1', 'A1:B5', 'A:C', '3:7' -> (c1, r1, c2, r2)."""
    ref = ref.replace("$", "")
    a, _, b = ref.partition(":")
    b = b or a
    if a.isalpha():
        return column_index_from_string(a), 1, column_index_from_string(b), MAX_ROW
    if a.isdigit():
        return 1, int(a), MAX_COL, int(b)
    c1, r1, c2, r2 = range_boundaries(f"{a}:{b}")
    return min(c1, c2), min(r1, r2), max(c1, c2), max(r1, r2)


def refs_in(formula: str):
    """Yield (sheet or None, box, start, end, ref_text) for each cell reference."""
    masked = mask_strings(formula)
    for m in REF_RE.finditer(masked):
        sheet = m.group("qs") or m.group("us")
        if sheet:
            sheet = (
                formula[m.start("qs") : m.end("qs")].replace("''", "'")
                if m.group("qs")
                else formula[m.start("us") : m.end("us")]
            )
        try:
            box = parse_box(m.group("ref"))
        except ValueError:
            continue
        yield sheet, box, m.start(), m.end(), m.group("ref")


def normalize(formula: str, row: int, col: int) -> str:
    """Relative (R1C1-style) form, so =B5*C5 in row 5 and =B6*C6 in row 6 compare equal."""
    out, last = [], 0
    for _sheet, _box, s, e, ref in refs_in(formula):

        def conv(mo):
            ca, cl, ra, rn = mo.groups()
            cn = column_index_from_string(cl)
            cs = f"C{cn}" if ca else f"C[{cn - col}]"
            rs = f"R{rn}" if ra else f"R[{int(rn) - row}]"
            return rs + cs

        body = CELL_PART.sub(conv, ref) if re.search(r"[A-Z]\$?\d", ref) else ref
        prefix = formula[s:e][: len(formula[s:e]) - len(ref)]
        out.append(formula[last:s] + prefix + body)
        last = e
    out.append(formula[last:])
    return re.sub(r"\s+", "", "".join(out))


def function_openings(masked: str):
    """Yield opening parentheses and preceding identifiers in one linear pass."""
    start = end = None
    active = False
    for i, ch in enumerate(masked):
        if "A" <= ch <= "Z":
            if not active:
                start = i
            end, active = i + 1, True
        elif active and (ch.isascii() and ch.isdigit() or ch == "."):
            end = i + 1
        elif ch.isspace():
            active = False
        else:
            if ch == "(":
                yield i, masked[start:end] if start is not None else ""
            start = end = None
            active = False


def function_context(masked: str):
    """For each character index: (innermost function name, argument index)."""
    ctx = [("", 0)] * len(masked)
    stack: list[list] = []
    openings = iter(function_openings(masked))
    for i, ch in enumerate(masked):
        if ch == "(":
            _index, name = next(openings)
            stack.append([name, 0])
        elif ch == ")" and stack:
            stack.pop()
        elif ch == "," and stack:
            stack[-1][1] += 1
        ctx[i] = (stack[-1][0], stack[-1][1]) if stack else ("", 0)
    return ctx


def literal_numbers(formula: str):
    """Business-looking numbers typed into a formula."""
    masked = mask_strings(formula)
    chars = list(masked)
    for _sheet, _box, s, e, _ref in refs_in(formula):
        chars[s:e] = ["\x00"] * (e - s)
    masked2 = "".join(chars)
    ctx = function_context(masked2)
    found = []
    for m in NUM_RE.finditer(masked2):
        text, pct = m.group(1), m.group(2)
        try:
            val = float(text) / (100 if pct else 1)
        except ValueError:
            continue
        func, arg = ctx[m.start()]
        if func in POSITIONAL and arg in POSITIONAL[func]:
            continue
        if not pct and (val in OK_NUMBERS or val in WORKDAYS):
            continue
        found.append(text + pct)
    return found


def if_depth(masked: str) -> int:
    depth = best = 0
    stack = []
    openings = iter(function_openings(masked))
    for ch in masked:
        if ch == "(":
            _index, name = next(openings)
            is_if = name in ("IF", "IFS")
            stack.append(is_if)
            if is_if:
                depth += 1
                best = max(best, depth)
        elif ch == ")" and stack:
            if stack.pop():
                depth -= 1
    return best


XL_PREFIX = re.compile(r"_xl(?:fn|ws|udf)\.", re.I)


def func_calls(formula: str):
    """Every function call as (NAME, [arg texts], start, end) - nested calls included."""
    masked = mask_strings(formula)
    out = []
    for m in re.finditer(
        r"(?<![\w.])((?:_xl(?:fn|ws)\.)*[A-Za-z][A-Za-z0-9.]*)\s*\(", masked
    ):
        name = XL_PREFIX.sub("", m.group(1)).upper()
        depth, i, args, last = 1, m.end(), [], m.end()
        while i < len(masked) and depth:
            ch = masked[i]
            if ch in "({":
                depth += 1
            elif ch in ")}":
                depth -= 1
                if depth == 0:
                    args.append(formula[last:i])
            elif ch == "," and depth == 1:
                args.append(formula[last:i])
                last = i + 1
            i += 1
        out.append((name, [a.strip() for a in args], m.start(), i))
    return out


def functions_used(formula: str):
    return {n for n, *_ in func_calls(formula)}


def lookup_family(formula: str):
    names = functions_used(formula)
    if "XLOOKUP" in names:
        return "XLOOKUP"
    if "INDEX" in names and ("MATCH" in names or "XMATCH" in names):
        return "INDEX/MATCH"
    if "VLOOKUP" in names or "HLOOKUP" in names:
        return "VLOOKUP"
    return None
