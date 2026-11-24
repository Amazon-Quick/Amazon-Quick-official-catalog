"""
description: The workbook file as parts: read parts on demand within the scan's size limits, add number formats, and save a copy that is never the original.
last_updated: 2026-11-24
"""

from __future__ import annotations

import html
import posixpath
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import scan_workbook as S
from apply_xml import attr, open_tag, set_attr


class Package:
    def __init__(self, path: Path):
        self.path = path
        # The scan's limits (part size, total size, compression ratio) apply here too.
        # Parts are read only when an edit needs them; the rest are streamed on save.
        S.check_archive_size(path)
        with zipfile.ZipFile(path) as z:
            self.infos = z.infolist()
        self.files = {i.filename: None for i in self.infos}
        self.dirty = set()
        wb = self.text("xl/workbook.xml")
        rels = self.text("xl/_rels/workbook.xml.rels")
        targets = {}
        for m in re.finditer(r"<Relationship\b[^>]*/>", rels):
            t = m.group(0)
            targets[attr(t, "Id")] = attr(t, "Target")
        self.sheets = {}
        for m in re.finditer(r"<sheet\b[^>]*/>", wb):
            t = m.group(0)
            name = html.unescape(attr(t, "name"))
            rid = re.search(r'\s[\w]+:id="([^"]+)"', t).group(1)
            tgt = targets[rid]
            self.sheets[name] = (
                tgt.lstrip("/")
                if tgt.startswith("/")
                else posixpath.normpath(posixpath.join("xl", tgt))
            )

    def text(self, name):
        if self.files[name] is None:
            with zipfile.ZipFile(self.path) as z:
                self.files[name] = z.read(name)
        return self.files[name].decode("utf-8")

    def put(self, name, s):
        self.files[name] = s.encode("utf-8")
        self.dirty.add(name)

    def sheet_rel_targets(self, sheet, kind):
        p = self.sheets[sheet]
        rp = posixpath.join(
            posixpath.dirname(p), "_rels", posixpath.basename(p) + ".rels"
        )
        if rp not in self.files:
            return []
        out = []
        for m in re.finditer(r"<Relationship\b[^>]*/>", self.text(rp)):
            t = m.group(0)
            if attr(t, "Type").endswith("/" + kind):
                tgt = attr(t, "Target")
                out.append(
                    tgt.lstrip("/")
                    if tgt.startswith("/")
                    else posixpath.normpath(posixpath.join(posixpath.dirname(p), tgt))
                )
        return out

    def save(self, out: Path, force=False):
        # Never write over the file the package was read from (the user's model).
        validate_output(self.path, out, force)
        # Reserve the temporary name so an existing alias cannot point at the source.
        with tempfile.NamedTemporaryFile(
            dir=out.parent, prefix=out.name + ".", suffix=".partial", delete=False
        ) as staging:
            tmp = Path(staging.name)
        try:
            with (
                zipfile.ZipFile(self.path) as source,
                zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z,
            ):
                for i in self.infos:
                    if i.filename in self.files:
                        if i.filename in self.dirty:
                            z.writestr(i, self.files[i.filename])
                        else:
                            with source.open(i) as src, z.open(i, "w") as dst:
                                shutil.copyfileobj(src, dst, length=1024 * 1024)
            # Re-check after staging, so an alias created meanwhile cannot make
            # the move land on the model.
            validate_output(self.path, out, force)
            shutil.move(str(tmp), str(out))
        finally:
            tmp.unlink(missing_ok=True)


class Styles:
    def __init__(self, pkg: Package):
        self.pkg, self.cache = pkg, {}

    def with_numfmt(self, s_idx: int, fmt_id: int) -> int:
        key = (s_idx, fmt_id)
        if key in self.cache:
            return self.cache[key]
        st = self.pkg.text("xl/styles.xml")
        m = re.search(r"<cellXfs\b[^>]*>(.*?)</cellXfs>", st, re.S)
        xfs = list(re.finditer(r"<xf\b[^>]*?(?:/>|>.*?</xf>)", m.group(1), re.S))
        base = xfs[s_idx].group(0) if s_idx < len(xfs) else xfs[0].group(0)
        tag = open_tag(base)
        new_tag = set_attr(set_attr(tag, "numFmtId", fmt_id), "applyNumberFormat", 1)
        new = new_tag + base[len(tag) :]
        inner = m.group(1) + new
        block = (
            set_attr(open_tag(m.group(0)), "count", len(xfs) + 1) + inner + "</cellXfs>"
        )
        self.pkg.put("xl/styles.xml", st[: m.start()] + block + st[m.end() :])
        self.cache[key] = len(xfs)
        return len(xfs)


def validate_output(model: Path, out: Path, force=False):
    if out.resolve() == model.resolve() or (out.exists() and out.samefile(model)):
        raise ValueError(
            "Refusing to write over the original model. Choose a different --out."
        )
    if out.exists() and not force:
        raise ValueError("Output already exists. Choose another --out or use --force.")
