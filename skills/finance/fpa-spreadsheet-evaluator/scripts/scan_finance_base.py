"""
description: Shared helpers for the finance checks: period headers, finance word lists, value and label helpers, units and currencies.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict

from scan_findings import rectangles
from scan_formats import fmt_decimals, fmt_scale, fmt_section, is_num
from scan_formula_text import REF_RE, mask_strings, parse_box, refs_in
from scan_labels import row_label_at

MONTH_NAMES = [
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
]
_MON = (
    r"(january|february|march|april|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|nov|dec)"
)
_TAIL = (
    r"(?:\s+(?:a|f|p|b|e|act|actual|actuals|fcst|forecast|plan|budget|est|estimate))?"
)
MON_RE = re.compile(r"^" + _MON + r"\.?(?:[\s'\-/]*(\d{4}|\d{2}))?" + _TAIL + r"$")
Q_RE = re.compile(
    r"^(?:q([1-4])|([1-4])q)(?:[\s'\-/]*(?:fy|cy)?\s*'?(\d{4}|\d{2}))?" + _TAIL + r"$"
)
FYQ_RE = re.compile(r"^(?:fy|cy)\s*'?(\d{4}|\d{2})[\s\-/]*q([1-4])" + _TAIL + r"$")
Y_RE = re.compile(r"^(?:(?:fy|cy)\s*'?(\d{4}|\d{2})|(19\d\d|20\d\d))" + _TAIL + r"$")
TOTAL_COL_RE = re.compile(
    r"\b(total|full[\s-]?year|annual|ytd|year[\s-]?to[\s-]?date|sum)\b", re.I
)
TOTAL_ROW_RE = re.compile(
    r"^\s*(total|grand total|sub[\s-]?total|sum|net)\b|\btotal\s*$", re.I
)
# Row labels for amounts that are not summed across periods (rates, balances, counts).
NON_ADDITIVE_WORDS = (
    "%",
    r"\brate",
    "ratio",
    "margin",
    r"\bavg\b",
    "average",
    r"\bper\b",
    "price",
    r"head\s*count",
    r"\bfte",
    r"\bheads?\b",
    "balance",
    "ending",
    "closing",
    "opening",
    "beginning",
    "cumulative",
    r"\bytd\b",
    r"\bdays\b",
    "multiple",
    "growth",
    "yield",
    "index",
    r"\bcount\b",
    "#",
    r"\bmix\b",
    "share",
    "utili[sz]ation",
    "attrition",
    "churn",
    r"\bpct\b",
    r"run[\s-]?rate",
    r"\barr\b",
    r"\bmrr\b",
    "inventory",
    "end of",
    r"\beop\b",
    r"\bbop\b",
)
NON_ADDITIVE = re.compile("|".join(NON_ADDITIVE_WORDS), re.I)
GROWTH_WORDS = re.compile(
    r"growth|change|\bchg\b|\bvar\b|variance|\byoy\b|\bmom\b|\bqoq\b|delta|diff|increase|decrease|%\s*chg",
    re.I,
)
KEY_WORDS = re.compile(
    r"revenue|sales|bookings|opex|expense|cost|cogs|head\s*count|\bfte|\bheads\b|margin|ebitda|profit|income|"
    r"payroll|salar|compensation|capex|cash",
    re.I,
)
SIGNED_POSITIVE = re.compile(
    r"revenue|sales|bookings|head\s*count|\bfte|\bheads\b|\bunits\b|customers|volume",
    re.I,
)
MARGIN_WORDS = re.compile(r"margin|% of (revenue|sales)", re.I)
ASSUMPTION_WORDS = re.compile(
    r"rate|%|growth|inflation|price|cost per|per unit|\bfx\b|exchange|\btax|discount|wacc|margin|attrition|"
    r"churn|salary|wage|bonus|benefit|load|assum|driver|multiplier|factor|\bdays\b|terms|\bdso\b|\bdpo\b|"
    r"useful life|depreciation",
    re.I,
)
LABEL_STOP = {
    "total",
    "subtotal",
    "sub total",
    "grand total",
    "sum",
    "other",
    "others",
    "value",
    "amount",
    "net",
    "check",
    "variance",
    "diff",
    "difference",
    "notes",
    "note",
    "memo",
    "balance",
    "actual",
    "actuals",
    "plan",
    "budget",
    "forecast",
    "result",
}
KEY_HEADER = re.compile(
    r"\b(id|key|code|no|number|#|employee|emp|account|acct|invoice|order|sku|ticket|po)\b",
    re.I,
)
NOT_MEASURE = re.compile(
    r"\b(id|key|code|no|number|#|zip|postal|phone|year|month|day|date|account|acct|invoice|order|sku|po|row|index)\b",
    re.I,
)
DEFAULT_TAB_RE = re.compile(
    r"^(sheet|tab)\s*\d*$|^copy of\b|\(\d+\)\s*$|\b(test|temp|tmp|old|scratch|backup|bkp|do not use)\b|^new\b",
    re.I,
)
LABEL_SCALE_RE = [
    (
        "thousands",
        re.compile(
            r"\(\s*[$€£]?\s*(k|000s?|'000s?|thousands?)\s*\)|[$€£]\s?k\b|in thousands|\(\s*[$€£]?\s*000\s*\)",
            re.I,
        ),
    ),
    (
        "millions",
        re.compile(
            r"\(\s*[$€£]?\s*(m|mm|mn|millions?)\s*\)|[$€£]\s?mm?\b|in millions", re.I
        ),
    ),
]
CUR_FMT_RE = re.compile(r"\[\$([^\]\-]*)")
CUR_CODE_RE = re.compile(
    r"\b(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|RMB|INR|MXN|BRL|SGD|HKD|SEK|NOK|DKK|NZD|ZAR|KRW)\b"
)
CUR_NORM = {
    "$": "$",
    "US$": "$",
    "USD": "$",
    "€": "€",
    "EUR": "€",
    "£": "£",
    "GBP": "£",
    "¥": "¥",
    "JPY": "¥",
    "₹": "₹",
    "INR": "₹",
}
MAX_JUDGMENT = 40  # questions are useful in small numbers; past this they become noise


def _v(x):
    """The value a cell shows: saved result for formulas, typed value otherwise."""
    if x is None:
        return None
    return x.cached if x.formula else x.raw


def _numv(x):
    v = _v(x)
    return v if is_num(v) and not (x is not None and x.is_date) else None


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if not n:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _year(t):
    if not t:
        return None
    y = int(t)
    return y + 2000 if y < 100 else y


def period_key(v):
    """('m'|'mo'|'q'|'qo'|'y', ordinal) for a period header, or None."""
    if isinstance(v, (dt.datetime, dt.date)):
        return ("m", v.year * 12 + v.month - 1)
    if is_num(v):
        return ("y", int(v)) if float(v).is_integer() and 1990 <= v <= 2100 else None
    if not isinstance(v, str):
        return None
    t = " ".join(v.strip().lower().replace("\u2019", "'").split())
    if not t or len(t) > 28:
        return None
    m = MON_RE.match(t)
    if m:
        mi = MONTH_NAMES.index(m.group(1)[:3])
        y = _year(m.group(2))
        return ("m", y * 12 + mi) if y else ("mo", mi)
    m = Q_RE.match(t)
    if m:
        q = int(m.group(1) or m.group(2)) - 1
        y = _year(m.group(3))
        return ("q", y * 4 + q) if y else ("qo", q)
    m = FYQ_RE.match(t)
    if m:
        return ("q", _year(m.group(1)) * 4 + int(m.group(2)) - 1)
    m = Y_RE.match(t)
    if m:
        return ("y", _year(m.group(1) or m.group(2)))
    return None


KIND_WORD = {"m": "month", "mo": "month", "q": "quarter", "qo": "quarter", "y": "year"}
KIND_RANK = {"m": 0, "mo": 0, "q": 1, "qo": 1, "y": 2}


def period_text(kind, o):
    if kind == "m":
        return f"{MONTH_NAMES[o % 12].title()} {o // 12}"
    if kind == "mo":
        return MONTH_NAMES[o % 12].title()
    if kind == "q":
        return f"Q{o % 4 + 1} {o // 4}"
    if kind == "qo":
        return f"Q{o % 4 + 1}"
    return str(o)


def period_layout(s):
    """Find the row of period headers: which columns are periods, and which are totals of them."""
    best = None
    for r in sorted(s.rows)[:15]:
        keys = {}
        for x in sorted(s.rows[r], key=lambda y: y.c):
            k = period_key(_v(x))
            if k:
                keys[x.c] = k
        by_kind = Counter(k[0] for k in keys.values())
        if not by_kind:
            continue
        kind, n = by_kind.most_common(1)[0]
        if n >= 3 and (best is None or n > best[2]):
            best = (r, kind, n, keys)
    if not best:
        return None
    r, kind, _, keys = best
    cols = {c: k[1] for c, k in keys.items() if k[0] == kind}
    order = sorted(cols)
    text = {}
    for x in s.rows[r]:
        v = _v(x)
        text[x.c] = (
            v.strftime("%b %Y")
            if isinstance(v, (dt.datetime, dt.date))
            else str(v).strip()
            if v is not None
            else ""
        )
    totals = {}
    last_sub = None
    for x in sorted(s.rows[r], key=lambda y: y.c):
        if x.c in cols:
            continue
        k = keys.get(x.c)
        coarser = k is not None and KIND_RANK[k[0]] > KIND_RANK[kind]
        is_total = (
            bool(isinstance(_v(x), str) and TOTAL_COL_RE.search(_v(x))) or coarser
        )
        if not is_total:
            continue
        if (
            k is not None and k[0] in ("q", "qo") and KIND_RANK[kind] == 0
        ):  # a quarter subtotal among months
            comps = [c for c in order if c < x.c and (last_sub is None or c > last_sub)]
            last_sub = x.c
        else:
            comps = list(order)
        if len(comps) >= 2:
            totals[x.c] = comps
    return {
        "row": r,
        "kind": kind,
        "cols": cols,
        "order": order,
        "totals": totals,
        "text": text,
    }


def _fmtn(v, fmt=""):
    if not is_num(v):
        return str(v)
    if "%" in fmt_section(fmt or ""):
        return f"{v * 100:,.4g}%"
    if v != 0 and abs(v) < 1:
        return f"{v:.4g}"
    return f"{v:,.0f}" if abs(v) >= 100 or float(v).is_integer() else f"{v:,.2f}"


def _close(a, b, fmt=""):
    scale = {"units": 1, "thousands": 1e3, "millions": 1e6, "billions": 1e9}[
        fmt_scale(fmt or "General")
    ]
    dec = fmt_decimals(fmt or "General")
    unit = scale * (10**-dec) if dec is not None else 0
    if "%" in fmt_section(fmt or ""):
        unit /= 100
    return abs(a - b) <= max(max(abs(a), abs(b)) * 5e-4, 0.5 * unit + 1e-9, 1e-6)


def _norm_label(t):
    t = re.sub(r"\([^)]*\)", " ", str(t).lower())
    return " ".join(re.sub(r"[^a-z0-9%&]+", " ", t).split())


def _label_left(s, r, c):
    return row_label_at(s, r, c) or ""


def _grouped_add(fs, check, sheet, pts, severity=None):
    """pts: [(r, c, key, text)]. One finding per pattern per rectangle, worded from its first cell."""
    by, first = defaultdict(list), {}
    for r, c, key, text in pts:
        by[key].append((r, c))
        first.setdefault(key, text)
    for key, cells in by.items():
        for rng in rectangles(cells):
            c1, r1, c2, r2 = parse_box(rng)
            n = (c2 - c1 + 1) * (r2 - r1 + 1)
            fs.add(
                check,
                sheet,
                rng,
                first[key]
                + (
                    f" The same formula repeats across {rng} ({n} cells)."
                    if n > 1
                    else ""
                ),
                severity=severity,
            )


def _find(fs, check, sheet, cell):
    return any(
        i["check"] == check and i["sheet"] == sheet and i.get("cell") == cell
        for i in fs.items
    )


def _cells_in(wb, sheet, box, cap=2000):
    c1, r1, c2, r2 = box
    if (c2 - c1 + 1) * (r2 - r1 + 1) > cap:
        return None
    return [(sheet, r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]


ADDITIVE_RE = re.compile(r"^=[\s+\-(),A-Z0-9$:!'_.\[\]]*$", re.I)


def additive_cells(wb, x, spend=None):
    """Cells a purely additive formula (=A1+A2, =SUM(A1:A5)+B2) adds up, or None."""
    f = mask_strings(x.formula)
    body = re.sub(r"\bSUM\s*\(", "(", f, flags=re.I)
    if (
        re.search(r"[A-Z]+\s*\(", re.sub(REF_RE, "R", body), re.I)
        or not ADDITIVE_RE.match(body)
        or "-" in re.sub(REF_RE, "R", body)
    ):
        return None
    out = set()
    for sh, box, *_ in refs_in(x.formula):
        tgt = wb.resolve(sh) if sh else x.sheet
        if not tgt:
            return None
        if spend is not None and not spend(
            min(2000, (box[2] - box[0] + 1) * (box[3] - box[1] + 1))
        ):
            return None
        cells = _cells_in(wb, tgt, box)
        if cells is None:
            return None
        out.update(cells)
    return out


def _direct_refs(wb, x, cap=400):
    out = []
    for sh, box, *_ in refs_in(x.formula):
        tgt = wb.resolve(sh) if sh else x.sheet
        if tgt:
            cells = _cells_in(wb, tgt, box, cap)
            if cells:
                out.extend(cells)
    return out


def _label_scale(text):
    for name, rx in LABEL_SCALE_RE:
        if rx.search(text or ""):
            return name
    return None


def sheet_title_text(s):
    """Text above the header row (titles like 'Payroll ($K)') plus the header row's first label."""
    top = (
        min(
            [s.header_row] + ([s.periods["row"]] if getattr(s, "periods", None) else [])
        )
        or 1
    )
    out = [
        str(_v(x))
        for r in sorted(s.rows)
        if r < top
        for x in s.rows[r]
        if isinstance(_v(x), str)
    ]
    head = sorted(
        (x for x in s.rows.get(top, []) if isinstance(_v(x), str)), key=lambda y: y.c
    )
    if head:
        out.append(str(_v(head[0])))
    return " ".join(out)


def stored_scale(wb, sh, r, c):
    """Unit the stored number is in: base units when the number format scales it for display,
    otherwise what the row label, column header or tab title says. None when nothing says."""
    s = wb.sheets.get(sh)
    x = s.cells.get((r, c)) if s else None
    if x is None or fmt_scale(x.fmt) != "units":
        return (
            None  # a scaling number format makes the stored unit ambiguous: don't guess
        )
    head = s.cells.get((s.header_row, c)) if s.header_row else None
    for text in (
        _label_left(s, r, c),
        _v(head) if head is not None else "",
        s.title_text,
    ):
        sc = _label_scale(str(text or ""))
        if sc:
            return sc
    return None


def cell_currency(wb, sh, r, c):
    s = wb.sheets.get(sh)
    x = s.cells.get((r, c)) if s else None
    if x is None:
        return None
    sec = (x.fmt or "").split(";")[0]
    for code in CUR_FMT_RE.findall(sec):
        code = code.strip()
        if code:
            # Unknown codes are workbook text: keep them as short as a currency code.
            return CUR_NORM.get(code.upper(), CUR_NORM.get(code, code.upper()[:8]))
    plain_fmt = re.sub(r"\[[^\]]*\]", "", sec)
    for sym in ("€", "£", "¥", "₹", "$"):
        if sym in plain_fmt:
            return sym
    head = s.cells.get((s.header_row, c)) if s.header_row else None
    for text in (_label_left(s, r, c), _v(head) if head is not None else ""):
        m = CUR_CODE_RE.search(str(text or ""))
        if m:
            return CUR_NORM.get(m.group(1), m.group(1))
    return None
