"""
description: In-memory workbook builders shared by the scan unit tests. Nothing touches the filesystem.
last_updated: 2026-11-24
"""

import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import openpyxl  # noqa: E402
from scan_finance_base import period_layout, sheet_title_text  # noqa: E402
from scan_load import Workbook  # noqa: E402

SLOW_SECONDS = 5  # each timed case took 25 s or more before its fix


def workbook_bytes(build) -> io.BytesIO:
    """Save an openpyxl workbook built by `build(ws, wb)` to memory."""
    wb = openpyxl.Workbook()
    build(wb.active, wb)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def rewrite_member(buf: io.BytesIO, member: str, edit) -> io.BytesIO:
    """Copy an in-memory .xlsx, passing one member's bytes through `edit`."""
    out = io.BytesIO()
    with (
        zipfile.ZipFile(buf) as zin,
        zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout,
    ):
        for info in zin.infolist():
            data = zin.read(info)
            zout.writestr(info, edit(data) if info.filename == member else data)
    out.seek(0)
    return out


def load(buf: io.BytesIO) -> Workbook:
    buf.seek(0)
    return Workbook(buf)


def prepare_finance(wb: Workbook) -> None:
    """Set the period layout and tab titles the finance checks read, as check_finance does."""
    for s in wb.sheets.values():
        s.periods = period_layout(s) if s.rows else None
        s.title_text = sheet_title_text(s) if s.rows else ""
