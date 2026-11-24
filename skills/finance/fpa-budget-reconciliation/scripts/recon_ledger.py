"""
description: Pure reconciliation steps for run_reconciliation.py: grain keys and hierarchy roll-up, currency conversion by period, and the purchase-order ledger that places each ordered dollar in one bucket.
last_updated: 2026-11-24
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
from recon_models import (
    CommitmentLink,
    CommitmentRow,
    Finding,
    InvoiceRow,
    Linkage,
    OpenBasis,
    RateDirection,
    ReconSpec,
)
from recon_parsing import (
    file_data,
    normal_text,
)

NOT_CODED = "(not coded)"
ACCRUAL_WORD = "accru"


class LineKeyer:
    """Builds the grain key for each row and rolls source values up to the plan's values."""

    def __init__(
        self,
        grain: list[str],
        plan_values: dict[str, set[str]],
        parents: dict[str, dict[str, str]],
    ) -> None:
        self.grain = grain
        self.plan_values = plan_values
        self.parents = parents

    def apply(
        self, frame: pd.DataFrame, source: str, findings: list[Finding]
    ) -> pd.DataFrame:
        frame = frame.copy()
        frame["unplanned_value"] = ""
        for dim in self.grain:
            if dim not in frame.columns:
                frame[dim] = NOT_CODED
                findings.append(
                    Finding(
                        code=f"{source}_missing_{dim}",
                        severity="warning",
                        message=f"{source} has no '{dim}' column; its rows are shown as {NOT_CODED} for {dim}.",
                    )
                )
                continue
            raw_vals = frame[dim].map(normal_text).replace("", NOT_CODED)
            frame[f"{dim}_source"] = raw_vals
            mapped = raw_vals.map(lambda v, d=dim: self._roll_up(d, v))
            unplanned = ~mapped.isin(self.plan_values.get(dim, set())) & (
                mapped != NOT_CODED
            )
            frame.loc[unplanned, "unplanned_value"] = (
                frame.loc[unplanned, "unplanned_value"]
                + f"{dim}="
                + raw_vals[unplanned]
                + " "
            )
            frame[dim] = mapped
        frame["key"] = frame[self.grain].astype(str).agg(" | ".join, axis=1)
        return frame

    def _roll_up(self, dim: str, value: str) -> str:
        allowed = self.plan_values.get(dim, set())
        seen = 0
        current = value
        tree = self.parents.get(dim, {})
        while current not in allowed and current in tree and seen < 20:
            current = tree[current]
            seen += 1
        return current if current in allowed else value


class FxConverter:
    """Converts source-currency amounts to the reporting currency at each period's rate."""

    def __init__(
        self, reporting: str, rates: pd.DataFrame, direction: RateDirection
    ) -> None:
        self.reporting = reporting
        self.rates = rates
        self.direction = direction

    def convert(
        self,
        frame: pd.DataFrame,
        columns: list[str],
        source: str,
        findings: list[Finding],
        used: dict[tuple[str, str], tuple[float, str]],
        period_col: str = "period",
    ) -> pd.DataFrame:
        frame = frame.copy()
        pairs = frame[["currency", period_col]].drop_duplicates()
        lookup = {
            (c, p): self._rate(c, p, used)
            for c, p in zip(pairs["currency"], pairs[period_col], strict=False)
        }
        frame["fx_rate"] = [
            lookup[(c, p)]
            for c, p in zip(frame["currency"], frame[period_col], strict=False)
        ]
        missing = frame["fx_rate"].isna()
        if missing.any():
            gross = float(frame.loc[missing, columns[0]].abs().sum())
            curr = sorted(set(frame.loc[missing, "currency"]))
            findings.append(
                Finding(
                    code=f"{source}_fx_missing",
                    severity="error",
                    count=int(missing.sum()),
                    amount=gross,
                    message=f"{int(missing.sum())} {source} rows in {file_data(curr)} have no exchange rate on or before their period; they are left out of the totals and listed in the tie-out.",
                )
            )
        for col in columns:
            frame[col + "_src"] = frame[col]
            frame[col] = frame[col] * frame["fx_rate"]
        return frame

    def _rate(
        self,
        currency: str,
        period: str | None,
        used: dict[tuple[str, str], tuple[float, str]],
    ) -> float:
        if not currency or currency == self.reporting:
            return 1.0
        if period is None or (isinstance(period, float) and math.isnan(period)):
            return float("nan")
        cached = used.get((currency, period))
        if cached:
            return cached[0]
        table = self.rates[
            (self.rates["currency"] == currency) & (self.rates["period"] <= period)
        ]
        if table.empty:
            return float("nan")
        row = table.sort_values("period").iloc[-1]
        rate = float(row["rate"])
        rate = (
            rate
            if self.direction == RateDirection.TO_REPORTING
            else (1.0 / rate if rate else float("nan"))
        )
        used[(currency, period)] = (
            rate,
            "exact" if row["period"] == period else f"fallback {row['period']}",
        )
        return rate


class CommitmentLedger:
    """Splits each purchase order into posted, pending, open and released dollars so no dollar is counted twice."""

    def __init__(self, spec: ReconSpec, as_of: date) -> None:
        self.spec = spec
        self.rules = spec.rules
        self.as_of = as_of

    def build(
        self,
        gl: pd.DataFrame,
        pos: pd.DataFrame | None,
        inv: pd.DataFrame | None,
        findings: list[Finding],
    ) -> tuple[list[CommitmentRow], list[InvoiceRow], Linkage, pd.DataFrame]:
        posted_lower = {s.lower() for s in self.rules.posted_invoice_statuses}
        inv_rows: list[InvoiceRow] = []
        pending_frame = pd.DataFrame(columns=["key", "amount"])
        gl_inv = (
            set(gl["invoice_ref"].map(normal_text)) - {""}
            if "invoice_ref" in gl.columns
            else set()
        )
        if inv is not None and not inv.empty:
            inv = inv.copy()
            inv["invoice_number"] = (
                inv["invoice_number"].map(normal_text)
                if "invoice_number" in inv.columns
                else ""
            )
            inv["po_number"] = (
                inv["po_number"].map(normal_text) if "po_number" in inv.columns else ""
            )
            inv["status"] = (
                inv["status"].map(lambda x: normal_text(x).lower())
                if "status" in inv.columns
                else ""
            )
            inv["posted_state"] = inv.apply(
                lambda r: self._posted(r, gl_inv, posted_lower), axis=1
            )
            unknown = int(inv["posted_state"].isna().sum())
            if unknown:
                findings.append(
                    Finding(
                        code="invoice_posting_unknown",
                        severity="warning",
                        count=unknown,
                        amount=float(
                            inv.loc[inv["posted_state"].isna(), "amount"].abs().sum()
                        ),
                        message=f"{unknown} invoices carry no status and no GL reference, so the skill cannot tell whether they are already in actuals. They are not added as pending (to avoid double counting) and are listed as unverified.",
                    )
                )
        link = self._link_method(gl, pos, inv)
        if pos is None or pos.empty:
            if inv is not None and not inv.empty:
                pend = inv[inv["posted_state"] == False]  # noqa: E712
                pending_frame = pend[["key", "amount"]]
                inv_rows = self._invoice_rows(inv)
            return [], inv_rows, link, pending_frame
        pos = pos.copy()
        pos["po_number"] = pos["po_number"].map(normal_text)
        pos["po_line"] = (
            pos["po_line"].map(normal_text) if "po_line" in pos.columns else "1"
        )
        pos["status"] = (
            pos["status"].map(lambda x: normal_text(x).lower())
            if "status" in pos.columns
            else "open"
        )
        gl_po = self._gl_by_po(gl, inv)
        inv_pending_po = {}
        inv_any_po = {}
        if inv is not None and not inv.empty:
            withpo = inv[inv["po_number"] != ""]
            inv_pending_po = (
                withpo[withpo["posted_state"].eq(False)]
                .groupby("po_number")["amount"]
                .sum()
                .to_dict()
            )
            inv_any_po = withpo.groupby("po_number")["amount"].sum().to_dict()
        rows: list[CommitmentRow] = []
        closed = {s.lower() for s in self.rules.closed_statuses}
        for po_number, group in pos.groupby("po_number", sort=False):
            ordered_total = float(group["ordered"].sum())
            posted = float(gl_po.get(po_number, 0.0))
            pending = float(inv_pending_po.get(po_number, 0.0))
            is_closed = group["status"].isin(closed).all()
            if link.method == CommitmentLink.BY_REFERENCE.value:
                consumed = posted + pending
            elif link.method == CommitmentLink.OPEN_COLUMN.value:
                open_given = float(group["open_amount"].sum())
                consumed = ordered_total - open_given
                if self.rules.open_basis == OpenBasis.NET_OF_POSTED:
                    pending = 0.0
            else:
                invoiced = (
                    float(group["invoiced"].sum())
                    if "invoiced" in group.columns
                    else float(inv_any_po.get(po_number, 0.0))
                )
                consumed = invoiced
            if link.method != CommitmentLink.BY_REFERENCE.value:
                posted = consumed - pending
            open_total = 0.0 if is_closed else max(ordered_total - consumed, 0.0)
            released = max(ordered_total - consumed, 0.0) if is_closed else 0.0
            overrun = max(consumed - ordered_total, 0.0)
            weights = group["ordered"].abs()
            weights = (
                weights / weights.sum()
                if weights.sum()
                else pd.Series([1.0 / len(group)] * len(group), index=group.index)
            )
            for idx, line in group.iterrows():
                w = float(weights.loc[idx])
                rows.append(
                    CommitmentRow(
                        po_number=po_number,
                        po_line=normal_text(line["po_line"]) or "1",
                        key=line["key"],
                        keys={d: normal_text(line[d]) for d in self.spec.grain},
                        vendor=normal_text(line.get("vendor", "")),
                        status=line["status"] or "open",
                        need_by=line.get("need_by_period") or None,
                        ordered=float(line["ordered"]),
                        posted=posted * w,
                        pending=pending * w,
                        open_amount=open_total * w,
                        released=released * w,
                        overrun=overrun * w,
                        link=link.method,
                    )
                )
        if inv is not None and not inv.empty:
            no_po = inv[
                (inv["po_number"] == "")
                | (~inv["po_number"].isin(set(pos["po_number"])))
            ]
            pend = no_po[no_po["posted_state"] == False]  # noqa: E712
            pending_frame = pend[["key", "amount"]]
            inv_rows = self._invoice_rows(inv)
        self._accrual_check(gl, findings)
        return rows, inv_rows, link, pending_frame

    def _posted(
        self, row: pd.Series, gl_inv: set[str], posted_lower: set[str]
    ) -> bool | None:
        if gl_inv:
            return row["invoice_number"] in gl_inv
        if "posted" in row.index and normal_text(row["posted"]):
            return normal_text(row["posted"]).lower() in {
                "y",
                "yes",
                "true",
                "1",
                "posted",
            }
        if row["status"]:
            return row["status"] in posted_lower
        return None

    def _link_method(
        self, gl: pd.DataFrame, pos: pd.DataFrame | None, inv: pd.DataFrame | None
    ) -> Linkage:
        chosen = self.rules.commitment_link
        if pos is None or pos.empty:
            return Linkage(
                method="none",
                confidence="n/a",
                matched_share=None,
                note="No purchase orders were provided, so open commitments are zero.",
            )
        po_numbers = set(pos["po_number"].map(normal_text))
        refs = (
            set(gl["reference"].map(normal_text))
            if "reference" in gl.columns
            else set()
        )
        if (
            inv is not None
            and "invoice_ref" in gl.columns
            and "po_number" in inv.columns
        ):
            inv_map = dict(
                zip(
                    inv["invoice_number"].map(normal_text),
                    inv["po_number"].map(normal_text),
                    strict=False,
                )
            )
            refs |= {inv_map.get(normal_text(x), "") for x in gl["invoice_ref"]}
        matched = len(po_numbers & refs)
        share = matched / len(po_numbers) if po_numbers else None
        if chosen == CommitmentLink.AUTO:
            if share and share >= 0.2:
                chosen = CommitmentLink.BY_REFERENCE
            elif "open_amount" in pos.columns:
                chosen = CommitmentLink.OPEN_COLUMN
            else:
                chosen = CommitmentLink.ORDERED_LESS_INVOICED
        notes = {
            CommitmentLink.BY_REFERENCE: "Open = ordered minus GL actuals carrying the PO (directly or through its invoice) minus invoices not yet posted. Each dollar sits in exactly one of posted, pending, or open.",
            CommitmentLink.OPEN_COLUMN: "Open amounts are taken from the PO file's open or remaining column, as confirmed with the user.",
            CommitmentLink.ORDERED_LESS_INVOICED: "Open = ordered minus invoiced. GL actuals carry no PO reference, so overlap between open POs and posted spend cannot be proven line by line.",
        }
        confidence = (
            "high"
            if chosen == CommitmentLink.BY_REFERENCE and share and share >= 0.6
            else ("medium" if chosen != CommitmentLink.ORDERED_LESS_INVOICED else "low")
        )
        return Linkage(
            method=chosen.value,
            confidence=confidence,
            matched_share=share,
            note=notes[chosen],
        )

    def _gl_by_po(self, gl: pd.DataFrame, inv: pd.DataFrame | None) -> dict[str, float]:
        frame = gl.copy()
        frame["po_link"] = (
            frame["reference"].map(normal_text) if "reference" in frame.columns else ""
        )
        if (
            inv is not None
            and "invoice_ref" in frame.columns
            and "po_number" in inv.columns
        ):
            inv_map = dict(zip(inv["invoice_number"], inv["po_number"], strict=False))
            fill = frame["invoice_ref"].map(lambda x: inv_map.get(normal_text(x), ""))
            frame["po_link"] = frame["po_link"].where(frame["po_link"] != "", fill)
        frame = frame[frame["po_link"] != ""]
        return frame.groupby("po_link")["amount"].sum().to_dict()

    def _invoice_rows(self, inv: pd.DataFrame) -> list[InvoiceRow]:
        rows: list[InvoiceRow] = []
        for _, r in inv.iterrows():
            state = r["posted_state"]
            posted = (
                None
                if state is None or (isinstance(state, float) and math.isnan(state))
                else bool(state)
            )
            inv_date = r.get("invoice_date_parsed")
            days = (
                (self.as_of - inv_date).days
                if (posted is False and isinstance(inv_date, date))
                else None
            )
            rows.append(
                InvoiceRow(
                    invoice_number=r["invoice_number"],
                    po_number=r["po_number"],
                    key=r["key"],
                    vendor=normal_text(r.get("vendor", "")),
                    invoice_date=inv_date.isoformat()
                    if isinstance(inv_date, date)
                    else None,
                    amount=float(r["amount"]),
                    status=r["status"] or "",
                    posted=posted,
                    days_unposted=days,
                )
            )
        return rows

    def _accrual_check(self, gl: pd.DataFrame, findings: list[Finding]) -> None:
        text = pd.Series([""] * len(gl), index=gl.index)
        for col in ("entry_type", "description"):
            if col in gl.columns:
                text = text + " " + gl[col].map(lambda x: normal_text(x).lower())
        accrual = text.str.contains(ACCRUAL_WORD)
        no_ref = (
            gl["reference"].map(normal_text) == ""
            if "reference" in gl.columns
            else pd.Series([True] * len(gl), index=gl.index)
        )
        hit = accrual & no_ref & (gl["amount"] > 0)
        if hit.any():
            amount = float(gl.loc[hit, "amount"].sum())
            note = (
                ""
                if self.rules.accruals_in_gl is not False
                else " The user said accruals are not booked, so check these entries."
            )
            findings.append(
                Finding(
                    code="accruals_without_po",
                    severity="warning",
                    count=int(hit.sum()),
                    amount=amount,
                    message=f"{int(hit.sum())} accrual entries ({amount:,.0f} in the reporting currency) carry no PO reference. If they accrue receipts on open POs, open commitments are overstated by up to this amount.{note}",
                )
            )
