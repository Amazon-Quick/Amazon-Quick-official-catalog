"""
description: Entry point. Reconcile plan or budget against GL actuals, pending invoices and open purchase-order commitments at the plan's own grain, placing each dollar in one bucket, converting currencies by period, screening for outliers, and writing results.json plus a tie-out proof.
last_updated: 2026-11-24
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from pydantic import ValidationError
from recon_ledger import CommitmentLedger, FxConverter, LineKeyer
from recon_models import (
    CommitmentRow,
    DrillRow,
    FilterAction,
    Finding,
    FlagItem,
    HeadcountRow,
    LineResult,
    MonthlyRow,
    Nature,
    ProofCheck,
    RateDirection,
    ReconResult,
    ReconSpec,
    SourceSpec,
    SpecError,
    TieOut,
    Tier,
    Totals,
    UnplannedRow,
    Window,
)
from recon_parsing import (
    DATA_TEXT_LIMIT,
    PERIOD_RE,
    PeriodParser,
    file_data,
    money,
    nice_round,
    normal_text,
    parse_date,
    pct_text,
    period_range,
    safe_pct,
    shift_period,
)
from recon_screen import HeadcountScreen, OutlierScreen
from recon_sources import SourceNormalizer, SpecReader, TableReader


class _PrintStream:
    """Routes log records to stdout via print (the sandbox only returns stdout)."""

    def write(self, message: str) -> None:
        if message.strip():
            print(message, end="")

    def flush(self) -> None:
        pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=_PrintStream(),
    force=True,
)
logger = logging.getLogger("run_reconciliation")

ENGINE_VERSION = "1.0.0"
TIE_TOLERANCE = 0.01
DRILL_ROWS = 25
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CAD": "C$",
    "AUD": "A$",
    "INR": "₹",
}


class Reconciliation:
    """Facade: loads every source in the spec, reconciles, screens, proves the tie-out and returns a ReconResult."""

    def __init__(
        self,
        spec: ReconSpec,
        base_dir: Path,
        drill_key: str | None = None,
        drill_period: str | None = None,
    ) -> None:
        self.spec = spec
        self.base_dir = base_dir
        self.drill_key = drill_key
        self.drill_period = drill_period

    def run(self) -> ReconResult:
        spec = self.spec
        findings: list[Finding] = []
        tie: list[TieOut] = []
        if not PERIOD_RE.match(spec.last_closed_period):
            raise SpecError("last_closed_period must be YYYY-MM")
        periods = PeriodParser(
            spec.fiscal_year_start_month, spec.fiscal_year_label, spec.date_order
        )
        reader = TableReader(self.base_dir)
        window = self._window()
        as_of = date.fromisoformat(window.as_of_date)
        symbol = CURRENCY_SYMBOLS.get(
            spec.reporting_currency.upper(), spec.reporting_currency.upper() + " "
        )

        plan = self._load("plan", spec.sources.plan, reader, periods, findings)
        gl = self._load("actuals", spec.sources.actuals, reader, periods, findings)
        pos = (
            self._load(
                "commitments", spec.sources.commitments, reader, periods, findings
            )
            if spec.sources.commitments
            else None
        )
        inv = (
            self._load("invoices", spec.sources.invoices, reader, periods, findings)
            if spec.sources.invoices
            else None
        )
        hc = (
            self._load("headcount", spec.sources.headcount, reader, periods, findings)
            if spec.sources.headcount
            else None
        )
        for name, frame in (("plan", plan), ("actuals", gl)):
            tie.append(
                TieOut(
                    source=name,
                    label="rows loaded",
                    amount=float(frame.attrs.get("loaded_rows", len(frame))),
                )
            )

        rates = self._rates(reader, periods, findings)
        unreadable = [f for f in findings if f.code.endswith("_number_unreadable")]
        for finding in unreadable:
            tie.append(
                TieOut(
                    source=finding.code.removesuffix("_number_unreadable"),
                    label="rows left out: unreadable number",
                    amount=float(finding.count),
                    note="row count; excluded monetary value is unknown",
                )
            )
        direction = (
            spec.sources.fx.rate_direction
            if spec.sources.fx
            else RateDirection.TO_REPORTING
        )
        self._currency_check(
            [plan, gl] + [f for f in (pos, inv) if f is not None], rates, findings
        )
        fx = FxConverter(spec.reporting_currency.upper(), rates, direction)
        used: dict[tuple[str, str], tuple[float, str]] = {}

        for dim in spec.grain:
            if dim not in plan.columns:
                raise SpecError(f"plan has no column mapped to grain '{dim}'")
        plan["nature"] = self._nature(plan)
        plan = fx.convert(plan, ["amount"], "plan", findings, used)
        plan_values = {d: set(plan[d].map(normal_text)) for d in spec.grain}
        parents = self._parents(reader)
        keyer = LineKeyer(spec.grain, plan_values, parents)
        plan = keyer.apply(plan, "plan", findings)
        dup = plan.groupby(["key", "period"]).size()
        if (dup > 1).any() and "version" not in plan.columns:
            findings.append(
                Finding(
                    code="plan_repeats",
                    severity="info",
                    count=int((dup > 1).sum()),
                    message=f"{int((dup > 1).sum())} plan line-periods appear on more than one row; they are summed. If the file holds several versions or scenarios, filter to one.",
                )
            )

        self._source_totals(gl, "actuals", tie)
        gl = fx.convert(gl, ["amount"], "actuals", findings, used)
        gl = keyer.apply(gl, "actuals", findings)
        gl["nature"] = self._nature(gl)
        gl_bad_period = gl["period"].isna()
        gl_bad_fx = gl["fx_rate"].isna()
        gl_ok = gl[~gl_bad_period & ~gl_bad_fx]
        tie.append(
            TieOut(
                source="actuals",
                label="left out: unreadable period",
                amount=float(gl.loc[gl_bad_period, "amount_src"].sum()),
                note="source currency",
            )
        )
        tie.append(
            TieOut(
                source="actuals",
                label="left out: no exchange rate",
                amount=float(gl.loc[gl_bad_fx & ~gl_bad_period, "amount_src"].sum()),
                note="source currency",
            )
        )

        ytd = set(window.ytd_periods)
        gl_ytd = gl_ok[gl_ok["period"].isin(ytd)]
        gl_before = gl_ok[gl_ok["period"] < window.horizon_start]
        gl_after = gl_ok[gl_ok["period"] > window.last_closed]
        if not gl_after.empty:
            findings.append(
                Finding(
                    code="open_period_actuals",
                    severity="info",
                    count=len(gl_after),
                    amount=float(gl_after["amount"].sum()),
                    message=f"{len(gl_after)} GL rows ({money(symbol, float(gl_after['amount'].sum()))}) are dated after the last closed period {window.last_closed}. They are shown separately and not counted as year-to-date actuals.",
                )
            )

        if pos is not None:
            pos = self._prep_commitments(pos, fx, keyer, findings, used, window)
        if inv is not None:
            inv = self._prep_invoices(inv, pos, fx, keyer, findings, used, window)
        ledger = CommitmentLedger(spec, as_of)
        commitments, invoices, linkage, pending_extra = ledger.build(
            gl_ok, pos, inv, findings
        )

        lines, monthly, history, plan_hist = self._lines(
            plan, gl_ok, gl_ytd, commitments, pending_extra, window
        )
        totals_plan_ytd = sum(litem.plan_ytd for litem in lines)
        gross_ytd = sum(abs(litem.plan_ytd) for litem in lines)
        gross_cur = sum(abs(litem.plan_cur) for litem in lines)
        m_ytd = (
            spec.rules.materiality_amount
            if spec.rules.materiality_amount
            else nice_round(spec.rules.materiality_share * gross_ytd)
        )
        m_cur = (
            spec.rules.materiality_amount
            if spec.rules.materiality_amount
            else nice_round(spec.rules.materiality_share * 2 * gross_cur)
        )
        screen = OutlierScreen(spec.rules, symbol, m_ytd, m_cur, window.last_closed)
        flags = screen.screen(lines, history, plan_hist, commitments, invoices, as_of)
        flagged: dict[str, list[FlagItem]] = {}
        for f in flags:
            flagged.setdefault(f.key, []).append(f)
        for litem in lines:
            fl = flagged.get(litem.key, [])
            litem.flags = [f.id for f in fl]
            litem.tier = (
                Tier.INSPECT
                if any(f.tier == Tier.INSPECT for f in fl)
                else (Tier.WATCH if fl else None)
            )

        unplanned = self._unplanned(gl_ytd)
        hc_rows, hc_flags = self._headcount(hc, keyer, findings, window)

        totals = Totals(
            plan_ytd=totals_plan_ytd,
            actual_ytd=sum(litem.actual_ytd for litem in lines),
            var_ytd=sum(litem.var_ytd for litem in lines),
            var_pct_ytd=safe_pct(
                sum(litem.var_ytd for litem in lines), totals_plan_ytd
            ),
            plan_cur=sum(litem.plan_cur for litem in lines),
            actual_cur=sum(litem.actual_cur for litem in lines),
            var_cur=sum(litem.var_cur for litem in lines),
            plan_fy=sum(litem.plan_fy for litem in lines),
            pending=sum(litem.pending for litem in lines),
            open_commitments=sum(litem.open_commitments for litem in lines),
            committed=sum(litem.committed for litem in lines),
            available=sum(litem.available for litem in lines),
            unplanned_ytd=sum(litem.actual_ytd for litem in lines if not litem.in_plan),
            open_period_actuals=float(gl_after["amount"].sum()),
            materiality_ytd=m_ytd,
            materiality_cur=m_cur,
        )
        proof = self._proof(
            gl_ok, gl_ytd, gl_before, gl_after, lines, commitments, plan, window
        )
        if unreadable:
            proof.append(
                self._check(
                    "All source numbers are readable",
                    float(sum(f.count for f in unreadable)),
                    0.0,
                    "Unreadable numeric rows must be corrected before totals "
                    "can be treated as complete; their monetary value is unknown.",
                )
            )
        if not all(p.passed for p in proof):
            findings.append(
                Finding(
                    code="tie_out_failed",
                    severity="error",
                    message="At least one tie-out check failed. Do not present totals until the failing check is explained.",
                )
            )
        tie.extend(
            [
                TieOut(
                    source="actuals",
                    label="year to date, on plan lines",
                    amount=sum(litem.actual_ytd for litem in lines if litem.in_plan),
                ),
                TieOut(
                    source="actuals",
                    label="year to date, unplanned",
                    amount=totals.unplanned_ytd,
                ),
                TieOut(
                    source="actuals",
                    label="before the plan horizon (history only)",
                    amount=float(gl_before["amount"].sum()),
                ),
                TieOut(
                    source="actuals",
                    label="after the last closed period",
                    amount=totals.open_period_actuals,
                ),
            ]
        )
        fx_used = [
            {"currency": c, "period": p, "rate": round(r, 8), "basis": b}
            for (c, p), (r, b) in sorted(used.items())
        ]
        fallback = [
            x
            for x in fx_used
            if str(x["basis"]).startswith("fallback")
            and str(x["period"]) <= window.last_closed
        ]
        future = [
            x
            for x in fx_used
            if str(x["basis"]).startswith("fallback")
            and str(x["period"]) > window.last_closed
        ]
        if future:
            findings.append(
                Finding(
                    code="fx_future_periods",
                    severity="info",
                    count=len(future),
                    message="Plan months after the last closed period use the latest available rate for each currency.",
                )
            )
        if fallback:
            pairs = ", ".join(f"{x['currency']} {x['period']}" for x in fallback[:6])
            findings.append(
                Finding(
                    code="fx_fallback",
                    severity="warning",
                    count=len(fallback),
                    message=f"No rate for {file_data(pairs)}{' and more' if len(fallback) > 6 else ''}; the latest earlier rate was used. Confirm or supply the period rate.",
                )
            )
        drill = self._drill(gl_ok, window) if self.drill_key else []
        return ReconResult(
            drill=drill,
            drill_key=self.drill_key,
            data_notice=spec.data_notice,
            engine_version=ENGINE_VERSION,
            name=spec.name,
            reporting_currency=spec.reporting_currency.upper(),
            currency_symbol=symbol,
            sign_convention=spec.sign_convention,
            grain=spec.grain,
            window=window,
            totals=totals,
            linkage=linkage,
            lines=lines,
            monthly=monthly,
            flags=flags,
            commitments=commitments,
            invoices=invoices,
            unplanned=unplanned,
            headcount=hc_rows,
            headcount_flags=hc_flags,
            tie_out=tie,
            proof=proof,
            findings=findings,
            fx_used=fx_used,
            spec=json.loads(spec.model_dump_json()),
            source_files=[
                str((self.base_dir / source.path).resolve())
                for source in [
                    *(source for _, source in spec.sources),
                    *spec.hierarchies,
                ]
                if source is not None and source.path
            ],
        )

    def _drill(self, gl_ok: pd.DataFrame, window: Window) -> list[DrillRow]:
        frame = gl_ok[gl_ok["key"] == self.drill_key]
        frame = (
            frame[frame["period"] == self.drill_period]
            if self.drill_period
            else frame[frame["period"].isin(set(window.ytd_periods))]
        )
        frame = frame.reindex(
            frame["amount"].abs().sort_values(ascending=False).index
        ).head(DRILL_ROWS)
        source_cols = [
            c for c in self.spec.grain if c in self.spec.sources.actuals.columns
        ]
        rows = []
        for _, r in frame.iterrows():
            rows.append(
                DrillRow(
                    period=r["period"],
                    amount=float(r["amount"]),
                    amount_source=float(r["amount_src"]),
                    currency=r["currency"],
                    vendor=normal_text(r.get("vendor", "")),
                    description=normal_text(r.get("description", "")),
                    reference=normal_text(r.get("reference", "")),
                    invoice_ref=normal_text(r.get("invoice_ref", "")),
                    source_value=", ".join(
                        f"{c}={normal_text(r.get(c + '_source', ''))}"
                        for c in source_cols
                    ),
                )
            )
        if frame.empty:
            logger.info("Drill: no GL rows for key %s", self.drill_key)
        return rows

    def _window(self) -> Window:
        spec = self.spec
        last = spec.last_closed_period
        fy = spec.fiscal_year_start_month
        y, m = int(last[:4]), int(last[5:])
        start_year = y if m >= fy else y - 1
        start = spec.horizon_start or f"{start_year:04d}-{fy:02d}"
        end = spec.horizon_end or shift_period(f"{start_year:04d}-{fy:02d}", 11)
        ytd = period_range(start, last)
        horizon = period_range(start, end)
        as_of = (
            spec.as_of_date
            or date(
                int(shift_period(last, 1)[:4]), int(shift_period(last, 1)[5:]), 1
            ).isoformat()
        )
        return Window(
            horizon_start=start,
            horizon_end=end,
            last_closed=last,
            ytd_periods=ytd,
            horizon_periods=horizon,
            elapsed_share=len(ytd) / max(len(horizon), 1),
            as_of_date=as_of,
        )

    def _load(
        self,
        name: str,
        src: SourceSpec | None,
        reader: TableReader,
        periods: PeriodParser,
        findings: list[Finding],
    ) -> pd.DataFrame:
        raw = reader.read(src)
        frame = SourceNormalizer(name, src, periods, findings).normalize(raw)
        frame["currency"] = frame["currency"].replace(
            "", self.spec.reporting_currency.upper()
        )
        logger.info(
            "%s: %d source rows, %d records after filters and layout",
            name,
            frame.attrs.get("loaded_rows", len(frame)),
            len(frame),
        )
        return frame

    def _rates(
        self,
        reader: TableReader,
        periods: PeriodParser,
        findings: list[Finding],
    ) -> pd.DataFrame:
        if not self.spec.sources.fx:
            return pd.DataFrame(columns=["currency", "period", "rate"])
        frame = SourceNormalizer(
            "fx", self.spec.sources.fx, periods, findings
        ).normalize(reader.read(self.spec.sources.fx))
        if any(f.code == "fx_number_unreadable" for f in findings):
            raise SpecError(
                "FX contains unreadable numbers; correct them before converting "
                "amounts so an older rate is not silently substituted."
            )
        frame = frame.dropna(subset=["period"])
        return frame[frame["rate"] > 0][["currency", "period", "rate"]]

    def _currency_check(
        self, frames: list[pd.DataFrame], rates: pd.DataFrame, findings: list[Finding]
    ) -> None:
        seen = set()
        for f in frames:
            seen |= set(f["currency"])
        foreign = sorted(c for c in seen - {self.spec.reporting_currency.upper(), ""})
        missing = [c for c in foreign if c not in set(rates["currency"])]
        if missing:
            findings.append(
                Finding(
                    code="fx_currency_missing",
                    severity="error",
                    count=len(missing),
                    message=f"No exchange rates were provided for {file_data(missing)}. Rows in those currencies are left out until rates are supplied.",
                )
            )

    def _nature(self, frame: pd.DataFrame) -> pd.Series:
        rev = self.spec.rules.revenue
        if not rev or rev.column not in frame.columns:
            return pd.Series([Nature.COST.value] * len(frame), index=frame.index)
        wanted = {v.lower() for v in rev.values}
        hit = frame[rev.column].map(lambda x: normal_text(x).lower() in wanted)
        if rev.action == FilterAction.EXCLUDE:
            hit = ~hit
        return hit.map(lambda h: Nature.REVENUE.value if h else Nature.COST.value)

    def _parents(self, reader: TableReader) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for h in self.spec.hierarchies:
            tree = {normal_text(k): normal_text(v) for k, v in h.mapping.items()}
            if h.path:
                frame = reader.read(SourceSpec(path=h.path, sheet=h.sheet))
                frame.columns = [normal_text(c) for c in frame.columns]
                if (
                    h.child_column not in frame.columns
                    or h.parent_column not in frame.columns
                ):
                    raise SpecError(
                        f"hierarchy for {h.dimension}: columns not found; "
                        f"{file_data([h.child_column, h.parent_column])}"
                    )
                for child, parent in zip(
                    frame[h.child_column], frame[h.parent_column], strict=False
                ):
                    if normal_text(child) and normal_text(parent):
                        tree[normal_text(child)] = normal_text(parent)
            out[h.dimension] = tree
        return out

    def _source_totals(
        self, frame: pd.DataFrame, source: str, tie: list[TieOut]
    ) -> float:
        total = 0.0
        for cur, amt in frame.groupby("currency")["amount"].sum().items():
            tie.append(
                TieOut(
                    source=source,
                    label=f"source total {cur or self.spec.reporting_currency}",
                    amount=float(amt),
                    note="source currency, after filters and sign",
                )
            )
            total += float(amt)
        return total

    def _prep_commitments(
        self,
        pos: pd.DataFrame,
        fx: FxConverter,
        keyer: LineKeyer,
        findings: list[Finding],
        used: dict,
        window: Window,
    ) -> pd.DataFrame:
        if "po_number" not in pos.columns or "ordered" not in pos.columns:
            raise SpecError("commitments need po_number and ordered columns")
        periods = PeriodParser(
            self.spec.fiscal_year_start_month,
            self.spec.fiscal_year_label,
            self.spec.date_order,
        )
        pos["po_number"] = pos["po_number"].map(normal_text)
        pos["need_by_period"] = (
            pos["need_by"].map(periods.parse) if "need_by" in pos.columns else None
        )
        pos["fx_period"] = window.last_closed
        cols = [
            c
            for c in ("ordered", "received", "invoiced", "open_amount")
            if c in pos.columns
        ]
        pos = fx.convert(
            pos, cols, "commitments", findings, used, period_col="fx_period"
        )
        pos = pos[~pos["fx_rate"].isna()]
        return keyer.apply(pos, "commitments", findings)

    def _prep_invoices(
        self,
        inv: pd.DataFrame,
        pos: pd.DataFrame | None,
        fx: FxConverter,
        keyer: LineKeyer,
        findings: list[Finding],
        used: dict,
        window: Window,
    ) -> pd.DataFrame:
        if "amount" not in inv.columns:
            raise SpecError("invoices need an amount column")
        if "invoice_number" not in inv.columns:
            inv["invoice_number"] = [f"row{i + 1}" for i in range(len(inv))]
        inv["invoice_number"] = inv["invoice_number"].map(normal_text)
        if "po_number" in inv.columns:
            inv["po_number"] = inv["po_number"].map(normal_text)
        inv["invoice_date_parsed"] = (
            inv["invoice_date"].map(self._as_date)
            if "invoice_date" in inv.columns
            else None
        )
        if "period" not in inv.columns or inv["period"].isna().all():
            inv["period"] = inv["invoice_date_parsed"].map(
                lambda d: (
                    f"{d.year:04d}-{d.month:02d}"
                    if isinstance(d, date)
                    else window.last_closed
                )
            )
        inv["period"] = inv["period"].fillna(window.last_closed)
        inv = fx.convert(inv, ["amount"], "invoices", findings, used)
        inv = inv[~inv["fx_rate"].isna()].copy()
        if pos is not None and "po_number" in inv.columns:
            first = pos.drop_duplicates("po_number").set_index("po_number")
            for dim in self.spec.grain:
                if dim not in inv.columns:
                    inv[dim] = ""
                fill = inv["po_number"].map(
                    lambda p, d=dim: (
                        first[d].get(normal_text(p), "")
                        if normal_text(p) in first.index
                        else ""
                    )
                )
                inv[dim] = (
                    inv[dim]
                    .map(normal_text)
                    .where(inv[dim].map(normal_text) != "", fill)
                )
        return keyer.apply(inv, "invoices", findings)

    def _as_date(self, value: object) -> date | None:
        return parse_date(value, self.spec.date_order)

    def _lines(
        self,
        plan: pd.DataFrame,
        gl_ok: pd.DataFrame,
        gl_ytd: pd.DataFrame,
        commitments: list[CommitmentRow],
        pending_extra: pd.DataFrame,
        window: Window,
    ) -> tuple[
        list[LineResult],
        list[MonthlyRow],
        dict[str, dict[str, float]],
        dict[str, dict[str, float]],
    ]:
        ytd = set(window.ytd_periods)
        horizon = set(window.horizon_periods)
        last = window.last_closed
        plan_ok = plan[~plan["fx_rate"].isna() & plan["period"].notna()]
        plan_lp = plan_ok.groupby(["key", "period"])["amount"].sum()
        gl_lp = gl_ok.groupby(["key", "period"])["amount"].sum()
        keys_info: dict[str, dict[str, str]] = {}
        nature: dict[str, str] = {}
        for frame in (plan_ok, gl_ok):
            for _, r in frame.drop_duplicates("key").iterrows():
                keys_info.setdefault(
                    r["key"], {d: normal_text(r[d]) for d in self.spec.grain}
                )
                nature.setdefault(r["key"], r.get("nature", Nature.COST.value))
        for c in commitments:
            keys_info.setdefault(c.key, c.keys)
            nature.setdefault(c.key, Nature.COST.value)
        if not pending_extra.empty:
            for k in pending_extra["key"]:
                keys_info.setdefault(
                    k, dict(zip(self.spec.grain, k.split(" | "), strict=False))
                )
                nature.setdefault(k, Nature.COST.value)
        plan_keys = set(plan_ok["key"])
        pend = {c.key: 0.0 for c in commitments}
        opn = {c.key: 0.0 for c in commitments}
        for c in commitments:
            pend[c.key] = pend.get(c.key, 0.0) + c.pending
            opn[c.key] = opn.get(c.key, 0.0) + c.open_amount
        if not pending_extra.empty:
            for k, amt in pending_extra.groupby("key")["amount"].sum().items():
                pend[k] = pend.get(k, 0.0) + float(amt)
        history: dict[str, dict[str, float]] = {}
        plan_hist: dict[str, dict[str, float]] = {}
        for (k, p), v in gl_lp.items():
            if p <= last:
                history.setdefault(k, {})[p] = float(v)
        for (k, p), v in plan_lp.items():
            plan_hist.setdefault(k, {})[p] = float(v)
        lines: list[LineResult] = []
        monthly: list[MonthlyRow] = []
        for key in sorted(keys_info):
            p_hist = plan_hist.get(key, {})
            a_hist = history.get(key, {})
            plan_ytd = sum(v for p, v in p_hist.items() if p in ytd)
            actual_ytd = sum(v for p, v in a_hist.items() if p in ytd)
            plan_cur = p_hist.get(last, 0.0)
            actual_cur = a_hist.get(last, 0.0)
            plan_fy = sum(v for p, v in p_hist.items() if p in horizon)
            is_cost = nature.get(key, Nature.COST.value) == Nature.COST.value
            pending = pend.get(key, 0.0) if is_cost else 0.0
            open_c = opn.get(key, 0.0) if is_cost else 0.0
            committed = actual_ytd + pending + open_c
            lines.append(
                LineResult(
                    key=key,
                    keys=keys_info[key],
                    nature=Nature(nature.get(key, Nature.COST.value)),
                    in_plan=key in plan_keys,
                    plan_ytd=plan_ytd,
                    actual_ytd=actual_ytd,
                    var_ytd=actual_ytd - plan_ytd,
                    var_pct_ytd=safe_pct(actual_ytd - plan_ytd, plan_ytd),
                    plan_cur=plan_cur,
                    actual_cur=actual_cur,
                    var_cur=actual_cur - plan_cur,
                    var_pct_cur=safe_pct(actual_cur - plan_cur, plan_cur),
                    plan_fy=plan_fy,
                    pending=pending,
                    open_commitments=open_c,
                    committed=committed,
                    available=plan_fy - committed,
                )
            )
            for p in window.horizon_periods:
                pv = p_hist.get(p, 0.0)
                av = a_hist.get(p, 0.0) if p <= last else 0.0
                if pv or av:
                    monthly.append(MonthlyRow(key=key, period=p, plan=pv, actual=av))
        return lines, monthly, history, plan_hist

    def _unplanned(self, gl_ytd: pd.DataFrame) -> list[UnplannedRow]:
        frame = gl_ytd[gl_ytd["unplanned_value"] != ""]
        out: list[UnplannedRow] = []
        for (key, val), amt in (
            frame.groupby(["key", "unplanned_value"])["amount"].sum().items()
        ):
            keys = dict(zip(self.spec.grain, key.split(" | "), strict=False))
            out.append(
                UnplannedRow(
                    key=key, keys=keys, source_value=val.strip(), actual_ytd=float(amt)
                )
            )
        out.sort(key=lambda r: -abs(r.actual_ytd))
        return out

    def _headcount(
        self,
        hc: pd.DataFrame | None,
        keyer: LineKeyer,
        findings: list[Finding],
        window: Window,
    ) -> tuple[list[HeadcountRow], list[FlagItem]]:
        if hc is None or hc.empty:
            return [], []
        dims = [d for d in self.spec.grain if d in hc.columns]
        if not dims:
            findings.append(
                Finding(
                    code="headcount_no_keys",
                    severity="warning",
                    message="Headcount has none of the grain columns, so it is shown as one total.",
                )
            )
        hc = hc.dropna(subset=["period"]).copy()
        hc["hc_key"] = hc[dims].astype(str).agg(" | ".join, axis=1) if dims else "Total"
        agg_cols = [
            c for c in ("plan_heads", "actual_heads", "open_reqs") if c in hc.columns
        ]
        grouped = hc.groupby(["hc_key", "period"])[agg_cols].sum().reset_index()
        rows: list[HeadcountRow] = []
        for _, r in grouped.iterrows():
            if r["period"] not in set(window.horizon_periods):
                continue
            keys = (
                dict(zip(dims, str(r["hc_key"]).split(" | "), strict=False))
                if dims
                else {"group": "Total"}
            )
            rows.append(
                HeadcountRow(
                    key=r["hc_key"],
                    keys=keys,
                    period=r["period"],
                    plan=float(r.get("plan_heads", 0.0)),
                    actual=float(r.get("actual_heads", 0.0))
                    if r["period"] <= window.last_closed
                    else 0.0,
                    open_reqs=float(r["open_reqs"]) if "open_reqs" in r.index else None,
                )
            )
        flags = HeadcountScreen(self.spec.rules, window.last_closed).screen(rows)
        return rows, flags

    def _proof(
        self,
        gl_ok: pd.DataFrame,
        gl_ytd: pd.DataFrame,
        gl_before: pd.DataFrame,
        gl_after: pd.DataFrame,
        lines: list[LineResult],
        commitments: list[CommitmentRow],
        plan: pd.DataFrame,
        window: Window,
    ) -> list[ProofCheck]:
        checks: list[ProofCheck] = []
        gl_total = float(gl_ok["amount"].sum())
        parts = (
            sum(litem.actual_ytd for litem in lines)
            + float(gl_before["amount"].sum())
            + float(gl_after["amount"].sum())
        )
        checks.append(
            self._check(
                "GL actuals are each counted once",
                gl_total,
                parts,
                "Converted GL total = year-to-date actuals on every line (planned and unplanned) + history before the horizon + activity after the last closed period.",
            )
        )
        plan_ok = plan[
            ~plan["fx_rate"].isna() & plan["period"].isin(set(window.horizon_periods))
        ]
        checks.append(
            self._check(
                "Plan is carried in full",
                float(plan_ok["amount"].sum()),
                sum(litem.plan_fy for litem in lines),
                "Converted plan rows inside the horizon = full-year plan summed across lines.",
            )
        )
        if commitments:
            ordered = sum(c.ordered for c in commitments)
            split = sum(
                c.posted + c.pending + c.open_amount + c.released - c.overrun
                for c in commitments
            )
            checks.append(
                self._check(
                    "Every ordered dollar is posted, pending, open, or released",
                    ordered,
                    split,
                    "Per PO: ordered = posted + pending + open + released by closing - overrun beyond the order.",
                )
            )
        return checks

    def _check(
        self, name: str, left: float, right: float, explanation: str
    ) -> ProofCheck:
        diff = left - right
        tol = max(TIE_TOLERANCE, 1e-9 * max(abs(left), abs(right)))
        return ProofCheck(
            name=name,
            left=left,
            right=right,
            difference=diff,
            passed=abs(diff) <= tol,
            explanation=explanation,
        )


class ResultWriter:
    """Writes the result JSON."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, result: ReconResult) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            result.model_dump_json(indent=1), encoding="utf-8", newline="\n"
        )


def inspect_items(result: ReconResult) -> int:
    """Inspect items as the report counts them: one per line or document, plus headcount groups."""
    seen = {
        f.key if f.view != "document" else f.id
        for f in result.flags
        if f.tier == Tier.INSPECT
    }
    return len(seen) + sum(1 for f in result.headcount_flags if f.tier == Tier.INSPECT)


def summary_lines(result: ReconResult) -> list[str]:
    s = result.currency_symbol
    t = result.totals
    w = result.window
    lines = [
        f"Window {w.horizon_start} to {w.horizon_end}, last closed {w.last_closed}, reporting {result.reporting_currency}",
        f"YTD plan {money(s, t.plan_ytd)} actual {money(s, t.actual_ytd)} variance {money(s, t.var_ytd)} ({pct_text(t.var_pct_ytd)})",
        f"Full-year plan {money(s, t.plan_fy)} pending {money(s, t.pending)} open {money(s, t.open_commitments)} available {money(s, t.available)}",
        f"Materiality floors: YTD {money(s, t.materiality_ytd)}, month {money(s, t.materiality_cur)}",
        f"Needs inspection: {inspect_items(result)} items (lines with several flags count once, headcount included); flags: {sum(1 for f in result.flags if f.tier == Tier.INSPECT)} inspect, {sum(1 for f in result.flags if f.tier == Tier.WATCH)} watch, {len(result.headcount_flags)} headcount",
        f"Linkage: {result.linkage.method} (confidence {result.linkage.confidence})",
        "Proof: "
        + "; ".join(f"{p.name} {'PASS' if p.passed else 'FAIL'}" for p in result.proof),
    ]
    for f in result.findings:
        lines.append(f"Finding [{f.severity}] {f.code}: {f.message}")
    return lines


def describe_spec_problem(err: Exception) -> str:
    """One line per spec field error, without echoing the submitted values."""
    if not isinstance(err, ValidationError):
        return str(err)
    return "; ".join(
        f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}"
        for issue in err.errors(include_url=False, include_input=False)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile plan against actuals, pending invoices and open commitments."
    )
    parser.add_argument(
        "--spec", required=True, help="Path to the reconciliation spec JSON."
    )
    parser.add_argument("--out", required=True, help="Path for results.json.")
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Folder that relative source paths are resolved against (default: the spec's folder).",
    )
    parser.add_argument(
        "--drill",
        default=None,
        help="A line key exactly as in results.json (for example 'Engineering | 6200') to list its largest GL entries.",
    )
    parser.add_argument(
        "--period",
        default=None,
        help="With --drill: one period YYYY-MM (default: the year to date).",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as err:
        return 0 if err.code == 0 else 2
    spec_path = Path(args.spec)
    try:
        spec = SpecReader(spec_path).read()
        result = Reconciliation(
            spec,
            Path(args.base_dir) if args.base_dir else spec_path.parent,
            args.drill,
            args.period,
        ).run()
    except (ValueError, OSError) as err:
        logger.error("Spec problem: %s", describe_spec_problem(err))
        return 2
    ResultWriter(Path(args.out)).write(result)
    for line in summary_lines(result):
        logger.info(line)
    for d in result.drill:
        logger.info(
            "Drill DATA (untrusted, from file): %s",
            json.dumps(
                {
                    "period": d.period,
                    "amount": d.amount,
                    "currency": d.currency[:DATA_TEXT_LIMIT],
                    "vendor": d.vendor[:DATA_TEXT_LIMIT],
                    "description": d.description[:DATA_TEXT_LIMIT],
                    "reference": d.reference[:DATA_TEXT_LIMIT],
                    "invoice_ref": d.invoice_ref[:DATA_TEXT_LIMIT],
                },
                ensure_ascii=True,
            ),
        )
    logger.info("Wrote %s", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
