"""
description: Planned workbook and layout changes: calculation mode, used range, unused names, column widths, frozen headers and merged cells.
last_updated: 2026-11-24
"""

from __future__ import annotations

import scan_workbook as S
from openpyxl.utils import get_column_letter
from plan_common import cells_of


def fix_calc_manual(p, f):
    """Set calculation to Automatic."""
    return p.add(
        [f["id"]],
        None,
        None,
        "setting",
        "confirm",
        "Set calculation to Automatic (it is Manual, so numbers can be stale)",
        [{"op": "calc_auto"}],
    )


def fix_used_range(p, f):
    """Drop empty formatted cells past the data."""
    s = p.wb.sheets[f["sheet"]]
    mr, mc = (
        max(x.r for x in s.cells.values()),
        max(x.c for x in s.cells.values()),
    )
    return p.add(
        [f["id"]],
        s.name,
        None,
        "cleanup",
        "safe",
        f"Remove the empty formatted cells past {get_column_letter(mc)}{mr} (the end of the data) for a smaller, faster file",
        [{"op": "trim", "sheet": s.name, "max_row": mr, "max_col": mc}],
    )


def fix_unused_names(p, f):
    """Delete named ranges nothing uses."""
    names = f.get("names") or []
    if not names:
        return p.needs_you(f)
    return p.add(
        [f["id"]],
        None,
        None,
        "cleanup",
        "confirm",
        f"Delete {S.plural(len(names), 'named range')} nothing uses: "
        + ", ".join(names[:6])
        + (" ..." if len(names) > 6 else ""),
        [{"op": "delete_names", "names": names}],
    )


def fix_narrow_column(p, f):
    """Widen a column so its numbers show."""
    s = p.wb.sheets[f["sheet"]]
    need = {}
    for r, c in cells_of(f["cell"]) or []:
        x = s.cells.get((r, c))
        if x and S.is_num(x.cached):
            t = S.display_text(float(x.cached), x.fmt)
            if t:
                need[c] = max(need.get(c, 0), t[1])
    edits = [
        {
            "op": "col_width",
            "sheet": s.name,
            "col": get_column_letter(c),
            "width": w + 2,
        }
        for c, w in need.items()
    ]
    if not edits:
        return p.needs_you(f)
    return p.add(
        [f["id"]],
        s.name,
        f["cell"],
        "layout",
        "safe",
        "Widen column "
        + ", ".join(f"{e['col']} to {e['width']}" for e in edits)
        + " so the number shows",
        edits,
    )


def fix_freeze_panes(p, f):
    """Freeze the header row."""
    s = p.wb.sheets[f["sheet"]]
    hdr = [x for x in s.cells.values() if x.r == s.header_row]
    if not (1 <= s.header_row <= 3) or sum(isinstance(x.raw, str) for x in hdr) < 2:
        return p.needs_you(
            f,
            "Freeze the row that holds the column headers (View > Freeze Panes). The header row isn't clear enough to pick automatically",
        )
    return p.add(
        [f["id"]],
        s.name,
        None,
        "layout",
        "safe",
        f"Freeze the header row (row {s.header_row}) so it stays visible",
        [{"op": "freeze", "sheet": s.name, "row": s.header_row}],
    )


def fix_merged_cells(p, f):
    """Unmerge cells in a calculation area."""
    return p.add(
        [f["id"]],
        f["sheet"],
        f["cell"],
        "layout",
        "safe",
        f"Unmerge {f['cell']} (the value stays in the first cell)",
        [{"op": "unmerge", "sheet": f["sheet"], "ref": f["cell"]}],
    )
