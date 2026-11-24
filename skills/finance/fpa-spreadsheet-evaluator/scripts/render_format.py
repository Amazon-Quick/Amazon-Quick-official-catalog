#!/usr/bin/env python3
"""
description: Small HTML formatting helpers shared by the review and comparison reports.
last_updated: 2026-11-24

render_format.py - numbers, before/after values, cell references, formula diffs, mini cell view.

Every string from the workbook or from agent-written JSON is passed through E (html.escape) before it
goes into the page, including attribute values (E escapes both quote characters).
"""

from __future__ import annotations

import difflib
import html
import json
import re
from pathlib import Path

from render_taxonomy import SEV_HELP, SEV_LABEL

E = html.escape


def load(p):
    return (
        json.loads(Path(p).read_text(encoding="utf-8"))
        if p and Path(p).exists()
        else None
    )


XL_PREFIX = re.compile(r"_xl(?:fn|ws|udf)\.", re.I)


def plain(text):
    """Hide Excel's internal function prefixes (for example _xlfn.XLOOKUP) in what people read."""
    return XL_PREFIX.sub("", str(text or ""))


# A JSON string literal, as scan_workbook.data_text quotes workbook fragments inside finding descriptions.
QUOTED = re.compile(r'"(?:[^"\\\n]|\\.){0,400}"')


def _unescape_quoted(m):
    """Show a JSON-quoted fragment with its escapes decoded; keep control and format characters escaped."""
    quoted = m.group(0)
    if "\\" not in quoted:
        return quoted
    try:
        text = json.loads(quoted)
    except ValueError:
        return quoted
    return (
        '"'
        + "".join(ch if ch.isprintable() else f"\\u{ord(ch):04x}" for ch in text)
        + '"'
    )


def readable(text):
    """A finding description for people: Excel prefixes hidden, quoted workbook fragments decoded.

    Not for formulas (an Excel string literal is not JSON). The result still needs E() for HTML.
    """
    return QUOTED.sub(_unescape_quoted, plain(text))


def cap(text):
    text = str(text or "").strip()
    return text[:1].upper() + text[1:]


def pl(n, word, many=None):
    return f"{n:,} {word if n == 1 else (many or word + 's')}"


def num(v):
    """Short, readable number (or the error text)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v).upper()
    if isinstance(v, (int, float)):
        if v != 0 and abs(v) < 1:
            return f"{v:.4g}"
        if abs(v) >= 1000 or float(v).is_integer():
            return f"{v:,.0f}"
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    return E(str(v))


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def delta(before, after):
    if not (is_num(before) and is_num(after)):
        return ""
    d = after - before
    if abs(d) < 1e-9:
        return "<span class='delta'>no change</span>"
    sign = "+" if d > 0 else "−"
    pct = f", {sign}{abs(d) / abs(before) * 100:.1f}%" if before else ""
    return f"<span class='delta'>{sign}{num(abs(d))}{pct}</span>"


def val_pair(before, after):
    """Before/after text; extra decimals when the short form would hide the difference."""

    def show(v):
        if isinstance(v, dict):
            return (
                f"'{E(v['text'])}' (text)" if v.get("kind") == "text" else E(v["text"])
            )
        return num(v)

    b, a = show(before), show(after)
    if b == a and is_num(before) and is_num(after):
        b, a = (
            f"{before:,.4f}".rstrip("0").rstrip("."),
            f"{after:,.4f}".rstrip("0").rstrip("."),
        )
    return (
        f"<span class='old'>{b or '(blank)'}</span>",
        f"<span class='new'>{a or '(blank)'}</span>",
    )


def val_html(v):
    b, a = val_pair(v["before"], v["after"])
    return f"<span class='val'><span class='vl'>{E(v.get('label') or v['where'])}</span>{b} → {a}{delta(v['before'], v['after'])}</span>"


def where_html(sheet, cell, label=""):
    ref = E((sheet or "(workbook)") + (f"!{cell}" if cell else ""))
    lab = f"<span class='lab'>{E(label)}</span>" if label else ""
    return f"<div class='loc'>{lab}<span class='ref'>{ref}</span></div>"


def sev_chip(sev):
    return f"<span class='chip {sev}' title='{SEV_HELP[sev]}'>{SEV_LABEL[sev]}</span>"


TOKEN = re.compile(
    r'"[^"]*"|\'[^\']+\'!|\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?|[A-Za-z_][A-Za-z0-9_.]*!?'
    r"|\d+(?:\.\d+)?|\s+|."
)


def diff_html(old, new):
    old, new = plain(old), plain(new)
    a, b = TOKEN.findall(old), TOKEN.findall(new)
    o, n = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, a, b, autojunk=False
    ).get_opcodes():
        x, y = E("".join(a[i1:i2])), E("".join(b[j1:j2]))
        if tag == "equal":
            o.append(x)
            n.append(y)
            continue
        if x:
            o.append(f"<del>{x.replace(' ', '␣')}</del>")  # make changed spaces visible
        if y:
            n.append(f"<ins>{y.replace(' ', '␣')}</ins>")
    return (
        "<div class='diff'><div class='d-old'><span class='d-sign'>−</span><code>"
        + "".join(o)
        + "</code></div>"
        "<div class='d-new'><span class='d-sign'>+</span><code>"
        + "".join(n)
        + "</code></div></div>"
    )


def as_text(v):
    if isinstance(v, str):
        return v
    return num(v) if is_num(v) else str(v)


def grid_html(g, sev):
    if not g:
        return ""
    head = "<th></th>" + "".join(
        "<th class='gap'>…</th>" if c is None else f"<th>{E(c)}</th>" for c in g["cols"]
    )
    body = []
    for row in g["rows"]:
        if row is None:
            body.append(
                "<tr><th class='rn gap'>⋮</th>"
                + "".join("<td class='gap'></td>" for _ in g["cols"])
                + "</tr>"
            )
            continue
        tds = []
        for c in row["cells"]:
            if c is None:
                tds.append("<td class='gap'>…</td>")
                continue
            cls = " ".join(
                x
                for x in (
                    f"k-{c['k']}" if c.get("k") else "",
                    "hl" if c.get("hl") else "",
                )
                if x
            )
            title = f" title='{E(plain(c['f']))}'" if c.get("f") else ""
            tds.append(f"<td class='{cls}'{title}>{E(c.get('t', ''))}</td>")
        body.append(f"<tr><th class='rn'>{row['r']}</th>{''.join(tds)}</tr>")
    return (
        f"<details class='cells'><summary>Show the cells</summary><table class='mini {sev}'><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table><div class='mini-leg'>Outlined: the cells in this finding. "
        "Point at a cell to see its formula.</div></details>"
    )
