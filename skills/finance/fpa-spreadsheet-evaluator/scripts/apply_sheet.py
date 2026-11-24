"""
description: Edit one worksheet's XML in place: cells, shared formulas, trimming, frozen panes, column widths, highlight rules and merged cells.
last_updated: 2026-11-24
"""

from __future__ import annotations

import re

import scan_workbook as S
from apply_package import Package
from apply_xml import (
    CELL_ANY,
    CF_BLOCK,
    attr,
    cell_pat,
    cf_signature,
    esc,
    map_element_names,
    open_tag,
    protect_xml_literals,
    set_attr,
    worksheet_view,
)
from openpyxl.utils import column_index_from_string, get_column_letter


class SheetXml:
    def __init__(self, pkg: Package, sheet: str, wf):
        self.pkg, self.sheet, self.path = pkg, sheet, pkg.sheets[sheet]
        protected, self.literals = protect_xml_literals(pkg.text(self.path))
        self.xml, self.prefix = worksheet_view(protected)
        self.wf = wf
        self.touched = False

    def serialize(self):
        xml = self.xml
        if self.prefix:
            xml = map_element_names(
                xml,
                lambda name, _token: self.prefix + name if ":" not in name else name,
            )
        for marker, literal in self.literals.items():
            xml = xml.replace(marker, literal)
        return xml

    def style_of(self, coord):
        m = cell_pat(coord).search(self.xml)
        return int(attr(open_tag(m.group(0)), "s") or 0) if m else 0

    def unshare(self, coords):
        """Turn shared formulas touching these cells into ordinary ones, so editing one cell can't break others."""
        groups = set()
        for coord in coords:
            m = cell_pat(coord).search(self.xml)
            if m and 't="shared"' in m.group(0):
                fm = re.search(r"<f\b([^>]*)", m.group(0))
                si = attr(fm.group(0), "si") if fm else None
                if si is not None:
                    groups.add(si)
        if not groups:
            return
        ws = self.wf[self.sheet]

        def fix(m):
            el = m.group(0)
            fm = re.search(r"<f\b[^>]*?(?:/>|>.*?</f>)", el, re.S)
            if (
                not fm
                or 't="shared"' not in fm.group(0)
                or attr(open_tag(fm.group(0)), "si") not in groups
            ):
                return el
            coord = attr(open_tag(el), "r")
            text = S.formula_text(ws[coord].value) or ""
            return el[: fm.start()] + f"<f>{esc(text[1:])}</f>" + el[fm.end() :]

        self.xml = CELL_ANY.sub(fix, self.xml)

    def set_cell(self, coord, formula=None, value=None, s=None, must_be_empty=False):
        m = cell_pat(coord).search(self.xml)
        if m and must_be_empty and re.search(r"<(f|v|is)\b", m.group(0)):
            raise ValueError(f"{self.sheet}!{coord} is no longer empty")
        old_tag = open_tag(m.group(0)) if m else f'<c r="{coord}">'
        s_val = s if s is not None else attr(old_tag, "s")
        if formula is None and value is None:  # style only
            if not m:
                raise ValueError(f"{self.sheet}!{coord} not found")
            tag = set_attr(old_tag, "s", s_val)
            el = tag + m.group(0)[len(old_tag) :]
        else:
            tag = f'<c r="{coord}"' + (
                f' s="{s_val}"' if s_val not in (None, "0") else ""
            )
            if formula is not None:
                el = f"{tag}><f>{esc(formula.lstrip('='))}</f></c>"
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                el = f"{tag}><v>{value if isinstance(value, int) else repr(float(value))}</v></c>"
            else:
                el = f'{tag} t="inlineStr"><is><t xml:space="preserve">{esc(str(value))}</t></is></c>'
        if m:
            self.xml = self.xml[: m.start()] + el + self.xml[m.end() :]
        else:
            self.insert(coord, el)
        self.touched = True

    def insert(self, coord, el):
        col = column_index_from_string(re.match(r"[A-Z]+", coord).group(0))
        row = int(re.search(r"\d+", coord).group(0))
        rm = re.search(
            rf'<row\b(?=[^>]*?\sr="{row}")[^>]*?(?:/>|>.*?</row>)', self.xml, re.S
        )
        if rm:
            rowel = rm.group(0)
            tag = set_attr(open_tag(rowel), "spans", None)
            if rowel.endswith("/>") and not rowel.endswith("</row>"):
                new = tag[:-2].rstrip() + ">" + el + "</row>"
            else:
                inner = rowel[len(open_tag(rowel)) : -len("</row>")]
                pos = len(inner)
                for cm in re.finditer(r'<c\b[^>]*?\sr="([A-Z]+)\d+"', inner):
                    if column_index_from_string(cm.group(1)) > col:
                        pos = cm.start()
                        break
                new = tag + inner[:pos] + el + inner[pos:] + "</row>"
            self.xml = self.xml[: rm.start()] + new + self.xml[rm.end() :]
            return
        new_row = f'<row r="{row}">{el}</row>'
        if re.search(r"<sheetData\s*/>", self.xml):
            self.xml = re.sub(
                r"<sheetData\s*/>",
                f"<sheetData>{new_row}</sheetData>",
                self.xml,
                count=1,
            )
            return
        for r in re.finditer(r'<row\b[^>]*?\sr="(\d+)"', self.xml):
            if int(r.group(1)) > row:
                self.xml = self.xml[: r.start()] + new_row + self.xml[r.start() :]
                return
        i = self.xml.index("</sheetData>")
        self.xml = self.xml[:i] + new_row + self.xml[i:]

    def trim(self, max_row, max_col):
        """Drop empty formatted cells, rows and column styles beyond the real data."""

        def keep_cell(m):
            el = m.group(0)
            coord = attr(open_tag(el), "r")
            letters = re.match(r"[A-Z]+", coord).group(0)
            col = column_index_from_string(letters)
            row = int(coord[len(letters) :])
            beyond = col > max_col or row > max_row
            if beyond and not re.search(r"<(f|v|is)\b", el):
                return ""
            return el

        def fix_row(m):
            el = m.group(0)
            r = int(attr(open_tag(el), "r"))
            tag = open_tag(el)
            if el.endswith("/>") and "</row>" not in el:
                return "" if r > max_row else el
            inner = CELL_ANY.sub(keep_cell, el[len(tag) : -len("</row>")])
            if r > max_row and not re.search(r"<c\b", inner):
                return ""
            return set_attr(tag, "spans", None) + inner + "</row>"

        self.xml = re.sub(
            r"<row\b[^>]*?(?:/>|>.*?</row>)", fix_row, self.xml, flags=re.S
        )
        m = re.search(r"<cols>(.*?)</cols>", self.xml, re.S)
        if m:
            cols = []
            for t in re.findall(r"<col\b[^>]*/>", m.group(1)):
                lo, hi = int(attr(t, "min")), int(attr(t, "max"))
                if lo > max_col:
                    continue
                cols.append(set_attr(t, "max", min(hi, max_col)))
            block = ("<cols>" + "".join(cols) + "</cols>") if cols else ""
            self.xml = self.xml[: m.start()] + block + self.xml[m.end() :]
        self.xml = re.sub(
            r'(<dimension\s+ref=)"[^"]*"',
            rf'\1"A1:{get_column_letter(max_col)}{max_row}"',
            self.xml,
            count=1,
        )
        self.touched = True

    def freeze(self, row):
        m = re.search(r"<sheetView\b[^>]*?(?:/>|>.*?</sheetView>)", self.xml, re.S)
        pane = f'<pane ySplit="{row}" topLeftCell="A{row + 1}" activePane="bottomLeft" state="frozen"/>'
        sel = (
            f'<selection pane="bottomLeft" activeCell="A{row + 1}" sqref="A{row + 1}"/>'
        )
        if m:
            el = m.group(0)
            if "<pane" in el:
                return
            tag = open_tag(el)
            if el.endswith("/>") and "</sheetView>" not in el:
                new = tag[:-2].rstrip() + ">" + pane + sel + "</sheetView>"
            else:
                inner = re.sub(
                    r"<selection\b[^>]*/>", "", el[len(tag) : -len("</sheetView>")]
                )
                new = tag + pane + sel + inner + "</sheetView>"
            self.xml = self.xml[: m.start()] + new + self.xml[m.end() :]
        else:
            block = f'<sheetViews><sheetView workbookViewId="0">{pane}{sel}</sheetView></sheetViews>'
            self.xml = re.sub(
                r"(<sheetFormatPr\b|<cols\b|<sheetData\b)",
                block + r"\1",
                self.xml,
                count=1,
            )
        self.touched = True

    def col_width(self, letter, width):
        c = column_index_from_string(letter)
        new_col = f'<col min="{c}" max="{c}" width="{width}" customWidth="1"/>'
        m = re.search(r"<cols>(.*?)</cols>", self.xml, re.S)
        if not m:
            self.xml = re.sub(
                r"(<sheetData\b)", f"<cols>{new_col}</cols>" + r"\1", self.xml, count=1
            )
            self.touched = True
            return
        cols = re.findall(r"<col\b[^>]*/>", m.group(1))
        out, done = [], False
        for t in cols:
            lo, hi = int(attr(t, "min")), int(attr(t, "max"))
            if lo <= c <= hi:
                if lo < c:
                    out.append(set_attr(t, "max", c - 1))
                out.append(
                    set_attr(
                        set_attr(
                            set_attr(set_attr(t, "min", c), "max", c), "width", width
                        ),
                        "customWidth",
                        1,
                    )
                )
                if c < hi:
                    out.append(set_attr(t, "min", c + 1))
                done = True
            else:
                out.append(t)
        if not done:
            out.append(new_col)
        out.sort(key=lambda t: int(attr(t, "min")))
        self.xml = (
            self.xml[: m.start()]
            + "<cols>"
            + "".join(out)
            + "</cols>"
            + self.xml[m.end() :]
        )
        self.touched = True

    def cf_merge(self, sqrefs, sqref):
        """Replace one-rule copies of the same highlight rule on `sqrefs` with one block on `sqref`.

        Only blocks that hold exactly one rule, identical apart from range and priority, are
        merged; any other block on the same ranges is left alone.
        """
        want = set(sqrefs)
        groups = {}
        for m in CF_BLOCK.finditer(self.xml):
            el = m.group(0)
            if attr(open_tag(el), "sqref") in want and el.count("<cfRule") == 1:
                groups.setdefault(cf_signature(el), []).append(m)
        matches = [
            ms
            for ms in groups.values()
            if sorted(attr(open_tag(m.group(0)), "sqref") for m in ms) == sorted(sqrefs)
        ]
        if len(matches) != 1 or len(matches[0]) < 2:
            raise ValueError("highlight rules no longer match the plan")
        els = matches[0]
        keep = els[0].group(0)
        new = set_attr(open_tag(keep), "sqref", sqref) + keep[len(open_tag(keep)) :]
        out, last = [], 0
        for i, m in enumerate(els):
            out.append(self.xml[last : m.start()] + (new if i == 0 else ""))
            last = m.end()
        out.append(self.xml[last:])
        self.xml = "".join(out)
        self.touched = True

    def cf_sqref(self, old, new):
        n = 0

        def sub(m):
            nonlocal n
            if attr(open_tag(m.group(0)), "sqref") == old and n == 0:
                n += 1
                return (
                    set_attr(open_tag(m.group(0)), "sqref", new)
                    + m.group(0)[len(open_tag(m.group(0))) :]
                )
            return m.group(0)

        self.xml = CF_BLOCK.sub(sub, self.xml)
        if not n:
            raise ValueError(f"no highlight rule on {old}")
        self.touched = True

    def cf_delete_ref(self, sqref):
        n = 0

        def sub(m):
            nonlocal n
            el = m.group(0)
            if attr(open_tag(el), "sqref") == sqref and "#REF!" in el:
                n += 1
                return ""
            return el

        self.xml = CF_BLOCK.sub(sub, self.xml)
        if not n:
            raise ValueError(f"no broken highlight rule on {sqref}")
        self.touched = True

    def unmerge(self, ref):
        before = self.xml
        self.xml = re.sub(rf'<mergeCell\s+ref="{re.escape(ref)}"\s*/>', "", self.xml)
        if self.xml == before:
            raise ValueError(f"{ref} is not merged")
        m = re.search(r"<mergeCells\b[^>]*>(.*?)</mergeCells>", self.xml, re.S)
        if m:
            n = len(re.findall(r"<mergeCell\b", m.group(1)))
            if n == 0:
                self.xml = self.xml[: m.start()] + self.xml[m.end() :]
            else:
                self.xml = (
                    self.xml[: m.start()]
                    + set_attr(open_tag(m.group(0)), "count", n)
                    + m.group(0)[len(open_tag(m.group(0))) :]
                    + self.xml[m.end() :]
                )
        self.touched = True
