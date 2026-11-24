#!/usr/bin/env python3
"""
description: Match rows, columns and findings between two workbook versions by meaning, not position.
last_updated: 2026-11-24

compare_keys.py - row keys (label or ID), column keys (header or period), and finding identity.

Version loads one workbook and indexes every cell by (row key, column key), so inserting a row or a
month doesn't make everything below it look changed.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import scan_workbook as S
from openpyxl.utils import get_column_letter


def _norm(t):
    return " ".join(re.sub(r"[^a-z0-9%&]+", " ", str(t).lower()).split())


def _v(x):
    return None if x is None else (x.cached if x.formula else x.raw)


def _num(x):
    v = _v(x)
    return v if S.is_num(v) and not (x is not None and x.is_date) else None


def row_label(s, r):
    xs = sorted(s.rows.get(r, []), key=lambda y: y.c)
    first_val = next(
        (x.c for x in xs if x.formula or S.is_num(x.raw) or x.is_date), None
    )
    for x in xs:
        if (
            isinstance(x.raw, str)
            and not x.formula
            and x.raw.strip()
            and (first_val is None or x.c < first_val)
        ):
            return x.raw.strip()
    return None


def _key_column(s):
    """On a data tab, the first column if it holds (nearly) unique IDs."""
    if not s.is_data or not s.rows:
        return None
    c0 = min(x.c for x in s.cells.values())
    vals = [
        _v(s.cells.get((r, c0)))
        for r in s.rows
        if r > s.header_row and s.cells.get((r, c0)) is not None
    ]
    vals = [str(v).strip() for v in vals if v not in (None, "")]
    if len(vals) >= 5 and len(set(vals)) >= 0.95 * len(vals):
        return c0
    return None


def row_keys(s):
    keys, seen = {}, Counter()
    last, k_after = ("top",), 0
    kc = _key_column(s)
    for r in sorted(s.rows):
        if r <= s.header_row:
            keys[r] = ("T", r)
            continue
        if kc:
            v = _v(s.cells.get((r, kc)))
            if v not in (None, ""):
                keys[r] = ("K", str(v).strip())
                continue
        lab = row_label(s, r)
        if lab:
            n = _norm(lab)
            seen[n] += 1
            last, k_after = ("L", n, seen[n]), 0
            keys[r] = last
        else:
            k_after += 1
            keys[r] = ("A", last, k_after)
    return keys


def col_keys(s):
    P = getattr(s, "periods", None)
    hr = P["row"] if P else s.header_row
    keys, seen = {}, Counter()
    cols = sorted({x.c for x in s.cells.values()})
    last, k_after = ("left",), 0
    for c in cols:
        h = s.cells.get((hr, c)) if hr else None
        v = _v(h)
        pk = S.period_key(v) if v is not None else None
        if pk:
            keys[c] = ("P",) + pk
            last, k_after = keys[c], 0
        elif v not in (None, "") and not (h is not None and S.is_num(h.raw) and not pk):
            n = _norm(v)
            seen[n] += 1
            keys[c] = ("H", n, seen[n])
            last, k_after = keys[c], 0
        else:
            k_after += 1
            keys[c] = ("C", last, k_after)
    return keys


class Version:
    def __init__(self, path, excel_target):
        self.path = Path(path)
        self.wb = S.Workbook(self.path)
        self.scan = S.scan(
            self.path, excel_target
        )  # also gives each sheet its period layout (via a fresh workbook)
        for s in self.wb.sheets.values():
            s.periods = S.period_layout(s) if s.rows else None
            s.title_text = S.sheet_title_text(s) if s.rows else ""
        self.idx = {}
        for s in self.wb.sheets.values():
            rk, ck = row_keys(s), col_keys(s)
            cells = {}
            for (r, c), x in s.cells.items():
                if r in rk and c in ck:
                    cells.setdefault((rk[r], ck[c]), x)
            self.idx[s.name] = {"rk": rk, "ck": ck, "cells": cells}
        self.referenced = Counter()
        for x in self.wb.formulas:
            for sh, box, *_ in S.refs_in(x.formula):
                tgt = self.wb.resolve(sh) if sh else x.sheet
                if tgt and (box[2] - box[0] + 1) * (box[3] - box[1] + 1) <= 400:
                    for r in range(box[1], box[3] + 1):
                        for c in range(box[0], box[2] + 1):
                            self.referenced[(tgt, r, c)] += 1

    def token(self, sheet, r, c, rename=None):
        sheet_idx = self.idx.get(sheet)
        name = (rename or {}).get(sheet, sheet)
        if sheet_idx and r in sheet_idx["rk"] and c in sheet_idx["ck"]:
            return f"<{name}|{sheet_idx['rk'][r]}|{sheet_idx['ck'][c]}>"
        return f"<{name}|@{r},{c}>"

    def sem(self, x, rename=None):
        """The formula with each reference replaced by what it points at (tab, row label, column header)."""
        out, last = [], 0
        for sh, box, s0, e0, _ref in S.refs_in(x.formula):
            tgt = self.wb.resolve(sh) if sh else x.sheet
            c1, r1, c2, r2 = box
            if not tgt or r2 - r1 > 100_000 or c2 - c1 > 1000:
                continue
            t = self.token(tgt, r1, c1, rename) + (
                "" if (c1, r1) == (c2, r2) else ":" + self.token(tgt, r2, c2, rename)
            )
            out.append(x.formula[last:s0] + t)
            last = e0
        out.append(x.formula[last:])
        return re.sub(r"\s+", "", "".join(out))


def _label(s, r, c):
    return S.range_label(s, f"{get_column_letter(c)}{r}") if s is not None else ""


def _rng(cells):
    rects = S.rectangles(cells)
    return rects[0] + (f" (+{len(rects) - 1} more)" if len(rects) > 1 else "")


TAB_LEVEL = {
    "inputs_outside_inputs_tab",
    "mixed_currency",
    "duplicate_rows",
    "duplicate_key",
    "no_freeze_panes",
    "default_sheet_name",
    "period_header_gap",
    "no_inputs_tab",
    "hidden_sheet",
    "excess_cell_styles",
    "inflated_used_range",
    "unused_named_range",
    "calc_manual",
    "iterative_calc_on",
}


def _fkey(f, rename=None):
    """Identity of a finding across versions: what and where in words, not cell addresses."""
    sh = (rename or {}).get(f.get("sheet"), f.get("sheet"))
    if f["check"] in TAB_LEVEL:
        return (f["check"], sh)
    lab = f.get("label") or f.get("cell") or ""
    if f.get("basis") == "judgment":
        return (f["check"], sh, lab.split(" \u00b7 ")[0])
    return (f["check"], sh, lab, re.sub(r"[\d.,%$€£-]+", "#", f["description"])[:80])
