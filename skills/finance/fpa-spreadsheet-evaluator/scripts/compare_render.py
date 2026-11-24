#!/usr/bin/env python3
"""
description: Build the single-file HTML comparison report from compare_workbooks.compare's result.
last_updated: 2026-11-24

compare_render.py - Summary, What changed, Structure and Issues tabs for two workbook versions.
"""

from __future__ import annotations

import datetime as dt

import render_report as RR
import scan_workbook as S
from compare_export import _change_log_link

UTC_TZ = dt.timezone.utc  # noqa: UP017 - datetime.UTC needs Python 3.11; the skill supports 3.10


def _val(v, pct=False):
    if pct and S.is_num(v):
        return f"{v * 100:,.1f}%"
    return RR.num(v) if v is not None else "(blank)"


def render(res, narrative=None, generated=None):
    E, where_html, pl = RR.E, RR.where_html, RR.pl
    narrative = narrative or {}
    notes = narrative.get("notes", {})
    generated = generated or dt.datetime.now(UTC_TZ).strftime("%d %b %Y, %H:%M UTC")
    c = res["counts"]
    flags = res["flags"]
    crit = [f for f in flags if f["severity"] == "critical"]
    [f for f in flags if f["severity"] == "warning" and f["basis"] == "verified"]
    if crit:
        vk, mark, head = (
            "v-crit",
            "!",
            f"{pl(len(crit), 'change')} broke something, and {pl(len(flags) - len(crit), 'more')} may be unintended.",
        )
    elif flags:
        vk, mark, head = (
            "v-warn",
            "!",
            f"{pl(len(flags), 'change')} may be unintended: check {'it' if len(flags) == 1 else 'them'} before this version goes out.",
        )
    else:
        vk, mark, head = "v-ok", "0", "No changes flagged as possibly unintended."
    moved = [o for o in res["outputs"] if o["before"] != o["after"]]
    nxt = (
        f"{pl(c['assumptions'], 'input row')} and {pl(c['formulas'], 'formula pattern')} changed; "
        f"{pl(c['rows_added'], 'row')} added, {c['rows_removed']} removed; {pl(len(moved), 'key result')} moved; "
        f"{pl(c['introduced'], 'new issue')}, {c['resolved']} resolved."
    )
    verdict = (
        f"<div class='verdict {vk}'><div class='v-mark'>{mark}</div><div><div class='v-head'>{E(head)}</div>"
        f"<div class='v-next'>{E(nxt)}</div>"
        + (
            f"<div class='v-sum'>{E(narrative['summary'])}</div>"
            if narrative.get("summary")
            else ""
        )
        + "</div></div>"
    )

    def flag_card(f):
        chip = RR.sev_chip(f["severity"]) + (
            " <span class='chip basis-j'>Question</span>"
            if f["basis"] == "judgment"
            else ""
        )
        note = notes.get(f["id"])
        return (
            f"<div class='qitem'><div class='qmeta'>{chip}{where_html(f.get('sheet'), f.get('cell'), f.get('label', ''))}"
            f"<span class='sub'>{E(f['id'])}</span></div><div class='what'>{E(RR.readable(f['text']))}</div>"
            + (f"<div class='qq'>Why it matters: {E(note)}</div>" if note else "")
            + "</div>"
        )

    flags_html = (
        (
            "<div class='qlist'>"
            + "".join(flag_card(f) for f in flags[:20])
            + "</div>"
            + (
                f"<p class='sub'>{pl(len(flags) - 20, 'more flag')} in the change log.</p>"
                if len(flags) > 20
                else ""
            )
        )
        if flags
        else "<p class='empty'>No changes flagged by the comparison.</p>"
    )

    def tile(name, n, sub=""):
        return (
            f"<div class='tile{' clear' if not n else ''}'><div class='t-top'><span class='t-name'>{E(name)}</span>"
            f"<span class='t-big'>{n}</span></div><div class='t-foot'>{E(sub)}</div></div>"
        )

    tiles = (
        "<div class='grid areas'>"
        + tile("Inputs changed", c["assumptions"], "rows of typed numbers")
        + tile("Formulas changed", c["formulas"], "distinct patterns")
        + tile("Formulas now typed", c["to_value"], "hardcodes added")
        + tile(
            "Rows added / removed",
            c["rows_added"] + c["rows_removed"],
            f"{c['rows_added']} added, {c['rows_removed']} removed",
        )
        + tile("New issues", c["introduced"], f"{c['resolved']} resolved")
        + "</div>"
    )
    if res["outputs"]:
        kr = (
            "<table class='kr'><thead><tr><th style='width:260px'>Result</th><th>Before</th><th>After</th></tr></thead><tbody>"
            + "".join(
                f"<tr><td>{where_html(o['sheet'], o['cell'], o['label'])}</td><td class='num'>{_val(o['before'], o['pct'])}</td>"
                f"<td class='num after'>{_val(o['after'], o['pct'])} "
                + (
                    RR.delta(o["before"], o["after"])
                    if not o["pct"]
                    else (
                        f"<span class='delta'>{(o['after'] - o['before']) * 100:+.1f} pts</span>"
                        if S.is_num(o["before"]) and S.is_num(o["after"])
                        else ""
                    )
                )
                + "</td></tr>"
                for o in res["outputs"]
            )
            + "</tbody></table>"
        )
    else:
        kr = "<p class='empty'>No key results identified.</p>"
    summary = (
        f"{verdict}<h2>At a glance</h2>{tiles}<h2>Check these first</h2>{flags_html}<h2>Key results</h2>{kr}"
        "<div class='disclaimer'>Automated comparison. Cells are matched by their row label and column header, so inserted rows "
        "and periods don't show as changes. Flags marked Question are judgment calls for the model owner.</div>"
    )
    # what changed
    a_rows = "".join(
        f"<tr><td>{where_html(e['sheet'], e['cell'], e['label'])}</td><td class='num'>{_val(e['before'], '%' in S.fmt_section(e.get('fmt') or ''))}</td>"
        f"<td class='num after'>{_val(e['after'], '%' in S.fmt_section(e.get('fmt') or ''))} {RR.delta(e['before'], e['after']) if '%' not in S.fmt_section(e.get('fmt') or '') else ''}</td>"
        f"<td>{'' if e['count'] == 1 else (pl(e['count'], 'cell') + (', same change' if e['same'] else ', first shown'))}</td>"
        f"<td>{pl(e['used_by'], 'formula') if e['used_by'] else '<span class=sub>not used by formulas</span>'}</td></tr>"
        for e in res["assumptions"]
    )
    a_html = (
        (
            "<table><thead><tr><th style='width:260px'>Input</th><th>Before</th><th>After</th><th>Cells</th><th>Used by</th></tr></thead><tbody>"
            + a_rows
            + "</tbody></table>"
        )
        if a_rows
        else "<p class='empty'>No typed inputs changed.</p>"
    )
    f_html = (
        "".join(
            f"<div class='chg{' r-confirm st-proposed' if e.get('partial') else ''}'><div class='chg-head'><span class='chg-n'>{E(str(e['count']))}×</span>"
            f"<div class='chg-where'>{where_html(e['sheet'], e['cell'], e['label'])}</div></div><div class='chg-body'>"
            + RR.diff_html(e["old"], e["new"])
            + (
                f"<div class='basis'>Shown for the first cell. {pl(e['partial'], 'cell')} in the same row still use the old formula.</div>"
                if e.get("partial")
                else ""
            )
            + "</div></div>"
            for e in res["formulas"]
        )
        or "<p class='empty'>No formula logic changed.</p>"
    )
    tv = "".join(
        f"<tr><td>{where_html(e['sheet'], e['cell'], e['label'])}</td><td><code>{E(RR.plain(e['old']))}</code></td>"
        f"<td class='num'>{RR.num(e['new'])}</td></tr>"
        for e in res["to_value"]
    )
    tf = "".join(
        f"<tr><td>{where_html(e['sheet'], e['cell'], e['label'])}</td><td class='num'>{RR.num(e['old'])}</td>"
        f"<td><code>{E(RR.plain(e['new']))}</code></td></tr>"
        for e in res["to_formula"]
    )
    d_html = ""
    for sh, d in res["data"].items():
        ex = "".join(
            f"<li>{E(x['label'] or x['cell'])}: {E(x['before'])} → {E(x['after'])}</li>"
            for x in d["examples"]
        )
        d_html += (
            f"<div class='card' style='margin-bottom:12px'><h3>{E(sh)}</h3><p>{pl(d['added'], 'record')} added, {d['removed']} removed, "
            f"{pl(d['changed'], 'value')} changed.</p>"
            + (
                f"<p class='sub'>Added: {E(', '.join(d['added_ids']))}</p>"
                if d["added_ids"]
                else ""
            )
            + (
                f"<p class='sub'>Removed: {E(', '.join(d['removed_ids']))}</p>"
                if d["removed_ids"]
                else ""
            )
            + (f"<ul class='sub'>{ex}</ul>" if ex else "")
            + "</div>"
        )
    changes = (
        f"<h2>Inputs and assumptions</h2>{a_html}<h2>Formula changes</h2>{f_html}"
        + (
            f"<h2>Formulas replaced by typed numbers</h2><table><thead><tr><th style='width:260px'>Where</th><th>Was</th><th>Now</th></tr></thead><tbody>{tv}</tbody></table>"
            if tv
            else ""
        )
        + (
            f"<h2>Typed numbers replaced by formulas</h2><table><thead><tr><th style='width:260px'>Where</th><th>Was</th><th>Now</th></tr></thead><tbody>{tf}</tbody></table>"
            if tf
            else ""
        )
        + (f"<h2>Data tabs</h2>{d_html}" if d_html else "")
    )
    # structure
    sh = res["sheets"]
    items = []
    for lab, key in (
        ("Tabs added", "added"),
        ("Tabs removed", "removed"),
        ("Newly hidden", "hidden"),
        ("Unhidden", "unhidden"),
    ):
        if sh[key]:
            items.append(f"<dt>{lab}</dt><dd>{E(', '.join(sh[key]))}</dd>")
    if sh["renamed"]:
        items.append(
            f"<dt>Renamed</dt><dd>{E(', '.join(a + ' → ' + b for a, b in sh['renamed']))}</dd>"
        )
    st_html = f"<div class='card'><dl class='kv'>{''.join(items) or '<dt>Tabs</dt><dd>Same tabs in both versions</dd>'}</dl></div>"
    rows_tbl = "".join(
        f"<tr><td><b>{E(n)}</b></td><td>{E(', '.join(v.get('rows_added', [])) or '-')}</td><td>{E(', '.join(v.get('rows_removed', [])) or '-')}</td>"
        f"<td>{E(', '.join(v.get('cols_added', [])) or '-')}</td><td>{E(', '.join(v.get('cols_removed', [])) or '-')}</td></tr>"
        for n, v in res["structure"].items()
    )
    st_html += (
        "<h2>Rows and columns</h2><table><thead><tr><th style='width:140px'>Tab</th><th>Rows added</th><th>Rows removed</th>"
        f"<th>Columns added</th><th>Columns removed</th></tr></thead><tbody>{rows_tbl}</tbody></table>"
        if rows_tbl
        else "<p class='empty'>No rows or columns added or removed.</p>"
    )

    def ftable(fs, empty):
        if not fs:
            return f"<p class='empty'>{empty}</p>"
        return (
            "<table><thead><tr><th style='width:96px'>Severity</th><th style='width:230px'>Where</th><th>Finding</th></tr></thead><tbody>"
            + "".join(
                f"<tr><td><div class='sevcell'>{RR.sev_chip(f['severity'])}"
                + (
                    "<span class='chip basis-j'>Question</span>"
                    if f.get("basis") == "judgment"
                    else ""
                )
                + "</div></td>"
                f"<td>{where_html(f.get('sheet'), f.get('cell'), f.get('label', ''))}</td><td>{E(RR.readable(f['description']))}</td></tr>"
                for f in fs
            )
            + "</tbody></table>"
        )

    issues = (
        f"<h2>New in this version</h2>{ftable(res['introduced'], 'No new issues.')}"
        f"<h2>Resolved since the old version</h2>{ftable(res['resolved'], 'Nothing resolved.')}"
    )
    tab_defs = [
        (
            "summary",
            "Summary",
            f"<span class='cnt {'crit' if crit else 'warn' if flags else 'ok'}'>{len(flags)}</span>",
        ),
        (
            "changes",
            "What changed",
            f"<span class='cnt'>{c['assumptions'] + c['formulas'] + c['to_value']}</span>",
        ),
        ("map", "Structure", ""),
        (
            "issues",
            "Issues",
            f"<span class='cnt'>{c['introduced']}</span>" if c["introduced"] else "",
        ),
    ]
    tabs_html = "".join(
        f"<input type='radio' name='tab' id='t-{k}'{' checked' if k == 'summary' else ''}><label for='t-{k}'>{lab}{cnt}</label>"
        for k, lab, cnt in tab_defs
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><title>Comparison: {E(res["new"])}</title><style>{RR.CSS}</style></head><body>
<header class='top'><div class='wrap'><div class='eyebrow'>Workbook comparison</div><h1>{E(res["old"])} → {E(res["new"])}</h1>
<div class='meta'><span>Compared {E(generated)}</span><span>Old version on the left of each change, new on the right</span></div></div></header>
<div class='tabs'>{tabs_html}<div class='panels'><div class='wrap'>
<section id='p-summary'>{summary}</section>
<section id='p-changes'>{changes}</section>
<section id='p-map'><h2>Structure</h2>{st_html}</section>
<section id='p-issues'>{issues}</section>
<footer>{_change_log_link(res, generated)}<span>Contains labels and formulas from both versions. Share it as you would the model.</span></footer>
</div></div></div></body></html>"""
