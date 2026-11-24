"""
description: Planned conditional-formatting changes: merge copies of one highlight rule, limit whole-column rules, delete broken ones.
last_updated: 2026-11-24
"""

from __future__ import annotations

import re

import scan_workbook as S
from openpyxl.formula.tokenizer import Tokenizer, TokenizerError
from openpyxl.utils import get_column_letter
from plan_common import boxes_overlap

# Highlight-rule copies larger than this, or on tabs with more blocks than this, are left to
# the user: the merge lists every cell, and the overlap check compares every pair of blocks.
CF_MERGE_CELLS = 200_000


CF_MERGE_BLOCKS = 2_000
CF_OVERLAP_PAIRS = 1_000_000  # range-part pairs compared before a merge; past this, send it to the owner


ABSOLUTE_REF = re.compile(r"\$[A-Z]{1,3}\$\d+(?::\$[A-Z]{1,3}\$\d+)?", re.I)


def cf_merge_key(cf):
    """What must match for copies of a highlight block to merge, or None if it must not merge.

    Only one-rule blocks of a cell-value or formula rule qualify (rankings and color scales
    depend on each block's cells), and only when every reference is absolute: a relative
    reference or a name is read from each block's top-left cell, which merging moves.
    """
    if len(cf.rules) != 1:
        return None
    rule = cf.rules[0]
    if rule.type not in {"cellIs", "expression"}:
        return None
    for formula in rule.formula or ():
        try:
            tokens = Tokenizer("=" + formula.lstrip("=")).items
        except TokenizerError:
            return None
        for token in tokens:
            if token.subtype == "RANGE" and not ABSOLUTE_REF.fullmatch(
                token.value.rsplit("!", 1)[-1]
            ):
                return None
    return (
        rule.type,
        rule.operator,
        tuple(rule.formula or ()),
        rule.dxfId,
        bool(rule.stopIfTrue),
        bool(cf.pivot),
    )


def merge_highlight_copies(p, f):
    """One rule for copies of the same highlight rule, when merging can't change any cell's look."""
    s = p.wb.sheets[f["sheet"]]
    box = S.parse_box(f["cell"])
    if len(s.ws.conditional_formatting) > CF_MERGE_BLOCKS:
        return p.needs_you(f)
    blocks = [
        (cf, [S.parse_box(p) for p in str(cf.sqref).split()])
        for cf in s.ws.conditional_formatting
    ]
    groups = {}
    for i, (cf, _) in enumerate(blocks):
        key = cf_merge_key(cf)
        if key:
            groups.setdefault(key, []).append(i)
    for members in groups.values():
        bs = [b for i in members for b in blocks[i][1]]
        if (
            len(members) < S.FRAGMENT_MIN
            or min(b[0] for b in bs) != box[0]
            or min(b[1] for b in bs) != box[1]
        ):
            continue
        if sum((b[2] - b[0] + 1) * (b[3] - b[1] + 1) for b in bs) > CF_MERGE_CELLS:
            return p.needs_you(
                f,
                "Limit the rule copies to the rows in use first, then replace them with one rule "
                "(Home > Conditional Formatting > Manage Rules).",
            )
        others = [b for i, (_, bb) in enumerate(blocks) if i not in members for b in bb]
        if len(bs) * len(others) > CF_OVERLAP_PAIRS:
            return p.needs_you(
                f,
                "This tab has too many highlight rules to check the merge safely; "
                "replace the copies with one rule by hand and check the rule order.",
            )
        if any(boxes_overlap(a, b) for a in bs for b in others):
            return p.needs_you(
                f,
                "Other highlight rules cover the same cells, so merging could change which rule "
                "wins; replace the copies with one rule by hand and check the rule order.",
            )
        ranges = [str(blocks[i][0].sqref) for i in members]
        pts = [
            (r, c)
            for b in bs
            for r in range(b[1], b[3] + 1)
            for c in range(b[0], b[2] + 1)
        ]
        merged = " ".join(S.rectangles(pts))
        return p.add(
            [f["id"]],
            s.name,
            f["cell"],
            "cleanup",
            "safe",
            f"Replace {len(ranges)} copies of one highlight rule with a single rule over {merged}",
            [
                {
                    "op": "cf_merge",
                    "sheet": s.name,
                    "sqrefs": ranges,
                    "sqref": merged,
                }
            ],
        )
    return p.needs_you(f)


def limit_whole_column(p, f):
    """Limit a whole-column highlight rule to the rows in use."""
    s = p.wb.sheets[f["sheet"]]
    fb = S.parse_box(f["cell"])
    last = max(s.rows) if s.rows else 1
    for cf in s.ws.conditional_formatting:
        for part in str(cf.sqref).split():
            b = S.parse_box(part)
            if (b[0], b[2]) != (fb[0], fb[2]):  # the finding's own columns
                continue
            if b[3] - b[1] + 1 >= S.MAX_ROW - 1:
                new = f"{get_column_letter(b[0])}{b[1]}:{get_column_letter(b[2])}{last}"
                return p.add(
                    [f["id"]],
                    s.name,
                    f["cell"],
                    "cleanup",
                    "safe",
                    f"Limit the highlight rule on {f['cell']} to the rows in use ({new})",
                    [
                        {
                            "op": "cf_sqref",
                            "sheet": s.name,
                            "old": str(cf.sqref),
                            "new": str(cf.sqref).replace(part, new),
                        }
                    ],
                )
    return p.needs_you(f)


def delete_broken_rule(p, f):
    """Delete a highlight rule that points at #REF!."""
    return p.add(
        [f["id"]],
        f["sheet"],
        f["cell"],
        "cleanup",
        "confirm",
        f"Delete the highlight rule on {f['cell']} that points at a deleted cell",
        [{"op": "cf_delete_ref", "sheet": f["sheet"], "sqref": f["cell"]}],
    )
