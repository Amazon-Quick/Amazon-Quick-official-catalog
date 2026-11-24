"""
description: Run the trend and anomaly analyses on lines of history and return the results, optionally writing the Excel workbook.
last_updated: 2026-11-24

Trend analysis and anomaly detection for lines of history, written up as one Excel workbook.

Two separate analyses on one shared reading of the data. Run either or both:

    import series_review as sr
    prep = sr.prepare(series)                      # check what was read; says what, if anything, to ask
    res = sr.run(series, analyses=("trend", "anomaly"))  # add out_path=<folder>/<name>.xlsx for the workbook
    print(res["summary"]); print(res["caveats"])   # what to tell the user, and what to warn them about

`series` is {name: {"dates": [...], "values": [...]}} as returned by series_intake.extract() and
extract_long(); plain lists of values work too when the grain is given.

Deterministic. No model calls, no network. numpy and xlsxwriter only (openpyxl when reading workbooks).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import os

import anomaly_detection as ad
import numpy as np
import series_engine as eng
import series_workbook
import trend_analysis as ta
from series_prepare import _GRAIN_WORD
from series_prepare import prepare as prepare
from series_summary import _caveats, _fmt, _summary

__all__ = ["prepare", "run", "guide", "find_components", "VERSION", "SENSITIVITY"]


VERSION = "1.0.1"


SENSITIVITY = {
    "low": 4.5,
    "standard": 3.5,
    "high": 3.0,
}  # robust score at which a period counts as unusual


ANALYSES = ("trend", "anomaly")


ANALYSES_GUIDES = ("trend_analysis", "anomaly_detection")


def guide(topic: str) -> str:
    """The reference text for one analysis: 'trend_analysis' or 'anomaly_detection'."""
    if topic not in ANALYSES_GUIDES:
        raise ValueError(
            "topic must be one of {}, not {!r}".format(
                ", ".join(ANALYSES_GUIDES), topic
            )
        )
    # The skill's own references folder, next to this module's scripts/ folder.
    refs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")
    filename = topic.replace("_", "-") + ".md"
    p = os.path.join(refs, filename)
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"reference file {filename} not found in the skill's references folder; "
            f"read references/{filename} with file_read instead"
        )
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def find_components(lines: dict) -> list:
    """Lines that are the sum of other lines: [{'total': name, 'components': [names]}].

    Two shapes are looked for, on the periods where every line has a value: a line equal to the sum of
    all the other lines, and a subtotal equal to the sum of the run of lines directly above it. `lines`
    is {name: values} on one grid, in the order read.
    """
    names = list(lines)
    arr = {n: np.asarray(lines[n], dtype=float) for n in names}
    out, totals = [], set()

    def matches(total, parts):
        tot = np.sum([arr[p] for p in parts], axis=0)
        ok = np.isfinite(arr[total]) & np.isfinite(tot) & (np.abs(tot) > 0)
        return ok.sum() >= 6 and np.allclose(arr[total][ok], tot[ok], rtol=0.002)

    for i, n in enumerate(names):
        found = None
        for k in range(2, min(i, 12) + 1):  # the k lines directly above
            parts = [p for p in names[i - k : i] if p not in totals]
            if len(parts) >= 2 and matches(n, parts):
                found = parts
                break
        if found is None and len(names) >= 3:
            parts = [p for p in names if p != n and p not in totals]
            if len(parts) >= 2 and matches(n, parts):
                found = parts
        if found:
            totals.add(n)
            out.append({"total": n, "components": found})
    return out


def run(
    series: dict,
    analyses=ANALYSES,
    freq: str | None = None,
    units: str = "",
    title: str | None = None,
    fiscal_year_start: int | None = None,
    line_types: dict | None = None,
    min_gap_pct: float = 0.10,
    min_gap_amount: float = 0.0,
    threshold_rule: str = "both",
    sensitivity: str = "standard",
    direction: str = "both",
    focus_last: int | None = None,
    components: list | None = None,
    provenance: dict | None = None,
    source_file: str | None = None,
    out_path: str | None = None,
    today: _dt.date | None = None,
    keep_incomplete: bool = False,
    aggregate_duplicates: bool = False,
    overwrite: bool = False,
) -> dict:
    """Run trend analysis, anomaly detection or both, and write the workbook.

    series            {name: {"dates": [...], "values": [...]}}, e.g. the `series` from series_intake
    analyses          ("trend", "anomaly"), or just one of them
    freq              the time grain if the dates do not settle it; a ValueError says so when it is needed
    units             shown in headers, e.g. "$K"
    fiscal_year_start month the fiscal year starts in (1-12), for year to date
    line_types        {name: 'flow' | 'balance' | 'rate'}: flows are totaled over a window, the others averaged
    min_gap_pct       materiality threshold as a share of expected (0.10 = 10%)
    min_gap_amount    materiality threshold in the data's own units (0 = no amount test)
    threshold_rule    'both' (must reach the percentage and the amount) or 'either'
    sensitivity       'standard' (score 3.5), 'high' (3.0, more flags) or 'low' (4.5, fewer)
    direction         'both', 'above' or 'below': which side of expected to report
    focus_last        only headline events that end within this many latest periods (all are still listed)
    components        [{"total": name, "components": [names]}]: a flagged period on a total is broken down by
                      its components. Found automatically when a line equals the sum of other lines that were
                      read (read totals with series_intake.extract(include_totals=True)); pass [] to switch off
    provenance        {name: where it was read from}, shown on the Method sheet
    out_path          where to write the workbook, only when the user asked for it; None (the default) skips it
    aggregate_duplicates  sum repeated periods only after the user confirms they are additive
    overwrite         replace an existing workbook at out_path (only one this review wrote)

    Returns {'path', 'summary', 'caveats', 'events', 'trends', 'data_checks', 'one_offs', 'lines', 'settings', ...}.
    'one_offs' is {line: [period labels]} for one-off and short-lived events: the periods a forecast of that
    line would usually leave out (the shape the fpa-forecast-coach skill takes as exclude=).
    """
    wanted = tuple(a for a in ANALYSES if a in tuple(analyses))
    if not wanted:
        raise ValueError("analyses must include 'trend', 'anomaly' or both")
    if sensitivity not in SENSITIVITY:
        raise ValueError("sensitivity must be one of {}".format(", ".join(SENSITIVITY)))
    if threshold_rule not in ("both", "either"):
        raise ValueError("threshold_rule must be 'both' or 'either'")
    if direction not in ("both", "above", "below"):
        raise ValueError("direction must be 'both', 'above' or 'below'")
    prep = prepare(
        series,
        freq,
        fiscal_year_start,
        line_types,
        today,
        keep_incomplete,
        aggregate_duplicates,
    )
    if prep["questions"]:
        raise ValueError(
            "Clarification required before analysis. " + " ".join(prep["questions"])
        )
    if prep["freq"] is None:
        raise ValueError(
            "The time grain could not be worked out from the data. Ask the user, then pass freq=."
        )
    f, labels, dates = prep["freq"], prep["labels"], prep["dates"]
    z = SENSITIVITY[sensitivity]
    voc = ta.VOCAB[f]

    lines, events, trends, checks, short = {}, [], [], [], []
    for name, ln in prep["lines"].items():
        d = eng.decompose(
            ln["values"], f, season=prep["season"], pos0=prep["pos0"], z_threshold=z
        )
        rec = {
            "name": name,
            "values": ln["values"],
            "kind": ln["kind"],
            "kind_source": ln["kind_source"],
            "d": d,
            "events": [],
            "checks": [],
            "trend": None,
        }
        if d["status"] != "ok":
            short.append(name)
        if "anomaly" in wanted:
            rec["checks"] = ad.data_checks(ln["values"], d, labels)
            rec["events"] = ad.find_events(d, labels, ln["kind"], direction=direction)
            flagged_by_check = {
                c["index"]: c["check"]
                for c in rec["checks"]
                if c["check"] in ("Zero value", "Sign reversed", "Units")
            }
            for e in rec["events"]:
                e["line"] = name
                hit = [
                    flagged_by_check[t]
                    for t in range(e["start"], e["end"] + 1)
                    if t in flagged_by_check
                ]
                e["data_issue"] = hit[0] if hit else None
                if hit:
                    e["type_label"] = "Possible data issue"
                    e["check"] = (
                        f"See the data checks ({hit[0].lower()}). Confirm the source figure before reading anything into this."
                    )
                e["material"] = ad.is_material(
                    e["gap"], e["gap_pct"], min_gap_pct, min_gap_amount, threshold_rule
                )
            for c in rec["checks"]:
                c["line"] = name
            events += rec["events"]
            checks += rec["checks"]
        if "trend" in wanted:
            rec["trend"] = ta.analyse(
                ln["values"],
                d,
                labels,
                dates if dates and dates[0] else None,
                ln["kind"],
                prep["fiscal_year_start"],
                name,
            )
            trends.append(rec["trend"])
        lines[name] = rec

    if components is None:
        components = find_components({n: r["values"] for n, r in lines.items()})
    for grp in components:
        tot, parts = (
            grp.get("total"),
            [
                p
                for p in grp.get("components", [])
                if p in lines and lines[p]["d"]["status"] == "ok"
            ],
        )
        if tot not in lines or not parts:
            continue
        for e in lines[tot]["events"]:
            if e["type"] in ("new_level", "temporary_level", "unwound_level"):
                contrib = []
                for p in parts:
                    hit = [
                        h
                        for h in lines[p]["d"]["shifts"]
                        if abs(h["index"] - e["start"]) <= 1
                    ]
                    if hit:
                        contrib.append((p, hit[0]["size"]))
            else:
                t = e["peak"]
                contrib = [
                    (p, float(lines[p]["d"]["gap"][t]))
                    for p in parts
                    if np.isfinite(lines[p]["d"]["gap"][t])
                ]
            contrib = sorted(contrib, key=lambda c: -abs(c[1]))[:3]
            if contrib and abs(e["gap"]) > 0:
                e["contributors"] = [
                    {"line": p, "gap": g, "share": g / e["gap"]} for p, g in contrib
                ]
                e["why"] += " Largest movements among its components: {}.".format(
                    "; ".join(
                        "{} {}{} ({:.0f}% of the gap)".format(
                            p, "+" if g > 0 else "-", _fmt(abs(g)), 100 * g / e["gap"]
                        )
                        for p, g in contrib
                    )
                )

    seen, dupes = {}, []
    for name, rec in lines.items():
        key = hashlib.sha1(
            np.nan_to_num(rec["values"], nan=-9.87654321e300).tobytes(),
            usedforsecurity=False,
        ).hexdigest()
        if key in seen:
            dupes.append((seen[key], name))
        else:
            seen[key] = name
    for a, b in dupes:
        checks.append(
            {
                "line": b,
                "check": "Duplicate line",
                "index": 0,
                "period": "all periods",
                "detail": f"Identical to {a} in every period. Check whether the same line was read twice.",
            }
        )

    events.sort(key=lambda e: -abs(e["gap"]))
    settings = {
        "analyses": list(wanted),
        "freq": f,
        "grain_word": _GRAIN_WORD[f],
        "grain_source": prep["grain"]["source"],
        "season": prep["season"],
        "fiscal_year_start": prep["fiscal_year_start"],
        "units": units,
        "min_gap_pct": float(min_gap_pct),
        "min_gap_amount": float(min_gap_amount),
        "threshold_rule": threshold_rule,
        "sensitivity": sensitivity,
        "z_threshold": z,
        "direction": direction,
        "focus_last": focus_last,
        "source_file": source_file,
        "version": VERSION,
        "business_days": prep["business_days"],
    }
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    run_id = hashlib.sha1(
        ("|".join(lines) + stamp).encode(), usedforsecurity=False
    ).hexdigest()[:8]
    res = {
        "title": title or "Trend analysis and anomaly detection",
        "run_id": run_id,
        "run_at": stamp,
        "labels": labels,
        "dates": dates,
        "lines": lines,
        "events": events,
        "trends": trends,
        "data_checks": checks,
        "issues": prep["issues"],
        "settings": settings,
        "provenance": provenance or {},
        "short": short,
        "skipped": prep["skipped"],
        "vocab": voc,
        "path": None,
        "components": components,
    }
    # periods a forecast should probably leave out: single unusual periods and short runs, not changes in level
    one_offs: dict = {}
    for e in events:
        if e["type"] in ("one_off", "pair", "temporary") and not e.get("data_issue"):
            one_offs.setdefault(e["line"], [])
            one_offs[e["line"]] += [
                labels[t]
                for t in range(e["start"], e["end"] + 1)
                if lines[e["line"]]["d"]["flagged"][t]
            ]
    res["one_offs"] = {k: sorted(set(v), key=labels.index) for k, v in one_offs.items()}
    res["summary"], res["caveats"] = _summary(res), _caveats(res)
    if out_path:
        if os.path.exists(out_path) and not overwrite:
            raise FileExistsError(
                f"{out_path} already exists. Choose another name, or pass overwrite=True only "
                "to replace a workbook this review wrote."
            )
        folder = os.path.dirname(out_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        res["path"] = series_workbook.write(res, out_path)
    return res
