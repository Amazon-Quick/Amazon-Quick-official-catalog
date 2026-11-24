"""
description: Value parsing and formatting for the purchase and invoice review engine: amounts, dates, periods, fiscal buckets, row lookup and the findings collector.
last_updated: 2026-11-24
"""

import datetime as dt
import re
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from pir_state import (
    _MAPPED_COLS,
    _STATE,
    INPUTS,
    SEV_RANK,
    VERDICT,
    ClarificationNeeded,
    _emit,
)


def D(v, default=None):
    if v is None:
        return default
    s = str(v).strip().replace(",", "").replace("$", "")
    if s == "":
        return default
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return default
    return (-d if neg else d) if d.is_finite() else default


def money(d):
    return str((d or Decimal(0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _pct(x):
    """Ratio as a percentage with one decimal ('0.05' -> '5.0%')."""
    return "{}%".format(
        (Decimal(x) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    )


def mfmt(v):
    """Report display form of an amount: thousands separators, two decimals (12500 -> '12,500.00')."""
    d = v if isinstance(v, Decimal) else D(v, Decimal(0))
    return "{:,.2f}".format(
        (d or Decimal(0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def date(v):
    s = (v or "").strip()
    if not s:
        return None
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        a, b = int(m[1]), int(m[2])
        order = _STATE.get("date_order")
        if a != b and a <= 12 and b <= 12 and not order:
            raise ClarificationNeeded(
                f"Does {s} mean month/day/year or day/month/year?",
                details={"field": "date", "value": s, "options": ["MDY", "DMY"]},
            )
        fmt = "%d/%m/%Y" if order == "DMY" or a > 12 else "%m/%d/%Y"
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            return None
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def g(r, *names, default=""):
    for n in names:
        if n in r and str(r[n]).strip() != "":
            return str(r[n]).strip()
    return default


def norm_ref(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper()).lstrip("0")


class Out:
    def __init__(self, sub, params):
        self.sub, self.params = sub, params
        self.findings, self.ok, self.extra = [], [], {}

    def add(self, rule, item, sev, what, number, src, at_stake=Decimal(0)):
        self.findings.append(
            {
                "rule": rule,
                "item": item,
                "severity": sev,
                "what": what,
                "number": number,
                "source": src,
                "at_stake": money(at_stake),
            }
        )

    def clear(self, rule, item, note):
        self.ok.append({"rule": rule, "item": item, "note": note})

    def skip(self, check, field, question="", item=None):
        """Record a check that was not run because a required threshold or input was absent."""
        entry = {"check": check, "field": field, "question": question}
        if item is not None:
            entry["item"] = item
        self.extra.setdefault("not_run", []).append(entry)

    def dump(self):
        worst = defaultdict(int)
        for f in self.findings:
            worst[f["item"]] = max(worst[f["item"]], SEV_RANK[f["severity"]])
        items = sorted(
            set([f["item"] for f in self.findings] + [o["item"] for o in self.ok])
        )
        verdicts = {i: VERDICT[worst.get(i, 0)] for i in items}
        self.findings.sort(
            key=lambda f: (f["item"], -SEV_RANK[f["severity"]], f["rule"], f["source"])
        )
        self.ok.sort(key=lambda o: (o["item"], o["rule"]))
        res = {
            "label": "script-computed",
            "subcommand": self.sub,
            "params": self.params,
            "inputs": INPUTS,
            "findings": self.findings,
            "checked_no_issue": self.ok,
            "suggested_verdict": verdicts,
        }
        # Fuzzy-mapping metadata
        if _MAPPED_COLS:
            res["mapped_columns"] = dict(_MAPPED_COLS)
        res.update(self.extra)
        _emit(res)


_MONTHS = {
    m: i
    for i, m in enumerate(
        (
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
        ),
        1,
    )
}


def _year(s):
    y = int(s)
    return y + 2000 if y < 100 else y


def _parse_period(period):
    """Read a period label. Returns ("month", year, month), ("quarter", year, quarter) or None.

    Months: 2026-11, 2026/11, 2026-11-15, 11/15/2026, 15/11/2026 (day > 12), 11-2026, Nov-2026,
    November 2026, Nov-26, 15-Nov-2026. Quarters: 2026-Q4, Q4-2026, Q4 2026, FY2026-Q4, FY26 Q4
    (read as fiscal-quarter labels). A label without a year (for example 'Q4') returns None.
    """
    s = str(period or "").strip()
    if not s or len(s) > 40:
        return None
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})(?:[-/.](\d{1,2}))?(?:[ T].*)?", s)
    if m:
        return ("month", int(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:[ T].*)?", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return ("month", int(m.group(3)), b if a > 12 else a)
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{4})", s)
    if m:
        return ("month", int(m.group(2)), int(m.group(1)))
    m = re.fullmatch(r"(?:\d{1,2}[-\s])?([A-Za-z]{3,9})\.?[-\s/']*(\d{4}|\d{2})", s)
    if m and m.group(1)[:3].lower() in _MONTHS:
        return ("month", _year(m.group(2)), _MONTHS[m.group(1)[:3].lower()])
    m = re.fullmatch(r"(?:FY)?\s*(\d{4}|\d{2})[-\s]*Q([1-4])", s, re.I)
    if m:
        return ("quarter", _year(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r"Q([1-4])[-\s]*(?:FY)?\s*(\d{4}|\d{2})", s, re.I)
    if m:
        return ("quarter", _year(m.group(2)), int(m.group(1)))
    return None


def fiscal(period, start_month):
    """period label -> (FY label, quarter label), or None when the period cannot be read.

    FY is named by the calendar year it ends in. Quarter labels (2026-Q4) are taken as fiscal.
    """
    p = _parse_period(period)
    if p is None:
        return None
    kind, y, n = p
    if kind == "quarter":
        return f"FY{y}", f"FY{y}-Q{n}"
    if not 1 <= n <= 12:
        return None
    fy = y if start_month == 1 or n < start_month else y + 1
    q = ((n - start_month) % 12) // 3 + 1
    return f"FY{fy}", f"FY{fy}-Q{q}"
