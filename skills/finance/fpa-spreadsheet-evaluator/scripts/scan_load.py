"""
description: Load a workbook for the scan within the archive and cell limits, and build the in-memory cell model.
last_updated: 2026-11-24

Part of the workbook scan; scan_workbook.py is the entry point and re-exports the names other scripts use.
"""

from __future__ import annotations

import datetime as dt
import zipfile
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter
from scan_findings import data_text
from scan_formats import DATE_TEXT, color_family, fill_family, is_num, numeric_text
from scan_formula_text import EXT_RE, mask_strings, normalize, refs_in
from scan_limits import (
    ARCHIVE_MEMBER_CAP,
    ARCHIVE_RATIO_CAP,
    ARCHIVE_SIZE_CAP,
    CELL_CAP,
    COL_CAP,
    DATA_MAX_FORMULA_SHARE,
    DATA_MIN_ROWS,
    ROW_CAP,
)


class C:
    __slots__ = (
        "sheet",
        "r",
        "c",
        "raw",
        "formula",
        "cached",
        "font",
        "fill",
        "bold",
        "fmt",
        "is_date",
        "top",
        "bottom",
        "norm",
        "links",
    )

    @property
    def coord(self):
        return f"{get_column_letter(self.c)}{self.r}"


class Sheet:
    def __init__(self, ws, wsv):
        self.ws, self.wsv, self.name = ws, wsv, ws.title
        self.hidden = ws.sheet_state != "visible"
        self.cells: dict[tuple[int, int], C] = {}
        self.capped = (ws.max_row or 0) > ROW_CAP or (ws.max_column or 0) > COL_CAP
        self.header_row = 1
        self.is_data = False
        self.role = ""


def formula_text(v):
    if isinstance(v, str) and v.startswith("="):
        return v
    t = getattr(v, "text", None)  # ArrayFormula
    if isinstance(t, str):
        return t if t.startswith("=") else "=" + t
    return None


def check_archive_size(path: Path):
    """Reject oversized XLSX packages before loading either workbook copy."""
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ValueError("The file is not a readable .xlsx package.") from exc
    with archive:
        total = 0
        for member in archive.infolist():
            total += member.file_size
            if member.file_size > ARCHIVE_MEMBER_CAP:
                raise ValueError(
                    f"Workbook member {data_text(member.filename)} exceeds the "
                    f"{ARCHIVE_MEMBER_CAP // (1024 * 1024)} MiB uncompressed limit."
                )
            if total > ARCHIVE_SIZE_CAP:
                raise ValueError(
                    "Workbook exceeds the "
                    f"{ARCHIVE_SIZE_CAP // (1024 * 1024)} MiB uncompressed limit."
                )
            if member.file_size > ARCHIVE_RATIO_CAP * max(member.compress_size, 1):
                raise ValueError(
                    f"Workbook member {data_text(member.filename)} exceeds the "
                    f"{ARCHIVE_RATIO_CAP}:1 compression ratio limit."
                )


class Workbook:
    def __init__(self, path: Path):
        self.path = path
        check_archive_size(path)
        self.wf = openpyxl.load_workbook(path, data_only=False)
        self.sheets: dict[str, Sheet] = {}
        self.lower = {}
        self.notes: list[dict] = []
        self.truncated = False
        self.fonts = Counter()
        with closing(
            openpyxl.load_workbook(path, data_only=True, read_only=True)
        ) as self.wv:
            self._load_sheets()
        self.formulas = [
            x for s in self.sheets.values() for x in s.cells.values() if x.formula
        ]
        for x in self.formulas:
            masked = mask_strings(x.formula)
            x.links = {
                self.resolve(sh)
                for sh, *_ in refs_in(x.formula)
                if sh and self.resolve(sh)
            } - {x.sheet}
            if EXT_RE.search(masked):
                x.links.add("[external]")
        self._classify()

    def _load_sheets(self):
        total = 0
        for ws in self.wf.worksheets:
            s = Sheet(ws, self.wv[ws.title])
            self.sheets[ws.title] = s
            self.lower[ws.title.lower()] = ws.title
            self.truncated |= s.capped
            # Private openpyxl 3.1 attribute: the stored cells only. The public
            # ws.iter_rows() walks the claimed grid and creates every empty cell in it.
            for (r, c), cell in ws._cells.items():
                if r > ROW_CAP or c > COL_CAP:
                    continue
                raw = cell.value
                if raw is None:
                    continue
                total += 1
                if total > CELL_CAP:
                    self.truncated = True
                    break
                x = C()
                x.sheet, x.r, x.c, x.raw = ws.title, r, c, raw
                x.formula = formula_text(raw)
                x.cached = None if x.formula else raw
                f = cell.font
                if f is not None and f.name:
                    self.fonts[(f.name, float(f.sz or 11))] += 1
                x.font = color_family(f.color) if f else "auto"
                x.bold = bool(f and f.b)
                x.fill = fill_family(cell.fill)
                x.fmt = cell.number_format or "General"
                x.is_date = isinstance(x.cached, (dt.datetime, dt.date))
                bd = cell.border
                x.top = (bd.top.style or "") if bd and bd.top else ""
                x.bottom = (bd.bottom.style or "") if bd and bd.bottom else ""
                x.norm = normalize(x.formula, r, c) if x.formula else None
                x.links = None
                s.cells[(r, c)] = x
            formulas = [x for x in s.cells.values() if x.formula]
            if not formulas:
                continue
            min_row = min(x.r for x in formulas)
            min_col = min(x.c for x in formulas)
            # Only stream the already bounded area containing scanned formulas.
            # Do not materialize the cached-values workbook or trust its dimensions.
            rows = s.wsv.iter_rows(
                min_row=min_row,
                max_row=min(ROW_CAP, max(x.r for x in formulas)),
                min_col=min_col,
                max_col=min(COL_CAP, max(x.c for x in formulas)),
                values_only=True,
            )
            for r, row in enumerate(rows, min_row):
                for c, value in enumerate(row, min_col):
                    x = s.cells.get((r, c))
                    if x is not None and x.formula:
                        x.cached = value
                        x.is_date = isinstance(value, (dt.datetime, dt.date))

    def resolve(self, name):
        if not name:
            return None
        if "[" in name:
            return None
        return self.lower.get(name.strip("'").lower())

    def cell(self, sheet, r, c):
        s = self.sheets.get(sheet)
        return s.cells.get((r, c)) if s else None

    def _classify(self):
        for s in self.sheets.values():
            rows = defaultdict(list)
            for x in s.cells.values():
                rows[x.r].append(x)
            # Prefer the full-width field/period row over sparse cover metadata.
            # Typed record values and formulas are not column headings.
            candidates = []
            for r in sorted(rows)[:15]:
                xs = rows[r]
                labels = sum(
                    isinstance(x.raw, str)
                    and not x.formula
                    and not numeric_text(x.raw)
                    and not DATE_TEXT.match(x.raw)
                    for x in xs
                )
                dates = sum(
                    x.is_date
                    or (isinstance(x.raw, str) and DATE_TEXT.match(x.raw) is not None)
                    for x in xs
                )
                if labels >= 1 and labels + dates == len(xs) and len(xs) >= 2:
                    candidates.append((len(xs), r))
            width = max((n for n, r in candidates), default=0)
            s.header_candidates = [r for n, r in candidates if n == width]
            if candidates:
                s.header_row = s.header_candidates[0]
            else:
                # no header row: skip the first row only if it's a title (text only), not data
                first = min(rows) if rows else 1
                s.header_row = (
                    0 if any(is_num(x.raw) for x in rows.get(first, [])) else first
                )
            n_form = sum(1 for x in s.cells.values() if x.formula)
            n_vals = sum(
                1
                for x in s.cells.values()
                if not x.formula
                and (is_num(x.raw) or x.is_date or isinstance(x.raw, str))
            )
            data_rows = len([r for r in rows if r > s.header_row])
            s.is_data = (
                data_rows >= DATA_MIN_ROWS
                and n_form <= DATA_MAX_FORMULA_SHARE * max(1, n_form + n_vals)
            )
            s.rows = rows
