"""
description: Write the one-page HTML dashboard of a review, with self-contained inline SVG charts and no external resources.
last_updated: 2026-11-24

One-page HTML dashboard of a review, for showing in the Quick chat as an HTML artifact.

    import series_dashboard as sd
    path = sd.write(res, out_path)   # out_path: the user's folder, else WORKSPACE_DIR/artifacts/<name>.html             # res from series_review.run
    path = sd.write(res, out_path, budget={"Cloud Hosting": {"dates": [...], "values": [...]}})   # optional

Panels: headline counts; actual against expected for each line with its events marked (one tab per line);
a heat map of how unusual every period is; trend rate against the last twelve months; only when a budget is
passed, actual against budget for the budgeted lines; and tables of every event and every data check, so the
page stands on its own without the workbook. Every figure comes from `res` (or the budget
passed in); nothing is recomputed except the budget totals. Charts are drawn as inline SVG by a short
script inside the page: no chart library, no external file and no network request. The colors come
from the Quick theme, with fallbacks so the file also opens on its own.
"""

from __future__ import annotations

import datetime as _dt
import html
import json
import math
import re
from pathlib import Path

__all__ = ["write", "build"]

TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "dashboard-template.html"
)
_PLACEHOLDER = re.compile(r"\{\{(TITLE|SUB|KPIS|TWO|TABLES|DATA)\}\}")

SCORE_CAP = (
    10.0  # heat map color scale is capped so a units slip does not wash out the rest
)


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else round(f, 4)


def _pct(v):
    v = _num(v)
    return None if v is None else round(v * 100, 2)


def _as_date(x):
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


def _line(name, ln, labels):
    d, t = ln.get("d") or {}, ln.get("trend") or {}
    vals = [_num(v) for v in ln.get("values", [])]
    exp = [_num(v) for v in d.get("expected", [None] * len(vals))]
    score = [_num(v) for v in d.get("score", [None] * len(vals))]
    events = []
    for e in ln.get("events", []):
        events.append(
            {
                "start": e["start"],
                "end": e["end"],
                "peak": e.get("peak", e["start"]),
                "period": e["period"],
                "label": e.get("type_label", e["type"]),
                "gap": _num(e.get("gap")),
                "pct": _pct(e.get("gap_pct")),
                "data": e.get("data_issue"),
                "material": bool(e.get("material")),
                "check": e.get("check", ""),
            }
        )
    # a data check inside the last 24 periods poisons the twelve-month comparison: say so rather than chart it
    n = len(vals)
    bad = sorted(
        {
            c["index"]
            for c in ln.get("checks", [])
            if c.get("check") in ("Units", "Sign reversed", "Zero value")
            and c.get("index", -1) >= n - 24
        }
    )
    ltm, ltm_chg = _pct(t.get("ltm_pct")), _num(t.get("ltm_change"))
    ltm_note = ""
    if bad and ltm is not None:
        ltm_note = "Data check in the window ({})".format(
            ", ".join(labels[i] for i in bad if i < len(labels))
        )
        ltm, ltm_chg = None, None
    return {
        "name": name,
        "kind": ln.get("kind", ""),
        "values": vals,
        "expected": exp,
        "score": [
            None if s is None else max(-SCORE_CAP, min(SCORE_CAP, s)) for s in score
        ],
        "events": events,
        "direction": t.get("direction") or "",
        "trend": _pct(t.get("trend_pct")),
        "under": _pct(t.get("underlying_pct")),
        "yoy": _pct(t.get("yoy_pct")),
        "ltm": ltm,
        "ltmchg": ltm_chg,
        "ltm_note": ltm_note,
        "last": t.get("last_period") or (labels[-1] if labels else ""),
    }


def _budget(res, budget):
    """{line: {"dates", "values"}} -> panel data on the budget's own months, actuals matched by date."""
    if not budget:
        return {}, []
    dates = [_as_date(x) for x in res.get("dates", [])]
    pos = {d: i for i, d in enumerate(dates) if d}
    months, out = None, {}
    for name, b in budget.items():
        if name not in res["lines"]:
            continue
        bd = [_as_date(x) for x in b.get("dates", [])]
        bv = [_num(v) for v in b.get("values", [])]
        act = [res["lines"][name]["values"][pos[d]] if d in pos else None for d in bd]
        act = [_num(v) for v in act]
        ya = sum(
            a for a, x in zip(act, bv, strict=False) if a is not None and x is not None
        )
        yb = sum(
            x for a, x in zip(act, bv, strict=False) if a is not None and x is not None
        )
        out[name] = {
            "actual": act,
            "budget": bv,
            "ytd_actual": round(ya, 4),
            "ytd_budget": round(yb, 4),
            "var": round(ya - yb, 4),
            "var_pct": round((ya - yb) / abs(yb) * 100, 2) if yb else None,
        }
        months = months or [d.strftime("%b-%y") if d else "" for d in bd]
    return out, months or []


def build(res: dict, budget: dict | None = None, title: str | None = None) -> str:
    """The dashboard as one HTML string."""
    labels = list(res.get("labels", []))
    lines = [_line(n, ln, labels) for n, ln in res["lines"].items()]
    bud, bmonths = _budget(res, budget)
    st = res.get("settings", {})
    ev = res.get("events", [])
    mat = [e for e in ev if e.get("material")]
    biz = [e for e in mat if not e.get("data_issue")]
    dirs = [litem["direction"] for litem in lines if litem["direction"]]
    source = st.get("source_file") or ""
    units = st.get("units") or "units not stated"
    span = f"{labels[0]} to {labels[-1]}" if labels else ""
    n_mat_lines = len({e["line"] for e in mat})
    mat_line_plural = "" if n_mat_lines == 1 else "s"
    kpis = [
        (
            "Material anomalies",
            str(len(mat)),
            f"on {n_mat_lines} line{mat_line_plural}, at or above {_thr(st)}",
            "",
        ),
        (
            "Data checks to confirm",
            str(len(res.get("data_checks", []))),
            "confirm these at the source first",
            "warn",
        ),
        (
            "Trend direction",
            f"{dirs.count('Rising')} ↑ · {dirs.count('Flat')} → · {dirs.count('Falling')} ↓",
            "rising · broadly flat · falling",
            "",
        ),
    ]
    if bud:
        big = max(bud.items(), key=lambda kv: abs(kv[1]["var_pct"] or 0))
        kpis.append(
            (
                f"{big[0]} against budget",
                _sgn(big[1]["var_pct"]) + "%",
                "{}{} year to date".format(
                    "+" if big[1]["var"] > 0 else "", "{:,.1f}".format(big[1]["var"])
                ),
                "err",
            )
        )
    elif biz:
        top = max(biz, key=lambda e: abs(e.get("gap") or 0))
        kpis.append(
            (
                "Largest business event",
                _sgn(_pct(top.get("gap_pct"))) + "%",
                "{}, {}: {}".format(
                    top["line"], top["period"], top.get("type_label", "")
                ),
                "err",
            )
        )
    else:
        kpis.append(
            ("Business events", "0", "nothing stands out beyond data checks", "")
        )
    data = {
        "labels": labels,
        "units": units,
        "z": _num(st.get("z_threshold")) or 3.5,
        "cap": SCORE_CAP,
        "lines": lines,
        "budget": bud,
        "bmonths": bmonths,
    }
    payload = (
        json.dumps(data, separators=(",", ":"), allow_nan=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    head = title or f"What moved, {span}"
    sub = " · ".join(
        x
        for x in [
            source,
            (f"{len(lines)} {st.get('grain_word', '')} lines").replace("  ", " "),
            units,
            "expected values come from each line's own history",
        ]
        if x
    )
    k_html = "".join(
        f'<div class="kpi"><div class="l">{html.escape(a)}</div><div class="v {c}">{html.escape(b)}</div><div class="d">{html.escape(d)}</div></div>'
        for a, b, d, c in kpis
    )
    bud_html = BUDGET_CARD if bud else ""
    trend_html = (
        TREND_CARD if any(litem["trend"] is not None for litem in lines) else ""
    )
    two = (
        f'<div class="two">{trend_html}{bud_html}</div>'
        if (trend_html and bud_html)
        else (trend_html or bud_html)
    )
    parts = {
        "TITLE": html.escape(head),
        "SUB": html.escape(sub),
        "KPIS": k_html,
        "TWO": two,
        "TABLES": _tables(res),
        "DATA": payload,
    }
    # one pass, so text from the user's file that looks like a placeholder is never filled in
    return _PLACEHOLDER.sub(lambda m: parts[m.group(1)], _template())


def _tables(res):
    st = res.get("settings", {})
    ev = sorted(
        res.get("events", []),
        key=lambda e: (not e.get("material"), -abs(e.get("gap") or 0)),
    )

    def f(v, d=1):
        return "" if v is None else "{:+,.{d}f}".format(v, d=d)

    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td class=n>{}</td><td class=n>{}</td><td class=n>{}</td><td>{}</td><td class=w>{}</td></tr>".format(
            html.escape(e["line"]),
            html.escape(e["period"]),
            html.escape(e.get("type_label", e["type"])),
            f(_num(e.get("gap"))),
            ""
            if _num(e.get("gap_pct")) is None or abs(e["gap_pct"]) >= 10
            else f(e["gap_pct"] * 100) + "%",
            f(_num(e.get("total_gap"))),
            "Yes" if e.get("material") else "No",
            html.escape(e.get("check", "")),
        )
        for e in ev
    )
    out = (
        '<div class="card"><h2>Events</h2><p class="note">Every period that does not fit its line\'s own pattern, '
        f"material ones first, largest amount first. Material = at or above {html.escape(_thr(st))}.</p>"
    )
    out += (
        (
            '<div class="tw"><table><tr><th>Line</th><th>Period</th><th>Type</th><th>Gap</th><th>Gap %</th>'
            f"<th>Total over event</th><th>Material?</th><th>What to check</th></tr>{rows}</table></div>"
        )
        if ev
        else '<p class="note">No period stands out from its line\'s own pattern.</p>'
    )
    out += "</div>"
    ck = res.get("data_checks", [])
    if ck:
        out += (
            '<div class="card"><h2>Data checks</h2><p class="note">Confirm these at the source before reading '
            'anything into the events.</p><div class="tw"><table><tr><th>Line</th><th>Period</th><th>Check</th>'
            "<th>Detail</th></tr>{}</table></div></div>".format(
                "".join(
                    "<tr><td>{}</td><td>{}</td><td>{}</td><td class=w>{}</td></tr>".format(
                        html.escape(c.get("line", "")),
                        html.escape(c.get("period", "")),
                        html.escape(c.get("check", "")),
                        html.escape(c.get("detail", "")),
                    )
                    for c in ck
                )
            )
        )
    return out


def write(
    res: dict,
    out_path: str,
    budget: dict | None = None,
    title: str | None = None,
    overwrite: bool = False,
) -> str:
    """Write the dashboard and return its path. An existing file is replaced only with overwrite=True."""
    path = Path(out_path)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"{path} already exists. Choose another name, or pass overwrite=True only "
            "to replace a dashboard this review wrote."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    page = build(res, budget=budget, title=title)
    with path.open("w" if overwrite else "x", encoding="utf-8", newline="\n") as f:
        f.write(page)
    return out_path


def _thr(st):
    p, a = st.get("min_gap_pct"), st.get("min_gap_amount")
    s = f"{p:.0%}" if p else ""
    if a:
        s += (
            f" {'and' if st.get('threshold_rule', 'both') == 'both' else 'or'} "
            if s
            else ""
        ) + f"{a:,.0f}"
    return s or "the threshold"


def _sgn(v):
    return "n/a" if v is None else ("+" if v > 0 else "") + f"{v:.1f}"


TREND_CARD = """<div class="card"><h2>Trend rate against last twelve months</h2>
<p class="note">Trend: the underlying annual rate, with unusual periods set aside. Last 12 months: against the
12 before. Faded bars are lines that are broadly flat.</p><div id="trend" style="height:330px"></div></div>"""

BUDGET_CARD = """<div class="card"><h2>Actual against budget</h2>
<p class="note">Bars are actuals; the dashed line is the budget, including months not yet reported.</p>
<div class="tabs" id="btabs"></div><div id="bud" style="height:290px"></div></div>"""


def _template() -> str:
    """The page template in assets/: HTML, CSS and the inline chart script, with {{...}} placeholders."""
    return TEMPLATE_PATH.read_text(encoding="utf-8")
