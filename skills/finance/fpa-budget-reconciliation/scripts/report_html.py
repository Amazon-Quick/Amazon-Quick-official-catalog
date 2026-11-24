"""
description: Pure HTML builder for create_report.py: the headline sentence and the self-contained one-page report.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math
from datetime import date

from report_format import (
    AVAILABLE_INK,
    CHAR_W,
    INK,
    KIND_LABELS,
    MAX_INSPECT_ROWS,
    MAX_VARIANCE_BARS,
    MUTED,
    OPEN,
    OVER,
    PENDING,
    RULE,
    SPENT,
    UNDER,
    esc,
    inspect_items,
    money,
    month_label,
    pct,
    signed_money,
    text_width,
)
from report_style import report_css


class HeadlineWriter:
    """Writes the one-sentence finding that heads the report and the workbook."""

    def __init__(self, result: dict, markup: bool) -> None:
        self.r = result
        self.markup = markup

    def write(self) -> str:
        t = self.r["totals"]
        s = esc(self.r["currency_symbol"]) if self.markup else self.r["currency_symbol"]
        w = self.r["window"]
        b, eb = ("<b>", "</b>") if self.markup else ("", "")
        n_inspect = inspect_items(self.r)
        through = month_label(w["last_closed"], True)
        var = t["var_ytd"]
        if t["plan_ytd"] and abs(var) / abs(t["plan_ytd"]) < 0.005:
            first = (
                f"Spend is on plan through {through} at {money(s, t['actual_ytd'])}."
            )
        else:
            word = "over" if var > 0 else "under"
            first = f"Spend is {b}{money(s, abs(var))} ({pct(t['var_pct_ytd']).lstrip('+-')}) {word}{eb} plan through {through}."
        committed = t["pending"] + t["open_commitments"]
        no_docs = self.r["linkage"]["method"] == "none" and not self.r["invoices"]
        if no_docs:
            second = f" No purchase orders or invoices were supplied, so {b}{money(s, t['available'])}{eb} of the {money(s, t['plan_fy'])} full-year budget is left after actuals alone"
        elif t["available"] >= 0:
            second = f" With {money(s, committed)} pending or on order, {b}{money(s, t['available'])}{eb} of the {money(s, t['plan_fy'])} full-year budget is uncommitted"
        else:
            second = f" With {money(s, committed)} pending or on order, the full-year budget of {money(s, t['plan_fy'])} is {b}committed {money(s, -t['available'])} beyond{eb}"
        tail = (
            f", and {b}{n_inspect} item{'s' if n_inspect != 1 else ''}{eb} need{'s' if n_inspect == 1 else ''} inspection."
            if n_inspect
            else ", and nothing crosses the inspection thresholds."
        )
        return first + second + tail


class HtmlReportBuilder:
    """Assembles the one-page report as a self-contained HTML string."""

    def __init__(self, result: dict, workbook_name: str) -> None:
        self.r = result
        self.workbook_name = workbook_name
        self.s = esc(result["currency_symbol"])

    def build(self) -> str:
        r = self.r
        t = r["totals"]
        w = r["window"]
        inspect = [f for f in r["flags"] if f["tier"] == "inspect"]
        title = esc(r["name"])
        meta = f"Through {month_label(w['last_closed'], True)} &middot; {esc(r['reporting_currency'])} &middot; plan year {month_label(w['horizon_start'])} {w['horizon_start'][:4]} to {month_label(w['horizon_end'])} {w['horizon_end'][:4]} &middot; as of {self._as_of()}"
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{self._css()}</style></head>
<body><main class="sheet">
{self._notice_banner()}<header class="top"><h1>{title}</h1><p class="meta">{meta}</p></header>
<section class="kpis" aria-label="Headline metrics">{self._kpis()}</section>
<div class="walk">{self._walk_svg()}</div>
<p class="headline">{HeadlineWriter(self.r, True).write()}</p>
<section class="block"><div class="bhead"><h2>{self._table_title()}</h2>{self._table_tools()}</div>{self._budget_table()}</section>
<section class="row1">
  <div class="panel inspect"><h2>Needs inspection <span class="count">{self._inspect_count()}</span></h2>{self._inspect_list(inspect)}</div>
  <div class="panel"><h2>Variance to plan by month</h2>{self._monthly_svg()}</div>
</section>
<section class="row2">
  <div class="panel"><h2>Largest variances, year to date</h2>{self._variance_svg()}</div>
  <div class="panel"><h2>{self._hc_title()}</h2>{self._headcount_svg()}</div>
  <div class="panel"><h2>Data checks</h2>{self._confidence()}</div>
</section>
<footer class="foot"><p>{esc(self._sign_note())} Materiality floors: {money(self.s, t["materiality_ytd"])} year to date, {money(self.s, t["materiality_cur"])} for the month. Every figure and flag is in <b>{esc(self.workbook_name)}</b>.</p></footer>
</main>{self._script()}</body></html>
"""

    def _kpis(self) -> str:
        t = self.r["totals"]
        s = self.s
        w = self.r["window"]
        budget = t["plan_fy"] or 1.0
        has_inv = bool(self.r["invoices"]) or bool(t["pending"])
        has_po = self.r["linkage"]["method"] != "none"
        year_left = 1 - w["elapsed_share"]
        var = t["var_ytd"]
        var_cls = "o" if var > 0 else ("u" if var < 0 else "")
        remain = t["available"]
        span = f"{month_label(w['horizon_start'])} {w['horizon_start'][:4]} to {month_label(w['horizon_end'])} {w['horizon_end'][:4]}"
        cards = [
            ("Full-year budget", money(s, t["plan_fy"]), f"Plan year {span}", "", None),
            (
                "Spent to date",
                money(s, t["actual_ytd"]),
                f"{t['actual_ytd'] / budget * 100:.0f}% of budget &middot; plan to date {money(s, t['plan_ytd'])}",
                "",
                (t["actual_ytd"] / budget, w["elapsed_share"], SPENT),
            ),
            (
                "Variance to plan, to date",
                signed_money(s, var),
                f"{pct(t['var_pct_ytd'])} {'over' if var > 0 else 'under'} plan through {month_label(w['last_closed'])}",
                var_cls,
                None,
            ),
            (
                "Pending invoices",
                money(s, t["pending"]) if has_inv else "Not supplied",
                "Approved, not yet in the GL"
                if has_inv
                else "No invoice file provided",
                "" if has_inv else "na",
                None,
            ),
            (
                "Open purchase orders",
                money(s, t["open_commitments"]) if has_po else "Not supplied",
                "Ordered, not yet invoiced or posted"
                if has_po
                else "No PO file provided",
                "" if has_po else "na",
                None,
            ),
            (
                "Remaining balance" if remain >= 0 else "Over-committed",
                money(s, remain),
                f"{remain / budget * 100:.0f}% of budget left &middot; {year_left * 100:.0f}% of the year left",
                "u" if remain >= 0 else "o",
                (max(remain, 0) / budget, year_left, AVAILABLE_INK),
            ),
        ]
        out = []
        for label, value, sub, cls, bar in cards:
            meter = ""
            if bar:
                frac, marker, color = bar
                meter = (
                    f'<div class="meter"><span style="width:{min(max(frac, 0), 1) * 100:.1f}%;background:{color}"></span>'
                    f'<i style="left:{min(max(marker, 0), 1) * 100:.1f}%" title="share of the plan year"></i></div>'
                )
            out.append(
                f'<div class="kpi"><div class="kl">{esc(label)}</div><div class="kv {cls}">{value}</div><div class="ks">{sub}</div>{meter}</div>'
            )
        return "".join(out)

    def _group_dim(self) -> str | None:
        grain = self.r["grain"]
        return grain[0] if len(grain) > 1 else None

    def _table_title(self) -> str:
        dim = self._group_dim()
        return f"Budget by {esc(dim.replace('_', ' '))}" if dim else "Budget by line"

    def _table_tools(self) -> str:
        if not self._group_dim():
            return ""
        return '<button type="button" class="tbtn" data-toggle-all>Show every line</button>'

    def _budget_table(self) -> str:
        r = self.r
        dim = self._group_dim()
        elapsed = r["window"]["elapsed_share"]
        flag_ids: dict[str, list[str]] = {}
        for f in r["flags"]:
            if f["tier"] == "inspect":
                flag_ids.setdefault(f["key"], []).append(f["id"])
        fields = (
            "plan_fy",
            "plan_ytd",
            "actual_ytd",
            "var_ytd",
            "pending",
            "open_commitments",
            "available",
        )
        groups: dict[str, list[dict]] = {}
        for litem in r["lines"]:
            g = litem["keys"].get(dim, "") if dim else ""
            groups.setdefault(g, []).append(litem)
        order = sorted(
            groups, key=lambda g: -sum(litem["plan_fy"] for litem in groups[g])
        )
        head = (
            "<thead><tr><th class='tl'>{}</th><th>Full-year budget</th><th>Plan to date</th><th>Actual to date</th><th>Variance</th><th>Var %</th>"
            "<th>Pending</th><th>Open POs</th><th>Remaining</th><th class='used'>Budget used</th><th class='tl'>Flags</th></tr></thead>"
        ).format(esc(dim.replace("_", " ").title()) if dim else "Line")
        body = []
        for gi, g in enumerate(order):
            rows = sorted(groups[g], key=lambda litem: -litem["plan_fy"])
            tot = {k: sum(litem[k] for litem in rows) for k in fields}
            ids = [i for litem in rows for i in flag_ids.get(litem["key"], [])]
            if dim:
                body.append(
                    self._row(
                        f"{esc(g)} <span class='n'>{len(rows)} line{'s' if len(rows) != 1 else ''}</span>",
                        tot,
                        ids,
                        elapsed,
                        "grp",
                        gi,
                        True,
                        self._nature(rows),
                    )
                )
            for litem in rows:
                label = (
                    " · ".join(v for k, v in litem["keys"].items() if k != dim)
                    or litem["key"]
                )
                # Escape the label before adding markup: these keys come from the
                # user's own export, so they can contain HTML.
                label_html = esc(label)
                if not litem["in_plan"]:
                    label_html += " <span class='np'>no plan</span>"
                body.append(
                    self._row(
                        label_html,
                        {k: litem[k] for k in fields},
                        flag_ids.get(litem["key"], []),
                        elapsed,
                        "line" if dim else "flat",
                        gi,
                        False,
                        litem["nature"],
                    )
                )
        t = r["totals"]
        total = {
            "plan_fy": t["plan_fy"],
            "plan_ytd": t["plan_ytd"],
            "actual_ytd": t["actual_ytd"],
            "var_ytd": t["var_ytd"],
            "pending": t["pending"],
            "open_commitments": t["open_commitments"],
            "available": t["available"],
        }
        foot = self._row(
            "Total", total, [], elapsed, "total", -1, True, self._nature(r["lines"])
        )
        return f'<div class="tablewrap"><table class="bt">{head}<tbody>{"".join(body)}</tbody><tfoot>{foot}</tfoot></table></div>'

    @staticmethod
    def _nature(lines: list[dict]) -> str | None:
        natures = {line["nature"] for line in lines}
        return next(iter(natures)) if len(natures) == 1 else None

    def _row(
        self,
        label: str,
        v: dict,
        ids: list[str],
        elapsed: float,
        kind: str,
        group: int,
        strong: bool,
        nature: str | None = None,
    ) -> str:
        s = self.s
        budget = v["plan_fy"]
        used = v["actual_ytd"] + v["pending"] + v["open_commitments"]
        var = v["var_ytd"]
        vp = (var / abs(v["plan_ytd"])) if v["plan_ytd"] else None
        favorable = var < 0 if nature == "cost" else var > 0
        vcls = ("u" if favorable else "o") if var and nature else ""
        rcls = "o" if v["available"] < 0 else ""
        if budget > 0:
            sp = min(v["actual_ytd"] / budget, 1.5)
            cm = min(max(used / budget - sp, 0), 1.5 - sp)
            over = used > budget
            bar = (
                f'<div class="ub"><span class="sp" style="width:{min(sp, 1) * 100:.1f}%"></span><span class="cm" style="left:{min(sp, 1) * 100:.1f}%;width:{min(cm, max(1 - min(sp, 1), 0)) * 100:.1f}%"></span>'
                f'<i style="left:{elapsed * 100:.1f}%"></i></div><span class="up{" o" if over else ""}">{used / budget * 100:.0f}%</span>'
            )
        else:
            bar = '<span class="up o">no budget</span>'
        chips = "".join(f'<span class="chip">{esc(i)}</span>' for i in ids[:4]) + (
            f'<span class="chip more">+{len(ids) - 4}</span>' if len(ids) > 4 else ""
        )
        attrs = {
            "grp": f' class="grp" data-g="{group}" tabindex="0" aria-expanded="false"',
            "line": f' class="line" data-g="{group}" hidden',
            "flat": ' class="line"',
            "total": ' class="total"',
        }[kind]
        caret = (
            '<svg class="caret" viewBox="0 0 10 10" aria-hidden="true"><path d="M3 2l4 3-4 3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            if kind == "grp"
            else ""
        )
        return (
            f'<tr{attrs}><td class="tl">{caret}{label}</td><td>{money(s, budget)}</td><td>{money(s, v["plan_ytd"])}</td><td>{money(s, v["actual_ytd"])}</td>'
            f'<td class="{vcls}">{signed_money(s, var)}</td><td class="{vcls}">{pct(vp)}</td><td>{money(s, v["pending"]) if v["pending"] else "&ndash;"}</td>'
            f'<td>{money(s, v["open_commitments"]) if v["open_commitments"] else "&ndash;"}</td><td class="{rcls}">{money(s, v["available"])}</td>'
            f'<td class="used">{bar}</td><td class="tl">{chips}</td></tr>'
        )

    def _script(self) -> str:
        if not self._group_dim():
            return ""
        return """<script>
(function () {
  var table = document.querySelector('table.bt');
  if (!table) return;
  function setGroup(row, open) {
    row.setAttribute('aria-expanded', open ? 'true' : 'false');
    table.querySelectorAll('tr.line[data-g="' + row.dataset.g + '"]').forEach(function (r) { r.hidden = !open; });
  }
  table.querySelectorAll('tr.grp').forEach(function (row) {
    function toggle() { setGroup(row, row.getAttribute('aria-expanded') !== 'true'); }
    row.addEventListener('click', toggle);
    row.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
  });
  var all = document.querySelector('[data-toggle-all]');
  if (all) all.addEventListener('click', function () {
    var open = all.dataset.open !== 'true';
    table.querySelectorAll('tr.grp').forEach(function (row) { setGroup(row, open); });
    all.dataset.open = open ? 'true' : 'false';
    all.textContent = open ? 'Show totals only' : 'Show every line';
  });
  window.addEventListener('beforeprint', function () { table.querySelectorAll('tr.grp').forEach(function (row) { setGroup(row, true); }); });
})();
</script>"""

    def _notice_banner(self) -> str:
        notice = self.r.get("data_notice")
        if not notice:
            return ""
        synthetic = notice.upper().startswith("SYNTHETIC DATA:")
        body = notice.split(":", 1)[1].strip() if synthetic else notice
        label = "Synthetic data" if synthetic else "Note"
        return f'<div class="notice" role="note"><b>{label}</b> {esc(body)}</div>'

    def _sign_note(self) -> str:
        if any(litem["nature"] == "revenue" for litem in self.r["lines"]):
            return self.r["sign_convention"]
        return "Variance is actual minus plan; a positive variance is over budget (unfavorable)."

    def _as_of(self) -> str:
        d = date.fromisoformat(self.r["window"]["as_of_date"])
        return d.strftime("%d %b %Y").lstrip("0")

    def _walk_svg(self) -> str:
        """The full-year budget as one bar: spent, pending, on order, remaining, with how much of the year has closed."""
        t = self.r["totals"]
        s = self.s
        budget = max(t["plan_fy"], 1.0)
        parts = [
            ("Spent", max(t["actual_ytd"], 0.0), SPENT),
            ("Pending", max(t["pending"], 0.0), PENDING),
            ("On order", max(t["open_commitments"], 0.0), OPEN),
        ]
        used = sum(v for _, v, _ in parts)
        scale = max(budget, used)
        segs = []
        for label, value, color in parts:
            if value <= 0:
                continue
            segs.append(
                f'<span class="ws" style="width:{value / scale * 100:.2f}%;background:{color}" title="{esc(label)}: {money(s, value)}"></span>'
            )
        if used < budget:
            segs.append(
                f'<span class="ws rest" style="width:{(budget - used) / scale * 100:.2f}%" title="Remaining: {money(s, budget - used)}"></span>'
            )
        else:
            segs.append(
                f'<span class="ws over" style="width:{(used - budget) / scale * 100:.2f}%" title="Committed beyond budget: {money(s, used - budget)}"></span>'
            )
        elapsed = self.r["window"]["elapsed_share"]
        mark = budget / scale * elapsed * 100
        bud = budget / scale * 100
        legend = f'<span><i style="background:{SPENT}"></i>Spent</span>'
        if self.r["invoices"] or t["pending"]:
            legend += (
                f'<span><i style="background:{PENDING}"></i>Pending invoices</span>'
            )
        if self.r["linkage"]["method"] != "none":
            legend += f'<span><i style="background:{OPEN}"></i>Open POs</span>'
        legend += '<span><i class="rest"></i>Remaining</span>'
        caption = f"{elapsed * 100:.0f}% of the plan year has closed (marker); {t['plan_ytd'] / budget * 100:.0f}% of the budget was planned to be spent by now, and {used / budget * 100:.0f}% is spent or committed."
        return (
            f'<div class="wbar" role="img" aria-label="{esc(caption)}">{"".join(segs)}<b style="left:{mark:.2f}%"></b><u style="left:{bud:.2f}%"></u></div>'
            f'<div class="wcap"><div class="wleg">{legend}</div><div class="wtxt">{esc(caption)}</div></div>'
        )

    def _monthly_svg(self) -> str:
        r = self.r
        periods = r["window"]["horizon_periods"]
        last = r["window"]["last_closed"]
        plan = dict.fromkeys(periods, 0.0)
        actual = dict.fromkeys(periods, 0.0)
        for m in r["monthly"]:
            if m["period"] in plan:
                plan[m["period"]] += m["plan"]
                actual[m["period"]] += m["actual"]
        var = {p: actual[p] - plan[p] for p in periods if p <= last}
        nature = self._nature(r["lines"])
        width, height = 860.0, 210.0
        left, top, bottom = 8.0, 20.0, 34.0
        vmax = max([abs(v) for v in var.values()] + [1.0])
        ch = height - top - bottom
        zero = top + ch / 2
        half = ch / 2 - 4
        step = (width - left) / max(len(periods), 1)
        bw = step * 0.5
        out = [
            f'<svg class="month-svg" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="Variance to plan by month">'
        ]
        out.append(
            f'<line x1="{left}" y1="{zero:.1f}" x2="{width}" y2="{zero:.1f}" stroke="{INK}" stroke-width="1"/>'
        )
        for i, p in enumerate(periods):
            cx = left + step * (i + 0.5)
            closed = p <= last
            if closed:
                v = var[p]
                hpx = abs(v) / vmax * half
                favorable = v < 0 if nature == "cost" else v > 0
                col = (UNDER if favorable else OVER) if nature else MUTED
                y = zero - hpx if v > 0 else zero
                out.append(
                    f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(hpx, 1):.1f}" fill="{col}"><title>{month_label(p)}: actual {money(self.s, actual[p])}, plan {money(self.s, plan[p])}, variance {signed_money(self.s, v)}</title></rect>'
                )
                ty = (zero - hpx - 5) if v > 0 else (zero + hpx + 12)
                out.append(
                    f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle" class="num">{signed_money(self.s, v)}</text>'
                )
            else:
                out.append(
                    f'<text x="{cx:.1f}" y="{zero - 8:.1f}" text-anchor="middle" class="axis open">plan {money(self.s, plan[p])}</text>'
                )
            out.append(
                f'<text x="{cx:.1f}" y="{height - 16:.1f}" text-anchor="middle" class="axis{"" if closed else " open"}">{month_label(p)}</text>'
            )
            if closed:
                out.append(
                    f'<text x="{cx:.1f}" y="{height - 3:.1f}" text-anchor="middle" class="axis faint">{pct(var[p] / abs(plan[p])) if plan[p] else ""}</text>'
                )
        if last in periods and periods.index(last) < len(periods) - 1:
            lx = left + step * (periods.index(last) + 1)
            out.append(
                f'<line x1="{lx:.1f}" y1="{top - 10}" x2="{lx:.1f}" y2="{height - 28}" stroke="{RULE}" stroke-width="1.5"/>'
            )
            out.append(
                f'<text x="{lx + 6:.1f}" y="{top - 4}" class="axis">not closed</text>'
            )
        out.append("</svg>")
        out.append(
            '<div class="mini-legend"><span class="o">Over plan</span><span class="u">Under plan</span><span>Bars are actual minus plan for each closed month; percent of that month\'s plan below.</span></div>'
        )
        return "".join(out)

    def _nice_ceiling(self, value: float) -> float:
        exponent = math.floor(math.log10(value))
        base = 10**exponent
        for step in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
            if value <= step * base:
                return step * base
        return 10 * base

    def _line_label(self, keys: dict, key: str) -> str:
        return (
            " · ".join(str(v) for v in keys.values())
            if keys
            else key.replace(" | ", " · ")
        )

    def _inspect_list(self, inspect: list[dict]) -> str:
        hc = [f for f in self.r["headcount_flags"] if f["tier"] == "inspect"]
        groups: list[list[dict]] = []
        index: dict[str, int] = {}
        for f in inspect:
            gkey = f["key"] if f["view"] != "document" else f"{f['key']}#{f['id']}"
            if gkey not in index:
                index[gkey] = len(groups)
                groups.append([])
            groups[index[gkey]].append(f)
        rows = []
        for group in groups[:MAX_INSPECT_ROWS]:
            lead = max(group, key=lambda f: abs(f["amount"]))
            label = self._line_label(lead.get("keys") or {}, lead["key"])
            amount = lead["amount"]
            unfavorable = lead["kind"] != "underspend" and (
                amount > 0 or lead["kind"] == "committed_beyond_budget"
            )
            shown = (
                signed_money(self.s, -amount)
                if lead["kind"] == "committed_beyond_budget"
                else (
                    money(self.s, amount)
                    if lead["view"] == "document"
                    else signed_money(self.s, amount)
                )
            )
            tags = "".join(
                f'<span class="kind">{esc(KIND_LABELS.get(f["kind"], f["kind"]))}</span>'
                for f in group
            )
            ids = lead["id"]
            text = " ".join(
                f["reason"].split(". ")[0].rstrip(".") + "." for f in group[:2]
            )
            rows.append(
                f'<li><div class="ih"><span class="iid">{esc(ids)}</span><span class="il">{esc(label)}</span><span class="ia {"o" if unfavorable else "u"}">{shown}</span></div>'
                f'<div class="ib">{tags}{esc(text)}</div></li>'
            )
        for f in hc[: max(0, MAX_INSPECT_ROWS - len(rows))]:
            label = self._line_label(f.get("keys") or {}, f["key"])
            rows.append(
                f'<li><div class="ih"><span class="iid">{esc(f["id"])}</span><span class="il">{esc(label)} headcount</span><span class="ia {"o" if f["amount"] > 0 else "u"}">{f["amount"]:+.0f} heads</span></div>'
                f'<div class="ib"><span class="kind">Headcount</span>{esc(f["reason"].split(". ")[0].rstrip("."))}.</div></li>'
            )
        if not rows:
            rows.append(
                '<li class="none">No line or document crosses the inspection thresholds. The workbook lists the watch items.</li>'
            )
        shown_groups = min(len(groups), MAX_INSPECT_ROWS)
        shown_hc = max(0, min(len(hc), MAX_INSPECT_ROWS - shown_groups))
        bits = []
        if len(groups) - shown_groups > 0:
            bits.append(f"{len(groups) - shown_groups} more to inspect")
        if len(hc) - shown_hc > 0:
            bits.append(
                f"{len(hc) - shown_hc} headcount item{'s' if len(hc) - shown_hc != 1 else ''}"
            )
        watch = sum(
            1
            for f in self.r["flags"] + self.r["headcount_flags"]
            if f["tier"] == "watch"
        )
        if watch:
            bits.append(f"{watch} to watch")
        tail = (
            f'<p class="more">Also in the workbook: {", ".join(bits)}.</p>'
            if bits
            else ""
        )
        return f'<ol class="ilist">{"".join(rows)}</ol>{tail}'

    def _inspect_count(self) -> int:
        return inspect_items(self.r)

    def _variance_svg(self) -> str:
        lines = [litem for litem in self.r["lines"] if abs(litem["var_ytd"]) > 0]
        lines.sort(key=lambda litem: -abs(litem["var_ytd"]))
        top = lines[:MAX_VARIANCE_BARS]
        if not top:
            return '<p class="empty">No year-to-date variance.</p>'
        width, row_h = 520.0, 22.0
        height = row_h * len(top) + 8
        label_w = 200.0
        mid = label_w + (width - label_w) / 2
        half = (width - label_w) / 2 - 52
        vmax = max(abs(litem["var_ytd"]) for litem in top)
        out = [
            f'<svg viewBox="0 0 {width:.0f} {height:.0f}" class="var-svg" role="img" aria-label="Largest year-to-date variances by line">'
        ]
        out.append(
            f'<line x1="{mid:.1f}" y1="0" x2="{mid:.1f}" y2="{height:.0f}" stroke="{INK}" stroke-width="1"/>'
        )
        for i, litem in enumerate(top):
            y = i * row_h + 4
            v = litem["var_ytd"]
            wpx = abs(v) / vmax * half
            favorable = (v < 0) if litem["nature"] == "cost" else (v > 0)
            col = UNDER if favorable else OVER
            x = mid if v > 0 else mid - wpx
            label = self._fit_label(
                list(litem["keys"].values()) or [litem["key"]], label_w - 8, 11
            )
            tag = " (no plan)" if not litem["in_plan"] else ""
            out.append(
                f'<text x="0" y="{y + 14:.1f}" class="lbl">{esc(label)}{tag}</text>'
            )
            out.append(
                f'<rect x="{x:.1f}" y="{y + 3:.1f}" width="{max(wpx, 1):.1f}" height="{row_h - 8:.1f}" fill="{col}"><title>{esc(label)}: {signed_money(self.s, v)} ({pct(litem["var_pct_ytd"])})</title></rect>'
            )
            tx = x + wpx + 4 if v > 0 else x - 4
            anchor = "start" if v > 0 else "end"
            out.append(
                f'<text x="{tx:.1f}" y="{y + 14:.1f}" text-anchor="{anchor}" class="num">{signed_money(self.s, v)}</text>'
            )
        out.append("</svg>")
        return (
            "".join(out)
            + '<div class="mini-legend"><span class="o">Over plan (unfavorable)</span><span class="u">Under plan (favorable)</span></div>'
        )

    def _fit_label(self, parts: list[str], width: float, size: float) -> str:
        """Joins key parts, shortening the leading parts first so the last (most specific) part stays whole."""
        full = " · ".join(str(p) for p in parts)
        if text_width(full, size) <= width:
            return full
        tail = str(parts[-1])
        budget = int(width / (size * CHAR_W)) - len(tail) - 4
        head = " · ".join(str(p) for p in parts[:-1])
        if budget < 4:
            return full[: int(width / (size * CHAR_W)) - 1] + "…"
        return head[:budget].rstrip() + "… · " + tail

    def _hc_title(self) -> str:
        return (
            f"Headcount at {month_label(self.r['window']['last_closed'], True)}"
            if self.r["headcount"]
            else "Headcount"
        )

    def _headcount_svg(self) -> str:
        last = self.r["window"]["last_closed"]
        rows = [h for h in self.r["headcount"] if h["period"] == last]
        if not rows:
            return '<p class="empty">No headcount file was provided. Add one to compare planned and actual heads.</p>'
        rows.sort(key=lambda h: -h["plan"])
        rows = rows[:8]
        width, row_h = 520.0, 24.0
        label_w = 120.0
        height = row_h * len(rows) + 22
        vmax = (
            max(max(h["plan"], h["actual"] + (h["open_reqs"] or 0)) for h in rows)
            * 1.08
        )
        scale = (width - label_w - 70) / max(vmax, 1)
        flagged = {f["key"] for f in self.r["headcount_flags"]}
        out = [
            f'<svg viewBox="0 0 {width:.0f} {height:.0f}" class="hc-svg" role="img" aria-label="Planned and actual heads by group">'
        ]
        for i, h in enumerate(rows):
            y = i * row_h + 14
            label = " · ".join(h["keys"].values())
            out.append(
                f'<text x="0" y="{y + 4:.1f}" class="lbl{" strong" if h["key"] in flagged else ""}">{esc(label)}</text>'
            )
            x0 = label_w
            xa = x0 + h["actual"] * scale
            xp = x0 + h["plan"] * scale
            out.append(
                f'<line x1="{x0}" y1="{y:.1f}" x2="{xa:.1f}" y2="{y:.1f}" stroke="{SPENT}" stroke-width="6"/>'
            )
            if h["open_reqs"]:
                xr = xa + h["open_reqs"] * scale
                out.append(
                    f'<line x1="{xa:.1f}" y1="{y:.1f}" x2="{xr:.1f}" y2="{y:.1f}" stroke="{OPEN}" stroke-width="6"><title>{h["open_reqs"]:.0f} open requisitions</title></line>'
                )
            out.append(
                f'<line x1="{xp:.1f}" y1="{y - 8:.1f}" x2="{xp:.1f}" y2="{y + 8:.1f}" stroke="{INK}" stroke-width="2"><title>Plan {h["plan"]:.0f}</title></line>'
            )
            diff = h["actual"] - h["plan"]
            col = MUTED if abs(diff) < 1 else (OVER if diff > 0 else UNDER)
            out.append(
                f'<text x="{width:.0f}" y="{y + 4:.1f}" text-anchor="end" class="num" fill="{col}">{h["actual"]:.0f} / {h["plan"]:.0f}</text>'
            )
        out.append(
            f'<text x="{label_w}" y="{height - 2:.0f}" class="axis">bar = actual heads, light extension = open requisitions, tick = plan; right: actual / plan</text>'
        )
        out.append("</svg>")
        return "".join(out)

    def _confidence(self) -> str:
        r = self.r
        # Raw symbol: each item's text is escaped once when it is written below.
        s = r["currency_symbol"]
        items = []
        proof_ok = all(p["passed"] for p in r["proof"])
        what = "GL and ordered dollar" if r["commitments"] else "GL dollar"
        passed = sum(1 for p in r["proof"] if p["passed"])
        items.append(
            (
                proof_ok,
                "Tie-out",
                f"{passed} of {len(r['proof'])} checks pass: each {what} is placed in one bucket."
                if proof_ok
                else f"{len(r['proof']) - passed} tie-out check fails. See the Tie-out sheet before using these totals.",
            )
        )
        link = r["linkage"]
        if link["method"] == "none":
            items.append(
                (
                    None,
                    "Commitments",
                    "No purchase orders supplied: open commitments are not included.",
                )
            )
        else:
            share = (
                f" ({link['matched_share'] * 100:.0f}% of POs matched to GL lines)"
                if link.get("matched_share") is not None
                else ""
            )
            items.append(
                (
                    link["confidence"] == "high",
                    "PO linkage",
                    f"{link['confidence'].capitalize()} confidence{share}.",
                )
            )
        codes = {f["code"]: f for f in r["findings"]}
        fx_issues = [
            f
            for f in r["findings"]
            if f["code"].startswith("fx_") and f["severity"] in {"warning", "error"}
        ]
        converted = bool(r["fx_used"])
        ok_text = (
            "All rows converted at their own month's rate."
            if converted
            else f"Single currency ({r['reporting_currency']}); no conversion needed."
        )
        items.append(
            (
                not fx_issues,
                "Currency",
                ok_text if not fx_issues else fx_issues[0]["message"],
            )
        )
        unpl = r["totals"]["unplanned_ytd"]
        items.append(
            (
                abs(unpl) < r["totals"]["materiality_cur"],
                "Coverage",
                f"{money(s, unpl)} of year-to-date actuals has no plan line."
                if unpl
                else "Every actual maps to a plan line.",
            )
        )
        acc = codes.get("accruals_without_po")
        if acc:
            items.append(
                (
                    False,
                    "Accruals",
                    f"{money(s, acc['amount'])} accrued without a PO reference may also sit in open POs.",
                )
            )
        opa = r["totals"]["open_period_actuals"]
        if opa:
            items.append(
                (
                    None,
                    "Open month",
                    f"{money(s, opa)} posted after {month_label(r['window']['last_closed'], True)} is held out of year to date.",
                )
            )
        rows = []
        for ok, label, text in items[:6]:
            icon = self._icon(ok)
            rows.append(
                f'<li>{icon}<span class="cl">{esc(label)}</span><span class="ct">{esc(text)}</span></li>'
            )
        return f'<ul class="conf">{"".join(rows)}</ul>'

    def _icon(self, ok: bool | None) -> str:
        if ok is None:
            return f'<svg class="ic" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" fill="none" stroke="{MUTED}" stroke-width="1.4"/><line x1="5" y1="8" x2="11" y2="8" stroke="{MUTED}" stroke-width="1.4"/></svg>'
        if ok:
            return f'<svg class="ic" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" fill="none" stroke="{UNDER}" stroke-width="1.4"/><path d="M5 8.3l2 2 4-4.3" fill="none" stroke="{UNDER}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        return f'<svg class="ic" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.5" fill="none" stroke="{OVER}" stroke-width="1.4"/><line x1="8" y1="4.5" x2="8" y2="9" stroke="{OVER}" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="11.4" r="0.9" fill="{OVER}"/></svg>'

    def _css(self) -> str:
        return report_css()
