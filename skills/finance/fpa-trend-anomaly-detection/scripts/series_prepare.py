"""
description: Check the lines that were read and put every line on one regular time grid, listing what must be asked first.
last_updated: 2026-11-24
"""

from __future__ import annotations

import datetime as _dt
import re

import numpy as np
import series_engine as eng
import series_stats as stats
from intake_cells import _untrusted_values
from intake_periods import parse_period

_BALANCE = re.compile(
    r"(inventor|head\s?count|\bfte\b|employees|balance|receivable|payable|\bcash\b|\bdebt\b|backlog|"
    r"subscribers|customers|accounts\b|members|\busers\b|assets|liabilit|equity|deferred|\bwip\b|"
    r"on hand|outstanding|closing|period[- ]end|\beop\b|\baum\b|installed base|stock level)",
    re.I,
)


_RATE = re.compile(
    r"(%|\bpct\b|percent|\brate\b|\bratio\b|margin|\bmix\b|\bshare\b|\bbps\b|yield|\bprice\b|\basp\b|"
    r"average|\bavg\b|\bper\b|index|score|\bnps\b|utili[sz]ation|\bdso\b|\bdpo\b|\bdio\b|\bdays\b)",
    re.I,
)


_KINDS = {
    "flow": "flow",
    "total": "flow",
    "sum": "flow",
    "balance": "balance",
    "stock": "balance",
    "rate": "rate",
    "ratio": "rate",
    "average": "rate",
}


def _as_date(x):
    if x is None:
        return None
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    if hasattr(x, "to_pydatetime"):
        return x.to_pydatetime().date()
    t = str(x).strip()
    for cut in (10, 7):
        try:
            return _dt.date.fromisoformat(t[:cut] if cut == 10 else t[:7] + "-01")
        except ValueError:
            pass
    try:
        return parse_period(t)
    except (TypeError, ValueError, OverflowError):
        return None


def _label(d: _dt.date, freq: str) -> str:
    if freq == "MS":
        return d.strftime("%b-%y")
    if freq == "QS":
        return f"Q{(d.month - 1) // 3 + 1}-{d.strftime('%y')}"
    if freq == "YS":
        return str(d.year)
    return d.strftime("%d-%b-%y")


def _slot(d: _dt.date, freq: str, origin: _dt.date, business: bool) -> int:
    """Position of a date on the regular grid that starts at `origin`."""
    if freq == "MS":
        return (d.year - origin.year) * 12 + d.month - origin.month
    if freq == "QS":
        return (d.year - origin.year) * 4 + (d.month - 1) // 3 - (origin.month - 1) // 3
    if freq == "YS":
        return d.year - origin.year
    days = (d - origin).days
    if freq == "W":
        return int(round(days / 7.0))
    if business:
        return int(np.busday_count(origin, d))
    return days


def _slot_date(k: int, freq: str, origin: _dt.date, business: bool) -> _dt.date:
    if freq == "MS":
        m = origin.month - 1 + k
        return _dt.date(origin.year + m // 12, m % 12 + 1, 1)
    if freq == "QS":
        q = (origin.month - 1) // 3 + k
        return _dt.date(origin.year + q // 4, (q % 4) * 3 + 1, 1)
    if freq == "YS":
        return _dt.date(origin.year + k, 1, 1)
    if freq == "W":
        return origin + _dt.timedelta(days=7 * k)
    if business:
        return np.busday_offset(origin, k, roll="forward").astype(object)
    return origin + _dt.timedelta(days=k)


def _period_end(d: _dt.date, freq: str) -> _dt.date:
    """Last day of the period that starts at d."""
    if freq == "MS":
        nxt = _dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        return nxt - _dt.timedelta(days=1)
    if freq == "QS":
        m = (d.month - 1) // 3 * 3 + 3
        nxt = _dt.date(d.year + (m == 12), m % 12 + 1, 1)
        return nxt - _dt.timedelta(days=1)
    if freq == "YS":
        return _dt.date(d.year, 12, 31)
    return d


def _kind(name: str, given) -> tuple:
    if given:
        k = _KINDS.get(str(given).strip().lower())
        if k is None:
            raise ValueError(
                f"line type for {name!r} must be 'flow', 'balance' or 'rate', not {given!r}"
            )
        return k, "given"
    if _RATE.search(name):
        return "rate", "from its name"
    if _BALANCE.search(name):
        return "balance", "from its name"
    return "flow", "assumed"


MIN_GAP_TO_ASK = (
    24  # a gap of more periods than this (and three seasonal cycles) is asked about
)
MAX_LINE_PERIODS = (
    20000  # lines x periods one review analyzes inside the sandbox time limit
)


def _largest_gap(
    dates: list, freq: str, origin: _dt.date, business: bool
) -> tuple | None:
    """(date before, date after, periods missing between them) for the widest gap in the dates."""
    slots = sorted({_slot(x, freq, origin, business) for x in dates})
    if len(slots) < 2:
        return None
    widths = np.diff(slots)
    k = int(np.argmax(widths))
    if widths[k] <= 1:
        return None
    by_slot = {_slot(x, freq, origin, business): x for x in sorted(dates)}
    return by_slot[slots[k]], by_slot[slots[k + 1]], int(widths[k] - 1)


def prepare(
    series: dict,
    freq: str | None = None,
    fiscal_year_start: int | None = None,
    line_types: dict | None = None,
    today: _dt.date | None = None,
    keep_incomplete: bool = False,
    aggregate_duplicates: bool = False,
) -> dict:
    """Validate what was read and put every line on one regular time grid.

    series             {name: {"dates": [...], "values": [...]}} or {name: [values]}
    freq               the time grain if known ('monthly', 'M', 'QS', 'W', 'D' ...); worked out from the
                       dates when omitted
    fiscal_year_start  month the fiscal year starts in (1-12); January when omitted
    line_types         {name: 'flow' | 'balance' | 'rate'}; otherwise read from the line's name
    today              used to leave out a last period that has not finished (default: the current date)
    keep_incomplete    keep that unfinished last period anyway
    aggregate_duplicates  sum repeated periods only after the user confirms they are additive

    Returns {'lines', 'freq', 'grain', 'season', 'labels', 'dates', 'issues', 'questions', 'table', ...}.
    `questions` lists what cannot be settled from the data and must be asked: it is empty when nothing
    needs asking. Read `issues` out to the user before analysing.
    """
    if not series:
        raise ValueError(
            "No lines were passed in. If series_intake returned status 'needs_clarification', "
            "ask its questions and re-read before calling prepare or run."
        )
    today = today or _dt.date.today()
    issues, questions = [], []
    raw = {}
    for name, obj in series.items():
        vals = obj["values"] if isinstance(obj, dict) else obj
        dts = obj.get("dates") if isinstance(obj, dict) else None
        try:
            v = np.array(
                [
                    np.nan if x is None or (isinstance(x, str) and not x.strip()) else x
                    for x in vals
                ],
                dtype=float,
            )
        except (TypeError, ValueError):
            questions.append(
                f"{name} has a value that is not numeric. What should it be? "
                "I have not removed the row or called it a missing period."
            )
            continue
        v[~np.isfinite(v)] = np.nan
        d = [_as_date(x) for x in dts] if dts is not None else None
        if d is not None and len(d) != len(v):
            questions.append(
                f"{name} has {len(d)} dates but {len(v)} values. Which value belongs to each date? The line has not been analyzed."
            )
            continue
        if d is not None and any(x is None for x in d):
            bad = sum(1 for x in d if x is None)
            examples = [str(dts[i]) for i, x in enumerate(d) if x is None][:3]
            questions.append(
                f"{name} has {bad} unreadable or ambiguous date labels, including {_untrusted_values(examples)}. What dates do these mean? If numeric dates are day/month/year or month/day/year, confirm which and re-read the source with date_order. No rows have been dropped."
            )
            continue
        raw[str(name)] = (d, v)
    if questions:
        return {
            "status": "needs_clarification",
            "lines": {},
            "freq": None,
            "grain": {"freq": None, "confident": False, "source": "unresolved input"},
            "issues": issues,
            "questions": questions,
            "table": [],
            "skipped": [],
            "fiscal_year_start": int(fiscal_year_start or 1),
        }
    if not raw:
        raise ValueError("no usable lines: " + " ".join(issues))

    # The time grain: from the caller, else from the dates; ask when neither settles it
    dated = [d for d, _ in raw.values() if d]
    longest = max(dated, key=len) if dated else None
    given = eng.normalise_freq(freq)
    if freq and not given:
        issues.append(f"The grain {freq!r} was not recognized.")
    inferred = (
        eng.infer_grain(longest)
        if longest
        else {"freq": None, "confident": False, "why": "no dates were supplied"}
    )
    f, grain_source = given, "given"
    if given and inferred["confident"] and inferred["freq"] != given:
        issues.append(
            "The grain was given as {} but the dates are spaced like {}.".format(
                given, inferred["freq"]
            )
        )
        questions.append(
            "The data looks {} but you said {}. Which is it?".format(
                _GRAIN_WORD[inferred["freq"]], _GRAIN_WORD[given]
            )
        )
    if not given:
        f, grain_source = inferred["freq"], "from the spacing of the dates"
        if not inferred["confident"]:
            f = None
            questions.append(
                "What is the time grain of this data (daily, weekly, monthly, quarterly, or yearly)? "
                "I could not tell from the data: {}.".format(inferred["why"])
            )
    grain = {
        "freq": f,
        "source": grain_source,
        "confident": bool(given or inferred["confident"]),
        "why": inferred["why"],
    }

    out = {
        "status": "ready",
        "lines": {},
        "freq": f,
        "grain": grain,
        "issues": issues,
        "questions": questions,
        "table": [],
        "fiscal_year_start": int(fiscal_year_start or 1),
        "skipped": [],
    }
    if f is None:
        return out

    all_dates = sorted({x for d, _ in raw.values() if d for x in d})
    business = (
        f == "D"
        and bool(all_dates)
        and all(x.weekday() < 5 for x in all_dates)
        and len(all_dates) >= 10
    )
    season = 5 if business else eng.SEASON[f]
    if all_dates:
        origin = all_dates[0]
        if f in ("MS", "QS", "YS"):
            origin = _dt.date(
                origin.year,
                origin.month
                if f == "MS"
                else ((origin.month - 1) // 3 * 3 + 1 if f == "QS" else 1),
                1,
            )
        n_slots = _slot(all_dates[-1], f, origin, business) + 1
        gap = _largest_gap(all_dates, f, origin, business)
        if gap and gap[2] > max(3 * season, MIN_GAP_TO_ASK):
            out["status"] = "needs_clarification"
            questions.append(
                f"There is no data between {gap[0].isoformat()} and {gap[1].isoformat()} "
                f"({gap[2]} periods). Is one of those dates mistyped (for example the year), "
                "or should the review cover only one side of the gap? No periods have been filled in."
            )
            return out
        if n_slots > stats.MAX_QN_POINTS:
            out["status"] = "needs_clarification"
            questions.append(
                f"The regular grid spans {n_slots} periods; analysis supports at most "
                f"{stats.MAX_QN_POINTS}. Confirm a shorter window or a coarser grain. "
                "No periods have been allocated or truncated."
            )
            return out
        grid = [_slot_date(k, f, origin, business) for k in range(n_slots)]
        # a last period that has not finished cannot be an actual
        if (
            not keep_incomplete
            and n_slots > 1
            and _period_end(grid[-1], f) >= today
            and f != "D"
        ):
            issues.append(
                f"Left out {_label(grid[-1], f)}: that period had not finished on {today.isoformat()}, so it is not a complete actual."
            )
            grid = grid[:-1]
            n_slots -= 1
        labels = [_label(d, f) for d in grid]
    else:
        n_slots = max(len(v) for _, v in raw.values())
        if n_slots > stats.MAX_QN_POINTS:
            out["status"] = "needs_clarification"
            questions.append(
                f"The history has {n_slots} periods; analysis supports at most "
                f"{stats.MAX_QN_POINTS}. Confirm a shorter window or a coarser grain. "
                "No history has been truncated."
            )
            return out
        origin, grid = None, [None] * n_slots
        labels = [f"P{i + 1}" for i in range(n_slots)]
    if n_slots * len(raw) > MAX_LINE_PERIODS:
        out["status"] = "needs_clarification"
        questions.append(
            f"{len(raw)} lines of {n_slots} periods is more than one review can analyze "
            f"({MAX_LINE_PERIODS} line-periods). Which lines, or which shorter window, should be "
            "reviewed? Nothing has been dropped."
        )
        return out
    if f == "MS":
        pos0 = grid[0].month - 1 if grid and grid[0] else 0
    elif f == "QS":
        pos0 = (grid[0].month - 1) // 3 if grid and grid[0] else 0
    elif f == "D":
        pos0 = grid[0].weekday() if grid and grid[0] else 0
    else:
        pos0 = 0

    for name, (d, v) in raw.items():
        if d is None and len(v) > n_slots:
            questions.append(
                f"{name}: {len(v)} undated values exceed the {n_slots}-period dated "
                "grid. Which dates belong to this history? No values have been truncated."
            )
    if not aggregate_duplicates:
        for name, (d, _) in raw.items():
            if d is None:
                continue
            slots = [_slot(x, f, origin, business) for x in d]
            slots = [k for k in slots if 0 <= k < n_slots]
            duplicates = len(slots) - len(set(slots))
            if duplicates:
                questions.append(
                    f"{name}: {duplicates} repeated period rows. Are these additive "
                    "amounts, separate lines, or repeated export rows? Confirm before "
                    "using aggregate_duplicates=True; no values have been combined."
                )
    if questions:
        out["status"] = "needs_clarification"
        return out

    assumed = []
    for name, (d, v) in raw.items():
        arr = np.full(n_slots, np.nan)
        if d is None:
            arr[n_slots - len(v) :] = (
                v  # undated lines are aligned at the latest period
            )
        else:
            dup = 0
            for x, val in zip(d, v, strict=False):
                k = _slot(x, f, origin, business)
                if not 0 <= k < n_slots or not np.isfinite(val):
                    continue
                if np.isfinite(arr[k]):
                    arr[k] += val
                    dup += 1
                else:
                    arr[k] = val
            if dup:
                issues.append(
                    f"{name}: {dup} period{'s' if dup > 1 else ''} had more than one row; they were added together."
                )
        ok = np.isfinite(arr)
        if ok.sum() == 0:
            issues.append(f"{name}: no values, so it was skipped.")
            out["skipped"].append(name)
            continue
        kind, src = _kind(name, (line_types or {}).get(name))
        if src == "assumed":
            assumed.append(name)
        first, last = int(np.where(ok)[0][0]), int(np.where(ok)[0][-1])
        out["lines"][name] = {
            "values": arr,
            "kind": kind,
            "kind_source": src,
            "first": first,
            "last": last,
        }
        out["table"].append(
            {
                "line": name,
                "periods": int(ok.sum()),
                "first": labels[first],
                "last": labels[last],
                "last_value": float(arr[last]),
                "type": kind,
                "type_source": src,
            }
        )
        if ok.sum() < eng.MIN_POINTS:
            issues.append(
                f"{name}: only {ok.sum()} periods of history, too few to judge. It is listed but not analyzed."
            )
    lasts = {v["last"] for v in out["lines"].values()}
    if len(lasts) > 1:
        late = max(lasts)
        behind = [n for n, v in out["lines"].items() if v["last"] < late]
        issues.append(
            f"{len(behind)} line{'s' if len(behind) > 1 else ''} stop{'' if len(behind) > 1 else 's'} before {labels[late]}: {', '.join(behind[:5]) + (' ...' if len(behind) > 5 else '')}."
        )
    if assumed:
        issues.append(
            "Treated as amounts for the period (totaled over a window): %s. Say so if any of them is a balance "
            "or a rate; it changes the year-to-date and 12-month figures, not the anomalies."
            % (
                ", ".join(assumed[:6])
                + (f" and {len(assumed) - 6} more" if len(assumed) > 6 else "")
            )
        )
    if fiscal_year_start is None and f in ("MS", "QS", "W", "D"):
        issues.append("Year to date assumes the fiscal year starts in January.")
    out.update(
        {
            "labels": labels,
            "dates": grid,
            "season": season,
            "pos0": pos0,
            "business_days": business,
        }
    )
    return out


_GRAIN_WORD = {
    "D": "daily",
    "W": "weekly",
    "MS": "monthly",
    "QS": "quarterly",
    "YS": "yearly",
}
