"""
description: Build the single standalone HTML scenario report with inline SVG charts (no chart library, no external files, no network).
last_updated: 2026-11-24

Sections in order: data limitations; hero P(hit target) and KPI strip; Monte Carlo distribution (largest visual)
with Bear/Base/Bull markers, target line and shaded band; Bull and Bear trend line; variance waterfall; sensitivity tornado; percentile
stack-rank with What has to be true; Areas to Probe; supporting tables (build-up, assumptions, context, appendix).
Called through scenario_engine.write_report(res, out_path).
"""

from __future__ import annotations

import html
import math
import os
import re

C = {
    "text": "#131920",
    "sec": "#5e5e5e",
    "muted": "#656871",
    "grid": "#e6e6ea",
    "card": "#ffffff",
    "bg": "#faf9fc",
    "base": "#4338ca",
    "bull": "#00802f",
    "bear": "#db0000",
    "band": "rgba(67,56,202,0.12)",
    "target": "#d97706",
    "bar": "#9aa0b5",
    "up": "#00802f",
    "down": "#db0000",
    "total": "#4338ca",
}
E = html.escape


def _scenario_labels(res):
    if res.get("target_direction") == "at_most":
        return {"bear": "Low case", "base": "Median", "bull": "High case"}
    return {"bear": "Bear", "base": "Base", "bull": "Bull"}


def _n(v, signed=False):
    if v is None:
        return "n/a"
    a = abs(v)
    s = (
        format(v / 1e9, ",.2f") + "B"
        if a >= 1e9
        else format(v / 1e6, ",.2f") + "M"
        if a >= 1e6
        else format(v / 1e3, ",.1f") + "K"
        if a >= 1e4
        else format(v, ",.0f")
    )
    return "+" + s if signed and v > 0 else s


MAX_TICKS = 50


def _ticks(lo, hi, n=5):
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return []
    # widen a range too narrow for float steps at this magnitude, so the loop always advances
    if not hi > lo:
        hi = lo + 1
    hi = max(hi, lo + abs(lo) * 1e-9)
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    f = raw / mag
    st = (1 if f < 1.5 else 2 if f < 3 else 5 if f < 7 else 10) * mag
    v, out = math.ceil(lo / st - 1e-9) * st, []
    while v <= hi + st * 1e-9 and len(out) < MAX_TICKS:
        out.append(round(v, 10))
        v += st
    return out


def _t(x, y, s, fill=None, anchor="start", size=11, weight=None):
    weight_attr = f' font-weight="{weight}"' if weight else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill or C["sec"]}" '
        f'font-size="{size}" text-anchor="{anchor}"{weight_attr}>{E(str(s))}</text>'
    )


def _r(x, y, w, h, fill, title=None, rx=0):
    return '<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" fill="{}" rx="{}">{}</rect>'.format(
        x,
        y,
        max(0, w),
        max(0, h),
        fill,
        rx,
        f"<title>{E(title)}</title>" if title else "",
    )


def _l(x1, y1, x2, y2, c, w=1, dash=None):
    return '<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="{}"{}/>'.format(
        x1, y1, x2, y2, c, w, f' stroke-dasharray="{dash}"' if dash else ""
    )


def _svg(w, h, label, body):
    return f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{E(label)}">{body}</svg>'


def distribution(res):
    labels = _scenario_labels(res)
    h, W, H, m = res["histogram"], 900, 360, {"l": 60, "r": 20, "t": 30, "b": 50}
    pw, ph = W - m["l"] - m["r"], H - m["t"] - m["b"]
    e, c = h["edges"], h["counts"]
    lo, hi, top = e[0], e[-1], max(c) or 1
    span = (hi - lo) or 1

    def X(v):
        return m["l"] + (v - lo) / span * pw

    def Y(k):
        return m["t"] + ph - k / top * ph

    g = _r(
        X(res["bear"]),
        m["t"],
        X(res["bull"]) - X(res["bear"]),
        ph,
        C["band"],
        f"{labels['bear']} to {labels['bull']} band",
    )
    for i, k in enumerate(c):
        x0, x1 = X(e[i]), X(e[i + 1])
        g += _r(
            x0 + 0.5,
            Y(k),
            x1 - x0 - 1,
            m["t"] + ph - Y(k),
            C["bar"],
            f"{_n(e[i])} to {_n(e[i + 1])}: {k} runs",
        )
    g += _l(m["l"], m["t"] + ph, W - m["r"], m["t"] + ph, C["grid"])
    for v in _ticks(lo, hi, 6):
        if lo <= v <= hi:
            g += _t(X(v), m["t"] + ph + 16, _n(v), anchor="middle")
    pl = res["percentile_labels"]
    for key, col in (("bear", C["bear"]), ("base", C["base"]), ("bull", C["bull"])):
        x = X(res[key])
        g += _l(x, m["t"], x, m["t"] + ph, col, 2) + _t(
            x,
            m["t"] - 8,
            f"{labels[key]} P{int(pl[key])} {_n(res[key])}",
            col,
            "middle",
            11,
            600,
        )
    if lo <= res["target"] <= hi:
        x = X(res["target"])
        g += _l(x, m["t"], x, m["t"] + ph, C["target"], 2, "6,4") + _t(
            x + 4, m["t"] + 14, "Target " + _n(res["target"]), C["target"]
        )
    g += _t(
        m["l"] + pw / 2,
        H - 10,
        "Simulated {} in {} ({} runs)".format(
            res["outcome_label"],
            res.get("units") or "Units not supplied",
            format(res["iterations"], ","),
        ),
        C["muted"],
        "middle",
    )
    return _svg(W, H, "Monte Carlo distribution of outcomes", g)


def trend_line(res):
    labels = _scenario_labels(res)
    p, W, H, m = res["per_period"], 900, 320, {"l": 64, "r": 20, "t": 20, "b": 56}
    pw, ph, n = W - m["l"] - m["r"], H - m["t"] - m["b"], len(p["labels"])
    vals = [
        v
        for k in ("actual", "bear", "base", "bull", "benchmark")
        for v in p.get(k, [])
        if v is not None
    ]
    if not vals or n == 0:
        return "<p class=note>No periods to chart.</p>"
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.08 or abs(hi) * 0.1 or 1
    lo, hi = lo - pad, hi + pad

    def X(i):
        return m["l"] + (i + 0.5) * pw / n

    def Y(v):
        return m["t"] + ph - (v - lo) / (hi - lo) * ph

    def path(series, col, w=2, dash=None):
        d, pen = "", False
        for i, v in enumerate(series):
            if v is None:
                pen = False
                continue
            d += ("L" if pen else "M") + f"{X(i):.1f},{Y(v):.1f}"
            pen = True
        return '<path d="{}" fill="none" stroke="{}" stroke-width="{}"{}/>'.format(
            d,
            col,
            w,
            f' stroke-dasharray="{dash}"' if dash else "",
        )

    g = ""
    for v in _ticks(lo, hi):
        if lo <= v <= hi:
            g += _l(m["l"], Y(v), W - m["r"], Y(v), C["grid"]) + _t(
                m["l"] - 6, Y(v) + 4, _n(v), anchor="end"
            )
    nh = p["n_hist"]
    fut = [i for i in range(nh, n) if p["bear"][i] is not None]
    if fut:
        anchor = [(nh - 1, p["actual"][nh - 1])] if nh else []
        up = anchor + [(i, p["bull"][i]) for i in fut]
        dn = [(i, p["bear"][i]) for i in reversed(fut)] + anchor
        g += '<path d="M{} Z" fill="{}"/>'.format(
            " L".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in up + dn),
            C["band"],
        )
    step = max(1, n // 12)
    for i, lab in enumerate(p["labels"]):
        if i % step == 0:
            g += _t(X(i), m["t"] + ph + 16, lab, anchor="middle", size=10)

    def link(k):
        return [None] * (nh - 1) + [p["actual"][nh - 1]] + p[k][nh:] if nh else p[k]

    if p.get("benchmark"):
        g += path(
            p["benchmark"] + [None] * (n - len(p["benchmark"])), C["target"], 1.5, "6,4"
        )
    g += (
        path(link("bear"), C["bear"], 2)
        + path(link("bull"), C["bull"], 2)
        + path(link("base"), C["base"], 2.5, "5,3")
    )
    g += path(p["actual"], C["text"], 2.5)
    items = [
        ("Actual", C["text"]),
        (labels["base"], C["base"]),
        (labels["bull"], C["bull"]),
        (labels["bear"], C["bear"]),
    ] + ([("Benchmark", C["target"])] if p.get("benchmark") else [])
    x = W / 2 - len(items) * 45
    for name, col in items:
        g += _l(x, H - 14, x + 18, H - 14, col, 2.5) + _t(x + 24, H - 10, name)
        x += 90
    return _svg(
        W,
        H,
        f"Actuals and {labels['bull']}, {labels['base']} and {labels['bear']} by period",
        g,
    )


def waterfall(res):
    b, W, H, m = res["bridge"], 900, 320, {"l": 64, "r": 20, "t": 24, "b": 70}
    pw, ph, n = W - m["l"] - m["r"], H - m["t"] - m["b"], len(b)
    run, bars = 0.0, []
    for s in b:
        if s["kind"] == "total":
            bars.append((s["label"], 0.0, s["value"], C["total"], s["value"]))
            run = s["value"]
        else:
            bars.append(
                (
                    s["label"],
                    run,
                    run + s["value"],
                    C["up"] if s["value"] >= 0 else C["down"],
                    s["value"],
                )
            )
            run += s["value"]
    vals = [v for _, a, z, _, _ in bars for v in (a, z)] + [0]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.08 or 1
    lo, hi = (lo - pad if lo < 0 else 0), hi + pad

    def Y(v):
        return m["t"] + ph - (v - lo) / (hi - lo) * ph

    bw = pw / n
    g = ""
    for v in _ticks(lo, hi):
        if lo <= v <= hi:
            g += _l(m["l"], Y(v), W - m["r"], Y(v), C["grid"]) + _t(
                m["l"] - 6, Y(v) + 4, _n(v), anchor="end"
            )
    for i, (lab, a, z, col, val) in enumerate(bars):
        x = m["l"] + i * bw + bw * 0.15
        top_, bot = Y(max(a, z)), Y(min(a, z))
        g += _r(
            x,
            top_,
            bw * 0.7,
            max(1, bot - top_),
            col,
            f"{lab}: {_n(val, True)}",
            3,
        )
        g += _t(
            x + bw * 0.35,
            top_ - 5,
            _n(val, col != C["total"]),
            anchor="middle",
            size=11,
            weight=600,
        )
        words, line, rows = lab.split(), "", []
        for w in words:
            if len(line) + len(w) > 16:
                rows.append(line)
                line = w
            else:
                line = (line + " " + w).strip()
        rows.append(line)
        for k, r in enumerate(rows[:3]):
            g += _t(
                x + bw * 0.35, m["t"] + ph + 16 + k * 13, r, anchor="middle", size=10
            )
    return _svg(
        W, H, f"Variance bridge to the {_scenario_labels(res)['base']} scenario", g
    )


def tornado(res):
    t = res["tornado"]
    if not t:
        return "<p class=note>No assumptions with a range to test.</p>"
    W, rowh = 900, 30
    H = len(t) * rowh + 60
    m = {"l": 300, "r": 40, "t": 10, "b": 40}
    pw = W - m["l"] - m["r"]
    lo = min(min(x["low"] for x in t), res["expected"])
    hi = max(max(x["high"] for x in t), res["expected"])
    pad = (hi - lo) * 0.05 or 1
    lo, hi = lo - pad, hi + pad

    def X(v):
        return m["l"] + (v - lo) / (hi - lo) * pw

    g = ""
    for i, x in enumerate(t):
        y = m["t"] + i * rowh
        g += _t(m["l"] - 8, y + rowh / 2 + 4, x["label"][:48], anchor="end")
        g += _r(
            X(x["low"]),
            y + 5,
            X(res["expected"]) - X(x["low"]),
            rowh - 10,
            C["down"],
            "Low end: {}".format(_n(x["low"])),
            2,
        )
        g += _r(
            X(res["expected"]),
            y + 5,
            X(x["high"]) - X(res["expected"]),
            rowh - 10,
            C["up"],
            "High end: {}".format(_n(x["high"])),
            2,
        )
    ex = X(res["expected"])
    g += _l(ex, m["t"], ex, m["t"] + len(t) * rowh, C["text"], 1.5)
    for v in _ticks(lo, hi, 6):
        if lo <= v <= hi:
            g += _t(X(v), H - 22, _n(v), anchor="middle")
    g += _t(ex, H - 6, "Expected outcome " + _n(res["expected"]), C["muted"], "middle")
    return _svg(W, H, "Sensitivity tornado", g)


def _table(head, rows):
    return "<table><tr>{}</tr>{}</table>".format(
        "".join(f"<th>{E(h)}</th>" for h in head),
        "".join(
            "<tr>{}</tr>".format("".join(f"<td>{E(str(c))}</td>" for c in r))
            for r in rows
        ),
    )


def build(res, title=None):
    pl = res["percentile_labels"]
    labels = _scenario_labels(res)
    units = res.get("units") or "Units not supplied"
    head = title or "Scenario estimate: {} through {}".format(
        res["outcome_label"],
        res["per_period"]["labels"][-1] if res["per_period"]["labels"] else "",
    )
    head += " (" + units + ")"

    def kpi(litem, v, d=""):
        return f'<div class="kpi"><div class="l">{E(litem)}</div><div class="v">{E(v)}</div><div class="d">{E(d)}</div></div>'

    kpis = (
        kpi(f"{labels['base']} P{int(pl['base'])}", _n(res["base"]), units)
        + kpi(f"{labels['bull']} P{int(pl['bull'])}", _n(res["bull"]), units)
        + kpi(f"{labels['bear']} P{int(pl['bear'])}", _n(res["bear"]), units)
        + (
            kpi("Benchmark", _n(res["benchmark_fy"]), units)
            if res["benchmark_fy"] is not None
            else kpi("Benchmark", "No full-year benchmark")
        )
    )
    band = (
        f"In {int(res['band'])}% of simulated runs the outcome is between "
        f"{_n(res['bear'])} ({labels['bear']}) and "
        f"{_n(res['bull'])} ({labels['bull']})."
    )
    lim = (
        "".join(f"<li>{E(x)}</li>" for x in res["limitations"])
        or "<li>None found.</li>"
    )

    def against_benchmark(v):
        return (
            _n(v - res["benchmark_fy"], True)
            if res["benchmark_fy"] is not None
            else "n/a"
        )

    pct_rows = [
        [f"P{p}", _n(res["percentiles"][p]), against_benchmark(res["percentiles"][p])]
        for p in (10, 25, 50, 75, 90)
    ]
    if res.get("mean") is not None:
        pct_rows.append(["Mean", _n(res["mean"]), against_benchmark(res["mean"])])
    wht = res["what_has_to_be_true"]

    def wl(k):
        return (
            "".join(f"<li>{E(x)}</li>" for x in wht[k])
            or "<li>No assumption has a range to test.</li>"
        )

    probes = (
        "".join(
            "<li><b>{}</b> {}</li>".format(E(p["priority"]), E(p["item"]))
            for p in res["areas_to_probe"]
        )
        or "<li><b>P3</b> No open items found; review the assumptions table.</li>"
    )
    bu = [
        [
            labels.get(k.lower(), k),
            _n(v["ytd_or_opening"]),
            _n(v["trend"]),
            _n(v["drivers"]),
            _n(v["judgment"]),
            _n(v["expected"]),
            _n(v["deviation"], True),
            _n(v["scenario"]),
        ]
        for k, v in res["buildup"].items()
    ]
    asm = [
        [
            a["name"],
            (
                f"{labels['bear']} P{pl['bear']}, {labels['base']} P{pl['base']}, "
                f"{labels['bull']} P{pl['bull']}"
            )
            if a["name"] == "Scenario percentiles"
            else a["value"],
            a["label"] + (" ({})".format(a["source"]) if a.get("source") else ""),
        ]
        for a in res["assumptions"]
    ]
    ctx = ""
    if res["context_findings"]:
        ctx = '<div class="card"><h2>External context</h2>{}</div>'.format(
            _table(
                ["Source", "Claim", "Affects"],
                [
                    [c.get("source", ""), c.get("claim", ""), c.get("affects", "")]
                    for c in res["context_findings"]
                ],
            )
        )
    audit = res.get("input_audit", {})
    if audit:
        ctx += '<div class="card"><h2>Basis of review</h2>{}</div>'.format(
            _table(
                ["Input", "Value"],
                [
                    ["Units", units],
                    [
                        "Number format",
                        "1,234.5 (comma groups thousands, point marks decimals); "
                        "K = thousand, M = million, B = billion",
                    ],
                    [
                        "Source file and sheet",
                        os.path.basename(str(audit.get("source", "working table")))
                        + " / "
                        + str(audit.get("sheet", "")),
                    ],
                    ["Header source row", audit.get("header_row", "provided table")],
                    ["Included data rows", audit.get("included_rows", "")],
                    ["Title rows", str(audit.get("title_source_rows", []))],
                    [
                        "Excluded source rows",
                        str(audit.get("excluded_source_rows", [])),
                    ],
                    ["Column mapping", str(audit.get("column_map", {}))],
                    [
                        "Date order",
                        audit.get("date_order") or "unambiguous source dates",
                    ],
                ],
            )
        )
    p = res["per_period"]
    app = [
        [
            p["labels"][i],
            _n(p["actual"][i]),
            _n(p["bear"][i]),
            _n(p["base"][i]),
            _n(p["bull"][i]),
        ]
        for i in range(len(p["labels"]))
    ]
    html = _fill(
        TEMPLATE,
        title=E(head),
        units=E(units),
        current=E(res["current_period"]),
        phit=f"{round(res['p_hit'] * 100)}%",
        target=E(_n(res["target"])),
        direction=E(
            "at most" if res.get("target_direction") == "at_most" else "at least"
        ),
        tsrc=E(res["target_source"]),
        runs=E(format(res["iterations"], ",")),
        kpis=kpis,
        band=E(band),
        lim=lim,
        dist=distribution(res),
        trend=trend_line(res),
        bridge=waterfall(res),
        tornado=tornado(res),
        pct=_table(
            ["Percentile", "Outcome (" + units + ")", "Against benchmark"], pct_rows
        ),
        bull=wl("bull"),
        bear=wl("bear"),
        bull_label=E(labels["bull"]),
        bear_label=E(labels["bear"]),
        base_label=E(labels["base"]),
        probes=probes,
        buildup=_table(
            [
                "Scenario",
                "Year-to-date actual or opening",
                "Trend + seasonality",
                "Drivers",
                "Judgment",
                "Expected",
                "Distribution deviation",
                "Scenario value",
            ],
            bu,
        ),
        assumptions=_table(["Assumption", "Value", "Provenance"], asm),
        context=ctx,
        appendix=_table(
            ["Period", "Actual", labels["bear"], labels["base"], labels["bull"]], app
        ),
        disclaimer=(
            "These figures are estimates from your own data and stated assumptions, not predictions. "
            "Outputs are informational and are not accounting or financial advice. Validate them with a "
            "qualified accountant or finance controller before distributing or acting on them."
        ),
    )
    return html


_PLACEHOLDER = re.compile(r"\{\{|\}\}|\{([a-z_]+)\}")


def _fill(template, **values):
    """Fill {name} placeholders in one pass, so braces in CSS and in user text are left alone.
    Doubled braces {{ }} in the template become single braces; inserted values are never rescanned."""

    def swap(m):
        token = m.group(0)
        if token in ("{{", "}}"):
            return token[0]
        return str(values[m.group(1)]) if m.group(1) in values else token

    return _PLACEHOLDER.sub(swap, template)


REPORT_SUFFIX = ".html"


def write(res, out_path, title=None, overwrite=False):
    """Write the report to a new .html file; replace an existing file only when overwrite is True."""
    if not str(out_path).lower().endswith(REPORT_SUFFIX):
        raise ValueError(f"The report path must end in {REPORT_SUFFIX}.")
    if os.path.exists(out_path) and not overwrite:
        raise FileExistsError(
            f"{os.path.basename(out_path)} already exists. Confirm with the user before replacing it."
        )
    d = os.path.dirname(out_path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(
        out_path, "w" if overwrite else "x", encoding="utf-8", newline="\n"
    ) as fh:
        fh.write(build(res, title))
    return out_path


def check_page(page: str, units: str) -> dict:
    """Where the confirmed unit label appears in a built report, so the agent checks the file without
    reading it into the conversation."""
    label = E(units)
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    hero = re.search(r'<div class="hero">(.*?)</div></div></div>', page, re.S)
    kpis = re.search(r'<div class="kpis">(.*?)</div>\n', page, re.S)
    basis = re.search(r"<h2>Basis of review</h2>(.*?)</table>", page, re.S)
    return {
        "title": bool(title and label in title.group(1)),
        "target_headline": bool(hero and label in hero.group(1)),
        "scenario_metrics": bool(kpis and label in kpis.group(1)),
        "basis_of_review": bool(basis and label in basis.group(1)),
        "units_missing_fallback": "Units not supplied" in page,
        "bytes": len(page.encode("utf-8")),
    }


def check(out_path: str, units: str) -> dict:
    """Read a written report and report where the unit label appears (see check_page)."""
    with open(out_path, encoding="utf-8") as fh:
        return check_page(fh.read(), units)


TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{title}</title>
<style>
body{{background:#faf9fc;color:#131920;font-family:"Amazon Ember","Helvetica Neue","Segoe UI",Roboto,Arial,sans-serif;margin:0;padding:22px 26px 34px}}
h1{{font-size:20px;margin:0 0 4px}}h2{{font-size:15px;margin:0 0 6px}}.sub,.note{{color:#5e5e5e;font-size:12px}}
.hero{{display:flex;gap:22px;align-items:center;background:#fff;border:1px solid #0000000f;border-radius:10px;padding:16px 20px;margin:14px 0}}
.hero .big{{font-size:56px;font-weight:700;color:#4338ca;line-height:1}}.hero .cap{{font-size:13px;color:#5e5e5e}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}}
.kpi,.card{{background:#fff;border:1px solid #0000000f;border-radius:10px;padding:12px 16px}}
.kpi .l{{font-size:11px;color:#656871;text-transform:uppercase;letter-spacing:.05em}}.kpi .v{{font-size:22px;font-weight:600;margin:4px 0}}
.card{{margin-bottom:14px}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
table{{border-collapse:collapse;width:100%;font-size:12px}}th{{text-align:left;color:#656871;border-bottom:1px solid #0000001f;padding:5px 8px}}
td{{border-bottom:1px solid #0000000f;padding:5px 8px}}li{{font-size:13px;margin:3px 0}}svg{{display:block;font-family:inherit}}
.disc{{font-size:11px;color:#656871;margin-top:18px}}
@media(max-width:820px){{.kpis,.two{{grid-template-columns:1fr 1fr}}}}
</style></head><body>
<h1>{title}</h1>
<p class="sub"><b>Forecast and target units: {units}</b></p>
<div class="sub">Current period (from the data): {current}</div>
<div class="card"><h2>Data limitations</h2><ul>{lim}</ul></div>
<div class="hero"><div class="big">{phit}</div><div><b>Estimated probability of an outcome {direction} {target} {units}</b><div class="cap">Share of {runs} simulated runs, an estimate from your data and stated assumptions, not a prediction. Target: {tsrc}. {band}</div></div></div>
<div class="kpis">{kpis}</div>
<div class="card"><h2>Monte Carlo distribution</h2><p class="note">{band}</p>{dist}</div>
<div class="card"><h2>Trend: {bull_label} and {bear_label}</h2><p class="note">Actuals, then one simulated run for each of {bear_label}, {base_label} and {bull_label}, chosen so its periods add up to that scenario's outcome. Each line is a single coherent path, not a per-period percentile.</p>{trend}</div>
<div class="card"><h2>Variance bridge</h2><p class="note">From the benchmark (or the year-to-date actual when there is no full-year benchmark) to the {base_label} scenario, one step per component.</p>{bridge}</div>
<div class="card"><h2>Sensitivity: what moves the number most</h2><p class="note">Each assumption moved across its range on its own, largest swing at the top.</p>{tornado}</div>
<div class="two"><div class="card"><h2>Percentile stack-rank</h2>{pct}</div>
<div class="card"><h2>What has to be true</h2><b>{bull_label}</b><ul>{bull}</ul><b>{bear_label}</b><ul>{bear}</ul></div></div>
<div class="card"><h2>Areas to probe</h2><ul>{probes}</ul></div>
<div class="card"><h2>Scenario build-up</h2>{buildup}</div>
<div class="card"><h2>Assumptions</h2>{assumptions}</div>
{context}
<div class="card"><h2>Appendix: by period</h2>{appendix}</div>
<p class="disc">{disclaimer}</p>
</body></html>
"""
