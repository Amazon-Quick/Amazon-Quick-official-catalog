"""
description: Check a cause ledger against the check report (pieces add up to each line's variance, tags and outlooks are valid, every Unexplained piece over the rounding tolerance has an owner and a due date) and total the pieces for the proof block.
last_updated: 2026-11-24

Pure function with no file access. variance_check re-exports check_ledger.
"""

from variance_table import clean_num, parse_table

TAGS = ("Data-supported", "Owner-stated", "Unexplained", "Rounding")
OUTLOOKS = ("one-time", "recurring", "growing", "unknown")
UNWINDING = "unwinding by "
OTHER_LINES = "other lines"
LEDGER_COLUMNS = (
    "line",
    "piece",
    "amount",
    "tag",
    "evidence",
    "outlook",
    "owner",
    "due",
)
MONEY_TYPES = ("revenue", "cost", "profit")
PLACEHOLDER_OWNERS = ("", "tbd", "tba", "unknown", "n/a", "none")
SUM_EPSILON = 1e-9


def _is_placeholder(owner):
    text = owner.strip().lower()
    return (
        text in PLACEHOLDER_OWNERS or "[" in text or "<" in text or "to confirm" in text
    )


def _valid_outlook(outlook):
    text = outlook.strip().lower()
    return text in OUTLOOKS or (
        text.startswith(UNWINDING) and len(text) > len(UNWINDING)
    )


def _read_pieces(text):
    header, raw = parse_table(text)
    missing = [c for c in LEDGER_COLUMNS if c not in header]
    if missing:
        return None, [f"Ledger is missing columns {missing}. Columns seen: {header}"]
    pieces, faults = [], []
    for n, r in enumerate(raw, start=2):
        amount = clean_num(r.get("amount"))
        line = str(r.get("line") or "").strip()
        if not line or amount is None:
            faults.append(f"Ledger row {n}: needs a line name and a numeric amount.")
            continue
        pieces.append(
            {
                "row": n,
                "line": line,
                "amount": amount,
                "tag": str(r.get("tag") or "").strip(),
                "outlook": str(r.get("outlook") or "").strip(),
                "owner": str(r.get("owner") or "").strip(),
                "due": str(r.get("due") or "").strip(),
            }
        )
    return pieces, faults


def _piece_faults(p, tol):
    faults = []
    where = f"Ledger row {p['row']} ('{p['line']}')"
    if p["tag"] not in TAGS:
        faults.append(f"{where}: tag must be one of {', '.join(TAGS)}.")
    if not _valid_outlook(p["outlook"]):
        faults.append(
            f"{where}: outlook must be one-time, recurring, growing, unwinding by <date>, or unknown."
        )
    if p["tag"] == "Rounding" and abs(p["amount"]) > tol + SUM_EPSILON:
        faults.append(
            f"{where}: a Rounding piece of {p['amount']:,.4g} is over the tolerance {tol:,.4g}; tag it Unexplained."
        )
    if p["tag"] == "Unexplained" and abs(p["amount"]) > tol + SUM_EPSILON:
        if _is_placeholder(p["owner"]) or not p["due"]:
            faults.append(
                f"{where}: an Unexplained piece over the tolerance needs a named owner and a due date."
            )
    return faults


def _line_sum_faults(pieces, rows_by_name):
    faults, sums = [], {}
    for p in pieces:
        key = p["line"].lower()
        if key != OTHER_LINES and key not in rows_by_name:
            faults.append(
                f"Ledger row {p['row']}: line '{p['line']}' is not in the check report."
            )
            continue
        sums[key] = sums.get(key, 0.0) + p["amount"]
    for key, total in sums.items():
        if key == OTHER_LINES:
            continue
        variance = rows_by_name[key]["variance"] or 0.0
        if abs(total - variance) > SUM_EPSILON * max(1.0, abs(variance)):
            faults.append(
                f"'{rows_by_name[key]['line']}': ledger pieces add up to {total:,.4g} but the variance is {variance:,.4g}."
            )
    return faults, sums


def check_ledger(ledger_text, report):
    """Check ledger text (CSV or Markdown) against a check() report and total the material component pieces."""
    pieces, faults = _read_pieces(ledger_text)
    if pieces is None:
        return {"status": "FAIL", "faults": faults}
    tol = report["tolerance"]
    rows = report["rows"]
    rows_by_name = {r["line"].lower(): r for r in rows}
    parents = {r["parent"].lower() for r in rows if r["parent"]}
    for p in pieces:
        faults.extend(_piece_faults(p, tol))
    sum_faults, sums = _line_sum_faults(pieces, rows_by_name)
    faults.extend(sum_faults)
    components = [
        r for r in rows if r["line"].lower() not in parents and r["type"] in MONEY_TYPES
    ]
    for r in components:
        if (
            r["variance"] is not None
            and abs(r["variance"]) > tol
            and r["line"].lower() not in sums
        ):
            faults.append(
                f"'{r['line']}': variance {r['variance']:,.4g} is over the tolerance but has no ledger rows."
            )
    material = {r["line"].lower() for r in components if r["material"]}
    gross = dict.fromkeys(TAGS, 0.0)
    for p in pieces:
        if p["line"].lower() in material and p["tag"] in gross:
            gross[p["tag"]] += abs(p["amount"])
    gross_total = sum(gross.values())
    share = round(gross["Unexplained"] / gross_total * 100, 1) if gross_total else 0.0
    return {
        "status": "FAIL" if faults else "PASS",
        "faults": faults,
        "gross_by_tag": {k: round(v, 10) for k, v in gross.items()},
        "gross_total": round(gross_total, 10),
        "unexplained_share_pct": share,
    }
