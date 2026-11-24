#!/usr/bin/env python3
"""
description: Build the Changes, Map and Performance tabs of the review report.
last_updated: 2026-11-24

render_tabs.py - three report tabs that only read the plan, the changelog and the scan.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

from render_format import (
    E,
    as_text,
    cap,
    diff_html,
    num,
    pl,
    plain,
    readable,
    val_html,
    where_html,
)
from render_map import flow_text, svg_map
from render_taxonomy import ROLE_LABEL


def changes_tab(plan, applied, status_of, ctx_changes, kept, dismissed):
    """The Changes tab: banners, one card per proposed change, and the Needs you list."""
    plan_changes = (plan or {}).get("changes", [])
    n_applied = sum(1 for r in status_of.values() if r["status"] == "applied")
    changes_html = "<p class='empty'>No changes proposed yet.</p>"
    if plan:
        banners = []
        rc = (applied or {}).get("recheck")
        if applied:
            banners.append(
                f"<div class='note ok'><div><b>Applied {n_applied} of {len(plan_changes)} to a copy:</b> {E(Path(applied['copy']).name)}. Your original wasn't changed."
                + (
                    f" Re-check: {rc['cleared']} of {rc['targeted']} targeted findings cleared, {len(rc['new'])} new."
                    if rc
                    else ""
                )
                + " Open the copy in Excel to see the updated values; Excel recalculates it on open."
                + "</div></div>"
            )
            if rc and rc.get("new"):
                banners.append(
                    "<div class='note crit'><div><b>New after the changes:</b> "
                    + "; ".join(
                        E(f"{n['sheet']}!{n['cell']}: {readable(n['description'])}")
                        for n in rc["new"][:6]
                    )
                    + "</div></div>"
                )
        else:
            banners.append(
                "<div class='note'><div><b>Nothing applied yet.</b> Reply in chat with the numbers you want, for example "
                "<i>apply 1, 3, 6</i> or <i>apply all safe</i>. Changes go into a copy; your original isn't touched.</div></div>"
            )
        cards = []
        for ch in plan_changes:
            st = (status_of.get(ch["n"]) or {}).get("status") or "proposed"
            why = (status_of.get(ch["n"]) or {}).get("why")
            cx = ctx_changes.get(str(ch["n"]), {})
            label = cx.get("label") or next(
                (
                    f.get("label")
                    for f in kept
                    if f["id"] in ch["finding_ids"] and f.get("label")
                ),
                "",
            )
            summ = plain(ch["summary"])
            m = re.match(
                r"^(?P<a>.+?) → (?P<b>.+?) \((?P<why>[^()]*(?:\([^()]*\)[^()]*)*)\)$",
                summ,
            )
            text = cap(m.group("why")) if (m and cx.get("old")) else summ
            body = f"<div class='chg-what'>{E(text)}</div>"
            if cx.get("old") is not None and cx.get("new") is not None:
                body += diff_html(as_text(cx["old"]), as_text(cx["new"]))
                if cx.get("cells", 0) > 1:
                    body += f"<div class='diff-note'>Shown for {E(cx.get('where', ''))}; the same change goes into {pl(cx['cells'] - 1, 'more cell')}.</div>"
            if cx.get("values"):
                body += (
                    "<div class='vals'>"
                    + "".join(val_html(v) for v in cx["values"])
                    + "</div>"
                )
                body += (
                    "<div class='basis'>"
                    + {
                        "applied": "In the fixed copy",
                        "isolated": "Estimated if this change is applied on its own",
                        "combined": "Estimated with every proposed change in place",
                    }.get(cx.get("basis"), "")
                    + "</div>"
                )
            elif cx.get("basis") in ("isolated", "applied") and cx.get("cells"):
                body += (
                    "<div class='basis'>Same results: the numbers don't change.</div>"
                )
            if why:
                body += f"<div class='basis'>Skipped: {E(why)}</div>"
            st_chip = {
                "applied": "<span class='chip applied'>Applied</span>",
                "skipped": "<span class='chip skipped'>Skipped</span>",
            }.get(st, "<span class='chip proposed'>Proposed</span>")
            risk_chip = (
                "<span class='chip safe'>safe</span>"
                if ch["risk"] == "safe"
                else "<span class='chip confirm' title='Could be intentional: check before applying'>confirm</span>"
            )
            cards.append(
                f"<div class='chg st-{st} r-{ch['risk']}'><div class='chg-head'><span class='chg-n'>#{ch['n']}</span>"
                f"<div class='chg-where'>{where_html(ch['sheet'], ch['target'], label)}</div><div class='chips'>{risk_chip}{st_chip}</div></div>"
                f"<div class='chg-body'>{body}</div></div>"
            )
        manual_by = {}
        for mrow in plan.get("manual", []):  # one row per place, with every reason
            manual_by.setdefault(mrow["where"], []).append(mrow)
        manual_rows = []
        for wh, ms in manual_by.items():
            f = next(
                (x for x in kept + dismissed if x["id"] == ms[0]["finding_id"]), {}
            )
            sh, _, cell = wh.partition("!")
            manual_rows.append(
                f"<tr><td>{where_html(sh, cell, f.get('label', ''))}</td><td>"
                + "".join(
                    f"<div class='{'what' if i == 0 else 'also'}'>{E(readable(m['what']))}</div>"
                    f"<div class='fix'><b>Suggested:</b> {E(m['recommendation'])}</div>"
                    for i, m in enumerate(ms)
                )
                + "</td></tr>"
            )
        changes_html = (
            "".join(banners)
            + "<h2>Recommended changes</h2>"
            + ("".join(cards) or "<p class='empty'>No automatic changes.</p>")
            + f"<h2>Needs you <span class='cnt'>{len(manual_rows)}</span></h2><p class='sub'>These need knowledge of the model and are never changed automatically."
            " Ask in chat to talk any of them through.</p>"
            + (
                (
                    "<table><thead><tr><th style='width:230px'>Where</th><th>What and what to do</th></tr></thead><tbody>"
                    + "".join(manual_rows)
                    + "</tbody></table>"
                )
                if manual_rows
                else "<p class='empty'>Nothing.</p>"
            )
        )
    return changes_html


def map_tab(scan, narrative, open_rows):
    """The Map tab: purpose, tab links, key inputs and results, and the tab table."""
    mp = scan.get("map", {})

    def rows_table(items, kind):
        if not items:
            return "<p class='empty'>None identified.</p>"
        head = "<th>Used by</th>" if kind == "in" else ""
        body = "".join(
            f"<tr><td>{where_html(i['sheet'], i['cell'], i.get('label') or '')}</td>"
            f"<td class='num'>{num(i.get('value'))}{' …' if i.get('periods', 1) > 1 else ''}</td>"
            + (f"<td>{pl(i['used_by'], 'formula')}</td>" if kind == "in" else "")
            + "</tr>"
            for i in items
        )
        return f"<table><thead><tr><th style='width:280px'>Line</th><th>Value</th>{head}</tr></thead><tbody>{body}</tbody></table>"

    by_sheet = defaultdict(Counter)
    for r in open_rows:
        for f in r["items"]:
            if f.get("sheet"):
                by_sheet[f["sheet"]][f["severity"]] += 1
    legend = "".join(
        f"<span><i class='lg-{k}'></i>{v}</span>"
        for k, v in ROLE_LABEL.items()
        if k not in ("external",)
    )
    hidden = [s["sheet"] for s in scan["sheets"] if s["state"] != "visible"]
    mapping = f"""<h2>Map</h2>
<div class='card'><dl class='kv'>
<dt>What it is</dt><dd>{E(narrative.get("purpose") or "Not described in the file. See the tab roles below.")}</dd>
<dt>Time horizon</dt><dd>{E(mp.get("time_horizon") or "Not date-based, or not detected")}</dd>
<dt>Links</dt><dd>{flow_text(scan) or "Tabs are not linked by formulas"}</dd>
{f"<dt>Hidden tabs</dt><dd>{E(', '.join(hidden))}</dd>" if hidden else ""}
</dl></div>
<h2>How the tabs feed each other</h2>
<div class='map'>{svg_map(scan, by_sheet)}</div>
<div class='legend'>{legend}<span><i class='lg-hidden'></i>Hidden tab or other file</span>
<span>Arrows: formulas pulling from one tab into another (number = how many)</span><span>Badge: open critical + warning issues</span></div>
<h2>Key inputs</h2><p class='sub'>Typed numbers that the most formulas depend on.</p>{rows_table(mp.get("key_inputs", []), "in")}
<h2>Key results</h2><p class='sub'>Totals and results that nothing else in the model uses; usually what the model is for.</p>{rows_table(mp.get("key_outputs", []), "out")}
<h2>Tabs</h2><table><thead><tr><th>Tab</th><th>Role</th><th>Rows</th><th>Formulas</th><th>Reads from</th><th>Feeds</th></tr></thead><tbody>
{"".join(f"<tr><td><b>{E(s['sheet'])}</b>{' <span class=sub>(hidden)</span>' if s['state'] != 'visible' else ''}</td><td>{E(ROLE_LABEL.get(s['role'], cap(s['role'])))}</td><td class='num'>{s['rows']:,}</td><td class='num'>{s['formulas']:,}</td><td>{E(', '.join(s['reads_from']))}</td><td>{E(', '.join(s['feeds']))}</td></tr>" for s in scan["sheets"])}
</tbody></table>"""
    return mapping


def performance_tab(perf, perf_issues_html):
    """The Performance tab: limits over and within range, then the performance findings."""
    over = (perf.get("reds") or 0) + (perf.get("yellows") or 0)
    pk, pt = {
        "fixes": (
            "",
            f"{pl(over, 'performance limit')} exceeded; see the fixes listed.",
        ),
        "restructure": (
            "crit",
            f"{pl(over, 'performance limit')} exceeded. The fixes listed help, but the model may also need "
            "restructuring (fewer tabs, simpler flow) to calculate quickly.",
        ),
    }.get(perf.get("verdict"), ("ok", "No performance limits exceeded."))

    def mval(m):
        return num(m["value"]) if not isinstance(m["value"], str) else E(m["value"])

    flagged = sorted(
        [m for m in perf.get("metrics", []) if m["rating"] in ("red", "yellow")],
        key=lambda m: m["rating"] != "red",
    )
    clear = [m for m in perf.get("metrics", []) if m["rating"] not in ("red", "yellow")]
    performance = (
        f"<h2>Performance</h2><div class='note {pk}'><div><b>Limits:</b> {E(pt)}</div></div>"
        + (
            (
                "<table><thead><tr><th style='width:260px'>Over the limit</th><th style='width:140px'>This model</th><th>Why it matters</th></tr></thead><tbody>"
                + "".join(
                    f"<tr><td><span class='dot {m['rating']}'></span>{E(m['label'])}</td><td class='num'>{mval(m)}</td><td>{E(m['note'])}</td></tr>"
                    for m in flagged
                )
                + "</tbody></table>"
            )
            if flagged
            else ""
        )
        + (
            "<h3 style='margin-top:20px'>Within limits</h3><div class='metrics'>"
            + "".join(
                f"<span class='metric'><span class='dot green'></span>{E(m['label'])} <b>{mval(m)}</b></span>"
                for m in clear
            )
            + "</div>"
            if clear
            else ""
        )
        + "<p class='sub'>Green / yellow / red limits are starting points for typical finance models. Real calculation time can only be measured in Excel.</p>"
        + perf_issues_html
    )
    return performance
