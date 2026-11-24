#!/usr/bin/env python3
"""
description: Build the single-file HTML audit report and the Excel sign-off checklist.
last_updated: 2026-11-24

render_report.py - build the single-file HTML review report.

  python3 render_report.py SCAN.json OUT.html [--changes CHANGES.json] [--applied CHANGELOG.json]
                           [--decisions DECISIONS.json] [--narrative NARRATIVE.json] [--context CONTEXT.json]
                           [--judgments JUDGMENTS.json]

JUDGMENTS.json holds the reviewer's own judgment calls (business sense, presentation), shown as questions:
  [{"area": "Financial logic", "title": "Hiring outpaces revenue", "sheet": "Payroll", "cell": "B2:M2",
    "observation": "Headcount grows 40% while revenue grows 5%.", "question": "Is the hiring plan funded?",
    "suggestion": "Add a capacity or productivity assumption.", "severity": "warning"}]

NARRATIVE.json holds the reviewer's own words (all optional):
  {"purpose": "Twelve-month headcount and payroll plan for ...",
   "summary": "Two or three sentences on overall health.",
   "excel_target": "Microsoft 365 (file already uses XLOOKUP)",
   "impacts": {"F-012": "Q2 payroll is understated by about $40K."}}

CONTEXT.json (from report_context.py, optional) adds the file's display path, the review time,
formula before/after for each change and how the values move.

The report is one self-contained file: no scripts, no network, no external fonts or libraries.
Tabs and filters work with plain HTML/CSS; the map is an inline SVG. The stylesheet (assets/report-style.md)
uses the host page's --color-* theme variables when they are defined, falls back to the system's
light/dark setting otherwise, and prints cleanly. It contains labels and formulas from the model, so
share it as you would the model.

Every string taken from the workbook or from agent-written JSON is HTML-escaped (E), and the only
links in the page are the two data: downloads.
"""

from __future__ import annotations

import datetime as dt
import sys
from collections import Counter
from pathlib import Path

from render_downloads import csv_link, issue_rows, xlsx_link
from render_format import (
    TOKEN,
    XL_PREFIX,
    E,
    as_text,
    cap,
    delta,
    diff_html,
    grid_html,
    is_num,
    load,
    num,
    pl,
    plain,
    readable,
    sev_chip,
    val_html,
    val_pair,
    where_html,
)
from render_map import EXT_NODE, excel_line, flow_text, layout, svg_map
from render_tabs import changes_tab, map_tab, performance_tab
from render_taxonomy import (
    AREA_KEYS,
    AREA_OF_GROUP,
    AREAS,
    DISCLAIMER,
    NOT_AN_ATTESTATION,
    NOTE_TITLES,
    PERFORMANCE_CHECKS,
    ROLE_LABEL,
    SEV_HELP,
    SEV_LABEL,
    SEV_ORDER,
    VALUE_CHECKS_SKIPPED,
    is_perf,
    judgment_findings,
    tab_of,
)

# Names other scripts read as render_report.X (compare_workbooks uses RR.*); keep them importable here.
__all__ = [
    "AREA_KEYS",
    "AREA_OF_GROUP",
    "AREAS",
    "CSS",
    "DISCLAIMER",
    "E",
    "EXT_NODE",
    "NOT_AN_ATTESTATION",
    "NOTE_TITLES",
    "PERFORMANCE_CHECKS",
    "ROLE_LABEL",
    "SEV_HELP",
    "SEV_LABEL",
    "SEV_ORDER",
    "VALUE_CHECKS_SKIPPED",
    "TOKEN",
    "XL_PREFIX",
    "as_text",
    "cap",
    "csv_link",
    "delta",
    "diff_html",
    "excel_line",
    "flow_text",
    "grid_html",
    "is_num",
    "is_perf",
    "issue_rows",
    "judgment_findings",
    "layout",
    "load",
    "main",
    "num",
    "pl",
    "plain",
    "readable",
    "render",
    "sev_chip",
    "svg_map",
    "tab_of",
    "val_html",
    "val_pair",
    "where_html",
    "xlsx_link",
]

# The stylesheet is plain CSS in the css block of assets/report-style.md. Colours come from --color-* theme variables when the
# page showing the report defines them; the fallbacks (light, plus a dark set for the system's dark mode)
# apply everywhere else.
UTC_TZ = dt.timezone.utc  # noqa: UP017 - datetime.UTC needs Python 3.11; the skill supports 3.10

STYLE_FILE = Path(__file__).resolve().parent.parent / "assets" / "report-style.md"
CSS_FENCE_OPEN, CSS_FENCE_CLOSE = "```css\n", "\n```"


def _load_css(text: str) -> str:
    """The stylesheet inside the css fence of report-style.md."""
    start = text.index(CSS_FENCE_OPEN) + len(CSS_FENCE_OPEN)
    return text[start : text.index(CSS_FENCE_CLOSE, start) + 1]


CSS = _load_css(STYLE_FILE.read_text(encoding="utf-8"))


def render(
    scan,
    plan=None,
    applied=None,
    decisions=None,
    narrative=None,
    open_tab="summary",
    context=None,
    judgments=None,
):
    narrative, decisions, ctx = narrative or {}, decisions or {}, context or {}
    impacts = narrative.get("impacts", {})
    ctx_changes = ctx.get("changes", {})
    kept, dismissed = [], []
    for f in scan["findings"]:
        d = decisions.get(f["id"], {})
        f = dict(f, note=d.get("note", ""))
        if d.get("severity") in SEV_LABEL:
            f["severity"] = d["severity"]
        (dismissed if d.get("status") == "dismiss" else kept).append(f)
    kept += judgment_findings(
        judgments if isinstance(judgments, list) else (judgments or {}).get("items")
    )
    change_of = {}
    for ch in (plan or {}).get("changes", []):
        for i in ch["finding_ids"]:
            change_of.setdefault(i, ch)
    status_of = {r["n"]: r for r in (applied or {}).get("results", [])}
    n_applied = sum(1 for r in status_of.values() if r["status"] == "applied")

    def status(ch):
        if not ch:
            return "manual"
        st = (status_of.get(ch["n"]) or {}).get("status")
        return (
            "fixed" if st == "applied" else "skipped" if st == "skipped" else "proposed"
        )

    # one row per change (or per cell when there's no change): related findings merge into one row
    def group_rows(items):
        rows, idx = [], {}
        by_cell = {
            (f.get("sheet"), f.get("cell")): change_of[f["id"]]
            for f in items
            if f["id"] in change_of and f.get("cell")
        }
        for f in sorted(items, key=lambda f: (SEV_ORDER[f["severity"]], f["id"])):
            ch = change_of.get(f["id"]) or by_cell.get((f.get("sheet"), f.get("cell")))
            k = (
                ("ch", ch["n"])
                if ch
                else ("cell", f.get("sheet"), f.get("cell") or f["check"])
            )
            if k in idx:
                idx[k]["items"].append(f)
                continue
            idx[k] = {
                "items": [f],
                "change": ch,
                "sev": f["severity"],
                "area": tab_of(f),
                "status": status(ch),
            }
            rows.append(idx[k])
        for r in rows:
            verified = [
                f for f in r["items"] if f.get("basis", "verified") == "verified"
            ]
            r["basis"] = "verified" if verified else "judgment"
            if (
                verified and verified[0] is not r["items"][0]
            ):  # lead with the verified finding
                r["items"].remove(verified[0])
                r["items"].insert(0, verified[0])
                r["sev"], r["area"] = verified[0]["severity"], tab_of(verified[0])
            if r["basis"] == "judgment" and r["status"] == "manual":
                r["status"] = "question"
        return rows

    rows_all = group_rows(kept)
    open_rows = [r for r in rows_all if r["status"] != "fixed"]
    sheet_ix = {s["sheet"]: i for i, s in enumerate(scan["sheets"])}

    def change_chip(r):
        ch = r["change"]
        if not ch and r["basis"] == "judgment":
            return "<span class='chip basis-j' title='AI judgment: worth asking the owner, not proof of an error'>Ask the owner</span>"
        if not ch:
            return "<span class='chip manual' title='Needs knowledge of the model; never changed automatically'>Needs you</span>"
        st = r["status"]
        if st == "fixed":
            return f"<span class='chip applied'>#{ch['n']} · Fixed</span>"
        if st == "skipped":
            return f"<span class='chip skipped'>#{ch['n']} · Skipped</span>"
        return (
            f"<span class='chip safe' title='Safe to apply'>#{ch['n']} · safe</span>"
            if ch["risk"] == "safe"
            else f"<span class='chip confirm' title='Could be intentional: check before applying'>#{ch['n']} · confirm</span>"
        )

    def row_html(r, filterable=True):
        f0 = r["items"][0]
        label = f0.get("label") or ""
        imp = next((impacts[f["id"]] for f in r["items"] if f["id"] in impacts), "")
        also = [f for f in r["items"][1:] if f["description"] != f0["description"]]
        grid = next((f["grid"] for f in r["items"] if f.get("grid")), None)
        notes = [f["note"] for f in r["items"] if f.get("note")]
        cls = (
            f" class='f a-{r['area']} sev-{r['sev']} st-{r['status']} b-{r['basis']} sh-{sheet_ix.get(f0.get('sheet'), 'x')}'"
            if filterable
            else ""
        )
        ids = ", ".join(f["id"] for f in r["items"])
        qs = [f["question"] for f in r["items"] if f.get("question")]
        basis = (
            "<span class='chip basis-j' title='AI judgment: detected by rule, but only the owner can say if it is wrong'>Question</span>"
            if r["basis"] == "judgment"
            else ""
        )
        return (
            f"<tr{cls} title='{E(ids)}'><td><div class='sevcell'>{sev_chip(r['sev'])}{basis}</div></td>"
            f"<td>{where_html(f0.get('sheet'), f0.get('cell'), label)}</td>"
            f"<td><div class='what'>{E(readable(f0['description']))}</div>"
            + "".join(
                f"<div class='also'>Also: {E(readable(a['description']))}</div>"
                for a in also
            )
            + "".join(
                f"<div class='q'><b>Question for the owner:</b> {E(q)}</div>"
                for q in qs
            )
            + (f"<div class='impact'><b>Impact:</b> {E(imp)}</div>" if imp else "")
            + f"<div class='fix'><b>How to fix:</b> {E(f0['fix'])}</div>"
            + "".join(f"<div class='rev'><b>Reviewer:</b> {E(n)}</div>" for n in notes)
            + grid_html(grid, r["sev"])
            + f"</td><td>{change_chip(r)}</td></tr>"
        )

    def table(rows, filterable=True, empty="Nothing found."):
        if not rows:
            return f"<p class='empty'>{empty}</p>"
        return (
            "<table><thead><tr><th style='width:96px'>Severity</th><th style='width:210px'>Where</th>"
            "<th>What's wrong and how to fix it</th><th style='width:130px'>Change</th></tr></thead><tbody>"
            + "".join(row_html(r, filterable) for r in rows)
            + "</tbody></table>"
        )

    perf = scan.get("performance", {})
    conv_notes = [
        n
        for n in scan["notes"]
        if n["note"].startswith(("convention", "no_convention"))
    ]
    other_notes = [n for n in scan["notes"] if n not in conv_notes] + list(
        ctx.get("notes", [])
    )
    incomplete = any(n["note"] == "scan_capped" for n in other_notes)
    generated = ctx.get("generated") or dt.datetime.now(UTC_TZ).strftime(
        "%d %b %Y, %H:%M UTC"
    )
    open_c = Counter(r["sev"] for r in open_rows if r["basis"] == "verified")
    [r for r in open_rows if r["basis"] == "judgment"]
    q_items = [f for r in open_rows for f in r["items"] if f.get("basis") == "judgment"]
    plan_changes = (plan or {}).get("changes", [])
    manual_n = sum(1 for r in rows_all if r["status"] == "manual")
    if incomplete:
        vk, mark = "v-warn", "!"
        head = (
            "Scan incomplete: some checks reached their limits. "
            f"Completed checks found {open_c['critical']} critical and "
            f"{open_c['warning']} warning issues still open; review the coverage "
            "notes for what remains unchecked."
        )
    elif open_c["critical"]:
        vk, mark = "v-crit", "!"
        head = (
            f"{pl(open_c['critical'], 'error')} {'is' if open_c['critical'] == 1 else 'are'} showing in the model"
            + (
                f", plus {pl(open_c['warning'], 'issue')} that could give wrong numbers."
                if open_c["warning"]
                else "."
            )
        )
    elif open_c["warning"]:
        vk, mark = "v-warn", "!"
        head = f"No errors showing, but {pl(open_c['warning'], 'issue')} could give wrong numbers."
    else:
        vk, mark = "v-ok", "0"
        head = "The checks that ran found no open errors or risky formulas." + (
            f" {pl(open_c['info'], 'suggestion')} still open." if open_c["info"] else ""
        )
    if any(n["note"] == "values_not_cached" for n in scan["notes"]):
        head += (
            f" Skipped because the file has no saved results: {VALUE_CHECKS_SKIPPED}."
        )
    nxt = ""
    if plan_changes:
        left = [
            c
            for c in plan_changes
            if (status_of.get(c["n"]) or {}).get("status") != "applied"
        ]
        safe_n = sum(1 for c in left if c["risk"] == "safe")
        if n_applied:
            nxt = (
                f"{pl(n_applied, 'change')} applied to a copy ({E(Path(applied['copy']).name)}); your original wasn't touched."
                + (
                    f" {pl(len(left), 'more change')} {'is' if len(left) == 1 else 'are'} waiting for your OK."
                    if left
                    else ""
                )
            )
        elif left:
            nxt = (
                f"{pl(len(left), 'change')} {'is' if len(left) == 1 else 'are'} ready for your OK ({safe_n} safe, {len(left) - safe_n} to check first)."
                " Reply in chat with the numbers to apply; they go into a copy."
            )
        if manual_n:
            nxt += f" {pl(manual_n, 'item')} can't be fixed automatically."
    if q_items:
        nxt += f" {pl(len(q_items), 'question')} for the model owner below."
    verdict = (
        f"<div class='verdict {vk}'><div class='v-mark'>{mark}</div><div>"
        f"<div class='v-head'>{E(head)}</div>"
        + (f"<div class='v-next'>{nxt}</div>" if nxt else "")
        + (
            f"<div class='v-sum'>{E(narrative['summary'])}</div>"
            if narrative.get("summary")
            else ""
        )
        + "</div></div>"
    )

    def tile(key, name):
        rs = [r for r in rows_all if r["area"] == key]
        c = Counter(
            r["sev"] for r in rs if r["status"] != "fixed" and r["basis"] == "verified"
        )
        c["q"] = sum(
            1 for r in rs if r["status"] != "fixed" and r["basis"] == "judgment"
        )
        fixed = sum(1 for r in rs if r["status"] == "fixed")
        total_open = sum(c.values())
        score = ""
        if key == "structure" and perf:
            parts = [
                f"{perf[k]} {lab}"
                for k, lab in (("reds", "red"), ("yellows", "yellow"))
                if perf.get(k)
            ]
            score = "Performance limits exceeded: " + (
                ", ".join(parts) if parts else "none"
            )
        if not rs:
            if incomplete:
                return (
                    f"<div class='tile'><div class='t-top'><span class='t-name'>{E(name)}</span>"
                    "<span class='t-big'>Incomplete</span></div>"
                    "<div class='t-foot'>No findings in completed checks; scan coverage is limited.</div></div>"
                )
            return (
                f"<div class='tile clear'><div class='t-top'><span class='t-name'>{E(name)}</span><span><span class='t-big'>0</span>"
                f"<span class='t-unit'>open</span></span></div><div class='t-foot'>Nothing found by the checks that ran{' · ' + score if score else ''}</div></div>"
            )
        tot = max(1, len(rs))
        bar = "".join(
            f"<i class='b-{k}' style='width:{v / tot * 100:.1f}%'></i>"
            for k, v in (
                ("c", c["critical"]),
                ("w", c["warning"]),
                ("i", c["info"]),
                ("q", c["q"]),
                ("f", fixed),
            )
            if v
        )
        leg = "".join(
            f"<span><i class='sw {k}'></i><b>{v}</b> {lab}</span>"
            for k, v, lab in (
                ("c", c["critical"], "critical"),
                ("w", c["warning"], "warning"),
                ("i", c["info"], "suggestion" if c["info"] == 1 else "suggestions"),
                ("q", c["q"], "question" if c["q"] == 1 else "questions"),
                ("f", fixed, "fixed"),
            )
            if v
        )
        perf_note = f"<div class='t-foot'>{score}</div>" if score else ""
        return (
            f"<div class='tile'><div class='t-top'><span class='t-name'>{E(name)}</span><span><span class='t-big'>{total_open}</span>"
            f"<span class='t-unit'>open</span></span></div><div class='bar'>{bar}</div><div class='t-leg'>{leg}</div>"
            + perf_note
            + "</div>"
        )

    tiles = (
        "<div class='grid areas'>" + "".join(tile(k, n) for k, n in AREAS) + "</div>"
    )
    fix_first = [
        r for r in open_rows if r["sev"] != "info" and r["basis"] == "verified"
    ][:8]
    fixed_rows = len(rows_all) - len(open_rows)
    fix_html = table(fix_first, False, "Nothing critical or risky is left open.")
    if fixed_rows:
        fix_html += f"<p class='sub' style='margin-top:8px'>{pl(fixed_rows, 'issue')} already fixed in the copy {'is' if fixed_rows == 1 else 'are'} not listed.</p>"

    outs = [o for o in ctx.get("outputs", []) if o.get("before") is not None]
    has_applied = any("applied" in o for o in outs)
    has_preview = any("preview" in o for o in outs)
    key_results = ""
    if outs and (has_applied or has_preview):
        head_cols = (
            "<th>Now</th>"
            + ("<th>In the fixed copy</th>" if has_applied else "")
            + ("<th>If every change is applied</th>" if has_preview else "")
        )
        body = []
        for o in outs:
            nf = (
                (lambda v: f"{v * 100:,.1f}%" if is_num(v) else num(v))
                if o.get("pct")
                else num
            )
            dl = (
                (
                    lambda a, b: (
                        f"<span class='delta'>{(b - a) * 100:+.1f} pts</span>"
                        if is_num(a) and is_num(b) and abs(b - a) > 1e-9
                        else (
                            "<span class='delta'>no change</span>"
                            if is_num(a) and is_num(b)
                            else ""
                        )
                    )
                )
                if o.get("pct")
                else delta
            )
            tds = f"<td class='num'>{nf(o['before'])}</td>"
            if has_applied:
                tds += f"<td class='num after'>{nf(o.get('applied'))} {dl(o['before'], o.get('applied'))}</td>"
            if has_preview:
                tds += f"<td class='num'>{nf(o.get('preview'))} {dl(o['before'], o.get('preview'))}</td>"
            body.append(
                f"<tr><td>{where_html(*o['where'].split('!', 1), o.get('label', ''))}</td>{tds}</tr>"
            )
        key_results = (
            f"<h2>How the key results move</h2><table class='kr'><thead><tr><th style='width:240px'>Result</th>{head_cols}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table><p class='sub' style='margin-top:6px'>Results are the totals nothing else in the model uses.</p>"
        )

    conv_html = (
        "".join(
            f"<p>{E(cap(n['detail']))} <span class='sub'>({'from the legend in the file' if n['note'] == 'convention_from_legend' else 'learned from the cells' if n['note'] == 'convention_detected' else 'formatting not graded'})</span></p>"
            for n in conv_notes
        )
        or "<p class='sub'>None detected.</p>"
    )
    notes_html = "".join(
        f"<div class='note warn'><div><b>{E(NOTE_TITLES.get(n['note'], cap(n['note'].replace('_', ' '))))}:</b> {E(cap(n['detail']))}</div></div>"
        for n in other_notes
    )
    scope = (
        f"<div class='card'><h3>Scope</h3><dl class='kv'><dt>Tabs</dt><dd>{scan['tabs']}</dd><dt>Formulas</dt><dd>{scan['formulas']:,}</dd>"
        f"<dt>Filled cells</dt><dd>{scan['filled_cells']:,}</dd><dt>Readers' Excel</dt><dd>{E(narrative.get('excel_target') or excel_line(scan))}</dd>"
        "<dt>Not checked</dt><dd>Charts, macros (VBA) and real calculation speed</dd></dl></div>"
    )
    questions = ""
    if q_items:
        shown = sorted(q_items, key=lambda f: (SEV_ORDER[f["severity"]], f["id"]))[:12]
        questions = (
            "<h2>Questions for the model owner</h2><p class='sub'>Found by the checks or the reviewer, but only someone who knows the "
            "business can say whether they're wrong. None of these is counted as an error.</p><div class='qlist'>"
            + "".join(
                f"<div class='qitem'><div class='qmeta'>{where_html(f.get('sheet'), f.get('cell'), f.get('label', ''))}"
                f"<span class='sub'>{E(dict(AREAS).get(tab_of(f), ''))}</span></div><div class='what'>{E(readable(f['description']))}</div>"
                f"<div class='qq'>{E(f.get('question') or 'Is this intended?')}</div></div>"
                for f in shown
            )
            + "</div>"
            + (
                f"<p class='sub' style='margin-top:8px'>{pl(len(q_items) - len(shown), 'more question')} on the Issues tab.</p>"
                if len(q_items) > len(shown)
                else ""
            )
        )
    summary = (
        f"{verdict}{notes_html}<h2>At a glance</h2>{tiles}<h2>Fix first</h2>{fix_html}{questions}{key_results}"
        f"<div class='grid' style='margin-top:24px'><div class='card'><h3>Formatting conventions in this model</h3>{conv_html}</div>{scope}</div>"
        f"<div class='disclaimer'>{E(DISCLAIMER)}</div>"
    )

    present_areas = [(k, n) for k, n in AREAS if any(r["area"] == k for r in rows_all)]
    present_sheets = [
        s["sheet"]
        for s in scan["sheets"]
        if any(r["items"][0].get("sheet") == s["sheet"] for r in rows_all)
    ]
    has_nosheet = any(not r["items"][0].get("sheet") for r in rows_all)

    def fgroup(label, name, opts):
        out = [
            f"<div class='fg' role='radiogroup' aria-label='{label}'><span class='fl'>{label}</span>"
        ]
        for i, (key, text, n) in enumerate(opts):
            fid = f"{name}-{key}"
            out.append(
                f"<input type='radio' name='{name}' id='{fid}'{' checked' if i == 0 else ''}><label for='{fid}'>{E(text)}"
                + (f"<span class='n'>{n}</span>" if n is not None else "")
                + "</label>"
            )
        return "".join(out) + "</div>"

    def cnt(pred):
        return sum(1 for r in rows_all if pred(r))

    filt_css = []
    groups = []
    if len(present_areas) > 1:
        groups.append(
            fgroup(
                "Area",
                "fa",
                [("all", "All", None)]
                + [
                    (k, n, cnt(lambda r, k=k: r["area"] == k)) for k, n in present_areas
                ],
            )
        )
        filt_css += [
            f"#p-issues:has(#fa-{k}:checked) tr.f:not(.a-{k}){{display:none}}"
            for k, _ in present_areas
        ]
    sev_opts = [
        (k, SEV_LABEL[k], cnt(lambda r, k=k: r["sev"] == k))
        for k in SEV_ORDER
        if any(r["sev"] == k for r in rows_all)
    ]
    if len(sev_opts) > 1:
        groups.append(fgroup("Severity", "fs", [("all", "All", None)] + sev_opts))
        filt_css += [
            f"#p-issues:has(#fs-{k}:checked) tr.f:not(.sev-{k}){{display:none}}"
            for k, _, _ in sev_opts
        ]
    if any(r["basis"] == "judgment" for r in rows_all):
        groups.append(
            fgroup(
                "Basis",
                "fb",
                [
                    ("all", "All", None),
                    ("verified", "Verified", cnt(lambda r: r["basis"] == "verified")),
                    ("judgment", "Questions", cnt(lambda r: r["basis"] == "judgment")),
                ],
            )
        )
        filt_css += [
            f"#p-issues:has(#fb-{k}:checked) tr.f:not(.b-{k}){{display:none}}"
            for k in ("verified", "judgment")
        ]
    st_opts = [("open", "Open", cnt(lambda r: r["status"] != "fixed"))]
    if any(r["status"] == "manual" for r in rows_all):
        st_opts.append(("manual", "Needs you", cnt(lambda r: r["status"] == "manual")))
    if fixed_rows:
        st_opts.append(("fixed", "Fixed in copy", fixed_rows))
    groups.append(fgroup("Status", "fst", [("all", "All", None)] + st_opts))
    filt_css += [
        "#p-issues:has(#fst-open:checked) tr.f.st-fixed{display:none}",
        "#p-issues:has(#fst-manual:checked) tr.f:not(.st-manual){display:none}",
        "#p-issues:has(#fst-fixed:checked) tr.f:not(.st-fixed){display:none}",
    ]
    if len(present_sheets) + has_nosheet > 1:
        sh_opts = [
            (str(sheet_ix[s]), s, cnt(lambda r, s=s: r["items"][0].get("sheet") == s))
            for s in present_sheets
        ]
        if has_nosheet:
            sh_opts.append(
                ("x", "Whole workbook", cnt(lambda r: not r["items"][0].get("sheet")))
            )
        groups.append(fgroup("Tab", "fsh", [("all", "All", None)] + sh_opts))
        filt_css += [
            f"#p-issues:has(#fsh-{k}:checked) tr.f:not(.sh-{k}){{display:none}}"
            for k, _, _ in sh_opts
        ]
    sevleg = (
        "<div class='sevleg'>"
        + "".join(
            f"<span>{sev_chip(k)} {SEV_HELP[k].lower()}</span>" for k in SEV_ORDER
        )
        + "<span><span class='chip basis-j'>Question</span> AI judgment for the owner to confirm</span>"
        + "<span>Hover a row to see its finding ID.</span></div>"
    )
    issues = (
        f"<h2>Issues</h2><p class='sub'>Every finding, in five areas. Formatting is graded against this model's own conventions. "
        f"Related findings on the same cells are combined into one row.</p><div class='filters'>{''.join(groups)}</div>{sevleg}"
        + table(
            rows_all,
            True,
            "No errors, hardcodes, broken patterns or formatting problems found.",
        )
    )
    if dismissed:
        issues += (
            f"<details class='judged'><summary>Reviewed and judged OK ({len(dismissed)})</summary>"
            + table(group_rows(dismissed), False)
            + "</details>"
        )

    changes_html = changes_tab(plan, applied, status_of, ctx_changes, kept, dismissed)
    mapping = map_tab(scan, narrative, open_rows)
    perf_rows = [r for r in rows_all if is_perf(r["items"][0])]
    performance = performance_tab(
        perf,
        "<h2>Performance issues</h2>" + table(perf_rows, False) if perf_rows else "",
    )

    def tab_count(rows):
        c = Counter(r["sev"] for r in rows)
        if not rows:
            return ""
        kind = "crit" if c["critical"] else "warn" if c["warning"] else ""
        return f"<span class='cnt {kind}'>{len(rows)}</span>"

    left_changes = [
        c
        for c in plan_changes
        if (status_of.get(c["n"]) or {}).get("status") != "applied"
    ]
    chg_count = (
        f"<span class='cnt'>{len(left_changes)}</span>"
        if left_changes
        else ("<span class='cnt ok'>0</span>" if plan_changes else "")
    )
    perf_dot = (
        "<span class='cnt crit'>!</span>"
        if perf.get("reds")
        else "<span class='cnt warn'>!</span>"
        if perf.get("yellows")
        else ""
    )
    tab_defs = [
        ("summary", "Summary", ""),
        ("issues", "Issues", tab_count(open_rows)),
        ("changes", "Changes", chg_count),
        ("map", "Map", ""),
        ("performance", "Performance", perf_dot),
    ]
    tabs_html = "".join(
        f"<input type='radio' name='tab' id='t-{k}'{' checked' if k == open_tab else ''}><label for='t-{k}'>{lab}{c}</label>"
        for k, lab, c in tab_defs
    )
    rows_dl = issue_rows(kept, change_of, status_of)
    source = ctx.get("source") or ""
    meta = "".join(
        f"<span>{x}</span>"
        for x in (
            E(source) if source else "",
            f"Reviewed {E(generated)}",
            f"{pl(scan['tabs'], 'tab')}",
            f"{pl(scan['formulas'], 'formula')}",
        )
        if x
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><title>Audit: {E(scan["workbook"])}</title><style>{CSS}{"".join(filt_css)}</style></head><body>
<header class='top'><div class='wrap'><div class='eyebrow'>Spreadsheet evaluation</div><h1>{E(scan["workbook"])}</h1><div class='meta'>{meta}</div></div></header>
<div class='tabs'>{tabs_html}<div class='panels'><div class='wrap'>
<section id='p-summary'>{summary}</section>
<section id='p-issues'>{issues}</section>
<section id='p-changes'><h2 class='print-only'>Changes</h2>{changes_html}</section>
<section id='p-map'>{mapping}</section>
<section id='p-performance'>{performance}</section>
<footer>{xlsx_link(rows_dl, scan["workbook"], generated, head)}{csv_link(rows_dl, scan["workbook"])}
<span>This report contains labels and formulas from the model. Share it as you would the model itself. {E(DISCLAIMER)}</span></footer>
</div></div></div></body></html>"""


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2

    def opt(k):
        return argv[argv.index(k) + 1] if k in argv else None

    scan = load(argv[0])
    out = Path(argv[1])
    page = render(
        scan,
        load(opt("--changes")),
        load(opt("--applied")),
        load(opt("--decisions")),
        load(opt("--narrative")),
        opt("--tab") or "summary",
        load(opt("--context")),
        load(opt("--judgments")),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(
        f"Wrote {out} ({out.stat().st_size / 1024:.0f} KB). Tabs: Summary, Issues, Changes, Map, Performance."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
