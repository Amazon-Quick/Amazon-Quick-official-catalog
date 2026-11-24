"""
description: Formula pattern and Excel version checks: lookup styles, IFERROR masking, redundant formulas and functions newer than the target Excel.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from scan_catalog import FUNCTION_VERSION, TARGETS, VERSION_ORDER
from scan_findings import Findings, add_grouped, data_text
from scan_formula_text import func_calls, functions_used, lookup_family, mask_strings
from scan_limits import CONVENTION_SHARE, MIN_ROLE_CELLS
from scan_load import Workbook


def excel_info(wb: Workbook, target: str):
    used = defaultdict(list)
    for x in wb.formulas:
        for fn in functions_used(x.formula):
            if fn in FUNCTION_VERSION:
                used[fn].append(x)
    need = max(
        (FUNCTION_VERSION[f] for f in used), key=VERSION_ORDER.index, default=None
    )
    tgt = TARGETS.get(target or "auto")
    if tgt is None:  # auto: what the file proves, else the safest choice
        effective = need if need in ("2021", "365") else "compatible"
    else:
        effective = tgt
    return {
        "target_setting": target or "auto",
        "functions_needing_newer_excel": {f: FUNCTION_VERSION[f] for f in used},
        "file_needs_at_least": need,
        "effective_target": effective,
        "_used": used,
    }


def modern_ok(effective):
    return effective in ("2021", "365")


def check_compat(wb: Workbook, fs: Findings, info):
    tgt = TARGETS.get(info["target_setting"])
    if tgt is None:
        return
    pts = defaultdict(dict)
    for fn, xs in info["_used"].items():
        if VERSION_ORDER.index(FUNCTION_VERSION[fn]) > VERSION_ORDER.index(tgt):
            for x in xs:
                pts[x.sheet][(x.r, x.c)] = fn
    for sheet, p in pts.items():
        add_grouped(
            fs,
            "compat_function",
            sheet,
            p,
            lambda k, rng: (
                f"{k} needs Excel {FUNCTION_VERSION[k] if FUNCTION_VERSION[k] != '365' else 'Microsoft 365'}"
                f" or newer; readers on Excel {tgt} see #NAME?."
            ),
        )


def check_formula_patterns(wb: Workbook, fs: Findings):
    approx, hardcol, mask_, redund = (
        defaultdict(dict),
        defaultdict(dict),
        defaultdict(dict),
        defaultdict(dict),
    )
    fam = Counter()
    fam_cells = defaultdict(list)
    for x in wb.formulas:
        calls = func_calls(x.formula)
        for name, args, *_ in calls:
            if name in ("VLOOKUP", "HLOOKUP"):
                if len(args) == 3:
                    approx[x.sheet][(x.r, x.c)] = name
                if (
                    len(args) >= 3
                    and re.fullmatch(r"\d+", args[2])
                    and int(args[2]) >= 2
                ):
                    hardcol[x.sheet][(x.r, x.c)] = (name, args[2])
            if (
                name == "IFERROR"
                and len(args) == 2
                and args[1].strip() in ("0", '""', '"-"', '"n/a"', '"N/A"')
            ):
                inner = functions_used(args[0])
                if not inner & {
                    "VLOOKUP",
                    "HLOOKUP",
                    "XLOOKUP",
                    "MATCH",
                    "XMATCH",
                    "INDEX",
                    "LOOKUP",
                }:
                    mask_[x.sheet][(x.r, x.c)] = args[1].strip()
        body = x.formula[1:].strip()
        if body.startswith("+"):
            redund[x.sheet][(x.r, x.c)] = "leading +"
        m = re.fullmatch(r"SUM\((.*)\)", body, re.I | re.S)
        if (
            m
            and len(calls) == 1
            and "," not in m.group(1)
            and ":" not in m.group(1)
            and re.search(r"[-+*/]", mask_strings(m.group(1)))
        ):
            redund[x.sheet][(x.r, x.c)] = "SUM around a single expression"
        f = lookup_family(x.formula)
        if f:
            fam[f] += 1
            fam_cells[f].append(x)
    for sheet, p in approx.items():
        add_grouped(
            fs,
            "vlookup_approx",
            sheet,
            p,
            lambda k, rng: (
                f"{k} has no fourth argument, so it does an approximate match. On an unsorted list it returns wrong values without any error."
            ),
        )
    for sheet, p in hardcol.items():
        add_grouped(
            fs,
            "lookup_hardcoded_col",
            sheet,
            p,
            lambda k, rng: (
                f"{k[0]} returns column {k[1]} by position; inserting a column in the lookup table silently changes the result."
            ),
        )
    for sheet, p in mask_.items():
        add_grouped(
            fs,
            "iferror_masking",
            sheet,
            p,
            lambda k, rng: (
                f"IFERROR turns any error in the calculation into {data_text(k)}, so real mistakes are hidden."
            ),
        )
    for sheet, p in redund.items():
        add_grouped(
            fs,
            "redundant_formula",
            sheet,
            p,
            lambda k, rng: f"Formula has a redundant {k}.",
        )
    total = sum(fam.values())
    if total >= MIN_ROLE_CELLS:
        top, n = fam.most_common(1)[0]
        if n >= CONVENTION_SHARE * total and n < total:
            pts = defaultdict(dict)
            for f, xs in fam_cells.items():
                if f != top:
                    for x in xs:
                        pts[x.sheet][(x.r, x.c)] = (f, top)
            for sheet, p in pts.items():
                add_grouped(
                    fs,
                    "lookup_style_inconsistent",
                    sheet,
                    p,
                    lambda k, rng: (
                        f"Uses {k[0]}; the rest of the model does its lookups with {k[1]}."
                    ),
                )
    return {
        "lookup_families": dict(fam),
        "dominant": fam.most_common(1)[0][0] if fam else None,
    }
