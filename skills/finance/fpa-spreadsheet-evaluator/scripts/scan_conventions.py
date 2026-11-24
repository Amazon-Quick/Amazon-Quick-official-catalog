"""
description: Formatting conventions learned from the workbook (legend or majority style) and the checks against them.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from openpyxl.utils import get_column_letter
from scan_findings import Findings, add_grouped, data_text
from scan_formats import COLOR_WORDS, is_num
from scan_limits import CONVENTION_SHARE, MIN_ROLE_CELLS
from scan_load import Workbook

ROLE_WORDS = [
    (
        "link",
        re.compile(
            r"another (tab|sheet)|other (tab|sheet)|link|pulls?|cross[- ]?(tab|sheet)|reference",
            re.I,
        ),
    ),
    (
        "input",
        re.compile(r"input|assumption|hard[- ]?cod|typed|enter|change|driver", re.I),
    ),
    ("formula", re.compile(r"formula|calculat|computed", re.I)),
]


def read_legend(wb: Workbook):
    legend = {}
    for s in wb.sheets.values():
        for x in s.cells.values():
            if not isinstance(x.raw, str) or x.formula or len(x.raw) > 200:
                continue
            words = set(re.findall(r"[a-z]+", x.raw.lower()))
            colors = words & COLOR_WORDS
            if not colors or not re.search(r"=|:|means|is |are |-", x.raw):
                continue
            role = next((r for r, rx in ROLE_WORDS if rx.search(x.raw)), None)
            if not role:
                continue
            attr = (
                "fill"
                if re.search(
                    r"fill|shad|background|highlight|cell colou?r", x.raw, re.I
                )
                else "font"
            )
            named = next(iter(colors))
            named = {"black": "auto", "grey": "gray"}.get(named, named)
            own = x.fill if attr == "fill" else x.font
            value = own if own not in ("auto", "none") else named
            legend[role] = (attr, value, f"{s.name}!{x.coord}")
    return legend


def nice(v):
    return {"auto": "black (default)", "none": "no fill"}.get(v, v)


def conventions(wb: Workbook, fs: Findings):
    roles = {"input": [], "formula": [], "link": []}
    for s in wb.sheets.values():
        if s.hidden or s.is_data:
            continue
        for r, xs in s.rows.items():
            if r <= s.header_row:
                continue
            nums = sorted(
                x.raw
                for x in xs
                if not x.formula
                and isinstance(x.raw, int)
                and not isinstance(x.raw, bool)
            )
            period_header = (
                len(nums) >= 3
                and all(b - a == 1 for a, b in zip(nums, nums[1:], strict=False))
                and len(nums) == sum(1 for x in xs if not x.formula and is_num(x.raw))
            )
            for x in xs:
                if x.formula:
                    roles["link" if (x.links - {"[external]"}) else "formula"].append(x)
                elif is_num(x.raw) and not period_header:
                    roles["input"].append(x)
    legend = read_legend(wb)
    conv, source = {}, {}
    for role, xs in roles.items():
        if role in legend:
            attr, value, where = legend[role]
            conv[role] = {attr: value}
            source[role] = f"legend at {data_text(where)}"
            continue
        if len(xs) < MIN_ROLE_CELLS:
            continue
        c = {}
        for attr in ("font", "fill"):
            cnt = Counter(getattr(x, attr) for x in xs)
            top, n = cnt.most_common(1)[0]
            if n >= CONVENTION_SHARE * len(xs):
                c[attr] = top
        if c:
            conv[role] = c
            source[role] = f"{len(xs)} cells"

    # a style only counts as a marker if it tells the role apart from formulas
    def marker(role):
        if role not in conv:
            return {}
        if role == "formula":
            return conv[role]
        other = conv.get("formula", {})
        return {
            a: v for a, v in conv[role].items() if role in legend or other.get(a) != v
        }

    m_input, m_link, m_form = marker("input"), marker("link"), conv.get("formula", {})
    desc = []
    if m_input:
        desc.append(
            "inputs = "
            + " + ".join(
                f"{'black (default)' if v == 'auto' else v} {a}"
                for a, v in m_input.items()
            )
            + f" ({source['input']})"
        )
    if m_form:
        desc.append(
            "formulas = "
            + " + ".join(
                f"{v} {a}"
                for a, v in m_form.items()
                if not (a == "fill" and v == "none")
            ).strip(" +")
            + f" ({source['formula']})"
        )
    if m_link:
        desc.append(
            "cross-tab formulas = "
            + " + ".join(f"{v} {a}" for a, v in m_link.items())
            + f" ({source['link']})"
        )
    desc = [d.replace("auto font", "black (default) font") for d in desc]
    if legend:
        wb.notes.append({"note": "convention_from_legend", "detail": "; ".join(desc)})
    elif m_input or m_link:
        wb.notes.append({"note": "convention_detected", "detail": "; ".join(desc)})
    else:
        wb.notes.append(
            {
                "note": "no_convention_found",
                "detail": "no consistent styling that sets inputs apart from formulas (or too few cells to tell); style checks skipped",
            }
        )
    brk, as_input, link_brk = defaultdict(dict), defaultdict(dict), defaultdict(dict)
    if m_input:
        for x in roles["input"]:
            off = [a for a, v in m_input.items() if getattr(x, a) != v]
            if off:
                brk[x.sheet][(x.r, x.c)] = " and ".join(
                    f"{a} is {nice(getattr(x, a))}, not {nice(m_input[a])}" for a in off
                )
        for x in roles["formula"] + roles["link"]:
            if all(getattr(x, a) == v for a, v in m_input.items()):
                as_input[x.sheet][(x.r, x.c)] = " + ".join(
                    f"{'black (default)' if v == 'auto' else v} {a}"
                    for a, v in m_input.items()
                )
    if m_link:
        for x in roles["link"]:
            if (x.sheet, x.r, x.c) in {
                (s, r, c) for s, p in as_input.items() for (r, c) in p
            }:
                continue
            off = [a for a, v in m_link.items() if getattr(x, a) != v]
            if off:
                link_brk[x.sheet][(x.r, x.c)] = " and ".join(
                    f"{a} is {nice(getattr(x, a))}, not {nice(m_link[a])}" for a in off
                )
    for sheet, p in brk.items():
        add_grouped(
            fs,
            "input_style_break",
            sheet,
            p,
            lambda k, rng: (
                f"Typed input not styled like the model's other inputs ({k})."
            ),
        )
    for sheet, p in as_input.items():
        add_grouped(
            fs,
            "formula_styled_as_input",
            sheet,
            p,
            lambda k, rng: (
                f"A formula styled like an input ({k}); looks safe to overwrite."
            ),
        )
    for sheet, p in link_brk.items():
        add_grouped(
            fs,
            "link_style_break",
            sheet,
            p,
            lambda k, rng: f"Cross-tab formula not styled like the others ({k}).",
        )
    # total rows: bold rows should share one border/fill style
    for s in wb.sheets.values():
        if s.hidden or s.is_data:
            continue
        emph = {}
        for r, xs in s.rows.items():
            nums = [x for x in xs if x.formula or is_num(x.raw)]
            if (
                r <= s.header_row
                or not nums
                or sum(x.bold for x in nums) * 2 <= len(nums)
            ):
                continue
            sig = Counter((x.top, x.bottom, x.fill) for x in nums).most_common(1)[0][0]
            emph[r] = (sig, min(x.c for x in nums), max(x.c for x in nums))
        if len(emph) >= 3:
            cnt = Counter(v[0] for v in emph.values())
            top, n = cnt.most_common(1)[0]
            if n >= CONVENTION_SHARE * len(emph):
                for r, (sig, c1, c2) in emph.items():
                    if sig != top:
                        want = (
                            ", ".join(
                                p
                                for p in (
                                    f"top border {top[0]}" if top[0] else "",
                                    f"bottom border {top[1]}" if top[1] else "",
                                    f"{top[2]} fill" if top[2] != "none" else "",
                                )
                                if p
                            )
                            or "no borders"
                        )
                        fs.add(
                            "total_style_break",
                            s.name,
                            f"{get_column_letter(c1)}{r}:{get_column_letter(c2)}{r}",
                            f"Total row styled differently from the tab's other total rows (they have {want}).",
                        )
    return {
        "roles": dict(conv.items()),
        "source": source,
        "legend": bool(legend),
    }
