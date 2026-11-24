"""
description: Fit the trend and seasonality, model forward drivers, run one Monte Carlo simulation and read Bear, Base and Bull, P(hit target), the variance bridge, the sensitivity tornado and the areas to probe off it.
last_updated: 2026-11-24

Scenario analysis engine, numpy and pandas only. Trend fits are ordinary least squares with numpy.polyfit.
This module is the skill's single entry point: it also exposes the intake and segment functions, so the
agent imports only scenario_engine. Every argument and returned field is documented in
references/engine-api.md; the agent never needs to open this file.

    import scenario_engine as sa
    df = sa.load("revenue_actuals.csv", colmap)          # or sa.prepare(a_dataframe, colmap)
    res = sa.run(df, config, drivers=None, context_findings=None)
    html_path = sa.write_report(res, "<folder the user chose>/Scenario_Analysis.html")
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import scenario_report
from scenario_config import DEFAULT_CONFIG, validate_config
from scenario_intake import (
    DEFAULT_COLMAP,
    SYNONYMS,
    ClarificationRequired,
    _is_num,
    file_text,
    inspect_source,
    load,
    prepare,
    suggest_colmap,
)
from scenario_segments import segment_screen

__all__ = [
    "DEFAULT_COLMAP",
    "DEFAULT_CONFIG",
    "SYNONYMS",
    "ClarificationRequired",
    "fit_trend",
    "inspect_source",
    "load",
    "prepare",
    "run",
    "segment_screen",
    "suggest_colmap",
    "check_report",
    "summarize",
    "write_report",
]

SIGNED = True


def _freq(periods, cfg):
    if cfg.get("freq"):
        return cfg["freq"]
    if _is_num(periods) or len(periods) < 3:
        return "M"
    days = np.median(
        np.diff(pd.to_datetime(periods).values).astype("timedelta64[D]").astype(float)
    )
    return "D" if days < 3 else "W" if days < 10 else "M" if days < 45 else "Q"


def _regularize(df, cfg):
    """Reindex dated history onto a complete calendar so a missing period stays a gap instead of shifting
    the fiscal year. Returns (df on the full calendar, list of missing period labels)."""
    if df.empty:
        return df, []
    if _is_num(df["period"]):
        if df["period"].duplicated().any():
            raise ClarificationRequired(
                "Duplicate numeric periods need a decision: corrections, segments, or additive rows?"
            )
        return df, []
    freq = _freq(df["period"].values, cfg)
    pi = pd.PeriodIndex(pd.to_datetime(df["period"]), freq=freq)
    if pi.duplicated().any():
        duplicate = df.loc[
            pi.duplicated(keep=False),
            ["period"] + (["_source_row"] if "_source_row" in df else []),
        ]
        rows = [
            f"source row {r.get('_source_row', '?')}: {file_text(r['period'])}"
            for r in duplicate.head(8).to_dict("records")
        ]
        raise ClarificationRequired(
            "Duplicate periods need a decision: separate segments, corrections, or additive rows? "
            + "; ".join(rows)
        )
    full = pd.period_range(pi.min(), pi.max(), freq=freq)
    if len(full) == len(pi):
        out = df.copy()
        out.attrs = dict(df.attrs, freq=freq)
        return out, []
    keyed = df.assign(_p=pi).set_index("_p").reindex(full)
    keyed["period"] = full.to_timestamp()
    out = keyed.reset_index(drop=True)
    out.attrs = dict(df.attrs, freq=freq)
    value = "measure" if "measure" in out else ("inflow" if "inflow" in out else None)
    missing = [str(p) for p, isnew in zip(full, ~full.isin(pi), strict=False) if isnew]
    if value is not None:
        last = out[value].last_valid_index()
        missing = [
            m
            for m, p in zip(
                missing,
                [full.get_loc(pd.Period(m, freq=freq)) for m in missing],
                strict=False,
            )
            if last is None or p <= last
        ]
    return out, missing


def _labels(periods, freq):
    if _is_num(periods):
        return [str(int(p)) for p in periods]
    pi = pd.PeriodIndex(pd.to_datetime(periods), freq=freq)
    return [str(p) for p in pi]


def _poly(x, y, deg):
    """Ordinary least squares polynomial fit of degree deg; returns (coefficients, fitted values, R2)."""
    deg = int(min(deg, max(len(x) - 1, 0)))
    coef = np.polyfit(x, y, deg) if len(x) > deg else np.array([y.mean()])
    fit = np.polyval(coef, x)
    ss_res, ss_tot = float(((y - fit) ** 2).sum()), float(((y - y.mean()) ** 2).sum())
    return coef, fit, (1 - ss_res / ss_tot) if ss_tot > 0 else 0.0


def fit_trend(y: np.ndarray, cfg: dict) -> dict:
    """Linear and polynomial fits, residual sigma, seasonality indices and the fit-quality gate."""
    L = int(cfg["fy_length_periods"])
    ok = ~np.isnan(y)
    x_all = np.arange(len(y), dtype=float)
    x, y = x_all[ok], y[ok]
    n = len(y)
    _, _, r2_lin = _poly(x, y, 1)
    coef, fit, r2 = _poly(x, y, cfg["poly_degree"])
    resid = y - fit
    sigma = float(resid.std(ddof=1)) if n > 2 else float(y.std())
    seas, seas_src = np.ones(L), "none"
    if cfg.get("seasonality_profile") is not None:
        seas = np.asarray(cfg["seasonality_profile"], dtype=float)
        seas, seas_src = seas / seas.mean(), "user profile"
    elif cfg["detect_seasonality"] and n >= L:
        if (y <= 0).any() or (fit <= 0.05 * np.abs(y).mean()).any():
            seas_src = "none (actuals or fitted trend not clearly positive)"
        else:
            detr = y / fit
            idx = x.astype(int) % L
            seas = np.array(
                [detr[idx == k].mean() if (idx == k).any() else 1.0 for k in range(L)]
            )
            seas, seas_src = seas / seas.mean(), "estimated from history"
    quality = (
        "HIGH (trend primary)"
        if r2 > 0.70
        else "MEDIUM (lean on drivers)"
        if r2 >= 0.50
        else "LOW (weight drivers and judgment)"
    )
    return {
        "coef": coef,
        "fit": fit,
        "r2": float(r2),
        "r2_linear": float(r2_lin),
        "resid_sigma": sigma,
        "seasonality": seas,
        "seasonality_source": seas_src,
        "quality": quality,
    }


def _project(trend, idx):
    return np.polyval(trend["coef"], idx.astype(float))


def prepare_drivers(drivers, cfg, period_index_of) -> list:
    """Normalize driver rows to {name, value, prob, offset, stage}. prob comes from its stage when blank.
    `period_index_of(date)` maps a driver date to the absolute period index used by the model."""
    out = []
    for d in drivers or []:
        prob = d.get("prob", d.get("driver_prob"))
        stage = d.get("stage", d.get("driver_stage"))
        if prob is None or (isinstance(prob, float) and math.isnan(prob)):
            prob = cfg["driver_stage_prob"].get(stage)
        date = d.get("date", d.get("driver_date"))
        out.append(
            {
                "name": str(d.get("name", d.get("driver_name", "driver"))),
                "value": float(d.get("value", d.get("driver_value", 0)) or 0),
                "prob": None if prob is None else float(prob),
                "stage": stage,
                "offset": d.get("period_offset")
                if d.get("period_offset") is not None
                else (period_index_of(date) if date is not None else None),
            }
        )
    return out


def run(
    df: pd.DataFrame, config: dict | None = None, drivers=None, context_findings=None
) -> dict:
    """The whole method: validate, trend, drivers, one Monte Carlo, scenarios, P(hit target), bridge, tornado,
    what has to be true, provenance and areas to probe. Returns a JSON-ready dict for the report."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    user_set = {
        k
        for k, v in (config or {}).items()
        if k in DEFAULT_CONFIG and v != DEFAULT_CONFIG[k]
    }

    def cfg_label(*keys):
        """Configuration is never DATA-BACKED: USER-SET when the user changed it, else DEFAULT."""
        return "USER-SET" if any(k in user_set for k in keys) else "DEFAULT"

    mtype = df.attrs.get("measure_type", "flow")
    if mtype not in ("flow", "balance"):
        raise ClarificationRequired(
            "Is the measure a per-period flow or a closing balance?"
        )
    if mtype == "balance" and not {"opening", "inflow", "outflow"} <= set(df.columns):
        raise ClarificationRequired(
            "A balance forecast needs opening, inflow, and outflow columns. Which columns contain them?"
        )
    balance = mtype == "balance" and {"inflow", "outflow"} <= set(df.columns)
    L, N = validate_config(cfg, len(drivers or []))
    if cfg["target_direction"] not in ("at_least", "at_most"):
        raise ClarificationRequired(
            "Does hitting target mean at least the target, or at most the target (for example, an expense cap)?"
        )
    limits, probes = [], []
    units = cfg.get("units")
    if units is not None and not isinstance(units, str):
        raise ClarificationRequired(
            "What unit label should the report use, including currency and scale where applicable?"
        )
    units = units.strip() if units else None
    if not units:
        limits.append(
            "Units not supplied; confirm the forecast and target units before using or sharing this report."
        )

    # 1. Validate the history; the current period comes from the data, never the clock
    value_col = "measure"
    df, missing_periods = _regularize(df, cfg)
    act = df[df[value_col].notna()].copy() if value_col in df else df.iloc[0:0]
    if balance:
        act = df[df["inflow"].notna() & df["outflow"].notna()].copy()
    if act.empty:
        raise ValueError("No actuals to forecast from.")
    last_act = act.index[-1]
    hist = df.loc[:last_act]
    n_hist = len(hist)
    freq = df.attrs.get("freq") or _freq(act["period"].values, cfg)
    labels_hist = _labels(hist["period"].values, freq)
    current_period = labels_hist[-1]
    if n_hist < L:
        limits.append(
            f"Only {n_hist} periods of history (under one fiscal year of {L}); seasonality is not estimated."
        )
    if missing_periods:
        limits.append(
            "Missing period(s) in the history: "
            + ", ".join(missing_periods[:12])
            + ". They are left as gaps in the calendar, never interpolated, and the fiscal-year window is set by date, not by row count."
        )
    if not balance and (act[value_col] < 0).any():
        limits.append(
            f"{int((act[value_col] < 0).sum())} negative actual(s) in the history; confirm they are real before relying on the trend."
        )
    rf_breaks = []
    if mtype == "balance" and {"opening", "measure"} <= set(df.columns):
        o, c = df["opening"].values[1:], df["measure"].values[:-1]
        rf_breaks = [
            _labels(
                df["period"].values,
                df.attrs.get("freq") or _freq(df["period"].values, cfg),
            )[i + 1]
            for i in range(min(len(o), n_hist - 1))
            if not (pd.isna(o[i]) or pd.isna(c[i]))
            and abs(o[i] - c[i]) > 1e-6 * max(1, abs(c[i]))
        ]
        if rf_breaks:
            limits.append(
                "Roll-forward breaks (opening is not the prior closing) at: "
                + ", ".join(rf_breaks[:6])
            )

    if cfg.get("fy_start_period") and not _is_num(act["period"]):
        fy0 = pd.Period(cfg["fy_start_period"], freq=freq)
        hist_p = pd.PeriodIndex(pd.to_datetime(hist["period"]), freq=freq)
        if fy0.ordinal > hist_p[-1].ordinal:
            raise ClarificationRequired(
                "The fiscal-year start is after the last actual period. "
                "Which fiscal-year start should be used?"
            )
        offset = (hist_p[-1].ordinal - fy0.ordinal) % L
        start_idx = n_hist - 1 - offset
        if start_idx < 0:
            raise ClarificationRequired(
                "The history starts after the fiscal-year start. Supply the "
                "earlier actuals or explicitly enter zero for periods confirmed "
                "to have had no activity."
            )
        fy_source = "CONFIG fy_start_period"
    else:
        start_idx = (
            (n_hist - 1) // L
        ) * L  # fiscal years aligned to the data's first period
        fy_source = "aligned to the first period in the data"
    start_idx = max(0, min(start_idx, n_hist - 1))
    n_ytd = n_hist - start_idx
    remaining = max(L - n_ytd, 0)
    if not balance and hist["measure"].iloc[start_idx:].isna().any():
        raise ClarificationRequired(
            "Missing actuals in the fiscal-year history prevent a full-year total. "
            "Supply the missing values or confirm that specific missing periods truly had zero activity."
        )
    if balance and hist[["inflow", "outflow"]].isna().any().any():
        raise ClarificationRequired(
            "Missing inflow or outflow history needs clarification before a balance forecast."
        )
    if rf_breaks:
        raise ClarificationRequired(
            "The balance history does not roll forward at "
            + ", ".join(rf_breaks[:6])
            + ". Which opening balance, closing balance, or adjustment should be used?"
        )
    fut_idx = np.arange(n_hist, n_hist + remaining)
    labels_fut = _future_labels(hist["period"].values, freq, remaining)

    series = (
        {"measure": hist[value_col].values.astype(float)}
        if not balance
        else {
            "inflow": hist["inflow"].values.astype(float),
            "outflow": hist["outflow"].values.astype(float),
        }
    )
    trends = {k: fit_trend(v, cfg) for k, v in series.items()}
    main = trends["measure"] if not balance else trends["inflow"]
    for k, t in trends.items():
        if t["seasonality_source"].startswith("none ("):
            limits.append(
                f"Seasonality for {k} was not estimated: actuals or the fitted "
                "trend are not clearly positive for multiplicative seasonality."
            )
        if t["r2"] < 0.50:
            probes.append(
                (
                    "P1",
                    f"Trend fit for {k} is LOW confidence (R2 {t['r2']:.2f}); drivers and judgment carry more weight.",
                )
            )

    def period_index_of(date):
        if _is_num(act["period"]):
            return int(date) - int(hist["period"].iloc[0])
        p0 = pd.Period(pd.to_datetime(hist["period"].iloc[0]), freq=freq)
        return int(pd.Period(pd.to_datetime(date), freq=freq).ordinal - p0.ordinal)

    drv = prepare_drivers(drivers, cfg, period_index_of)
    for d in drv:
        if d["prob"] is None:
            raise ClarificationRequired(
                f"Driver {file_text(d['name'])} has no probability for stage {file_text(d['stage'])}. "
                "What probability should be used, or should this driver be excluded?"
            )
        if not math.isfinite(d["prob"]) or not 0 <= d["prob"] <= 1:
            raise ClarificationRequired(
                f"Driver {file_text(d['name'])} probability is {d['prob']}. Is that a fraction or a percentage?"
            )
        if d["offset"] is None:
            probes.append(
                (
                    "P2",
                    f"Driver {file_text(d['name'])} has no date; it is assumed to land in the remaining periods of the year.",
                )
            )
    judg = cfg["judgment_adjustments"] or []

    rng = np.random.default_rng(cfg["seed"])
    seas_f = {k: t["seasonality"][fut_idx % L] for k, t in trends.items()}
    base_f = {k: _project(t, fut_idx) * seas_f[k] for k, t in trends.items()}
    paths = np.zeros((N, remaining))
    for k in base_f:
        draw = base_f[k] + rng.normal(0, trends[k]["resid_sigma"], size=(N, remaining))
        paths += draw if k in ("measure", "inflow") else -draw
    for d in drv:
        hit = rng.random(N) < d["prob"]
        off = (
            (n_hist + rng.integers(0, max(remaining, 1), N))
            if d["offset"] is None
            else np.rint(rng.normal(d["offset"], cfg["driver_timing_sigma"], N)).astype(
                int
            )
        )
        col = off - n_hist
        ok = hit & (col >= 0) & (col < remaining)
        np.add.at(paths, (np.nonzero(ok)[0], col[ok]), d["value"])
    judg_draw = np.zeros(N)
    for a in judg:
        lo, mid, hi = float(a["low"]), float(a["likely"]), float(a["high"])
        judg_draw += (
            np.full(N, mid)
            if hi <= lo
            else rng.triangular(lo, min(max(mid, lo), hi), hi, N)
        )

    if balance:
        opening_now = (
            float(df["measure"].dropna().iloc[-1])
            if "measure" in df and df["measure"].notna().any()
            else float(df["opening"].dropna().iloc[-1])
            + float(series["inflow"][-1] - series["outflow"][-1])
        )
        level_paths = (
            opening_now + np.cumsum(paths, axis=1)
            if remaining
            else np.full((N, 0), opening_now)
        )
        sims = (
            level_paths[:, -1] if remaining else np.full(N, opening_now)
        ) + judg_draw
        ytd_actual, outcome_label = opening_now, "closing balance"
        hist_values = (
            df["measure"].values[:n_hist].astype(float)
            if "measure" in df
            else np.cumsum(series["inflow"] - series["outflow"])
        )
    else:
        ytd_actual = float(np.nansum(series["measure"][start_idx:]))
        level_paths = paths
        sims = ytd_actual + paths.sum(axis=1) + judg_draw
        outcome_label = "fiscal-year total"
        hist_values = series["measure"]

    pct = {p: float(np.percentile(sims, p)) for p in (5, 10, 25, 50, 75, 90, 95)}
    mean = float(sims.mean())
    bear, base, bull = (
        float(np.percentile(sims, cfg[k]))
        for k in ("bear_percentile", "base_percentile", "bull_percentile")
    )
    band = cfg["bull_percentile"] - cfg["bear_percentile"]

    bench_fy = None
    if "benchmark" in df.columns and df["benchmark"].notna().any():
        b = df["benchmark"].values.astype(float)
        if balance:
            bench_fy = (
                float(b[start_idx + L - 1])
                if len(b) >= start_idx + L and np.isfinite(b[start_idx + L - 1])
                else None
            )
        else:
            win = b[start_idx : start_idx + L]
            bench_fy = (
                float(win.sum()) if len(win) == L and np.isfinite(win).all() else None
            )
        if bench_fy is None:
            msg = (
                f"Benchmark is not a complete {L}-period full-year plan"
                if not balance
                else "Benchmark does not include the fiscal-year closing balance"
            )
            if cfg["target"] is None:
                raise ClarificationRequired(
                    msg
                    + ". What is the full-year target, in the same units as the actuals?"
                )
            limits.append(
                msg
                + "; excluded from the full-year bridge. The explicit target is used."
            )
    if cfg["target"] is None and bench_fy is None:
        raise ClarificationRequired(
            "No target or complete benchmark was supplied. What full-year total or closing-balance target should be tested?"
        )
    target = cfg["target"] if cfg["target"] is not None else bench_fy
    try:
        target = float(target)
    except (ValueError, TypeError):
        raise ClarificationRequired(
            "Target must be a number in the same units as the actuals. What target should be used?"
        ) from None
    if not math.isfinite(target):
        raise ClarificationRequired(
            "Target must be a finite number in the same units as the actuals."
        )
    target_source = (
        "CONFIG target" if cfg["target"] is not None else "benchmark FY total"
    )
    p_hit = (
        float((sims >= target).mean())
        if cfg["target_direction"] == "at_least"
        else float((sims <= target).mean())
    )

    per = {
        "labels": labels_hist + labels_fut,
        "actual": [
            None if np.isnan(v) else float(v)
            for v in np.asarray(hist_values, dtype=float)
        ]
        + [None] * remaining,
        "bear": [None] * n_hist,
        "base": [None] * n_hist,
        "bull": [None] * n_hist,
        "n_hist": n_hist,
        "line_basis": "one simulated run per scenario, chosen so its outcome equals that scenario; the periods add up to it",
    }
    rep_runs = {}
    for key, val in (("bear", bear), ("base", base), ("bull", bull)):
        i = int(
            np.argmin(np.abs(sims - val))
        )  # the run whose outcome is that percentile
        rep_runs[key] = i
        run_path = level_paths[i] if remaining else np.zeros(0)
        if remaining:
            # put the judgment draw (not period-specific) and any rounding into the last period, so the run ties exactly
            run_path = run_path.astype(float).copy()
            tie = val - (run_path[-1] if balance else ytd_actual + run_path.sum())
            run_path[-1] += tie
        per[key] += [float(v) for v in run_path]
    if "benchmark" in df.columns:
        per["benchmark"] = [
            None if pd.isna(v) else float(v)
            for v in df["benchmark"].values[: n_hist + remaining]
        ]

    trend_noseas = sum(
        float(_project(trends[k], fut_idx).sum())
        * (1 if k in ("measure", "inflow") else -1)
        for k in trends
    )
    trend_seas = sum(
        float(base_f[k].sum()) * (1 if k in ("measure", "inflow") else -1)
        for k in base_f
    )
    drv_exp = sum(
        d["value"]
        * d["prob"]
        * _land_share(d, n_hist, remaining, cfg["driver_timing_sigma"])
        for d in drv
    )
    judg_exp = sum(
        (float(a["low"]) + float(a["likely"]) + float(a["high"])) / 3 for a in judg
    )
    start = bench_fy if bench_fy is not None else ytd_actual
    steps = [
        (
            "Benchmark"
            if bench_fy is not None
            else ("Opening balance" if balance else "Year to date actual"),
            start,
            "total",
        ),
        (
            "Trend delta"
            if bench_fy is not None
            else "Trend projection (remaining periods)",
            ytd_actual + trend_noseas - start,
            "step",
        ),
        ("Driver conversion", drv_exp, "step"),
        ("Seasonality", trend_seas - trend_noseas, "step"),
        ("Judgment", judg_exp, "step"),
    ]
    expected = ytd_actual + trend_seas + drv_exp + judg_exp
    if abs(base - expected) > 1e-9 * max(1.0, abs(base)):
        steps.append(
            (
                f"Distribution shape (P{int(cfg['base_percentile'])} against expected)",
                base - expected,
                "step",
            )
        )
    steps.append(("Base scenario", base, "total"))
    bridge = [{"label": a, "value": float(b), "kind": c} for a, b, c in steps]

    tornado = []
    if remaining:
        s1 = sum(trends[k]["resid_sigma"] for k in trends) * math.sqrt(remaining)
        tornado.append(
            {
                "label": "Trend level (+/- 1 sigma of residual error)",
                "low": expected - s1,
                "high": expected + s1,
            }
        )
        if not trends[next(iter(trends))]["seasonality_source"].startswith("none"):
            tornado.append(
                {
                    "label": "Seasonality (off or on)",
                    "low": min(expected, expected - (trend_seas - trend_noseas)),
                    "high": max(expected, expected - (trend_seas - trend_noseas)),
                }
            )
    for d in drv:
        share = _land_share(d, n_hist, remaining, cfg["driver_timing_sigma"])
        tornado.append(
            {
                "label": f"Driver: {d['name']} (does not convert or converts)",
                "low": expected - d["value"] * d["prob"] * share,
                "high": expected + d["value"] * (1 - d["prob"]) * share,
            }
        )
    for a in judg:
        mid = (float(a["low"]) + float(a["likely"]) + float(a["high"])) / 3
        tornado.append(
            {
                "label": f"Judgment: {a['label']}",
                "low": expected - mid + float(a["low"]),
                "high": expected - mid + float(a["high"]),
            }
        )
    for t in tornado:
        t["swing"] = t["high"] - t["low"]
    tornado.sort(key=lambda t: -abs(t["swing"]))

    top = tornado[:3]
    wht = {
        "bull": [
            f"{t['label'].split(' (')[0]} lands at its high end (about {_fmt(t['high'] - expected, SIGNED)} compared with expected)."
            for t in top
        ],
        "bear": [
            f"{t['label'].split(' (')[0]} lands at its low end (about {_fmt(t['low'] - expected, SIGNED)} compared with expected)."
            for t in top
        ],
    }
    for c in context_findings or []:
        side = (
            "bull"
            if c.get("direction", "").lower() in ("up", "upside", "bull")
            else "bear"
        )
        wht[side].append(
            f"{c.get('claim', '')} (CONTEXT-INFORMED: {c.get('source', 'context')})"
        )
        if c.get("conflict"):
            probes.append(
                (
                    "P1",
                    f"Context conflicts with the data: {c.get('claim', '')} ({c.get('source', '')})",
                )
            )
        elif c.get("unverified", True):
            probes.append(
                (
                    "P2",
                    f"Verify context claim: {c.get('claim', '')} ({c.get('source', '')})",
                )
            )

    assumptions = [
        {
            "name": "Trend fit",
            "value": f"polynomial degree {cfg['poly_degree']}, R2 {main['r2']:.2f} ({main['quality']})",
            "label": "DATA-BACKED",
        },
        {
            "name": "Residual error",
            "value": _fmt(main["resid_sigma"]) + " per period",
            "label": "DATA-BACKED",
        },
        {
            "name": "Seasonality",
            "value": main["seasonality_source"],
            "label": "DEFAULT"
            if main["seasonality_source"].startswith("none")
            else (
                "USER-SET"
                if main["seasonality_source"] == "user profile"
                else "DATA-BACKED"
            ),
        },
        {
            "name": "Scenario percentiles",
            "value": f"Bear P{cfg['bear_percentile']}, Base P{cfg['base_percentile']}, Bull P{cfg['bull_percentile']}",
            "label": cfg_label("bear_percentile", "base_percentile", "bull_percentile"),
        },
        {
            "name": "Monte Carlo iterations",
            "value": f"{N:,} (seed {cfg['seed']})",
            "label": cfg_label("mc_iterations", "seed"),
        },
        {
            "name": "Fiscal year",
            "value": f"{L} periods, {fy_source}; {n_ytd} actual, {remaining} forecast",
            "label": cfg_label("fy_start_period", "fy_length_periods"),
        },
        {
            "name": "Target",
            "value": f"{_fmt(target)} ({target_source})",
            # A target is the user's choice, whether stated or taken from their own plan: never DATA-BACKED.
            "label": "USER-SET",
        },
        {
            "name": "Target direction",
            "value": cfg["target_direction"],
            "label": cfg_label("target_direction"),
        },
    ]
    if drv:
        assumptions.append(
            {
                "name": "Driver timing sigma",
                "value": f"{cfg['driver_timing_sigma']} periods",
                "label": cfg_label("driver_timing_sigma"),
            }
        )
        if (
            any(d["stage"] is not None for d in drv)
            and "driver_stage_prob" not in user_set
        ):
            assumptions.append(
                {
                    "name": "Driver stage probabilities",
                    "value": ", ".join(
                        f"{k} {v:.0%}" for k, v in cfg["driver_stage_prob"].items()
                    ),
                    "label": "DEFAULT",
                }
            )
            probes.append(
                (
                    "P2",
                    "Driver stage probabilities are the shipped defaults; replace them with the user's own conversion rates.",
                )
            )
    for a in judg:
        assumptions.append(
            {
                "name": f"Judgment: {a['label']}",
                "value": f"low {_fmt(a['low'])}, likely {_fmt(a['likely'])}, high {_fmt(a['high'])}",
                "label": "CONTEXT-INFORMED" if a.get("source") else "USER-SET",
                "source": a.get("source", ""),
            }
        )
    for msg in limits:
        probes.append(("P2", msg))
    if not drv and not judg:
        probes.append(
            (
                "P3",
                "No drivers or judgment adjustments were given; the range reflects trend and seasonality only.",
            )
        )

    buildup = {
        name: {
            "ytd_or_opening": ytd_actual,
            "trend": trend_seas,
            "drivers": drv_exp,
            "judgment": judg_exp,
            "expected": expected,
            "deviation": val - expected,
            "scenario": val,
        }
        for name, val in (("Bear", bear), ("Base", base), ("Bull", bull))
    }
    # Deviation is scenario minus expected: the build-up ties by construction.
    if any(not math.isfinite(value) for v in buildup.values() for value in v.values()):
        raise ClarificationRequired(
            "The scenario build-up contains a non-finite amount. "
            "Review the mapped values and assumptions before reporting a result."
        )
    return {
        "current_period": current_period,
        "measure_type": "balance" if balance else "flow",
        "outcome_label": outcome_label,
        "units": units,
        "freq": freq,
        "n_hist": n_hist,
        "n_ytd": n_ytd,
        "remaining": remaining,
        "limitations": limits,
        "trend": {
            k: {
                "r2": t["r2"],
                "r2_linear": t["r2_linear"],
                "resid_sigma": t["resid_sigma"],
                "quality": t["quality"],
                "seasonality": [float(x) for x in t["seasonality"]],
                "seasonality_source": t["seasonality_source"],
            }
            for k, t in trends.items()
        },
        "percentiles": pct,
        "mean": mean,
        "bear": bear,
        "base": base,
        "bull": bull,
        "band": band,
        "percentile_labels": {
            "bear": cfg["bear_percentile"],
            "base": cfg["base_percentile"],
            "bull": cfg["bull_percentile"],
        },
        "target": float(target),
        "target_source": target_source,
        "benchmark_fy": bench_fy,
        "p_hit": p_hit,
        "target_direction": cfg["target_direction"],
        "input_audit": df.attrs.get("input_audit", {}),
        "expected": expected,
        "bridge": bridge,
        "tornado": tornado,
        "what_has_to_be_true": wht,
        "assumptions": assumptions,
        "areas_to_probe": [
            {"priority": p, "item": t} for p, t in sorted(probes, key=lambda x: x[0])
        ],
        "buildup": buildup,
        "per_period": per,
        "histogram": _hist(sims),
        "drivers": drv,
        "context_findings": list(context_findings or []),
        "iterations": N,
    }


def _land_share(d, n_hist, remaining, sigma):
    """Share of a driver's timing distribution that lands inside the forecast window."""
    if remaining <= 0:
        return 0.0
    if d["offset"] is None:
        return 1.0

    def cdf(x):
        return (
            0.5 * (1 + math.erf((x - d["offset"]) / (sigma * math.sqrt(2))))
            if sigma > 0
            else float(x >= d["offset"])
        )

    return max(0.0, cdf(n_hist + remaining - 0.5) - cdf(n_hist - 0.5))


def _future_labels(periods, freq, k):
    if k <= 0:
        return []
    if _is_num(periods):
        last = int(periods[-1])
        return [str(last + i + 1) for i in range(k)]
    last = pd.Period(pd.to_datetime(periods[-1]), freq=freq)
    return [str(last + i + 1) for i in range(k)]


def _hist(sims, bins=40):
    counts, edges = np.histogram(sims, bins=bins)
    return {"counts": [int(c) for c in counts], "edges": [float(e) for e in edges]}


def _fmt(v, signed=False):
    v = float(v)
    s = f"{v:+,.0f}" if signed else f"{v:,.0f}"
    return s


SUMMARY_TOP_ITEMS = 3
SUMMARY_MAX_ROWS = 20


def summarize(res: dict) -> dict:
    """The fields the chat summary and the step 8 checks need, so the agent never prints the whole result."""
    per = res["per_period"]
    nh, flow = per["n_hist"], res["measure_type"] == "flow"
    ytd = res["buildup"]["Base"]["ytd_or_opening"]

    def path_total(key: str) -> float | None:
        fut = per[key][nh:]
        if not fut:
            return None
        return float(ytd + sum(fut)) if flow else float(fut[-1])

    bridge = res["bridge"]
    audit = res.get("input_audit", {})
    return {
        "limitations": res["limitations"],
        "current_period": res["current_period"],
        "outcome_label": res["outcome_label"],
        "units": res["units"],
        "bear": res["bear"],
        "base": res["base"],
        "bull": res["bull"],
        "band_percent": res["band"],
        "target": res["target"],
        "target_source": res["target_source"],
        "target_direction": res["target_direction"],
        "p_hit": res["p_hit"],
        "trend_r2": {k: round(t["r2"], 3) for k, t in res["trend"].items()},
        "forecast_periods": per["labels"][nh:],
        "bridge": [(s["label"], round(s["value"], 6)) for s in bridge],
        "bridge_gap": float(
            bridge[0]["value"]
            + sum(s["value"] for s in bridge[1:-1])
            - bridge[-1]["value"]
        ),
        "path_gaps": {
            k: None if path_total(k) is None else float(path_total(k) - res[k])
            for k in ("bear", "base", "bull")
        },
        "top_tornado": [
            (t["label"], round(t["swing"], 6))
            for t in res["tornado"][:SUMMARY_TOP_ITEMS]
        ],
        "drivers_included": [d["name"] for d in res["drivers"]],
        "areas_to_probe": res["areas_to_probe"],
        "included_rows": audit.get("included_rows"),
        "excluded_source_rows": audit.get("excluded_source_rows", [])[
            :SUMMARY_MAX_ROWS
        ],
        "excluded_row_count": len(audit.get("excluded_source_rows", [])),
    }


def write_report(
    res: dict, out_path: str, title: str | None = None, overwrite: bool = False
) -> str:
    """Write the standalone HTML report with the sibling scenario_report module."""
    return scenario_report.write(res, out_path, title=title, overwrite=overwrite)


def check_report(out_path: str, units: str) -> dict:
    """Where the confirmed unit label appears in the written report, without reading it into chat."""
    return scenario_report.check(out_path, units)
